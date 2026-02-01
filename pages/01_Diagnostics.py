import streamlit as st
import pandas as pd
import io

from data_utils import (
    load_data,
    generate_edge_list,
    build_graph,
    diagnostics_summary,
    find_nodes_with_missing_coords,
    find_isolated_nodes,
    edge_weight_distribution,
    strongest_edges
)

# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(
    page_title="Diagnostics",
    layout="wide"
)

st.title("Diagnostics & Sanity Checks")

# --------------------------------------------------
# Load data
# --------------------------------------------------
meta, nodes, matrix = load_data("supply_chain_dummy_data.xlsx")

# --------------------------------------------------
# Generate edges (on demand)
# --------------------------------------------------
st.header("Edge list generation")

if st.button("Generate edge list from matrix"):
    st.session_state["edges_generated"] = generate_edge_list(nodes, matrix)

# --------------------------------------------------
# Use generated edges if available
# --------------------------------------------------
edges = st.session_state.get("edges_generated")

if edges is not None:
    G = build_graph(nodes, edges)

    # --------------------------------------------------
    # High-level diagnostics
    # --------------------------------------------------
    st.header("High-level consistency checks")

    summary = diagnostics_summary(nodes, edges, G)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Nodes", summary["node_count"])
        st.metric("Graph nodes", summary["graph_nodes"])

    with col2:
        st.metric("Edges", summary["edge_count"])
        st.metric("Graph edges", summary["graph_edges"])

    with col3:
        st.metric("Regions", summary["region_count"])

    # --------------------------------------------------
    # Node diagnostics
    # --------------------------------------------------
    st.header("Node diagnostics")

    missing_coords = find_nodes_with_missing_coords(nodes)

    if missing_coords.empty:
        st.success("All nodes have valid coordinates")
    else:
        st.warning("Some nodes have missing coordinates")
        st.dataframe(missing_coords)

    isolated_nodes = find_isolated_nodes(G)

    if isolated_nodes:
        st.warning("Some nodes are isolated")
        st.write(isolated_nodes)

    # --------------------------------------------------
    # Edge diagnostics
    # --------------------------------------------------
    st.header("Edge diagnostics")

    st.subheader("Edge weight distribution")
    st.dataframe(edge_weight_distribution(edges))

    st.subheader("Strongest dependencies")
    st.dataframe(strongest_edges(edges))

    # --------------------------------------------------
    # Export
    # --------------------------------------------------
    st.header("Export")

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        edges.to_excel(
            writer,
            sheet_name="EDGES",
            index=False
        )

    st.download_button(
        label="Download EDGES.xlsx",
        data=output.getvalue(),
        file_name="EDGES.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("Generate the edge list to view diagnostics and export.")



