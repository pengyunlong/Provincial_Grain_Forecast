"""
七类动物性食品消费数据提取与可视化
从原始消费数据中提取各省份全体居民口径的七类动物性食品消费量
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

# ===== 路径配置 =====
INPUT_PATH = "/media/sf_/粮食需求/宏观数据收集（CSV编码）/消费数据（省级）.csv"
OUTPUT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLE_DIR = os.path.join(OUTPUT_DIR, "table")
FIGURE_DIR = os.path.join(OUTPUT_DIR, "figure")
os.makedirs(TABLE_DIR, exist_ok=True)
os.makedirs(FIGURE_DIR, exist_ok=True)

# ===== 1. 读取数据 =====
print("=" * 50)
print("七类动物性食品消费数据提取")
print("=" * 50)

df = pd.read_csv(
    INPUT_PATH,
    header=None,
    skiprows=3,
    encoding='utf-8',
    na_values=['#N/A', '']
)

# 过滤无效行
df = df[df.iloc[:, 0].notna()].copy()
print(f"\n有效数据行数: {len(df)}")
print(f"省份数量: {df.iloc[:, 0].nunique()}")

# ===== 2. 提取七类动物性消费数据 =====
# Col 0:省份, 1:年份, 2:行政区划代码
# 全体居民口径: Col 10=猪肉, 11=牛肉, 12=羊肉, 13=禽肉, 14=水产品, 15=蛋类, 16=奶类
col_mapping = {
    '省份': df.iloc[:, 0].values,
    '年份': df.iloc[:, 1].astype(int).values,
    '行政区划代码': df.iloc[:, 2].astype(int).values,
    '猪肉（千克/人）': pd.to_numeric(df.iloc[:, 10], errors='coerce').values,
    '牛肉（千克/人）': pd.to_numeric(df.iloc[:, 11], errors='coerce').values,
    '羊肉（千克/人）': pd.to_numeric(df.iloc[:, 12], errors='coerce').values,
    '禽肉（千克/人）': pd.to_numeric(df.iloc[:, 13], errors='coerce').values,
    '水产品（千克/人）': pd.to_numeric(df.iloc[:, 14], errors='coerce').values,
    '蛋类（千克/人）': pd.to_numeric(df.iloc[:, 15], errors='coerce').values,
    '奶类（千克/人）': pd.to_numeric(df.iloc[:, 16], errors='coerce').values,
}

animal_food = pd.DataFrame(col_mapping)
animal_food = animal_food.sort_values(['省份', '年份']).reset_index(drop=True)

# 缺失诊断
food_items = ['猪肉（千克/人）', '牛肉（千克/人）', '羊肉（千克/人）',
              '禽肉（千克/人）', '水产品（千克/人）', '蛋类（千克/人）', '奶类（千克/人）']
animal_food['缺失分项数'] = animal_food[food_items].isna().sum(axis=1)

print(f"\n七类动物性消费数据概览:")
print(f"  年份范围: {animal_food['年份'].min()} - {animal_food['年份'].max()}")
print(f"  非缺失完整记录（7项齐全）: {(animal_food['缺失分项数'] == 0).sum()}")
print(f"  部分缺失记录:                        {(animal_food['缺失分项数'] > 0).sum()}")

# 各年完整记录数
print(f"\n各年完整记录（7项齐全）数:")
yearly_complete = animal_food.groupby('年份').apply(lambda x: (x['缺失分项数'] == 0).sum())
for yr, cnt in yearly_complete.items():
    print(f"  {yr}年: {cnt}个省")

# ===== 3. 输出表格 =====
print(f"\n输出表格...")

# 3a. 面板格式：各省七类分项逐年的完整数据
animal_food.to_csv(
    os.path.join(TABLE_DIR, '省级七类动物性消费长表数据.csv'),
    index=False,
    encoding='utf-8-sig'
)
print(f"  [OK] 省级七类动物性消费长表数据.csv")

# 3b. 各分项面板（方便查看）
for item in food_items:
    pivot = animal_food.pivot_table(
        index=['省份', '行政区划代码'],
        columns='年份',
        values=item
    )
    pivot.columns = [f'{int(col)}年' for col in pivot.columns]
    # 简化文件名
    short_name = item.replace('（千克/人）', '')
    pivot.to_csv(
        os.path.join(TABLE_DIR, f'省级{short_name}面板数据.csv'),
        encoding='utf-8-sig'
    )
    print(f"  [OK] 省级{short_name}面板数据.csv")

# 3c. 缺失诊断表
missing_diag = animal_food[animal_food['缺失分项数'] > 0][
    ['省份', '年份'] + food_items + ['缺失分项数']
]
missing_diag.to_csv(
    os.path.join(TABLE_DIR, '动物性消费缺失诊断.csv'),
    index=False,
    encoding='utf-8-sig'
)
print(f"  [OK] 动物性消费缺失诊断.csv（{len(missing_diag)}行）")

# ===== 4. 可视化 =====
print(f"\n生成图表...")
plt.rcParams['font.sans-serif'] = ['SimHei', 'WenQuanYi Micro Hei', 'Noto Sans CJK SC',
                                     'Noto Sans CJK', 'AR PL UMing CN', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 2015年以后的数据才完整，可视化主要用2015-2024
valid = animal_food[animal_food['年份'] >= 2015].copy()
years = sorted(valid['年份'].unique())

# 4a. 七类分项各年均值（全国平均）
fig, ax = plt.subplots(figsize=(14, 8))
mean_by_year = valid.groupby('年份')[food_items].mean()
labels_short = ['猪肉', '牛肉', '羊肉', '禽肉', '水产品', '蛋类', '奶类']
colors = ['#E74C3C', '#8E44AD', '#F39C12', '#3498DB', '#1ABC9C', '#E67E22', '#95A5A6']

for i, (item, label) in enumerate(zip(food_items, labels_short)):
    ax.plot(mean_by_year.index, mean_by_year[item],
            marker='o', linewidth=2.5, color=colors[i], label=label)

ax.set_xlabel('年份', fontsize=13)
ax.set_ylabel('消费量（千克/人）', fontsize=13)
ax.set_title('全国七类动物性食品平均消费量趋势', fontsize=15, fontweight='bold')
ax.legend(fontsize=12, ncol=2)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(FIGURE_DIR, '全国七类动物性消费均值趋势.png'), dpi=200)
plt.close()
print(f"  [OK] 全国七类动物性消费均值趋势.png")

# 4b. 31省猪肉消费热图（2015-2024）
pork_pivot = valid.pivot_table(
    index='省份', columns='年份', values='猪肉（千克/人）'
)
fig, ax = plt.subplots(figsize=(12, 12))
im = ax.imshow(pork_pivot.values, cmap='YlOrRd', aspect='auto')

ax.set_xticks(range(len(years)))
ax.set_xticklabels(years)
ax.set_yticks(range(len(pork_pivot.index)))
ax.set_yticklabels(pork_pivot.index)
ax.set_title('31省猪肉消费量热图（2015-2024，千克/人）', fontsize=14, fontweight='bold')

fig.colorbar(im, ax=ax, shrink=0.6)
plt.tight_layout()
plt.savefig(os.path.join(FIGURE_DIR, '31省猪肉消费热图.png'), dpi=200)
plt.close()
print(f"  [OK] 31省猪肉消费热图.png")

# 4c. 猪肉 + 禽肉 + 水产品 三大类各年趋势（分省）
n_provs = len(valid['省份'].unique())
n_cols = 6
n_rows = int(np.ceil(n_provs / n_cols))
fig, axes = plt.subplots(n_rows, n_cols, figsize=(n_cols * 3.5, n_rows * 3.5))
axes = axes.flatten()

provinces = sorted(valid['省份'].unique())
top3_items = ['猪肉（千克/人）', '禽肉（千克/人）', '水产品（千克/人）']
top3_labels = ['猪肉', '禽肉', '水产品']
top3_colors = ['#E74C3C', '#3498DB', '#1ABC9C']

for idx, prov in enumerate(provinces):
    ax = axes[idx]
    grp = valid[valid['省份'] == prov].set_index('年份')
    for i, item in enumerate(top3_items):
        ax.plot(grp.index, grp[item], marker='o', linewidth=2,
                color=top3_colors[i], label=top3_labels[i])
    ax.set_title(prov, fontsize=11, fontweight='bold')
    ax.set_ylabel('千克/人', fontsize=9)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

for idx in range(len(provinces), len(axes)):
    axes[idx].axis('off')

plt.suptitle('各省猪肉/禽肉/水产品消费趋势（2015-2024）', fontsize=16, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig(os.path.join(FIGURE_DIR, '各省猪肉禽肉水产品趋势.png'), dpi=200)
plt.close()
print(f"  [OK] 各省猪肉禽肉水产品趋势.png")

print(f"\n完成！输出目录: {OUTPUT_DIR}")
