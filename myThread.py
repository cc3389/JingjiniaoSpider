import os.path
import re
from bs4 import BeautifulSoup
from decode import decode_base64_in_js
from util import *

def thread_spider(thread_url, block_name):
    """
    爬取具体的文章并存入文档中
    """
    title = ""
    recommend_num = 0
    favorite_num = 0
    page_num = 1
    try:
        while True:
            response = make_request(thread_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            # 判断是否出现错误提示
            if len(soup.select("#messagetext")) > 0:
                error_message = soup.select("#messagetext")[0].text + soup.select("#messagetext")[0].next_sibling.text
                raise Exception(error_message)
            # 获取标题
            elements = soup.select('#thread_subject')
            if page_num == 1:
                # 点赞数
                recommend_num = soup.find(id='recommendv_add').text
                # 收藏数
                favorite_num = soup.find(id='favoritenumber').text
                title = elements[0].text
            title = re.sub(r"\[最后更新.*?\]", "", title)
            title = title.replace("/", "").replace(":", "").replace("*", "").replace("?", "").replace(" ", "")
            title = title.replace("\\", "").replace("<", "").replace(">", "").replace("|", "")
            # if page_num == 1:
            # print("正在爬取 {} 板块的 {}".format(block_name, title))
            # print("正在爬取第" + str(page_num) + "页")

            # 选择class=t_f的tags
            t_f = soup.select(".t_f div")
            # js脚本拼成的base64串，实际为文章第一个回复
            if len(soup.select(".t_f script")) == 2:
                base64_js_str = soup.select(".t_f script")[1].text
                wmsj_enmessage_str = decode_base64_in_js(base64_js_str)
                wmsj_enmessageTag = BeautifulSoup(wmsj_enmessage_str, 'html.parser')
                t_f.insert(0, wmsj_enmessageTag)
            for tags in t_f:
                for tag in tags.find_all(style='display:none') + tags.find_all(class_='jammer') \
                           + tags.find_all(['br', 'img', 'a', 'i']) + tags.find_all('div', class_='quote'):
                    tag.decompose()
            # 存入文件中
            fileDir = os.path.abspath("./小说输出/" + block_name)
            valid_title = "".join(c for c in title if c.isalnum() or c in (' ', '.', '_')).rstrip()
            filePath = os.path.join(fileDir, valid_title + ".txt")
            if not os.path.exists(fileDir):
                os.makedirs(fileDir, exist_ok=True)
            if page_num == 1:
                try:
                    if os.path.exists(filePath):  # 判断文件是否存在
                        os.remove(filePath)  # 删除文件
                        print(f"文件 {filePath} 删除成功！")
                except Exception as e:
                    error_message = str(e)
                    if "[WinError 32]" in error_message:
                        # active_threads = threading.enumerate()
                        # print(f"Current active threads: {[t.name for t in active_threads]}")
                        # 翻页时遇到两个相同的文章链接
                        return recommend_num, favorite_num
                    else:
                        print(f"删除文件 {filePath} 失败: {e}")
            temp_text = ''
            for tags in t_f:
                for tag in tags:
                    # 过滤无关的脚本标签
                    if 'script' == tag.name:
                        continue
                    temp_text += tag.text
            with open(filePath, "a", encoding='utf-8') as f:
                f.write(temp_text)
            # 找到下一页
            nextLinkTag = soup.select('.nxt')
            if nextLinkTag:
                nextLinkStr = nextLinkTag[0].attrs['href']
                thread_url = nextLinkStr
                page_num = page_num + 1
            else:
                # print(title+"爬取完成")
                break
    except Exception as e:
        print(f'爬取 {thread_url}失败。原因： {e}')
        return recommend_num, favorite_num
    return recommend_num, favorite_num


if __name__ == '__main__':
    # 主题的地址
    thread_spider('https://www.jingjiniao.info/forum.php?mod=viewthread&tid=37419&page=1&authorid=8988', 'test')
