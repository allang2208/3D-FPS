"""Blender 5.1 procedural AAA builder for LumberMill-R49c (3A weathered scarred chopping stumps for official SM_BattleAxe,
3D bark/woodchip scatter clusters, zero-Z-fighting 3-room mill raised cleanly above Nanite Landscape displacement,
organic bark-furrowed sawbuck log, sculpted draped bunk beds, forged hearth andirons & hoist rigging).

Produces 16 watertight, zero-open-edge, zero-coplanar-overlap FBX meshes:
  1.  SM_LM_Warehouse          (10.4 x 7.0 m barn, extended wagon ramp to Z=-18 cm yard, forged hoist shackle & rope)
  2.  SM_LM_ToolRoom           (6.8 x 7.0 m workshop + 6.4 x 3.1 m sawing canopy with centered rx=0 rafter & 2-step stone entry)
  3.  SM_LM_Bunkhouse          (7.2 x 8.4 m 2-story walkable dormitory, 2-step stone porch, forged hearth andirons & 16-step stair)
  4.  SM_LM_SawbuckStation     (heavy oak X-trestle sawmill frame + organic bark-furrowed cylindrical-UV oak log with kerf)
  5.  SM_LM_TwoManCrosscutSaw  (186 cm curved steel two-man logging crosscut saw with M-teeth & twin vertical oak handles)
  6.  SM_LM_FramePitSaw        (118 x 68 cm medieval wooden frame buck/pit saw with toothed steel blade & toggle rope)
  7.  SM_LM_WorkbenchSawSet    (carpenter panel hand saw + joiner's oak mallet + steel drawknife & chisels)
  8.  SM_LM_ChoppingStumpA     (3A gnarled root-flared oak stump, deep drying splits, concave chopped bowl, 7 sculpted axe kerfs, riveted iron hoop & wedge splits)
  9.  SM_LM_ChoppingStumpB     (2nd distinct 3A scarred oak stump variant with cleft billet, different roots & hack scars)
  10. SM_LM_BunkBed            (2-tier rustic bunk bed with sculpted slumped pillows, creased mattresses, draped wool blankets & iron brackets)
  11. SM_LM_TimberRack         (heavy cantilevered 3-tier A-frame lumber rack with crisp segments=1 joinery, iron straps & staggered planks)
  12. SM_LM_CampFencePanel     (240 cm weathered Stable-style 3-rail mortised oak camp fence panel, deep buried base)
  13. SM_LM_CampFencePost      (heavy chamfered weathered oak corner/end post with stone collar & iron cap strap)
  14. SM_LM_CampGateArch       (560 cm wide clear sawmill camp timber entrance gateway with hanging signboard & forged lantern hooks)
  15. SM_LM_BarkChipScatterA   (3A 3D curved oak bark slabs, triangular split woodchips & twigs for natural yard grounding)
  16. SM_LM_BarkChipScatterB   (2nd asymmetric 3D bark/woodchip cluster variant for sawbuck & chopping zone)
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

PROPS_LIB = Path("D:/FPS3D/FPSGAME/Tools/WorldGeneration/VillageStable/PropsR43")
sys.path.insert(0, str(PROPS_LIB))
import props_geom as pg

pg.UV_SCALES_M.update({
    "Slate": 1.40,
    "Footing": 1.25,
    "Flagstone": 1.35,
    "Bark": 0.90,
    "Mulch": 1.45,
})
pg.PREVIEW_COLORS.update({
    "Slate": (0.20, 0.22, 0.25),
    "Footing": (0.36, 0.35, 0.32),
    "Flagstone": (0.40, 0.38, 0.34),
    "Bark": (0.22, 0.16, 0.11),
    "Mulch": (0.24, 0.18, 0.12),
})

OUT_DIR = Path("F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/LumberMill-R49/ArchFBX")


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def add_prism_gable(b: pg.AssetBuilder, label: str, axis: str, pos: float,
                    span0: float, span1: float, z_base: float, z_peak: float,
                    thick: float = 19.6, mat: str = "Lime"):
    """Build a crisp, watertight triangular prism gable wall (ZERO stepped overlap & ZERO roof poke-through!)."""
    mid = 0.5 * (span0 + span1)
    ht = 0.5 * thick
    z_top = z_peak - 8.0  # safely recessed 8 cm underneath slate roof plane!
    if z_top <= z_base + 12.0:
        return
    if axis == "X":
        # Triangle in YZ plane extruded along X in [pos-ht .. pos+ht]
        pts = [
            (pos - ht, span0, z_base), (pos - ht, span1, z_base), (pos - ht, mid, z_top),
            (pos + ht, span0, z_base), (pos + ht, span1, z_base), (pos + ht, mid, z_top),
        ]
    else:
        # Triangle in XZ plane extruded along Y in [pos-ht .. pos+ht]
        pts = [
            (span0, pos - ht, z_base), (span1, pos - ht, z_base), (mid, pos - ht, z_top),
            (span0, pos + ht, z_base), (span1, pos + ht, z_base), (mid, pos + ht, z_top),
        ]
    faces = [
        (0, 2, 1),       # side A
        (3, 4, 5),       # side B
        (0, 1, 4, 3),    # bottom
        (1, 2, 5, 4),    # slope +
        (2, 0, 3, 5),    # slope -
    ]
    obj = b._new_mesh_obj(label, pts, faces, mat)
    b._bake_smooth(obj, 35.0)
    b._uv_box(obj, long_axis=2)

    # Recessed exterior timber gable studs proud by 1.4 cm on each side (start +0.5 cm above z_base -> ZERO bottom Z-fight!)
    half = 0.5 * (span1 - span0)
    for idx_s, s in enumerate((-0.44, 0.0, 0.44)):
        h_s = (z_top - z_base) * (1.0 - abs(s) * 1.06) - 8.5
        if h_s > 28.0:
            if axis == "X":
                b.block(f"{label}_Stud_{idx_s}", (pos, mid + s * half, z_base + 0.5 + h_s * 0.5),
                        (22.4, 12.0, h_s), mat="DarkWood", bevel_cm=0.20, segments=1)
            else:
                b.block(f"{label}_Stud_{idx_s}", (mid + s * half, pos, z_base + 0.5 + h_s * 0.5),
                        (12.0, 22.4, h_s), mat="DarkWood", bevel_cm=0.20, segments=1)


def add_pitched_roof(b: pg.AssetBuilder, prefix: str, x0: float, x1: float, y0: float, y1: float,
                     z_eave: float, z_ridge: float, ridge_axis: str = "X",
                     eave_overhang: float = 64.0, gable_overhang_neg: float = 48.0,
                     gable_overhang_pos: float = 48.0, slab_thick: float = 14.0, n_trusses: int = 4):
    """Build dual pitched slate roof planes (strictly non-overlapping at ridge), fascia, purlins & trusses."""
    rise = z_ridge - z_eave

    if ridge_axis == "X":
        cx = 0.5 * ((x0 - gable_overhang_neg) + (x1 + gable_overhang_pos))
        cy = 0.5 * (y0 + y1)
        span_half = 0.5 * (y1 - y0)
        run_len = (x1 - x0) + gable_overhang_neg + gable_overhang_pos
        slope_run = span_half + eave_overhang
        slope_angle = math.degrees(math.atan2(rise, span_half))
        slope_len = math.hypot(slope_run, slope_run * (rise / span_half)) - 2.0
        z_drop = eave_overhang * (rise / span_half)
        z_mid = 0.5 * (z_ridge + (z_eave - z_drop)) + slab_thick * 0.65

        ext_neg = 2.0 if gable_overhang_neg > 0.0 else -0.6
        ext_pos = 2.0 if gable_overhang_pos > 0.0 else -0.6
        cx_ext = 0.5 * ((x0 - gable_overhang_neg - ext_neg) + (x1 + gable_overhang_pos + ext_pos))
        len_ext = (x1 - x0) + gable_overhang_neg + gable_overhang_pos + ext_neg + ext_pos
        slate_cx = 0.5 * ((x0 - gable_overhang_neg + (0.0 if gable_overhang_neg > 0.0 else 0.15)) +
                          (x1 + gable_overhang_pos - (0.0 if gable_overhang_pos > 0.0 else 0.15)))
        slate_len = (x1 - x0) + gable_overhang_neg + gable_overhang_pos - (0.0 if gable_overhang_neg > 0.0 else 0.15) - (0.0 if gable_overhang_pos > 0.0 else 0.15)

        for side in (-1, 1):
            y_mid = cy + side * (0.5 * slope_run + 1.0)
            b.block(f"{prefix}_Slate_{side}", (slate_cx, y_mid, z_mid), (slate_len, slope_len, slab_thick),
                    mat="Slate", rot_deg=(-side * slope_angle, 0.0, 0.0), bevel_cm=0.6)
            y_eave = cy + side * (span_half + eave_overhang - 2.0)
            b.block(f"{prefix}_Fascia_{side}", (cx_ext, y_eave, z_eave - z_drop - 6.0), (len_ext, 5.0, 16.0),
                    mat="DarkWood", bevel_cm=0.3)
            b.block(f"{prefix}_Purlin_{side}", (cx, cy + side * span_half * 0.5, z_eave + rise * 0.5 - 14.0),
                    (run_len - 18.0, 12.0, 14.0), mat="DarkWood", bevel_cm=0.3)
            b.add_collider((cx, cy + side * (span_half * 0.5), z_eave + rise * 0.5 + 12.0),
                           (run_len, span_half + 24.0, 26.0))

        b.block(f"{prefix}_RidgeBeam", (cx, cy, z_ridge - 16.0), (run_len - 14.0, 14.0, 20.0), mat="DarkWood", bevel_cm=0.3)
        b.block(f"{prefix}_RidgeCap", (cx_ext, cy, z_ridge + slab_thick * 0.95), (len_ext, 24.0, 11.0), mat="Slate", bevel_cm=0.5)

        xs = [x0 + 68.0 + k * ((x1 - x0 - 136.0) / max(1, n_trusses - 1)) for k in range(n_trusses)]
        for ti, tx in enumerate(xs):
            b.block(f"{prefix}_Tie_{ti}", (tx, cy, z_eave - 12.0), (15.0, (y1 - y0) - 34.0, 18.0), mat="DarkWood", bevel_cm=0.3)
            b.block(f"{prefix}_KP_{ti}", (tx, cy, z_eave + rise * 0.5 - 12.0), (12.0, 11.0, rise - 26.0), mat="DarkWood", bevel_cm=0.25)
            for s in (-1, 1):
                b.beam(f"{prefix}_Raf_{ti}_{s}",
                       (tx, cy + s * (span_half + eave_overhang * 0.65), z_eave - z_drop * 0.65 - 10.0),
                       (tx, cy + s * 8.0, z_ridge - 14.0), 11.0, 12.0, mat="DarkWood")
                b.beam(f"{prefix}_Strut_{ti}_{s}",
                       (tx, cy + s * 8.0, z_eave + 4.0),
                       (tx, cy + s * span_half * 0.45, z_eave + rise * 0.45 - 18.0), 9.0, 10.0, mat="DarkWood")
    else:
        cx = 0.5 * (x0 + x1)
        cy = 0.5 * ((y0 - gable_overhang_neg) + (y1 + gable_overhang_pos))
        span_half = 0.5 * (x1 - x0)
        run_len = (y1 - y0) + gable_overhang_neg + gable_overhang_pos
        slope_run = span_half + eave_overhang
        slope_angle = math.degrees(math.atan2(rise, span_half))
        slope_len = math.hypot(slope_run, slope_run * (rise / span_half)) - 2.0
        z_drop = eave_overhang * (rise / span_half)
        z_mid = 0.5 * (z_ridge + (z_eave - z_drop)) + slab_thick * 0.65

        for side in (-1, 1):
            x_mid = cx + side * (0.5 * slope_run + 1.0)
            b.block(f"{prefix}_Slate_{side}", (x_mid, cy, z_mid), (slope_len, run_len, slab_thick),
                    mat="Slate", rot_deg=(0.0, side * slope_angle, 0.0), bevel_cm=0.6)
            x_eave = cx + side * (span_half + eave_overhang - 2.0)
            b.block(f"{prefix}_Fascia_{side}", (x_eave, cy, z_eave - z_drop - 6.0), (5.0, run_len + 2.0, 16.0),
                    mat="DarkWood", bevel_cm=0.3)
            b.block(f"{prefix}_Purlin_{side}", (cx + side * span_half * 0.5, cy, z_eave + rise * 0.5 - 14.0),
                    (12.0, run_len - 18.0, 14.0), mat="DarkWood", bevel_cm=0.3)
            b.add_collider((cx + side * (span_half * 0.5), cy, z_eave + rise * 0.5 + 12.0),
                           (span_half + 24.0, run_len, 26.0))

        b.block(f"{prefix}_RidgeBeam", (cx, cy, z_ridge - 16.0), (14.0, run_len - 14.0, 20.0), mat="DarkWood", bevel_cm=0.3)
        b.block(f"{prefix}_RidgeCap", (cx, cy, z_ridge + slab_thick * 0.95), (24.0, run_len + 4.0, 11.0), mat="Slate", bevel_cm=0.5)

        ys = [y0 + 72.0 + k * ((y1 - y0 - 144.0) / max(1, n_trusses - 1)) for k in range(n_trusses)]
        for ti, ty in enumerate(ys):
            z_col = z_eave + 62.0
            col_w = 2.0 * span_half * (1.0 - 66.0 / max(rise, 1.0)) - 20.0
            b.block(f"{prefix}_Col_{ti}", (cx, ty, z_col), (col_w, 13.0, 15.0), mat="DarkWood", bevel_cm=0.3)
            b.block(f"{prefix}_KP_{ti}", (cx, ty, 0.5 * (z_col + z_ridge - 18.0)), (11.0, 10.5, z_ridge - z_col - 26.0), mat="DarkWood", bevel_cm=0.25)
            for s in (-1, 1):
                b.beam(f"{prefix}_Raf_{ti}_{s}",
                       (cx + s * (span_half + eave_overhang * 0.65), ty, z_eave - z_drop * 0.65 - 10.0),
                       (cx + s * 8.0, ty, z_ridge - 14.0), 11.0, 12.0, mat="DarkWood")


def add_wall_zero_flicker(
    b: pg.AssetBuilder, prefix: str, axis: str, pos: float,
    u0: float, u1: float, z_floor: float, z_top: float,
    openings=None, mat_wall: str = "Oak", mat_plinth: str = "Footing",
    z_plinth: float = 42.0, own_corners: bool = False, out_sign: float = 1.0,
    add_colliders: bool = True,
):
    """Build a 100% ZERO-Z-FIGHTING, ZERO-DOOR-BLOCKER timber-framed wall with strict depth hierarchy:
       - Corner posts (if own_corners): 28.0 cm thick (own full corner volume; non-corner walls stop 14 cm shy!)
       - Stone plinth:                  27.0 cm thick, Z in [-10 .. z_plinth], NEVER under doorways!
       - Sill beam:                     24.6 cm thick, Z in [z_plinth .. z_plinth+12], SPLIT around doorways!
       - Top wall plate:                25.2 cm thick, Z in [z_top-16 .. z_top]
       - Intermediate wall posts:       23.4 cm thick, Z in [sill_top .. plate_bot]
       - Window sills:                  26.4 cm thick, Z in [oz0-8 .. oz0]
       - Opening lintels:               24.2 cm thick, Z in [oz1 .. oz1+14]
       - Opening jambs:                 22.6 cm thick, Z in [oz0 .. oz1]
       - Wall infill panels:            20.0 cm thick, strictly non-overlapping EVERY frame piece!
    """
    openings = sorted(openings or [], key=lambda o: o[0])
    # If own_corners, reserve 14 cm at each end for full-height corner posts; otherwise caller trimmed u0/u1!
    inner_u0 = u0 + 14.0 if own_corners else u0
    inner_u1 = u1 - 14.0 if own_corners else u1
    z_plate_bot = z_top - 16.0
    has_plinth = z_plinth > z_floor + 4.0
    z_sill_top = (z_plinth + 12.0) if has_plinth else z_floor

    def box(tag, su0, su1, sz0, sz1, thick, mat, col=False):
        if su1 - su0 < 1.5 or sz1 - sz0 < 1.5:
            return
        um, ul = 0.5 * (su0 + su1), su1 - su0
        zm, zh = 0.5 * (sz0 + sz1), sz1 - sz0
        if axis == "Y":
            b.block(tag, (um, pos, zm), (ul, thick, zh), mat=mat, bevel_cm=0.20, segments=1)
            if col and add_colliders:
                b.add_collider((um, pos, zm), (ul, thick + 2.0, zh))
        else:
            b.block(tag, (pos, um, zm), (thick, ul, zh), mat=mat, bevel_cm=0.20, segments=1)
            if col and add_colliders:
                b.add_collider((pos, um, zm), (thick + 2.0, ul, zh))

    # 1) Corner posts (ONLY built by corner-owning X-walls -> ZERO corner overlap!)
    if own_corners:
        for cs, cu0, cu1 in (("N", u0, u0 + 14.0), ("P", u1 - 14.0, u1)):
            if has_plinth:
                box(f"{prefix}_CPl_{cs}", cu0, cu1, -12.0, z_plinth, 27.8, mat_plinth, col=True)
                box(f"{prefix}_CPo_{cs}", cu0, cu1, z_plinth, z_top, 27.2, "DarkWood", col=True)
            else:
                box(f"{prefix}_CPo_{cs}", cu0, cu1, z_floor, z_top, 27.2, "DarkWood", col=True)

    # 2) Continuous Top Wall Plate strictly between corner posts
    box(f"{prefix}_TopPlate", inner_u0, inner_u1, z_plate_bot, z_top, 25.0, "DarkWood", col=True)

    # 3) Partition inner wall span into solid bays vs openings (ZERO overlap!)
    cuts = [inner_u0]
    for ou0, ou1, _, _ in openings:
        cuts.extend([max(inner_u0, ou0 - 12.0), min(inner_u1, ou1 + 12.0)])
    cuts.append(inner_u1)
    cuts = sorted(set(cuts))

    # Build each opening's crisp non-overlapping frame + wall below/above, and solid bays between!
    solid_spans = []
    cur_u = inner_u0
    for oi, (ou0, ou1, oz0, oz1) in enumerate(openings):
        jamb_w = 12.0
        fu0, fu1 = max(inner_u0, ou0 - jamb_w), min(inner_u1, ou1 + jamb_w)
        if fu0 > cur_u + 1.5:
            solid_spans.append((cur_u, fu0))
        cur_u = fu1

        is_door = (oz0 <= z_floor + 4.0)
        # Jambs (strictly at [fu0..ou0] and [ou1..fu1], thickness 22.4 cm!)
        j_bot = z_floor if is_door else oz0
        box(f"{prefix}_JmbL_{oi}", fu0, ou0, j_bot, oz1, 22.4, "DarkWood", col=True)
        box(f"{prefix}_JmbR_{oi}", ou1, fu1, j_bot, oz1, 22.4, "DarkWood", col=True)
        # Lintel strictly at [oz1 .. oz1+14], spanning [fu0..fu1], thickness 24.0 cm
        lint_top = min(z_plate_bot, oz1 + 14.0)
        box(f"{prefix}_Lint_{oi}", fu0, fu1, oz1, lint_top, 24.0, "DarkWood", col=True)
        # Wall panel above lintel strictly [lint_top .. z_plate_bot], thickness 20.0 cm
        if z_plate_bot > lint_top + 1.5:
            box(f"{prefix}_Above_{oi}", fu0, fu1, lint_top, z_plate_bot, 20.0, mat_wall, col=True)

        if is_door:
            # Flush flat stone threshold at Z in [-12..z_floor-0.5], ZERO blocking sill bar!
            box(f"{prefix}_Thresh_{oi}", fu0, fu1, -12.0, z_floor - 0.5, 25.0, "Flagstone", col=False)
        else:
            # Window: stone plinth -> sill beam -> lower infill -> window sill ledge (ZERO overlap!)
            wsill_bot = max(z_floor, oz0 - 8.0)
            if has_plinth:
                box(f"{prefix}_WPl_{oi}", fu0, fu1, -12.0, min(z_plinth, wsill_bot), 26.4, mat_plinth, col=True)
                if wsill_bot > z_plinth + 1.5:
                    box(f"{prefix}_WSB_{oi}", fu0, fu1, z_plinth, min(z_sill_top, wsill_bot), 24.4, "DarkWood", col=True)
                if wsill_bot > z_sill_top + 1.5:
                    box(f"{prefix}_WLow_{oi}", fu0, fu1, z_sill_top, wsill_bot, 20.0, mat_wall, col=True)
            else:
                if wsill_bot > z_floor + 1.5:
                    box(f"{prefix}_WLow_{oi}", fu0, fu1, z_floor, wsill_bot, 20.0, mat_wall, col=True)
            box(f"{prefix}_WSill_{oi}", max(inner_u0, fu0 - 3.0), min(inner_u1, fu1 + 3.0), wsill_bot, oz0, 26.0, "DarkWood", col=True)

            # Non-overlapping window mullions (center vertical + split left/right horizontal) & exterior shutters!
            mid_u = 0.5 * (ou0 + ou1)
            win_h = oz1 - oz0
            win_zc = 0.5 * (oz0 + oz1)
            box(f"{prefix}_MulV_{oi}", mid_u - 2.5, mid_u + 2.5, oz0 + 0.5, oz1 - 0.5, 6.0, "DarkWood", col=False)
            box(f"{prefix}_MulHL_{oi}", ou0 + 0.5, mid_u - 2.6, win_zc + 4.0, win_zc + 9.0, 5.2, "DarkWood", col=False)
            box(f"{prefix}_MulHR_{oi}", mid_u + 2.6, ou1 - 0.5, win_zc + 4.0, win_zc + 9.0, 5.2, "DarkWood", col=False)

            # Propped-open wooden shutters cleanly outside the wall face (offset +/- 15.5 cm, ZERO clipping!)
            sw = min(52.0, 0.46 * (ou1 - ou0))
            for ss, su_c in ((-1, fu0 - sw * 0.5 - 3.0), (1, fu1 + sw * 0.5 + 3.0)):
                # Only place shutter if it stays well inside the wall edge
                if su_c - sw * 0.5 < inner_u0 + 2.0 or su_c + sw * 0.5 > inner_u1 - 2.0:
                    continue
                if axis == "Y":
                    b.block(f"{prefix}_Shut_{oi}_{ss}", (su_c, pos + out_sign * 15.6, win_zc),
                            (sw, 4.2, win_h - 4.0), mat="OiledOak", bevel_cm=0.22)
                else:
                    b.block(f"{prefix}_Shut_{oi}_{ss}", (pos + out_sign * 15.6, su_c, win_zc),
                            (4.2, sw, win_h - 4.0), mat="OiledOak", bevel_cm=0.22)

    if inner_u1 > cur_u + 1.5:
        solid_spans.append((cur_u, inner_u1))

    # 4) Build every solid wall bay (Plinth -> SillBeam -> WallInfill + intermediate timber studs!)
    for bi, (su0, su1) in enumerate(solid_spans):
        if has_plinth:
            box(f"{prefix}_Pl_{bi}", su0, su1, -12.0, z_plinth, 26.4, mat_plinth, col=True)
            box(f"{prefix}_SB_{bi}", su0, su1, z_plinth, z_sill_top, 24.4, "DarkWood", col=True)
        # Split wide solid bays with intermediate vertical posts (23.2 cm thick) & infill panels (20.0 cm thick)
        bay_w = su1 - su0
        n_sub = max(1, int(round(bay_w / 195.0)))
        sub_w = bay_w / n_sub
        post_w = 13.0
        for si in range(n_sub):
            pu0 = su0 + si * sub_w
            pu1 = su0 + (si + 1) * sub_w
            # Put intermediate stud strictly on internal divisions (never overlapping jambs or corners!)
            in0 = pu0 + (post_w * 0.5 if si > 0 else 0.0)
            in1 = pu1 - (post_w * 0.5 if si < n_sub - 1 else 0.0)
            box(f"{prefix}_Wl_{bi}_{si}", in0, in1, z_sill_top, z_plate_bot, 20.0, mat_wall, col=True)
            if si < n_sub - 1:
                box(f"{prefix}_St_{bi}_{si}", pu1 - post_w * 0.5, pu1 + post_w * 0.5,
                    z_sill_top, z_plate_bot, 23.2, "DarkWood", col=True)


def add_open_barn_door(b: pg.AssetBuilder, label: str, hinge_xyz, width: float, height: float,
                       yaw_open_deg: float, mat="OiledOak"):
    """Swung-open medieval plank barn door with Z-braces & iron hinges (cleanly outside jambs, 0 door obstruction!)."""
    b.push_xform(hinge_xyz, (0.0, 0.0, yaw_open_deg))
    n_planks = max(4, int(round(width / 24.0)))
    pw = width / n_planks
    for k in range(n_planks):
        px = (k + 0.5) * pw
        b.block(f"{label}_P{k}", (px, 0.0, height * 0.5), (pw - 0.8, 5.2, height), mat=mat, bevel_cm=0.2)
    # Cross ledges & Z-braces strictly offset on +Y face (+4.6 cm vs plank +2.6 cm -> ZERO Z-fighting!)
    for lz in (26.0, height * 0.5, height - 26.0):
        b.block(f"{label}_L{int(lz)}", (width * 0.5, 4.6, lz), (width - 10.0, 3.6, 13.0), mat="DarkWood", bevel_cm=0.18)
    b.beam(f"{label}_Z1", (14.0, 4.6, 35.0), (width - 14.0, 4.6, height * 0.5 - 9.0), 9.0, 3.2, mat="DarkWood")
    b.beam(f"{label}_Z2", (14.0, 4.6, height * 0.5 + 9.0), (width - 14.0, 4.6, height - 35.0), 9.0, 3.2, mat="DarkWood")
    for hz in (36.0, height - 36.0):
        b.block(f"{label}_H{int(hz)}", (width * 0.34, -3.5, hz), (width * 0.66, 1.4, 5.0), mat="ScaleIron", bevel_cm=0.1)
    b.add_collider((width * 0.5, 0.0, height * 0.5), (width, 10.0, height), yaw_deg=yaw_open_deg)
    b.pop_xform()


def build_warehouse(out_dir: Path):
    """Room 1: 仓库 (1040 x 700 cm, zero sill bar across doors, zero Z-fighting, hoist beam)."""
    b = pg.AssetBuilder("SM_LM_Warehouse", seed=4921, ground_mud_cm=55.0)
    hx, hy = 520.0, 350.0
    z_eave, z_ridge = 356.0, 560.0

    # Deep recessed foundation (-120..0) & interior oak floor (0..16, collider spans +6 cm over X=0 seam -> 0 floor dip!)
    # Building sits at yard Z=+30 cm (FL1=+46 cm, 100% above peak +42 cm Nanite Landscape moss/root displacement!), so exterior yard is at local Z=-30 cm.
    b.block("WH_Found", (0.0, 0.0, -60.0), (1016.0, 676.0, 120.0), mat="Footing", bevel_cm=0.6)
    b.block("WH_Floor", (0.0, 0.0, 8.0), (1000.0, 660.0, 16.0), mat="Oak", bevel_cm=0.25)
    b.add_collider((3.0, 0.0, 8.0), (1048.0, 696.0, 16.0))
    # Smooth gentle walk-in timber wagon ramp sloping UP from yard (+Y, local Z=-30) to door floor (-Y, local Z=+16)!
    b.block("WH_RampBase", (0.0, hy + 88.0, -24.0), (304.0, 180.0, 42.0), mat="Footing", bevel_cm=0.5, segments=1)
    b.block("WH_Ramp", (0.0, hy + 96.0, -9.0), (312.0, 206.0, 12.0), mat="DarkWood", rot_deg=(-12.8, 0.0, 0.0), bevel_cm=0.25, segments=1)
    b.add_collider((0.0, hy + 42.0, 6.0), (312.0, 88.0, 12.0))
    b.add_collider((0.0, hy + 114.0, -9.0), (312.0, 88.0, 12.0))
    b.add_collider((0.0, hy + 178.0, -22.0), (312.0, 72.0, 12.0))

    # X-walls own all 4 corners (u in [-hy..hy]); Y-walls stop strictly between them (u in [-hx+14..hx-14])!
    add_wall_zero_flicker(b, "WH_West", "X", -hx + 14.0, -hy, hy, 16.0, z_eave,
                          openings=[(-75.0, 75.0, 152.0, 252.0)], mat_wall="Oak", z_plinth=44.0, own_corners=True, out_sign=-1.0)
    add_wall_zero_flicker(b, "WH_East", "X", hx - 14.0, -hy, hy, 16.0, z_eave,
                          openings=[(-110.0, 30.0, 16.0, 256.0)], mat_wall="Oak", z_plinth=44.0, own_corners=True, out_sign=1.0)
    add_wall_zero_flicker(b, "WH_Front", "Y", hy - 14.0, -hx + 27.6, hx - 27.6, 16.0, z_eave,
                          openings=[(-150.0, 150.0, 16.0, 292.0)], mat_wall="Oak", z_plinth=44.0, own_corners=False, out_sign=1.0)
    add_wall_zero_flicker(b, "WH_Back", "Y", -hy + 14.0, -hx + 27.6, hx - 27.6, 16.0, z_eave,
                          openings=[(-310.0, -185.0, 152.0, 252.0), (185.0, 310.0, 152.0, 252.0)], mat_wall="Oak", z_plinth=44.0, own_corners=False, out_sign=-1.0)

    # Watertight triangular gable prisms + dual pitched roof (0 overhang on +X so it meets ToolRoom seamlessly!)
    add_prism_gable(b, "WH_GW", "X", -hx + 14.0, -hy + 14.0, hy - 14.0, z_eave, z_ridge, mat="Lime")
    add_prism_gable(b, "WH_GE", "X", hx - 14.0, -hy + 14.0, hy - 14.0, z_eave, z_ridge, mat="Lime")
    add_pitched_roof(b, "WH_Roof", -hx, hx, -hy, hy, z_eave, z_ridge, ridge_axis="X",
                     eave_overhang=66.0, gable_overhang_neg=52.0, gable_overhang_pos=0.0, n_trusses=4)

    # Projecting front hoist beam above double barn doors + forged iron shackle & hanging hoist rope (connects solidly to q_pulley!)
    b.block("WH_HoistBeam", (0.0, hy + 56.0, 342.0), (20.0, 180.0, 22.0), mat="DarkWood", bevel_cm=0.35)
    b.beam("WH_HoistBrL", (-14.0, hy + 2.0, 304.0), (-6.0, hy + 104.0, 336.0), 10.0, 10.0, mat="DarkWood")
    b.beam("WH_HoistBrR", (14.0, hy + 2.0, 304.0), (6.0, hy + 104.0, 336.0), 10.0, 10.0, mat="DarkWood")
    # Forged iron collar & vertical drop shackle at Y = hy+95 (= yard Y=-225) holding the wooden double pulley cleanly!
    b.block("WH_HoistCollar", (0.0, hy + 95.0, 342.0), (23.0, 10.0, 24.5), mat="ScaleIron", bevel_cm=0.2, segments=1)
    b.ring_torus("WH_HoistEye", (0.0, hy + 95.0, 326.0), 4.6, 1.35, mat="ScaleIron", axis="X", major_segs=16, minor_segs=8)
    # 3-strand braided hemp haul rope dropping down from pulley and angled back to right door-jamb cleat
    b.rope_braid("WH_HoistRopeDrop", [(0.0, hy + 95.0, 276.0), (0.0, hy + 95.0, 178.0), (2.0, hy + 95.0, 128.0)], radius_cm=1.35, mat="Rope")
    b.rope_braid("WH_HoistRopeTail", [(4.0, hy + 95.0, 286.0), (54.0, hy + 58.0, 232.0), (146.0, hy + 10.0, 132.0)], radius_cm=1.20, mat="Rope")
    b.block("WH_RopeCleat", (146.0, hy + 5.0, 132.0), (5.0, 8.0, 22.0), mat="ScaleIron", bevel_cm=0.2, segments=1)

    # Swung-open heavy plank double barn doors (hinged strictly OUTSIDE front wall at Y=hy+6 -> 300 cm clear entry!)
    add_open_barn_door(b, "WH_DoorL", (-156.0, hy + 6.0, 18.0), 142.0, 268.0, yaw_open_deg=132.0)
    add_open_barn_door(b, "WH_DoorR", (156.0, hy + 6.0, 18.0), 142.0, 268.0, yaw_open_deg=48.0)

    return b.finish(out_dir, lod_ratios=(1.0,))


def build_toolroom(out_dir: Path):
    """Room 2: 工具间 (680 x 700 cm workshop + 640 x 310 cm front sawing canopy + built-in workbench, zero Z-fighting)."""
    b = pg.AssetBuilder("SM_LM_ToolRoom", seed=4922, ground_mud_cm=52.0)
    hx, hy = 340.0, 350.0
    z_eave, z_ridge = 356.0, 560.0

    # Deep recessed foundation & flagstone floor (collider bridges both X=-hx & X=+hx seams -> 0 floor dip!)
    b.block("TR_Found", (0.0, 0.0, -60.0), (664.0, 676.0, 120.0), mat="Footing", bevel_cm=0.6)
    b.block("TR_Floor", (0.0, 0.0, 8.0), (660.0, 660.0, 16.0), mat="Flagstone", bevel_cm=0.3)
    b.add_collider((0.0, 0.0, 8.0), (696.0, 696.0, 16.0))
    # Smooth 3-step Normandy flagstone stoop (~15 cm per riser) connecting yard (local Z=-30) up to ToolRoom floor (local Z=+16)!
    b.block("TR_StepTop", (0.0, hy + 28.0, -15.0), (208.0, 56.0, 60.0), mat="Flagstone", bevel_cm=0.45, segments=1)
    b.block("TR_StepMid", (0.0, hy + 72.0, -22.5), (218.0, 44.0, 45.0), mat="Flagstone", bevel_cm=0.45, segments=1)
    b.block("TR_StepBot", (0.0, hy + 112.0, -30.0), (228.0, 42.0, 30.0), mat="Flagstone", bevel_cm=0.45, segments=1)
    b.add_collider((0.0, hy + 28.0, 7.5), (208.0, 56.0, 15.0))
    b.add_collider((0.0, hy + 72.0, -7.5), (218.0, 44.0, 15.0))
    b.add_collider((0.0, hy + 112.0, -22.5), (228.0, 42.0, 15.0))

    # East wall (+X) connects to Bunkhouse (doorway Y in [-90..+40], height 236 cm); West (-X) joins Warehouse's East wall!
    add_wall_zero_flicker(b, "TR_East", "X", hx - 14.0, -hy, hy, 16.0, z_eave,
                          openings=[(-90.0, 40.0, 16.0, 252.0)], mat_wall="Lime", z_plinth=44.0, own_corners=True, out_sign=1.0)
    # Continuous Flagstone threshold bridge (Z=0.5..15.2 -> 0.3 cm below Thresh top 15.5 -> ZERO coplanar Z-fighting!)
    b.block("TR_EastBridge", (hx, -25.0, 7.85), (56.0, 130.0, 14.7), mat="Flagstone", bevel_cm=0.20, segments=1)
    b.add_collider((hx, -25.0, 8.0), (72.0, 134.0, 16.0))
    add_wall_zero_flicker(b, "TR_Front", "Y", hy - 14.0, -hx - 0.5, hx - 27.6, 16.0, z_eave,
                          openings=[(-270.0, -150.0, 106.0, 222.0), (-90.0, 90.0, 16.0, 258.0), (145.0, 265.0, 106.0, 222.0)],
                          mat_wall="Lime", z_plinth=48.0, own_corners=False, out_sign=1.0)
    # Back windows spaced wide ([-280..-160] & [+160..+280]) -> 320 cm solid center plaster wall for Two-Man Crosscut Saw!
    add_wall_zero_flicker(b, "TR_Back", "Y", -hy + 14.0, -hx - 0.5, hx - 27.6, 16.0, z_eave,
                          openings=[(-280.0, -160.0, 116.0, 228.0), (160.0, 280.0, 116.0, 228.0)],
                          mat_wall="Lime", z_plinth=48.0, own_corners=False, out_sign=-1.0)

    # Swung-open workshop door (strictly outside front wall at Y=hy+6 -> 180 cm wide clear entry!)
    add_open_barn_door(b, "TR_Door", (96.0, hy + 6.0, 18.0), 116.0, 236.0, yaw_open_deg=44.0)

    # Roof seamlessly continues Warehouse ridge & tucks 12 cm into Bunkhouse 2F west wall valley!
    add_pitched_roof(b, "TR_Roof", -hx, hx, -hy, hy, z_eave, z_ridge, ridge_axis="X",
                     eave_overhang=66.0, gable_overhang_neg=0.0, gable_overhang_pos=12.0, n_trusses=3)

    # Attached Covered Front Open-Sided Timber Sawing Canopy (4 posts at -294, -108, +108, +294 -> 200 cm CLEAR center entry!)
    # Piers extend deeply to local Z=-96 cm (= yard Z=-78 cm) so they seat rock-solidly in terrain!
    can_y0, can_y1 = hy + 2.0, hy + 310.0
    can_z0, can_z1 = 292.0, 236.0
    for px in (-294.0, -108.0, 108.0, 294.0):
        b.block(f"Can_Pier_{int(px)}", (px, can_y1 - 16.0, -32.0), (32.0, 32.0, 128.0), mat="Footing", bevel_cm=0.7)
        b.block(f"Can_Post_{int(px)}", (px, can_y1 - 16.0, 129.0), (16.5, 16.5, 194.0), mat="DarkWood", bevel_cm=0.32)
        b.add_collider((px, can_y1 - 16.0, 105.0), (26.0, 26.0, 250.0))
        for sx in (-1, 1):
            if (px < -200 and sx < 0) or (px > 200 and sx > 0):
                continue
            b.beam(f"Can_BrX_{int(px)}_{sx}", (px + sx * 6.0, can_y1 - 16.0, 186.0), (px + sx * 48.0, can_y1 - 16.0, 226.0), 9.5, 9.5, mat="DarkWood")
        b.beam(f"Can_BrY_{int(px)}", (px, can_y1 - 22.0, 186.0), (px, can_y1 - 74.0, 234.0), 9.5, 9.5, mat="DarkWood")
    b.block("Can_Header", (0.0, can_y1 - 16.0, can_z1), (624.0, 21.0, 20.0), mat="DarkWood", bevel_cm=0.32)
    b.block("Can_Ledger", (0.0, can_y0 + 10.0, can_z0), (624.0, 15.0, 18.0), mat="DarkWood", bevel_cm=0.32)
    # Centered rafter layout (-288..+288 step 72 -> exact rx=0 center rafter for hanging Canopy chain pendant!)
    for rx in range(-288, 289, 72):
        b.beam(f"Can_Raf_{rx}", (float(rx), can_y0 + 8.0, can_z0 + 4.0), (float(rx), can_y1 + 22.0, can_z1 - 2.0), 9.0, 12.0, mat="DarkWood")
    can_slope = math.degrees(math.atan2(can_z0 - can_z1, can_y1 - can_y0))
    can_len = math.hypot(can_y1 - can_y0 + 48.0, (can_z0 - can_z1) * 1.15)
    b.block("Can_Slate", (0.0, 0.5 * (can_y0 + can_y1) + 12.0, 0.5 * (can_z0 + can_z1) + 15.0),
            (646.0, can_len, 12.0), mat="Slate", rot_deg=(-can_slope, 0.0, 0.0), bevel_cm=0.5)
    b.add_collider((0.0, 0.5 * (can_y0 + can_y1), 274.0), (636.0, 316.0, 24.0))

    # Built-in Heavy Joiner's Workbench along south wall (cleanly 14 cm off wall so ZERO clipping!)
    wb_y = -hy + 82.0
    b.block("TR_BenchTop", (0.0, wb_y, 90.0), (350.0, 86.0, 10.0), mat="OiledOak", bevel_cm=0.45)
    b.block("TR_BenchShelf", (0.0, wb_y, 34.0), (332.0, 72.0, 6.0), mat="Sawn", bevel_cm=0.25)
    for lx in (-158.0, 0.0, 158.0):
        for ly in (-32.0, 32.0):
            b.block(f"TR_BenchLeg_{int(lx)}_{int(ly)}", (lx, wb_y + ly, 50.0), (11.0, 11.0, 70.0), mat="DarkWood", bevel_cm=0.25)
    b.block("TR_ViseJaw", (-110.0, wb_y + 47.0, 86.0), (42.0, 7.0, 18.0), mat="OiledOak", bevel_cm=0.25)
    b.lathe("TR_ViseScrew", (-110.0, wb_y + 52.0, 86.0), [(0.0, 2.2), (12.0, 2.2), (14.0, 3.8), (18.0, 3.8)], mat="DarkWood", axis="Y", sides=12)
    b.add_collider((0.0, wb_y, 55.0), (354.0, 92.0, 84.0))

    # Wall-mounted timber tool rail cleanly in front of back wall inner face (-hy+27 -> rail at -hy+31)
    b.block("TR_ToolRail1", (0.0, -hy + 32.0, 154.0), (260.0, 5.5, 13.0), mat="DarkWood", bevel_cm=0.18)
    b.block("TR_ToolRail2", (0.0, -hy + 32.0, 188.0), (260.0, 5.5, 13.0), mat="DarkWood", bevel_cm=0.18)
    for px in range(-110, 115, 22):
        b.block(f"TR_Peg_{px}", (float(px), -hy + 38.5, 154.0), (2.6, 8.0, 2.6), mat="ScaleIron", bevel_cm=0.1)

    return b.finish(out_dir, lod_ratios=(1.0,))


def build_bunkhouse(out_dir: Path):
    """Room 3: 临时宿舍（二层）(720 x 840 cm 2-story walkable dormitory, zero door bar, zero Z-fighting, 16-step stair)."""
    b = pg.AssetBuilder("SM_LM_Bunkhouse", seed=4923, ground_mud_cm=55.0)
    hx, hy = 360.0, 420.0
    z1_top = 296.0
    z2_flr = 312.0
    z2_eave = 528.0
    z2_ridge = 728.0

    # Deep recessed foundation & 1F oak floor strictly inside inner walls
    b.block("BH_Found", (0.0, 0.0, -60.0), (696.0, 816.0, 120.0), mat="Footing", bevel_cm=0.6)
    b.block("BH_Floor1F", (0.0, 0.0, 8.0), (680.0, 800.0, 16.0), mat="Oak", bevel_cm=0.25)
    b.add_collider((0.0, 0.0, 8.0), (716.0, 836.0, 16.0))

    # 1F Walls (ZERO sill bar across front doorway [-68..+68] or west ToolRoom doorway [-160..-30]!)
    add_wall_zero_flicker(b, "BH1_West", "X", -hx + 14.0, -hy, hy, 16.0, z1_top,
                          openings=[(-160.0, -30.0, 16.0, 252.0)], mat_wall="Lime", z_plinth=44.0, own_corners=True, out_sign=-1.0)
    add_wall_zero_flicker(b, "BH1_East", "X", hx - 14.0, -hy, hy, 16.0, z1_top,
                          openings=[(160.0, 290.0, 102.0, 214.0)], mat_wall="Lime", z_plinth=44.0, own_corners=True, out_sign=1.0)
    add_wall_zero_flicker(b, "BH1_Front", "Y", hy - 14.0, -hx + 27.6, hx - 27.6, 16.0, z1_top,
                          openings=[(-280.0, -155.0, 102.0, 214.0), (-68.0, 68.0, 16.0, 248.0), (155.0, 280.0, 102.0, 214.0)],
                          mat_wall="Lime", z_plinth=44.0, own_corners=False, out_sign=1.0)
    add_wall_zero_flicker(b, "BH1_Back", "Y", -hy + 14.0, -hx + 27.6, hx - 27.6, 16.0, z1_top,
                          openings=[(-150.0, -20.0, 138.0, 236.0)], mat_wall="Lime", z_plinth=44.0, own_corners=False, out_sign=-1.0)

    # Swung-open 1F main entry door strictly outside front wall & 60 cm clear of porch post!
    add_open_barn_door(b, "BH_MainDoor", (74.0, hy + 6.0, 18.0), 124.0, 224.0, yaw_open_deg=18.0)

    # Sheltered front entry porch & smooth 3-step Normandy stone stoop (meets yard local Z=-30 cleanly!)
    b.block("BH_PorchStep", (0.0, hy + 58.0, -18.0), (262.0, 114.0, 64.0), mat="Flagstone", bevel_cm=0.45, segments=1)
    b.block("BH_PorchMidStep", (0.0, hy + 128.0, -24.5), (226.0, 42.0, 49.0), mat="Flagstone", bevel_cm=0.45, segments=1)
    b.block("BH_PorchLowStep", (0.0, hy + 166.0, -32.0), (236.0, 40.0, 34.0), mat="Flagstone", bevel_cm=0.45, segments=1)
    b.add_collider((0.0, hy + 58.0, 7.0), (262.0, 114.0, 14.0))
    b.add_collider((0.0, hy + 128.0, -8.0), (226.0, 42.0, 16.0))
    b.add_collider((0.0, hy + 166.0, -23.0), (236.0, 40.0, 16.0))
    for sx in (-122.0, 122.0):
        b.block(f"BH_PPier_{int(sx)}", (sx, hy + 104.0, -32.0), (28.0, 28.0, 124.0), mat="Footing", bevel_cm=0.5)
        b.block(f"BH_PPost_{int(sx)}", (sx, hy + 104.0, 137.0), (16.0, 16.0, 210.0), mat="DarkWood", bevel_cm=0.28)
        b.add_collider((sx, hy + 104.0, 108.0), (26.0, 26.0, 248.0))
    b.block("BH_PHeader", (0.0, hy + 104.0, 248.0), (274.0, 19.0, 18.0), mat="DarkWood", bevel_cm=0.28)
    b.block("BH_PRoof", (0.0, hy + 68.0, 266.0), (296.0, 136.0, 12.0), mat="Slate", rot_deg=(-14.0, 0.0, 0.0), bevel_cm=0.45)

    # Stone Hearth Fireplace, Forged-Iron Andirons (Fire-Dogs) & Exterior Chimney Stack on East wall (+X)
    b.block("BH_HearthPad", (hx - 62.0, -30.0, 19.0), (76.0, 200.0, 6.0), mat="Flagstone", bevel_cm=0.35, segments=1)
    b.block("BH_HearthBack", (hx - 33.0, -30.0, 86.0), (10.0, 134.0, 132.0), mat="Footing", bevel_cm=0.35, segments=1)
    b.block("BH_HearthCheekL", (hx - 52.5, -112.0, 86.0), (48.0, 30.0, 132.0), mat="Footing", bevel_cm=0.6, segments=1)
    b.block("BH_HearthCheekR", (hx - 52.5, 52.0, 86.0), (48.0, 30.0, 132.0), mat="Footing", bevel_cm=0.6, segments=1)
    b.block("BH_HearthMantel", (hx - 54.0, -30.0, 160.0), (54.0, 206.0, 16.0), mat="DarkWood", bevel_cm=0.35, segments=1)
    b.block("BH_HearthHood", (hx - 48.0, -30.0, 232.0), (34.0, 168.0, 128.0), mat="Footing", bevel_cm=0.7, segments=1)
    # Pair of forged iron hearth andirons (log grate) resting on BH_HearthPad top (Z=22 cm)!
    for ay in (-66.0, 6.0):
        b.block(f"BH_AndBar_{int(ay)}", (hx - 54.0, ay, 27.0), (34.0, 3.2, 3.2), mat="ScaleIron", bevel_cm=0.15, segments=1)
        b.block(f"BH_AndLegF_{int(ay)}", (hx - 74.0, ay, 24.5), (3.4, 12.0, 5.0), mat="ScaleIron", bevel_cm=0.15, segments=1)
        b.block(f"BH_AndLegB_{int(ay)}", (hx - 38.5, ay, 24.5), (3.4, 3.4, 5.0), mat="ScaleIron", bevel_cm=0.15, segments=1)
        b.block(f"BH_AndPost_{int(ay)}", (hx - 74.0, ay, 41.0), (3.8, 3.8, 28.0), mat="ScaleIron", bevel_cm=0.2, segments=1)
        b.lathe(f"BH_AndFin_{int(ay)}", (hx - 74.0, ay, 55.0), [(0.0, 2.0), (2.5, 3.4), (5.5, 3.0), (7.0, 0.0)], mat="ScaleIron", axis="Z", sides=10)
    b.block("BH_AndCross", (hx - 54.0, -30.0, 29.5), (4.0, 76.0, 2.4), mat="ScaleIron", bevel_cm=0.12, segments=1)
    # Exterior chimney flue strictly OUTSIDE east wall (X = hx+1..hx+58 -> ZERO overlap with East wall!)
    b.block("BH_ChimBase", (hx + 30.0, -30.0, 210.0), (58.0, 184.0, 480.0), mat="Footing", bevel_cm=0.8)
    b.block("BH_ChimUpper", (hx + 32.0, -30.0, 610.0), (56.0, 114.0, 320.0), mat="Footing", bevel_cm=0.8)
    b.block("BH_ChimCap", (hx + 32.0, -30.0, 778.0), (70.0, 128.0, 16.0), mat="Stone", bevel_cm=0.5)
    b.add_collider((hx - 38.0, -30.0, 155.0), (66.0, 196.0, 276.0))

    # =========================================================================
    # WALKABLE 16-STEP OAK STAIRCASE (1F Z=+16 -> 2F Z=+312 along south wall)
    # =========================================================================
    n_steps = 16
    x_st0, x_st1 = -215.0, 225.0
    y_st_c, y_st_w = -330.0, 120.0
    z_st0, z_st1 = 16.0, z2_flr
    dx_s = (x_st1 - x_st0) / n_steps
    dz_s = (z_st1 - z_st0) / n_steps
    for k in range(n_steps):
        sx = x_st0 + (k + 0.5) * dx_s
        sz = z_st0 + (k + 1.0) * dz_s
        b.block(f"Stair_Tr_{k}", (sx, y_st_c, sz - 2.5), (dx_s + 2.5, y_st_w, 5.0), mat="OiledOak", bevel_cm=0.18, segments=1)
        b.block(f"Stair_Rs_{k}", (sx - dx_s * 0.46, y_st_c, sz - dz_s * 0.5 - 2.5), (3.2, y_st_w - 4.0, dz_s - 4.5), mat="Oak", bevel_cm=0.10, segments=1)
        b.add_collider((sx, y_st_c, sz - dz_s * 0.5), (dx_s + 4.0, y_st_w, dz_s))
    for sy_s, sy in (("S", y_st_c - y_st_w * 0.5 - 4.0), ("N", y_st_c + y_st_w * 0.5 + 4.0)):
        b.beam(f"Stair_Str_{sy_s}", (x_st0 - 6.0, sy, z_st0), (x_st1 + 6.0, sy, z_st1 - 8.0), 7.5, 22.0, mat="DarkWood")
    y_rail = y_st_c + y_st_w * 0.5 + 4.5
    b.block("Stair_NBot", (x_st0 - 4.0, y_rail, z_st0 + 50.0), (11.0, 11.0, 100.0), mat="DarkWood", bevel_cm=0.25)
    b.block("Stair_NTop", (x_st1 + 4.0, y_rail, z_st1 + 46.0), (11.0, 11.0, 96.0), mat="DarkWood", bevel_cm=0.25)
    b.beam("Stair_Rail", (x_st0 - 4.0, y_rail, z_st0 + 96.0), (x_st1 + 4.0, y_rail, z_st1 + 92.0), 7.5, 6.5, mat="OiledOak")
    for k in range(1, n_steps, 2):
        bx = x_st0 + (k + 0.5) * dx_s
        bz = z_st0 + (k + 0.5) * dz_s
        b.block(f"Stair_Bal_{k}", (bx, y_rail, bz + 46.0), (4.5, 4.5, 88.0), mat="Oak", bevel_cm=0.14)

    # =========================================================================
    # 2F FLOOR DECK (Z=296..312, strictly inside walls except +24 cm front jetty!)
    # =========================================================================
    hy2 = hy + 24.0
    for jy in (-244.0, -140.0, -35.0, 70.0, 175.0, 280.0, 385.0):
        b.block(f"BH_Joist_{int(jy)}", (0.0, jy, z1_top - 8.0), (662.0, 13.0, 15.0), mat="DarkWood", bevel_cm=0.25)
    # 2F floor deck slabs (Z = 296.5..312.0, stops strictly at Y=+415.5 abutting BH_JettyFascia -> ZERO Z-fighting!)
    b.block("BH_F2_Main", (0.0, 78.75, 304.25), (684.0, 673.5, 15.5), mat="Oak", bevel_cm=0.25)
    b.add_collider((0.0, 88.0, 304.25), (700.0, 700.0, 16.0))
    b.block("BH_F2_LandE", (284.0, -330.0, 304.25), (116.0, 144.0, 15.5), mat="Oak", bevel_cm=0.25)
    b.add_collider((284.0, -330.0, 304.25), (124.0, 150.0, 16.0))
    b.block("BH_F2_LandW", (-288.0, -330.0, 304.25), (108.0, 144.0, 15.5), mat="Oak", bevel_cm=0.25)
    b.add_collider((-288.0, -330.0, 304.25), (116.0, 150.0, 16.0))
    # Jetty fascia beam & 3 perimeter rim-joist beams cleanly sealing the Z=296..312 band on ALL 4 sides (Z in [296.4..311.6] -> 0 coplanar Z-fight!)
    b.block("BH_JettyFascia", (0.0, 429.75, 304.0), (724.0, 28.5, 16.0), mat="DarkWood", bevel_cm=0.25, segments=1)
    b.block("BH_RimBack", (0.0, -hy + 14.0, 304.0), (720.0, 25.4, 15.2), mat="DarkWood", bevel_cm=0.18, segments=1)
    b.block("BH_RimWest", (-hx + 14.0, 10.6, 304.0), (25.4, 808.8, 15.2), mat="DarkWood", bevel_cm=0.18, segments=1)
    b.block("BH_RimEast", (hx - 14.0, 10.6, 304.0), (25.4, 808.8, 15.2), mat="DarkWood", bevel_cm=0.18, segments=1)
    for cx in (-320, -212, 212, 320):
        b.block(f"BH_Corbel_{cx}", (float(cx), hy + 10.0, 284.0), (14.0, 28.0, 22.0), mat="DarkWood", bevel_cm=0.25)

    # 2F Stairwell safety balustrade (east end stops at X=+211 -> wide generous turn off top stair onto 2F dorm!)
    b.block("BH2_RailLong", (-11.0, -258.0, z2_flr + 92.0), (442.0, 8.5, 7.5), mat="OiledOak", bevel_cm=0.22)
    b.block("BH2_RailMid", (-11.0, -258.0, z2_flr + 50.0), (438.0, 5.5, 5.5), mat="Oak", bevel_cm=0.18)
    b.add_collider((-11.0, -258.0, z2_flr + 48.0), (444.0, 12.0, 96.0))
    for rx in range(-220, 212, 43):
        b.block(f"BH2_BalL_{rx}", (float(rx), -258.0, z2_flr + 46.0), (5.0, 5.0, 88.0), mat="Oak", bevel_cm=0.14)
    # West end rail abuts BH2_RailLong strictly at Y=-262.5 (ZERO corner coplanar overlap!)
    b.block("BH2_RailEnd", (-234.0, -332.5, z2_flr + 92.0), (8.5, 139.0, 7.5), mat="OiledOak", bevel_cm=0.22)
    b.add_collider((-234.0, -332.5, z2_flr + 48.0), (12.0, 142.0, 96.0))
    for ry in (-385, -345, -305, -265):
        b.block(f"BH2_BalE_{ry}", (-234.0, float(ry), z2_flr + 46.0), (5.0, 5.0, 88.0), mat="Oak", bevel_cm=0.14)

    # 2F Walls (strictly Z=312..528, ZERO corner overlap!)
    add_wall_zero_flicker(b, "BH2_West", "X", -hx + 14.0, -hy, hy2, z2_flr, z2_eave,
                          openings=[(160.0, 300.0, z2_flr + 86.0, z2_flr + 194.0)], mat_wall="Lime", z_plinth=0.0, own_corners=True, out_sign=-1.0)
    add_wall_zero_flicker(b, "BH2_East", "X", hx - 14.0, -hy, hy2, z2_flr, z2_eave,
                          openings=[(140.0, 270.0, z2_flr + 86.0, z2_flr + 194.0)], mat_wall="Lime", z_plinth=0.0, own_corners=True, out_sign=1.0)
    add_wall_zero_flicker(b, "BH2_Front", "Y", hy2 - 14.0, -hx + 27.6, hx - 27.6, z2_flr, z2_eave,
                          openings=[(-240.0, -105.0, z2_flr + 86.0, z2_flr + 194.0), (105.0, 240.0, z2_flr + 86.0, z2_flr + 194.0)],
                          mat_wall="Lime", z_plinth=0.0, own_corners=False, out_sign=1.0)
    add_wall_zero_flicker(b, "BH2_Back", "Y", -hy + 14.0, -hx + 27.6, hx - 27.6, z2_flr, z2_eave,
                          openings=[(-80.0, 80.0, z2_flr + 86.0, z2_flr + 194.0)], mat_wall="Lime", z_plinth=0.0, own_corners=False, out_sign=-1.0)

    # Crisp triangular gable walls + steep pitched roof (ridge along Y)
    add_prism_gable(b, "BH_GN", "Y", hy2 - 14.0, -hx + 14.0, hx - 14.0, z2_eave, z2_ridge, mat="Lime")
    add_prism_gable(b, "BH_GS", "Y", -hy + 14.0, -hx + 14.0, hx - 14.0, z2_eave, z2_ridge, mat="Lime")
    add_pitched_roof(b, "BH_Roof", -hx, hx, -hy, hy2, z2_eave, z2_ridge, ridge_axis="Y",
                     eave_overhang=62.0, gable_overhang_neg=52.0, gable_overhang_pos=56.0, n_trusses=4)

    return b.finish(out_dir, lod_ratios=(1.0,))


def _add_organic_log_segment(
    b: pg.AssetBuilder, label: str, x0: float, x1: float, z_center: float,
    r_base: float, r_tip: float, n_rings: int = 16, sides: int = 28, seed: int = 11,
    bark_mat: str = "Bark", cap_mat: str = "Endgrain", bow_y: float = 1.6, bow_z: float = 0.9,
):
    """Build a 3A organic bark-furrowed horizontal oak log along X with proper cylindrical UV (ZERO stretching!)
    and recessed concave end-grain growth-ring caps!
    """
    verts = []
    faces = []
    face_mats = []
    # Ring vertices: (n_rings + 1) rings * sides
    for j in range(n_rings + 1):
        t = j / n_rings
        x = x0 + (x1 - x0) * t
        r0 = r_base * (1.0 - t) + r_tip * t
        # Gentle organic trunk bow & taper
        cy = bow_y * math.sin(t * math.pi + seed * 0.7)
        cz = z_center + bow_z * math.sin(t * math.pi * 1.4 - seed * 0.4)
        # Slight chamfer/bevel right at sawn cut ends
        end_bev = 0.94 if (j == 0 or j == n_rings) else 1.0
        for k in range(sides):
            ang = k * math.tau / sides
            # Multi-harmonic bark furrows running gently twisted along trunk + 2 organic knots
            furrow = (
                0.78 * math.sin(ang * 7.0 + t * 2.1 + seed)
                + 0.46 * math.cos(ang * 13.0 - t * 3.4 + seed * 1.7)
                + 0.28 * math.sin(ang * 21.0 + t * 1.2)
            )
            knot1 = 1.65 * math.exp(-((t - 0.34) * 6.5) ** 2 - ((ang - 1.1) * 2.4) ** 2)
            knot2 = 1.30 * math.exp(-((t - 0.72) * 7.0) ** 2 - ((ang - 4.2) * 2.6) ** 2)
            rad = (r0 + furrow + knot1 + knot2) * end_bev
            vy = cy + rad * math.cos(ang)
            vz = cz + rad * math.sin(ang)
            verts.append((x, vy, vz))
    # Cap center vertices (slightly recessed for natural saw-cut cup)
    c0_idx = len(verts)
    verts.append((x0 + 0.35, 0.0, z_center))
    c1_idx = len(verts)
    verts.append((x1 - 0.35, 0.0, z_center))

    for j in range(n_rings):
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((j * sides + k, j * sides + k2, (j + 1) * sides + k2, (j + 1) * sides + k))
            face_mats.append(bark_mat)
    for k in range(sides):
        k2 = (k + 1) % sides
        faces.append((c0_idx, k2, k))
        face_mats.append(cap_mat)
        base_last = n_rings * sides
        faces.append((c1_idx, base_last + k, base_last + k2))
        face_mats.append(cap_mat)

    obj = b._new_mesh_obj(label, verts, faces, bark_mat, face_mats=face_mats)
    b._bake_smooth(obj, 52.0)

    # Proper cylindrical UV on bark (zero stretching!) + centered planar radial UV on Endgrain caps!
    data = obj.data
    uv_layer = data.uv_layers.new(name="UV0")
    uv_layer.active_render = True
    data.uv_layers.active = uv_layer
    bark_sc = pg.UV_SCALES_M.get(bark_mat, 0.90)
    eg_sc = pg.UV_SCALES_M.get(cap_mat, 0.24)
    perim_m = (math.tau * 0.5 * (r_base + r_tip)) * 0.01
    mats = list(data.materials)
    for poly in data.polygons:
        mname = mats[poly.material_index].name
        if mname == cap_mat:
            for li in poly.loop_indices:
                v_bl = data.vertices[data.loops[li].vertex_index].co
                uv_layer.data[li].uv = (v_bl.y / eg_sc + 0.5, (v_bl.z - z_center * 0.01) / eg_sc + 0.5)
        else:
            # Cylindrical mapping using loop vertex index (j, k) to avoid seam wrap glitch!
            ks = [data.loops[li].vertex_index % sides for li in poly.loop_indices]
            wrap_seam = (max(ks) - min(ks)) > (sides // 2)
            for li in poly.loop_indices:
                vi = data.loops[li].vertex_index
                j_r, k_s = divmod(vi, sides)
                kf = sides if (wrap_seam and k_s == 0) else k_s
                u_c = (kf / sides) * (perim_m / bark_sc)
                v_c = (x0 + (x1 - x0) * (j_r / n_rings)) * 0.01 / bark_sc
                uv_layer.data[li].uv = (u_c, v_c)
    return obj


def _add_split_wood_wedge(
    b: pg.AssetBuilder, label: str, center_cm, length_cm: float, radius_cm: float,
    arc_deg: float = 78.0, yaw_deg: float = 0.0, pitch_deg: float = 0.0, roll_deg: float = 0.0,
    seed: int = 1,
):
    """3A organic pie-wedge axe-split oak firewood log (curved Bark back + jagged split Sawn radial faces + Endgrain ends)."""
    b.push_xform(center_cm, (roll_deg, pitch_deg, yaw_deg))
    n_arc = 7
    n_len = 5
    half_l = 0.5 * length_cm
    arc_rad = math.radians(arc_deg)
    a0 = -0.5 * arc_rad
    # Cross-section: apex (0,0) -> curved bark rim points -> back to apex (closed wedge!)
    # Add 2 slight mid-radius points along the two radial split cheeks so split faces look organically cleft!
    verts = []
    n_sec = n_arc + 4  # 0=apex, 1=mid_left, 2..2+n_arc=bark rim, last=mid_right
    for j in range(n_len + 1):
        t = j / n_len
        x = -half_l + length_cm * t
        taper = 1.0 - 0.08 * t
        # Subtle organic twist/bend along split wood fiber
        sway = 0.55 * math.sin(t * math.pi + seed * 1.3)
        r_j = radius_cm * taper
        # 0: inner split ridge apex
        verts.append((x, sway * 0.3, 0.35 + 0.25 * math.sin(t * 5.0 + seed)))
        # 1: mid-point on left split plane
        ra = a0
        verts.append((x, 0.52 * r_j * math.sin(ra) + sway * 0.4, 0.52 * r_j * math.cos(ra) + 0.35 * math.cos(t * 6.0 + seed)))
        # 2..2+n_arc: curved bark back
        for k in range(n_arc + 1):
            ak = a0 + arc_rad * (k / n_arc)
            ridge = 0.45 * math.sin(ak * 9.0 + t * 2.5 + seed) + 0.22 * math.cos(ak * 17.0 - seed)
            rk = r_j + ridge
            verts.append((x, rk * math.sin(ak) + sway, rk * math.cos(ak)))
        # last: mid-point on right split plane
        rb = a0 + arc_rad
        verts.append((x, 0.52 * r_j * math.sin(rb) + sway * 0.4, 0.52 * r_j * math.cos(rb) - 0.30 * math.sin(t * 7.0 + seed)))

    faces = []
    face_mats = []
    for j in range(n_len):
        for k in range(n_sec):
            k2 = (k + 1) % n_sec
            faces.append((j * n_sec + k, j * n_sec + k2, (j + 1) * n_sec + k2, (j + 1) * n_sec + k))
            # Outer bark faces are k in [2 .. 2+n_arc-1]; radial split cheeks are Sawn!
            is_bark = (2 <= k < 2 + n_arc)
            face_mats.append("Bark" if is_bark else "Sawn")
    # End-grain caps
    faces.append(tuple(reversed(range(n_sec))))
    face_mats.append("Endgrain")
    faces.append(tuple(n_len * n_sec + k for k in range(n_sec)))
    face_mats.append("Endgrain")

    obj = b._new_mesh_obj(label, verts, faces, "Sawn", face_mats=face_mats)
    b._bake_smooth(obj, 38.0)
    b._uv_box(obj, long_axis=0)
    b.pop_xform()
    return obj


def build_sawbuck_station(out_dir: Path):
    """Heavy oak X-trestle sawmill frame + 3A organic bark-furrowed crooked oak log with active saw kerf & forged iron dogs."""
    b = pg.AssetBuilder("SM_LM_SawbuckStation", seed=4924, ground_mud_cm=38.0)
    for lx in (-95.0, 0.0, 95.0):
        b.beam(f"SB_LegA_{int(lx)}", (lx, -56.0, -3.0), (lx, 44.0, 108.0), 11.2, 12.2, mat="DarkWood")
        b.beam(f"SB_LegB_{int(lx)}", (lx, 56.0, -3.0), (lx, -44.0, 108.0), 11.2, 12.2, mat="DarkWood")
        b.block(f"SB_Strap_{int(lx)}", (lx, 0.0, 62.0), (13.6, 15.0, 4.2), mat="ScaleIron", bevel_cm=0.14, segments=1)
        b.bolt((lx + 7.2, 0.0, 62.0), axis="X", radius_cm=1.35, height_cm=1.8, mat="ScaleIron")
        b.bolt((lx - 7.2, 0.0, 62.0), axis="X", radius_cm=1.35, height_cm=1.8, mat="ScaleIron")
    for sy in (-46.0, 46.0):
        sk = b.block(f"SB_Skid_{int(sy)}", (0.0, sy, 5.5), (226.0, 12.5, 13.0), mat="DarkWood", bevel_cm=0.32, segments=1)
        rl = b.block(f"SB_Rail_{int(sy)}", (0.0, sy * 0.62, 38.0), (216.0, 9.2, 11.2), mat="Oak", bevel_cm=0.25, segments=1)
        # Rotate horizontal rail/skid UVs so wood grain runs lengthwise along X (zero vertical stripes!)
        for obj_h in (sk, rl):
            uvl = obj_h.data.uv_layers.active
            if uvl:
                for lp in obj_h.data.loops:
                    u0, v0 = uvl.data[lp.index].uv
                    uvl.data[lp.index].uv = (v0, u0)
        for bx in (-95.0, 0.0, 95.0):
            b.peg((bx, sy * 0.62 + (5.2 if sy > 0 else -5.2), 38.0), axis="Y", radius_cm=0.9, length_cm=2.2)

    # 3A Organic bark-furrowed crooked oak log split at X=+28 cm leaving a crisp 1.4 cm saw kerf!
    _add_organic_log_segment(b, "SB_LogL", -128.0, 27.3, 92.0, 19.6, 18.6, n_rings=18, sides=30, seed=17, bow_y=1.8, bow_z=0.9)
    _add_organic_log_segment(b, "SB_LogR", 28.7, 128.0, 92.0, 18.5, 17.2, n_rings=12, sides=30, seed=31, bow_y=-1.4, bow_z=0.7)
    # Uncut lower heartwood bridge beneath the active saw kerf
    b.lathe("SB_KerfBridge", (0.0, 0.0, 85.0), [(26.0, 10.2), (30.0, 10.2)], mat="Sawn", axis="X", sides=14, cap_mat="Endgrain")
    # Freshly sawn bright oak cant slab with waney bark edge resting beside log on the cradle
    b.block("SB_SawnFlitch", (-14.0, -25.5, 86.0), (226.0, 17.0, 6.8), mat="Sawn", rot_deg=(12.0, 0.0, 0.0), bevel_cm=0.25, segments=1, endgrain_axis=0)
    for dx in (-68.0, 68.0):
        b.block(f"SB_DogBar_{int(dx)}", (dx, 14.0, 108.0), (3.4, 27.0, 3.4), mat="ScaleIron", bevel_cm=0.14, segments=1)
        b.block(f"SB_DogSpA_{int(dx)}", (dx, 2.5, 100.5), (3.0, 3.4, 15.0), mat="ScaleIron", bevel_cm=0.14, segments=1)
        b.block(f"SB_DogSpB_{int(dx)}", (dx, 25.5, 98.5), (3.0, 3.4, 17.0), mat="ScaleIron", bevel_cm=0.14, segments=1)
        b.bolt((dx, 14.0, 110.2), axis="Z", radius_cm=1.1, height_cm=1.2, mat="ScaleIron")

    b.add_collider((0.0, 0.0, 58.0), (254.0, 120.0, 116.0))
    return b.finish(out_dir, lod_ratios=(1.0,))


def build_two_man_crosscut_saw(out_dir: Path):
    """Hero Sawmill Tool: 186 cm curved steel Two-Man Logging Crosscut Saw (双人伐木大拉锯) with M-teeth & vertical oak handles!"""
    b = pg.AssetBuilder("SM_LM_TwoManCrosscutSaw", seed=4925, ground_mud_cm=12.0, is_wall_mounted=True)
    n_seg = 26
    x0, x1 = -78.0, 78.0
    hy_t = 0.42
    top_pts, bot_pts = [], []
    for i in range(n_seg + 1):
        u = i / n_seg
        x = x0 + (x1 - x0) * u
        arch = 1.0 - (2.0 * u - 1.0) ** 2
        z_top = 15.5 + 2.8 * arch
        z_bot = 6.2 - 5.2 * arch
        top_pts.append((x, z_top))
        bot_pts.append((x, z_bot))
    tooth_pts = []
    for i in range(n_seg):
        xa, za = bot_pts[i]
        xb, zb = bot_pts[i + 1]
        xm, zm = 0.5 * (xa + xb), 0.5 * (za + zb)
        tooth_pts.append((xa, za))
        if 1 <= i <= n_seg - 2:
            tooth_pts.append((xm, zm - 3.6))
    tooth_pts.append(bot_pts[-1])

    verts, faces = [], []
    for x, zb in tooth_pts:
        u = (x - x0) / (x1 - x0)
        arch = 1.0 - (2.0 * u - 1.0) ** 2
        zt = 15.5 + 2.8 * arch
        verts.extend([(x, -hy_t, zt), (x, hy_t, zt), (x, hy_t, zb), (x, -hy_t, zb)])
    n_st = len(tooth_pts)
    for k in range(n_st - 1):
        a, c = k * 4, (k + 1) * 4
        faces.extend([
            (a + 0, c + 0, c + 3, a + 3), (c + 1, a + 1, a + 2, c + 2),
            (a + 1, c + 1, c + 0, a + 0), (a + 3, c + 3, c + 2, a + 2),
        ])
    faces.append((0, 3, 2, 1))
    last = (n_st - 1) * 4
    faces.append((last + 1, last + 2, last + 3, last + 0))
    obj = b._new_mesh_obj("CrosscutBlade", verts, faces, "Steel")
    b._bake_smooth(obj, 28.0)
    b._uv_box(obj, long_axis=0)

    for sx in (-1, 1):
        hx_end = sx * 80.5
        b.block(f"CS_Clamp_{sx}", (hx_end, 0.0, 10.5), (8.0, 3.2, 11.5), mat="ScaleIron", bevel_cm=0.2, segments=1)
        b.bolt((hx_end - sx * 2.0, 2.0, 12.5), axis="Y", radius_cm=0.8, height_cm=0.8, mat="Brass")
        b.bolt((hx_end - sx * 2.0, 2.0, 8.5), axis="Y", radius_cm=0.8, height_cm=0.8, mat="Brass")
        b.lathe(f"CS_Handle_{sx}", (hx_end + sx * 2.5, 0.0, 14.5),
                [(0.0, 1.9), (3.0, 2.4), (13.0, 2.6), (23.0, 2.1), (27.0, 2.5), (29.0, 1.4), (30.0, 0.0)],
                mat="OiledOak", axis="Z", sides=14)
        b.lathe(f"CS_Ferrule_{sx}", (hx_end + sx * 2.5, 0.0, 14.5),
                [(-1.0, 2.1), (3.2, 2.3)], mat="Brass", axis="Z", sides=14)

    b.add_collider((0.0, 0.0, 18.0), (178.0, 10.0, 40.0))
    return b.finish(out_dir, lod_ratios=(1.0,))


def build_frame_pit_saw(out_dir: Path):
    """Hero Sawmill Tool: 118 x 68 cm Medieval Wooden Frame Buck/Pit Saw (传统木框锯) with tension cord & steel blade!"""
    b = pg.AssetBuilder("SM_LM_FramePitSaw", seed=4926, ground_mud_cm=15.0, is_wall_mounted=True)
    for sx in (-52.0, 52.0):
        b.block(f"FS_Cheek_{int(sx)}", (sx, 0.0, 32.0), (7.5, 4.8, 64.0), mat="OiledOak", bevel_cm=0.3, segments=1)
        b.lathe(f"FS_Grip_{int(sx)}", (sx, 0.0, -10.0),
                [(0.0, 1.7), (5.0, 2.2), (10.5, 1.8)], mat="DarkWood", axis="Z", sides=12)
    b.block("FS_Stretcher", (0.0, 0.0, 34.0), (102.0, 4.4, 7.2), mat="Oak", bevel_cm=0.25, segments=1)
    b.rope_braid("FS_CordA", [(-52.0, -1.2, 57.5), (52.0, -1.2, 57.5)], radius_cm=0.85, mat="Rope", pitch_cm=5.0)
    b.rope_braid("FS_CordB", [(-52.0, 1.2, 57.5), (52.0, 1.2, 57.5)], radius_cm=0.85, mat="Rope", pitch_cm=5.0)
    b.block("FS_Toggle", (8.0, 0.0, 47.0), (3.6, 2.8, 25.0), mat="OiledOak", rot_deg=(0.0, 14.0, 0.0), bevel_cm=0.18, segments=1)

    n_t = 22
    verts, faces = [], []
    for k in range(n_t + 1):
        x = -50.0 + 100.0 * k / n_t
        zb = 3.2 if (k % 2 == 1 and 1 <= k <= n_t - 1) else 5.8
        verts.extend([(x, -0.35, 12.2), (x, 0.35, 12.2), (x, 0.35, zb), (x, -0.35, zb)])
    for k in range(n_t):
        a, c = k * 4, (k + 1) * 4
        faces.extend([
            (a + 0, c + 0, c + 3, a + 3), (c + 1, a + 1, a + 2, c + 2),
            (a + 1, c + 1, c + 0, a + 0), (a + 3, c + 3, c + 2, a + 2),
        ])
    faces.append((0, 3, 2, 1))
    l = n_t * 4
    faces.append((l + 1, l + 2, l + 3, l + 0))
    obj = b._new_mesh_obj("FrameSawBlade", verts, faces, "Steel")
    b._bake_smooth(obj, 28.0)
    b._uv_box(obj, long_axis=0)
    for sx in (-52.0, 52.0):
        b.block(f"FS_Tang_{int(sx)}", (sx, 0.0, 8.8), (9.0, 2.4, 4.8), mat="ScaleIron", bevel_cm=0.12, segments=1)

    b.add_collider((0.0, 0.0, 30.0), (114.0, 8.0, 74.0))
    return b.finish(out_dir, lod_ratios=(1.0,))


def build_workbench_saw_set(out_dir: Path):
    """Hero Tool Room Workbench Set: Carpenter panel hand saw + wooden mallet + steel drawknife & chisels!"""
    b = pg.AssetBuilder("SM_LM_WorkbenchSawSet", seed=4927, ground_mud_cm=5.0, is_wall_mounted=True)
    b.block("HS_Blade", (8.0, 0.0, 1.2), (56.0, 11.5, 0.65), mat="Steel", bevel_cm=0.06, segments=1)
    for k in range(12):
        b.block(f"HS_Tooth_{k}", (-16.0 + k * 4.4, -6.2, 1.2), (2.2, 1.8, 0.6), mat="Steel", rot_deg=(0.0, 0.0, 35.0), bevel_cm=0.04, segments=1)
    b.block("HS_GripBack", (-25.0, 1.0, 2.0), (14.0, 15.0, 3.0), mat="OiledOak", bevel_cm=0.3, segments=1)
    b.block("HS_GripLoop", (-33.0, 1.0, 2.0), (4.5, 13.0, 2.8), mat="OiledOak", bevel_cm=0.25, segments=1)
    for rx in (-21.0, -24.5):
        b.bolt((rx, 1.5, 3.6), axis="Z", radius_cm=0.65, height_cm=0.4, mat="Brass")
    b.block("ML_Head", (24.0, 22.0, 5.2), (16.5, 9.8, 10.2), mat="DarkWood", rot_deg=(0.0, 0.0, -18.0), bevel_cm=0.4, segments=1)
    b.block("ML_Handle", (11.0, 18.0, 4.4), (30.0, 3.4, 3.0), mat="OiledOak", rot_deg=(0.0, 0.0, -18.0), bevel_cm=0.2, segments=1)
    for ci, (cy, yaw) in enumerate(((-18.0, 8.0), (-25.0, -6.0))):
        b.block(f"CH_Blade_{ci}", (10.0, cy, 1.2), (18.0, 2.4 - ci * 0.6, 0.7), mat="Steel", rot_deg=(0.0, 0.0, yaw), bevel_cm=0.06, segments=1)
        b.lathe(f"CH_Hnd_{ci}", (-5.0, cy, 1.8), [(-6.0, 1.4), (0.0, 1.7), (7.0, 1.2)], mat="OiledOak", axis="X", sides=10, rot_deg=(0, 0, yaw))
        b.lathe(f"CH_Fer_{ci}", (1.5, cy, 1.8), [(-0.8, 1.25), (0.8, 1.25)], mat="Brass", axis="X", sides=10, rot_deg=(0, 0, yaw))
    return b.finish(out_dir, lod_ratios=(1.0,))


def _build_scarred_chopping_stump(
    out_dir: Path, name: str, seed: int, height_cm: float, r_top: float,
    root_angles: list, split_angles: list, chop_scars: list,
    main_kerf: tuple, hoop_z: float, split_wedges: list, add_cleft_billet: bool = False,
):
    """Build a TRUE 3A weathered, deeply scarred oak chopping stump:
       - 48-radial x 22-ring fluted trunk with asymmetric gnarled buttress roots buried -20 cm underground
       - Deep vertical bark furrows, peeled bark chips & 3 jagged vertical drying/seasoning splits
       - 10-ring high-res concave chopped end-grain top face with sculpted V-shaped overlapping axe hack scars
         and a crisp primary V-kerf groove sized for official SM_BattleAxe!
       - Hammered hand-forged iron binding hoop with lap-joint & protruding dome rivets
       - Organic pie-wedge split oak firewood pieces (ZERO procedural axe, ZERO boxy blocks!)
       - Rich custom Col weathering: dark sap/rot cavities inside scars & drying splits, mud splash up roots!
    """
    b = pg.AssetBuilder(name, seed=seed, ground_mud_cm=42.0)
    sides = 60
    n_v = 22
    z_bot = -20.0
    n_cap_rings = 12

    def trunk_radius(ang: float, z: float):
        tz = max(0.0, min(1.0, (z - z_bot) / (height_cm - z_bot)))
        # Base waist profile: slight pinch mid-trunk, wide flaring roots below Z=22 cm
        waist = r_top * (1.03 - 0.06 * math.sin(tz * math.pi) + 0.04 * (1.0 - tz))
        # Asymmetric gnarled buttress roots concentrated in lower half (strongest below Z=18 cm)
        root_env = max(0.0, 1.0 - (z + 8.0) / 48.0) ** 1.65
        root_flare = 0.0
        for ra, r_amp, r_sharp in root_angles:
            da = math.atan2(math.sin(ang - ra), math.cos(ang - ra))
            root_flare += r_amp * math.exp(-((da * r_sharp) ** 2))
        r = waist + root_env * (5.0 + root_flare)
        # Multi-frequency organic oak bark furrows with subtle trunk grain spiral
        twist_a = ang + 0.14 * tz
        furrow = (
            1.15 * math.sin(twist_a * 9.0 + seed * 0.7)
            + 0.72 * math.cos(twist_a * 17.0 - seed * 1.3 + tz * 1.4)
            + 0.42 * math.sin(twist_a * 29.0 + tz * 3.1)
        )
        # Chipped / missing bark pockets near upper rim from stray axe blows
        rim_env = max(0.0, (z - (height_cm - 22.0)) / 22.0) ** 1.4
        chip = -2.2 * rim_env * max(0.0, math.sin(ang * 3.0 + seed) * math.cos(ang * 5.0 - 0.8))
        # Deep jagged vertical seasoning/drying cracks (widest near upper half!)
        crack_env = max(0.0, (z + 6.0) / (height_cm + 6.0)) ** 0.9
        crack = 0.0
        for sa, s_depth, s_width in split_angles:
            wiggle = 0.055 * math.sin(tz * 7.5 + sa * 3.0)
            da = abs(math.atan2(math.sin(ang - (sa + wiggle)), math.cos(ang - (sa + wiggle))))
            if da < s_width:
                crack += s_depth * ((1.0 - da / s_width) ** 1.6) * crack_env
        return max(12.0, r + furrow + chip - crack), crack

    def top_z_and_scar(px: float, py: float):
        """Evaluate sculpted concave chopped top height + scar cavity intensity at (px, py)."""
        r_norm = math.hypot(px, py) / max(1.0, r_top)
        # Concave dished bowl worn down from years of wood chopping (-2.4 cm at center) + slight weathered rim bevel
        bowl = -2.4 * max(0.0, 1.0 - r_norm * r_norm) ** 1.35
        rim_roll = -1.6 * max(0.0, (r_norm - 0.86) / 0.14) ** 2
        # Micro wood-grain undulation
        grain = 0.32 * math.sin(px * 0.24 + py * 0.17 + seed) + 0.18 * math.cos(px * 0.51 - py * 0.39)
        dz = bowl + rim_roll + grain
        scar_cav = 0.0
        # Evaluate all overlapping V-shaped axe hack scars: (cx, cy, angle_deg, half_len, half_w, depth)
        all_scars = list(chop_scars) + [main_kerf]
        for si, (cx, cy, ang_d, hlen, hw, depth) in enumerate(all_scars):
            ar = math.radians(ang_d)
            ca, sa = math.cos(ar), math.sin(ar)
            dx, dy = px - cx, py - cy
            u_along = dx * ca + dy * sa
            v_perp = -dx * sa + dy * ca
            if abs(u_along) < hlen and abs(v_perp) < hw:
                t_u = 1.0 - (u_along / hlen) ** 2
                # Sharp V-groove profile across axe blade width!
                t_v = 1.0 - abs(v_perp) / hw
                cut = depth * t_u * (t_v ** 1.25)
                if cut > 0.0:
                    dz -= cut
                    # Main kerf & deep hacks get extra dark cavity staining
                    scar_cav = max(scar_cav, min(1.0, (cut / max(0.8, depth)) * (1.15 if si == len(all_scars) - 1 else 0.88)))
        # Subtle drying crack extensions across top end-grain radiating from rim inward
        ang = math.atan2(py, px)
        for sa, s_depth, s_width in split_angles:
            da = abs(math.atan2(math.sin(ang - sa), math.cos(ang - sa)))
            if da < s_width * 0.85 and r_norm > 0.18:
                c_cut = 1.9 * ((1.0 - da / (s_width * 0.85)) ** 1.6) * min(1.0, (r_norm - 0.18) / 0.55)
                dz -= c_cut
                scar_cav = max(scar_cav, min(1.0, c_cut * 0.65))
        return height_cm + dz, scar_cav

    # 1) Build sculpted stump mesh directly (Bark trunk + high-res concentric Endgrain top + closed bottom)
    verts = []
    v_meta = []  # (is_top, crack_or_scar_cav, z_cm) for custom weathering vertex color
    faces = []
    face_mats = []

    # Trunk rings j=0..n_v
    for j in range(n_v + 1):
        tz = j / n_v
        z = z_bot + (height_cm - z_bot) * tz
        for k in range(sides):
            ang = k * math.tau / sides
            rad, crack = trunk_radius(ang, z)
            px, py = rad * math.cos(ang), rad * math.sin(ang)
            if j == n_v:
                pz, sc = top_z_and_scar(px, py)
                verts.append((px, py, pz))
                v_meta.append((True, max(sc, min(1.0, crack * 0.25)), pz))
            else:
                verts.append((px, py, z))
                v_meta.append((False, min(1.0, crack * 0.30), z))

    # Trunk side faces (Bark)
    for j in range(n_v):
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((j * sides + k, j * sides + k2, (j + 1) * sides + k2, (j + 1) * sides + k))
            face_mats.append("Bark")

    # High-resolution concentric end-grain top cap (connects outer rim ring n_v inward to center!)
    # Assign aged DarkWood inside deep sculpted V-shaped axe hack scars & drying cracks for authentic weathered contrast!
    prev_ring = [n_v * sides + k for k in range(sides)]
    for cr in range(1, n_cap_rings):
        frac = 1.0 - cr / n_cap_rings
        cur_ring = []
        for k in range(sides):
            ang = k * math.tau / sides
            r_outer, _ = trunk_radius(ang, height_cm)
            rad = r_outer * frac
            px, py = rad * math.cos(ang), rad * math.sin(ang)
            pz, sc = top_z_and_scar(px, py)
            cur_ring.append(len(verts))
            verts.append((px, py, pz))
            v_meta.append((True, sc, pz))
        for k in range(sides):
            k2 = (k + 1) % sides
            q = (prev_ring[k], prev_ring[k2], cur_ring[k2], cur_ring[k])
            faces.append(q)
            avg_sc = 0.25 * sum(v_meta[vi][1] for vi in q)
            face_mats.append("DarkWood" if avg_sc > 0.42 else "Endgrain")
        prev_ring = cur_ring

    # Center vertex of top face
    cz, csc = top_z_and_scar(0.0, 0.0)
    c_top_idx = len(verts)
    verts.append((0.0, 0.0, cz))
    v_meta.append((True, csc, cz))
    for k in range(sides):
        k2 = (k + 1) % sides
        tri = (prev_ring[k], prev_ring[k2], c_top_idx)
        faces.append(tri)
        avg_sc = (v_meta[tri[0]][1] + v_meta[tri[1]][1] + v_meta[tri[2]][1]) / 3.0
        face_mats.append("DarkWood" if avg_sc > 0.42 else "Endgrain")

    # Closed bottom cap (buried at Z=-20 cm)
    c_bot_idx = len(verts)
    verts.append((0.0, 0.0, z_bot))
    v_meta.append((False, 0.6, z_bot))
    for k in range(sides):
        k2 = (k + 1) % sides
        faces.append((c_bot_idx, k2, k))
        face_mats.append("Bark")

    stump_obj = b._new_mesh_obj("StumpBody", verts, faces, "Bark", face_mats=face_mats)
    b._bake_smooth(stump_obj, 50.0)

    # Proper Cylindrical Bark UV on trunk + Planar Radial Endgrain UV on chopped top!
    data = stump_obj.data
    uv_layer = data.uv_layers.new(name="UV0")
    uv_layer.active_render = True
    data.uv_layers.active = uv_layer
    bark_sc = pg.UV_SCALES_M.get("Bark", 0.90)
    eg_sc = pg.UV_SCALES_M.get("Endgrain", 0.36)
    perim_m = (math.tau * r_top) * 0.01
    mats = list(data.materials)
    for poly in data.polygons:
        mname = mats[poly.material_index].name
        if mname in ("Endgrain", "DarkWood"):
            for li in poly.loop_indices:
                v_bl = data.vertices[data.loops[li].vertex_index].co
                uv_layer.data[li].uv = (v_bl.x / eg_sc + 0.5, v_bl.y / eg_sc + 0.5)
        else:
            vis = [data.loops[li].vertex_index for li in poly.loop_indices]
            if all(vi < (n_v + 1) * sides for vi in vis):
                ks = [vi % sides for vi in vis]
                wrap = (max(ks) - min(ks)) > (sides // 2)
                for li in poly.loop_indices:
                    vi = data.loops[li].vertex_index
                    j_r, k_s = divmod(vi, sides)
                    kf = sides if (wrap and k_s == 0) else k_s
                    u_c = (kf / sides) * (perim_m / bark_sc)
                    v_c = (z_bot + (height_cm - z_bot) * (j_r / n_v)) * 0.01 / bark_sc
                    uv_layer.data[li].uv = (u_c, v_c)
            else:
                for li in poly.loop_indices:
                    v_bl = data.vertices[data.loops[li].vertex_index].co
                    uv_layer.data[li].uv = (v_bl.x / bark_sc, v_bl.y / bark_sc)

    # 2) Hand-forged hammered iron binding hoop hugging sculpted bark tightly (embeds slightly into bark ridges -> ZERO air gap!)
    hoop_pts = []
    for k in range(48):
        ang = k * math.tau / 48
        rr, _ = trunk_radius(ang, hoop_z)
        r_h = rr + 0.15
        hoop_pts.append((r_h * math.cos(ang), r_h * math.sin(ang), hoop_z + 0.25 * math.sin(ang * 3.0 + seed)))
    b.strap("CS_ForgedHoop", hoop_pts, width_cm=5.2, thick_cm=1.8, mat="ScaleIron", cyclic=True, up_hint=(0.0, 0.0, 1.0))
    # Forged dome rivets seated solidly onto the iron hoop!
    for ri, r_ang in enumerate((0.15, 0.34, 2.2, 4.3)):
        rr, _ = trunk_radius(r_ang, hoop_z)
        r_h = rr + 0.95
        rx, ry = r_h * math.cos(r_ang), r_h * math.sin(r_ang)
        b.rivet((rx, ry, hoop_z + (1.0 if ri % 2 == 0 else -1.0)), axis="X" if abs(math.cos(r_ang)) > 0.7 else "Y",
                radius_cm=0.85, height_cm=0.75, mat="ScaleIron")

    # 3) Optional half-split cracked oak log billet standing cleanly on the OPPOSITE side (+16, +15) clear of SM_BattleAxe!
    if add_cleft_billet:
        _add_split_wood_wedge(b, "CS_TopHalfA", (15.0, 13.0, height_cm + 10.5), 25.0, 9.6, arc_deg=148.0,
                              yaw_deg=-35.0, pitch_deg=90.0, roll_deg=10.0, seed=seed + 3)
        _add_split_wood_wedge(b, "CS_TopHalfB", (19.0, 17.5, height_cm + 10.0), 24.0, 8.8, arc_deg=130.0,
                              yaw_deg=148.0, pitch_deg=85.0, roll_deg=-8.0, seed=seed + 7)

    # 4) Organic pie-wedge split oak firewood resting naturally around root flares (ZERO brick boxes!)
    for idx, (fx, fy, fz, flen, frad, farc, fyaw, fpitch, froll) in enumerate(split_wedges):
        _add_split_wood_wedge(b, f"CS_SplitWedge_{idx}", (fx, fy, fz), flen, frad, arc_deg=farc,
                              yaw_deg=fyaw, pitch_deg=fpitch, roll_deg=froll, seed=seed + idx * 13)

    b.add_collider((0.0, 0.0, height_cm * 0.5), (r_top * 2.35, r_top * 2.35, height_cm + 8.0))
    info = b.finish(out_dir, lod_ratios=(1.0,))

    # Post-bake rich dark cavity weathering inside sculpted chop scars, vertical drying splits & root flares!
    mesh_obj = bpy.data.objects.get(name)
    if mesh_obj and mesh_obj.data.color_attributes.get("Col"):
        col_attr = mesh_obj.data.color_attributes.get("Col")
        me = mesh_obj.data
        for lp in me.loops:
            co = me.vertices[lp.vertex_index].co
            # UE cm coords from Blender m coords: x=co.x*100, y=-co.y*100, z=co.z*100
            x_cm, y_cm, z_cm = co.x * 100.0, -co.y * 100.0, co.z * 100.0
            old_r, old_g, old_b, _ = col_attr.data[lp.index].color
            # Compute top scar darkness & rim highlight directly by spatial coordinate!
            r_out = old_r
            g_out = old_g
            b_out = old_b
            if z_cm > height_cm - 9.0 and math.hypot(x_cm, y_cm) < r_top + 4.0:
                _, scar_cav = top_z_and_scar(x_cm, y_cm)
                # Deep dark grime inside axe chop kerfs & drying cracks + worn pale wood on raised center!
                r_out = min(1.0, max(old_r, 0.22 + 0.76 * scar_cav))
                g_out = min(0.18, old_g * 0.25)  # Keep chopped top free of ground mud!
                b_out = min(1.0, max(old_b, 0.45 * (1.0 - scar_cav)))
            elif z_cm < 24.0:
                # Damp earthy mud splash clinging naturally around root flutes
                mud_h = max(0.0, min(1.0, (24.0 - z_cm) / 26.0))
                g_out = min(1.0, max(old_g, 0.78 * (mud_h ** 1.25)))
            col_attr.data[lp.index].color = (r_out, g_out, b_out, 1.0)
        pg._active(mesh_obj)
        bpy.ops.export_scene.fbx(
            filepath=str(out_dir / f"{name}.fbx"),
            use_selection=True, object_types={"MESH"}, axis_forward="-Y", axis_up="Z",
            mesh_smooth_type="FACE", use_tspace=True, colors_type="LINEAR",
            bake_anim=False, add_leaf_bones=False,
        )
    return info


def build_chopping_stump_a(out_dir: Path):
    """Primary 3A scarred oak chopping stump (top Z=72 cm, central V-kerf at (6, -2) yaw=18 deg for official SM_BattleAxe!)."""
    return _build_scarred_chopping_stump(
        out_dir, "SM_LM_ChoppingStumpA", seed=4941, height_cm=72.0, r_top=33.5,
        root_angles=[
            (0.25, 11.5, 2.2), (1.38, 13.0, 2.0), (2.42, 9.5, 2.5),
            (3.55, 12.2, 2.1), (4.72, 10.4, 2.3), (5.58, 8.8, 2.7),
        ],
        split_angles=[(0.95, 5.2, 0.14), (2.92, 4.4, 0.12), (4.98, 3.8, 0.11)],
        chop_scars=[
            # (cx, cy, angle_deg, half_len, half_w, depth_cm)
            (-11.0, 7.5, -34.0, 12.5, 1.9, 2.2),
            (-6.5, -12.0, 52.0, 11.0, 1.7, 1.9),
            (13.0, 10.5, 12.0, 10.0, 1.6, 1.8),
            (-14.0, -5.0, 78.0, 9.5, 1.5, 1.6),
            (4.0, 14.0, -18.0, 11.5, 1.8, 2.0),
            (15.5, -9.5, 38.0, 9.0, 1.5, 1.7),
            (-2.0, 2.0, -64.0, 12.0, 1.7, 2.1),
        ],
        # Primary deep splitting kerf aligned with official SM_BattleAxe blade!
        main_kerf=(6.0, -2.0, 18.0, 14.5, 2.6, 4.6),
        hoop_z=55.5,
        split_wedges=[
            # (fx, fy, fz, length, rad, arc_deg, yaw, pitch, roll)
            (-48.0, -22.0, 1.2, 36.0, 9.2, 82.0, 24.0, 3.0, -12.0),
            (46.0, -31.0, 1.0, 34.0, 8.6, 72.0, -38.0, -2.0, 115.0),
            (52.0, 20.0, 1.4, 38.0, 9.6, 88.0, 72.0, 4.0, -92.0),
            (-35.0, 46.0, 1.1, 32.0, 8.2, 68.0, -18.0, -3.0, 162.0),
            (-44.0, 14.0, 14.0, 35.0, 8.8, 76.0, 15.0, 54.0, 28.0),  # propped leaning against stump bark!
        ],
        add_cleft_billet=False,
    )


def build_chopping_stump_b(out_dir: Path):
    """2nd distinct 3A scarred oak chopping stump (top Z=68 cm, wider 36 cm radius, cleft billet + V-kerf at (-4, 3) yaw=-28 deg!)."""
    return _build_scarred_chopping_stump(
        out_dir, "SM_LM_ChoppingStumpB", seed=4942, height_cm=68.0, r_top=36.0,
        root_angles=[
            (0.65, 13.5, 1.9), (1.95, 11.2, 2.2), (3.12, 12.8, 2.0),
            (4.35, 9.8, 2.4), (5.48, 12.0, 2.1),
        ],
        split_angles=[(1.42, 5.6, 0.15), (3.85, 4.8, 0.13), (5.75, 3.9, 0.11)],
        chop_scars=[
            (10.0, 9.0, 44.0, 13.0, 1.9, 2.3),
            (12.0, -11.0, -22.0, 11.5, 1.8, 2.0),
            (-12.0, -10.5, 62.0, 10.5, 1.7, 1.9),
            (2.0, -16.0, 8.0, 11.0, 1.6, 1.7),
            (-16.0, -2.0, -48.0, 10.0, 1.6, 1.8),
            (6.5, 15.5, -14.0, 9.5, 1.5, 1.6),
        ],
        main_kerf=(6.0, -3.0, -28.0, 14.5, 2.6, 4.5),
        hoop_z=52.0,
        split_wedges=[
            (48.0, 26.0, 1.2, 35.0, 9.0, 80.0, -24.0, 2.0, 108.0),
            (-50.0, -26.0, 1.0, 33.0, 8.5, 70.0, 48.0, -3.0, -20.0),
            (18.0, -50.0, 1.3, 37.0, 9.4, 84.0, 12.0, 2.0, 172.0),
        ],
        add_cleft_billet=True,
    )


def build_bunk_bed(out_dir: Path):
    """3A Two-tier medieval timber lumberjack bunk bed with crisp segments=1 joinery, forged iron corner straps,
    sculpted slumped linen pillows, creased quilted mattresses & softly draped overhanging wool blankets!
    """
    b = pg.AssetBuilder("SM_LM_BunkBed", seed=4929, ground_mud_cm=16.0)
    lx, ly = 102.0, 47.0
    for sx in (-lx, lx):
        for sy in (-ly, ly):
            b.block(f"BB_Post_{int(sx)}_{int(sy)}", (sx, sy, 96.0), (10.5, 10.5, 192.0), mat="DarkWood", bevel_cm=0.35, segments=1)
            b.block(f"BB_Cap_{int(sx)}_{int(sy)}", (sx, sy, 194.0), (12.4, 12.4, 4.2), mat="OiledOak", bevel_cm=0.3, segments=1)
            for bz_i in (44.0, 138.0):
                b.block(f"BB_Iron_{int(sx)}_{int(sy)}_{int(bz_i)}", (sx, sy, bz_i), (11.6, 11.6, 8.0), mat="ScaleIron", bevel_cm=0.14, segments=1)
    for bi, bz in enumerate((44.0, 138.0)):
        for sy in (-ly, ly):
            b.block(f"BB_SR_{bi}_{int(sy)}", (0.0, sy, bz), (192.0, 5.2, 14.0), mat="Oak", bevel_cm=0.22, segments=1)
        for sx in (-lx, lx):
            b.block(f"BB_ER_{bi}_{int(sx)}", (sx, 0.0, bz + 8.0), (5.2, 82.0, 26.0), mat="Oak", bevel_cm=0.22, segments=1)
        for sl in range(-84, 88, 24):
            b.block(f"BB_Sl_{bi}_{sl}", (float(sl), 0.0, bz - 2.0), (13.0, 84.0, 3.0), mat="Sawn", bevel_cm=0.1, segments=1)

        # 1) Sculpted organic quilted mattress pad (soft crown + subtle sleeper sag + creased edges!)
        nu_m, nv_m = 13, 9
        m_grid = []
        for i in range(nu_m):
            u = -1.0 + 2.0 * i / (nu_m - 1)
            row = []
            for j in range(nv_m):
                v = -1.0 + 2.0 * j / (nv_m - 1)
                edge_drop = -2.8 * (max(abs(u), abs(v)) ** 4)
                sag = -1.4 * math.exp(-((u + 0.05) * 2.0) ** 2 - (v * 2.1) ** 2)
                quilt = 0.55 * math.sin(u * 9.0 + bi) * math.cos(v * 6.5)
                row.append((u * 93.0, v * 40.5, bz + 12.0 + edge_drop + sag + quilt))
            m_grid.append(row)
        b.thick_grid(f"BB_Mat_{bi}", m_grid, thick_cm=11.0, mat="Linen")

        # 2) Sculpted slumped linen pillow (puffed edges + natural head depression in middle!)
        nu_p, nv_p = 9, 9
        p_grid = []
        for i in range(nu_p):
            u = -1.0 + 2.0 * i / (nu_p - 1)
            row = []
            for j in range(nv_p):
                v = -1.0 + 2.0 * j / (nv_p - 1)
                r2 = min(1.0, u * u + v * v)
                puff = 4.6 * ((1.0 - r2 * 0.88) ** 0.7)
                dent = -1.9 * math.exp(-(u * 2.4) ** 2 - (v * 2.2) ** 2)
                tilt = -1.6 * u
                row.append((-70.0 + u * 18.0, v * 29.0, bz + 19.5 + puff + dent + tilt))
            p_grid.append(row)
        b.thick_grid(f"BB_Pil_{bi}", p_grid, thick_cm=5.2, mat="Linen")

        # 3) Softly draped overhanging wool blanket (covers lower 2/3 of bed + drapes down over front rail with folds!)
        nu_b, nv_b = 11, 11
        b_grid = []
        x_start = -26.0 + (8.0 if bi == 1 else 0.0)
        x_end = 94.0
        for i in range(nu_b):
            tu = i / (nu_b - 1)
            px = x_start + (x_end - x_start) * tu
            row = []
            for j in range(nv_b):
                tv = j / (nv_b - 1)
                # tv in [0..0.78] crosses mattress width [-41..+42]; tv in [0.78..1.0] drapes down front edge!
                fold = 1.1 * math.sin(tu * 11.0 + bi * 1.9 + tv * 3.0) + 0.65 * math.cos(tu * 21.0 - tv * 5.0)
                if tv <= 0.78:
                    sv = tv / 0.78
                    py = -41.5 + 84.5 * sv
                    pz = bz + 19.2 - 1.5 * ((2.0 * sv - 1.0) ** 4) + fold * 0.7
                else:
                    dr = (tv - 0.78) / 0.22
                    py = 43.0 + 2.4 * math.sin(dr * 1.57) + fold * 0.5
                    pz = bz + 17.8 - dr * 15.5 + 0.6 * math.sin(tu * 14.0 + bi)
                row.append((px, py, pz))
            b_grid.append(row)
        b.thick_grid(f"BB_Blnk_{bi}", b_grid, thick_cm=2.6, mat="Blanket")

    b.block("BB_Guard", (-28.0, ly, 166.0), (132.0, 4.5, 9.0), mat="OiledOak", bevel_cm=0.2, segments=1)
    for ldx in (48.0, 86.0):
        b.block(f"BB_LR_{int(ldx)}", (ldx, ly + 8.0, 90.0), (5.0, 5.5, 174.0), mat="OiledOak", bevel_cm=0.18, segments=1)
    for rz in (34.0, 68.0, 102.0, 136.0):
        b.block(f"BB_Rg_{int(rz)}", (67.0, ly + 8.0, rz), (34.0, 4.2, 4.2), mat="Oak", bevel_cm=0.16, segments=1)
    b.add_collider((0.0, 0.0, 96.0), (214.0, 104.0, 194.0))
    return b.finish(out_dir, lod_ratios=(1.0,))


def build_timber_rack(out_dir: Path):
    """Warehouse/Yard Heavy Cantilevered Timber Lumber Storage Rack (270 x 112 x 218 cm) — crisp segments=1 joinery,
    forged iron joint collars & organically staggered seasoned lumber stacks (ZERO thin-plank triangulation glitches!).
    """
    b = pg.AssetBuilder("SM_LM_TimberRack", seed=4930, ground_mud_cm=32.0)
    for sx in (-105.0, 0.0, 105.0):
        b.block(f"TRK_Foot_{int(sx)}", (sx, 0.0, 6.0), (14.0, 108.0, 12.0), mat="DarkWood", bevel_cm=0.25, segments=1)
        b.block(f"TRK_Up_{int(sx)}", (sx, -34.0, 114.0), (13.5, 13.5, 204.0), mat="DarkWood", bevel_cm=0.25, segments=1)
        b.beam(f"TRK_Br_{int(sx)}", (sx, 38.0, 12.0), (sx, -28.0, 68.0), 9.5, 9.5, mat="DarkWood")
        for az in (68.0, 134.0, 198.0):
            b.block(f"TRK_Arm_{int(sx)}_{int(az)}", (sx, 14.0, az), (10.5, 82.0, 10.5), mat="Oak", bevel_cm=0.2, segments=1)
            b.block(f"TRK_Collar_{int(sx)}_{int(az)}", (sx, -34.0, az), (15.2, 15.2, 7.5), mat="ScaleIron", bevel_cm=0.12, segments=1)
            b.beam(f"TRK_Gus_{int(sx)}_{int(az)}", (sx, -28.0, az - 26.0), (sx, 22.0, az - 5.0), 7.5, 7.5, mat="Oak")
    for tz in (60.0, 134.0, 196.0):
        b.block(f"TRK_Tie_{int(tz)}", (0.0, -44.0, tz), (232.0, 5.5, 11.5), mat="DarkWood", bevel_cm=0.18, segments=1)
    # Organically staggered seasoned boards & timbers across all 3 tiers!
    for tier_i, tz in enumerate((76.5, 142.5, 206.5)):
        n_boards = 5 - tier_i
        for bi in range(n_boards):
            by = -16.0 + bi * 14.8
            for layer in range(2 if tier_i < 2 else 1):
                jitter_x = b.rng.uniform(-9.0, 9.0)
                blen = 256.0 - layer * 18.0 + b.rng.uniform(-14.0, 8.0)
                b.block(f"TRK_B_{tier_i}_{bi}_{layer}", (jitter_x, by, tz + layer * 5.8),
                        (blen, 11.8, 5.0), mat="Sawn" if (bi + layer) % 2 == 0 else "Oak",
                        bevel_cm=0.18, segments=1, endgrain_axis=0)
    b.add_collider((0.0, 0.0, 108.0), (268.0, 110.0, 216.0))
    return b.finish(out_dir, lod_ratios=(1.0,))


def build_camp_fence_panel(out_dir: Path):
    """Secondary-Developed Weathered Stable-Style Sawmill Camp Fence Panel (240 cm post-to-post bay, local X in [0..240])."""
    b = pg.AssetBuilder("SM_LM_CampFencePanel", seed=4931, ground_mud_cm=58.0)
    span = 240.0
    b.block("CF_PostL", (0.0, 0.0, 44.0), (17.0, 17.0, 198.0), mat="DarkWood", bevel_cm=0.55, segments=1)
    b.block("CF_CapL", (0.0, 0.0, 145.5), (20.5, 20.5, 5.0), mat="OiledOak", bevel_cm=0.45, segments=1)
    b.block("CF_CollarL", (0.0, 0.0, -4.0), (22.0, 22.0, 26.0), mat="Footing", bevel_cm=0.65, segments=1)
    b.block("CF_MidStud", (span * 0.5, 5.5, 68.0), (8.5, 5.0, 116.0), mat="Oak", bevel_cm=0.22, segments=1)
    for ri, rz in enumerate((34.0, 78.0, 122.0)):
        mat_r = "Oak" if ri == 1 else "DarkWood"
        b.block(f"CF_Rail_{ri}", (span * 0.5, 0.0, rz), (span - 14.0, 5.8, 13.5), mat=mat_r, bevel_cm=0.28, segments=1)
        b.block(f"CF_Strap_{ri}", (12.0, -3.5, rz), (10.0, 1.2, 4.2), mat="ScaleIron", bevel_cm=0.1, segments=1)
        b.block(f"CF_StrapR_{ri}", (span - 12.0, -3.5, rz), (10.0, 1.2, 4.2), mat="ScaleIron", bevel_cm=0.1, segments=1)
    b.beam("CF_Brace", (12.0, -5.2, 38.0), (span * 0.5 - 4.0, -5.2, 118.0), 8.5, 4.2, mat="DarkWood")
    b.add_collider((span * 0.5, 0.0, 72.0), (span, 18.0, 146.0))
    return b.finish(out_dir, lod_ratios=(1.0,))


def build_camp_fence_post(out_dir: Path):
    """Matching Heavy Weathered Oak Closing/Corner Post for SM_LM_CampFencePanel (deep -55 cm burial!)."""
    b = pg.AssetBuilder("SM_LM_CampFencePost", seed=4932, ground_mud_cm=58.0)
    b.block("CP_Body", (0.0, 0.0, 46.0), (19.0, 19.0, 202.0), mat="DarkWood", bevel_cm=0.55, segments=1)
    b.block("CP_Cap", (0.0, 0.0, 149.5), (23.0, 23.0, 5.5), mat="OiledOak", bevel_cm=0.5, segments=1)
    b.block("CP_Band", (0.0, 0.0, 136.0), (20.4, 20.4, 4.5), mat="ScaleIron", bevel_cm=0.14, segments=1)
    b.block("CP_Footing", (0.0, 0.0, -4.0), (26.0, 26.0, 32.0), mat="Footing", bevel_cm=0.75, segments=1)
    b.add_collider((0.0, 0.0, 74.0), (24.0, 24.0, 150.0))
    return b.finish(out_dir, lod_ratios=(1.0,))


def build_camp_gate_arch(out_dir: Path):
    """Grand Sawmill Camp Timber Entrance Gateway (560 cm clear wagon opening, twin stone-footed timber piers,
    overhead mortised lintel beam, hanging carved sawmill signboard & twin forged iron lantern arms!).
    """
    b = pg.AssetBuilder("SM_LM_CampGateArch", seed=4933, ground_mud_cm=55.0)
    gx = 292.0
    for sx in (-gx, gx):
        b.block(f"GA_Pier_{int(sx)}", (sx, 0.0, -8.0), (46.0, 46.0, 112.0), mat="Footing", bevel_cm=0.9, segments=1)
        b.block(f"GA_Post_{int(sx)}", (sx, 0.0, 224.0), (26.0, 26.0, 356.0), mat="DarkWood", bevel_cm=0.5, segments=1)
        b.block(f"GA_Cap_{int(sx)}", (sx, 0.0, 406.0), (33.0, 33.0, 9.0), mat="OiledOak", bevel_cm=0.45, segments=1)
        s_in = -1.0 if sx > 0 else 1.0
        b.beam(f"GA_Brace_{int(sx)}", (sx + s_in * 10.0, 0.0, 300.0), (sx + s_in * 88.0, 0.0, 376.0), 14.0, 14.0, mat="DarkWood")
        b.block(f"GA_Iron_{int(sx)}", (sx, 0.0, 384.0), (28.0, 28.0, 8.0), mat="ScaleIron", bevel_cm=0.14, segments=1)
        # Forged iron lantern bracket arm + diagonal scroll strut jutting toward road (+Y)
        b.block(f"GA_LArm_{int(sx)}", (sx, 26.0, 332.0), (4.2, 46.0, 4.2), mat="ScaleIron", bevel_cm=0.12, segments=1)
        b.beam(f"GA_LStrut_{int(sx)}", (sx, 12.0, 308.0), (sx, 38.0, 331.0), 2.8, 2.8, mat="ScaleIron")
        b.ring_torus(f"GA_LEye_{int(sx)}", (sx, 44.0, 327.0), 2.8, 0.85, mat="ScaleIron", axis="X", major_segs=14, minor_segs=6)
        b.add_collider((sx, 0.0, 190.0), (42.0, 42.0, 380.0))

    b.block("GA_Header", (0.0, 0.0, 388.0), (gx * 2.0 + 72.0, 24.0, 28.0), mat="DarkWood", bevel_cm=0.45, segments=1)
    b.block("GA_RoofL", (0.0, -22.0, 414.0), (gx * 2.0 + 88.0, 56.0, 9.0), mat="Slate", rot_deg=(20.0, 0.0, 0.0), bevel_cm=0.35, segments=1)
    b.block("GA_RoofR", (0.0, 22.0, 414.0), (gx * 2.0 + 88.0, 56.0, 9.0), mat="Slate", rot_deg=(-20.0, 0.0, 0.0), bevel_cm=0.35, segments=1)
    for cx in (-76.0, 76.0):
        b.block(f"GA_Chain_{int(cx)}", (cx, 0.0, 368.0), (3.5, 3.5, 22.0), mat="ScaleIron", bevel_cm=0.1, segments=1)
    b.block("GA_SignBoard", (0.0, 0.0, 336.0), (210.0, 7.5, 46.0), mat="OiledOak", bevel_cm=0.3, segments=1)
    b.block("GA_SignTrimT", (0.0, 0.0, 360.0), (218.0, 10.5, 5.5), mat="DarkWood", bevel_cm=0.2, segments=1)
    b.block("GA_SignTrimB", (0.0, 0.0, 312.0), (218.0, 10.5, 5.5), mat="DarkWood", bevel_cm=0.2, segments=1)
    for sx in (-100.0, 100.0):
        b.block(f"GA_SignEnd_{int(sx)}", (sx, 0.0, 336.0), (6.0, 9.8, 44.0), mat="DarkWood", bevel_cm=0.18, segments=1)
        for sz in (320.0, 352.0):
            b.block(f"GA_SignStrap_{int(sx)}_{int(sz)}", (sx * 0.92, 0.0, sz), (16.0, 10.6, 3.2), mat="ScaleIron", bevel_cm=0.1, segments=1)
    for sy_f in (-4.4, 4.4):
        b.block(f"GA_EmbSaw_{int(sy_f)}", (0.0, sy_f, 327.0), (108.0, 1.4, 7.0), mat="Steel", bevel_cm=0.1, segments=1)
        b.block(f"GA_EmbAx1_{int(sy_f)}", (0.0, sy_f, 341.0), (42.0, 1.6, 4.2), mat="ScaleIron", rot_deg=(0.0, 28.0, 0.0), bevel_cm=0.1, segments=1)
        b.block(f"GA_EmbAx2_{int(sy_f)}", (0.0, sy_f, 341.0), (42.0, 1.6, 4.2), mat="ScaleIron", rot_deg=(0.0, -28.0, 0.0), bevel_cm=0.1, segments=1)
    return b.finish(out_dir, lod_ratios=(1.0,))


def _build_bark_chip_scatter(out_dir: Path, name: str, seed: int, n_chips: int = 34, radius_cm: float = 165.0):
    """3A 3D Scattered Oak Bark Shards, Axe-Chopped Triangular Wood Chips & Fallen Twigs!
    Replaces flat elliptical mulch discs: real 3D parallax chips hugging mud softly (Z=-0.6..+2.8 cm)
    arranged in asymmetric irregular non-circular drifts to complement our rain-wet M_LM_WoodchipDecal!
    """
    b = pg.AssetBuilder(name, seed=seed, ground_mud_cm=8.0)
    rng = b.rng
    # 3 asymmetric drift lobes so scatter NEVER reads as a circle!
    lobes = [
        (rng.uniform(-45, 45), rng.uniform(-35, 35), rng.uniform(0.65, 1.15), rng.uniform(0, math.tau))
        for _ in range(3)
    ]
    for ci in range(n_chips):
        lx, ly, lsc, lang = lobes[ci % len(lobes)]
        # Exponential radial falloff -> dense pockets + stray distant chips!
        ang = lang + rng.gauss(0.0, 1.25)
        dist = min(radius_cm, 24.0 + abs(rng.gauss(0.0, 56.0)) * lsc)
        px = lx + dist * math.cos(ang)
        py = ly + dist * math.sin(ang)
        yaw = rng.uniform(0.0, 360.0)
        kind = ci % 4
        if kind == 0:
            # Small weathered curved oak bark shard (tapered, organic, nestled softly into mud — NO big pale rectangles!)
            w = rng.uniform(4.5, 9.5)
            l = rng.uniform(8.0, 16.0)
            curl = rng.uniform(0.9, 2.0)
            b.push_xform((px, py, rng.uniform(-0.5, 0.2)), (rng.uniform(-4, 4), rng.uniform(-5, 5), yaw))
            grid = []
            for ii in range(4):
                u = -0.5 + ii / 3.0
                taper = 1.0 - 0.55 * abs(u)  # organic pointed/tapered ends instead of square strip!
                row = []
                for jj in range(4):
                    v = -0.5 + jj / 3.0
                    z = curl * (1.0 - 3.2 * v * v) + 0.25 * math.sin(u * 5.0)
                    row.append((u * l, v * w * taper, z))
                grid.append(row)
            b.thick_grid(f"BC_Bark_{ci}", grid, thick_cm=rng.uniform(0.8, 1.5), mat="Bark")
            b.pop_xform()
        elif kind in (1, 2):
            # Small dark weathered axe-chopped triangular woodchip (Bark / DarkWood / Oak — zero bright pale bricks!)
            cl = rng.uniform(5.0, 11.5)
            cw = rng.uniform(2.8, 6.2)
            ct = rng.uniform(0.8, 1.8)
            mat_c = "DarkWood" if (ci % 3 == 0) else ("Bark" if ci % 2 == 0 else "Oak")
            b.push_xform((px, py, rng.uniform(-0.5, 0.2)), (rng.uniform(-7, 7), rng.uniform(-6, 6), yaw))
            verts = [
                (-cl * 0.5, -cw * 0.45, 0.0), (cl * 0.5, -cw * 0.12, 0.1),
                (cl * 0.42, cw * 0.20, 0.05), (-cl * 0.38, cw * 0.46, 0.0),
                (-cl * 0.44, -cw * 0.36, ct), (cl * 0.42, -cw * 0.08, ct * 0.25),
                (cl * 0.36, cw * 0.16, ct * 0.28), (-cl * 0.34, cw * 0.38, ct * 0.85),
            ]
            faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
            obj = b._new_mesh_obj(f"BC_Chip_{ci}", verts, faces, mat_c)
            b._bake_smooth(obj, 34.0)
            b._uv_box(obj, long_axis=0)
            b.pop_xform()
        else:
            # Crooked fallen branch splinter / bark twig
            tl = rng.uniform(22.0, 46.0)
            r0 = rng.uniform(0.9, 1.9)
            b.push_xform((px, py, rng.uniform(-0.2, 0.5)), (rng.uniform(-4, 4), rng.uniform(-4, 4), yaw))
            pts = [
                (-tl * 0.5, 0.0, r0 * 0.5),
                (-tl * 0.12, rng.uniform(-2.6, 2.6), r0 * 0.85),
                (tl * 0.22, rng.uniform(-2.6, 2.6), r0 * 0.72),
                (tl * 0.5, rng.uniform(-1.8, 1.8), r0 * 0.38),
            ]
            b.tube(f"BC_Twig_{ci}", pts, [r0, r0 * 0.9, r0 * 0.72, r0 * 0.48], mat="Bark", sides=7)
            b.pop_xform()
    return b.finish(out_dir, lod_ratios=(1.0,))


def build_bark_chip_scatter_a(out_dir: Path):
    return _build_bark_chip_scatter(out_dir, "SM_LM_BarkChipScatterA", seed=4951, n_chips=36, radius_cm=175.0)


def build_bark_chip_scatter_b(out_dir: Path):
    return _build_bark_chip_scatter(out_dir, "SM_LM_BarkChipScatterB", seed=4952, n_chips=32, radius_cm=155.0)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    builders = [
        build_warehouse,
        build_toolroom,
        build_bunkhouse,
        build_sawbuck_station,
        build_two_man_crosscut_saw,
        build_frame_pit_saw,
        build_workbench_saw_set,
        build_chopping_stump_a,
        build_chopping_stump_b,
        build_bunk_bed,
        build_timber_rack,
        build_camp_fence_panel,
        build_camp_fence_post,
        build_camp_gate_arch,
        build_bark_chip_scatter_a,
        build_bark_chip_scatter_b,
    ]
    manifest = []
    for fn in builders:
        clear_scene()
        info = fn(OUT_DIR)
        print(f"[ARCH-R49c] {info['name']:24s} | tris={info['lods'][0]['triangles']:6d} | size_cm={info['size_cm']} | col={len(info['colliders'])} | mats={info['materials']}", flush=True)
        manifest.append(info)
    (OUT_DIR / "arch-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"ARCH_R49C_OK: {len(manifest)} watertight 3A FBX assets exported to {OUT_DIR}")


if __name__ == "__main__":
    main()
