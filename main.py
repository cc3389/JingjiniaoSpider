import concurrent.futures
from util import *
import forum


headers = load_json_from_file("headers.json")

hash_map = load_hashmap_from_file()


def block():
    block_link_dict = load_json_from_file("./blockList.json")
    if len(headers) == 0:
        print("请提供请求头")
        return
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = [executor.submit(forum.main_spider, headers, key, value, hash_map) for (key, value) in
                   block_link_dict.items()]
        concurrent.futures.wait(results)

        save_hashmap_to_file(hash_map)
        print("任务已完成")


if __name__ == '__main__':
    block()
