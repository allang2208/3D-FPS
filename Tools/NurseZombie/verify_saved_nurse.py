import unreal,json
from pathlib import Path
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert level.load_level('/Game/GameMaps/L_Normandy_FPS_Test')
ns=[a for a in actors.get_all_level_actors() if isinstance(a,unreal.NurseZombie)]
assert len(ns)==2
for a in actors.get_all_level_actors():
    if isinstance(a,unreal.PlayerStart): unreal.log('NURSE_PLAYERSTART '+str(a.get_actor_transform())+' rot='+str(a.get_actor_rotation()))
unreal.log('NURSE_ROTATOR '+str(unreal.Rotator(0,180,0)))
report=[]
for a in ns:
    for key in ['idle_clip','walk_clip','attack_clip','visual_mesh']:
        assert a.get_editor_property(key) is not None
    data={k:str(a.get_editor_property(k)) for k in ['idle_clip','walk_clip','attack_clip','visual_mesh','walk_speed']}
    data['location']=str(a.get_actor_location());data['mesh']=str(a.mesh.skeletal_mesh_asset)
    data['materials']=[str(a.mesh.get_material(i)) for i in range(a.mesh.get_num_materials())]
    report.append(data)
Path(unreal.Paths.project_saved_dir()+'/NurseZombie/saved-readback.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('NURSE_READBACK '+json.dumps(report))
bp=unreal.load_asset('/Game/Monsters/NurseZombie/BP_NurseZombie')
cdo=unreal.get_default_object(bp.generated_class())
for key in ['idle_clip','walk_clip','attack_clip','visual_mesh']:
    assert cdo.get_editor_property(key) is not None, key
unreal.log('NURSE_SAVED_READBACK_OK actors=2 blueprint_defaults=valid')
