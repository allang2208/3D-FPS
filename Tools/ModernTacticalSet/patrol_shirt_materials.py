"""Shared studio and Unreal PBR palette of the TS01 coyote combat shirt."""
from pathlib import Path

from coyote_glove_materials import create as fabric_materials

ROOT = Path(__file__).resolve().parents[2] / "SourceAssets/ModernTacticalSet20261113/PatrolShirtR2"
TILE_CM = 8.
# Linear tile length is shared by the native body, viewmodel and item UVs.
# Colours are sRGB reflectance, followed by roughness, sheen and texture size.
SURFACES = {
    "Jersey":        ((115,  92, 64), .85, .20, 2048),
    "Ripstop":       ((130, 107, 74), .82, .14, 2048),
    "Reinforcement": ((126, 102, 69), .83, .15, 2048),
    "Loop":          ((110,  91, 64), .91, .24, 1024),
    "Binding":       ((116,  95, 65), .80, .12, 1024),
    "Thread":        ((145, 122, 85), .78, .16, 512),
    "Hardware":      (( 78,  68, 49), .48, .00, 512),
}


def create():
    return fabric_materials(SURFACES, ROOT, "PS_", TILE_CM)
