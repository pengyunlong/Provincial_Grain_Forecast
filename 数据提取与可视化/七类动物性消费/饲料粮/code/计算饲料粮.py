"""
饲料粮折算计算与可视化
基于七类动物性食品消费量，按折算系数计算饲料粮

折算系数：
  猪肉: 3.3, 牛肉: 2.0, 羊肉: 1.0, 禽肉: 1.9,
  水产品: 0.8, 蛋类: 2.0, 奶类: 0.5

计算公式：
  饲料粮 = 猪肉×3.3 + 牛肉×2.0 + 羊肉×1.0 + 禽肉×1.9
         + 水产品×0.8 + 蛋类×2.0 + 奶类×0.5
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

# ===== 路径配置 =====
# 输入：七类动物性消费的输出表格
INPUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "table", "省级七类动物性消费长表数据.csv"
)
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
TABLE_DIR = os.path.join(OUTPUT_DIR, "..", "table")
FIGURE_DIR = os.path.join(OUTPUT_DIR, "..", "figure")

# 确保路径存在
TABLE_DIR = os.path.normpath(TABLE_DIR)
FIGURE_DIR = os.path.normpath(FIGURE_DIR)
os.makedirs(TABLE_DIR, exist_ok=True)
os.makedirs(FIGURE_DIR, exist_ok=True)

# ===== 折算系数 =====
COEFFICIENTS = {
    '猪肉（千克/人）': 3.3,
    '牛肉（千克/人）': 2.0,
    '羊肉（千克/人）': 1.0,
    '禽肉（千克/人）': 1.9,
    '水产品（千克/人）': 0.8,
    '蛋类（千克/人）': 2.0,
    '奶类（千克/人）': 0.5,
}
FOOD_ITEMS = list(COEFFICIENTS.keys())

print("=" * 50)
print("饲料粮折算计算")
print("=" * 50)

# ===== 1. 读取七类动物性消费数据 =====
print(f"\n读取数据: {INPUT_PATH}")
df = pd.read_csv(INPUT_PATH, encoding='utf-8-sig')
print(f"  行数: {len(df)}")
print(f"  省份数: {df['省份'].nunique()}")
print(f"  年份范围: {df['年份'].min()} - {df['年份'].max()}")

# ===== 2. 计算饲料粮 =====
print(f"\n计算饲料粮...")

# 检查各项系数是否匹配
for item in FOOD_ITEMS:
    if item not in df.columns:
        print(f"  [警告] 列 '{item}' 未找到！")

# 计算饲料粮：仅当所有分项都非缺失时计算
feed_mask = df[FOOD_ITEMS].notna().all(axis=1)
df['饲料粮折算值（千克/人）'] = np.where(
    feed_mask,
    sum(df[item] * coeff for item, coeff in COEFFICIENTS.items()),
    np.nan
)

# 缺失分项计数
df['饲料粮缺失分项数'] = df[FOOD_ITEMS].isna().sum(axis=1)

print(f"  有效记录（饲料粮有值）: {feed_mask.sum()}")
print(f"  缺失记录: {(~feed_mask).sum()}")

# ===== 3. 输出表格 =====
print(f"\n输出表格...")

# 3a. 完整饲料粮长表
feed_table = df[['省份', '年份', '行政区划代码'] + FOOD_ITEMS +
                ['饲料粮折算值（千克/人）', '饲料粮缺失分项数']].copy()
feed_table.to_csv(
    os.path.join(TABLE_DIR, '省级饲料粮长表数据.csv'),
    index=False, encoding='utf-8-sig'
)
print(f"  [OK] 省级饲料粮长表数据.csv")

# 3b. 面板格式
pivot = df.pivot_table(
    index=['省份', '行政区划代码'],
    columns='年份',
    values='饲料粮折算值（千克/人）'
)
pivot.columns = [f'{int(col)}年' for col in pivot.columns]
pivot.to_csv(
    os.path.join(TABLE_DIR, '省级饲料粮面板数据.csv'),
    encoding='utf-8-sig'
)
print(f"  [OK] 省级饲料粮面板数据.csv")

# 3c. 七类分项对饲料粮的贡献（各分项折算后的绝对值）
for item, coeff in COEFFICIENTS.items():
    contribution_col = f'{item}（折算）'
    df[contribution_col] = df[item] * coeff

contrib_cols = [f'{item}（折算）' for item in FOOD_ITEMS]
contrib_df = df[['省份', '年份', '行政区划代码'] + contrib_cols + ['饲料粮折算值（千克/人）']].copy()
contrib_df.to_csv(
    os.path.join(TABLE_DIR, '省级饲料粮分项贡献表.csv'),
    index=False, encoding='utf-8-sig'
)
print(f"  [OK] 省级饲料粮分项贡献表.csv")

# ===== 4. 可视化 =====
print(f"\n生成图表...")
plt.rcParams['font.sans-serif'] = ['SimHei', 'WenQuanYi Micro Hei', 'Noto Sans CJK SC',
                                     'Noto Sans CJK', 'AR PL UMing CN', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 只使用2015年之后的完整数据
valid = df[df['年份'] >= 2015].copy()

# 4a. 31省饲料粮历史轨迹
fig, ax = plt.subplots(figsize=(16, 10))
colors = plt.cm.tab20(np.linspace(0, 1, 20))
colors = list(colors) * 2

for i, (prov, grp) in enumerate(valid.groupby('省份')):
    data = grp.dropna(subset=['饲料粮折算值（千克/人）'])
    if len(data) > 0:
        ax.plot(data['年份'], data['饲料粮折算值（千克/人）'],
                color=colors[i % len(colors)], linewidth=1.5, alpha=0.8, label=prov)

ax.set_xlabel('年份', fontsize=13)
ax.set_ylabel('饲料粮折算值（千克/人）', fontsize=13)
ax.set_title('31省饲料粮折算值历史轨迹（2015-2024）', fontsize=15, fontweight='bold')
ax.set_xticks(range(2015, 2026))
ax.legend(ncol=4, fontsize=8, loc='upper left')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(FIGURE_DIR, '31省饲料粮历史轨迹汇总.png'), dpi=200)
plt.close()
print(f"  [OK] 31省饲料粮历史轨迹汇总.png")

# 4b. 全国饲料粮均值趋势 vs 口粮均值趋势
fig, ax1 = plt.subplots(figsize=(12, 7))

# 饲料粮（左轴）
feed_mean = valid.groupby('年份')['饲料粮折算值（千克/人）'].mean()
color1 = '#C0392B'
ax1.plot(feed_mean.index, feed_mean.values, marker='o', linewidth=2.5,
         color=color1, label='饲料粮折算值')
ax1.set_xlabel('年份', fontsize=13)
ax1.set_ylabel('饲料粮（千克/人）', fontsize=13, color=color1)
ax1.tick_params(axis='y', labelcolor=color1)

# 口粮（右轴）- 读取口粮数据
food_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))),
    "口粮", "table", "省级口粮长表数据.csv"
)
if os.path.exists(food_path):
    food_df = pd.read_csv(food_path, encoding='utf-8-sig')
    food_valid = food_df[food_df['年份'] >= 2015].copy()
    food_mean = food_valid.groupby('年份')['口粮（千克/人）'].mean()

    ax2 = ax1.twinx()
    color2 = '#2980B9'
    ax2.plot(food_mean.index, food_mean.values, marker='s', linewidth=2.5,
             color=color2, label='口粮', linestyle='--')
    ax2.set_ylabel('口粮（千克/人）', fontsize=13, color=color2)
    ax2.tick_params(axis='y', labelcolor=color2)

fig.suptitle('全国口粮与饲料粮人均消费量对比（2015-2024）', fontsize=15, fontweight='bold')
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=12)
ax1.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(FIGURE_DIR, '全国口粮与饲料粮对比趋势.png'), dpi=200)
plt.close()
print(f"  [OK] 全国口粮与饲料粮对比趋势.png")

# 4c. 各省饲料粮堆叠面积图：七类分项贡献
top_provs = sorted(valid.groupby('省份')['饲料粮折算值（千克/人）'].last().nlargest(8).index.tolist())

fig, axes = plt.subplots(2, 4, figsize=(20, 10))
axes = axes.flatten()

labels_cn = ['猪肉', '牛肉', '羊肉', '禽肉', '水产品', '蛋类', '奶类']
colors_stack = ['#E74C3C', '#8E44AD', '#F39C12', '#3498DB', '#1ABC9C', '#E67E22', '#95A5A6']

for idx, prov in enumerate(top_provs):
    ax = axes[idx]
    grp = valid[valid['省份'] == prov].set_index('年份').sort_index()
    contribs = grp[contrib_cols].dropna()

    if len(contribs) > 0:
        ax.stackplot(contribs.index,
                     [contribs[col] for col in contrib_cols],
                     labels=labels_cn, colors=colors_stack, alpha=0.85)
        ax.plot(contribs.index, contribs.sum(axis=1),
                color='black', linewidth=2, label='饲料粮合计')

    ax.set_title(prov, fontsize=12, fontweight='bold')
    ax.set_ylabel('千克/人', fontsize=10)
    ax.legend(fontsize=7, ncol=2)
    ax.set_xlim(2015, 2024)
    ax.grid(True, alpha=0.3)

plt.suptitle('前8位省份饲料粮分项贡献堆叠图（2015-2024）', fontsize=16, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig(os.path.join(FIGURE_DIR, '前8省饲料粮分项贡献堆叠图.png'), dpi=200)
plt.close()
print(f"  [OK] 前8省饲料粮分项贡献堆叠图.png")

# 4d. 2024年饲料粮省际分布柱状图
latest_year = valid['年份'].max()
latest = valid[valid['年份'] == latest_year].dropna(subset=['饲料粮折算值（千克/人）'])
latest_sorted = latest.sort_values('饲料粮折算值（千克/人）', ascending=False)

fig, ax = plt.subplots(figsize=(14, 10))
bars = ax.barh(range(len(latest_sorted)), latest_sorted['饲料粮折算值（千克/人）'].values,
               color='#27AE60', edgecolor='white')
ax.set_yticks(range(len(latest_sorted)))
ax.set_yticklabels(latest_sorted['省份'].values)
ax.set_xlabel('饲料粮折算值（千克/人）', fontsize=13)
ax.set_title(f'{latest_year}年各省饲料粮折算值', fontsize=15, fontweight='bold')
ax.invert_yaxis()
for i, (_, row) in enumerate(latest_sorted.iterrows()):
    ax.text(row['饲料粮折算值（千克/人）'] + 0.5, i,
            f'{row["饲料粮折算值（千克/人）"]:.1f}', va='center', fontsize=9)
ax.grid(True, alpha=0.3, axis='x')
plt.tight_layout()
plt.savefig(os.path.join(FIGURE_DIR, f'{latest_year}年各省饲料粮折算值排名.png'), dpi=200)
plt.close()
print(f"  [OK] {latest_year}年各省饲料粮折算值排名.png")

# ===== 5. 数据摘要 =====
print(f"\n数据摘要 ...")
for prov, grp in valid.groupby('省份'):
    latest_val = grp[grp['年份'] == latest_year]['饲料粮折算值（千克/人）'].values
    if len(latest_val) > 0 and not np.isnan(latest_val[0]):
        print(f"  {prov}: {latest_year}年 = {latest_val[0]:.1f} 千克/人")

print(f"\n完成！输出目录: {TABLE_DIR}")
