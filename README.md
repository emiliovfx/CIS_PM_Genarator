---

# **OBJ2PM Bodies Engine**

### *Topology-Driven Body Reconstruction for X-Plane Plane-Maker*

---

## 📌 Overview

The **OBJ2PM Bodies Engine** converts Blender-exported `.obj` meshes into complete, Plane-Maker-compatible body blocks (`_body/n`) using a robust **topology-driven method** that mimics Blender’s edge-loop logic.

This produces **accurate, stable, PM-ready geometry** for fuselages, engine cowlings, tail fairings, and any symmetrical aircraft body mesh.

The output is a **1:1 structural match** to Plane-Maker’s serialized format.

---

# 🖼️ Diagrams

Visual explanations of the OBJ2PM body pipeline:

### **1. BFS Station Layering**

*Stations i=0..N detected by topological distance from nose to tail.*

![BFS Layering](./OBJ2PM_BFS_Layers.svg)

---

### **2. Full OBJ → PM Data Flow**

*Top → bottom pipeline from Blender OBJ to final PM-friendly `_body/n` block.*

![Data Flow](./OBJ2PM_DataFlow.svg)

---

### **3. Station Ring j-Winding (0–17)**

*j=0 top, j=1..7 right, j=8 bottom, j=9..17 mirrored left.*

![j Winding](./OBJ2PM_J_Winding.svg)

---

### **4. j Filling & Station Padding**

*How mid-rings with 8–16 verts fill j slots, how tip/tail collapse all j, and how empty stations get `0,0,0`.*

![j Filling & Stations](./OBJ2PM_J_Filling_Stations.svg)

---

# 🎯 Features

* Topology-based (BFS) station detection
* Blender-accurate ring ordering via `atan2`
* Full 18-slot PM j-ring generation
* Automatic `_part_x`, `_part_rad`, `_r_dim`, `_s_dim`
* Perfect PM i/j ordering
* Template-driven 1:1 body block reconstruction
* Multi-mesh OBJ support
* Zero cropping or clamping in Plane-Maker

---

# 🧠 Mesh Requirements

1. One vertex at **nose** (min Z)
2. One vertex at **tail** (max Z)
3. Mid rings: **8–16 vertices**
4. Continuous topology (no broken loops)
5. Mesh may be offset in **X**
6. Up to ~20 BFS layers (stations)

---

# 🔍 How It Works

## **1. Build Mesh Topology**

* Parse OBJ vertices and faces
* Build adjacency list (graph)

## **2. BFS Station Detection**

* BFS from nose vertex
* BFS distance = station id
* Last BFS layer → tail vertex

## **3. Build j-Rings**

For each station:

* Extract half-ring (X ≥ 0)
* Sort using `atan2(y, x)`
* Fill j=0..8 (mesh → fill bottom centerline)
* Mirror j=9..17

## **4. Compute PM Parameters**

```
_part_x   = lateral centroid
_part_rad = max(|x|,|y|) + 1 ft
_r_dim    = 2 * half_n_max
_s_dim    = len(stations)
```

## **5. Fill PM Template**

* Load neutral zeroed `_body/b` template
* Replace header params
* Insert all `_geo_xyz/i,j,k` values
* Maintain PM-native ordering

---

# 🧪 Validation

Successfully tested on 4 meshes:

* Fuselage
* Left cowling
* Right cowling
* Tail fairing

Results:

* Correct topology rings
* Accurate j-winding
* No PM cropping after `_part_rad` fix
* Perfect visual match in Plane-Maker
* Deterministic, repeatable outputs

---

# 🛠 Installation

```bash
git clone https://github.com/YOURNAME/OBJ2PM-Bodies-Engine.git
cd OBJ2PM-Bodies-Engine
pip install -r requirements.txt
```

---

# 🚀 Usage

Generate body blocks:

```bash
python obj2pm_build_bodies.py --obj bodies.obj
```

Rebuild `.acf`:

```bash
python obj2pm_build_bodies.py --obj bodies.obj --acf input.acf --write
```

Outputs:

```
body_0_full_block.txt
body_1_full_block.txt
body_2_full_block.txt
body_3_full_block.txt
```

Paste these blocks into the `.acf` or let the script auto-inject them.

---

# 🤝 Contributing

Contributions welcome! Ideas:

* GUI tools
* 3D preview of rings
* OBJ export of PM bodies
* Mesh topology diagnostics

---

# 📄 License

MIT — free to use, modify, and integrate into your aircraft pipelines.

---


