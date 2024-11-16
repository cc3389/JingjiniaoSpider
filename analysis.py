import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import seaborn as sns
from datetime import datetime
import logging

plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置中文字体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

def analyze_post_trends(csv_path: str = "data.csv") -> None:
    """分析文章发表趋势并生成报表"""
    logging.info("开始分析文章发表趋势")
    
    # 读取CSV文件
    df = pd.read_csv(csv_path)
    
    # 将发表时间转换为datetime类型
    df['发表时间'] = pd.to_datetime(df['发表时间'])
    
    # 添加年月列
    df['年月'] = df['发表时间'].dt.strftime('%Y-%m')
    
    # 按年月和板块统计文章数量
    monthly_counts = df.groupby(['年月', '板块']).size().unstack(fill_value=0)
    total_monthly = df.groupby('年月').size()
    
    # 创建输出目录
    output_dir = Path("./分析报告")
    output_dir.mkdir(exist_ok=True)
    
    # 生成总体趋势图
    plt.figure(figsize=(15, 8))
    total_monthly.plot(kind='line', marker='o')
    plt.title('文章发表数量月度趋势')
    plt.xlabel('年月')
    plt.ylabel('文章数量')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_dir / '总体发表趋势.png')
    plt.close()
    
    # 生成堆叠面积图
    plt.figure(figsize=(15, 8))
    monthly_counts.plot(kind='area', stacked=True)
    plt.title('各板块文章发表数量趋势')
    plt.xlabel('年月')
    plt.ylabel('文章数量')
    plt.xticks(rotation=45)
    plt.legend(title='板块', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_dir / '板块分布趋势.png')
    plt.close()
    
    # 生成热力图
    plt.figure(figsize=(15, 8))
    sns.heatmap(monthly_counts.T, cmap='YlOrRd', annot=True, fmt='g')
    plt.title('文章发表数量热力图')
    plt.xlabel('年月')
    plt.ylabel('板块')
    plt.tight_layout()
    plt.savefig(output_dir / '发表数量热力图.png')
    plt.close()
    
    # 生成统计报告
    with open(output_dir / '统计报告.txt', 'w', encoding='utf-8') as f:
        f.write('文章发表统计报告\n')
        f.write('=' * 50 + '\n\n')
        
        f.write('1. 总体统计\n')
        f.write(f'总文章数：{len(df)}\n')
        f.write(f'统计周期：{df["发表时间"].min().strftime("%Y-%m")} 至 {df["发表时间"].max().strftime("%Y-%m")}\n\n')
        
        f.write('2. 板块分布\n')
        block_stats = df['板块'].value_counts()
        for block, count in block_stats.items():
            f.write(f'{block}: {count}篇 ({count/len(df)*100:.2f}%)\n')
        f.write('\n')
        
        f.write('3. 月度发表TOP5\n')
        top_months = total_monthly.sort_values(ascending=False).head()
        for month, count in top_months.items():
            f.write(f'{month}: {count}篇\n')
            
    logging.info("分析完成，报告已生成")

def analyze_post_quality(csv_path: str = "data.csv") -> None:
    """分析文章质量并生成报表"""
    logging.info("开始分析文章质量")
    
    # 读取CSV文件
    df = pd.read_csv(csv_path)
    
    # 数据预处理
    df['浏览数'] = df['浏览数'].astype(int)
    df['点赞数'] = df['点赞数'].astype(int)
    df['收藏数'] = df['收藏数'].astype(int)
    
    # 计算综合评分
    # 1. 计算互动率 = (点赞数 + 收藏数) / 浏览数
    df['互动率'] = (df['点赞数'] + df['收藏数']) / df['浏览数']
    
    # 2. 计算标准化分数
    def normalize(series):
        return (series - series.min()) / (series.max() - series.min())
    
    df['浏览数_标准化'] = normalize(df['浏览数'])
    df['互动率_标准化'] = normalize(df['互动率'])
    
    # 3. 计算综合评分 (可以调整权重)
    df['综合评分'] = df['浏览数_标准化'] * 0.4 + df['互动率_标准化'] * 0.6
    
    # 创建输出目录
    output_dir = Path("./分析报告")
    output_dir.mkdir(exist_ok=True)
    
    # 生成TOP20文章报告
    top_20 = df.nlargest(20, '综合评分')[['标题', '板块', '浏览数', '点赞数', '收藏数', '互动率', '综合评分']]
    top_20.to_csv(output_dir / 'TOP20优质文章.csv', index=False, encoding='utf-8-sig')
    
    # 生成板块质量分析
    block_quality = df.groupby('板块').agg({
        '浏览数': 'mean',
        '点赞数': 'mean',
        '收藏数': 'mean',
        '互动率': 'mean',
        '综合评分': 'mean'
    }).round(4)
    
    block_quality.to_csv(output_dir / '板块质量分析.csv', encoding='utf-8-sig')
    
    # 生成可视化图表
    plt.figure(figsize=(15, 8))
    
    # 1. 互动率与浏览数的散点图
    plt.scatter(df['浏览数'], df['互动率'], alpha=0.5)
    plt.title('文章浏览数与互动率关系')
    plt.xlabel('浏览数')
    plt.ylabel('互动率')
    
    # 添加TOP10文章标注
    top_10 = df.nlargest(10, '综合评分')
    for _, row in top_10.iterrows():
        plt.annotate(row['标题'][:10] + '...', 
                    (row['浏览数'], row['互动率']),
                    xytext=(5, 5), textcoords='offset points')
    
    plt.tight_layout()
    plt.savefig(output_dir / '浏览数与互动率关系.png')
    plt.close()
    
    # 2. 板块质量箱型图
    plt.figure(figsize=(15, 8))
    df.boxplot(column='综合评分', by='板块', figsize=(15, 8))
    plt.title('各板块文章质量分布')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_dir / '板块质量分布.png')
    plt.close()
    
    # 输出统计结果
    logging.info(f"分析完成，结果已保存到 {output_dir} 目录")
    
    # 打印一些关键发现
    print("\n=== 文章质量分析报告 ===")
    print("\nTOP5 最受欢迎的文章：")
    for _, row in top_20.head().iterrows():
        print(f"\n标题：{row['标题']}")
        print(f"板块：{row['板块']}")
        print(f"浏览数：{row['浏览数']}")
        print(f"点赞数：{row['点赞数']}")
        print(f"收藏数：{row['收藏数']}")
        print(f"综合评分：{row['综合评分']:.4f}")
    
    print("\n各板块平均质量排名：")
    block_rank = block_quality['综合评分'].sort_values(ascending=False)
    for block, score in block_rank.items():
        print(f"{block}: {score:.4f}")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    analyze_post_trends() 