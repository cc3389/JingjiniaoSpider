import os.path
import re

from bs4 import BeautifulSoup
import requests


headers = {}


'''
爬取具体的文章并存入文档中
'''
def thread_spider(thread_url, headers, block_name):
    page_num = 1
    print("爬取的文章url为：\n"+thread_url)
    while(True):
        response = requests.get(thread_url, headers=headers)
        print(response.status_code)
        print("正在爬取第"+str(page_num)+"页")
        soup = BeautifulSoup(response.text, 'html.parser')
        # 获取标题
        elements = soup.select('#thread_subject')
        if elements:
            title = elements[0].text
        else:
            title = soup.find('title').text
            print("出错了！\n")
        title = re.sub(r"\[最后更新.*?\]", "", title)
        title = title.replace("/", "").replace(":", "").replace("*", "").replace("?", "").replace(" ","")
        title = title.replace("\\", "").replace("<", "").replace(">", "").replace("|", "")
        if page_num == 1:
            print(title)
        # 选择class=t_f的tags
        t_f = soup.select(".t_f div")
        for tags in t_f:
            for tag in tags.find_all(style='display:none') + tags.find_all(class_='jammer') \
                       + tags.find_all(['br', 'img', 'a',  'i']) + tags.find_all('div', class_='quote'):
                tag.decompose()
        # 存入文件中
        if not os.path.exists("./" + block_name):
            os.mkdir(".\\" + block_name)
        for tags in t_f:
            for tag in tags:
                file = open(".\\"+block_name+"\\" + title + ".txt", "a", encoding='utf-8')
                file.write(tag.text)
        # 找到下一页
        nextLinkTag = soup.select('.nxt')
        if nextLinkTag:
            nextLinkStr = nextLinkTag[0].attrs['href']
            thread_url = nextLinkStr
            page_num = page_num + 1
        else:
            print("爬取完成")
            break
if __name__ == '__main__':
    # 主题的地址
    thread_spider('https://www.jingjiniao.info/thread-43826-1-1.html', headers)
