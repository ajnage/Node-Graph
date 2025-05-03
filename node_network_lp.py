import networkx as nx
import pulp
import matplotlib.pyplot as plt
import numpy as np

# Step 1: Create directed graph
G = nx.DiGraph()

# Define nodes
G.add_nodes_from(['P1', 'P2', 'P3', 'C1', 'C2', 'C3', 'Premium'])

# Define edges with costs and capacities
edges = [
    ('P1', 'C1', 600, 25),
    ('P1', 'C2', 700, 25),
    ('P1', 'C3', 400, 25),
    ('P2', 'C1', 320, 40),
    ('P2', 'C2', 300, 40),
    ('P2', 'C3', 350, 40),
    ('P3', 'C1', 500, 30),
    ('P3', 'C2', 480, 30),
    ('P3', 'C3', 450, 30),  # Added P3 to C3 connection
    # Add premium backup suppliers for C1 and C2 only (not connected to C3)
    ('Premium', 'C1', 1000, 1000),
    ('Premium', 'C2', 1000, 1000),
]

for u, v, cost, cap in edges:
    G.add_edge(u, v, cost=cost)
    if cap is not None:
        G[u][v]['capacity'] = cap

# Step 2: Define LP problem
prob = pulp.LpProblem("MinCostFlow", pulp.LpMinimize)

# Step 3: Define flow variables for each edge
flow = {}
for u, v in G.edges():
    capacity = G[u][v].get('capacity', None)
    if capacity is not None:
        flow[(u, v)] = pulp.LpVariable(f"flow_{u}_{v}", lowBound=0, upBound=capacity)
    else:
        flow[(u, v)] = pulp.LpVariable(f"flow_{u}_{v}", lowBound=0)

# Step 4: Objective function (minimize cost)
prob += pulp.lpSum(G[u][v]['cost'] * flow[(u, v)] for u, v in G.edges())

# Step 5: Flow conservation constraints
node_balance = {
    'P1': -25,
    'P2': -40,
    'P3': -30,
    'Premium': 0,  # Premium node can supply any amount needed
    'C1': 36,  # 30 + 20%
    'C2': 42,  # 35 + 20%
    'C3': 30,  # 25 + 20%
}

for node in G.nodes():
    inflow = pulp.lpSum(flow[(u, v)] for u, v in G.in_edges(node))
    outflow = pulp.lpSum(flow[(u, v)] for u, v in G.out_edges(node))
    if node == 'Premium':
        # Premium node can supply any amount (no strict balance constraint)
        prob += (inflow - outflow <= 0), f"flow_conservation_{node}"
    else:
        prob += (inflow - outflow == node_balance.get(node, 0)), f"flow_conservation_{node}"

import os
# Step 6: Print node balances, remove old LP file, write LP, then solve
print("Final node balances:", node_balance)
try:
    os.remove("debug_model.lp")
except FileNotFoundError:
    pass
prob.writeLP("debug_model.lp")
result_status = prob.solve()
print("Status:", pulp.LpStatus[result_status])

# Step 7: Output results
if pulp.LpStatus[prob.status] in ('Optimal', 'Feasible'):
    print("\n--- Optimal Flows ---")
    for (u, v), var in flow.items():
        print(f"Flow {u} -> {v}: {var.varValue:.1f}")
    print(f"\nTotal Cost: {pulp.value(prob.objective):.1f}")
else:
    print("\nSolution is infeasible. No flows to display.")

# City-wise Power Distribution Table
if pulp.LpStatus[prob.status] in ('Optimal', 'Feasible'):
    print("\n--- City-wise Power Distribution ---")
    cities = ['C1', 'C2', 'C3']
    sources = ['P1', 'P2', 'P3', 'Premium']
    print(f"{'City':<5} {'From':<8} {'Flow':>8} {'Cost/unit':>10} {'Total Cost':>12}")
    for city in cities:
        for source in sources:
            if (source, city) in flow:
                amount = flow[(source, city)].varValue
                if amount > 0:
                    unit_cost = G[source][city]['cost']
                    total_cost = amount * unit_cost
                    print(f"{city:<5} {source:<8} {amount:>8.1f} {unit_cost:>10.1f} {total_cost:>12.1f}")

# After solving the problem and before drawing the graph, add:
print("\n--- Shadow Prices (Opportunity Cost) ---")
print("These values show the cost reduction ($/unit) if we increase plant capacity by 1 unit")
for name, constraint in prob.constraints.items():
    if name.startswith("flow_conservation_P") and name != "flow_conservation_Premium":  # Only power plant constraints
        plant = name.split('_')[-1]
        shadow_price = -constraint.pi  # Negative because constraints are in form: outflow <= capacity
        current_flow = sum(flow[(plant, city)].varValue for city in ['C1', 'C2', 'C3'] if (plant, city) in flow)
        if plant != 'Premium':
            capacity = -node_balance[plant]  # Capacity is negative of node balance for plants
            print(f"{plant}:")
            print(f"  Current Capacity: {capacity:.1f} million kWh")
            print(f"  Current Usage: {current_flow:.1f} million kWh")
            print(f"  Capacity Utilization: {(current_flow/capacity)*100:.1f}%")
            print(f"  Shadow Price: ${abs(shadow_price):.2f}/unit")
            if abs(shadow_price) < 0.01:
                print("  → No benefit from increasing capacity (plant not at full capacity)")
            else:
                print(f"  → Increasing capacity by 1 unit would reduce total cost by ${abs(shadow_price):.2f}")
            print()

# Add analysis of city demand shadow prices
print("\n--- City Demand Shadow Prices ---")
print("These values show the marginal cost ($/unit) of increasing demand at each city")
for name, constraint in prob.constraints.items():
    if name.startswith("flow_conservation_C"):  # Only city constraints
        city = name.split('_')[-1]
        shadow_price = constraint.pi  # No negative here as constraints are in form: inflow - outflow = demand
        current_demand = node_balance[city]
        total_flow = sum(flow[(p, city)].varValue for p in ['P1', 'P2', 'P3', 'Premium'] if (p, city) in flow)
        
        print(f"{city}:")
        print(f"  Current Demand: {current_demand:.1f} million kWh")
        print(f"  Total Flow Received: {total_flow:.1f} million kWh")
        print(f"  Marginal Cost: ${abs(shadow_price):.2f}/unit")
        
        # Analyze sources of power
        print("  Power Sources:")
        for plant in ['P1', 'P2', 'P3', 'Premium']:
            if (plant, city) in flow and flow[(plant, city)].varValue > 0:
                amount = flow[(plant, city)].varValue
                cost = G[plant][city]['cost']
                print(f"    - {plant}: {amount:.1f} units at ${cost}/unit")
        print()

# Optional: visualize the graph
def draw_graph(G, node_labels=None):
    # Create figure with better proportions and two subplots
    fig = plt.figure(figsize=(20, 16))
    
    # Add table subplot
    ax1 = plt.subplot2grid((4, 1), (0, 0), rowspan=1)
    ax1.axis('off')
    
    # Create table data
    table_data = []
    header = ['Node', 'Type', 'Flow', 'Shadow Price', 'Details']
    table_data.append(header)
    
    # Get shadow prices
    shadow_prices = {}
    for name, constraint in prob.constraints.items():
        if name.startswith("flow_conservation_"):
            node = name.split('_')[-1]
            if node.startswith('P') and node != 'Premium':
                shadow_price = -constraint.pi
            elif node.startswith('C'):
                shadow_price = constraint.pi
            shadow_prices[node] = shadow_price
    
    # Add power plants to table
    for node in sorted([n for n in G.nodes() if n.startswith('P')]):
        outflow = sum(flow[(node, v)].varValue for v in G.neighbors(node))
        if node == 'Premium':
            row = [node, 'Plant', f"{outflow:.1f}", 'N/A', 'Unlimited capacity']
        else:
            sp = shadow_prices.get(node, 0)
            capacity = -node_balance[node]
            row = [node, 'Plant', f"{outflow:.1f}", f"${abs(sp):.0f}", f"Capacity: {capacity:.1f}"]
        table_data.append(row)
    
    # Add cities to table
    for node in sorted([n for n in G.nodes() if n.startswith('C')]):
        inflow = sum(flow[(u, node)].varValue for u in G.predecessors(node))
        sp = shadow_prices.get(node, 0)
        sources = [f"{u}: {flow[(u, node)].varValue:.1f} @ ${G[u][node]['cost']}" 
                  for u in G.predecessors(node) if flow[(u, node)].varValue > 0]
        row = [node, 'City', f"{inflow:.1f}", f"${abs(sp):.0f}", 
               f"Sources: {', '.join(sources)}"]
        table_data.append(row)
    
    # Create and style the table
    table = ax1.table(cellText=table_data,
                     loc='center',
                     cellLoc='center',
                     bbox=[0.1, 0, 0.8, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.8)
    
    # Style header
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold')
            cell.set_facecolor('#e6e6e6')
    
    # Add network diagram subplot
    ax2 = plt.subplot2grid((4, 1), (1, 0), rowspan=3)
    ax2.set_xlim([-10, 10])
    ax2.set_ylim([-8, 8])
    
    # Set fixed manual positions for nodes with better spacing
    pos = {
        'P1': (-7, 4),     # Power plants on left
        'P2': (-7, 0),
        'P3': (-7, -4),
        'Premium': (-7, -7),
        'C1': (7, 4),      # Cities on right
        'C2': (7, 0),
        'C3': (7, -4),
    }
    
    # Simplify node labels to just show the node name
    node_labels = {}
    for node in G.nodes():
        if node.startswith('P') and node != 'Premium':
            capacity = -node_balance[node]
            shadow_price = shadow_prices.get(node, 0)
            node_labels[node] = f"{node}\nS: {capacity:.0f}\nSP: ${abs(shadow_price):.0f}"
        elif node == 'Premium':
            outflow = sum(flow[(node, v)].varValue for v in G.neighbors(node))
            node_labels[node] = f"{node}\nS: ∞\nOut: {outflow:.0f}"
        else:  # Cities
            demand = node_balance[node]
            shadow_price = shadow_prices.get(node, 0)
            node_labels[node] = f"{node}\nD: {demand:.0f}\nSP: ${abs(shadow_price):.0f}"

    # Draw plants (blue)
    plant_nodes = ['P1', 'P2', 'P3', 'Premium']
    nx.draw_networkx_nodes(G, pos, 
                          nodelist=plant_nodes,
                          node_color='lightblue',
                          node_size=3000,  # Increased size for better label visibility
                          edgecolors='steelblue',
                          linewidths=2,
                          ax=ax2)
    
    # Draw cities (green)
    city_nodes = ['C1', 'C2', 'C3']
    nx.draw_networkx_nodes(G, pos, 
                          nodelist=city_nodes,
                          node_color='lightgreen',
                          node_size=3000,  # Increased size for better label visibility
                          edgecolors='forestgreen',
                          linewidths=2,
                          ax=ax2)
    
    # Draw node labels with smaller font
    nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=9)
    
    # Draw edges with better visibility and color coding
    for (u, v) in G.edges():
        if flow[(u, v)].varValue > 0:
            start = np.array(pos[u])
            end = np.array(pos[v])
            
            cost = G[u][v]['cost']
            if cost >= 1000:
                edge_color = 'red'
            elif cost >= 400:
                edge_color = 'orange'
            else:
                edge_color = 'gray'
            
            # Draw edge with arrow
            ax2.arrow(start[0], start[1],
                     end[0] - start[0], end[1] - start[1],
                     head_width=0.2,
                     head_length=0.3,
                     fc=edge_color,
                     ec=edge_color,
                     length_includes_head=True,
                     alpha=0.6,
                     linewidth=2)
            
            flow_val = flow[(u, v)].varValue
            total_cost = cost * flow_val
            label = f"{flow_val:.1f}\n${cost:,.0f}/unit\n${total_cost:,.0f}"
            
            # Calculate angle of the edge for label rotation
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            angle = np.degrees(np.arctan2(dy, dx))
            
            # Position label along the edge
            label_pos = start + (end - start) * 0.35
            
            # Add label with white background
            ax2.annotate(label,
                        xy=label_pos,
                        xytext=label_pos,
                        textcoords='data',
                        ha='center',
                        va='center',
                        rotation=angle,
                        bbox=dict(facecolor='white',
                                edgecolor=edge_color,
                                alpha=0.8,
                                pad=1,
                                boxstyle='round'),
                        fontsize=8)
    
    # Add title and section labels
    ax2.set_title("Power Distribution Network\nOptimal Flow Solution", 
                  pad=20, fontsize=16, fontweight='bold')
    ax2.text(-9, 6, "Power Plants", fontsize=12, fontweight='bold')
    ax2.text(6, 6, "Cities", fontsize=12, fontweight='bold')
    
    # Add legend
    legend_elements = [
        plt.Line2D([0], [0], color='gray', label='Normal Cost', linewidth=2),
        plt.Line2D([0], [0], color='orange', label='High Cost (≥$400)', linewidth=2),
        plt.Line2D([0], [0], color='red', label='Premium Cost ($1000)', linewidth=2)
    ]
    ax2.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, -0.05))
    
    ax2.axis('off')
    plt.tight_layout()
    
    # Save the figure before showing it
    plt.savefig('network_visualization.png', dpi=300, bbox_inches='tight')
    
    plt.show()

if __name__ == "__main__":
    # Calculate inflow, outflow, and net balance for annotation
    node_flow_info = {}
    for node in G.nodes():
        inflow_val = sum(flow[(u, v)].varValue for u, v in G.in_edges(node))
        outflow_val = sum(flow[(u, v)].varValue for u, v in G.out_edges(node))
        net_balance = inflow_val - outflow_val
        node_flow_info[node] = (
            f"{node}\n"
            f"in:{inflow_val:.0f}\n"
            f"out:{outflow_val:.0f}\n"
            f"bal:{net_balance:.0f}"
        )
    draw_graph(G, node_labels=node_flow_info)