import pandas as pd
import networkx as nx
import streamlit as st

# --------------------------------------------------
# Data loading
# --------------------------------------------------
@st.cache_data
def load_data(path):
    xls = pd.ExcelFile(path)
    meta = pd.read_excel(xls, "META")
    nodes = pd.read_excel(xls, "NODES")
    matrix = pd.read_excel(xls, "MATRIX")
    return meta, nodes, matrix


# --------------------------------------------------
# Edge & graph construction
# --------------------------------------------------
def build_edges(nodes, matrix):
    edges = []
    node_ids = nodes["id"].tolist()

    for _, row in matrix.iterrows():
        src = row["FROM/TO"]
        for tgt in node_ids:
            w = row[tgt]
            if w > 0:
                edges.append({
                    "from": src,
                    "to": tgt,
                    "weight": w
                })

    return pd.DataFrame(edges)


def generate_edge_list(nodes, matrix):
    edges = build_edges(nodes, matrix)

    # Editable scaffolding for non-expert users
    edges["type"] = "material"
    edges["notes"] = ""
    edges["active"] = True

    return edges


def build_graph(nodes, edges):
    G = nx.MultiDiGraph()

    for _, row in nodes.iterrows():
        G.add_node(row["id"], **row.to_dict())

    for _, row in edges.iterrows():
        G.add_edge(
            row["from"],
            row["to"],
            weight=row["weight"],
            type=row.get("type", None),
            active=row.get("active", True)
        )

    return G


# --------------------------------------------------
# Diagnostics & validation helpers
# --------------------------------------------------
def diagnostics_summary(nodes, edges, graph):
    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "graph_nodes": graph.number_of_nodes(),
        "graph_edges": graph.number_of_edges(),
        "region_count": nodes["region"].nunique(),
    }


def find_nodes_with_missing_coords(nodes):
    return nodes[
        nodes["latitude"].isna() |
        nodes["longitude"].isna()
    ]


def find_isolated_nodes(graph):
    return [
        n for n in graph.nodes
        if graph.in_degree(n) == 0 and graph.out_degree(n) == 0
    ]


def edge_weight_distribution(edges):
    return edges["weight"].value_counts().sort_index()


def strongest_edges(edges, n=10):
    return edges.sort_values("weight", ascending=False).head(n)

# --------------------------------------------------
# Dependency computations
# --------------------------------------------------
def compute_dependency_subgraph(
    graph,
    focus_node,
    max_depth=1
):
    """
    Returns sets of upstream nodes, downstream nodes,
    and the induced subgraph containing only relevant edges.
    """

    if focus_node is None or focus_node not in graph:
        return set(), set(), graph

    upstream = set()
    downstream = set()

    # Upstream traversal
    current = {focus_node}
    for _ in range(max_depth):
        parents = set()
        for n in current:
            parents |= set(graph.predecessors(n))
        upstream |= parents
        current = parents

    # Downstream traversal
    current = {focus_node}
    for _ in range(max_depth):
        children = set()
        for n in current:
            children |= set(graph.successors(n))
        downstream |= children
        current = children

    relevant_nodes = upstream | downstream | {focus_node}

    subgraph = graph.subgraph(relevant_nodes).copy()

    return upstream, downstream, subgraph

def classify_nodes(focus_node, upstream, downstream):
    """
    Returns a dict: node_id -> role
    """
    roles = {}

    for n in upstream:
        roles[n] = "upstream"

    for n in downstream:
        roles[n] = "downstream"

    if focus_node is not None:
        roles[focus_node] = "focus"

    return roles


def compute_impact_metrics(
    graph,
    nodes_df,
    focus_node,
    max_depth=1
):
    """
    Computes upstream and downstream impact metrics
    for a given focus node.
    """

    if focus_node is None or focus_node not in graph:
        return {
            "upstream_count": 0,
            "downstream_count": 0,
            "regions_affected": 0,
            "downstream_weight": 0
        }

    # --- Upstream ---
    upstream = set()
    current = {focus_node}

    for _ in range(max_depth):
        parents = set()
        for n in current:
            parents |= set(graph.predecessors(n))
        upstream |= parents
        current = parents

    # --- Downstream ---
    downstream = set()
    current = {focus_node}

    for _ in range(max_depth):
        children = set()
        for n in current:
            children |= set(graph.successors(n))
        downstream |= children
        current = children

    # --- Regions affected ---
    downstream_nodes_df = nodes_df[
        nodes_df["id"].isin(downstream)
    ]

    regions_affected = downstream_nodes_df["region"].nunique()

    # --- Total downstream dependency weight ---
    downstream_weight = 0

    for u, v, data in graph.edges(data=True):
        if u in downstream or u == focus_node:
            if v in downstream:
                downstream_weight += data.get("weight", 0)

    return {
        "upstream_count": len(upstream),
        "downstream_count": len(downstream),
        "regions_affected": regions_affected,
        "downstream_weight": downstream_weight
    }


