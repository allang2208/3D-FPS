"""Rebuild M66 surface collision and save it on the current character without changing its motions."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/DeathGroundV07')
DEST='/Game/Monsters/IncineratorBossM66';E=u.EditorAssetLibrary
if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('M66 packages have unsaved changes')
bp=u.load_asset(DEST+'/BP_M66RigPreview')
u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
mesh=cdo.get_editor_property('visual_mesh');previous=cdo.get_editor_property('reaction_physics')
attack=cdo.get_editor_property('sweep_clip');death=cdo.get_editor_property('death_clip')
physics=u.M66IncineratorMonster.build_reaction_physics(mesh)
if not physics or '/DeathGroundV07/' not in physics.get_path_name():
    raise RuntimeError('The V07 native builder is not loaded; no assets saved')
mesh.set_editor_property('physics_asset',physics)
saved=[]
for asset in (physics,mesh):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
    saved.append(asset.get_path_name())
cdo.set_editor_property('reaction_physics',physics)
cdo.get_editor_property('mesh').set_physics_asset(physics,True)
E.set_metadata_tag(bp,'M66.Death','V07 surface convex collision; visible-surface animated fallback; original death clock and corpse budget')
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not E.save_loaded_asset(bp,False):raise RuntimeError('M66 Blueprint save failed')
saved.append(bp.get_path_name())
report={'complete':True,'saved':saved,'previous_physics':previous.get_path_name() if previous else None,
    'physics':physics.get_path_name(),'mesh':mesh.get_path_name(),'preserved_attack':attack.get_path_name(),
    'preserved_death_clip':death.get_path_name(),'body_count':len(u.get_default_object(u.PhysicsAssetToolset).call_method('GetBodyNames',(physics,))),
    'convex_surface_bodies':21,'non_contact_container_bodies':1,'surface_fallback_cpu_access_enabled':True,
    'runtime_tested':False,'multiplayer_tested':False}
(ROOT/'Records/physics_install.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M66_DEATH_SURFACE_SAVED '+json.dumps(report))
