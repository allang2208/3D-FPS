"""Author the missing simple box on the hub's shared upper handrail asset."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
ROOT=Path(__file__).parent;PROJECT=ROOT.parents[2]
PATH='/Game/Props/RomanColumn20260915/SM_RomanRail_200'
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('End PIE before rebuilding the shared handrail collision')
if any(p.get_path_name()==PATH for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved handrail asset changes')
mesh=u.load_asset(PATH)
if not mesh:raise RuntimeError('Missing upper handrail mesh')
setup=mesh.get_editor_property('body_setup');agg=setup.get_editor_property('agg_geom')
count=sum(len(agg.get_editor_property(k)) for k in ['box_elems','convex_elems','sphere_elems','sphyl_elems'])
report={'mesh':PATH,'existing_simple_shapes':count,'changed':False,'runtime_tested':False}
if count==0:
    src=PROJECT/'Content/Props/RomanColumn20260915/SM_RomanRail_200.uasset'
    backup=PROJECT/'trash/godspace-rail-collision-20260927/Before/Content/Props/RomanColumn20260915/SM_RomanRail_200.uasset'
    if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,backup)
    report['backup']={'path':str(backup),'sha256':hashlib.sha256(backup.read_bytes()).hexdigest()}
    # One box fitted to this top beam only. The space below the beam stays open.
    setup.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    index=u.get_editor_subsystem(u.StaticMeshEditorSubsystem).add_simple_collisions(mesh,u.ScriptCollisionShapeType.BOX)
    if index<0:raise RuntimeError('Upper handrail box could not be authored')
    if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Upper handrail collision save failed')
    report.update(changed=True,added_box_index=index,box_size_cm=[200,40,40],box_center_cm=[0,0,20])
(ROOT/'Receipts/rail-collision-saved.json').write_text(json.dumps(report,indent=2))
print('HANDRAIL_COLLISION_SAVED '+json.dumps(report))
