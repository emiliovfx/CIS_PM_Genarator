import math
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from pathlib import Path

# ---------- Constants ----------

# Meters to feet (X-Plane / Plane Maker uses feet internally)
M2FT = 3.280839895

# Wing template (zeroed) inside Templates folder
WING_TEMPLATE_PATH = "Templates/wing_block_template_zeroed.txt"


# ---------- Geometry helpers (ORIGINAL, working) ----------

def parse_obj_by_object(obj_path):
    """
    Return dict: {name: [(x,y,z), ...]} from an OBJ file.

    Supports both:
      o Wing1
      g Wing1_Plane.001
    """
    objects = {}
    current = None
    with open(obj_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Start a new logical object on either 'o' or 'g'
            if line.startswith("o ") or line.startswith("g "):
                current = line.split(maxsplit=1)[1].strip()
                objects[current] = []
            elif line.startswith("v ") and current:
                parts = line.split()
                if len(parts) >= 4:
                    _, xs, ys, zs = parts[:4]
                    objects[current].append((float(xs), float(ys), float(zs)))
    return objects


def get_panel_points(objs, logical_name):
    """
    Given a dict of {obj_or_group_name: points},
    find the entry that corresponds to a logical name like 'Wing1',
    even if the actual OBJ name is 'Wing1_Plane.001', etc.
    """
    # 1) Exact match
    if logical_name in objs:
        return objs[logical_name]

    # 2) Prefix matches: Wing1_, Wing1., Wing1-...
    for name in objs:
        if name.startswith(logical_name + "_") or name.startswith(logical_name + ".") or name.startswith(logical_name + "-"):
            return objs[name]

    # 3) Fallback: contains the token somewhere
    for name in objs:
        if logical_name in name:
            return objs[name]

    # If nothing matches, be loud:
    raise ValueError(
        f"Could not find mesh/group for '{logical_name}' in OBJ. "
        f"Available names: {sorted(objs.keys())}"
    )


def section_chord_info(points, span_axis):
    """
    Given all points of one panel:
    - span_axis: 'x' or 'y' defining spanwise direction
    Assumes:
      - Leading edge is at MIN Z (because -Z is LE)
      - Chord direction is Z
      - Span is X (wings, hstab) or Y (vstab)
    Returns dict with:
      chord_root, chord_tip, z25_root, z25_tip,
      span_root, span_tip, semi, sweep_deg,
      x_root, y_root, z_root25 (root 25% point in OBJ coords)
    """
    import numpy as np

    pts = np.array(points)

    if span_axis == "x":
        span_vals = pts[:, 0]
    elif span_axis == "y":
        span_vals = pts[:, 1]
    else:
        raise ValueError("span_axis must be 'x' or 'y'")

    unique = sorted(set(span_vals))
    if len(unique) < 2:
        raise ValueError("Not enough distinct spanwise positions to define root & tip.")

    # Root = closest to fuselage / origin, tip = farthest spanwise from root
    root_val = min(unique, key=lambda v: abs(v))
    tip_val = max(unique, key=lambda v: abs(v - root_val))

    root_pts = pts[abs(span_vals - root_val) < 1e-6]
    tip_pts = pts[abs(span_vals - tip_val) < 1e-6]

    def chord_and_z25(pts_section):
        z_vals = pts_section[:, 2]
        z_le = z_vals.min()   # -Z is leading edge
        z_te = z_vals.max()
        chord = z_te - z_le
        z25 = z_le + 0.25 * chord
        return chord, z25

    chord_root, z25_root = chord_and_z25(root_pts)
    chord_tip, z25_tip = chord_and_z25(tip_pts)

    span_root = root_val
    span_tip = tip_val

    d_span = span_tip - span_root
    d_z25 = z25_tip - z25_root

    semi = math.sqrt(d_span ** 2 + d_z25 ** 2)
    sweep_deg = math.degrees(math.atan2(abs(d_z25), abs(d_span))) if abs(d_span) > 1e-9 else 0.0

    # Approximate root 25% 3D point:
    root_any = root_pts[0]
    if span_axis == "x":
        x_root = span_root
        y_root = root_any[1]
    else:  # span_axis == "y"
        x_root = root_any[0]
        y_root = span_root
    z_root25 = z25_root

    return {
        "chord_root": chord_root,
        "chord_tip": chord_tip,
        "z25_root": z25_root,
        "z25_tip": z25_tip,
        "span_root": span_root,
        "span_tip": span_tip,
        "semi": semi,
        "sweep_deg": sweep_deg,
        "x_root": x_root,
        "y_root": y_root,
        "z_root25": z_root25,
    }


def compute_all_panels(obj_path, wing_dihed_deg, log_func=print):
    """
    Parse the OBJ and compute geometric data for:
      Wing1, Wing2, Horizontal_Stab, Vert_Stab

    wing_dihed_deg: dihedral (deg) to apply to Wing1 and Wing2.
    H-Stab stays 0 deg. Vert_Stab is 90 deg.
    """
    objs = parse_obj_by_object(obj_path)

    # For debug visibility
    log_func("Found objects: " + ", ".join(sorted(objs.keys())))

    results = {}

    # Wings and H-Stab span along X
    for name in ["Wing1", "Wing2", "Horizontal_Stab"]:
        pts = get_panel_points(objs, name)
        info = section_chord_info(pts, span_axis="x")
        if name in ["Wing1", "Wing2"]:
            info["dihed_deg"] = float(wing_dihed_deg)  # as before
        else:
            info["dihed_deg"] = 0.0
        results[name] = info
        log_func(
            f"{name}: Croot={info['chord_root']:.3f} m, "
            f"Ctip={info['chord_tip']:.3f} m, semi={info['semi']:.3f} m, "
            f"sweep={info['sweep_deg']:.3f}°, dihed={info['dihed_deg']:.1f}°, "
            f"root25=({info['x_root']:.3f}, {info['y_root']:.3f}, {info['z_root25']:.3f})"
        )

    # Vertical stab spans along Y
    pts_vert = get_panel_points(objs, "Vert_Stab")
    vinfo = section_chord_info(pts_vert, span_axis="y")
    vinfo["dihed_deg"] = 90.0
    results["Vert_Stab"] = vinfo
    log_func(
        f"Vert_Stab: Croot={vinfo['chord_root']:.3f} m, "
        f"Ctip={vinfo['chord_tip']:.3f} m, semi={vinfo['semi']:.3f} m, "
        f"sweep={vinfo['sweep_deg']:.3f}°, dihed={vinfo['dihed_deg']:.1f}°, "
        f"root25=({vinfo['x_root']:.3f}, {vinfo['y_root']:.3f}, {vinfo['z_root25']:.3f})"
    )

    return results


# ---------- Template-based wing block builder & ACF rewrite ----------

def build_wing_blocks_from_template(panel_data, template_path, log_func=print):
    """
    Build full P _wing/n blocks for all wings using a zeroed template.

    panel_data: dict returned by compute_all_panels(), with keys:
        'Wing1', 'Wing2', 'Horizontal_Stab', 'Vert_Stab'
        Each value is a dict with at least:
            chord_root, chord_tip, semi, sweep_deg, dihed_deg,
            x_root, y_root, z_root25   (in meters)

    Returns: list of strings (without trailing newlines).
    """
    template_text = Path(template_path).read_text(encoding="utf-8", errors="ignore")
    template_lines = template_text.splitlines()

    mapping = {
        "Wing1": [0, 1],
        "Wing2": [2, 3],
        "Horizontal_Stab": [8, 9],
        "Vert_Stab": [10],
    }

    summary_rows = []
    all_lines = []

    for name, indices in mapping.items():
        if name not in panel_data:
            continue

        info = panel_data[name]

        # Convert meters → feet
        croot_ft = info["chord_root"] * M2FT
        ctip_ft = info["chord_tip"] * M2FT
        semi_ft = info["semi"] * M2FT

        lat_ft = info["x_root"] * M2FT
        vert_ft = info["y_root"] * M2FT
        long_ft = info["z_root25"] * M2FT

        # Choose airfoil type
        if name in ["Wing1", "Wing2"]:
            airfoil = "NACA 2412 (popular).afl"
            surf_type = "wing"
        else:
            airfoil = "NACA 0009 (symmetrical).afl"
            surf_type = "stab"

        for idx in indices:
            # Mirror lat for Wing2 as in your original patch
            if name == "Wing2":
                lat_mag = abs(lat_ft)
                if idx == 2:   # left
                    lat_here = -lat_mag
                elif idx == 3: # right
                    lat_here = lat_mag
                else:
                    lat_here = lat_ft
            else:
                lat_here = lat_ft

            for line in template_lines:
                raw = line.rstrip("\n")
                stripped = raw.strip()

                # --- Parameters we control ---
                if stripped.startswith("P _wing/w/_Croot"):
                    all_lines.append(f"P _wing/{idx}/_Croot {croot_ft:.9f}")
                    continue
                if stripped.startswith("P _wing/w/_Ctip"):
                    all_lines.append(f"P _wing/{idx}/_Ctip {ctip_ft:.9f}")
                    continue
                if stripped.startswith("P _wing/w/_semilen_SEG"):
                    all_lines.append(f"P _wing/{idx}/_semilen_SEG {semi_ft:.9f}")
                    continue
                if stripped.startswith("P _wing/w/_sweep_design"):
                    all_lines.append(f"P _wing/{idx}/_sweep_design {info['sweep_deg']:.9f}")
                    continue
                if stripped.startswith("P _wing/w/_dihed_design"):
                    all_lines.append(f"P _wing/{idx}/_dihed_design {info['dihed_deg']:.9f}")
                    continue

                if stripped.startswith("P _wing/w/_part_x"):
                    all_lines.append(f"P _wing/{idx}/_part_x {lat_here:.9f}")
                    continue
                if stripped.startswith("P _wing/w/_part_y"):
                    all_lines.append(f"P _wing/{idx}/_part_y {vert_ft:.9f}")
                    continue
                if stripped.startswith("P _wing/w/_part_z"):
                    all_lines.append(f"P _wing/{idx}/_part_z {long_ft:.9f}")
                    continue

                if stripped.startswith("P _wing/w/_geo_xyz/0,0,0"):
                    all_lines.append(f"P _wing/{idx}/_geo_xyz/0,0,0 {lat_here:.9f}")
                    continue
                if stripped.startswith("P _wing/w/_geo_xyz/0,0,1"):
                    all_lines.append(f"P _wing/{idx}/_geo_xyz/0,0,1 {vert_ft:.9f}")
                    continue
                if stripped.startswith("P _wing/w/_geo_xyz/0,0,2"):
                    all_lines.append(f"P _wing/{idx}/_geo_xyz/0,0,2 {long_ft:.9f}")
                    continue

                if stripped.startswith("P _wing/w/_afl_file_1"):
                    all_lines.append(f"P _wing/{idx}/_afl_file_1 {airfoil}")
                    continue
                if stripped.startswith("P _wing/w/_afl_file_2"):
                    all_lines.append(f"P _wing/{idx}/_afl_file_2 {airfoil}")
                    continue
                if stripped.startswith("P _wing/w/_afl_file_3"):
                    all_lines.append(f"P _wing/{idx}/_afl_file_3 {airfoil}")
                    continue

                # --- Generic wing/w lines: just swap /w/ for /idx/ ---
                if "_wing/w/" in stripped:
                    all_lines.append(raw.replace("_wing/w/", f"_wing/{idx}/"))
                    continue

                # Non-wing lines or blanks: keep as-is
                all_lines.append(raw)

            summary_rows.append({
                "name": name,
                "idx": idx,
                "croot": croot_ft,
                "ctip": ctip_ft,
                "semi": semi_ft,
                "sweep": info["sweep_deg"],
                "dihed": info["dihed_deg"],
                "part_x": lat_here,
                "part_y": vert_ft,
                "part_z": long_ft,
                "type": surf_type,
            })

    # ---- Log summary table ----
    if summary_rows:
        log_func("")
        log_func("ASSIGNED VALUES PER WING (lengths in ft, angles in deg):")
        header = (
            f"{'Name':<18}{'idx':>4}"
            f"{'Croot':>10}{'Ctip':>10}{'Semi':>10}"
            f"{'Sweep':>10}{'Dihed':>10}"
            f"{'part_x':>12}{'part_y':>12}{'part_z':>12}"
        )
        log_func(header)
        log_func("-" * len(header))

        for row in sorted(summary_rows, key=lambda r: (r["idx"], r["name"])):
            line = (
                f"{row['name']:<18}{row['idx']:>4}"
                f"{row['croot']:>10.3f}{row['ctip']:>10.3f}{row['semi']:>10.3f}"
                f"{row['sweep']:>10.3f}{row['dihed']:>10.1f}"
                f"{row['part_x']:>12.3f}{row['part_y']:>12.3f}{row['part_z']:>12.3f}"
            )
            log_func(line)

    return all_lines


def rewrite_acf_wings(acf_in_path, acf_out_path, new_wing_lines):
    """
    Strip existing P _wing/... lines inside PROPERTIES block and insert
    our new template-based wing blocks.
    """
    with open(acf_in_path, "r", encoding="utf-8") as f:
        lines = [ln.rstrip("\n") for ln in f]

    prop_begin = None
    prop_end = None

    for idx, line in enumerate(lines):
        if line.strip() == "PROPERTIES_BEGIN":
            prop_begin = idx
        elif line.strip() == "PROPERTIES_END":
            prop_end = idx
            break

    if prop_begin is None or prop_end is None or prop_end <= prop_begin:
        # Fallback: append at end
        new = lines + list(new_wing_lines)
        with open(acf_out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(new))
        return

    wing_start = None
    wing_end = None
    for idx in range(prop_begin + 1, prop_end):
        if lines[idx].lstrip().startswith("P _wing/"):
            if wing_start is None:
                wing_start = idx
            wing_end = idx

    if wing_start is None:
        wing_start = prop_begin + 1
        wing_end = wing_start - 1

    new_lines = []
    new_lines.extend(lines[:wing_start])
    new_lines.extend(new_wing_lines)
    new_lines.extend(lines[wing_end + 1:])

    with open(acf_out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines))


def generate_wings_from_template_and_rewrite_acf(acf_path, panel_data, template_path, log_func=print):
    """
    High-level helper that:
      1) Builds full wing blocks from template
      2) Rewrites the ACF's P _wing/... section
      3) Returns output path (same naming as previous patch_acf)
    """
    acf_path_obj = Path(acf_path)
    out_path = acf_path_obj.with_name(acf_path_obj.stem + "_updated.acf")

    new_lines = build_wing_blocks_from_template(panel_data, template_path, log_func=log_func)
    rewrite_acf_wings(acf_path, out_path, new_lines)

    return out_path


# ---------- GUI (almost identical to original, but calls template-based writer) ----------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Generate Wings/Tails in ACF from OBJ")
        self.geometry("720x500")

        self.obj_path = tk.StringVar()
        self.acf_path = tk.StringVar()
        self.wing_dihed = tk.StringVar(value="0.0")  # default dihedral

        frm = tk.Frame(self)
        frm.pack(fill="x", padx=10, pady=10)

        # Row 0: OBJ
        tk.Label(frm, text="Wings OBJ:").grid(row=0, column=0, sticky="w")
        tk.Entry(frm, textvariable=self.obj_path, width=60).grid(row=0, column=1, sticky="we")
        tk.Button(frm, text="Browse…", command=self.browse_obj).grid(row=0, column=2, padx=5)

        # Row 1: ACF
        tk.Label(frm, text="ACF file:").grid(row=1, column=0, sticky="w")
        tk.Entry(frm, textvariable=self.acf_path, width=60).grid(row=1, column=1, sticky="we")
        tk.Button(frm, text="Browse…", command=self.browse_acf).grid(row=1, column=2, padx=5)

        # Row 2: Wing dihedral
        tk.Label(frm, text="Wing dihedral (deg):").grid(row=2, column=0, sticky="w")
        tk.Entry(frm, textvariable=self.wing_dihed, width=10).grid(row=2, column=1, sticky="w")

        frm.columnconfigure(1, weight=1)

        tk.Button(self, text="Run update", command=self.run_update).pack(pady=5)

        self.log = scrolledtext.ScrolledText(self, height=20)
        self.log.pack(fill="both", expand=True, padx=10, pady=5)

    def log_print(self, msg):
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        print(msg)

    def browse_obj(self):
        path = filedialog.askopenfilename(
            title="Select wings OBJ",
            filetypes=[("OBJ files", "*.obj"), ("All files", "*.*")]
        )
        if path:
            self.obj_path.set(path)

    def browse_acf(self):
        path = filedialog.askopenfilename(
            title="Select ACF file",
            filetypes=[("ACF files", "*.acf"), ("All files", "*.*")]
        )
        if path:
            self.acf_path.set(path)

    def run_update(self):
        obj = self.obj_path.get().strip()
        acf = self.acf_path.get().strip()
        dihed_str = self.wing_dihed.get().strip() or "0.0"

        if not obj or not Path(obj).is_file():
            messagebox.showerror("Error", "Please select a valid wings OBJ file.")
            return
        if not acf or not Path(acf).is_file():
            messagebox.showerror("Error", "Please select a valid ACF file.")
            return

        try:
            wing_dihed = float(dihed_str)
        except ValueError:
            messagebox.showerror("Error", f"Invalid wing dihedral angle: {dihed_str}")
            return

        try:
            self.log_print(f"Wing dihedral angle (Wing1/Wing2): {wing_dihed:.3f} deg\n")
            self.log_print("Parsing OBJ and computing panel geometry (meters)…")
            panel_data = compute_all_panels(obj, wing_dihed, log_func=self.log_print)

            self.log_print("\nConverting to feet and generating wings in ACF from template…")
            out_path = generate_wings_from_template_and_rewrite_acf(
                acf,
                panel_data,
                template_path=WING_TEMPLATE_PATH,
                log_func=self.log_print,
            )

            self.log_print(f"\nDone. Saved updated ACF as:\n{out_path}")
            messagebox.showinfo("Success", f"Updated ACF saved as:\n{out_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Something went wrong:\n{e}")
            self.log_print(f"ERROR: {e}")


if __name__ == "__main__":
    App().mainloop()
