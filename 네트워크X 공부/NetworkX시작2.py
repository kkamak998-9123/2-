import networkx as nx
import matplotlib.pyplot as plt

print("=" * 70)
print("LESSON 4: Graph Analysis")
print("=" * 70)
print()

# 그래프 생성
G = nx.DiGraph()

# 노드 추가
accounts = ["Cash", "Sales", "AR", "Expense", "Vendor_Payable"]
G.add_nodes_from(accounts)

# 거래 추가 (source, target, amount)
transactions = [
    ("Cash", "Expense", 500),
    ("AR", "Sales", 1000),
    ("Cash", "Sales", 2000),
    ("Vendor_Payable", "Expense", 300),
    ("Sales", "Cash", 1500),
]

for source, target, amount in transactions:
    G.add_edge(source, target, weight=amount)

print("=" * 70)
print("Step 1: Basic Graph Info")
print("=" * 70)
print(f"Number of nodes: {G.number_of_nodes()}")
print(f"Number of edges: {G.number_of_edges()}")
print(f"Nodes: {list(G.nodes())}")
print()

print("=" * 70)
print("Step 2: Degree Analysis")
print("=" * 70)
print()

print("In-Degree (Incoming transactions):")
for node in G.nodes():
    in_degree = G.in_degree(node)
    print(f"  {node}: {in_degree}")
print()

print("Out-Degree (Outgoing transactions):")
for node in G.nodes():
    out_degree = G.out_degree(node)
    print(f"  {node}: {out_degree}")
print()

print("=" * 70)
print("Step 3: Path Finding")
print("=" * 70)
print()

# Cash에서 Expense까지 경로 찾기
try:
    path = nx.shortest_path(G, "Cash", "Expense")
    print(f"Path from Cash to Expense: {' -> '.join(path)}")
except nx.NetworkXNoPath:
    print("No path from Cash to Expense")

# AR에서 Cash까지 경로 찾기
try:
    path = nx.shortest_path(G, "AR", "Cash")
    print(f"Path from AR to Cash: {' -> '.join(path)}")
except nx.NetworkXNoPath:
    print("No path from AR to Cash")

print()

print("=" * 70)
print("Step 4: Centrality Analysis")
print("=" * 70)
print()

print("In-Degree Centrality (Most important accounts):")
in_centrality = nx.in_degree_centrality(G)
sorted_in = sorted(in_centrality.items(), key=lambda x: x[1], reverse=True)
for account, score in sorted_in:
    print(f"  {account}: {score:.3f}")
print()

print("Out-Degree Centrality:")
out_centrality = nx.out_degree_centrality(G)
sorted_out = sorted(out_centrality.items(), key=lambda x: x[1], reverse=True)
for account, score in sorted_out:
    print(f"  {account}: {score:.3f}")
print()

print("=" * 70)
print("Step 5: Cycle Detection")
print("=" * 70)
print()

# 순환 거래가 있는지 확인
try:
    cycle = nx.find_cycle(G)
    print(f"WARNING: Circular transaction found!")
    print(f"Cycle: {cycle}")
except nx.NetworkXNoCycle:
    print("OK: No circular transactions found")
print()

print("=" * 70)
print("Step 6: Transaction Summary")
print("=" * 70)
print()

total_amount = 0
print("All transactions:")
for source, target, data in G.edges(data=True):
    amount = data['weight']
    print(f"  {source} -> {target}: ${amount}")
    total_amount += amount

print(f"\nTotal transaction amount: ${total_amount}")
print()

# 그래프 시각화
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# 왼쪽: 기본 거래 흐름
ax1 = axes[0]
pos = nx.spring_layout(G, seed=42, k=2)

nx.draw_networkx_nodes(G, pos, ax=ax1, node_color="lightblue", node_size=3000)
nx.draw_networkx_labels(G, pos, ax=ax1, font_size=10, font_weight="bold")
nx.draw_networkx_edges(G, pos, ax=ax1, 
                       edge_color="gray", width=2,
                       arrowsize=20, arrowstyle='-|>',
                       connectionstyle="arc3,rad=0.1")

edge_labels = nx.get_edge_attributes(G, 'weight')
edge_labels = {k: f"${v}" for k, v in edge_labels.items()}
nx.draw_networkx_edge_labels(G, pos, edge_labels, ax=ax1, font_size=9)

ax1.set_title("Transaction Flow", fontsize=14, fontweight="bold")
ax1.axis("off")

# 오른쪽: 중심성 분석 (노드 크기로 중요도 표현)
ax2 = axes[1]

in_centrality = nx.in_degree_centrality(G)
node_sizes = [in_centrality[node] * 5000 for node in G.nodes()]
node_colors = [in_centrality[node] for node in G.nodes()]

nx.draw_networkx_nodes(G, pos, ax=ax2, 
                       node_color=node_colors, node_size=node_sizes,
                       cmap="YlOrRd", vmin=0, vmax=0.5)
nx.draw_networkx_labels(G, pos, ax=ax2, font_size=10, font_weight="bold")
nx.draw_networkx_edges(G, pos, ax=ax2,
                       edge_color="gray", width=2,
                       arrowsize=20, arrowstyle='-|>',
                       connectionstyle="arc3,rad=0.1")

ax2.set_title("Centrality Analysis (Node Size = Importance)", fontsize=14, fontweight="bold")
ax2.axis("off")

plt.tight_layout()
plt.savefig("lesson4_analysis.png", dpi=300, bbox_inches='tight')
print("Saved: lesson4_analysis.png")
plt.show()