import pandas as pd
import json
import os
import glob
from pathlib import Path
import subprocess
import shutil
from datetime import datetime

def find_latest_file(pattern='rs_model_*.csv'):
    search_paths = [pattern, f"rs_report/{pattern}"]
    list_of_files = []
    for p in search_paths:
        list_of_files.extend(glob.glob(p))
        
    if not list_of_files:
        raise FileNotFoundError(f"No matching CSV files found. Ensure rs_model_*.csv exists.")
        
    latest_file = max(list_of_files, key=os.path.getmtime)
    return latest_file

def process_data(input_file):
    print(f"[INFO] Loading raw data: {input_file} ...")
    df = pd.read_csv(input_file)

    print("[INFO] Calculating Momentum Acceleration Factor ...")
    df['season_rank'] = df['current_season_change'].rank(pct=True) * 100
    df['acceleration'] = df['season_rank'] - df['rank']

    df_clean = df.fillna(0)
    json_data = df_clean.to_json(orient='records', force_ascii=False)
    return json_data

def generate_html(json_data, output_html):
    print("[INFO] Generating Interactive Dashboard ...")
    
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Momentum Dashboard</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f0f2f5; margin: 0; padding: 20px; color: #333; }}
        
        .header {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }}
        .header h2 {{ margin-top: 0; color: #1a237e; border-bottom: 2px solid #f0f2f5; padding-bottom: 10px; }}
        
        .tab-container {{ display: flex; border-bottom: 2px solid #e9ecef; margin-bottom: 20px; }}
        .tab-btn {{ padding: 12px 24px; cursor: pointer; border: none; background: none; font-size: 16px; font-weight: 600; color: #6c757d; border-bottom: 3px solid transparent; transition: all 0.2s ease; outline: none; }}
        .tab-btn:hover {{ color: #1a237e; }}
        .tab-btn.active {{ color: #1a237e; border-bottom-color: #1a237e; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}

        .control-panel {{ display: flex; flex-wrap: wrap; gap: 20px; margin-top: 15px; background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #e9ecef; }}
        .control-group {{ display: flex; flex-direction: column; gap: 8px; flex: 1; min-width: 200px; }}
        .control-group label {{ font-weight: 600; font-size: 13px; color: #495057; display: flex; justify-content: space-between; align-items: center; }}
        .val-badge {{ background: #1a237e; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; }}
        .filter-badge {{ background: #e74c3c; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; }}
        
        input[type="range"] {{ width: 100%; cursor: pointer; }}
        input[type="text"] {{ padding: 8px 12px; border-radius: 4px; border: 1px solid #ced4da; font-size: 14px; outline: none; transition: border-color 0.2s; }}
        input[type="text"]:focus {{ border-color: #1a237e; box-shadow: 0 0 0 2px rgba(26,35,126,0.2); }}
        select, input[type="checkbox"] {{ cursor: pointer; padding: 8px; border-radius: 4px; border: 1px solid #ced4da; font-size: 14px; margin-right: 5px; }}
        
        .dashboard-grid {{ display: flex; flex-direction: column; gap: 20px; }}
        .row-top {{ display: flex; gap: 20px; height: 500px; }}
        .row-bottom {{ display: flex; gap: 20px; height: 350px; }}
        
        .card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); position: relative; }}
        .card-title {{ margin-top: 0; margin-bottom: 15px; font-size: 15px; color: #495057; border-bottom: 2px solid #f0f2f5; padding-bottom: 10px; font-weight: bold; }}
        
        .scatter-card {{ flex: 6; }}
        .table-card {{ flex: 4; overflow-y: auto; }}
        .hist-card {{ flex: 5; }}
        .bar-card {{ flex: 5; }}
        
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        th, td {{ padding: 10px 8px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ position: sticky; top: 0; background-color: #f8f9fa; z-index: 10; }}
        tr:hover {{ background-color: #f1f3f5; cursor: pointer; }}
        .highlight-row {{ background-color: #fff3cd !important; }}
        
        .raw-data-container {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); overflow-x: auto; max-height: 800px; }}
        .tooltip {{ position: absolute; background: rgba(255, 255, 255, 0.98); border: 1px solid #e9ecef; padding: 15px; border-radius: 8px; pointer-events: none; opacity: 0; box-shadow: 0 10px 20px rgba(0,0,0,0.1); font-size: 13px; z-index: 100; min-width: 220px; }}
        .axis-label {{ font-size: 12px; font-weight: bold; fill: #6c757d; }}
        
        .filter-list {{ display: flex; flex-direction: column; gap: 8px; margin-top: 10px; background: #fff; padding: 10px; border-radius: 6px; border: 1px solid #dee2e6; }}
        .filter-list label {{ font-weight: normal; cursor: pointer; display: flex; justify-content: flex-start; align-items: center; font-size: 13px; }}
    </style>
</head>
<body>

    <div class="header">
        <h2>Momentum Screener</h2>
        
        <div class="tab-container">
            <button class="tab-btn active" onclick="openTab('dashboard-tab')">Dashboard</button>
            <button class="tab-btn" onclick="openTab('rawdata-tab')">Raw Data</button>
        </div>

        <div class="control-panel">
            <div class="control-group" style="min-width: 150px;">
                <label>Search Ticker</label>
                <input type="text" id="searchInput" placeholder="e.g., TSLA, NVDA..." autocomplete="off">
            </div>
            
            <div class="control-group">
                <label>Q-Matrix X-Axis (Total Rank) <span class="val-badge" id="qxVal">50</span></label>
                <input type="range" id="qxSlider" min="0" max="100" value="50">
            </div>
            <div class="control-group">
                <label>Q-Matrix Y-Axis (Season Rank) <span class="val-badge" id="qyVal">50</span></label>
                <input type="range" id="qySlider" min="0" max="100" value="50">
            </div>
            
            <div class="control-group" style="background:#fff3cd; padding:10px; border-radius:6px; border:1px solid #ffeeba;">
                <label style="color:#856404;">Min Rank Filter <span class="filter-badge" id="minRankVal">0</span></label>
                <input type="range" id="minRankSlider" min="0" max="100" value="0">
            </div>

            <div class="control-group" style="min-width: 250px;">
                <label>View Selection</label>
                <select id="quadrantFilter">
                    <option value="All">All Quadrants</option>
                    <option value="Q1">Q1: Leaders</option>
                    <option value="Q2">Q2: Dark Horses</option>
                    <option value="Q3">Q3: Laggards</option>
                    <option value="Q4">Q4: Decelerating</option>
                </select>
                <div class="filter-list">
                    <label>
                        <input type="checkbox" id="maFilter"> MA Uptrend Only
                    </label>
                    <label>
                        <input type="checkbox" id="tenPercentFilter"> Close to High 10%
                    </label>
                    <label>
                        <input type="checkbox" id="breakoutFilter"> Breakout with Volume
                    </label>
                </div>
            </div>
        </div>
    </div>

    <div id="dashboard-tab" class="tab-content active">
        <div class="dashboard-grid">
            <div class="row-top">
                <div class="card scatter-card">
                    <h3 class="card-title">Dynamic Quadrant Matrix</h3>
                    <div id="scatterPlot" style="width:100%; height:calc(100% - 40px);"></div>
                </div>
                <div class="card table-card">
                    <h3 class="card-title">Actionable Watchlist (<span id="stockCount">0</span>)</h3>
                    <table id="dataTable">
                        <thead>
                            <tr>
                                <th>Ticker</th>
                                <th>Quadrant</th>
                                <th>Acc. Score</th>
                                <th>Vol(%)</th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>
            <div class="row-bottom">
                <div class="card hist-card">
                    <h3 class="card-title">Acceleration Distribution</h3>
                    <div id="histogramChart" style="width:100%; height:calc(100% - 40px);"></div>
                </div>
                <div class="card bar-card">
                    <h3 class="card-title">Industry Money Flow (Top 10 Accelerating)</h3>
                    <div id="barChart" style="width:100%; height:calc(100% - 40px);"></div>
                </div>
            </div>
        </div>
    </div>

    <div id="rawdata-tab" class="tab-content">
        <div class="raw-data-container">
            <h3 class="card-title">Complete Raw Dataset (<span id="rawStockCount">0</span>)</h3>
            <table id="rawDataTable">
                <thead>
                    <tr id="rawTableHeader"></tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
    </div>
    
    <div class="tooltip" id="tooltip"></div>

    <script>
        const rawData = {json_data};
        const colors = {{'Q1': '#2ecc71', 'Q2': '#e74c3c', 'Q3': '#95a5a6', 'Q4': '#f39c12'}};

        function openTab(tabId) {{
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            event.currentTarget.classList.add('active');
        }}

        const scMargin = {{top: 20, right: 30, bottom: 40, left: 50}};
        const scElem = document.getElementById('scatterPlot');
        const scW = scElem.clientWidth - scMargin.left - scMargin.right;
        const scH = scElem.clientHeight - scMargin.top - scMargin.bottom;
        
        const scSvg = d3.select("#scatterPlot").append("svg")
            .attr("width", scW + scMargin.left + scMargin.right)
            .attr("height", scH + scMargin.top + scMargin.bottom)
            .append("g").attr("transform", `translate(${{scMargin.left}},${{scMargin.top}})`);

        const scX = d3.scaleLinear().domain([0, 100]).range([0, scW]);
        const scY = d3.scaleLinear().domain([0, 100]).range([scH, 0]);

        scSvg.append("g").attr("transform", `translate(0,${{scH}})`).call(d3.axisBottom(scX))
            .append("text").attr("class", "axis-label").attr("x", scW/2).attr("y", 35).style("text-anchor", "middle").text("Total Rank (X-Axis)");
        scSvg.append("g").call(d3.axisLeft(scY))
            .append("text").attr("class", "axis-label").attr("transform", "rotate(-90)").attr("x", -scH/2).attr("y", -35).style("text-anchor", "middle").text("Season Rank (Y-Axis)");

        const vLine = scSvg.append("line").attr("y1", 0).attr("y2", scH).attr("stroke", "#e74c3c").attr("stroke-dasharray", "5,5").attr("stroke-width", 2);
        const hLine = scSvg.append("line").attr("x1", 0).attr("x2", scW).attr("stroke", "#e74c3c").attr("stroke-dasharray", "5,5").attr("stroke-width", 2);
        
        const qTexts = [
            scSvg.append("text").attr("fill", "#ccc").attr("font-size", "24px").attr("font-weight", "bold").attr("opacity", 0.3).text("Q1"),
            scSvg.append("text").attr("fill", "#ccc").attr("font-size", "24px").attr("font-weight", "bold").attr("opacity", 0.3).text("Q2"),
            scSvg.append("text").attr("fill", "#ccc").attr("font-size", "24px").attr("font-weight", "bold").attr("opacity", 0.3).text("Q3"),
            scSvg.append("text").attr("fill", "#ccc").attr("font-size", "24px").attr("font-weight", "bold").attr("opacity", 0.3).text("Q4")
        ];

        const dotsGroup = scSvg.append("g");
        const tooltip = d3.select("#tooltip");

        const hMargin = {{top: 20, right: 30, bottom: 40, left: 40}};
        const hElem = document.getElementById('histogramChart');
        const hW = hElem.clientWidth - hMargin.left - hMargin.right;
        const hH = hElem.clientHeight - hMargin.top - hMargin.bottom;
        
        const hSvg = d3.select("#histogramChart").append("svg")
            .attr("width", hW + hMargin.left + hMargin.right).attr("height", hH + hMargin.top + hMargin.bottom)
            .append("g").attr("transform", `translate(${{hMargin.left}},${{hMargin.top}})`);
            
        const hX = d3.scaleLinear().domain([-100, 100]).range([0, hW]);
        const hY = d3.scaleLinear().range([hH, 0]);
        
        const hXAxis = hSvg.append("g").attr("transform", `translate(0,${{hH}})`);
        const hYAxis = hSvg.append("g");
        hSvg.append("text").attr("class", "axis-label").attr("x", hW/2).attr("y", hH + 35).style("text-anchor", "middle").text("Acceleration Score");
        hSvg.append("line").attr("x1", hX(0)).attr("x2", hX(0)).attr("y1", 0).attr("y2", hH).attr("stroke", "#e74c3c").attr("stroke-dasharray", "4,4");

        const bMargin = {{top: 20, right: 30, bottom: 40, left: 160}};
        const bElem = document.getElementById('barChart');
        const bW = bElem.clientWidth - bMargin.left - bMargin.right;
        const bH = bElem.clientHeight - bMargin.top - bMargin.bottom;
        
        const bSvg = d3.select("#barChart").append("svg")
            .attr("width", bW + bMargin.left + bMargin.right).attr("height", bH + bMargin.top + bMargin.bottom)
            .append("g").attr("transform", `translate(${{bMargin.left}},${{bMargin.top}})`);
            
        const bX = d3.scaleLinear().range([0, bW]);
        const bY = d3.scaleBand().range([0, bH]).padding(0.2);
        
        const bXAxis = bSvg.append("g").attr("transform", `translate(0,${{bH}})`);
        const bYAxis = bSvg.append("g");
        bSvg.append("text").attr("class", "axis-label").attr("x", bW/2).attr("y", bH + 35).style("text-anchor", "middle").text("Avg. Acceleration Score");

        function initRawDataTable() {{
            if (rawData.length === 0) return;
            const keys = Object.keys(rawData[0]);
            const thead = d3.select("#rawTableHeader");
            thead.selectAll("th").data(keys).enter().append("th").text(d => d);
        }}
        initRawDataTable();

        function getDynamicQuadrant(d, qx, qy) {{
            if (d.rank >= qx && d.season_rank >= qy) return 'Q1';
            if (d.rank < qx && d.season_rank >= qy) return 'Q2';
            if (d.rank < qx && d.season_rank < qy) return 'Q3';
            return 'Q4';
        }}

        function isTrue(val) {{
            return val === true || val === 1 || val === "1" || val === "true" || val === "True";
        }}

        function update() {{
            const qX = +d3.select("#qxSlider").node().value;
            const qY = +d3.select("#qySlider").node().value;
            const minRank = +d3.select("#minRankSlider").node().value;
            const selectedQ = d3.select("#quadrantFilter").node().value;
            
            const needsMA = d3.select("#maFilter").node().checked;
            const needsTenPercent = d3.select("#tenPercentFilter").node().checked;
            const needsBreakout = d3.select("#breakoutFilter").node().checked;
            
            const searchQuery = d3.select("#searchInput").node().value.trim().toUpperCase();

            d3.select("#qxVal").text(qX);
            d3.select("#qyVal").text(qY);
            d3.select("#minRankVal").text(minRank);

            vLine.transition().duration(200).attr("x1", scX(qX)).attr("x2", scX(qX));
            hLine.transition().duration(200).attr("y1", scY(qY)).attr("y2", scY(qY));
            qTexts[0].attr("x", scX((100+qX)/2)).attr("y", scY((100+qY)/2));
            qTexts[1].attr("x", scX(qX/2)).attr("y", scY((100+qY)/2));
            qTexts[2].attr("x", scX(qX/2)).attr("y", scY(qY/2));
            qTexts[3].attr("x", scX((100+qX)/2)).attr("y", scY(qY/2));

            rawData.forEach(d => {{ d.current_quad = getDynamicQuadrant(d, qX, qY); }});
            
            const filteredData = rawData.filter(d => {{
                const rankMatch = d.rank >= minRank;
                const searchMatch = searchQuery === "" || String(d.name).toUpperCase().includes(searchQuery);
                const qMatch = selectedQ === "All" || d.current_quad === selectedQ;
                
                const maMatch = !needsMA || isTrue(d.above_all_moving_avg_line);
                const tenPercentMatch = !needsTenPercent || isTrue(d['close_to_high_10%']);
                const breakoutMatch = !needsBreakout || isTrue(d.breakout_with_big_volume); 
                
                return rankMatch && searchMatch && qMatch && maMatch && tenPercentMatch && breakoutMatch;
            }});

            const circles = dotsGroup.selectAll("circle").data(filteredData, d => d.name);
            
            circles.enter().append("circle").attr("class", d => `dot-${{d.name}}`)
                .attr("cx", d => scX(d.rank)).attr("cy", d => scY(d.season_rank))
                .attr("r", 5).style("stroke", "white")
                .on("mouseover", function(event, d) {{
                    d3.select(this).style("stroke", "#1a237e").style("stroke-width", 2).attr("r", 8);
                    d3.select(`#row-${{d.name}}`).classed("highlight-row", true);
                    
                    const row = document.getElementById(`row-${{d.name}}`);
                    if(row) row.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});

                    tooltip.transition().duration(100).style("opacity", 1);
                    tooltip.html(`
                        <div style="font-size:16px; margin-bottom:8px; border-bottom:1px solid #eee; padding-bottom:5px;">
                            <strong>${{d.name}}</strong> <span style="font-size:12px;color:#6c757d;float:right;">${{d.industry_name}}</span>
                        </div>
                        Total Rank: <strong>${{d.rank.toFixed(2)}}</strong><br/>
                        Season Rank: <strong>${{d.season_rank.toFixed(2)}}</strong><br/>
                        Quadrant: <strong style="color:${{colors[d.current_quad]}}">${{d.current_quad}}</strong><br/>
                        Acc Score: <strong>${{d.acceleration.toFixed(2)}}</strong><br/>
                        Volatility: ${{d['volatility(%)']}}%<br/>
                        <hr style="margin:5px 0; border:0; border-top:1px solid #eee;"/>
                        Close to High 10%: ${{ isTrue(d['close_to_high_10%']) ? '<span style="color:#e74c3c; font-weight:bold;">Yes</span>' : 'No' }}<br/>
                        Breakout with Vol: ${{ isTrue(d.breakout_with_big_volume) ? '<span style="color:#2ecc71; font-weight:bold;">Yes</span>' : 'No' }}
                    `).style("left", (event.pageX + 15) + "px").style("top", (event.pageY - 28) + "px");
                }})
                .on("mouseout", function(event, d) {{
                    d3.select(this).style("stroke", "white").style("stroke-width", 1).attr("r", 5);
                    d3.select(`#row-${{d.name}}`).classed("highlight-row", false);
                    tooltip.transition().duration(200).style("opacity", 0);
                }})
                .merge(circles)
                .transition().duration(300)
                .attr("cx", d => scX(d.rank)).attr("cy", d => scY(d.season_rank))
                .style("fill", d => colors[d.current_quad])
                .style("opacity", 0.75);

            circles.exit().transition().duration(200).attr("r", 0).remove();

            const tableData = [...filteredData].sort((a, b) => b.acceleration - a.acceleration);
            d3.select("#stockCount").text(tableData.length);
            
            const tbody = d3.select("#dataTable tbody");
            tbody.selectAll("tr").remove();
            
            const rows = tbody.selectAll("tr").data(tableData).enter()
                .append("tr").attr("id", d => `row-${{d.name}}`)
                .on("mouseover", (event, d) => d3.select(`.dot-${{d.name}}`).style("stroke", "#1a237e").style("stroke-width", 2).attr("r", 8))
                .on("mouseout", (event, d) => d3.select(`.dot-${{d.name}}`).style("stroke", "white").style("stroke-width", 1).attr("r", 5));
                
            rows.append("td").html(d => `<strong>${{d.name}}</strong>`);
            rows.append("td").style("color", d => colors[d.current_quad]).style("font-weight", "bold").text(d => d.current_quad);
            rows.append("td").text(d => d.acceleration.toFixed(2));
            rows.append("td").text(d => `${{d['volatility(%)'].toFixed(1)}}%`);

            d3.select("#rawStockCount").text(filteredData.length);
            const rawTbody = d3.select("#rawDataTable tbody");
            rawTbody.selectAll("tr").remove();
            
            if (filteredData.length > 0) {{
                const keys = Object.keys(filteredData[0]);
                const rawRows = rawTbody.selectAll("tr").data(filteredData).enter().append("tr");
                
                keys.forEach(key => {{
                    rawRows.append("td").text(d => {{
                        let val = d[key];
                        if (typeof val === 'number') return Number.isInteger(val) ? val : val.toFixed(4);
                        return val;
                    }});
                }});
            }}

            hXAxis.transition().duration(500).call(d3.axisBottom(hX));
            
            if(filteredData.length > 0) {{
                const histogram = d3.bin().value(d => d.acceleration).domain(hX.domain()).thresholds(hX.ticks(40));
                const bins = histogram(filteredData);
                
                hY.domain([0, d3.max(bins, d => d.length) || 10]).nice();
                hYAxis.transition().duration(500).call(d3.axisLeft(hY).ticks(5));
                
                const hBars = hSvg.selectAll(".bar").data(bins);
                hBars.enter().append("rect").attr("class", "bar")
                    .attr("x", d => hX(d.x0) + 1).attr("width", d => Math.max(0, hX(d.x1) - hX(d.x0) - 1))
                    .attr("y", hH).attr("height", 0).style("fill", "#3498db")
                    .merge(hBars).transition().duration(500)
                    .attr("x", d => hX(d.x0) + 1).attr("width", d => Math.max(0, hX(d.x1) - hX(d.x0) - 1))
                    .attr("y", d => hY(d.length)).attr("height", d => hH - hY(d.length));
                hBars.exit().transition().duration(300).attr("y", hH).attr("height", 0).remove();
            }} else {{
                hSvg.selectAll(".bar").transition().duration(300).attr("y", hH).attr("height", 0).remove();
            }}

            if(filteredData.length > 0) {{
                const indRollup = d3.rollup(filteredData, v => d3.mean(v, d => d.acceleration), d => d.industry_name);
                const minCount = searchQuery === "" ? 2 : 1;
                const indCounts = d3.rollup(filteredData, v => v.length, d => d.industry_name);
                
                let indArray = Array.from(indRollup, ([key, value]) => ({{industry: key, mean: value}}))
                                    .filter(d => indCounts.get(d.industry) >= minCount) 
                                    .sort((a, b) => b.mean - a.mean).slice(0, 10);
                                    
                bY.domain(indArray.map(d => d.industry));
                bX.domain([0, d3.max(indArray, d => d.mean) || 10]).nice();
                
                bXAxis.transition().duration(500).call(d3.axisBottom(bX).ticks(5));
                bYAxis.transition().duration(500).call(d3.axisLeft(bY));
                
                const bRects = bSvg.selectAll(".ind-bar").data(indArray, d => d.industry);
                bRects.enter().append("rect").attr("class", "ind-bar")
                    .attr("y", d => bY(d.industry)).attr("height", bY.bandwidth())
                    .attr("x", 0).attr("width", 0).style("fill", "#9b59b6")
                    .merge(bRects).transition().duration(500)
                    .attr("y", d => bY(d.industry)).attr("height", bY.bandwidth())
                    .attr("width", d => bX(Math.max(0, d.mean)));
                bRects.exit().transition().duration(300).attr("width", 0).remove();
            }} else {{
                bSvg.selectAll(".ind-bar").transition().duration(300).attr("width", 0).remove();
                bY.domain([]);
                bYAxis.transition().duration(500).call(d3.axisLeft(bY));
            }}
        }}

        d3.selectAll("input[type=range], select, input[type=checkbox], #searchInput").on("input", update);
        update();
    </script>
</body>
</html>
"""
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html_template)
    print(f"[INFO] Dashboard successfully generated: {output_html}")

def deploy_to_github(source_path, target_path):
    print("[INFO] Syncing to GitHub...")
    src = Path(source_path)
    dst = Path(target_path)
    
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        
        target_dir = dst.parent
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        subprocess.run(["git", "add", dst.name], cwd=target_dir, check=True)
        subprocess.run(["git", "commit", "-m", f"Update: {date_str}"], cwd=target_dir, check=True)
        subprocess.run(["git", "push"], cwd=target_dir, check=True)
        
        print(f"[SUCCESS] Version {date_str} deployed to GitHub.")
    except Exception as e:
        print(f"[ERROR] Sync failed: {e}")

if __name__ == "__main__":
    print("="*50)
    print(" Momentum Workflow")
    print("="*50)
    
    try:
        INPUT_FILE = find_latest_file()
        
        OUTPUT_DIR = Path(__file__).parent / "momentum_dashboard"
        if not OUTPUT_DIR.exists():
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_HTML = OUTPUT_DIR / 'momentum_dashboard.html'

        json_string = process_data(INPUT_FILE)
        generate_html(json_string, OUTPUT_HTML)
        
        target_path = Path(__file__).parents[1] / "galaxy-dashboard" / "momentum_dashboard.html"
        deploy_to_github(source_path=OUTPUT_HTML, target_path=target_path)

        print("\n All Done!")
        print(f" Latest file used: {INPUT_FILE}")
        print(f" Open '{OUTPUT_HTML}' to explore.")
    except Exception as e:
        print(f"\n[ERROR]: {str(e)}")
