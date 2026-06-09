"""
省级口粮数据提取与可视化
从原始消费数据中提取各省份全体居民口径的粮食（原粮）消费量
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
print("省级口粮数据提取")
print("=" * 50)

df = pd.read_csv(
    INPUT_PATH,
    header=None,
    skiprows=3,
    encoding='utf-8',
    na_values=['#N/A', '']
)

# 过滤无效行（省份为空的行）
df = df[df.iloc[:, 0].notna()].copy()
print(f"\n有效数据行数: {len(df)}")
print(f"省份数量: {df.iloc[:, 0].nunique()}")

# ===== 2. 提取口粮数据 =====
# Col 0: 省份, Col 1: 年份, Col 2: 行政区划代码, Col 3: 粮食（原粮）
food_grain = pd.DataFrame({
    '省份': df.iloc[:, 0].values,
    '年份': df.iloc[:, 1].astype(int).values,
    '行政区划代码': df.iloc[:, 2].astype(int).values,
    '口粮（千克/人）': pd.to_numeric(df.iloc[:, 3], errors='coerce').values
})

# 按省份、年份排序
food_grain = food_grain.sort_values(['省份', '年份']).reset_index(drop=True)

print(f"\n口粮数据概览:")
print(f"  年份范围: {food_grain['年份'].min()} - {food_grain['年份'].max()}")
print(f"  非缺失记录数: {food_grain['口粮（千克/人）'].notna().sum()}")
print(f"  缺失记录数: {food_grain['口粮（千克/人）'].isna().sum()}")

# 各年有效数据量
yearly_valid = food_grain.groupby('年份')['口粮（千克/人）'].apply(
    lambda x: x.notna().sum()
)
print(f"\n各年有效省份数:")
for yr, cnt in yearly_valid.items():
    if cnt > 0:
        print(f"  {yr}年: {cnt}个省")

# ===== 3. 输出表格（中文列头） =====
print(f"\n输出表格...")

# 3a. 面板格式：每个省一行，每年一列
pivot = food_grain.pivot_table(
    index=['省份', '行政区划代码'],
    columns='年份',
    values='口粮（千克/人）'
)
pivot.columns = [f'{col}年' for col in pivot.columns]
pivot.to_csv(os.path.join(TABLE_DIR, '省级口粮面板数据.csv'), encoding='utf-8-sig')
print(f"  [OK] 省级口粮面板数据.csv")

# 3b. 长表格式
food_grain.to_csv(
    os.path.join(TABLE_DIR, '省级口粮长表数据.csv'),
    index=False,
    encoding='utf-8-sig'
)
print(f"  [OK] 省级口粮长表数据.csv")

# ===== 4. 可视化 =====
print(f"\n生成图表...")
plt.rcParams['font.sans-serif'] = ['SimHei', 'WenQuanYi Micro Hei', 'Noto Sans CJK SC',
                                     'Noto Sans CJK', 'AR PL UMing CN', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 4a. 31省口粮历史轨迹（汇总图）
fig, ax = plt.subplots(figsize=(16, 10))
colors = plt.cm.tab20(np.linspace(0, 1, 20))
colors = list(colors) * 2

for i, (prov, grp) in enumerate(food_grain.groupby('省份')):
    valid = grp.dropna(subset=['口粮（千克/人）'])
    if len(valid) > 0:
        ax.plot(valid['年份'], valid['口粮（千克/人）'],
                color=colors[i % len(colors)], linewidth=1.5, alpha=0.8, label=prov)

ax.set_xlabel('年份', fontsize=13)
ax.set_ylabel('口粮（千克/人）', fontsize=13)
ax.set_title('31省口粮历史轨迹（全体居民口径）', fontsize=15, fontweight='bold')
ax.set_xticks(range(2000, 2026, 2))
ax.legend(ncol=4, fontsize=8, loc='upper right')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(FIGURE_DIR, '31省口粮历史轨迹汇总.png'), dpi=200)
plt.close()
print(f"  [OK] 31省口粮历史轨迹汇总.png")

# 4b. 分区域子图
region_map = {
    '华北': ['北京', '天津', '河北', '山西', '内蒙古'],
    '东北': ['辽宁', '吉林', '黑龙江'],
    '华东': ['上海', '江苏', '浙江', '安徽', '福建', '江西', '山东'],
    '华中': ['河南', '湖北', '湖南'],
    '华南': ['广东', '广西', '海南'],
    '西南': ['重庆', '四川', '贵州', '云南', '西藏'],
    '西北': ['陕西', '甘肃', '青海', '宁夏', '新疆']
}

fig, axes = plt.subplots(3, 3, figsize=(18, 14))
axes = axes.flatten()

for idx, (region, provs) in enumerate(region_map.items()):
    ax = axes[idx]
    for prov in provs:
        grp = food_grain[food_grain['省份'] == prov].dropna(subset=['口粮（千克/人）'])
        if len(grp) > 0:
            ax.plot(grp['年份'], grp['口粮（千克/人）'], linewidth=1.8, label=prov)
    ax.set_title(region, fontsize=13, fontweight='bold')
    ax.set_xlabel('年份', fontsize=11)
    ax.set_ylabel('口粮（千克/人）', fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

# 隐藏多余的子图
for idx in range(len(region_map), len(axes)):
    axes[idx].axis('off')

plt.suptitle('分区域口粮历史轨迹', fontsize=16, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig(os.path.join(FIGURE_DIR, '分区域口粮历史轨迹.png'), dpi=200)
plt.close()
print(f"  [OK] 分区域口粮历史轨迹.png")

# ===== 5. 数据摘要 =====
print(f"\n数据摘要:")
latest_year = food_grain['年份'].max()
for prov, grp in food_grain.groupby('省份'):
    latest = grp[grp['年份'] == latest_year]
    if len(latest) > 0 and latest['口粮（千克/人）'].notna().any():
        val = latest['口粮（千克/人）'].values[0]
        print(f"  {prov}: {latest_year}年 = {val:.1f} 千克/人")

print(f"\n完成！输出目录: {OUTPUT_DIR}")
