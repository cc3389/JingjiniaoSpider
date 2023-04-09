import os.path
import re

from bs4 import BeautifulSoup
import requests
from util import load_json_from_file

headers = load_json_from_file("headers.json")

'''
爬取具体的文章并存入文档中
'''


def thread_spider(thread_url, headers, block_name):
    page_num = 1
    print("爬取的文章url为：\n" + thread_url)
    while True:
        response = requests.get(thread_url, headers=headers)
        print(response.status_code)
        print("正在爬取第" + str(page_num) + "页")
        soup = BeautifulSoup(response.text, 'html.parser')
        # 获取标题
        elements = soup.select('#thread_subject')
        if elements:
            title = elements[0].text
        else:
            title = soup.find('title').text
            print("出错了！\n", )
        title = re.sub(r"\[最后更新.*?\]", "", title)
        title = title.replace("/", "").replace(":", "").replace("*", "").replace("?", "").replace(" ", "")
        title = title.replace("\\", "").replace("<", "").replace(">", "").replace("|", "")
        if page_num == 1:
            print(title)
        # 选择class=t_f的tags
        t_f = soup.select(".t_f div")
        for tags in t_f:
            for tag in tags.find_all(style='display:none') + tags.find_all(class_='jammer') \
                       + tags.find_all(['br', 'img', 'a', 'i']) + tags.find_all('div', class_='quote'):
                tag.decompose()
        # 存入文件中
        fileDir = os.path.abspath("./小说输出/" + block_name)
        filePath = os.path.join(fileDir, title + ".txt")
        if not os.path.exists(fileDir):
            os.makedirs(fileDir)
        if page_num == 1:
            if os.path.exists(filePath):  # 判断文件是否存在
                os.remove(filePath)  # 删除文件
                print(f"文件 {filePath} 删除成功！")
        for tags in t_f:
            for tag in tags:
                with open(filePath, "a", encoding='utf-8') as f:
                    f.write(tag.text)
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
