import marimo

__generated_with = "0.21.1"
app = marimo.App(width="full", app_title="Q1: Communication Intelligence Dashboard")


@app.cell
def _():
    import json as json_lib
    import marimo as mo
    import pandas as pd
    return json_lib, mo, pd


@app.cell
def _(mo, pd):
    _base = mo.notebook_location() / "public"
    df_intents = pd.read_csv(str(_base / "categories_v2.csv"))
    print(f"Loaded {len(df_intents)} classified messages")
    return (df_intents,)


@app.cell
def _(df_intents, json_lib, mo):
    # Aggregate data for D3
    _cat_counts = df_intents.groupby("category").size().reset_index(name="count").sort_values("count", ascending=False)
    _cat_data = _cat_counts.to_dict(orient="records")

    _entity_cat = df_intents.groupby(["sender_name", "category"]).size().reset_index(name="count")
    _entity_totals = _entity_cat.groupby("sender_name")["count"].sum().sort_values(ascending=False)
    _top_entities = _entity_totals.head(25).index.tolist()
    _entity_cat_top = _entity_cat[_entity_cat["sender_name"].isin(_top_entities)]
    _entity_data = _entity_cat_top.to_dict(orient="records")
    _entity_order = _top_entities

    _date_cat = df_intents.groupby(["date_str", "category"]).size().reset_index(name="count")
    _heatmap_data = _date_cat.to_dict(orient="records")
    _dates_sorted = sorted(df_intents["date_str"].unique().tolist())
    _cats_sorted = _cat_counts["category"].tolist()

    _cat_json = json_lib.dumps(_cat_data)
    _entity_json = json_lib.dumps(_entity_data)
    _entity_order_json = json_lib.dumps(_entity_order)
    _heatmap_json = json_lib.dumps(_heatmap_data)
    _dates_json = json_lib.dumps(_dates_sorted)
    _cats_json = json_lib.dumps(_cats_sorted)

    _n_msgs = len(df_intents)
    _n_cats = len(_cats_sorted)
    _n_entities = len(_top_entities)

    _cat_overview = mo.iframe(f"""
<!DOCTYPE html>
<html>
<head>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: 'Segoe UI', sans-serif; background: #fafafa; }}
#container {{ width: 100%; background: white; border: 1px solid #ddd; border-radius: 6px;
              padding: 16px; overflow: hidden; }}
#stats {{
    font-size: 11px; color: #666; margin-bottom: 10px;
    display: flex; gap: 16px; align-items: center;
}}
.stat-box {{
    padding: 3px 10px; background: #f5f5f5; border-radius: 4px; border: 1px solid #eee;
    text-align: center;
}}
.stat-val {{ font-size: 16px; font-weight: bold; color: #333; }}
.stat-lbl {{ font-size: 9px; color: #888; }}
#filter-msg {{
    font-size: 12px; color: #555; margin: 6px 0;
    padding: 4px 10px; background: #fffde7; border-radius: 4px; border: 1px solid #f0e68c;
    display: none; cursor: pointer;
}}
.section-title {{
    font-size: 13px; font-weight: bold; color: #444; margin: 14px 0 6px;
    border-bottom: 1px solid #eee; padding-bottom: 3px;
}}
.tooltip {{
    position: fixed; background: white; border: 1px solid #ccc; border-radius: 6px;
    padding: 8px 12px; font-size: 12px; pointer-events: none;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.15); display: none;
    max-width: 300px; z-index: 1000;
}}
.bar:hover {{ opacity: 0.85; cursor: pointer; }}
.hm-cell:hover {{ stroke: #333; stroke-width: 1.5; cursor: pointer; }}
</style>
</head>
<body>
<div id="container">
    <div id="stats">
        <div class="stat-box"><div class="stat-val">{_n_msgs}</div><div class="stat-lbl">Messages</div></div>
        <div class="stat-box"><div class="stat-val">{_n_cats}</div><div class="stat-lbl">Categories</div></div>
        <div class="stat-box"><div class="stat-val">{_n_entities}</div><div class="stat-lbl">Top Senders</div></div>
        <div style="flex:1"></div>
        <div style="font-size:10px;color:#aaa">Click a category bar to filter &middot; Click again to reset</div>
    </div>
    <div id="filter-msg">Filtered: <span id="filter-cat"></span> — click to clear</div>
    <div class="section-title">Category Distribution</div>
    <div id="cat-chart"></div>
    <div class="section-title">Message Categories by Sender (Top {_n_entities})</div>
    <div id="entity-chart"></div>
    <div class="section-title">Category Frequency Over Time</div>
    <div id="heatmap-chart"></div>
</div>
<div class="tooltip" id="tooltip"></div>

<script>
try {{

var catData = {_cat_json};
var entityData = {_entity_json};
var entityOrder = {_entity_order_json};
var heatmapData = {_heatmap_json};
var datesSorted = {_dates_json};
var catsSorted = {_cats_json};

var tooltip = d3.select("#tooltip");
var filterMsg = d3.select("#filter-msg");
var filterCat = d3.select("#filter-cat");

// Color scale
var catColors = d3.scaleOrdinal(d3.schemeTableau10).domain(catsSorted);

var activeFilter = null;

function setFilter(cat) {{
    if (activeFilter === cat) {{
        activeFilter = null;
        filterMsg.style("display", "none");
    }} else {{
        activeFilter = cat;
        filterCat.text(cat);
        filterMsg.style("display", "block");
    }}
    updateAll();
}}

filterMsg.on("click", function() {{ activeFilter = null; filterMsg.style("display", "none"); updateAll(); }});

// ═══ 1. CATEGORY BAR CHART ═══
var catMargin = {{top: 5, right: 60, bottom: 5, left: 160}};
var catW = 700, catBarH = 24;
var catH = catData.length * catBarH + catMargin.top + catMargin.bottom;

var catSvg = d3.select("#cat-chart").append("svg")
    .attr("width", catW).attr("height", catH);
var catG = catSvg.append("g").attr("transform", "translate(" + catMargin.left + "," + catMargin.top + ")");

var catX = d3.scaleLinear().range([0, catW - catMargin.left - catMargin.right]);
var catY = d3.scaleBand().range([0, catH - catMargin.top - catMargin.bottom]).padding(0.15);

function drawCatBars() {{
    var data = catData;
    var maxVal = d3.max(data, function(d) {{ return d.count; }});
    catX.domain([0, maxVal]);
    catY.domain(data.map(function(d) {{ return d.category; }}));

    var bars = catG.selectAll(".cat-bar-g").data(data, function(d) {{ return d.category; }});
    var enter = bars.enter().append("g").attr("class", "cat-bar-g");

    enter.append("rect").attr("class", "bar");
    enter.append("text").attr("class", "bar-label");
    enter.append("text").attr("class", "bar-count");

    var merged = enter.merge(bars);

    merged.select("rect.bar")
        .attr("x", 0)
        .attr("y", function(d) {{ return catY(d.category); }})
        .attr("height", catY.bandwidth())
        .transition().duration(300)
        .attr("width", function(d) {{ return catX(d.count); }})
        .attr("fill", function(d) {{ return catColors(d.category); }})
        .attr("opacity", function(d) {{ return (!activeFilter || activeFilter === d.category) ? 1 : 0.2; }});

    merged.select("text.bar-label")
        .attr("x", -6)
        .attr("y", function(d) {{ return catY(d.category) + catY.bandwidth() / 2; }})
        .attr("dy", "0.35em")
        .attr("text-anchor", "end")
        .style("font-size", "11px")
        .style("fill", function(d) {{ return (!activeFilter || activeFilter === d.category) ? "#333" : "#bbb"; }})
        .text(function(d) {{ return d.category; }});

    merged.select("text.bar-count")
        .attr("y", function(d) {{ return catY(d.category) + catY.bandwidth() / 2; }})
        .attr("dy", "0.35em")
        .style("font-size", "11px")
        .style("font-weight", "bold")
        .style("fill", function(d) {{ return (!activeFilter || activeFilter === d.category) ? "#333" : "#ccc"; }})
        .transition().duration(300)
        .attr("x", function(d) {{ return catX(d.count) + 5; }})
        .text(function(d) {{ return d.count; }});

    merged.select("rect.bar")
        .on("click", function(event, d) {{ setFilter(d.category); }})
        .on("mouseover", function(event, d) {{
            tooltip.style("display", "block")
                .html("<strong>" + d.category + "</strong><br/>" + d.count + " messages (" + (100*d.count/{_n_msgs}).toFixed(1) + "%)")
                .style("left", (event.clientX + 14) + "px")
                .style("top", (event.clientY - 20) + "px");
        }})
        .on("mouseout", function() {{ tooltip.style("display", "none"); }});

    bars.exit().remove();
}}

// ═══ 2. ENTITY STACKED BAR CHART ═══
var entMargin = {{top: 5, right: 30, bottom: 5, left: 160}};
var entBarH = 20;
var entW = 700;

var entSvg = d3.select("#entity-chart").append("svg").attr("width", entW);
var entG = entSvg.append("g").attr("transform", "translate(" + entMargin.left + "," + entMargin.top + ")");

var entX = d3.scaleLinear().range([0, entW - entMargin.left - entMargin.right]);
var entY = d3.scaleBand().padding(0.12);

function drawEntityBars() {{
    // Aggregate per entity
    var filteredData = activeFilter
        ? entityData.filter(function(d) {{ return d.category === activeFilter; }})
        : entityData;

    var entityMap = {{}};
    filteredData.forEach(function(d) {{
        if (!entityMap[d.sender_name]) entityMap[d.sender_name] = {{}};
        entityMap[d.sender_name][d.category] = (entityMap[d.sender_name][d.category] || 0) + d.count;
    }});

    var entityTotals = Object.keys(entityMap).map(function(e) {{
        var total = 0;
        for (var c in entityMap[e]) total += entityMap[e][c];
        return {{entity: e, total: total, cats: entityMap[e]}};
    }}).sort(function(a, b) {{ return b.total - a.total; }}).slice(0, 25);

    var entH = entityTotals.length * entBarH + entMargin.top + entMargin.bottom;
    entSvg.attr("height", entH);
    entY.range([0, entH - entMargin.top - entMargin.bottom]);

    var maxTotal = d3.max(entityTotals, function(d) {{ return d.total; }}) || 1;
    entX.domain([0, maxTotal]);
    entY.domain(entityTotals.map(function(d) {{ return d.entity; }}));

    // Build stacked segments
    var segments = [];
    entityTotals.forEach(function(ent) {{
        var x0 = 0;
        var catsUsed = activeFilter ? [activeFilter] : catsSorted;
        catsUsed.forEach(function(cat) {{
            var v = ent.cats[cat] || 0;
            if (v > 0) {{
                segments.push({{entity: ent.entity, category: cat, x0: x0, x1: x0 + v, count: v}});
                x0 += v;
            }}
        }});
    }});

    // Labels
    var labels = entG.selectAll(".ent-label").data(entityTotals, function(d) {{ return d.entity; }});
    labels.exit().remove();
    var labelsE = labels.enter().append("text").attr("class", "ent-label");
    labelsE.merge(labels)
        .attr("x", -6).attr("y", function(d) {{ return entY(d.entity) + entY.bandwidth()/2; }})
        .attr("dy", "0.35em").attr("text-anchor", "end")
        .style("font-size", "10px").style("fill", "#333")
        .text(function(d) {{ return d.entity; }});

    // Bars
    var bars = entG.selectAll(".ent-seg").data(segments, function(d) {{ return d.entity + "-" + d.category; }});
    bars.exit().remove();
    var barsE = bars.enter().append("rect").attr("class", "ent-seg bar");
    barsE.merge(bars)
        .attr("y", function(d) {{ return entY(d.entity); }})
        .attr("height", entY.bandwidth())
        .attr("fill", function(d) {{ return catColors(d.category); }})
        .transition().duration(300)
        .attr("x", function(d) {{ return entX(d.x0); }})
        .attr("width", function(d) {{ return Math.max(0, entX(d.x1) - entX(d.x0)); }});

    entG.selectAll(".ent-seg")
        .on("mouseover", function(event, d) {{
            tooltip.style("display", "block")
                .html("<strong>" + d.entity + "</strong><br/>" + d.category + ": " + d.count + " messages")
                .style("left", (event.clientX + 14) + "px")
                .style("top", (event.clientY - 20) + "px");
        }})
        .on("mouseout", function() {{ tooltip.style("display", "none"); }})
        .on("click", function(event, d) {{ setFilter(d.category); }});
}}

// ═══ 3. HEATMAP ═══
var hmMargin = {{top: 5, right: 30, bottom: 60, left: 160}};
var hmCellW = 38, hmCellH = 22;
var hmW = Math.max(700, datesSorted.length * hmCellW + hmMargin.left + hmMargin.right);
var hmH = catsSorted.length * hmCellH + hmMargin.top + hmMargin.bottom;

var hmSvg = d3.select("#heatmap-chart").append("svg")
    .attr("width", hmW).attr("height", hmH);
var hmG = hmSvg.append("g").attr("transform", "translate(" + hmMargin.left + "," + hmMargin.top + ")");

var hmX = d3.scaleBand().domain(datesSorted).range([0, datesSorted.length * hmCellW]).padding(0.05);
var hmY = d3.scaleBand().domain(catsSorted).range([0, catsSorted.length * hmCellH]).padding(0.05);

// Axis labels
hmG.append("g").attr("class", "hm-x-axis")
    .attr("transform", "translate(0," + (catsSorted.length * hmCellH) + ")")
    .call(d3.axisBottom(hmX))
    .selectAll("text").attr("transform", "rotate(-40)").style("text-anchor", "end").style("font-size", "9px");

hmG.append("g").attr("class", "hm-y-axis")
    .call(d3.axisLeft(hmY))
    .selectAll("text").style("font-size", "10px");

function drawHeatmap() {{
    var filtered = activeFilter
        ? heatmapData.filter(function(d) {{ return d.category === activeFilter; }})
        : heatmapData;

    var maxCount = d3.max(filtered, function(d) {{ return d.count; }}) || 1;
    var colorScale = d3.scaleSequential(d3.interpolateBlues).domain([0, maxCount]);

    var cells = hmG.selectAll(".hm-cell").data(filtered, function(d) {{ return d.date_str + "-" + d.category; }});
    cells.exit().transition().duration(200).attr("opacity", 0).remove();

    var cellsE = cells.enter().append("rect").attr("class", "hm-cell");
    cellsE.merge(cells)
        .attr("x", function(d) {{ return hmX(d.date_str); }})
        .attr("y", function(d) {{ return hmY(d.category); }})
        .attr("width", hmX.bandwidth())
        .attr("height", hmY.bandwidth())
        .attr("rx", 2)
        .transition().duration(300)
        .attr("fill", function(d) {{ return colorScale(d.count); }})
        .attr("opacity", 1);

    hmG.selectAll(".hm-cell")
        .on("mouseover", function(event, d) {{
            d3.select(this).attr("stroke", "#333").attr("stroke-width", 1.5);
            tooltip.style("display", "block")
                .html("<strong>" + d.category + "</strong><br/>Date: " + d.date_str + "<br/>Messages: " + d.count)
                .style("left", (event.clientX + 14) + "px")
                .style("top", (event.clientY - 20) + "px");
        }})
        .on("mouseout", function() {{
            d3.select(this).attr("stroke", "none");
            tooltip.style("display", "none");
        }})
        .on("click", function(event, d) {{ setFilter(d.category); }});
}}

// ═══ UPDATE ALL ═══
function updateAll() {{
    drawCatBars();
    drawEntityBars();
    drawHeatmap();
}}

updateAll();

}} catch(e) {{
    document.getElementById("container").innerHTML = "<pre style='color:red;padding:12px'>" + e.message + "\\n" + e.stack + "</pre>";
}}
</script>
</body>
</html>
    """, width="100%", height="1650px")

    q1_category_bar = _cat_overview
    q1_entity_bar = mo.md("")
    q1_heatmap = mo.md("")
    return q1_category_bar, q1_entity_bar, q1_heatmap



@app.cell
def _(df_intents, mo):
    _unique_cats = ["All"] + sorted(df_intents["category"].unique().tolist())
    category_dropdown = mo.ui.dropdown(options=_unique_cats, value="All", label="Filter by Category")

    _entity_types = ["All"] + sorted(set(
        [t for t in df_intents["sender_type"].unique().tolist() if t] +
        [t for t in df_intents["receiver_type"].unique().tolist() if t]
    ))
    entity_type_dropdown = mo.ui.dropdown(options=_entity_types, value="All", label="Filter by Entity Type")

    _all_entities = sorted(set(
        df_intents["sender_name"].dropna().unique().tolist() +
        df_intents["receiver_name"].dropna().unique().tolist()
    ))
    entity_dropdown = mo.ui.multiselect(options=_all_entities, value=[], label="Filter by Entity")

    suspicion_slider = mo.ui.slider(
        start=0, stop=10, step=1, value=0,
        label="Min. Suspicion",
        show_value=True
    )
    return (
        category_dropdown,
        entity_dropdown,
        entity_type_dropdown,
        suspicion_slider,
    )



@app.cell
def _(
    category_dropdown,
    df_intents,
    entity_dropdown,
    entity_type_dropdown,
    json_lib,
    mo,
    suspicion_slider,
):
    _selected_cat = category_dropdown.value
    _min_suspicion = suspicion_slider.value

    # Apply filters
    _df_filtered = df_intents.copy()

    if _selected_cat != "All":
        _df_filtered = _df_filtered[_df_filtered["category"] == _selected_cat]

    if entity_type_dropdown.value != "All":
        _df_filtered = _df_filtered[
            (_df_filtered["sender_type"] == entity_type_dropdown.value) |
            (_df_filtered["receiver_type"] == entity_type_dropdown.value)
        ]

    if len(entity_dropdown.value) > 0:
        _selected_entities = list(entity_dropdown.value)
        _df_filtered = _df_filtered[
            (_df_filtered["sender_name"].isin(_selected_entities)) |
            (_df_filtered["receiver_name"].isin(_selected_entities))
        ]

    if _min_suspicion > 0:
        _df_filtered = _df_filtered[_df_filtered["suspicion"] >= _min_suspicion]

    _unique_dates = json_lib.dumps(sorted(df_intents["date_str"].unique().tolist()))

    _category_colors = {
        "routine operations": "#5B9BD5",
        "environmental monitoring": "#3cb44b",
        "permit and regulatory": "#42d4f4",
        "covert coordination": "#f58231",
        "illegal activity": "#e6194b",
        "surveillance and intelligence": "#911eb4",
        "cover story": "#ffe119",
        "music and tourism": "#f032e6",
        "interpersonal and social": "#a9a9a9",
        "command and control": "#800000",
        "unknown": "#999999"
    }

    # Build filtered records for D3
    _records = []
    for _, _row in _df_filtered.iterrows():
        _records.append({
            "node_id": str(_row["node_id"]),
            "sender_name": str(_row["sender_name"]),
            "receiver_name": str(_row["receiver_name"]),
            "sender_type": str(_row["sender_type"]),
            "receiver_type": str(_row["receiver_type"]),
            "date_str": str(_row["date_str"]),
            "hour_float": float(_row["hour_float"]),
            "timestamp": str(_row["timestamp"]),
            "category": str(_row["category"]),
            "suspicion": int(_row["suspicion"]) if str(_row["suspicion"]).isdigit() else 0,
            "content": str(_row["content"]),
            "category_color": _category_colors.get(str(_row["category"]), "#999"),
        })

    # Build ALL records (unfiltered) for chat history and ego network
    _all_records = []
    for _, _row in df_intents.iterrows():
        _all_records.append({
            "node_id": str(_row["node_id"]),
            "sender_name": str(_row["sender_name"]),
            "receiver_name": str(_row["receiver_name"]),
            "sender_type": str(_row["sender_type"]),
            "receiver_type": str(_row["receiver_type"]),
            "date_str": str(_row["date_str"]),
            "hour_float": float(_row["hour_float"]),
            "timestamp": str(_row["timestamp"]),
            "category": str(_row["category"]),
            "suspicion": int(_row["suspicion"]) if str(_row["suspicion"]).isdigit() else 0,
            "content": str(_row["content"]),
            "category_color": _category_colors.get(str(_row["category"]), "#999"),
        })

    _filtered_json = json_lib.dumps(_records)
    _all_json = json_lib.dumps(_all_records)
    _category_colors_json = json_lib.dumps(_category_colors)
    _msg_count = len(_df_filtered)

    # === THE BIG COMBINED D3 IFRAME ===
    _dashboard = mo.iframe(f"""
    <!DOCTYPE html>
    <html>
    <head>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: 'Segoe UI', sans-serif; background: #fafafa; }}
    #container {{ display: flex; width: 100%; height: 830px; }}
    #timeline-panel {{ width: 60%; height: 100%; overflow-y: auto; border-right: 2px solid #ddd; background: white; }}
    #right-panel {{ width: 40%; height: 100%; display: flex; flex-direction: column; }}
    #chat-panel {{ height: 50%; border-bottom: 2px solid #ddd; display: flex; flex-direction: column; background: white; }}
    #ego-panel {{ height: 50%; background: white; position: relative; }}
    #chat-header {{ padding: 6px 10px; background: #f0f0f0; border-bottom: 1px solid #ddd;
                    font-weight: bold; font-size: 12px; flex-shrink: 0; }}
    #chat-tabs {{ display: flex; gap: 0; border-bottom: 1px solid #ddd; flex-shrink: 0; }}
    .chat-tab {{ padding: 5px 12px; font-size: 11px; cursor: pointer; border: none;
                 background: #f0f0f0; border-bottom: 2px solid transparent; color: #666;
                 transition: all 0.15s; }}
    .chat-tab:hover {{ background: #e8e8e8; }}
    .chat-tab.active {{ background: white; color: #333; font-weight: bold;
                        border-bottom: 2px solid #5B9BD5; }}
    #chat-messages {{ flex: 1; overflow-y: auto; padding: 8px; }}
    .chat-msg {{ padding: 8px 10px; margin: 4px 0; border-radius: 8px; font-size: 12px;
                 border-left: 4px solid #ccc; background: #f9f9f9; cursor: pointer; transition: all 0.15s; }}
    .chat-msg:hover {{ background: #eef; }}
    .chat-msg.highlighted {{ background: #fff3cd; border-left-color: #ff5555; box-shadow: 0 0 6px rgba(255,85,85,0.3); }}
    .chat-msg .full-content {{ white-space: pre-wrap; word-break: break-word; }}
    .chat-msg .meta {{ font-size: 10px; color: #888; margin-top: 3px; }}
    .chat-msg .sender {{ font-weight: bold; }}
    .chat-msg .badge {{ display: inline-block; padding: 1px 6px; border-radius: 3px;
                        font-size: 9px; color: white; margin-left: 4px; }}
    .tooltip {{
        position: fixed; background: white; border: 1px solid #ccc; border-radius: 6px;
        padding: 8px 12px; font-size: 12px; pointer-events: none;
        box-shadow: 2px 2px 6px rgba(0,0,0,0.15); display: none; max-width: 450px; z-index: 1000;
    }}
    #ego-title {{ position: absolute; top: 4px; left: 10px; font-size: 12px; font-weight: bold; color: #333; z-index: 10; }}
    #chat-empty {{ padding: 30px; text-align: center; color: #aaa; font-size: 13px; }}
    #ego-empty {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
                  color: #aaa; font-size: 13px; text-align: center; }}
    </style>
    </head>
    <body>
    <div id="container">
    <div id="timeline-panel"><div id="chart"></div></div>
    <div id="right-panel">
        <div id="chat-panel">
            <div id="chat-header">Message History <span id="chat-entity" style="color:#555"></span></div>
            <div id="chat-tabs">
                <button class="chat-tab active" id="tab-all" onclick="switchTab('all')">All from Sender</button>
                <button class="chat-tab" id="tab-convo" onclick="switchTab('convo')">Conversation</button>
            </div>
            <div id="chat-messages"><div id="chat-empty">Click a message in the timeline to see conversation history</div></div>
        </div>
        <div id="ego-panel">
            <div id="ego-title">Ego Network</div>
            <div id="ego-empty">Click a message to see the sender's communication network</div>
            <svg id="ego-svg" width="100%" height="100%"></svg>
        </div>
    </div>
    </div>
    <div class="tooltip" id="tooltip"></div>

    <script>
    try {{

    var filteredData = {_filtered_json};
    var allData = {_all_json};
    var allDates = {_unique_dates};
    var categoryColors = {_category_colors_json};

    var typeColors = {{
    "Person": "#7B68EE",
    "Organization": "#DC143C",
    "Vessel": "#00CED1",
    "Group": "#FF8C00",
    "Location": "#4169E1"
    }};

    // ============================================================
    // LEFT PANEL: TIMELINE
    // ============================================================
    var margin = {{top: 60, right: 15, bottom: 35, left: 55}};
    var rowHeight = 55;
    var summaryHeight = 50;
    var tlWidth = document.getElementById("timeline-panel").offsetWidth - margin.left - margin.right - 10;
    if (tlWidth < 400) tlWidth = 620;
    var tlHeight = allDates.length * rowHeight;
    var totalHeight = tlHeight + summaryHeight;
    var dotSize = 9;
    var dotGap = 2;
    var maxCols = 6;

    var svg = d3.select("#chart")
    .append("svg")
    .attr("width", tlWidth + margin.left + margin.right)
    .attr("height", totalHeight + margin.top + margin.bottom)
    .append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    var x = d3.scaleLinear().domain([8, 15]).range([0, tlWidth]);
    var y = d3.scaleBand().domain(allDates).range([0, tlHeight]).padding(0.1);
    var tickVals = [8,9,10,11,12,13,14,15];

    svg.append("g")
    .call(d3.axisTop(x).tickValues(tickVals).tickFormat(function(d) {{ return d + ":00"; }}))
    .selectAll("text").style("font-size", "11px");

    tickVals.forEach(function(h) {{
    svg.append("line").attr("x1", x(h)).attr("x2", x(h))
        .attr("y1", 0).attr("y2", totalHeight)
        .attr("stroke", "#eee").attr("stroke-width", 1);
    }});

    allDates.forEach(function(date, i) {{
    svg.append("rect").attr("x", 0).attr("y", y(date))
        .attr("width", tlWidth).attr("height", y.bandwidth())
        .attr("fill", i % 2 === 0 ? "#f9f9f9" : "#ffffff").attr("stroke", "#eee");
    svg.append("text").attr("x", -6).attr("y", y(date) + y.bandwidth() / 2)
        .attr("text-anchor", "end").attr("dominant-baseline", "middle")
        .style("font-size", "10px").style("font-weight", "bold").text(i + 1);
    }});

    // Density curves
    allDates.forEach(function(date) {{
    var dayData = filteredData.filter(function(d) {{ return d.date_str === date; }});
    if (dayData.length === 0) return;
    var values = dayData.map(function(d) {{ return d.hour_float; }});
    var bins = d3.bin().domain([8, 15.5]).thresholds(25)(values);
    var maxCount = d3.max(bins, function(b) {{ return b.length; }});
    var areaY = d3.scaleLinear().domain([0, maxCount || 1])
        .range([y(date) + y.bandwidth(), y(date) + y.bandwidth() * 0.2]);
    var area = d3.area()
        .x(function(b) {{ return x((b.x0 + b.x1) / 2); }})
        .y0(y(date) + y.bandwidth())
        .y1(function(b) {{ return areaY(b.length); }})
        .curve(d3.curveBasis);
    svg.append("path").datum(bins).attr("d", area).attr("fill", "#5B9BD5").attr("opacity", 0.15);
    }});

    // Group by date+hour
    var grouped = {{}};
    filteredData.forEach(function(d) {{
    var hour = Math.floor(d.hour_float);
    var key = d.date_str + "|" + hour;
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(d);
    }});

    var tooltip = d3.select("#tooltip");
    var allDotGroups = [];

    // Draw clickable dots
    Object.keys(grouped).forEach(function(key) {{
    var parts = key.split("|");
    var date = parts[0];
    var hour = parseInt(parts[1]);
    var items = grouped[key];
    var binLeft = x(hour) + 4;
    var rowTop = y(date);

    items.forEach(function(d, idx) {{
        var col = idx % maxCols;
        var row = Math.floor(idx / maxCols);
        var px = binLeft + col * (dotSize + dotGap);
        var py = rowTop + row * (dotSize + dotGap);

        var g = svg.append("g").style("cursor", "pointer").datum(d);

        g.append("rect").attr("class", "dot-rect")
            .attr("x", px).attr("y", py)
            .attr("width", dotSize).attr("height", dotSize)
            .attr("fill", d.category_color).attr("rx", 2)
            .attr("stroke", "#fff").attr("stroke-width", 0.5);

        g.on("mouseover", function(event) {{
            d3.select(this).select(".dot-rect").attr("stroke", "#333").attr("stroke-width", 2);
            tooltip.style("display", "block")
                .html(
                    "<strong>" + d.sender_name + " &rarr; " + d.receiver_name + "</strong><br/>"
                    + d.timestamp + "<br/>"
                    + "<strong>Category:</strong> " + d.category
                    + " <span style='background:" + (categoryColors[d.category]||"#999")
                    + ";color:#fff;padding:1px 5px;border-radius:3px;font-size:10px'>"
                    + d.suspicion + "/10</span><br/>"
                    + "<div style='max-height:200px;overflow-y:auto;margin-top:4px;font-style:italic;white-space:pre-wrap'>" + d.content + "</div>"
                )
                .style("left", (event.clientX + 14) + "px")
                .style("top", (event.clientY - 20) + "px");
        }})
        .on("mouseout", function() {{
            d3.select(this).select(".dot-rect").attr("stroke", "#fff").attr("stroke-width", 0.5);
            tooltip.style("display", "none");
        }})
        .on("click", function(event, datum) {{
            onMessageClick(datum);
        }});

        allDotGroups.push({{g: g, d: d}});
    }});
    }});

    // Summary row
    var summaryTop = tlHeight + 10;
    svg.append("rect").attr("x", 0).attr("y", summaryTop)
    .attr("width", tlWidth).attr("height", summaryHeight)
    .attr("fill", "#f0f0f0").attr("stroke", "#ddd");
    svg.append("text").attr("x", -6).attr("y", summaryTop + summaryHeight / 2)
    .attr("text-anchor", "end").attr("dominant-baseline", "middle")
    .style("font-size", "10px").style("font-weight", "bold").text("All");

    var allValues = filteredData.map(function(d) {{ return d.hour_float; }});
    if (allValues.length > 0) {{
    var allBins = d3.bin().domain([8, 15.5]).thresholds(40)(allValues);
    var allMax = d3.max(allBins, function(b) {{ return b.length; }});
    var summaryY = d3.scaleLinear().domain([0, allMax || 1])
        .range([summaryTop + summaryHeight, summaryTop + 10]);
    var summaryArea = d3.area()
        .x(function(b) {{ return x((b.x0 + b.x1) / 2); }})
        .y0(summaryTop + summaryHeight)
        .y1(function(b) {{ return summaryY(b.length); }})
        .curve(d3.curveBasis);
    svg.append("path").datum(allBins).attr("d", summaryArea)
        .attr("fill", "#5B9BD5").attr("opacity", 0.35);
    svg.append("path").datum(allBins)
        .attr("d", d3.line()
            .x(function(b) {{ return x((b.x0 + b.x1) / 2); }})
            .y(function(b) {{ return summaryY(b.length); }})
            .curve(d3.curveBasis))
        .attr("fill", "none").attr("stroke", "#5B9BD5").attr("stroke-width", 2);
    }}

    svg.append("g")
    .attr("transform", "translate(0," + (summaryTop + summaryHeight) + ")")
    .call(d3.axisBottom(x).tickValues(tickVals).tickFormat(function(d) {{ return d + ":00"; }}))
    .selectAll("text").style("font-size", "11px");

    // Legends
    var cleg = svg.append("g").attr("transform", "translate(0,-50)");
    cleg.append("text").attr("x", 0).attr("y", 0).text("Category:").style("font-size", "9px").style("font-weight", "bold");
    Object.entries(categoryColors).forEach(function(e, i) {{
    var col = i % 5;
    var row = Math.floor(i / 5);
    cleg.append("rect").attr("x", 60 + col * 125).attr("y", -8 + row * 14)
        .attr("width", 9).attr("height", 9).attr("fill", e[1]).attr("rx", 1);
    cleg.append("text").attr("x", 60 + col * 125 + 12).attr("y", row * 14).text(e[0]).style("font-size", "8px");
    }});

    // ============================================================
    // CLICK HANDLER — updates chat box + ego network
    // ============================================================
    function onMessageClick(d) {{
    updateChatBox(d);
    updateEgoNetwork(d);

    // Highlight the clicked dot in timeline
    allDotGroups.forEach(function(item) {{
        if (item.d.node_id === d.node_id) {{
            item.g.select(".dot-rect").attr("stroke", "#ff0000").attr("stroke-width", 2.5);
        }} else {{
            item.g.select(".dot-rect").attr("stroke", "#fff").attr("stroke-width", 0.5);
        }}
    }});
    }}

    // ============================================================
    // RIGHT TOP: CHAT BOX (tabbed)
    // ============================================================
    var currentClickedMsg = null;
    var currentTab = "all";

    function switchTab(tab) {{
    currentTab = tab;
    document.getElementById("tab-all").className = "chat-tab" + (tab === "all" ? " active" : "");
    document.getElementById("tab-convo").className = "chat-tab" + (tab === "convo" ? " active" : "");
    if (currentClickedMsg) renderChat(currentClickedMsg);
    }}

    function updateChatBox(clickedMsg) {{
    currentClickedMsg = clickedMsg;
    renderChat(clickedMsg);
    }}

    function renderChat(clickedMsg) {{
    var entity = clickedMsg.sender_name;
    var receiver = clickedMsg.receiver_name;

    if (currentTab === "all") {{
        document.getElementById("chat-entity").textContent = "— all from " + entity;
    }} else {{
        document.getElementById("chat-entity").textContent = "— " + entity + " ↔ " + receiver;
    }}

    // Filter messages based on active tab
    var history;
    if (currentTab === "all") {{
        history = allData.filter(function(m) {{
            return m.sender_name === entity || m.receiver_name === entity;
        }});
    }} else {{
        history = allData.filter(function(m) {{
            return (m.sender_name === entity && m.receiver_name === receiver)
                || (m.sender_name === receiver && m.receiver_name === entity);
        }});
    }}

    history.sort(function(a, b) {{
        return a.timestamp.localeCompare(b.timestamp);
    }});

    var container = document.getElementById("chat-messages");
    container.innerHTML = "";

    if (history.length === 0) {{
        container.innerHTML = "<div style='padding:20px;text-align:center;color:#aaa'>No messages found</div>";
        return;
    }}

    history.forEach(function(m) {{
        var div = document.createElement("div");
        var isClicked = m.node_id === clickedMsg.node_id;
        div.className = "chat-msg" + (isClicked ? " highlighted" : "");
        div.setAttribute("data-nodeid", m.node_id);

        var isSender = m.sender_name === entity;
        var catColor = categoryColors[m.category] || "#999";
        var suspColor = m.suspicion >= 7 ? "#e6194b" : m.suspicion >= 4 ? "#f58231" : "#3cb44b";

        div.style.borderLeftColor = catColor;

        var contentText = m.content;

        div.innerHTML =
            "<span class='sender' style='color:" + (isSender ? "#333" : "#666") + "'>"
            + m.sender_name + " &rarr; " + m.receiver_name + "</span>"
            + "<span class='badge' style='background:" + suspColor + "'>" + m.suspicion + "/10</span>"
            + "<span class='badge' style='background:" + catColor + "'>" + m.category + "</span>"
            + "<div class='full-content' style='margin-top:4px;font-size:12px;color:#333'>"
            + contentText + "</div>"
            + "<div class='meta'>" + m.timestamp + "</div>";

        div.addEventListener("click", function() {{
            onMessageClick(m);
        }});

        container.appendChild(div);
    }});

    // Scroll to highlighted
    var highlighted = container.querySelector(".highlighted");
    if (highlighted) {{
        highlighted.scrollIntoView({{ behavior: "smooth", block: "center" }});
    }}
    }}

    // ============================================================
    // RIGHT BOTTOM: EGO NETWORK (hub-and-spoke, ego in center)
    // ============================================================
    function updateEgoNetwork(clickedMsg) {{
    var entity = clickedMsg.sender_name;
    document.getElementById("ego-title").textContent = "Network — " + entity;
    var emptyEl = document.getElementById("ego-empty");
    if (emptyEl) emptyEl.remove();

    // Gather ALL messages involving this entity
    var entityMsgs = allData.filter(function(m) {{
        return m.sender_name === entity || m.receiver_name === entity;
    }});

    // Build partner stats
    var partnerMap = {{}};
    entityMsgs.forEach(function(m) {{
        var partner = m.sender_name === entity ? m.receiver_name : m.sender_name;
        var direction = m.sender_name === entity ? "out" : "in";
        if (!partnerMap[partner]) {{
            partnerMap[partner] = {{ name: partner, type: "", out: 0, in: 0,
                categories: {{}}, maxSusp: 0, totalSusp: 0, totalMsgs: 0 }};
        }}
        partnerMap[partner][direction]++;
        partnerMap[partner].totalMsgs++;
        partnerMap[partner].totalSusp += (m.suspicion || 0);
        partnerMap[partner].categories[m.category] = (partnerMap[partner].categories[m.category] || 0) + 1;
        if (m.suspicion > partnerMap[partner].maxSusp) partnerMap[partner].maxSusp = m.suspicion;
    }});

    // Get types
    allData.forEach(function(m) {{
        if (partnerMap[m.sender_name]) partnerMap[m.sender_name].type = m.sender_type;
        if (partnerMap[m.receiver_name]) partnerMap[m.receiver_name].type = m.receiver_type;
    }});

    var partners = Object.values(partnerMap);
    var nPartners = partners.length;

    // Clear
    var egoSvg = d3.select("#ego-svg");
    egoSvg.selectAll("*").remove();

    var egoEl = document.getElementById("ego-panel");
    var egoW = egoEl.offsetWidth || 400;
    var egoH = egoEl.offsetHeight || 350;
    var egoR = Math.min(egoW, egoH) / 2 - 65;
    var ecx = egoW / 2;
    var ecy = egoH / 2;

    egoSvg.attr("viewBox", "0 0 " + egoW + " " + egoH);

    // Arrow markers
    var defs = egoSvg.append("defs");
    defs.append("marker").attr("id", "ego-arrow-out")
        .attr("viewBox", "0 0 10 10").attr("refX", 26).attr("refY", 5)
        .attr("markerWidth", 5).attr("markerHeight", 5).attr("orient", "auto")
        .append("path").attr("d", "M 0 0 L 10 5 L 0 10 Z").attr("fill", "#555");

    var egoTooltip = d3.select("#tooltip");

    // Get ego type
    var egoType = "";
    allData.forEach(function(m) {{
        if (m.sender_name === entity) egoType = m.sender_type;
    }});

    // Position partners in a circle around center
    partners.forEach(function(p, i) {{
        var ang = (2 * Math.PI * i / nPartners) - Math.PI / 2;
        p.px = ecx + Math.cos(ang) * egoR;
        p.py = ecy + Math.sin(ang) * egoR;
        p.ang = ang;
    }});

    // Draw edges (center to each partner)
    partners.forEach(function(p) {{
        var total = p.out + p.in;
        var avgSusp = p.totalMsgs > 0 ? (p.totalSusp / p.totalMsgs).toFixed(1) : "0";
        var dominantCat = Object.entries(p.categories).sort(function(a,b){{return b[1]-a[1];}})[0][0];
        var edgeColor = categoryColors[dominantCat] || "#999";
        var suspColor = parseFloat(avgSusp) >= 7 ? "#e6194b" : parseFloat(avgSusp) >= 4 ? "#f58231" : "#3cb44b";

        var dx = p.px - ecx;
        var dy = p.py - ecy;
        var dist = Math.sqrt(dx*dx + dy*dy) || 1;

        if (p.out > 0 && p.in > 0) {{
            // Bidirectional: curve both slightly apart
            var offset = 14;
            var mx1 = (ecx+p.px)/2 + (-dy/dist)*offset;
            var my1 = (ecy+p.py)/2 + (dx/dist)*offset;
            var mx2 = (ecx+p.px)/2 + (dy/dist)*offset;
            var my2 = (ecy+p.py)/2 + (-dx/dist)*offset;

            egoSvg.append("path")
                .attr("d","M"+ecx+","+ecy+" Q"+mx1+","+my1+" "+p.px+","+p.py)
                .attr("fill","none").attr("stroke",edgeColor)
                .attr("stroke-width",Math.max(1.5,Math.min(p.out*1.3,5)))
                .attr("opacity",0.65).attr("marker-end","url(#ego-arrow-out)");
            egoSvg.append("path")
                .attr("d","M"+p.px+","+p.py+" Q"+mx2+","+my2+" "+ecx+","+ecy)
                .attr("fill","none").attr("stroke",edgeColor)
                .attr("stroke-width",Math.max(1,Math.min(p.in*1.1,4)))
                .attr("opacity",0.45).attr("stroke-dasharray","5,3");
        }} else if (p.out > 0) {{
            egoSvg.append("line")
                .attr("x1",ecx).attr("y1",ecy).attr("x2",p.px).attr("y2",p.py)
                .attr("stroke",edgeColor)
                .attr("stroke-width",Math.max(1.5,Math.min(p.out*1.3,5)))
                .attr("opacity",0.65).attr("marker-end","url(#ego-arrow-out)");
        }} else {{
            egoSvg.append("line")
                .attr("x1",p.px).attr("y1",p.py).attr("x2",ecx).attr("y2",ecy)
                .attr("stroke",edgeColor)
                .attr("stroke-width",Math.max(1,Math.min(p.in*1.1,4)))
                .attr("opacity",0.45).attr("stroke-dasharray","5,3");
        }}

        // Invisible wide hover target for edge tooltip
        egoSvg.append("line")
            .attr("x1",ecx).attr("y1",ecy).attr("x2",p.px).attr("y2",p.py)
            .attr("stroke","transparent").attr("stroke-width",14)
            .style("cursor","pointer")
            .on("mouseover",function(event) {{
                var catHTML = Object.entries(p.categories)
                    .sort(function(a,b){{return b[1]-a[1];}})
                    .map(function(kv){{
                        return "<span style='color:"+(categoryColors[kv[0]]||"#999")+"'>&#9632;</span> "+kv[0]+": "+kv[1];
                    }}).join("<br/>");
                egoTooltip.style("display","block")
                    .html(
                        "<strong>"+entity+" &harr; "+p.name+"</strong><br/>"
                        +"<div style='margin:4px 0;padding:4px 8px;background:#f5f5f5;border-radius:4px'>"
                        +"<span style='font-size:16px;font-weight:bold'>"+total+"</span> messages"
                        +" &nbsp;&middot;&nbsp; "
                        +"<span style='font-size:10px'>sent "+p.out+" / received "+p.in+"</span>"
                        +"</div>"
                        +"<div style='margin:3px 0'>"
                        +"Avg suspicion: <strong style='color:"+suspColor+"'>"+avgSusp+"/10</strong>"
                        +" &nbsp;&middot;&nbsp; Max: <strong>"+p.maxSusp+"/10</strong>"
                        +"</div>"
                        +"<div style='margin-top:4px;font-size:11px'>"+catHTML+"</div>"
                    )
                    .style("left",(event.clientX+14)+"px")
                    .style("top",(event.clientY-20)+"px");
            }})
            .on("mouseout",function(){{ egoTooltip.style("display","none"); }});

        // Count label on edge midpoint
        if (total > 1) {{
            var labelDist = dist * 0.45;
            var lx = ecx + (dx/dist)*labelDist;
            var ly = ecy + (dy/dist)*labelDist;
            egoSvg.append("text").attr("x",lx).attr("y",ly-5)
                .attr("text-anchor","middle").style("font-size","9px").style("fill","#555")
                .style("pointer-events","none").text(total);
        }}
    }});

    // Center ego node (on top)
    egoSvg.append("circle").attr("cx",ecx).attr("cy",ecy).attr("r",16)
        .attr("fill",typeColors[egoType]||"#999")
        .attr("stroke","#333").attr("stroke-width",2.5);
    egoSvg.append("circle").attr("cx",ecx).attr("cy",ecy).attr("r",22)
        .attr("fill","none").attr("stroke",typeColors[egoType]||"#999")
        .attr("stroke-width",1.5).attr("opacity",0.3);
    egoSvg.append("text").attr("x",ecx).attr("y",ecy+30)
        .attr("text-anchor","middle").style("font-size","11px").style("font-weight","bold")
        .style("pointer-events","none")
        .text(entity.length>20 ? entity.substring(0,20)+"\u2026" : entity);

    // Partner nodes
    partners.forEach(function(p) {{
        var suspBorder = p.maxSusp >= 7 ? "#e6194b" : p.maxSusp >= 4 ? "#f58231" : "#666";
        var r = 9;
        var g = egoSvg.append("g")
            .attr("transform","translate("+p.px+","+p.py+")")
            .style("cursor","pointer");
        g.append("circle").attr("r",r)
            .attr("fill",typeColors[p.type]||"#999")
            .attr("stroke",suspBorder)
            .attr("stroke-width",p.maxSusp>=4?2.5:1.2);

        var anchor = (p.ang>Math.PI/2||p.ang<-Math.PI/2) ? "end" : "start";
        var lxOff = Math.cos(p.ang)*(r+6);
        var lyOff = Math.sin(p.ang)*(r+6);
        egoSvg.append("text")
            .attr("x",p.px+lxOff).attr("y",p.py+lyOff)
            .attr("text-anchor",anchor).attr("dominant-baseline","middle")
            .style("font-size","9px").style("fill","#333")
            .style("pointer-events","none")
            .text(p.name.length>16?p.name.substring(0,16)+"\u2026":p.name);

        g.on("mouseover",function(event) {{
            d3.select(this).select("circle").attr("stroke","#333").attr("stroke-width",2.5);
            var avgS = p.totalMsgs>0?(p.totalSusp/p.totalMsgs).toFixed(1):"0";
            egoTooltip.style("display","block")
                .html("<strong>"+p.name+"</strong><br/>"+p.type
                    +"<br/>"+p.totalMsgs+" msgs with "+entity
                    +"<br/>Avg susp: "+avgS+"/10 &middot; Max: "+p.maxSusp+"/10")
                .style("left",(event.clientX+12)+"px")
                .style("top",(event.clientY-20)+"px");
        }})
        .on("mouseout",function() {{
            d3.select(this).select("circle")
                .attr("stroke",suspBorder)
                .attr("stroke-width",p.maxSusp>=4?2.5:1.2);
            egoTooltip.style("display","none");
        }})
        .on("click",function() {{
            var fakeMsg = allData.find(function(m){{ return m.sender_name===p.name; }})
                || allData.find(function(m){{ return m.receiver_name===p.name; }});
            if(fakeMsg) {{
                var newMsg = Object.assign({{}},fakeMsg);
                newMsg.sender_name = p.name;
                onMessageClick(newMsg);
            }}
        }});
    }});

    // Legend
    var eLeg = egoSvg.append("g").attr("transform","translate(6,"+(egoH-50)+")");
    eLeg.append("text").attr("x",0).attr("y",0).style("font-size","10px").style("font-weight","bold").text("Entity type:");
    Object.entries(typeColors).forEach(function(e,i) {{
        eLeg.append("circle").attr("cx",8+i*78).attr("cy",14).attr("r",5).attr("fill",e[1]);
        eLeg.append("text").attr("x",16+i*78).attr("y",18).style("font-size","9px").text(e[0]);
    }});
    eLeg.append("line").attr("x1",0).attr("y1",32).attr("x2",18).attr("y2",32)
        .attr("stroke","#888").attr("stroke-width",2);
    eLeg.append("text").attr("x",22).attr("y",36).style("font-size","9px").text("sent");
    eLeg.append("line").attr("x1",56).attr("y1",32).attr("x2",74).attr("y2",32)
        .attr("stroke","#888").attr("stroke-width",1.5).attr("stroke-dasharray","4,3");
    eLeg.append("text").attr("x",78).attr("y",36).style("font-size","9px").text("received");
    eLeg.append("circle").attr("cx",120).attr("cy",32).attr("r",5)
        .attr("fill","none").attr("stroke","#e6194b").attr("stroke-width",2);
    eLeg.append("text").attr("x",128).attr("y",36).style("font-size","9px").text("susp ≥ 7");
    eLeg.append("circle").attr("cx",185).attr("cy",32).attr("r",5)
        .attr("fill","none").attr("stroke","#f58231").attr("stroke-width",2);
    eLeg.append("text").attr("x",193).attr("y",36).style("font-size","9px").text("susp ≥ 4");
    }}

    }} catch(e) {{
    document.getElementById("chart").innerHTML = "<pre style='color:red'>" + e.message + "\\n" + e.stack + "</pre>";
    }}
    </script>
    </body>
    </html>
    """, width="100%", height="850px")

    # === Summary statistics ===
    _mean_susp = round(_df_filtered["suspicion"].mean(), 1) if len(_df_filtered) > 0 else 0
    _max_susp_entity = ""
    _max_susp_val = 0
    if len(_df_filtered) > 0:
        _entity_susp = _df_filtered.groupby("sender_name")["suspicion"].mean()
        if len(_entity_susp) > 0:
            _max_susp_entity = _entity_susp.idxmax()
            _max_susp_val = round(_entity_susp.max(), 1)

    _top_cats = _df_filtered["category"].value_counts().head(4)
    _cat_html = "".join([
        f"<span style='display:inline-block;margin:1px 2px;padding:1px 6px;border-radius:3px;"
        f"font-size:10px;background:{_category_colors.get(c, '#999')};color:white'>"
        f"{c}: {n}</span>"
        for c, n in _top_cats.items()
    ])

    _n_high = len(_df_filtered[_df_filtered["suspicion"] >= 7])
    _n_entities = len(set(
        _df_filtered["sender_name"].tolist() + _df_filtered["receiver_name"].tolist()
    ))

    _stats_panel = mo.md(f"""
    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
    <div style="text-align:center;padding:3px 10px;background:#f5f5f5;border-radius:5px;border:1px solid #e0e0e0">
    <div style="font-size:18px;font-weight:bold;color:#333">{_msg_count}</div>
    <div style="font-size:9px;color:#888">Messages</div></div>
    <div style="text-align:center;padding:3px 10px;background:#f5f5f5;border-radius:5px;border:1px solid #e0e0e0">
    <div style="font-size:18px;font-weight:bold;color:#333">{_n_entities}</div>
    <div style="font-size:9px;color:#888">Entities</div></div>
    <div style="text-align:center;padding:3px 10px;background:#f5f5f5;border-radius:5px;border:1px solid #e0e0e0">
    <div style="font-size:18px;font-weight:bold;color:{'#e6194b' if _mean_susp >= 5 else '#f58231' if _mean_susp >= 3 else '#3cb44b'}">{_mean_susp}</div>
    <div style="font-size:9px;color:#888">Avg Suspicion</div></div>
    <div style="text-align:center;padding:3px 10px;background:#f5f5f5;border-radius:5px;border:1px solid #e0e0e0">
    <div style="font-size:18px;font-weight:bold;color:#e6194b">{_n_high}</div>
    <div style="font-size:9px;color:#888">High Risk (≥7)</div></div>
    <div style="text-align:center;padding:3px 10px;background:#f5f5f5;border-radius:5px;border:1px solid #e0e0e0">
    <div style="font-size:13px;font-weight:bold;color:#333">{_max_susp_entity[:16]}</div>
    <div style="font-size:9px;color:#888">Top Suspect (avg {_max_susp_val})</div></div>
    </div>
    <div style="margin-top:2px">{_cat_html}</div>
    """)

    q1_dashboard = mo.vstack([
        mo.md(f"### Communication Intelligence Dashboard"),
        mo.hstack([
            mo.vstack([
                mo.hstack([category_dropdown, entity_type_dropdown, entity_dropdown, suspicion_slider]),
            ]),
            _stats_panel,
        ], justify="space-between", align="start"),
        _dashboard,
    ])
    return (q1_dashboard,)



@app.cell(hide_code=True)
def _(mo, q1_category_bar, q1_dashboard):
    _q1_page = mo.ui.tabs({
        "Interactive Dashboard": q1_dashboard,
        "Category Overview": q1_category_bar,
    })
    mo.vstack([
        mo.md("# Communication Intelligence Dashboard"),
        mo.md("Interactive analysis of classified radio communications from the Oceanus maritime network."),
        _q1_page,
    ])
    return


if __name__ == "__main__":
    app.run()