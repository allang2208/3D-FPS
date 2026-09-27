"""Refresh only the changed saved meshes for the post-import fit inspection."""
import ast, json
from pathlib import Path
import unreal as u
O=Path(__file__).parent/'FitInspection'
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights
tree=ast.parse((O.parent/'read_installed_fit.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'xyz','matrix','read'}],type_ignores=[]),'fit_geometry_read_helpers','exec'),globals())
for key in ['dw715_rubber_grip','dw715_target_wood_grip']:
    read(key,'/Game/Weapons/DanWesson715/GripBrake20260927/Meshes/SM_'+key)
u.log('DW715_REVISED_GRIP_SNAPSHOTS_SAVED')
