import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np

df = pd.read_csv('분개장_06회_1급_2.csv', encoding='utf-8-sig')
company_name = "Company"

# 원재료 (차변금액) - TOP 20
raw_materials = df[df['계정명'] == '원재료']
inflow_data = raw_materials.groupby('거래처코드')['차변금액'].sum().reset_index()
inflow_data.columns = ['vendor_code', 'amount']
inflow_data = inflow_data[inflow_data['amount'] > 0].dropna()
inflow_data = inflow_data.nlargest(20, 'amount')

# 외상매출금 (대변금액) - TOP 20
accounts_receivable = df[df['계정명'].str.contains('외상매출금', na=False)]
outflow_data = accounts_receivable.groupby('거래처코드')['대변금액'].sum().reset_index()
outflow_data.columns = ['vendor_code', 'amount']
outflow_data = outflow_data[outflow_data['amount'] > 0].dropna()
outflow_data = outflow_data.nlargest(20, 'amount')

# 엣지 생성
edges = []
for idx, row in inflow_data.iterrows():
    vendor = int(row['vendor_code'])
    edges.append({
        'from': f'Vendor {vendor}',
        'to': company_name,
        'amount': row['amount'],
        'type': 'inflow'
    })

for idx, row in outflow_data.iterrows():
    vendor = int(row['vendor_code'])
    edges.append({
        'from': company_name,
        'to': f'Vendor {vendor}',
        'amount': row['amount'],
        'type': 'outflow'
    })

# NetworkX 그래프
G = nx.DiGraph()
G.add_node(company_name, node_type='company')

for idx, row in inflow_data.iterrows():
    vendor = int(row['vendor_code'])
    G.add_node(f'Vendor {vendor}', node_type='inflow')

for idx, row in outflow_data.iterrows():
    vendor = int(row['vendor_code'])
    G.add_node(f'Vendor {vendor}', node_type='outflow')

for edge in edges:
    G.add_edge(edge['from'], edge['to'],
               weight=edge['amount'],
               edge_type=edge['type'])

# 수동 레이아웃: 왼쪽 → 중앙 → 오른쪽
pos = {}
pos[company_name] = [0, 0]

# 왼쪽: 원형 배치
inflow_vendors = [f'Vendor {int(v)}' for v in inflow_data['vendor_code']]
n_inflow = len(inflow_vendors)
for i, vendor in enumerate(inflow_vendors):
    angle = 2 * np.pi * i / n_inflow
    x = -3 + 0.5 * np.cos(angle)
    y = 3 * np.sin(angle)
    pos[vendor] = [x, y]

# 오른쪽: 원형 배치
outflow_vendors = [f'Vendor {int(v)}' for v in outflow_data['vendor_code']]
n_outflow = len(outflow_vendors)
for i, vendor in enumerate(outflow_vendors):
    angle = 2 * np.pi * i / n_outflow
    x = 3 + 0.5 * np.cos(angle)
    y = 3 * np.sin(angle)
    pos[vendor] = [x, y]

# 시각화
fig, ax = plt.subplots(figsize=(24, 16))

# 노드
node_colors = []
for node in G.nodes():
    if node == company_name:
        node_colors.append('gold')
    elif G.nodes[node].get('node_type') == 'inflow':
        node_colors.append('lightgreen')
    else:
        node_colors.append('lightcoral')

node_sizes = [5000 if n == company_name else 2000 for n in G.nodes()]

nx.draw_networkx_nodes(G, pos, ax=ax,
                       node_color=node_colors,
                       node_size=node_sizes,
                       alpha=0.9,
                       edgecolors='black',
                       linewidths=2)

nx.draw_networkx_labels(G, pos, ax=ax, font_size=10, font_weight='bold')

# 유입 (녹색)
inflow_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('edge_type') == 'inflow']
if inflow_edges:
    inflow_widths = [min(G[u][v]['weight'] / 100000000, 5) for u, v in inflow_edges]
    nx.draw_networkx_edges(G, pos, ax=ax,
                           edgelist=inflow_edges,
                           edge_color='green',
                           width=inflow_widths,
                           alpha=0.6,
                           arrowsize=25,
                           arrowstyle='->',
                           connectionstyle='arc3,rad=0.1')

# 유출 (빨간색)
outflow_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('edge_type') == 'outflow']
if outflow_edges:
    outflow_widths = [min(G[u][v]['weight'] / 100000000, 5) for u, v in outflow_edges]
    nx.draw_networkx_edges(G, pos, ax=ax,
                           edgelist=outflow_edges,
                           edge_color='red',
                           width=outflow_widths,
                           alpha=0.6,
                           arrowsize=25,
                           arrowstyle='->',
                           connectionstyle='arc3,rad=0.1')

ax.set_title('Account-Based Network\nInflow → Company → Outflow', 
             fontsize=18, fontweight='bold')
ax.axis('off')
plt.tight_layout()
plt.savefig('account_network_clean.png', dpi=300, bbox_inches='tight')
plt.show()