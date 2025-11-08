# 🚦 SUMO Simulation Builder Pro

**Author:**  Mahbub  
**Institution:** Chulalongkorn University  
**Year:** 2025  

An open-source, Streamlit-based platform that simplifies the creation and analysis of **SUMO (Simulation of Urban Mobility)** traffic scenarios — for research, teaching, and intelligent transportation system (ITS) experimentation.

---

## 🧭 Features

✅ **Interactive Editors**
- Nodes, Edges, Vehicle Types, Routes, Flows, Trips  
- Detectors (E1) and Traffic Light Programs

✅ **Driving Side Selector**
- Switch between left-hand and right-hand driving  
- Automatically updates `netconvert` commands with `--lefthand`

✅ **Simulation Controls**
- Configure time, step length, lane-change, car-following, and collision handling

✅ **Outputs Manager**
- tripinfo, FCD, emissions, summary, edgeData, laneData (with frequency and file name)

✅ **XML Generation**
- nodes.nod.xml, edges.edg.xml, routes.rou.xml, additional.add.xml, simulation.sumocfg

✅ **Export Project ZIP**
- Includes all XMLs + README with SUMO command instructions

✅ **Analytics Dashboard**
- Upload `tripinfo.xml` or `summary.xml` and visualize travel time, emissions, and performance

---

## 🚀 Installation

### 1️⃣ Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/SUMO-Simulation-Builder-Pro.git
cd SUMO-Simulation-Builder-Pro
