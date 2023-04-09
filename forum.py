import requests
from bs4 import BeautifulSoup
import re
import concurrent.futures
import thread
from util import *

'''
爬取板块的所有帖子链接
'''


# 定义主函数main_spider，传入请求头headers，板块名称block_name和板块链接block_url
def main_spider(headers, block_name, block_url, hash_map):
    base_url = block_url
    page_num = 1
    last_page_num = "999"
    linkList = []
    while True:
        if page_num > int(last_page_num):
            break
        response = requests.get(base_url, headers=headers)
        print(response.status_code)
        soup = BeautifulSoup(response.text, 'html.parser')
        # 获取本页中的所有文章链接
        links = soup.select('.s.xst')
        uidLinkTags = soup.findAll('a', attrs={'cs': '1'}, href=re.compile('uid'))
        if page_num == 1:
            uidLinkTags.pop(0)
            last_page_tag = soup.find("span", title=re.compile("共 [0-9]+ 页"))
            last_page_num = last_page_tag.text.replace(" ", "").replace("/", "").replace("页", "")
        print("正在爬取" + block_name + "板块第" + str(page_num) + "页", "/共", last_page_num, "页")
        tidList = []
        uidList = []
        update_timeList = []
        # print()
        for link in links:
            # print(type(link))
            span_tag = link.find('span')
            if span_tag is None:
                update_time = "1990-1-1 00:00"
            else:
                update_time = span_tag.get('title')
            update_timeList.append(update_time)
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
        for uidLinkTag in uidLinkTags:
            # uidLink = uidLinkTag.attrs.get('href')
            uid = re.findall('(?<=uid-)([^\.]+)', uidLinkTag.attrs['href'])[0]
            uidList.append(uid)
        for uid, tid, update_time in zip(uidList, tidList, update_timeList):
            if tid is None:
                continue
            if tid not in hash_map or compare_time_str(hash_map[tid], update_time):
                linkList.append(
                    'https://www.jingjiniao.info/forum.php?mod=viewthread&tid=' + tid + '&page=1&authorid=' + uid)
                hash_map[tid] = update_time
        # 找到下一页
        nextLinkTag = soup.select('.nxt')
        if nextLinkTag:
            nextLinkStr = nextLinkTag[0].attrs['href']
            base_url = nextLinkStr
            page_num = page_num + 1
        else:
            break
    print("开始爬取{}板块第{}页的文章".format(block_name, page_num - 1))
    # 多线程遍历爬取文章
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = [executor.submit(thread.thread_spider, link, headers, block_name) for link in linkList]
        concurrent.futures.wait(results)


if __name__ == '__main__':
    # json格式的请求头
    headers = load_json_from_file("./headers.json")
    hash_map = load_hashmap_from_file()
    main_spider(headers, "新生投票区", "https://www.jingjiniao.info/forum-102-1.html", hash_map)
