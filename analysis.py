import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
import logging
import numpy as np
import traceback

from analyze_author import analyze_author
from analyze_post_trends import analyze_post_trends
from util import clean_title, normalize

plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置中文字体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

def analyze_post_quality(csv_path: str = "data.csv", output_dir='分析报告') -> None:
    """分析近期文章并生成报表"""
    logging.info("开始分析近期文章")


    
    # 将 output_dir 转换为 Path 对象
    output_dir = Path(output_dir)
    
    # 确保输出目录存在
    output_dir.mkdir(exist_ok=True)
    
    # 读取CSV文件
    df = pd.read_csv(csv_path)
    
    # 确保数值列为数值类型
    df['浏览数'] = pd.to_numeric(df['浏览数'], errors='coerce')
    df['点赞数'] = pd.to_numeric(df['点赞数'], errors='coerce')
    df['收藏数'] = pd.to_numeric(df['收藏数'], errors='coerce')
    df['字数'] = pd.to_numeric(df['字数'], errors='coerce')
    
    # 将NaN值替换为0
    df[['浏览数', '点赞数', '收藏数']] = df[['浏览数', '点赞数', '收藏数']].fillna(0)
    
    # 清理标题
    df['标题'] = df['标题'].apply(clean_title)
    
    # 过滤数据
    df = df[
        (df['作者'] != 'Admin_荆棘鸟') &  # 过滤管理员文章
        (df['字数'] > 0)  # 过滤字数为0的文章
    ]
    
    # 数据预处理
    df['浏览数'] = df['浏览数'].astype(int)
    df['点赞数'] = df['点赞数'].astype(int)
    df['收藏数'] = df['收藏数'].astype(int)
    
    # 设置字数阈值和权重计算参数
    MIN_WORDS = 5000      # 最低字数要求
    BASE_WORDS = 15000    # 基准字数
    TARGET_WORDS = 30000  # 目标字数
    
    # 计算字数权重（强化高字数的权重）
    def calculate_word_weight(words):
        if words < MIN_WORDS:  # 5000
            return 0.75
        elif words < BASE_WORDS:  # 15000
            ratio = (words - MIN_WORDS) / (BASE_WORDS - MIN_WORDS)
            return 0.75 + (0.25 * ratio)
        elif words < TARGET_WORDS:  # 30000
            ratio = (words - BASE_WORDS) / (TARGET_WORDS - BASE_WORDS)
            return 1.0 + (0.15 * ratio)
        else:
            # 更严格的对数衰减
            base_score = 1.15
            if words > 50000:  # 对超长文章施加额外惩罚
                penalty = min(0.25, (words - 50000) / 100000 * 0.25)
                base_score -= penalty
            return max(0.9, base_score)  # 设置最低限制
    
    # 应用字数权重
    df['字数权重'] = df['字数'].apply(calculate_word_weight)
    
    # 1. 计算基础互动率
    df['互动率'] = (df['点赞数'] + df['收藏数']) / df['浏览数']
    
    # 2. 修改字数权重计算方式，对短文章施加惩罚
    df['字数权重'] = df['字数'].apply(lambda x: min(1.0, (x / MIN_WORDS) ** 0.5))
    
    # 3. 标准化各个指标
    df['浏览数_标准化'] = normalize(df['浏览数'])
    df['互动率_标准化'] = normalize(df['互动率'])
    
    # 修改评分算法部分
    # 1. 对浏览数进行对数转换，减少极值影响
    df['浏览数_对数'] = np.log1p(df['浏览数'])  # log1p 避免 log(0)
    
    # 2. 重新定义互动率计算
    df['互动率'] = (df['点赞数'] + df['收藏数']) / df['浏览数'].clip(lower=1)
    
    # 3. 设置最小阈值，防止过度奖励低浏览量文章
    MIN_VIEWS = 100  # 最小浏览量阈值
    df['浏览量权重'] = df['浏览数'].apply(lambda x: min(1.0, (x / MIN_VIEWS) ** 0.5))
    
    # 3. 重新计算互动质量分
    df['互动质量'] = (df['收藏数'] * 2 + df['点赞数'] + df['评论数']) / (df['浏览数'] + 10000)
    df['互动质量_标准化'] = normalize(df['互动质量'])
    
    # 2. 计算互动密度（考虑字数的互动频率）
    WORD_SEGMENT = 1000  # 每1000字为一个段
    df['段落数'] = (df['字数'] / WORD_SEGMENT).clip(lower=1)
    df['互动密度'] = (df['点赞数'] + df['收藏数']) / df['段落数']
    
    # 确保互动密度列存在
    if '互动密度' not in df.columns:
        df['互动密度'] = 0  # 如果没有计算出互动密度，初始化为0

    # 标准化互动密度
    df['互动密度_标准化'] = normalize(df['互动密度'])
    
    # 1. 增加评论数的处理
    df['评论数'] = pd.to_numeric(df['评论数'], errors='coerce').fillna(0)
    
    # 2. 增加时间因素的考虑
    df['发表时间'] = pd.to_datetime(df['发表时间'])
    df['更新时间'] = pd.to_datetime(df['更新时间'])
    current_time = datetime.now()
    
    # 计算发布和更新以来的天数
    df['发布时长'] = (current_time - df['发表时间']).dt.total_seconds() / (24 * 3600)
    df['更新时长'] = (current_time - df['更新时间']).dt.total_seconds() / (24 * 3600)
    
    # 优化日均浏览计算
    SMOOTHING_FACTOR = 7  # 平滑因子，用于减少极端值的影响
    MIN_DAYS = 3  # 最小考察天数，避免新文章数据失真
    MAX_DAYS = 720  # 最大考察天数，避免过老文章的数据失真
    
    # 计算有效统计天数
    df['有效统计天数'] = df['发布时长'].clip(lower=MIN_DAYS, upper=MAX_DAYS)
    
    # 使用平滑处理计算日均浏览
    df['日均浏览'] = (
        df['浏览数'] / (df['有效统计天数'] + SMOOTHING_FACTOR)
    ).round(1)
    
    # 标准化日均浏览
    df['日均浏览_标准化'] = normalize(df['日均浏览'])
    
    # 进一步优化时间权重参数
    MAX_TIME_WEIGHT = 1.35    # 从1.40降低到1.35
    MIN_TIME_WEIGHT = 0.65    # 从0.60提高到0.65
    DECAY_DAYS = 45          # 从40增加到45
    DECAY_RATE = 0.035      # 从0.04降低到0.035
    
    df['时间权重'] = df['发布时长'].apply(
        lambda x: MAX_TIME_WEIGHT if x <= DECAY_DAYS else 
        max(MIN_TIME_WEIGHT, MAX_TIME_WEIGHT * np.exp(-DECAY_RATE * (x - DECAY_DAYS)))
    )
    
    # 修改浏览量惩罚机制，增加区分度
    def calculate_view_penalty(views):
        if views >= 20000:          # 从18000提高到20000
            return 1.0
        elif views >= 7000:         # 从6000提高到7000
            ratio = (views - 7000) / (13000)
            return 0.85 + (0.15 * ratio)
        else:
            return max(0.75, 0.85 * (views / 7000))
    
    # 修改评分计算部分
    df['浏览量惩罚'] = df['浏览数'].apply(calculate_view_penalty)
    
    # 2. 为中等长度文章添加奖励
    def calculate_length_bonus(words):
        if 15000 <= words <= 50000:
            center = 32500
            distance = abs(words - center)
            max_distance = 17500
            bonus = 0.12 * (1 - distance / max_distance)  # 从0.15降低到0.12
            return 1 + bonus
        return 1.0

    # 在综合评分中应用长度奖励
    df['长度奖励'] = df['字数'].apply(calculate_length_bonus)
    
    # 计算点赞-收藏差异指标
    df['点赞收藏比'] = df['点赞数'] / df['收藏数'].clip(lower=1)
    df['点赞收藏差'] = df['点赞数'] - df['收藏数']
    
    # 计算深度互动率（收藏率）和轻互动率（点赞率）
    # 添加平滑因子，防止极端值
    MIN_VIEWS = 1000  # 最小浏览量基数
    df['收藏率'] = (df['收藏数'] + 1) / (df['浏览数'] + MIN_VIEWS)
    df['点赞率'] = (df['点赞数'] + 2) / (df['浏览数'] + MIN_VIEWS)

    
    # 计算互动转化效率
    df['互动转化率'] = (df['收藏数'] +5)/ (df['点赞数'] + 50)
    
    # 标准化互动转换率
    df['互动转化率_标准化'] = normalize(df['互动转化率'])
    
    # 修改综合评分计算
    df['综合评分'] = (
        df['浏览数_标准化'] * 0.20 +           # 从0.22降低到0.20
        df['日均浏览_标准化'] * 0.28 +         # 从0.30降低到0.28
        df['互动质量_标准化'] * 0.12 +         # 从0.32降低到0.30
        df['互动密度_标准化'] * 0.06 +         # 保持0.12
        df['字数权重'] * 0.04 +                # 保持0.04
        df['互动转化率_标准化'] * 0.3         # 新增互动转化率权重
    ) * df['时间权重'] * df['浏览量惩罚'] * df['长度奖励']
    
    # 生成推荐排名
    recommended_posts = df.sort_values('综合评分', ascending=False)
    
    # 准备出数据
    output_columns = [
        '排名', '标题', '作者', '字数', '浏览数', '日均浏览', '有效统计天数',
        '点赞数', '收藏数', '评论数', '点赞收藏比', '收藏率', '点赞率', '互动转化率',
        '发表时间', '综合评分'
    ]
    
    # 格式化输出数据
    recommended_posts_output = recommended_posts[output_columns[1:]].copy()  # 先不包含排名列
    recommended_posts_output['发表时间'] = recommended_posts_output['发表时间'].dt.strftime('%Y-%m-%d')
    recommended_posts_output['综合评分'] = recommended_posts_output['综合评分'].round(3)
    recommended_posts_output['日均浏览'] = recommended_posts_output['日均浏览'].round(1)
    recommended_posts_output['有效统计天数'] = recommended_posts_output['有效统计天数'].round(1)
    
    # 添加排名列
    recommended_posts_output.insert(0, '排名', range(1, len(recommended_posts_output) + 1))
    
    # 保存推荐排名
    output_file = output_dir / '文章推荐排名.csv'
    recommended_posts_output.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    # 调用作者分析函数
    analyze_author(df, output_dir)

    logging.info(f"分析完成，结果已保存到 {output_dir} 目录")
    evaluate_ranking_quality()
def evaluate_ranking_quality():
    """评估排名质量"""
    df = pd.read_csv('./分析报告/文章推荐排名.csv')
    current_time = pd.Timestamp.now()
    df['发表时间'] = pd.to_datetime(df['发表时间'])
    
    # 计算时间分布
    df['文章年龄'] = (current_time - df['发表时间']).dt.days

    # 统计前10/50的时间分布
    top10_age = df.iloc[:10]['文章年龄']
    top50_age = df.iloc[:50]['文章年龄']

    # 计算评分分布
    score_ratio_10 = df.iloc[0]['综合评分'] / df.iloc[9]['综合评分']
    score_ratio_50 = df.iloc[0]['综合评分'] / df.iloc[49]['综合评分']

    # 输出评估报告
    print("\n排名质量评估报告：")
    print(f"前10名中30天内文章占比: {(top10_age <= 30).mean():.1%}")
    print(f"前50名中90天内文章占比: {(top50_age <= 90).mean():.1%}")
    print(f"前10名分数比值: {score_ratio_10:.1f}")
    print(f"前50名分数比值: {score_ratio_50:.1f}")
    print(f"前10名平均字数: {df.iloc[:10]['字数'].mean():.0f}")
    print(f"前10名平均日均浏览: {df.iloc[:10]['日均浏览'].mean():.1f}")

    # 添加更多评估维度
    print("\n详细评估指标：")
    print(f"前10名字数中位数: {df.iloc[:10]['字数'].median():.0f}")
    # 计算互动率（如果需要的话）
    df['互动率'] = (df['点赞数'] + df['收藏数']) / df['浏览数'].clip(lower=1)
    print(f"前10名互动率: {df.iloc[:10]['互动率'].mean():.3f}")
    print(f"10-30名平均分/前10名平均分: {df.iloc[9:29]['综合评分'].mean() / df.iloc[:10]['综合评分'].mean():.2f}")
    
    # 字数分布分析
    word_ranges = [(0, 15000), (15000, 30000), (30000, 50000), (50000, float('inf'))]
    for start, end in word_ranges:
        count = len(df[(df['排名'] <= 50) & (df['字数'] > start) & (df['字数'] <= end)])
        print(f"前50名中{start}-{end if end != float('inf') else '以上'}字文章数量: {count}")

    print("\n互动指标分析：")
    print(f"前10名平均收藏率: {df.iloc[:10]['收藏率'].mean():.3f}")
    print(f"前10名平均点赞率: {df.iloc[:10]['点赞率'].mean():.3f}")
    print(f"前10名平均互动转化率: {df.iloc[:10]['互动转化率'].mean():.3f}")

if __name__ == "__main__":
    # 设置日志配置
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    # 设置数据文件路径
    data_file = "data.csv"
    try:
        analyze_post_trends(data_file)
        analyze_post_quality(data_file)
        logging.info("所有分析任务已完成")
    except Exception as e:
        logging.error(f"分析过程中出现错误: {str(e)}")
        logging.error(f"错误堆栈:\n{traceback.format_exc()}")
            