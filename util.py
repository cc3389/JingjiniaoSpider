import csv
import logging
import re
import time
from io import BytesIO
from pathlib import Path
from typing import Dict, Any
import pickle
import json
import threading
from retrying import retry
import requests
import yaml
import os

def load_config(config_path: str = "config.yaml") -> dict:
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# 加载全局配置
CONFIG = load_config()
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

@retry_with_logging(
    retry_times=CONFIG['request']['retry_times'],
    wait_multiplier=CONFIG['request']['wait_multiplier'],
    wait_max=CONFIG['request']['wait_max']
)
def make_request(url: str) -> requests.Response:
    headers = FileHandler().load_json('headers.json')
    timeout = CONFIG['request']['timeout']
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response

# 定义一个互斥锁
map_lock = threading.Lock()
csv_lock = threading.Lock()

def extract_tid_from_url(url: str) -> str:
    """从URL中提取tid"""
    tid_match = re.search(r'tid=(\d+)', url)
    if tid_match:
        return tid_match.group(1)
    # 处理其他可能的URL格式
    tid_match = re.search(r'thread-(\d+)-', url)
    if tid_match:
        return tid_match.group(1)
    return None

def write_to_csv(titleList, authorList, commentList, viewList, block_name, update_timeList, urlList, filename,
                 recommend_list, favorite_list, create_timeList, word_counts):
    logging.info(f'开始写入 {block_name} 数据到 CSV 文件')
    
    # 准备新数据
    new_data = {}
    for i in range(len(titleList)):
        tid = extract_tid_from_url(urlList[i])
        if tid:
            new_data[tid] = [
                titleList[i], authorList[i], commentList[i], viewList[i],
                recommend_list[i], favorite_list[i], word_counts[i], block_name,
                create_timeList[i], update_timeList[i], urlList[i]
            ]
    
    with csv_lock:
        # 如果文件不存在,创建新文件
        if not Path(filename).exists():
            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['标题', '作者', '评论数', '浏览数', '点赞数', '收藏数', '字数', 
                               '板块', '发表时间', '更新时间', '链接'])
        
        # 更新CSV文件
        update_csv(new_data, filename)

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

# 预编译正则表达式以提高性能
CLEAN_TITLE_PATTERN = re.compile(r"\[最后更新.*?\]")
INVALID_CHAR_PATTERN = re.compile(r"[^\w ._]")

def clean_title(title):
    """
    清理标题中的无效字符
    """
    # 移除指定的模式
    title = CLEAN_TITLE_PATTERN.sub("", title)
    # 移除不需要的字符
    title = INVALID_CHAR_PATTERN.sub("", title).rstrip()
    return title

def update_csv(new_data: dict, filename: str):
    """
    更新CSV文件中的数据
    - 如果是新文章则追加
    - 如果是更新则覆盖原有行
    """
    temp_file = filename + '.tmp'
    is_updated = False
    
    # 读取现有数据,创建tid到行号的映射
    tid_to_row = {}
    with open(filename, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        headers = next(reader)  # 跳过表头
        for i, row in enumerate(reader):
            # 从链接中提取tid
            tid = re.findall(r'tid=(\d+)', row[10])[0] if row[10] else None
            if tid:
                tid_to_row[tid] = i + 1  # +1 因为跳过了表头
    
    # 创建临时文件
    with open(filename, 'r', encoding='utf-8-sig') as f_in, \
         open(temp_file, 'w', newline='', encoding='utf-8-sig') as f_out:
        reader = csv.reader(f_in)
        writer = csv.writer(f_out)
        
        # 写入表头
        headers = next(reader)
        writer.writerow(headers)
        
        # 复制现有数据到临时文件
        rows = list(reader)
        
        # 处理每个新数据
        for tid, data in new_data.items():
            if tid in tid_to_row:
                # 更新现有行
                row_num = tid_to_row[tid]
                rows[row_num-1] = data  # -1 因为rows从0开始
                is_updated = True
            else:
                # 添加新行
                rows.append(data)
                is_updated = True
        
        # 写入所有行
        writer.writerows(rows)
    
    # 如果有更新,替换原文件
    if is_updated:
        os.replace(temp_file, filename)
    else:
        os.remove(temp_file)

if __name__ == '__main__':
    title = clean_title('标题♥[]{}【】，：。！@#￥%……&*（）')
    print(title)