# OBJ → Plane‑Maker Wings/Tails Pipeline – Status Summary

_Last updated: current chat session_

## 1. Goal of the Tool

Create a **standalone Python GUI tool** that:

- Takes any `.acf` file (even one with **no wings defined** yet).
- Takes a `Wings.obj` exported from Blender with four objects:
  - `Wing1` – inner main wing section (root panel)
  - `Wing2` – outer main wing section (tip panel)
  - `Horizontal_Stab` – horizontal stabilizer
  - `Vert_Stab` – vertical stabilizer
- Computes all relevant **wing/tail geometry** and **placement** from the OBJ.
- Writes the full wing/tail definition into the `.acf` in the correct slots, in the units and format Plane‑Maker expects.

The idea is: you can start from **any** ACF (even “bare”) and generate a **consistent, correctly placed wing system** driven by the 3D model.

---

## 2. Coordinate System & Conventions

We assume the OBJ uses the same axis conventions as Plane‑Maker:

- **X** → lateral (left/right)  
  - `+X` = right wing, `–X` = left wing
- **Y** → vertical (up/down)  
  - `+Y` = up, `–Y` = down
- **Z** → longitudinal (nose ↔ tail)  
  - `–Z` = nose, **leading edge**  
  - `+Z` = tail, **trailing edge**

Panel layout in the OBJ:

- `Wing1` and `Wing2` and `Horizontal_Stab` span along **X**.
- `Vert_Stab` spans along **Y**.
- Chord is always measured along **Z**, from **min Z (LE)** to **max Z (TE)**.

---

## 3. What the Script Computes from the OBJ

For each object (`Wing1`, `Wing2`, `Horizontal_Stab`, `Vert_Stab`), the script:

1. Groups vertices into **root** and **tip** sections:
   - For span along X: smallest |X| is root, farthest is tip.
   - For span along Y: smallest |Y| is root, farthest is tip.

2. For each section (root and tip), it computes:
   - `chord_root` / `chord_tip` – distance between LE and TE along Z.  
   - `z25_root` / `z25_tip` – Z‑coordinate of the **25% chord point**.

3. From root vs tip 25% chord positions:
   - `semi` – **semi‑span measured along the 25% chord line** (sqrt of Δspan² + Δz25²).
   - `sweep_deg` – **quarter‑chord sweep** (atan2(Δz25, Δspan), in degrees).

4. The **root aerodynamic origin** for arms is taken as the **root 25% chord point**:
   - `x_root`, `y_root`, `z_root25` (in meters).
   - This becomes the source of **lat/vert/long arms**.

---

## 4. Plane‑Maker Wing Index Mapping

We map the four logical surfaces into Plane‑Maker’s `_wing/n` indices like this:

- **Main wing, inner panel** – `Wing1`
  - `_wing/0` – left or first half
  - `_wing/1` – right or mirrored half

- **Main wing, outer panel** – `Wing2`
  - `_wing/2` – left
  - `_wing/3` – right

- **Horizontal stabilizer** – `Horizontal_Stab`
  - `_wing/8` – left
  - `_wing/9` – right

- **Vertical stabilizer** – `Vert_Stab`
  - `_wing/10` – single fin

> This matches your CIS Chieftain layout:  
> indices 0–3 = wing, 8–9 = H‑stab, 10 = V‑stab.

---

## 5. Fields Written into the `.acf`

For each mapped `_wing/n`, the script **creates or overwrites** these parameters:

### 5.1 Planform Geometry

(All lengths converted from meters to feet using `M2FT = 3.280839895`)

- `P _wing/n/_Croot` – root chord (ft)
- `P _wing/n/_Ctip` – tip chord (ft)
- `P _wing/n/_semilen_SEG` – semi‑span segment length along 25% chord (ft)
- `P _wing/n/_sweep_design` – design sweep (deg), from 25% chord geometry
- `P _wing/n/_dihed_design` – design dihedral (deg):
  - `Wing1` / `Wing2`: from the GUI **“Wing dihedral (deg)”** field
  - `Horizontal_Stab`: always `0°` (flat tailplane)
  - `Vert_Stab`: always `90°` (vertical tail convention)

### 5.2 Position / Arms

The 3D root 25% point (in feet) is used as the long/lat/vert arms:

- `lat_ft = x_root * M2FT`  
- `vert_ft = y_root * M2FT`  
- `long_ft = z_root25 * M2FT`  

These are then written as:

- `P _wing/n/_part_x` – **lateral arm** (ft)
- `P _wing/n/_part_y` – **vertical arm** (ft)
- `P _wing/n/_part_z` – **longitudinal arm** (ft)

In addition, we keep the `_geo_xyz` root consistent:

- `P _wing/n/_geo_xyz/0,0,0` – same as `_part_x`
- `P _wing/n/_geo_xyz/0,0,1` – same as `_part_y`
- `P _wing/n/_geo_xyz/0,0,2` – same as `_part_z`

#### Wing2 lateral mirroring

Because `Wing2` is modeled only on one side in some workflows, the script **mirrors** the lateral arm:

- For `_wing/2` (left): `part_x = -|lat_ft|`
- For `_wing/3` (right): `part_x =  +|lat_ft|`

Other surfaces use `lat_ft` directly (usually ~0 for centerline surfaces).

---

## 6. Dihedral Handling

The script does **not** try to infer dihedral from the OBJ (which is modeled flat). Instead:

- The GUI exposes a **“Wing dihedral (deg)”** input:
  - This value is used for:
    - `_wing/0/_dihed_design` (Wing1 left)
    - `_wing/1/_dihed_design` (Wing1 right)
    - `_wing/2/_dihed_design` (Wing2 left)
    - `_wing/3/_dihed_design` (Wing2 right)

- Horizontal stabilizer:
  - `_wing/8/_dihed_design` = 0°  
  - `_wing/9/_dihed_design` = 0°

- Vertical stabilizer:
  - `_wing/10/_dihed_design` = 90°

This lets you quickly test different dihedral angles without touching the OBJ.

---

## 7. GUI Overview

The Tkinter GUI provides:

1. **Wings OBJ** selector
   - Path to `Wings.obj` containing: `Wing1`, `Wing2`, `Horizontal_Stab`, `Vert_Stab`.

2. **ACF file** selector
   - Any `.acf` (with or without existing wings).  
   - The script will **append/replace** the relevant `_wing/n` blocks.

3. **Wing dihedral (deg)** input
   - A float (e.g. `0.0`, `3.5`, `5.0`) used for Wing1 & Wing2 dihedral.

4. **Run update** button
   - Parses OBJ, computes geometry, patches the ACF, and writes `<name>_updated.acf`.

5. **Scrollable log** output
   - Shows step‑by‑step messages (panels found, geometry computed, fields patched).
   - At the end, prints a **summary table** per wing index.

Example of the summary table in the log:

```text
ASSIGNED VALUES PER WING (lengths in ft, angles in deg):
Name                idx     Croot     Ctip     Semi     Sweep     Dihed      part_x      part_y      part_z
-----------------------------------------------------------------------------------------------------------
Wing1                0      ...       ...      ...      ...       ...        ...         ...         ...
Wing1                1      ...       ...      ...      ...       ...        ...         ...         ...
Wing2                2      ...       ...      ...      ...       ...        ...         ...         ...
Wing2                3      ...       ...      ...      ...       ...        ...         ...         ...
Horizontal_Stab      8      ...       ...      ...      ...       ...        ...         ...         ...
Horizontal_Stab      9      ...       ...      ...      ...       ...        ...         ...         ...
Vert_Stab           10      ...       ...      ...      ...       ...        ...         ...         ...
```

This makes it easy to visually verify the numbers before even opening Plane‑Maker.

---

## 8. Current Status

- ✅ The script **correctly computes** geometry from your current `Wings.obj` for:
  - Wing1 (inner panel)
  - Wing2 (outer panel)
  - Horizontal stabilizer
  - Vertical stabilizer
- ✅ It writes **planform geometry** and **arms** into the `.acf` exactly where you want them.
- ✅ It works even if the source `.acf` has **no wings defined** yet.
- ✅ The GUI includes a user‑definable **wing dihedral**.
- ✅ The logging summary is in place and helps debug/check each `_wing/n` block.

Next extensions (if/when we want to go further):

- Auto‑deriving **incidence** or twist from OBJ if modeling includes it.
- Letting the user pick which `_wing` indices to use instead of hard‑coding 0/1/2/3/8/9/10.
- Handling multi‑segment tails (e.g. split H‑stab or multiple fins) in a generic way.

For now, the **core pipeline is working as intended** for the CIS Chieftain wings and tails.
