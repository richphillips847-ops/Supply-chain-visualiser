import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from data_utils import (
    load_data,
    build_graph,
    compute_dependency_subgraph,
    classify_nodes,
    build_edges,
    compute_impact_metrics
)

# --------------------------------------------------
# Page setup
# --------------------------------------------------
st.set_page_config(
    page_title="Supply Chain Dependency Map",
    layout="wide"
)

# --------------------------------------------------
# Load data
# --------------------------------------------------
meta, nodes, matrix = load_data("supply_chain_dummy_data1.xlsx")
meta_dict = dict(zip(meta["key"], meta["value"]))

# --------------------------------------------------
# Build edges + graph (single source of truth)
# --------------------------------------------------
edges = build_edges(nodes, matrix)
G = build_graph(nodes, edges)

# --------------------------------------------------
# Geographic positions
# --------------------------------------------------
geo_pos = {
    row["id"]: (row["longitude"], row["latitude"])
    for _, row in nodes.iterrows()
}

# --------------------------------------------------
# Map figure (pure presentation)
# --------------------------------------------------
def build_map_figure(filtered_nodes, filtered_edges, node_roles, geo_pos):
    edge_traces = []

    for _, row in filtered_edges.iterrows():
        u, v, w = row["from"], row["to"], row["weight"]
        lon0, lat0 = geo_pos[u]
        lon1, lat1 = geo_pos[v]

        edge_traces.append(
            go.Scattergeo(
                lon=[lon0, lon1],
                lat=[lat0, lat1],
                mode="lines",
                line=dict(width=1, color="gray"),
                hoverinfo="text",
                text=f"{u} → {v} | weight {w}",
                showlegend=False
            )
        )

    color_map = {
        "focus": "gold",
        "upstream": "firebrick",
        "downstream": "steelblue"
    }

    node_colors = [
        color_map.get(node_roles.get(n), "lightgray")
        for n in filtered_nodes["id"]
    ]

    node_trace = go.Scattergeo(
        lon=filtered_nodes["longitude"],
        lat=filtered_nodes["latitude"],
        mode="markers",
        hoverinfo="text",
        text=filtered_nodes["label"],
        marker=dict(
            size=8,
            color=node_colors,
            line=dict(width=1, color="black")
        ),
        showlegend=False
    )

    fig = go.Figure(edge_traces + [node_trace])

    fig.update_layout(
        title=None,
        geo=dict(
            projection_type="miller",
            showland=True,
            landcolor="rgb(245,245,245)",
            showocean=True,
            oceancolor="rgb(230,236,245)",
            showcountries=True,
            countrycolor="rgb(180,180,180)",
            showcoastlines=True,
            coastlinecolor="rgb(170,170,170)",
            showframe=False,
            bgcolor="white",
        ),
        margin=dict(l=20, r=20, t=20, b=20),
        height=650
    )

    return fig

# --------------------------------------------------
# Sidebar controls
# --------------------------------------------------
st.sidebar.markdown("## Supply Chain Dependency Map")

regions = sorted(nodes["region"].unique())
selected_regions = st.sidebar.multiselect("Regions", regions, default=regions)

min_weight = st.sidebar.slider(
    "Minimum dependency weight",
    min_value=1,
    max_value=int(edges["weight"].max()),
    value=1
)

nodes_sorted = nodes.sort_values("size", ascending=False)
node_options = dict(zip(nodes_sorted["label"], nodes_sorted["id"]))

focus_label = st.sidebar.selectbox("Focus node", node_options.keys())
focus_node = node_options[focus_label]

depth = st.sidebar.slider("Degrees of separation", 1, 5, 1)

view_mode = st.sidebar.radio(
    "Dependency view",
    options=["Downstream", "Upstream", "Both"],
    index=0  # default to Downstream
)


# --------------------------------------------------
# Filtering
# --------------------------------------------------
filtered_nodes = nodes[nodes["region"].isin(selected_regions)]

filtered_edges = edges[
    (edges["from"].isin(filtered_nodes["id"])) &
    (edges["to"].isin(filtered_nodes["id"])) &
    (edges["weight"] >= min_weight)
]

# --------------------------------------------------
# Dependency analysis (delegated)
# --------------------------------------------------
upstream, downstream, subgraph = compute_dependency_subgraph(
    G,
    focus_node,
    max_depth=depth
)

if view_mode == "Downstream":
    visible_nodes = {focus_node} | downstream
elif view_mode == "Upstream":
    visible_nodes = {focus_node} | upstream
else:  # Both
    visible_nodes = {focus_node} | upstream | downstream


impact = compute_impact_metrics(
    G,
    nodes,
    focus_node,
    max_depth=depth
)


node_roles = classify_nodes(focus_node, upstream, downstream)


# Apply region + visibility filtering
filtered_nodes = nodes[
    (nodes["region"].isin(selected_regions)) &
    (nodes["id"].isin(visible_nodes))
]

filtered_edges = edges[
    (edges["from"].isin(visible_nodes)) &
    (edges["to"].isin(visible_nodes)) &
    (edges["weight"] >= min_weight)
]


st.subheader("Impact metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Upstream dependencies", impact["upstream_count"])

with col2:
    st.metric("Downstream impacts", impact["downstream_count"])

with col3:
    st.metric("Regions affected", impact["regions_affected"])

with col4:
    st.metric("Total downstream weight", impact["downstream_weight"])


# --------------------------------------------------
# Render
# --------------------------------------------------
fig = build_map_figure(
    filtered_nodes,
    filtered_edges,
    node_roles,
    geo_pos
)



st.markdown(
    f"""
    ### Focus: {focus_label}

    Showing **upstream dependencies** (red) and **downstream impacts** (blue)  
    up to **{depth} degree(s) of separation**.

    Filters applied:
    - Regions
    - Minimum weight ≥ {min_weight}
    """
)

st.plotly_chart(fig, use_container_width=True)



