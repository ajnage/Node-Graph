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
    if name.startswith("flow_conservation_P"):  # Only power plant constraints
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

# Optional: visualize the graph
def draw_graph(G, node_labels=None):
    # Create figure with better proportions
    fig = plt.figure(figsize=(20, 12))  # Wider figure, shorter height
    
    # Create single subplot for the entire visualization
    ax = plt.gca()
    ax.set_xlim([-10, 10])
    ax.set_ylim([-8, 8])
    
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
    
    # Get shadow prices for plants
    shadow_prices = {}
    for name, constraint in prob.constraints.items():
        if name.startswith("flow_conservation_P") and name != "flow_conservation_Premium":
            plant = name.split('_')[-1]
            shadow_price = -constraint.pi
            shadow_prices[plant] = shadow_price

    # Update node labels with cleaner formatting
    node_labels = {}
    for node in G.nodes():
        inflow_val = sum(flow[(u, v)].varValue for u, v in G.in_edges(node))
        outflow_val = sum(flow[(u, v)].varValue for u, v in G.out_edges(node))
        net_balance = inflow_val - outflow_val
        
        if node.startswith('P') and node != 'Premium':
            shadow_price = shadow_prices.get(node, 0)
            node_labels[node] = (
                f"{node}\n"
                f"Out: {outflow_val:.0f}\n"
                f"SP: ${abs(shadow_price):.0f}"
            )
        elif node == 'Premium':
            node_labels[node] = (
                f"{node}\n"
                f"Out: {outflow_val:.0f}"
            )
        else:  # Cities
            node_labels[node] = (
                f"{node}\n"
                f"In: {inflow_val:.0f}"
            )

    # Draw plants (blue) with adjusted size
    plant_nodes = ['P1', 'P2', 'P3', 'Premium']
    nx.draw_networkx_nodes(G, pos, 
                          nodelist=plant_nodes,
                          node_color='lightblue',
                          node_size=2500,
                          edgecolors='steelblue',
                          linewidths=2)
    
    # Draw cities (green)
    city_nodes = ['C1', 'C2', 'C3']
    nx.draw_networkx_nodes(G, pos, 
                          nodelist=city_nodes,
                          node_color='lightgreen',
                          node_size=2500,
                          edgecolors='forestgreen',
                          linewidths=2)
    
    # Draw node labels
    nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=10)

    # Draw edges with better visibility and color coding
    edge_labels = []
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
            plt.arrow(start[0], start[1],
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
            label = f"Flow: {flow_val:.1f}\nCost: ${cost:,.0f}\nTotal: ${total_cost:,.0f}"
            
            # Calculate midpoint and offset for label
            # Position labels closer to the power plants (source nodes)
            # Use 0.25 as the interpolation factor (closer to start point)
            label_pos = start + (end - start) * 0.25
            
            # Add small vertical offset to prevent overlap with edges
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length = np.sqrt(dx*dx + dy*dy)
            normal = np.array([-dy/length, dx/length])
            label_pos = label_pos + normal * 0.4
            
            # Add label with white background
            plt.annotate(label,
                        xy=label_pos,  # Changed from mid_point to label_pos
                        xytext=label_pos,
                        textcoords='data',
                        ha='center',
                        va='center',
                        bbox=dict(facecolor='white',
                                edgecolor=edge_color,
                                alpha=0.8,
                                pad=2,
                                boxstyle='round'),
                        fontsize=9)
    
    # Add title and section labels with better positioning
    plt.title("Power Distribution Network\nOptimal Flow Solution", 
              pad=20, fontsize=16, fontweight='bold')
    plt.text(-9, 6, "Power Plants", fontsize=12, fontweight='bold')
    plt.text(6, 6, "Cities", fontsize=12, fontweight='bold')
    
    # Add legend with better positioning
    legend_elements = [
        plt.Line2D([0], [0], color='gray', label='Normal Cost', linewidth=2),
        plt.Line2D([0], [0], color='orange', label='High Cost (≥$400)', linewidth=2),
        plt.Line2D([0], [0], color='red', label='Premium Cost ($1000)', linewidth=2)
    ]
    plt.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, -0.05))
    
    plt.axis('off')
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