# Power Distribution Network Optimization

This project implements a power distribution network optimization model using Python, solving the minimum cost flow problem for power distribution from plants to cities.

## Original Problem Statement

Three electric power plants with capacities of 25, 40, and 30 million kWh supply electricity to three cities. The maximum demands at the three cities are estimated at 30, 35, and 25 million kWh. During the month of August, there is a 20% increase in demand at each of the three cities, which can be met by purchasing electricity from another network at a premium rate of $1000 per million kWh. The network is not linked to city 3, however.

The price per million kWh at the three cities is given in the following table:

| Plant | City 1 | City 2 | City 3 |
| ----- | ------ | ------ | ------ |
| P1    | $600   | $700   | $400   |
| P2    | $320   | $300   | $350   |
| P3    | $500   | $480   | $450   |

The utility company needs to determine:

1. The most economical plan for the distribution and purchase of additional energy
2. The optimal distribution plan
3. The cost of the additional power purchased by each of the three cities

## Solution Overview

This implementation provides:

- A complete transportation model formulation
- Optimal distribution plan visualization
- Analysis of additional power purchases and costs
- Shadow price analysis for capacity planning

## Problem Description

The model optimizes power distribution from multiple power plants (P1, P2, P3, and a Premium source) to three cities (C1, C2, C3), considering:

- Plant capacity constraints
- City demand requirements (with 20% safety margin)
- Transmission costs
- Network flow constraints

## Visualization

![Power Distribution Network Optimization](network_visualization.png)

### Network Components:

- **Blue Nodes**: Power Plants (including shadow prices)
- **Green Nodes**: Cities (with demand requirements)
- **Edge Colors**:
  - Gray: Normal cost routes
  - Orange: High cost routes (≥$400)
  - Red: Premium cost routes ($1000)

## Solution Visualization

The solution consists of two parts:

### 1. Network Summary Table

| Node    | Type  | Flow | Shadow Price | Details                                        |
| ------- | ----- | ---- | ------------ | ---------------------------------------------- |
| P1      | Plant | 25.0 | $400         | Capacity: 25.0                                 |
| P2      | Plant | 40.0 | $680         | Capacity: 40.0                                 |
| P3      | Plant | 30.0 | $500         | Capacity: 30.0                                 |
| Premium | Plant | 13.0 | N/A          | Unlimited capacity                             |
| C1      | City  | 36.0 | $1000        | Sources: P3: 23.0 @ $500, Premium: 13.0 @$1000 |
| C2      | City  | 42.0 | $980         | Sources: P2: 40.0 @ $300, P3: 2.0 @$480        |
| C3      | City  | 30.0 | $950         | Sources: P1: 25.0 @ $400, P3: 5.0 @$450        |

### 2. Network Flow Diagram

![Power Distribution Network Optimization](network_visualization.png)

The visualization shows:

- **Nodes**:
  - Blue circles: Power plants with supply (S) and shadow price (SP)
  - Green circles: Cities with demand (D) and shadow price (SP)
- **Edges**:
  - Gray: Normal cost routes (<$400/unit)
  - Orange: High cost routes (≥$400/unit)
  - Red: Premium cost routes ($1000/unit)
- **Edge Labels**: Show flow amount, cost per unit, and total cost
- **Node Labels**: Display supply/demand and shadow prices

### Key Solution Features:

1. **Optimal Flow Distribution**:

   - All base plants (P1, P2, P3) operating at full capacity
   - Premium source used only for C1's excess demand
   - P3 split among all three cities for optimal cost

2. **Cost Structure**:

   - Total system cost: $49,710
   - Premium power used only when necessary
   - Efficient utilization of lower-cost routes

3. **Shadow Prices**:
   - Plants: Range from $400-$680/unit
   - Cities: Range from $950-$1000/unit
   - Indicates high value of capacity expansion

## Key Features

1. **Power Plants**:

   - P1: 25 million kWh capacity
   - P2: 40 million kWh capacity
   - P3: 30 million kWh capacity
   - Premium: Unlimited capacity (backup source)

2. **Cities (Demand + 20% margin)**:

   - C1: 36 million kWh
   - C2: 42 million kWh
   - C3: 30 million kWh

3. **Optimization Results**:
   - Total System Cost: $49,710
   - All base plants operating at full capacity
   - Premium source used for additional demand
   - Shadow prices showing opportunity costs for capacity increases

## Implementation Details

The solution uses:

- `NetworkX`: For network modeling and visualization
- `PuLP`: For linear programming optimization
- `Matplotlib`: For visualization rendering

## Shadow Prices Analysis

### Power Plant Shadow Prices

The shadow prices for power plants indicate potential cost savings per unit of capacity increase:

- P1: $400/unit - Would reduce total cost by $400 per unit of additional capacity
- P2: $680/unit - Would reduce total cost by $680 per unit of additional capacity
- P3: $500/unit - Would reduce total cost by $500 per unit of additional capacity

All power plants are operating at 100% capacity utilization, indicating a highly constrained system.

### City Demand Shadow Prices

The shadow prices for cities show the marginal cost of increasing demand at each location:

1. **City 1 (C1)**:

   - Marginal Cost: $1000/unit
   - Currently receiving:
     - 23.0 units from P3 at $500/unit
     - 13.0 units from Premium at $1000/unit
   - Highest marginal cost due to reliance on premium power

2. **City 2 (C2)**:

   - Marginal Cost: $980/unit
   - Currently receiving:
     - 40.0 units from P2 at $300/unit
     - 2.0 units from P3 at $480/unit
   - High marginal cost due to network constraints

3. **City 3 (C3)**:
   - Marginal Cost: $950/unit
   - Currently receiving:
     - 25.0 units from P1 at $400/unit
     - 5.0 units from P3 at $450/unit
   - Lowest marginal cost among cities but still high

### Key Insights

1. The high city shadow prices ($950-$1000) compared to plant shadow prices ($400-$680) indicate that:

   - Demand reduction would be more valuable than capacity increase
   - The system is highly constrained
   - Additional demand would be very expensive to meet

2. The premium power source is only used for City 1, explaining its highest marginal cost

3. All base power plants are at capacity, suggesting potential value in capacity expansion

## Requirements

```
networkx
pulp
matplotlib
numpy
```

## Usage

Run the script using:

```bash
python node_network_lp.py
```

This will:

1. Solve the optimization problem
2. Display the optimal flows and costs
3. Show shadow prices analysis
4. Generate the network visualization
