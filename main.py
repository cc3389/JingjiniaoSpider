import concurrent.futures

import forum

'''
这里提供请求头获取登录权限
'''
headers = {}


def block():
    block_link_dict = {"中长篇": "https://www.jingjiniao.info/forum-85-1.html",
                           "短篇新区": "https://www.jingjiniao.info/forum-97-1.html",
                           "翻译 同人作品区": "https://www.jingjiniao.info/forum-104-1.html",
                           "2022-荆棘鸟的涅槃": "https://www.jingjiniao.info/forum-112-1.html",
                           "2020-荆棘鸟的填坑计划": "https://www.jingjiniao.info/forum-108-1.html",
                           "重度区": "https://www.jingjiniao.info/forum-95-1.html",
                           "短篇老区": "https://www.jingjiniao.info/forum-69-1.html",
                           "2019-荆棘鸟的校园计划": "https://www.jingjiniao.info/forum-83-1.html"}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = [executor.submit(forum.main_spider, headers, key, value) for (key, value) in block_link_dict.items()]
        concurrent.futures.wait(results)


if __name__ == '__main__':
    block()
