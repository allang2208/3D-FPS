"""Measured-scale surface palette for the TS01 coyote high boot."""
from pathlib import Path

from coyote_glove_materials import create as textile_materials


ROOT = Path(__file__).resolve().parents[2] / "SourceAssets/ModernTacticalSet20261113/RidgeBootsR2"
TILE_CM = 4.0
# Base sRGB, mean roughness, fibre sheen, tile size in pixels.
SURFACES = {
    "Suede":    ((159, 128, 98), .88, .22, 2048),
    "Textile":  ((146, 116, 90), .82, .14, 2048),
    "Frame":    ((133, 113, 89), .63, .00, 1024),
    "Outsole":  ((148, 136, 118), .75, .00, 1024),
    "Lace":     ((161, 136, 103), .82, .12, 1024),
    "Lining":   ((102, 85, 66), .89, .19, 1024),
    "Hardware": ((161, 145, 124), .43, .00, 512),
    "Thread":   ((172, 144, 112), .79, .12, 512),
}


def create():
    return textile_materials(SURFACES, ROOT, "RB_", TILE_CM)
