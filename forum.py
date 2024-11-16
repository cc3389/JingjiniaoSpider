from bs4 import BeautifulSoup
import re
import concurrent.futures
from myThread import thread_spider
from util import *
import logging
from typing import Optional, Tuple
from dataclasses import dataclass, field
from typing import List

@dataclass
class ForumData:
    """论坛数据容器类"""
    links: List[str] = field(default_factory=list)
    comments: List[str] = field(default_factory=list)
    views: List[str] = field(default_factory=list)
    authors: List[str] = field(default_factory=list)
    tids: List[str] = field(default_factory=list)
    uids: List[str] = field(default_factory=list)
    titles: List[str] = field(default_factory=list)
    update_times: List[str] = field(default_factory=list)
    create_times: List[str] = field(default_factory=list)
    recommends: List[int] = field(default_factory=list)
    favorites: List[int] = field(default_factory=list)
    _tid_set: set = field(default_factory=set)  # 新增：用于追踪已存在的tid

    def add_thread(self, tid: str, link: str, comment: str, view: str, 
                  author: str, uid: str, title: str, update_time: str, 
                  create_time: str) -> bool:
        """
        添加一个主题的数据，如果tid已存在则返回False
        """
        if tid in self._tid_set:
            return False
            
        self._tid_set.add(tid)
        self.tids.append(tid)
        self.links.append(link)
        self.comments.append(comment)
        self.views.append(view)
        self.authors.append(author)
        self.uids.append(uid)
        self.titles.append(title)
        self.update_times.append(update_time)
        self.create_times.append(create_time)
        return True

class ForumSpiderError(Exception):
    """爬虫相关的自定义异常基类"""
    pass

class ParseError(ForumSpiderError):
    """解析错误"""
    pass

class NetworkError(ForumSpiderError):
    """网络请求错误"""
    pass

def main_spider(block_name: str, block_url: str, download_images: bool) -> Optional[ForumData]:
    logger = logging.getLogger(__name__)
    total_data = ForumData()
    
    try:
        # 首先获取第一页以确定总页数
        response = make_request(block_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        if len(soup.select("#messagetext")) > 0:
            error_message = soup.select("#messagetext")[0].text + soup.select("#messagetext")[0].next_sibling.text
            raise NetworkError(error_message)
        
        last_page_num = int(_get_last_page_number(soup))
        logger.info(f"检测到总页数: {last_page_num}")
        
        # 生成所有页面的URL
        page_urls = []
        for page_num in range(1, last_page_num + 1):
            if page_num == 1:
                page_urls.append(block_url)
            else:
                page_url = block_url.replace("-1.html", f"-{page_num}.html")
                page_urls.append(page_url)
        
        # 使用线程池并行处理所有页面
        page_data_list = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            future_to_url = {
                executor.submit(_fetch_page_data, url, page_num + 1): url 
                for page_num, url in enumerate(page_urls)
            }
            
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    page_data = future.result()
                    if page_data:
                        page_data_list.append(page_data)
                except Exception as e:
                    logger.error(f'处理页面 {url} 失败: {e}')

        # 合并所有页面数据
        for page_data in page_data_list:
            _merge_page_data(total_data, page_data)

        # 获取完所有页面数据后，使用集合去重确保任务不重复
        processed_tasks = set()  # 用于追踪已提交的任务
        thread_futures = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # 修改提交任务的逻辑
            for tid, link, title in zip(total_data.tids, total_data.links, total_data.titles):
                # 使用tid作为唯一标识
                task_key = f"{tid}"
                if task_key not in processed_tasks:
                    processed_tasks.add(task_key)
                    future = executor.submit(threadWrapper, link, block_name, title, download_images)
                    thread_futures.append(future)

            # 处理线程结果
            _process_thread_results(thread_futures, total_data)
        
        # 保存数据
        write_to_csv(total_data.titles, total_data.authors, total_data.comments,
                    total_data.views, block_name, total_data.update_times, 
                    total_data.links, "data.csv", total_data.recommends, total_data.favorites,
                    total_data.create_times)
        
        return total_data
        
    except Exception as e:
        logger.error(f'爬取 {block_name} 失败: {e}', exc_info=True)
        return None

def _fetch_page_data(url: str, page_num: int) -> Optional[ForumData]:
    """
    获取单个页面的数据
    
    Args:
        url: 页面URL
        page_num: 页码
        
    Returns:
        ForumData 对象或在发生错误时返回 None
    """
    logger = logging.getLogger(__name__)
    try:
        response = make_request(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        if len(soup.select("#messagetext")) > 0:
            error_message = soup.select("#messagetext")[0].text + soup.select("#messagetext")[0].next_sibling.text
            raise NetworkError(error_message)
        
        page_data = parse_page_data(soup, ForumData(), page_num)
        return page_data
        
    except Exception as e:
        logger.error(f'获取页面 {url} 数据失败: {e}')
        return None

def _get_last_page_number(soup: BeautifulSoup) -> str:
    """获取最后一页的页码"""
    last_page_tag = soup.find("span", title=re.compile("共 [0-9]+ 页"))
    if not last_page_tag:
        raise ParseError("无法获取总页数")
    return last_page_tag.text.replace(" ", "").replace("/", "").replace("页", "")

def _get_next_page_url(soup: BeautifulSoup) -> Optional[str]:
    """获取下一页的URL"""
    next_link_tag = soup.select('.nxt')
    return next_link_tag[0].attrs['href'] if next_link_tag else None

def _merge_page_data(total_data: ForumData, page_data: ForumData) -> None:
    """合并页面数据到总数据中，会自动去除重复的主题"""
    for i, tid in enumerate(page_data.tids):
        total_data.add_thread(
            tid=tid,
            link=page_data.links[i],
            comment=page_data.comments[i],
            view=page_data.views[i],
            author=page_data.authors[i],
            uid=page_data.uids[i],
            title=page_data.titles[i],
            update_time=page_data.update_times[i],
            create_time=page_data.create_times[i]
        )

def _process_thread_results(futures: List[concurrent.futures.Future], total_data: ForumData) -> None:
    """处理线程执行结果"""
    logger = logging.getLogger(__name__)
    
    for future in concurrent.futures.as_completed(futures):
        try:
            result = future.result()
            if result:
                recommend_count, favorite_count = result
                total_data.recommends.append(recommend_count)
                total_data.favorites.append(favorite_count)
            else:
                total_data.recommends.append(0)
                total_data.favorites.append(0)
        except Exception as e:
            logger.error(f"处理线程结果时出错: {e}")
            total_data.recommends.append(0)
            total_data.favorites.append(0)

def threadWrapper(link, block_name, name, download_images):
    # 创建线程并执行
    result = None
    def thread_func():
        nonlocal result
        result = thread_spider(link, block_name, download_images)
    
    thread = threading.Thread(target=thread_func, name=name)
    thread.start()
    thread.join()
    return result

def parse_page_data(soup, page_data, page_num=1):
    """解析页面数据并填充到 page_data 对象中"""
    links = soup.select('.s.xst')
    if len(links) == 0:
        raise ValueError("找不到链接，可能是cookie有误或过期了")
    
    # 临时存储数据
    temp_data = {
        'comments': [],
        'views': [],
        'authors': [],
        'create_times': [],
        'titles': [],
        'update_times': [],
        'tids': [],
        'uids': [],
        'links': []
    }
    
    # 记录解析失败的索引
    failed_indices = set()
    
    # 解析评论数和浏览数
    for i, comment in enumerate(soup.select(".acgifnums")):
        try:
            a_tag = comment.find('a', class_="xi2")
            viewTag = comment.find("span")
            if not a_tag or not viewTag:
                failed_indices.add(i)
                temp_data['comments'].append("0")
                temp_data['views'].append("0")
            else:
                temp_data['comments'].append(a_tag.text)
                temp_data['views'].append(viewTag.text)
        except Exception:
            failed_indices.add(i)
            temp_data['comments'].append("0")
            temp_data['views'].append("0")

    # 解析作者与创建时间
    for i, tag in enumerate(soup.find_all('div', class_='acgifby1')):
        try:
            author_link = tag.find('a')
            if not author_link:
                failed_indices.add(i)
                temp_data['authors'].append("未知作者")
            else:
                temp_data['authors'].append(author_link.text)

            spans_with_title = tag.find_all('span', attrs={'title': True})
            if spans_with_title:
                create_time = spans_with_title[0]['title']
            else:
                create_time = tag.find_all("span")[0].text
            if not create_time:
                failed_indices.add(i)
                temp_data['create_times'].append("1990-1-1 00:00")
            else:
                temp_data['create_times'].append(create_time)
        except Exception:
            failed_indices.add(i)
            temp_data['authors'].append("未知作者")
            temp_data['create_times'].append("1990-1-1 00:00")

    # 解析标题和更新时间
    for i, link in enumerate(links):
        try:
            title = re.sub(r'\[最后更新:.*]', '', link.text)
            update_time = _parse_update_time(link)
            tid = _parse_tid(link)
            
            if not tid:
                failed_indices.add(i)
                
            temp_data['titles'].append(title)
            temp_data['update_times'].append(update_time)
            temp_data['tids'].append(tid if tid else "0")
        except Exception:
            failed_indices.add(i)
            temp_data['titles'].append("解析失败")
            temp_data['update_times'].append("1990-1-1 00:00")
            temp_data['tids'].append("0")

    # 解析uid
    uid_tags = soup.findAll('a', attrs={'cs': '1'}, href=re.compile('uid'))
    if page_num == 1 and len(temp_data['tids']) < len(uid_tags):
        uid_tags.pop(0)
        
    for i in range(len(temp_data['tids'])):
        try:
            if i < len(uid_tags):
                uid = re.findall('(?<=uid[-=])([^\.]+)', uid_tags[i].attrs['href'])[0]
                temp_data['uids'].append(uid)
            else:
                failed_indices.add(i)
                temp_data['uids'].append("0")
        except Exception:
            failed_indices.add(i)
            temp_data['uids'].append("0")

    # 移除所有解析失败的数据
    valid_indices = [i for i in range(len(temp_data['tids'])) if i not in failed_indices]
    
    # 只添加成功解析的数据到page_data
    for i in valid_indices:
        url = f'https://www.jingjiniao.info/forum.php?mod=viewthread&tid={temp_data["tids"][i]}&page=1&authorid={temp_data["uids"][i]}'
        page_data.add_thread(
            tid=temp_data['tids'][i],
            link=url,
            comment=temp_data['comments'][i],
            view=temp_data['views'][i],
            author=temp_data['authors'][i],
            uid=temp_data['uids'][i],
            title=temp_data['titles'][i],
            update_time=temp_data['update_times'][i],
            create_time=temp_data['create_times'][i]
        )

    return page_data

def _parse_update_time(link):
    """解析更新时间"""
    span_tag = link.find('span')
    if span_tag is None:
        match = re.search(r'\[(最后更新|Last update):\s*(\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{1,2})\]', link.text)
        return match.group(2) if match else "1990-1-1 00:00"
    return span_tag.get('title')

def _parse_tid(link):
    """解析tid"""
    tid_list = re.findall('(?<=tid=)([^&]+)', link.attrs['href'])
    if tid_list:
        return tid_list[0]
    tid_list = re.findall("(?<=thread-)[0-9]+-", link.attrs['href'])
    if tid_list:
        return tid_list[0].replace("-", "")
    return None

if __name__ == '__main__':
    main_spider("中长篇", "https://www.jingjiniao.info/forum-85-1.html", False)
