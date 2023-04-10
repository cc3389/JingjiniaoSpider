import csv
import pickle
import json
import os
import threading
from datetime import datetime
from retrying import retry
import requests

HashMap_file_path = "./tidHashMap.dat"


@retry(wait_fixed=2000, stop_max_attempt_number=3)
def make_request(base_url):
    headers = load_json_from_file('headers.json')
    response = requests.get(base_url, headers=headers)
    response.raise_for_status()
    return response


def compare_time_str(time_str1, time_str2):
    """
    比较格式为"%Y-%m-%d %H:%M"的时间字符串，如果返回True，则说明time_str1比time_str2早
    """
    time_obj1 = datetime.strptime(time_str1, "%Y-%m-%d %H:%M")
    time_obj2 = datetime.strptime(time_str2, "%Y-%m-%d %H:%M")
    return time_obj1 < time_obj2


# 定义一个互斥锁
map_lock = threading.Lock()


# 定义一个更新哈希表的函数，该函数是线程安全的
def update_hash_map(tid, update_time, hash_map):
    with map_lock:
        hash_map[tid] = update_time


csv_lock = threading.Lock()


def write_to_csv(titleList, authorList, commentList, viewList, block_name, update_timeList, urlList, filename):
    with csv_lock:
        with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            # 如果文件为空，写入表头
            if csvfile.tell() == 0:
                writer.writerow(['标题', '作者', '评论数', '浏览数', '板块', '更新时间', '链接'])
            # 写入数据
            for i in range(len(commentList)):
                writer.writerow([titleList[i], authorList[i], commentList[i],
                                 viewList[i], block_name, update_timeList[i],urlList[i]])


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
    with open(file_path, "r", encoding="utf-8") as file:
        try:
            json_data = file.read()
            python_obj = json.loads(json_data)
        except json.JSONDecodeError as e:
            print('文件内容不是合法的 JSON 格式，错误信息：', e)
        except Exception as e:
            print('发生了未知错误，错误信息：', e)

    return python_obj
