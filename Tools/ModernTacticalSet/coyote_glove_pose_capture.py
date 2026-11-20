"""Capture the two equipped TS01 skeletal meshes used in the glove pose comparison."""
import ast
import hashlib
import json
from pathlib import Path

import unreal as u

P=Path(__file__).resolve().parents[2]
OUT=P/"SourceAssets/ModernTacticalSet20261113/CoyoteGlovesR2/Review/Read"
OUT.mkdir(parents=True,exist_ok=True)
G,Q,B,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_List
src=P/"Tools/ST6SleeveRepair/capture.py"
fns=[n for n in ast.parse(src.read_text("utf8")).body if isinstance(n,ast.FunctionDef) and n.name in ("xyz","read")]
exec(compile(ast.Module(fns,[]),str(src),"exec"))
config=json.loads((P/"Content/ColdSteelData/modular_outfits.json").read_bytes())
for rig in ("Super90","M16"):
    value=config["items"]["ue_modern_tactical_gloves"]["rig_meshes"][rig]
    if "/CoyoteGlovesR2/" not in value:
        raise RuntimeError(f"The fitted glove is not yet registered for {rig}")
    read(value,rig)
read(config["items"]["ue_modern_kevlar_vest"]["rig_meshes"]["Super90"],"Super90_Shirt")
