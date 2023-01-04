import concurrent.futures

from bs4 import BeautifulSoup
import requests
import re
import thread

'''
爬取板块的所有帖子链接
'''
def main_spider(headers,block_name,block_url):

    base_url = block_url
    page_num = 1
    last_page_num = "999"
    linkList = []
    print("正在爬取文章链接")
    while (True):
        if page_num > int(last_page_num):
            break
        response = requests.get(base_url, headers=headers)
        # headers = response.headers
        print(response.status_code)
        soup = BeautifulSoup(response.text, 'html.parser')
        # 获取本页中的所有文章链接
        links = soup.select('.s.xst')
        uidLinkTags = soup.findAll('a', attrs={'cs': '1'}, href=re.compile('uid'))
        if page_num == 1:
            uidLinkTags.pop(0)
            last_page_tag = soup.find("span",title=re.compile("共 [0-9]+ 页"))
            last_page_num = last_page_tag.text.replace(" ","").replace("/","").replace("页","")
        print("正在爬取板块第" + str(page_num) + "页", "/共", last_page_num, "页")
        tidList = []
        uidList = []
        print(links)
        for link in links:
            tid_list = re.findall('(?<=tid=)([^&]+)', link.attrs['href'])
            if tid_list:
                tid = tid_list[0]
            else:
                tid_list = re.findall("(?<=thread-)[0-9]+-",link.attrs['href'])
                if tid_list:
                    tid = (tid_list[0]).replace("-","")
                else:
                    tid = None
            tidList.append(tid)
        for uidLinkTag in uidLinkTags:
            # uidLink = uidLinkTag.attrs.get('href')
            uid = re.findall('(?<=uid-)([^\.]+)', uidLinkTag.attrs['href'])[0]
            uidList.append(uid)
        for uid, tid in zip(uidList, tidList):
            if tid is None:
                continue
            linkList.append(
                'https://www.jingjiniao.info/forum.php?mod=viewthread&tid=' + tid + '&page=1&authorid=' + uid)
        # 找到下一页
        nextLinkTag = soup.select('.nxt')
        if nextLinkTag:
            nextLinkStr = nextLinkTag[0].attrs['href']
            base_url = nextLinkStr
            page_num = page_num + 1
        else:
            break
    print("正在多线程爬取文章")
    print(linkList)
    # 多线程遍历爬取文章
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = [executor.submit(thread.thread_spider, link, headers, block_name) for link in linkList]
        concurrent.futures.wait(results)

if __name__ == '__main__':
    # json格式的请求头
    header = {}
    main_spider(header)


