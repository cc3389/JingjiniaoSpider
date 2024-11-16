import csv
import logging
import time
from io import BytesIO
from pathlib import Path
from typing import Dict, Any
import pickle
import json
import threading
from datetime import datetime
from retrying import retry
import requests

class FileHandler:
    def __init__(self):
        self.hashmap_path = Path("./tidHashMap.dat")
        self.csv_lock = threading.Lock()
        self.map_lock = threading.Lock()

    def save_hashmap(self, hashmap: Dict) -> None:
        try:
            with self.hashmap_path.open("wb") as f:
                pickle.dump(hashmap, f)
        except Exception as e:
            logging.error(f"保存哈希映射失败: {str(e)}")
            raise

    def load_hashmap(self) -> Dict:
        if not self.hashmap_path.exists():
            return {}
        try:
            with self.hashmap_path.open("rb") as f:
                return pickle.load(f)
        except Exception as e:
            logging.error(f"加载哈希映射失败: {str(e)}")
            raise

    def load_json(self, file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logging.error(f"JSON解析错误: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"读取JSON文件失败: {str(e)}")
            raise


def retry_with_logging(retry_times=3, wait_multiplier=1000, wait_max=10000):
    def decorator(func):
        @retry(
            stop_max_attempt_number=retry_times,
            wait_exponential_multiplier=wait_multiplier,
            wait_exponential_max=wait_max,
            retry_on_exception=lambda e: isinstance(e, (requests.Timeout, requests.ConnectionError, requests.RequestException))
        )
        def wrapper(*args, **kwargs):
            if not hasattr(wrapper, '_retry_count'):
                wrapper._retry_count = {}
            
            thread_id = threading.get_ident()
            if thread_id not in wrapper._retry_count:
                wrapper._retry_count[thread_id] = 0
            
            try:
                wrapper._retry_count[thread_id] += 1
                current_attempt = wrapper._retry_count[thread_id]
                
                # 获取URL参数（假设它是第一个参数）
                url = args[0] if args else kwargs.get('url', 'unknown_url')
                startTime = time.time()
                result = func(*args, **kwargs)
                # print(f'第 {current_attempt} 次请求成功，耗时: {time.time() - startTime:.2f}秒。')
                wrapper._retry_count[thread_id] = 0
                return result
            except Exception as e:
                if current_attempt >= retry_times:
                    print(f"已达到最大重试次数，放弃请求: {url}")
                    wrapper._retry_count[thread_id] = 0
                raise
        return wrapper
    return decorator

@retry_with_logging(retry_times=3, wait_multiplier=1000, wait_max=10000)
def make_request(url: str) -> requests.Response:
    headers = FileHandler().load_json('headers.json')
    response = requests.get(url, headers=headers, timeout=5)
    response.raise_for_status()
    return response

# 定义一个互斥锁
map_lock = threading.Lock()
csv_lock = threading.Lock()


def write_to_csv(titleList, authorList, commentList, viewList, block_name, update_timeList, urlList, filename,
                 recommend_list, favorite_list, create_timeList):
    logging.info(f'开始写入 {block_name} 数据到 CSV 文件')
    with csv_lock:
        with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            # 如果文件为空，写入表头
            if csvfile.tell() == 0:
                writer.writerow(
                    ['标题', '作者', '评论数', '浏览数', '点赞数', '收藏数', '板块',
                     '发表时间', '更新时间', '链接'])
            # 写入数据
            for i in range(len(commentList)):
                writer.writerow([titleList[i], authorList[i], commentList[i],
                               viewList[i], recommend_list[i], favorite_list[i], block_name,
                               create_timeList[i], update_timeList[i], urlList[i]])

def download_image(img_url):
    """
    下载图片并返回图片流
    """
    try:
        start_time = time.time()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.34',
            'Referer': 'https://www.jingjiniao.info/'
        }
        img_data = requests.get(img_url, headers=headers, timeout=20).content
        end_time = time.time()
        logging.info(f'下载图片 {img_url} 耗时: {end_time - start_time:.2f}秒')
        return BytesIO(img_data)  # 返回图片流
    except:
        logging.error(f'图片 {img_url} 下载失败')
        return None