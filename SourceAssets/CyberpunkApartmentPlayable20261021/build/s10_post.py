"""s10 - compositor (Blender 5.x socket-based API): bloom, streaks, vignette, grade."""
from __future__ import annotations

import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cy_lib as cy  # noqa: E402


def enum_in(node, sock, cands):
    if sock not in node.inputs:
        return None
    for c in cands:
        try:
            node.inputs[sock].default_value = c
            return c
        except Exception:
            continue
    return None


def num(node, sock, val):
    if sock in node.inputs:
        try:
            node.inputs[sock].default_value = val
            return True
        except Exception:
            return False
    return False


def build() -> dict:
    scn = bpy.context.scene
    rep = {}
    tree = bpy.data.node_groups.get("CP_Comp") or bpy.data.node_groups.new(
        "CP_Comp", "CompositorNodeTree")
    tree.nodes.clear()
    if not tree.interface.items_tree:
        tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")

    rl = tree.nodes.new("CompositorNodeRLayers")
    rl.location = (-1000, 200)

    # ---- soft bloom
    g1 = tree.nodes.new("CompositorNodeGlare")
    g1.location = (-760, 200)
    rep["bloom_type"] = enum_in(g1, "Type", ("Fog Glow", "FOG_GLOW", "Bloom", "BLOOM"))
    enum_in(g1, "Quality", ("High", "HIGH"))
    num(g1, "Threshold", 0.80)
    num(g1, "Size", 0.72)
    num(g1, "Strength", 0.42)
    num(g1, "Saturation", 1.15)
    num(g1, "Smoothness", 0.25)
    tree.links.new(rl.outputs["Image"], g1.inputs["Image"])

    # ---- tight anamorphic streaks on the hottest cores
    g2 = tree.nodes.new("CompositorNodeGlare")
    g2.location = (-540, 200)
    rep["streak_type"] = enum_in(g2, "Type", ("Streaks", "STREAKS"))
    enum_in(g2, "Quality", ("Medium", "MEDIUM"))
    num(g2, "Threshold", 1.5)
    num(g2, "Streaks", 2)
    num(g2, "Streaks Angle", 0.0)
    num(g2, "Fade", 0.90)
    num(g2, "Strength", 0.10)
    tree.links.new(g1.outputs["Image"], g2.inputs["Image"])

    # ---- grade
    cb = tree.nodes.new("CompositorNodeColorBalance")
    cb.location = (-320, 200)
    rep["cb_inputs"] = [i.name for i in cb.inputs]
    if "Lift" in cb.inputs:
        def set_col(first, second, val):
            for idx in (first, second):
                try:
                    cb.inputs[idx].default_value = val
                    return True
                except Exception:
                    continue
            return False
        ok = (set_col(3, 4, (1.01, 1.00, 1.02, 1.0))
              and set_col(5, 6, (1.0, 1.0, 1.0, 1.0))
              and set_col(7, 8, (1.05, 1.0, 0.97, 1.0)))
        rep["grade"] = ok
    tree.links.new(g2.outputs["Image"], cb.inputs["Image"])

    # ---- vignette
    mask = tree.nodes.new("CompositorNodeEllipseMask")
    mask.location = (-540, -260)
    num(mask, "Width", 0.95)
    num(mask, "Height", 0.92)
    blur = tree.nodes.new("CompositorNodeBlur")
    blur.location = (-330, -260)
    enum_in(blur, "Filter Type", ("Gauss", "GAUSS"))
    if "Size" in blur.inputs:
        try:
            blur.inputs["Size"].default_value = (220, 220)
        except Exception:
            num(blur, "Size", 220)
    tree.links.new(mask.outputs["Mask"], blur.inputs["Image"])

    mix = tree.nodes.new("ShaderNodeMix")
    mix.location = (0, 0)
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 0.35
    tree.links.new(cb.outputs["Image"], mix.inputs[6])
    tree.links.new(blur.outputs["Image"], mix.inputs[7])

    out = tree.nodes.new("NodeGroupOutput")
    out.location = (260, 200)
    tree.links.new(mix.outputs[2], out.inputs[0])

    scn.compositing_node_group = tree
    try:
        scn.render.use_compositing = True
    except Exception:
        pass

    # ---- final render settings
    scn.render.engine = "CYCLES"
    scn.cycles.device = "GPU"
    scn.cycles.samples = 220
    scn.cycles.use_denoising = True
    scn.cycles.use_adaptive_sampling = True
    scn.cycles.adaptive_threshold = 0.02
    scn.render.resolution_x = 1600
    scn.render.resolution_y = 900
    scn.render.resolution_percentage = 100
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_depth = "8"
    scn.render.film_transparent = False
    scn.view_settings.view_transform = "AgX"
    for cand in ("AgX - Punchy", "Punchy", "AgX - Medium High Contrast"):
        try:
            scn.view_settings.look = cand
            rep["look"] = scn.view_settings.look
            break
        except TypeError:
            continue
    scn.view_settings.exposure = 0.45
    rep.update({"nodes": len(tree.nodes), "exposure": 0.35, "samples": 220})
    return rep


_result = build()
print(_result, flush=True)