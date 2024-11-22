import concurrent.futures

import analyze_post_trends
from analysis import analyze_post_quality
from forum import main_spider
from util import *

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def process_blocks(block_dict: Dict[str, str], download_images: bool = False) -> None:
    """处理区块数据的主函数"""
    data_file = Path("./data.csv")
    last_crawled_data = {}

    # 读取已爬取的数据
    if data_file.exists():
        with open(data_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 从链接中提取tid
                tid = extract_tid_from_url(row['链接'])
                if tid:
                    last_crawled_data[tid] = row['更新时间']

    try:
        thread_pool_size = CONFIG['spider']['thread_pool_size']
        with concurrent.futures.ThreadPoolExecutor(max_workers=thread_pool_size) as executor:
            futures = {
                executor.submit(main_spider, key, value, download_images, last_crawled_data): key
                for key, value in block_dict.items()
            }

            for future in concurrent.futures.as_completed(futures):
                block_key = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"处理区块 {block_key} 时发生错误: {str(e)}")

        logging.info("所有区块处理完成")
        # 依次执行所有分析函数
        analyze_post_quality(data_file)
        analyze_post_trends.analyze_post_trends(data_file)

    except Exception as e:
        logging.error(f"执行过程中发生错误: {str(e)}")
        raise

def main():
    try:
        config = CONFIG['spider']
        blocks = CONFIG['blocks']
        process_blocks(blocks, config['download_images'])
    except Exception as e:
        logging.error(f"程序执行失败: {str(e)}")
        raise

if __name__ == '__main__':
    main()



