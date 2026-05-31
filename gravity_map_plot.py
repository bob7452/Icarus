from pathlib import Path
import pandas as pd
import numpy as np
import json
import os
import time
import warnings
import cudf
import cugraph

import subprocess
import shutil
from datetime import datetime

warnings.filterwarnings('ignore')

# =========================================================
# 🎛️ 核心篩選與視覺化參數控制面板 (可依需求自由調整)
# =========================================================
RANK_THRESHOLD = 50.0         # 候選名單門檻：只採納 rank > 此分數的強勢股
CORR_EDGE_THRESHOLD = 0.55   # 連線相關度門檻：大於此數值才建立引力連線 (調高可讓畫面更清爽)
TOP_GALAXY_COUNT = 8          # 最終網頁上最多顯示的前幾大核心星系

def setup_environment(dir_name="solar_system_test"):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    print(f"📁 Output directory verified/created: ./{dir_name}/")
    return dir_name

def load_all_candles_data(json_path, keep_tickers):
    """
    【白名單機制】只載入在 keep_tickers 集合內的股票 K 線資料，阻斷垃圾資料
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        candles_data = json.load(f)
        
    close_prices = {}
    
    # 只允許在白名單內的股票進入系統
    target_tickers = [t for t in candles_data.keys() if t in keep_tickers]
    print(f"   -> Loading {len(target_tickers)} core whitelisted stocks.")
    
    for ticker in target_tickers:
        timestamps = candles_data[ticker].get('timestamps', [])
        closes = candles_data[ticker].get('closes', [])
        if len(timestamps) > 0 and len(closes) > 0:
            idx = pd.to_datetime(timestamps, unit='s')
            close_prices[ticker] = pd.Series(closes, index=idx)
                
    price_df = pd.DataFrame(close_prices)
    price_df.sort_index(inplace=True)
    price_df.ffill(inplace=True)
    return price_df

# =========================================================
# 🔍 新增：搜尋與高亮功能注入腳本
# =========================================================
def inject_search_feature(html_filepath):
    """
    在 Pyecharts 產生的 HTML 檔案中注入懸浮搜尋框與 ECharts 互動 JS 腳本。
    """
    with open(html_filepath, 'r', encoding='utf-8') as f:
        html_content = f.read()

    search_html = """
    <div style="position: fixed; top: 20px; right: 30px; z-index: 9999; background: rgba(10, 15, 25, 0.85); padding: 15px; border-radius: 8px; border: 1px solid #333; box-shadow: 0 4px 15px rgba(0,0,0,0.7); backdrop-filter: blur(4px);">
        <div style="color: #ccc; margin-bottom: 8px; font-family: sans-serif; font-size: 13px; font-weight: bold;">🌌 搜尋星系節點</div>
        <input type="text" id="nodeSearch" placeholder="輸入代碼 (例: NVDA)"
               style="padding: 8px; font-size: 14px; text-transform: uppercase; border: 1px solid #555; border-radius: 4px; background: #111; color: #fff; width: 160px; outline: none;"
               onkeydown="if(event.keyCode==13) highlightSymbol()">
        <button onclick="highlightSymbol()" style="padding: 8px 12px; font-size: 14px; cursor: pointer; background: #1890ff; color: white; border: none; border-radius: 4px; margin-left: 5px; transition: 0.2s;">搜尋 / 標亮</button>
        <button onclick="resetHighlight()" style="padding: 8px 12px; font-size: 14px; cursor: pointer; background: #444; color: white; border: none; border-radius: 4px; margin-left: 5px; transition: 0.2s;">重置</button>
    </div>

    <script>
    // 取得畫面上所有的 ECharts 實例 (Tab 會產生多個圖表)
    function getEchartsInstances() {
        var divs = document.getElementsByTagName('div');
        var charts = [];
        for (var i = 0; i < divs.length; i++) {
            if (typeof echarts !== 'undefined') {
                var chart = echarts.getInstanceByDom(divs[i]);
                if (chart) charts.push(chart);
            }
        }
        return charts;
    }

    function highlightSymbol() {
        var symbol = document.getElementById('nodeSearch').value.toUpperCase().trim();
        if (!symbol) return;

        var charts = getEchartsInstances();
        charts.forEach(function(chart) {
            var option = chart.getOption();
            var series = option.series;
            if (!series || series.length === 0) return;

            // 取得當前圖表的節點與連線
            var nodes = series[0].data || series[0].nodes;
            var links = series[0].links || series[0].edges;
            if (!nodes) return;

            // 尋找目標節點
            var targetName = "";
            for (var i = 0; i < nodes.length; i++) {
                if (nodes[i].name && nodes[i].name.toUpperCase() === symbol) {
                    targetName = nodes[i].name;
                    break;
                }
            }

            if (targetName !== "") {
                // 找出所有與該節點相連的鄰居節點
                var connectedNames = [targetName];
                if (links) {
                    for (var i = 0; i < links.length; i++) {
                        if (links[i].source === targetName) connectedNames.push(links[i].target);
                        if (links[i].target === targetName) connectedNames.push(links[i].source);
                    }
                }

                // 1. 取消畫布上其他高亮狀態
                chart.dispatchAction({ type: 'downplay' });

                // 2. 高亮目標節點與其鄰居節點
                chart.dispatchAction({
                    type: 'highlight',
                    seriesIndex: 0,
                    name: connectedNames
                });

                // 3. 彈出該目標節點的 Tooltip
                chart.dispatchAction({
                    type: 'showTip',
                    seriesIndex: 0,
                    name: targetName
                });
            } else {
                // 若找不到則解除高亮
                chart.dispatchAction({ type: 'downplay' });
                chart.dispatchAction({ type: 'hideTip' });
            }
        });
    }

    function resetHighlight() {
        document.getElementById('nodeSearch').value = '';
        var charts = getEchartsInstances();
        charts.forEach(function(chart) {
            chart.dispatchAction({ type: 'downplay' });
            chart.dispatchAction({ type: 'hideTip' });
        });
    }
    </script>
    """

    if "</body>" in html_content:
        html_content = html_content.replace("</body>", f"{search_html}\n</body>")
    else:
        html_content += search_html

    with open(html_filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)


def plot_interactive_html(cpu_edges_df, result_df, output_path):
    print("6. [CPU] Generating Pyecharts Galaxy Molecular Tab Map...")

    try:
        from pyecharts import options as opts
        from pyecharts.charts import Graph, Tab
    except ImportError:
        print("❌ pyecharts 未安裝。請先執行: pip install pyecharts")
        return

    top_clusters = result_df['Cluster_ID'].value_counts().head(TOP_GALAXY_COUNT).index.tolist()
    if not top_clusters:
        print("⚠️ 沒有找到符合條件的星系群組合。")
        return

    tab = Tab()

    for cluster in top_clusters:
        cluster_nodes_df = result_df[result_df['Cluster_ID'] == cluster]
        valid_tickers = cluster_nodes_df['Ticker'].tolist()

        # 篩選屬於該星系內部的連線
        cluster_edges = cpu_edges_df[
            (cpu_edges_df['source'].isin(valid_tickers)) &
            (cpu_edges_df['destination'].isin(valid_tickers)) &
            (cpu_edges_df['weight'] >= CORR_EDGE_THRESHOLD) 
        ]

        nodes = []
        for _, row in cluster_nodes_df.iterrows():
            # 強制轉型，防止 JS 解析 Numpy 型態時崩潰
            node_name = str(row['Ticker'])
            role = str(row['Role'])
            rs_score = float(max(0.0, row['rank']))
            industry = str(row['Industry'])

            # 視覺分類邏輯：針對不同角色與超級強勢股給予不同顏色與大小
            if rs_score >= 90.0:
                color = '#ff9900'  # 90分以上頂級強勢股：耀眼橘金光
                size = int(55 + rs_score * 0.1)
                category_idx = 0
                display_role = f"👑 大哥級核心 ({role})"
            elif role == '1_Star':
                color = '#ff4d4f'  # 星系引力中心：紅色
                size = int(45 + rs_score * 0.1)
                category_idx = 1
                display_role = "核心恆星 (Star)"
            elif role == '2_Planet':
                color = '#1890ff'  # 高相關性骨幹：藍色
                size = int(25 + rs_score * 0.1)
                category_idx = 2
                display_role = "骨幹行星 (Planet)"
            else:
                color = '#73d13d'  # 連帶跟漲衛星：綠色
                size = int(14 + rs_score * 0.1)
                category_idx = 3
                display_role = "跟隨衛星 (Satellite)"

            tooltip = f"""
            <b>{node_name}</b><br/>
            角色特徵: {display_role}<br/>
            所屬產業: {industry}<br/>
            RS Alpha 分數: {rs_score:.2f}
            """

            nodes.append(
                opts.GraphNode(
                    name=node_name,
                    symbol_size=size,
                    category=category_idx,
                    tooltip_opts=opts.TooltipOpts(formatter=tooltip),
                    itemstyle_opts=opts.ItemStyleOpts(color=color)
                )
            )

        edges = []
        for _, row in cluster_edges.iterrows():
            edges.append(
                opts.GraphLink(
                    source=str(row['source']),
                    target=str(row['destination']),
                    value=float(round(row['weight'], 2))
                )
            )

        categories = [
            opts.GraphCategory(name="Rank >= 90 大哥"),
            opts.GraphCategory(name="星系恆星 (Star)"),
            opts.GraphCategory(name="骨幹行星 (Planet)"),
            opts.GraphCategory(name="跟隨衛星 (Satellite)"),
        ]

        # 建立力導向圖，使用 width="95vw" 避免 Tab 切換時畫布縮成 0
        g = (
            Graph(init_opts=opts.InitOpts(width="95vw", height="850px", theme="dark", bg_color="#02050a"))
            .add(
                "",
                nodes=nodes,
                links=edges,
                categories=categories,
                layout="force",            # 啟用物理分子引擎
                is_roam=True,              # 允許縮放與畫布拖拽
                is_draggable=True,         # 允許滑鼠抓取單個節點
                is_focusnode=True,         # 滑鼠懸停時高亮相連節點與線條
                repulsion=1000,            # 斥力參數，數值越大分子拉得越開
                edge_length=[60, 180],     # 線條彈性長度
                gravity=0.15,              # 中心收束引力
                linestyle_opts=opts.LineStyleOpts(width=1.5, curve=0.15, opacity=0.5, color="source"),
                label_opts=opts.LabelOpts(
                    is_show=True, 
                    position="right", 
                    color="#ffffff",
                    font_size=11
                )
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title=f"🌌 {cluster} 分子結構圖 (門檻 Rank > {RANK_THRESHOLD})", 
                    pos_left="center", 
                    title_textstyle_opts=opts.TextStyleOpts(color="#ffffff", font_size=16)
                ),
                legend_opts=opts.LegendOpts(
                    is_show=True, 
                    pos_left="left", 
                    textstyle_opts=opts.TextStyleOpts(color="#ffffff")
                ),
                tooltip_opts=opts.TooltipOpts(is_show=True)
            )
        )
        
        tab.add(g, f"{cluster.replace('_', ' ')}")

    tab.render(output_path)
    print(f"✅ Galaxy Molecular Map (Tab View) saved to {output_path}")

    # =========================================================
    # 🔗 呼叫注入腳本，將搜尋功能加進剛產生的 HTML 中
    # =========================================================
    inject_search_feature(output_path)
    print("✅ Search and Highlight feature injected successfully!")


def analyze_convergence_gpu(rs_csv_path, candles_json_path, output_dir):
    start_time = time.time()
    print("1. [CPU] Reading RS Data and Generating Whitelist...")
    
    keep_tickers = set()
    rs_dict = {}
    ind_dict = {}
    
    if os.path.exists(rs_csv_path):
        rs_df = pd.read_csv(rs_csv_path)
        exclude_keywords = 'Bio|Medical|Drug|Health|Diagnostics|Banks Regional'
        bad_sector_mask = rs_df['industry_name'].str.contains(exclude_keywords, case=False, na=False)
        niche_industries = rs_df['industry_name'].value_counts()[lambda x: x < 3].index
        
        # 篩選出 乾淨的產業 + RS大於門檻 的超級名單 (白名單)
        valid_rs_df = rs_df[
            ~bad_sector_mask & 
            ~rs_df['industry_name'].isin(niche_industries) & 
            (rs_df['rank'] > RANK_THRESHOLD)
        ]
        
        # 將符合條件的股票名稱加入白名單集合
        keep_tickers = set(valid_rs_df['name'].tolist())
        rs_dict = dict(zip(valid_rs_df['name'], valid_rs_df['rank']))
        ind_dict = dict(zip(valid_rs_df['name'], valid_rs_df['industry_name']))
        
    print("2. [CPU] Reading Raw Candle Data...")
    pd_price_df = load_all_candles_data(candles_json_path, keep_tickers)
    
    if pd_price_df.empty or pd_price_df.shape[1] < 2:
        print("❌ 錯誤：經過過濾後剩餘股票過少，無法計算相關性。請調低 RANK_THRESHOLD。")
        return

    print("3. [GPU] Calculating returns and correlation...")
    gdf_corr = cudf.from_pandas(pd_price_df).pct_change().dropna().corr()
    gdf_corr['source'] = gdf_corr.index
    edges = gdf_corr.melt(id_vars=['source'], var_name='destination', value_name='weight')
    edges = edges[edges['source'] < edges['destination']]
    
    # 用較寬容的 0.5 去建立基礎連線網路，以便 cugraph 分群
    math_edges = edges[edges['weight'] >= 0.5]
    
    print("4. [GPU] Building network and computing Centrality...")
    G = cugraph.Graph(directed=False)
    G.from_cudf_edgelist(math_edges, source='source', destination='destination', edge_attr='weight')
    partitions, _ = cugraph.louvain(G)
    centrality = cugraph.eigenvector_centrality(G)
    
    print("5. [GPU -> CPU] Assigning Roles and Mapping RS Alpha...")
    cpu_results = partitions.merge(centrality, on='vertex').to_pandas()
    pd_corr = gdf_corr.to_pandas()
    cpu_edges_df = edges.to_pandas()
    
    results = []
    grouped = cpu_results.groupby('partition')
    for cluster_id, (partition_id, group) in enumerate(grouped):
        if len(group) < 3: continue  # 降維後小群組門檻放寬到 3 顆股票
        star_ticker = group.loc[group['eigenvector_centrality'].idxmax()]['vertex']
        
        for _, row in group.iterrows():
            ticker = row['vertex']
            cent_val = row['eigenvector_centrality']
            corr_with_star = pd_corr.loc[ticker, star_ticker] if ticker != star_ticker else 1.0
            
            role = "1_Star" if ticker == star_ticker else "2_Planet" if corr_with_star >= 0.7 else "3_Satellite"
            
            # 因為已經全盤白名單化，這裡取資料保證不會報錯或出現預設值 0.0
            rs_score = rs_dict[ticker]
            ind_display = ind_dict[ticker]
            
            results.append({
                "Cluster_ID": f"Galaxy_{cluster_id + 1}",
                "Ticker": ticker, "Role": role,
                "Corr_with_Star": round(corr_with_star, 4),
                "Centrality": round(cent_val, 4),
                "rank": round(rs_score, 4),
                "Industry": ind_display
            })
            
    if not results:
        print("⚠️ 過濾後的結果集為空，請確認資料與門檻設定。")
        return

    result_df = pd.DataFrame(results).sort_values(by=['Cluster_ID', 'Role', 'rank'], ascending=[True, True, False])
    plot_interactive_html(cpu_edges_df, result_df, os.path.join(output_dir, 'gravity_map_interactive.html'))
    print(f"✅ Total execution time: {time.time() - start_time:.2f} seconds")

def deploy_to_github(source_path, target_path):
    """
    使用 pathlib 將檔案複製並自動執行 git 指令進行部署
    """
    print("🚀 [Deploy] 開始同步到 GitHub...")
    
    src = Path(source_path)
    dst = Path(target_path)
    
    try:
        # 1. 確保目標資料夾存在 (如果不存在則建立)
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        # 2. 複製檔案
        shutil.copy2(src, dst)
        
        # 3. 定義 Git 目錄與日期
        target_dir = dst.parent
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        # 4. 執行 Git 指令
        # 使用 cwd 參數指定工作目錄，不需要頻繁切換 os.chdir
        git_cmd = ["git", "add", dst.name]
        subprocess.run(git_cmd, cwd=target_dir, check=True)
        
        commit_cmd = ["git", "commit", "-m", f"Update: {date_str}"]
        subprocess.run(commit_cmd, cwd=target_dir, check=True)
        
        push_cmd = ["git", "push"]
        subprocess.run(push_cmd, cwd=target_dir, check=True)
        
        print(f"✅ [Deploy] 成功！{date_str} 版本已推送至 GitHub。")
        
    except Exception as e:
        print(f"❌ [Deploy] 同步失敗: {e}")

if __name__ == "__main__":
    # json_file = Path("candles.json")

    # if not json_file.exists():
    #     print(f"❌ Error: Cannot find {json_file}")
    #     exit(1)

    # RS_REPORT_FOLDER = Path(__file__).parent / "rs_report"

    # try:
    #     rs_csv = next(RS_REPORT_FOLDER.glob("rs_model_*.csv"))
    # except StopIteration:
    #     print("❌ Error: No rs_model_*.csv found in rs_report/")
    #     exit(1)

    output_dir = setup_environment("solar_system_test")

    # analyze_convergence_gpu(
    #     str(rs_csv),
    #     str(json_file),
    #     output_dir,
    # )

    source_path = Path(output_dir) / 'gravity_map_interactive.html'
    target_path = Path(__file__).parents[1] / "galaxy-dashboard" /  'gravity_map_interactive.html'
    deploy_to_github(source_path=source_path,target_path=target_path)