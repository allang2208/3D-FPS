"""Emit the MCP tool calls that build the textured PBR material library."""
from __future__ import annotations

import json
import os

TEX = r"D:\CyberpunkApartment\textures"

# key, tile-metres, has_emissive
SPECS = [
    ("concrete_floor", 3.0),
    ("concrete_wall", 2.5),
    ("concrete_ceiling", 3.0),
    ("plaster", 2.0),
    ("wood_floor", 2.0),
    ("wood_dark", 0.8),
    ("fabric", 0.35),
    ("leather", 0.5),
    ("metal_brushed", 0.6),
    ("metal_rust", 1.2),
    ("tile_bath", 1.2),
    ("carpet", 0.5),
    ("marble", 1.6),
    ("rug", 3.2),
    ("curtain", 1.4),
    ("brick", 1.6),
    ("holo_panel", 1.6),
    ("tech_panel", 0.9),
    ("circuit", 0.4),
    ("screen_ui", 1.0),
    ("asphalt_wet", 6.0),
    ("deck_wet", 2.0),
    ("diamond_plate", 0.5),
    ("neon_grille", 0.8),
    ("glass_smudge", 2.0),
    ("wall_graffiti", 2.5),
    ("facade_office", 8.0),
    ("facade_hab", 6.0),
    ("facade_mega", 12.0),
]


def p(name: str) -> str:
    fp = os.path.join(TEX, name)
    if not os.path.exists(fp):
        raise SystemExit(f"missing texture: {fp}")
    return fp


def main() -> None:
    calls = []
    for key, tile in SPECS:
        calls.append({
            "tool": "material_create_pbr_from_textures",
            "args": {
                "name": key,
                "baseColor": p(f"{key}_alb.png"),
                "normal": p(f"{key}_nrm.png"),
                "roughness": p(f"{key}_rgh.png"),
                "normalSpace": "OpenGL",
                "replaceExisting": True,
            },
        })
    out = os.path.join(os.path.dirname(__file__), "..", "_setup", "mat_calls.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(calls, fh, indent=1)
    print(f"wrote {len(calls)} calls -> {out}")
    print(json.dumps([[k, t] for k, t in SPECS]))


if __name__ == "__main__":
    main()