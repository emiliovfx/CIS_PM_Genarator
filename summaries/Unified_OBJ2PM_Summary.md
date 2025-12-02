
# Unified Summary – OBJ2PM Bodies & Wings Modules (Master Project Overview)

This document summarizes the complete, current state of the **OBJ2PM Bodies Engine** and the **OBJ2PM Wings Module**, and defines how both will be integrated into a unified architecture with a master GUI controller (`cis_obj2pm.py`) and two supporting modules (`cis_bodies.py`, `cis_wings.py`).

Use this summary when starting a **new chat**, so ChatGPT has full context and can continue development cleanly and efficiently.

---

# 1. Overall Goal

Create **one tool** and **one executable** (`cis_obj2pm.exe`) which:

- Takes **one .obj file** containing:
  - Fuselage, cowlings, fairings → Bodies module
  - Wings, horizontal stab, vertical stab → Wings module  
- Takes **one base .acf**
- Rebuilds:
  - ALL `P _body/n/...` blocks using the **Bodies module**
  - ALL `P _wing/n/...` blocks using the **Wings module**
- Inserts the new blocks into the correct location of the ACF
- Preserves everything else in the `.acf`
- Uses GUI mappings to assign:
  - Body index and PM `_descrip` name
  - Wing index and PM wing name
- Outputs a modified `<name>_bodies.acf` or future `<name>_aircraft.acf`

The tool uses:
- Template-based block generation  
- ACF block replacement inside `PROPERTIES_BEGIN ... PROPERTIES_END`  
- PyInstaller-ready resource loading (`resource_path()`)

---

# 2. MODULE 1 – Bodies Module Summary

File: **cis_bodies.py**

### Status: **Fully working**

### Core Responsibilities:
- Parse body meshes from `.obj`
- Build BFS station layers:
  - i = 0 → nose (1 vertex)
  - i = N → tail (1 vertex)
  - mid stations → variable vertex counts (8–16 ring vertices)
- Build ring winding (full j=0..17) using Blender-style logic:
  - Extract half-ring where X ≥ 0
  - Sort by atan2(y, x)
  - Fill j=0..8 (real + centerline fill)
  - Mirror to j=9..17
- Calculate:
  - `_part_x`
  - `_part_rad` = max radius + buffer
  - `_r_dim`
  - `_s_dim`
- Template-driven block builder:
  - Loads zeroed body template (`Templates/body_block_template_zeroed.txt`)
  - Replaces:
    - `_part_x`, `_part_y`, `_part_z`
    - `_part_rad`
    - `_r_dim`, `_s_dim`
    - `_geo_xyz/i,j,k`
    - `_descrip`
- ACF rewriting:
  - Removes ALL existing body lines within PROPERTIES block
  - Reinserts new body blocks in exact PM ordering

### Outputs:
- `build_bodies_from_obj(obj_path)`
- `build_body_block_from_template(bodies, idx, template_path)`
- `rewrite_acf_bodies(acf_in, acf_out, body_lines)`

### Template Folder:
```
Templates/
    body_block_template_zeroed.txt
```

---

# 3. MODULE 2 – Wings Module Summary (From Wings Chat)

File: **cis_wings.py** (to be created/refactored)

### Status: **Working geometry logic; template + ACF insertion pending**

### Current Abilities:
- Detect wing meshes from `.obj` (named: `"Wing"`, `"LeftWing"`, `"RightWing"`, `"HStab"`, `"VStab"`, etc.)
- Extract wing root/tip chord profiles
- Compute:
  - Wing span
  - Root chord
  - Tip chord
  - Dihedral angle
  - Sweep
  - Part_x, part_y, part_z
- Set correct PM coordinates depending on axis

### Missing / To Implement:
1. **Template-based wing block builder**  
   Similar to bodies, but for:
   ```
   P _wing/n/_rootchord
   P _wing/n/_tipchord
   P _wing/n/_dihedral
   P _wing/n/_sweep
   P _wing/n/_part_x
   P _wing/n/_part_y
   P _wing/n/_part_z
   ...
   ```
   Using new file:
   ```
   Templates/wing_block_template_zeroed.txt
   ```

2. **ACF rewrite logic for wings**
   - Remove existing `P _wing/...` blocks
   - Insert new wing blocks in correct PM order

3. **GUI integration**
   - Table listing detected wing meshes
   - Assign index (0..N)
   - Assign PM `_descrip`
   - Validate continuous indices

### Expected Public API after refactor:
```
def build_wings_from_obj(obj_path): -> list[dict]
def build_wing_block_from_template(wings, idx, template_path): -> list[str]
def rewrite_acf_wings(acf_in, acf_out, wing_lines): -> None
```

---

# 4. MASTER SCRIPT – cis_obj2pm.py

### Status: **Bodies integrated, GUI complete. Wings not yet integrated.**

### Responsibilities:
- Launch Tkinter GUI
- Handle:
  - Selecting `.acf` input
  - Selecting `.obj` input
  - Setting output filename `<base>_bodies.acf`
  - Mesh scanning
  - Body/wings index assignment
  - Logging
  - Running bodies build + wings build
- Resource loading function:

```python
def resource_path(relative_path):
    try: base = sys._MEIPASS
    except: base = os.path.abspath(".")
    return os.path.join(base, relative_path)
```

### After refactor:
GUI will have two separate modules:

```
[Bodies Section]
Meshes → body index → PM name

[Wings Section]
Meshes → wing index → PM name
```

Both passed into callback functions:

```
generate_bodies(...)
generate_wings(...)
```

---

# 5. Templates Folder Structure

```
Templates/
    body_block_template_zeroed.txt
    wing_block_template_zeroed.txt   # NEW
```

---

# 6. PyInstaller Packaging

Command:

```
pyinstaller ^
  --noconsole ^
  --onefile ^
  --name cis_obj2pm ^
  --add-data "Templates;Templates" ^
  --add-data "UsersGuide;UsersGuide" ^
  cis_obj2pm.py
```

`resource_path()` handles internal access.

---

# 7. What To Upload in the New Chat

For perfect reconstruction:

### ✔ `cis_bodies.py`  
### ✔ your current wings module script  
### ✔ `cis_obj2pm.py` (optional but recommended)

This ensures the new chat can:
- Inspect real code
- Match function signatures
- Generate correct patches
- Avoid hallucinating missing functions

---

# 8. Next Development Tasks (after starting new chat)

1. Build **wing_block_template_zeroed.txt**  
2. Implement template-based wing block builder  
3. Implement ACF rewrite logic for wings  
4. Integrate wings module into main GUI  
5. Ensure proper ordering in ACF (bodies first, then wings)  
6. Final integration test with Plane-Maker  
7. Build new `.exe`

---

# END

Paste this into the new chat after uploading your scripts.
