import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[4]
E=u.EditorAssetLibrary
src='/Game/UnrealNormandy/StaticMeshes/SM_H_OldWall_Window_00A'
dst='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/WindowR7/Meshes/SM_SmithWindowWall_R7'
original=u.load_asset(src);body=original.get_editor_property('body_setup');agg=body.get_editor_property('agg_geom')
report={'original_trace_flag':str(body.get_editor_property('collision_trace_flag')),'original_boxes':len(agg.get_editor_property('box_elems')),'original_convex':len(agg.get_editor_property('convex_elems'))}
mesh=u.load_asset(dst) if E.does_asset_exist(dst) else E.duplicate_asset(src,dst)
if not mesh:raise RuntimeError('Window-wall collision variant')
mesh.modify();body=mesh.get_editor_property('body_setup');body.modify()
body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
if not E.save_loaded_asset(mesh,False):raise RuntimeError('Save window wall')
report.update(saved_path=dst,trace_flag='USE_COMPLEX_AS_SIMPLE',scope='three fitted upper shop windows only')
(ROOT/'SourceAssets/HillsVillageBlacksmith20261117/WindowR7/wall-collision.json').write_text(json.dumps(report,indent=2))
