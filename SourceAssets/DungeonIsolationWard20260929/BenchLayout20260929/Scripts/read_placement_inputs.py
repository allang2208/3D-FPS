"""Read the current source mesh and editor state needed for the placement batch."""
import json
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1]
mesh=u.load_asset('/Game/Props/HospitalWaitingBench20260929/SM_Hospital_Waiting_Bench')
if not mesh:raise RuntimeError('Imported waiting bench is missing')
bb=mesh.get_bounding_box()
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=editor.get_editor_world()
body=mesh.get_editor_property('body_setup')
agg=body.get_editor_property('agg_geom') if body else None
result=dict(mesh=mesh.get_path_name(),bounds_cm=dict(min=[bb.min.x,bb.min.y,bb.min.z],max=[bb.max.x,bb.max.y,bb.max.z]),
    collision_trace_flag=str(body.get_editor_property('collision_trace_flag')) if body else None,
    convex_hulls=len(agg.get_editor_property('convex_elems')) if agg else 0,
    box_hulls=len(agg.get_editor_property('box_elems')) if agg else 0,
    editor_world=world.get_path_name() if world else None,playing=bool(editor.get_game_world()),
    dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
    dirty_bench_assets=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
                        if 'HospitalWaitingBench' in p.get_name()])
(ROOT/'Receipts/placement-inputs.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('BENCH_PLACEMENT_INPUTS',json.dumps(result),flush=True)
