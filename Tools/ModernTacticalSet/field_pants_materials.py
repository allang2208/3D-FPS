"""TS01 field trousers fabric palette and shared Blender material factory."""
from pathlib import Path

from coyote_glove_materials import create as textile_materials

ROOT=Path(__file__).resolve().parents[2]/"SourceAssets/ModernTacticalSet20261113/FieldTrousersR2"
TILE_CM=8.
# sRGB yarn colour, roughness, cloth sheen and square texture resolution.
SURFACES={
    "Ripstop":       ((134,113,88), .83,.17,2048),
    "Stretch":       ((102,86,69),  .86,.21,2048),
    "Reinforcement": ((123,101,78), .84,.15,2048),
    "Webbing":       ((114,95,73),  .80,.18,1024),
    "Thread":        ((150,126,96), .76,.22,512),
    "Hardware":      ((65,60,48),   .52,.00,512),
}


def create():
    return textile_materials(SURFACES,ROOT,"FT_",TILE_CM)
