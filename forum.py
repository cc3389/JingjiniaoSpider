from bs4 import BeautifulSoup
import re
import concurrent.futures
from thread import thread_spider
from util import *

'''
爬取板块的所有帖子链接
'''


# 定义主函数main_spider，传入请求头headers，板块名称block_name和板块链接block_url
def main_spider(block_name, block_url, hash_map):
    base_url = block_url
    page_num = 1
    last_page_num = "999"
    total_linkList = []
    # 评论数列表
    total_commentList = []
    # 浏览数列表
    total_viewList = []
    # 作者名列表
    total_authorList = []
    # tid列表
    total_tidList = []
    # uid列表
    total_uidList = []
    # 标题列表
    total_titleList = []
    # 更新时间列表
    total_update_timeList = []
    # 点赞列表
    recommend_list = []
    # 收藏列表
    favorite_list = []
    future_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        while True:
            linkList = []
            # 评论数列表
            commentList = []
            # 浏览数列表
            viewList = []
            # 作者名列表
            authorList = []
            # tid列表
            tidList = []
            # uid列表
            uidList = []
            # 标题列表
            titleList = []
            # 更新时间列表
            update_timeList = []
            if page_num > int(last_page_num):
                break
            response = make_request(base_url)
            soup = BeautifulSoup(response.text, 'html.parser')

            # 获取本页中的所有文章链接
            links = soup.select('.s.xst')
            commentTags = soup.select(".acgifnums")

            # 获取评论数和浏览数
            for comment in commentTags:
                a_tag = comment.find('a', class_="xi2")
                commentList.append(a_tag.text)
                viewTag = comment.find("span")
                viewList.append(viewTag.text)

            # 获取作者列表
            author_divs = soup.find_all('div', class_='acgifby1')
            for tag in author_divs:
                for link in tag.find_all('a'):
                    authorList.append(link.text)
            if len(links) == 0:
                print("找不到链接，可能是cookie有误或过期了")
            for link in links:
                # 获取标题
                titleList.append(re.sub(r'\[最后更新:.*]', '', link.text))
                # 获取更新时间
                span_tag = link.find('span')
                if span_tag is None:
                    # 更新时间在标题中
                    match = re.search(r'\[(最后更新|Last update):\s*(\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{1,2})\]', link.text)
                    if match:
                        time_str = match.group(2)
                        update_time = time_str
                    else:
                        update_time = "1990-1-1 00:00"
                else:
                    update_time = span_tag.get('title')
                update_timeList.append(update_time)

                # 获取tid
                tid_list = re.findall('(?<=tid=)([^&]+)', link.attrs['href'])
                if tid_list:
                    tid = tid_list[0]
                else:
                    tid_list = re.findall("(?<=thread-)[0-9]+-", link.attrs['href'])
                    if tid_list:
                        tid = (tid_list[0]).replace("-", "")
                    else:
                        tid = None
                tidList.append(tid)
            uidLinkTags = soup.findAll('a', attrs={'cs': '1'}, href=re.compile('uid'))
            if page_num == 1:
                # 去除 admin
                if len(tidList) < len(uidLinkTags):
                    authorList.pop(0)
                    uidLinkTags.pop(0)
                last_page_tag = soup.find("span", title=re.compile("共 [0-9]+ 页"))
                last_page_num = last_page_tag.text.replace(" ", "").replace("/", "").replace("页", "")
            print("正在爬取" + block_name + "板块第" + str(page_num) + "页", "/共", last_page_num, "页")
            # 获取uid
            for uidLinkTag in uidLinkTags:
                uid = re.findall('(?<=uid-)([^\.]+)', uidLinkTag.attrs['href'])[0]
                uidList.append(uid)
            temp_urlList = []
            # 获取文章链接列表
            for uid, tid, update_time in zip(uidList, tidList, update_timeList):
                if tid is None:
                    continue
                url = 'https://www.jingjiniao.info/forum.php?mod=viewthread&tid=' + tid + '&page=1&authorid=' + uid
                temp_urlList.append(url)
                if tid not in hash_map or compare_time_str(hash_map[tid], update_time):
                    linkList.append(url)
                    hash_map[tid] = update_time
            print("{}的第{}页需要更新{}篇".format(block_name, page_num, len(linkList)))
            for link in linkList:
                future = executor.submit(thread_spider, link, block_name)
                future_list.append(future)
            total_tidList.extend(tidList)
            total_viewList.extend(viewList)
            total_uidList.extend(uidList)
            total_titleList.extend(titleList)
            total_authorList.extend(authorList)
            total_update_timeList.extend(update_timeList)
            total_commentList.extend(commentList)
            total_linkList.extend(temp_urlList)
            # 找到下一页
            nextLinkTag = soup.select('.nxt')
            if nextLinkTag:
                nextLinkStr = nextLinkTag[0].attrs['href']
                base_url = nextLinkStr
                page_num = page_num + 1
            else:
                break
    # 迭代future对象，按完成顺序获取结果
    for future in future_list:
        try:
            recommend_num, favorite_num = future.result()
            recommend_list.append(recommend_num)
            favorite_list.append(favorite_num)
        except Exception as e:
            print(f'Error fetching data for URL {url}: {e}')
    # 加锁用csv保存数据
    try:
        write_to_csv(total_titleList, total_authorList, total_commentList,
                     total_viewList, block_name, total_update_timeList, total_linkList, "data.csv", recommend_list, favorite_list)
    except Exception as e:
        print('发生了未知错误，错误信息：', e)


if __name__ == '__main__':
    hash_map = {}
    main_spider("中长篇", "https://www.jingjiniao.info/forum-85-1.html", hash_map)
