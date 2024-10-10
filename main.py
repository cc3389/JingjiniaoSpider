import concurrent.futures
from util import *
from forum import main_spider

hash_map = load_hashmap_from_file()


def block():
    block_link_dict = load_json_from_file("./blockList.json")
    if os.path.exists("./data.csv"):  # 判断文件是否存在
        os.remove("./data.csv")
        print("已删除data.csv")
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = [executor.submit(main_spider, key, value, hash_map) for (key, value) in
                   block_link_dict.items()]
        concurrent.futures.wait(results)
        print("==========================================================")
        print("任务已完成")
        # 增量有问题，先注释掉
        # print("任务已完成,正在将索引写入文件...")
        # save_hashmap_to_file(hash_map)
        # print("写入完成")

if __name__ == '__main__':
    block()



