import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import seaborn as sns
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
    output_dir = Path("分析报告")
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
            f.write(f'{block}: {count}篇 ({count / len(df) * 100:.2f}%)\n')
        f.write('\n')

        f.write('3. 月度发表TOP5\n')
        top_months = total_monthly.sort_values(ascending=False).head()
        for month, count in top_months.items():
            f.write(f'{month}: {count}篇\n')

    logging.info("分析完成，报告已生成")
