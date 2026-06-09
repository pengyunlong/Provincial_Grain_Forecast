import json
from pathlib import Path

ROOT = Path("/media/sf_/粮食需求/Provincial_Grain_Forecast/Province_Clusting")

# Load compiled JS data
with open(ROOT / "scratch" / "data.js", "r", encoding="utf-8") as f:
    data_js_content = f.read()

# We will create the index.html (or 聚类结果可视化.html) directly
# Let's write the HTML structure, CSS, and JS logic
html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>省级多维特征聚类结果可视化看板</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap" rel="stylesheet">
    <!-- ECharts -->
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        :root {
            /* Dark Theme Tokens */
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-tertiary: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --border-color: #334155;
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1);
            
            /* Cluster Colors (Dark Mode) */
            --cluster-0: #60a5fa; /* Blue */
            --cluster-1: #fbbf24; /* Yellow */
            --cluster-2: #34d399; /* Green */
            --cluster-3: #f87171; /* Red */
            
            --cluster-0-bg: rgba(96, 165, 250, 0.15);
            --cluster-1-bg: rgba(251, 191, 36, 0.15);
            --cluster-2-bg: rgba(52, 211, 153, 0.15);
            --cluster-3-bg: rgba(248, 113, 113, 0.15);
        }

        [data-theme="light"] {
            /* Light Theme Tokens */
            --bg-primary: #f8fafc;
            --bg-secondary: #ffffff;
            --bg-tertiary: #f1f5f9;
            --text-primary: #0f172a;
            --text-secondary: #64748b;
            --border-color: #e2e8f0;
            --shadow-sm: 0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px 0 rgba(0,0,0,0.06);
            --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.08), 0 2px 4px -2px rgba(0,0,0,0.04);
            --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.06), 0 4px 6px -4px rgba(0,0,0,0.04);
            
            /* Cluster Colors (Light Mode) */
            --cluster-0: #2563eb;
            --cluster-1: #d97706;
            --cluster-2: #059669;
            --cluster-3: #dc2626;
            
            --cluster-0-bg: rgba(37, 99, 235, 0.1);
            --cluster-1-bg: rgba(217, 119, 6, 0.1);
            --cluster-2-bg: rgba(5, 150, 105, 0.1);
            --cluster-3-bg: rgba(220, 38, 230, 0.1);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            transition: background-color 0.25s, border-color 0.25s, color 0.1s;
        }

        body {
            font-family: 'Outfit', 'Noto Sans SC', sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 24px;
            overflow-x: hidden;
        }

        /* Container Layout */
        .dashboard-container {
            max-width: 1600px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }

        /* Header Style */
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 24px;
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            box-shadow: var(--shadow-md);
        }

        .header-title-area h1 {
            font-size: 22px;
            font-weight: 700;
            letter-spacing: -0.5px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .header-title-area h1 span.badge {
            font-size: 11px;
            font-weight: 500;
            padding: 2px 8px;
            background-color: var(--bg-tertiary);
            color: var(--text-secondary);
            border-radius: 9999px;
            border: 1px solid var(--border-color);
        }

        .header-title-area p {
            font-size: 13px;
            color: var(--text-secondary);
            margin-top: 4px;
        }

        .header-controls {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        /* Search input */
        .search-container {
            position: relative;
        }

        .search-input {
            width: 240px;
            padding: 8px 16px 8px 36px;
            background-color: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-primary);
            font-size: 13px;
            outline: none;
        }

        .search-input:focus {
            border-color: var(--cluster-0);
        }

        .search-icon {
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            width: 16px;
            height: 16px;
            fill: var(--text-secondary);
            pointer-events: none;
        }

        /* Theme Toggle Button */
        .theme-toggle-btn {
            background: none;
            border: 1px solid var(--border-color);
            background-color: var(--bg-tertiary);
            color: var(--text-primary);
            width: 38px;
            height: 38px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
        }

        .theme-toggle-btn:hover {
            border-color: var(--text-secondary);
        }

        .theme-toggle-icon {
            width: 18px;
            height: 18px;
            fill: currentColor;
        }

        /* Main Section Grid */
        .main-grid {
            display: grid;
            grid-template-columns: 1.2fr 1fr;
            gap: 24px;
        }

        @media (max-width: 1100px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
        }

        /* Card Container styling */
        .card {
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            box-shadow: var(--shadow-md);
            display: flex;
            flex-direction: column;
            gap: 20px;
            position: relative;
        }

        .card-header-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 12px;
        }

        .card-title {
            font-size: 16px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Tabs Selector */
        .domain-tabs {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            background-color: var(--bg-tertiary);
            padding: 4px;
            border-radius: 10px;
            border: 1px solid var(--border-color);
        }

        .tab-btn {
            background: none;
            border: none;
            color: var(--text-secondary);
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            text-align: center;
            white-space: nowrap;
        }

        .tab-btn:hover {
            color: var(--text-primary);
        }

        .tab-btn.active {
            background-color: var(--bg-secondary);
            color: var(--text-primary);
            box-shadow: var(--shadow-sm);
            font-weight: 600;
        }

        /* Map Canvas */
        .map-wrapper {
            position: relative;
            background-color: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            height: 480px;
            overflow: hidden;
        }

        .chart-container {
            width: 100%;
            height: 100%;
        }

        /* Legend style */
        .custom-legend {
            position: absolute;
            bottom: 12px;
            left: 12px;
            background-color: rgba(30, 41, 59, 0.85);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.05);
            padding: 10px 12px;
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            z-index: 10;
            box-shadow: var(--shadow-md);
        }

        [data-theme="light"] .custom-legend {
            background-color: rgba(255, 255, 255, 0.85);
            border: 1px solid rgba(0, 0, 0, 0.05);
        }

        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 11px;
            cursor: pointer;
        }

        .legend-color {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }

        .legend-label {
            color: var(--text-primary);
            font-weight: 500;
        }

        .legend-count {
            color: var(--text-secondary);
        }

        /* Task details description card */
        .metadata-box {
            background-color: var(--bg-tertiary);
            border-radius: 12px;
            padding: 16px;
            font-size: 13px;
            border: 1px solid var(--border-color);
        }

        .metadata-box p {
            margin-bottom: 6px;
            line-height: 1.5;
        }

        .metadata-box p:last-child {
            margin-bottom: 0;
        }

        .metadata-box strong {
            color: var(--text-primary);
        }

        /* Right Panel: Province Info Grid */
        .province-info-grid {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .province-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }

        .province-name-container h2 {
            font-size: 26px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }

        .province-name-container p {
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 2px;
        }

        /* Multi Domain Cluster Badge Grid */
        .domain-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }

        .domain-cell {
            background-color: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 12px;
            cursor: pointer;
            position: relative;
        }

        .domain-cell:hover {
            border-color: var(--text-secondary);
        }

        .domain-cell.active-domain-border {
            border-color: var(--cluster-0);
            box-shadow: 0 0 0 1px var(--cluster-0);
        }

        .domain-cell-title {
            font-size: 11px;
            color: var(--text-secondary);
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }

        .domain-cell-value {
            font-size: 13px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
            margin-top: 4px;
        }

        .circle-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
        }

        /* Metrics list */
        .metrics-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
            max-height: 240px;
            overflow-y: auto;
            padding-right: 4px;
        }

        .metric-item {
            background-color: var(--bg-tertiary);
            padding: 10px 14px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }

        .metric-header {
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            margin-bottom: 6px;
        }

        .metric-title {
            color: var(--text-primary);
            font-weight: 500;
        }

        .metric-value {
            font-weight: 600;
        }

        .metric-bar-bg {
            height: 6px;
            background-color: rgba(255,255,255,0.06);
            border-radius: 9999px;
            position: relative;
            overflow: hidden;
        }

        [data-theme="light"] .metric-bar-bg {
            background-color: rgba(0,0,0,0.05);
        }

        .metric-bar-fill {
            height: 100%;
            border-radius: 9999px;
            background-color: var(--cluster-0);
        }

        .metric-marker-avg {
            position: absolute;
            top: 0;
            width: 2px;
            height: 100%;
            background-color: #ef4444; /* red average line */
            z-index: 5;
        }

        .metric-comparison-text {
            font-size: 10px;
            color: var(--text-secondary);
            margin-top: 4px;
            display: flex;
            justify-content: space-between;
        }

        /* Cluster Center Profile Tab Panel */
        .analysis-tabs-nav {
            display: flex;
            border-bottom: 1px solid var(--border-color);
            gap: 16px;
        }

        .analysis-tab-header {
            font-size: 14px;
            font-weight: 600;
            padding: 8px 4px;
            color: var(--text-secondary);
            cursor: pointer;
            border-bottom: 2px solid transparent;
        }

        .analysis-tab-header.active {
            color: var(--text-primary);
            border-bottom-color: var(--cluster-0);
        }

        .analysis-tab-content {
            display: none;
            min-height: 280px;
        }

        .analysis-tab-content.active {
            display: block;
        }

        .radar-chart-wrapper {
            height: 280px;
            width: 100%;
        }

        .provinces-list-grid {
            display: flex;
            flex-direction: column;
            gap: 12px;
            max-height: 280px;
            overflow-y: auto;
            padding-right: 4px;
        }

        .cluster-group {
            background-color: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 10px 12px;
        }

        .cluster-group-title {
            font-size: 11px;
            font-weight: 600;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .provinces-badges-container {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }

        .prov-badge {
            font-size: 11px;
            padding: 2px 8px;
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            color: var(--text-primary);
            cursor: pointer;
        }

        .prov-badge:hover, .prov-badge.active {
            border-color: var(--text-primary);
            background-color: var(--bg-tertiary);
        }

        /* Bottom flow section */
        .bottom-section {
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            box-shadow: var(--shadow-md);
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .sankey-wrapper {
            height: 480px;
            width: 100%;
            background-color: var(--bg-tertiary);
            border-radius: 12px;
            border: 1px solid var(--border-color);
            padding: 16px;
        }

        /* Scrollbar styling */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }

        ::-webkit-scrollbar-track {
            background: transparent;
        }

        ::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 3px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--text-secondary);
        }
    </style>
</head>
<body data-theme="dark">

<div class="dashboard-container">
    <!-- Header -->
    <header>
        <div class="header-title-area">
            <h1>省级多维特征聚类结果可视化看板 <span class="badge">ECharts 交互版</span></h1>
            <p>融合口粮消费、饲料粮消费、人口结构、经济水平与价格指数的 31 省级聚类关联分析 (2000-2024)</p>
        </div>
        <div class="header-controls">
            <!-- Province Search -->
            <div class="search-container">
                <svg class="search-icon" viewBox="0 0 24 24">
                    <path d="M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z"/>
                </svg>
                <input type="text" class="search-input" id="province-search" placeholder="输入省份名称 (如 北京)..." oninput="handleSearch()">
            </div>
            
            <!-- Theme Toggle -->
            <button class="theme-toggle-btn" onclick="toggleTheme()" title="切换主题">
                <svg class="theme-toggle-icon" id="theme-icon" viewBox="0 0 24 24">
                    <!-- Sun icon -->
                    <path d="M12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,2A1,1 0 0,1 13,3V5A1,1 0 0,1 12,6A1,1 0 0,1 11,5V3A1,1 0 0,1 12,2M12,18A1,1 0 0,1 13,19V21A1,1 0 0,1 12,22A1,1 0 0,1 11,21V19A1,1 0 0,1 12,18M5.64,16.29L7.05,17.71L5.64,19.12L4.22,17.71L5.64,16.29M18.36,5.64L19.78,7.05L18.36,8.46L16.95,7.05L18.36,5.64M2,12A1,1 0 0,1 3,11H5A1,1 0 0,1 6,12A1,1 0 0,1 5,13H3A1,1 0 0,1 2,12M18,12A1,1 0 0,1 19,11H21A1,1 0 0,1 22,12A1,1 0 0,1 21,13H19A1,1 0 0,1 18,12M7.05,6.29L5.64,7.71L4.22,6.29L5.64,4.88L7.05,6.29M19.78,16.29L18.36,17.71L16.95,16.29L18.36,14.88L19.78,16.29Z"/>
                </svg>
            </button>
        </div>
    </header>

    <!-- Main Grid Section -->
    <div class="main-grid">
        <!-- Left Column: Map and Controls -->
        <div class="card">
            <div class="domain-tabs">
                <button class="tab-btn active" id="tab-economy_clustering" onclick="switchDomain('economy_clustering')">经济水平与物价</button>
                <button class="tab-btn" id="tab-population_clustering" onclick="switchDomain('population_clustering')">人口结构特征</button>
                <button class="tab-btn" id="tab-food_grain_clustering" onclick="switchDomain('food_grain_clustering')">口粮消费特征</button>
                <button class="tab-btn" id="tab-feed_grain_clustering" onclick="switchDomain('feed_grain_clustering')">饲料粮消费特征</button>
            </div>
            
            <div class="map-wrapper">
                <div id="map-chart" class="chart-container"></div>
                <!-- Custom legend overlay -->
                <div class="custom-legend" id="map-legend">
                    <!-- populated by JS -->
                </div>
            </div>

            <!-- Task Metadata box -->
            <div class="metadata-box" id="task-metadata-box">
                <!-- populated by JS -->
            </div>
        </div>

        <!-- Right Column: Detail Panels -->
        <div style="display: flex; flex-direction: column; gap: 24px;">
            <!-- Province Details Card -->
            <div class="card">
                <div class="province-header">
                    <div class="province-name-container">
                        <h2 id="detail-province-name">北京</h2>
                        <p id="detail-province-code">行政区划代码: 110000</p>
                    </div>
                    <div style="background-color: var(--bg-tertiary); padding: 4px 12px; border-radius: 6px; font-size: 12px; border: 1px solid var(--border-color); color: var(--text-secondary);">
                        数据联动省份
                    </div>
                </div>

                <!-- 4 Domain badges summary -->
                <div class="domain-grid" id="detail-domain-badges">
                    <!-- populated by JS -->
                </div>

                <!-- Feature metrics comparing to averages -->
                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <h3 style="font-size: 13px; color: var(--text-secondary); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">当前领域核心指标明细</h3>
                    <div class="metrics-list" id="detail-metrics-list">
                        <!-- populated by JS -->
                    </div>
                </div>
            </div>

            <!-- Cluster Center Analysis Card -->
            <div class="card">
                <div class="analysis-tabs-nav">
                    <div class="analysis-tab-header active" id="tab-head-radar" onclick="switchAnalysisTab('radar')">聚类特征均值对比</div>
                    <div class="analysis-tab-header" id="tab-head-list" onclick="switchAnalysisTab('list')">聚类省份列表</div>
                </div>

                <!-- Tab content: Radar chart -->
                <div class="analysis-tab-content active" id="analysis-tab-radar">
                    <div class="radar-chart-wrapper">
                        <div id="radar-chart" class="chart-container"></div>
                    </div>
                    <div style="font-size: 11px; color: var(--text-secondary); text-align: center; margin-top: 4px;">
                        提示：各轴指标经过 Min-Max 标准化，折线表示各类中心在全国各指标中的相对水位（%）
                    </div>
                </div>

                <!-- Tab content: Province list group -->
                <div class="analysis-tab-content" id="analysis-tab-list">
                    <div class="provinces-list-grid" id="cluster-provinces-list">
                        <!-- populated by JS -->
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Bottom Section: Multi-Domain Flow (Sankey Diagram) -->
    <div class="bottom-section">
        <div class="card-header-row">
            <h2 class="card-title">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19,3H5C3.89,3 3,3.89 3,5V19C3,20.1 3.89,21 5,21H19C20.1,21 21,20.1 21,19V5C21,3.89 20.1,3 19,3M19,19H5V5H19V19M17,17H15V13H17V17M13,17H11V7H13V17M9,17H7V10H9V17Z"/>
                </svg>
                多维聚类关联特征流动 (Sankey Flow)
            </h2>
            <div style="font-size: 12px; color: var(--text-secondary);">
                鼠标悬浮于流动路径，可查看联动的省份名单及其特征转移路径
            </div>
        </div>

        <div class="sankey-wrapper">
            <div id="sankey-chart" class="chart-container"></div>
        </div>
    </div>
</div>

<!-- Raw data injection -->
<script>
//DATA_PLACEHOLDER//
</script>

<!-- Logic implementation -->
<script>
    // Global state variables
    let activeDomain = 'economy_clustering';
    let selectedProvince = '北京';
    let activeAnalysisTab = 'radar';
    let activeTheme = 'dark';
    
    // Chart instances
    let mapChart = null;
    let radarChart = null;
    let sankeyChart = null;

    // Set cluster specific color variables dynamically
    function getClusterColor(clusterId) {
        return getComputedStyle(document.documentElement).getPropertyValue(`--cluster-${clusterId}`).trim();
    }

    function getClusterBg(clusterId) {
        return getComputedStyle(document.documentElement).getPropertyValue(`--cluster-${clusterId}-bg`).trim();
    }

    // Helper: Normalize name
    function normalizeName(name) {
        const replacements = [
            ["维吾尔自治区", ""],
            ["壮族自治区", ""],
            ["回族自治区", ""],
            ["自治区", ""],
            ["特别行政区", ""],
            ["省", ""],
            ["市", ""]
        ];
        let out = String(name).trim();
        for (const [old, val] of replacements) {
            out = out.replaceAll(old, val);
        }
        return out;
    }

    // Initialize Charts
    window.addEventListener('load', () => {
        // Find default province in data
        const provinces = Object.keys(dashboardData.prov_clusters);
        if (provinces.length > 0 && !provinces.includes(selectedProvince)) {
            selectedProvince = provinces[0];
        }

        initMapChart();
        initRadarChart();
        initSankeyChart();

        // Render initially
        switchDomain(activeDomain);
        selectProvince(selectedProvince);

        // Resize handler
        window.addEventListener('resize', () => {
            mapChart && mapChart.resize();
            radarChart && radarChart.resize();
            sankeyChart && sankeyChart.resize();
        });
    });

    // Theme Toggle
    function toggleTheme() {
        const body = document.body;
        const btn = document.querySelector('.theme-toggle-btn');
        const icon = document.getElementById('theme-icon');
        
        if (body.getAttribute('data-theme') === 'light') {
            body.removeAttribute('data-theme');
            activeTheme = 'dark';
            // Sun icon
            icon.innerHTML = '<path d="M12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,2A1,1 0 0,1 13,3V5A1,1 0 0,1 12,6A1,1 0 0,1 11,5V3A1,1 0 0,1 12,2M12,18A1,1 0 0,1 13,19V21A1,1 0 0,1 12,22A1,1 0 0,1 11,21V19A1,1 0 0,1 12,18M5.64,16.29L7.05,17.71L5.64,19.12L4.22,17.71L5.64,16.29M18.36,5.64L19.78,7.05L18.36,8.46L16.95,7.05L18.36,5.64M2,12A1,1 0 0,1 3,11H5A1,1 0 0,1 6,12A1,1 0 0,1 5,13H3A1,1 0 0,1 2,12M18,12A1,1 0 0,1 19,11H21A1,1 0 0,1 22,12A1,1 0 0,1 21,13H19A1,1 0 0,1 18,12M7.05,6.29L5.64,7.71L4.22,6.29L5.64,4.88L7.05,6.29M19.78,16.29L18.36,17.71L16.95,16.29L18.36,14.88L19.78,16.29Z"/>';
        } else {
            body.setAttribute('data-theme', 'light');
            activeTheme = 'light';
            // Moon icon
            icon.innerHTML = '<path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4Z"/>';
        }

        // Re-render charts with the new theme colors
        setTimeout(() => {
            updateChartsTheme();
        }, 100);
    }

    function updateChartsTheme() {
        if (!mapChart) return;
        
        // Update Map colors
        const visualMapPieces = [
            { value: 0, label: '类 0', color: getClusterColor(0) },
            { value: 1, label: '类 1', color: getClusterColor(1) },
            { value: 2, label: '类 2', color: getClusterColor(2) },
            { value: 3, label: '类 3', color: getClusterColor(3) }
        ];

        mapChart.setOption({
            visualMap: { pieces: visualMapPieces },
            series: [{
                itemStyle: {
                    borderColor: activeTheme === 'dark' ? '#334155' : '#e2e8f0',
                    areaColor: activeTheme === 'dark' ? '#1e293b' : '#f1f5f9'
                }
            }]
        });

        // Re-render Radar and Sankey
        renderRadarChart();
        renderSankeyChart();
        
        // Update legends
        renderCustomLegend();
    }

    // Map initialization
    function initMapChart() {
        mapChart = echarts.init(document.getElementById('map-chart'));
        echarts.registerMap('china', chinaGeoJSON);

        mapChart.on('click', (params) => {
            if (params.data && params.data.name) {
                selectProvince(params.data.name);
            }
        });
    }

    // Switch active clustering domain
    function switchDomain(domain) {
        activeDomain = domain;
        
        // Toggle tabs UI
        document.querySelectorAll('.domain-tabs .tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        const activeBtn = document.getElementById(`tab-${domain}`);
        if (activeBtn) activeBtn.classList.add('active');

        // Update map rendering
        renderMapData();
        
        // Update description box
        renderMetadataBox();

        // Update Cluster Composition Group List
        renderClusterComposition();

        // Update Radar
        renderRadarChart();

        // Highlight active domain cell in Details Card
        updateDetailDomainBadges();

        // Refresh metrics
        updateMetricsList();
    }

    // Populate Map with data
    function renderMapData() {
        if (!mapChart) return;

        const mapData = Object.values(dashboardData.prov_clusters).map(p => {
            const taskData = p.tasks[activeDomain];
            return {
                name: p.name,
                value: taskData.cluster,
                clusterLabel: taskData.cluster_label,
                summary: taskData.summary,
                adminCode: p.code
            };
        });

        const visualMapPieces = [
            { value: 0, label: '类 0', color: getClusterColor(0) },
            { value: 1, label: '类 1', color: getClusterColor(1) },
            { value: 2, label: '类 2', color: getClusterColor(2) },
            { value: 3, label: '类 3', color: getClusterColor(3) }
        ];

        const option = {
            tooltip: {
                trigger: 'item',
                backgroundColor: activeTheme === 'dark' ? '#1e293b' : '#ffffff',
                borderColor: activeTheme === 'dark' ? '#334155' : '#cbd5e1',
                textStyle: {
                    color: activeTheme === 'dark' ? '#f8fafc' : '#0f172a',
                    fontSize: 12
                },
                formatter: function (params) {
                    if (!params.data) return params.name;
                    const d = params.data;
                    const color = getClusterColor(d.value);
                    return `<div style="font-weight:600; font-size:14px; margin-bottom: 6px;">${d.name}</div>` +
                           `<div style="display:flex; align-items:center; gap:6px; margin-bottom: 8px;">` +
                           `<span style="background-color:${color}; width:8px; height:8px; border-radius:50%; display:inline-block;"></span>` +
                           `<b style="color:${color}">类 ${d.value}: ${d.clusterLabel}</b>` +
                           `</div>` +
                           `<div style="font-size:11px; color:var(--text-secondary); max-width:260px; white-space:normal; line-height: 1.5;">` +
                           `${d.summary.replaceAll('；', '<br/>')}` +
                           `</div>`;
                }
            },
            visualMap: {
                type: 'piecewise',
                pieces: visualMapPieces,
                show: false
            },
            series: [
                {
                    name: '聚类结果',
                    type: 'map',
                    map: 'china',
                    roam: true,
                    zoom: 1.15,
                    center: [104.2, 35.8],
                    label: {
                        show: false,
                        emphasis: {
                            show: true,
                            color: activeTheme === 'dark' ? '#f8fafc' : '#0f172a',
                            fontSize: 11
                        }
                    },
                    itemStyle: {
                        borderColor: activeTheme === 'dark' ? '#334155' : '#cbd5e1',
                        borderWidth: 0.8,
                        areaColor: activeTheme === 'dark' ? '#1e293b' : '#f1f5f9'
                    },
                    emphasis: {
                        itemStyle: {
                            areaColor: activeTheme === 'dark' ? '#475569' : '#e2e8f0',
                            shadowBlur: 8,
                            shadowColor: 'rgba(0,0,0,0.15)'
                        }
                    },
                    data: mapData
                }
            ]
        };

        mapChart.setOption(option, true);
        renderCustomLegend();
    }

    // Render Custom Map Legend Overlay
    function renderCustomLegend() {
        const legendDiv = document.getElementById('map-legend');
        legendDiv.innerHTML = '';
        
        // Count provinces in each cluster
        const counts = { 0: 0, 1: 0, 2: 0, 3: 0 };
        Object.values(dashboardData.prov_clusters).forEach(p => {
            const c = p.tasks[activeDomain].cluster;
            counts[c]++;
        });

        // Find unique cluster labels
        const labels = {};
        Object.values(dashboardData.prov_clusters).forEach(p => {
            const task = p.tasks[activeDomain];
            labels[task.cluster] = task.cluster_label;
        });

        for (let i = 0; i < 4; i++) {
            const color = getClusterColor(i);
            const label = labels[i] || '未命聚类';
            const count = counts[i] || 0;

            const item = document.createElement('div');
            item.className = 'legend-item';
            item.onclick = () => {
                // Focus on cluster in radar
                highlightClusterRadar(i);
            };
            item.innerHTML = `
                <span class="legend-color" style="background-color: ${color}"></span>
                <span class="legend-label">类 ${i}: ${label}</span>
                <span class="legend-count">(${count}省)</span>
            `;
            legendDiv.appendChild(item);
        }
    }

    // Render Metadata Info Card
    function renderMetadataBox() {
        const meta = dashboardData.task_metadata[activeDomain];
        const box = document.getElementById('task-metadata-box');
        box.innerHTML = `
            <p><strong>聚类指标域：</strong>${meta.name}</p>
            <p><strong>聚类模型参数：</strong>K-means (固定 K = ${meta.k})，分析时间区间: ${meta.time_range}</p>
            <p><strong>输入特征构成：</strong>${meta.features_desc}</p>
            <p style="font-size: 11px; color: var(--text-secondary); margin-top: 4px; border-top: 1px solid var(--border-color); padding-top: 6px;">
                * 聚类特征均在时间序列上计算了最新水平值、均值值、首尾变化量、变化率、线性拟合斜率、标准差及变异系数，用以全面捕捉省际的【水平 + 趋势 + 波动】多维特征。
            </p>
        `;
    }

    // Select Province Globally
    function selectProvince(provinceName) {
        if (!provinceName) return;
        selectedProvince = provinceName;

        const pData = dashboardData.prov_clusters[provinceName];
        if (!pData) return;

        // Highlight map feature
        if (mapChart) {
            mapChart.dispatchAction({
                type: 'mapSelect',
                name: provinceName
            });
        }

        // Update Detail Panel Header
        document.getElementById('detail-province-name').innerText = pData.name;
        document.getElementById('detail-province-code').innerText = `行政区划代码: ${pData.code}`;

        // Update the 4 Domain cards in details view
        updateDetailDomainBadges();

        // Update metrics list for active domain
        updateMetricsList();

        // Highlight badges in list
        document.querySelectorAll('.prov-badge').forEach(badge => {
            if (badge.innerText === provinceName) {
                badge.classList.add('active');
            } else {
                badge.classList.remove('active');
            }
        });
    }

    // Update the 4 domain badges summary in Detail panel
    function updateDetailDomainBadges() {
        const pData = dashboardData.prov_clusters[selectedProvince];
        if (!pData) return;

        const container = document.getElementById('detail-domain-badges');
        container.innerHTML = '';

        const domainLabels = {
            'economy_clustering': '经济水平与物价',
            'population_clustering': '人口结构特征',
            'food_grain_clustering': '口粮消费特征',
            'feed_grain_clustering': '饲料粮消费特征'
        };

        Object.keys(domainLabels).forEach(dom => {
            const task = pData.tasks[dom];
            const isActive = dom === activeDomain;
            const color = getClusterColor(task.cluster);
            const bg = getClusterBg(task.cluster);

            const cell = document.createElement('div');
            cell.className = `domain-cell ${isActive ? 'active-domain-border' : ''}`;
            cell.onclick = () => switchDomain(dom);

            cell.innerHTML = `
                <div class="domain-cell-title">${domainLabels[dom]}</div>
                <div class="domain-cell-value" style="color: ${color}">
                    <span class="circle-dot" style="background-color: ${color}"></span>
                    类 ${task.cluster}: ${task.cluster_label}
                </div>
            `;
            container.appendChild(cell);
        });
    }

    // Helper: Formatter for float values
    function formatVal(val, key) {
        if (val === undefined || val === null) return '无数据';
        
        if (key.includes('占比') || key.includes('率')) {
            // If it is already percent scale (e.g. CPI change rate or urbanization)
            if (Math.abs(val) <= 1.0) {
                return (val * 100).toFixed(2) + '%';
            }
            return val.toFixed(2) + '%';
        }
        if (key.includes('指数') || key.includes('变异系数')) {
            return val.toFixed(4);
        }
        if (key.includes('斜率') || key.includes('量')) {
            return (val > 0 ? '+' : '') + val.toFixed(2);
        }
        return val.toFixed(2);
    }

    // Update metrics list for active province
    function updateMetricsList() {
        const container = document.getElementById('detail-metrics-list');
        container.innerHTML = '';

        const pData = dashboardData.prov_clusters[selectedProvince];
        if (!pData) return;

        const taskData = pData.tasks[activeDomain];
        const radFeats = dashboardData.radar_features[activeDomain];
        const natAvgs = dashboardData.national_averages[activeDomain];
        const ranges = dashboardData.feature_ranges[activeDomain];

        radFeats.forEach(f => {
            const featKey = f[0];
            const featLabel = f[1];
            
            const rawVal = taskData.metrics[featKey];
            const avgVal = natAvgs[featKey];
            const range = ranges[featKey];

            // Compute percentages for progress bar
            // Normalization to [0, 100] for progress bar filling
            const span = range.max - range.min || 1;
            const fillPct = Math.max(0, Math.min(100, ((rawVal - range.min) / span) * 100));
            const avgPct = Math.max(0, Math.min(100, ((avgVal - range.min) / span) * 100));

            const mItem = document.createElement('div');
            mItem.className = 'metric-item';

            mItem.innerHTML = `
                <div class="metric-header">
                    <span class="metric-title">${featLabel}</span>
                    <span class="metric-value">${formatVal(rawVal, featKey)}</span>
                </div>
                <div class="metric-bar-bg">
                    <div class="metric-bar-fill" style="width: ${fillPct}%; background-color: ${getClusterColor(taskData.cluster)}"></div>
                    <div class="metric-marker-avg" style="left: ${avgPct}%" title="全国平均: ${formatVal(avgVal, featKey)}"></div>
                </div>
                <div class="metric-comparison-text">
                    <span>最小值: ${formatVal(range.min, featKey)}</span>
                    <span style="color:#ef4444;">红线: 全国均值 (${formatVal(avgVal, featKey)})</span>
                    <span>最大值: ${formatVal(range.max, featKey)}</span>
                </div>
            `;
            container.appendChild(mItem);
        });
    }

    // Radar Chart initialization and rendering
    function initRadarChart() {
        radarChart = echarts.init(document.getElementById('radar-chart'));
    }

    function renderRadarChart() {
        if (!radarChart) return;

        const task = activeDomain;
        const radFeats = dashboardData.radar_features[task];
        const ranges = dashboardData.feature_ranges[task];
        const centers = dashboardData.cluster_centers[task];

        // Prepare indicators
        const indicators = radFeats.map(f => {
            return { name: f[1], max: 1, min: 0 };
        });

        // Get label descriptions
        const labels = {};
        Object.values(dashboardData.prov_clusters).forEach(p => {
            const t = p.tasks[task];
            labels[t.cluster] = t.cluster_label;
        });

        // Prepare data series
        const seriesData = [];
        for (let cid = 0; cid < 4; cid++) {
            const rawCenter = centers[cid];
            const normValues = radFeats.map(f => {
                const fKey = f[0];
                const r = ranges[fKey];
                const span = r.max - r.min || 1;
                return (rawCenter[fKey] - r.min) / span;
            });

            seriesData.push({
                value: normValues,
                name: `类 ${cid}: ${labels[cid] || '聚类'}`,
                clusterId: cid,
                itemStyle: { color: getClusterColor(cid) },
                lineStyle: { width: cid === 0 ? 3 : 2, type: 'solid' }, // highlight cluster 0 default
                areaStyle: { color: getClusterBg(cid), opacity: 0.1 }
            });
        }

        const option = {
            tooltip: {
                trigger: 'item',
                backgroundColor: activeTheme === 'dark' ? '#1e293b' : '#ffffff',
                borderColor: activeTheme === 'dark' ? '#334155' : '#cbd5e1',
                textStyle: {
                    color: activeTheme === 'dark' ? '#f8fafc' : '#0f172a',
                    fontSize: 11
                },
                formatter: function (params) {
                    const cid = params.data.clusterId;
                    const rawCenter = centers[cid];
                    let html = `<div style="font-weight:600; font-size:13px; margin-bottom:6px; color:${getClusterColor(cid)}">类 ${cid}: ${labels[cid]} (聚类中心)</div>`;
                    radFeats.forEach(f => {
                        const fKey = f[0];
                        const displayVal = formatVal(rawCenter[fKey], fKey);
                        html += `<div style="display:flex; justify-content:space-between; gap:20px; font-size:11px; margin-bottom:2px;">` +
                                `<span style="color:var(--text-secondary)">${f[1]}</span>` +
                                `<b>${displayVal}</b>` +
                                `</div>`;
                    });
                    return html;
                }
            },
            radar: {
                indicator: indicators,
                shape: 'polygon',
                splitNumber: 4,
                axisName: {
                    color: activeTheme === 'dark' ? '#94a3b8' : '#475569',
                    fontSize: 10,
                    fontFamily: 'Noto Sans SC'
                },
                splitLine: {
                    lineStyle: {
                        color: activeTheme === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)'
                    }
                },
                splitArea: {
                    show: false
                },
                axisLine: {
                    lineStyle: {
                        color: activeTheme === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)'
                    }
                }
            },
            series: [
                {
                    type: 'radar',
                    data: seriesData
                }
            ]
        };

        radarChart.setOption(option, true);
    }

    // Highlight one specific cluster line on Radar Chart
    function highlightClusterRadar(clusterId) {
        if (!radarChart) return;
        const option = radarChart.getOption();
        
        // Loop through and increase thickness of selected cluster line
        option.series[0].data.forEach(item => {
            if (item.clusterId === clusterId) {
                item.lineStyle.width = 4;
                item.areaStyle.opacity = 0.35;
            } else {
                item.lineStyle.width = 1.5;
                item.areaStyle.opacity = 0.05;
            }
        });
        
        radarChart.setOption(option);
    }

    // Switch right panel analysis tab (Radar vs List)
    function switchAnalysisTab(tab) {
        activeAnalysisTab = tab;
        
        document.getElementById('tab-head-radar').classList.toggle('active', tab === 'radar');
        document.getElementById('tab-head-list').classList.toggle('active', tab === 'list');

        document.getElementById('analysis-tab-radar').classList.toggle('active', tab === 'radar');
        document.getElementById('analysis-tab-list').classList.toggle('active', tab === 'list');

        if (tab === 'radar' && radarChart) {
            setTimeout(() => radarChart.resize(), 50);
        }
    }

    // Populate Right Panel Group List
    function renderClusterComposition() {
        const container = document.getElementById('cluster-provinces-list');
        container.innerHTML = '';

        // Group provinces by cluster
        const groups = { 0: [], 1: [], 2: [], 3: [] };
        Object.values(dashboardData.prov_clusters).forEach(p => {
            const taskData = p.tasks[activeDomain];
            groups[taskData.cluster].push(p.name);
        });

        // Get label descriptions
        const labels = {};
        Object.values(dashboardData.prov_clusters).forEach(p => {
            const t = p.tasks[activeDomain];
            labels[t.cluster] = t.cluster_label;
        });

        for (let i = 0; i < 4; i++) {
            const color = getClusterColor(i);
            const label = labels[i] || '未分配';
            const provs = groups[i].sort();

            const groupDiv = document.createElement('div');
            groupDiv.className = 'cluster-group';

            const badgeContainer = document.createElement('div');
            badgeContainer.className = 'provinces-badges-container';

            provs.forEach(prov => {
                const b = document.createElement('span');
                b.className = `prov-badge ${prov === selectedProvince ? 'active' : ''}`;
                b.innerText = prov;
                b.onclick = () => selectProvince(prov);
                badgeContainer.appendChild(b);
            });

            groupDiv.innerHTML = `
                <div class="cluster-group-title" style="color: ${color}">
                    <span class="circle-dot" style="background-color: ${color}"></span>
                    类 ${i}: ${label} (${provs.length}省)
                </div>
            `;
            groupDiv.appendChild(badgeContainer);
            container.appendChild(groupDiv);
        }
    }

    // Sankey Chart initialization and rendering
    function initSankeyChart() {
        sankeyChart = echarts.init(document.getElementById('sankey-chart'));
    }

    function renderSankeyChart() {
        if (!sankeyChart) return;

        // Custom styling for Sankey nodes
        const nodes = dashboardData.sankey.nodes.map(n => {
            // Assign colors to nodes based on cluster ID in name
            let color = '#ccc';
            if (n.name.includes('类0')) color = getClusterColor(0);
            if (n.name.includes('类1')) color = getClusterColor(1);
            if (n.name.includes('类2')) color = getClusterColor(2);
            if (n.name.includes('类3')) color = getClusterColor(3);

            return {
                name: n.name,
                itemStyle: { color: color }
            };
        });

        const links = dashboardData.sankey.links.map(l => {
            return {
                source: l.source,
                target: l.target,
                value: l.value,
                provinces: l.provinces
            };
        });

        const option = {
            tooltip: {
                trigger: 'item',
                backgroundColor: activeTheme === 'dark' ? '#1e293b' : '#ffffff',
                borderColor: activeTheme === 'dark' ? '#334155' : '#cbd5e1',
                textStyle: {
                    color: activeTheme === 'dark' ? '#f8fafc' : '#0f172a',
                    fontSize: 12
                },
                formatter: function (params) {
                    if (params.dataType === 'edge') {
                        const provs = params.data.provinces || [];
                        return `<div style="font-weight:600; font-size:13px; margin-bottom:6px;">流转路径分析</div>` +
                               `<span style="color:var(--text-secondary)">源节点:</span> <b>${params.data.source}</b><br/>` +
                               `<span style="color:var(--text-secondary)">目标节点:</span> <b>${params.data.target}</b><br/>` +
                               `<div style="margin-top:8px; border-top:1px solid var(--border-color); padding-top:6px;">` +
                               `<b>流动省份 (${provs.length}个):</b><br/>` +
                               `<span style="color:${getClusterColor(0)}">${provs.join(', ')}</span>` +
                               `</div>`;
                    } else {
                        // Node tooltip
                        return `<b>${params.name}</b>`;
                    }
                }
            },
            series: [
                {
                    type: 'sankey',
                    data: nodes,
                    links: links,
                    emphasis: {
                        focus: 'adjacency'
                    },
                    nodeAlign: 'justify',
                    lineStyle: {
                        color: 'gradient',
                        curveness: 0.5,
                        opacity: activeTheme === 'dark' ? 0.25 : 0.35
                    },
                    label: {
                        color: activeTheme === 'dark' ? '#f8fafc' : '#0f172a',
                        fontSize: 10,
                        fontFamily: 'Noto Sans SC',
                        position: 'right'
                    }
                }
            ]
        };

        sankeyChart.setOption(option, true);
    }

    // Search input handler
    function handleSearch() {
        const query = document.getElementById('province-search').value.trim();
        if (!query) return;

        const normalizedQuery = normalizeName(query);
        const provinces = Object.keys(dashboardData.prov_clusters);

        // Find exact match
        let match = provinces.find(p => normalizeName(p) === normalizedQuery);
        
        // Find partial match if no exact match
        if (!match) {
            match = provinces.find(p => normalizeName(p).includes(normalizedQuery) || normalizedQuery.includes(normalizeName(p)));
        }

        if (match) {
            selectProvince(match);
        }
    }
</script>
</body>
</html>
"""

# Inject data into template
html_content = html_template.replace("//DATA_PLACEHOLDER//", data_js_content)

# Write file
output_path = ROOT / "聚类结果可视化.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Successfully generated HTML dashboard at: {output_path}")
