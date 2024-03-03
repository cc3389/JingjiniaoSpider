import os.path
import re

from bs4 import BeautifulSoup
from util import *


def thread_spider(thread_url, block_name):
    """
    爬取具体的文章并存入文档中
    """
    recommend_num = 0
    favorite_num = 0
    page_num = 1
    while True:
        response = make_request(thread_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        # 获取标题
        elements = soup.select('#thread_subject')
        if page_num == 1:
            # 点赞数
            recommend_num = soup.select('#recommendv_add')[0].text
            # 收藏数
            favorite_num = soup.select('#favoritenumber')[0].text
        if elements:
            title = elements[0].text
        else:
            print("出错了！链接为：", thread_url + "\n")
            with open('log.txt', 'a', encoding='utf-8') as f1:
                f1.write(response.status_code + "\n" + response.text + "\n\n" +
                         "------------------------------------------------------" + "\n\n")
            with open("错误链接.txt", "a", encoding='utf-8') as f2:
                f2.write(thread_url + "\n")
            break
        title = re.sub(r"\[最后更新.*?\]", "", title)
        title = title.replace("/", "").replace(":", "").replace("*", "").replace("?", "").replace(" ", "")
        title = title.replace("\\", "").replace("<", "").replace(">", "").replace("|", "")
        if page_num == 1:
            print("正在爬取 {} 板块的 {}".format(block_name, title))
        # print("正在爬取第" + str(page_num) + "页")
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
                # print(f"文件 {filePath} 删除成功！")
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
            print(title+"爬取完成")
            break
    return recommend_num, favorite_num


if __name__ == '__main__':
    # 主题的地址
    thread_spider('https://www.jingjiniao.info/thread-43826-1-1.html')
