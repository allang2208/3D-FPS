"""Reuse the maintained importer for three privately named correction assets."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT.parent/'RefineV2/Scripts/import_assets.py').read_text('utf8')
source=source.replace("BASE='/Game/Dungeons/StationWorkshop20261003/RefineV2'",
    "BASE='/Game/Dungeons/StationWorkshop20261003/RefineV3'")
source=source.replace("build=sub.get_lod_build_settings(mesh,0)",
    "\n        if item.get('complex_collision'):mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)\n        build=sub.get_lod_build_settings(mesh,0)")
sys.modules.pop('materials',None)
exec(compile(source,'workshop_v3_asset_importer','exec'))
