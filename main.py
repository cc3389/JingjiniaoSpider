import concurrent.futures
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
    if data_file.exists():
        data_file.unlink()
        logging.info("已删除旧的 data.csv 文件")
    
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(main_spider, key, value, download_images): key 
                for key, value in block_dict.items()
            }
            
            for future in concurrent.futures.as_completed(futures):
                block_key = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"处理区块 {block_key} 时发生错误: {str(e)}")
                    
        logging.info("所有区块处理完成")
        
    except Exception as e:
        logging.error(f"执行过程中发生错误: {str(e)}")
        raise

def main(download_images: bool = False):
    try:
        file_handler = FileHandler()
        block_dict = file_handler.load_json("./blockList.json")
        process_blocks(block_dict, download_images)
    except Exception as e:
        logging.error(f"程序执行失败: {str(e)}")
        raise

if __name__ == '__main__':
    download_images = False
    main(download_images)



