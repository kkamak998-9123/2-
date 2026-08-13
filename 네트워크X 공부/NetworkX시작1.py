import networkx as nx
import matplotlib.pyplot as plt

G = nx.DiGraph()

G.add_node("Cash")
G.add_node("Sales")
G.add_node("AR")

G.add_edge("Cash", "Sales", weight=1000)
G.add_edge("AR", "Sales", weight=1500)

print("nodes:", list(G.nodes()))
print("edges:")
for edge in G.edges(data=True):
    print(f" {edge[0]} -> {edge[1]}, weight: {edge[2]['weight']}")
print()

plt.figure(figsize=(10, 8))
pos = nx.spring_layout(G, seed=42)

nx.draw_networkx_nodes(G, pos, node_color = "lightblue", node_size = 500)
nx.draw_networkx_labels(G, pos, font_size=12, font_weight = "bold")
nx.draw_networkx_edges(G, pos, 
                       edge_color = "gray", 
                       width=2, 
                       arrowsize = 30, 
                       arrowstyle='-|>'
                       )
edge_labels = nx.get_edge_attributes(G, 'weight')
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=11)

plt.title("Graph Visualization", fontsize=16)
plt.axis("off")
plt.tight_layout()
plt.savefig("lesson3_practice.png", dpi = 300, bbox_inches = "tight")
plt.show()