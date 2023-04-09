import pickle
import json
import os
import threading
from datetime import datetime

HashMap_file_path = "./tidHashMap"


def compare_time_str(time_str1, time_str2):
    """
    比较格式为"%Y-%m-%d %H:%M"的时间字符串，如果返回True，则说明time_str1比time_str2早
    """
    time_obj1 = datetime.strptime(time_str1, "%Y-%m-%d %H:%M")
    time_obj2 = datetime.strptime(time_str2, "%Y-%m-%d %H:%M")
    return time_obj1 < time_obj2


# 定义一个互斥锁
lock = threading.Lock()


# 定义一个更新哈希表的函数，该函数是线程安全的
def update_hash_map(tid, update_time, hash_map):
    with lock:
        hash_map[tid] = update_time


def save_hashmap_to_file(hashmap):
    """
    将HashMap保存到文件中
    """
    with open(HashMap_file_path, "wb") as file:
        pickle.dump(hashmap, file)


def load_hashmap_from_file():
    """
    从文件中加载HashMap
    """
    if not os.path.isfile(HashMap_file_path):
        # Create a new file if it does not exist
        with open(HashMap_file_path, "wb") as file:
            hashmap = {}
            pickle.dump(hashmap, file)
    else:
        with open(HashMap_file_path, "rb") as file:
            hashmap = pickle.load(file)
    return hashmap


def load_json_from_file(file_path):
    """
    从文件中加载JSON数据并返回Python对象
    """
    with open(file_path, "r", encoding='utf-8') as file:
        json_data = file.read()
        python_obj = json.loads(json_data)
    return python_obj
