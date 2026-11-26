"""Update the 154 boundary-wall instances only, saving the existing village map."""
import json
from pathlib import Path
import unreal as u

root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
source=root/'SourceAssets/TemperateHillsVillage'
batch=source/'WallSupport20261114'
old=json.loads((batch/'Before/SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf-8'))
new=json.loads((source/'layout.json').read_text(encoding='utf-8'))
before=[i for w in old['yard_walls'] for i in w['native_instances']]
after=[i for w in new['yard_walls'] for i in w['native_instances']]
if len(before)!=154 or len(after)!=len(before):raise RuntimeError('Unexpected boundary-wall inventory')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world():raise RuntimeError('Active game: preserve editor state')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Unsaved maps: preserve editor state')
previous=editor.get_editor_world().get_path_name().split('.')[0]
camera=editor.get_level_viewport_camera_info()
level='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
world=u.EditorLoadingAndSavingUtils.load_map(level)
if not world:raise RuntimeError('Cannot load village')

instances=[]
for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    for comp in actor.get_components_by_class(u.InstancedStaticMeshComponent):
        mesh=comp.static_mesh
        if not mesh or 'StoneWall' not in mesh.get_name():continue
        for index in range(comp.get_instance_count()):
            instances.append((actor,comp,index,comp.get_instance_transform(index,True),mesh.get_path_name()))
edits=[]
used=set()
for original,replacement in zip(before,after):
    candidates=[]
    for key,row in enumerate(instances):
        actor,comp,index,t,path=row
        if path!=original['mesh']:continue
        if (t.translation-u.Vector(*original['pos'])).length()>.05:continue
        if (t.scale3d-u.Vector(*original['scale'])).length()>.001:continue
        candidates.append((key,row))
    if len(candidates)!=1:raise RuntimeError('Wall match is not unique: '+str(original))
    key,row=candidates[0]
    if key in used:raise RuntimeError('Duplicate instance match')
    used.add(key)
    pitch,yaw,roll=replacement['rot']
    transform=u.Transform(location=replacement['pos'],rotation=u.Rotator(pitch=pitch,yaw=yaw,roll=roll),scale=replacement['scale'])
    edits.append((row,transform))

# Matching completes before any mutation. House masonry shares these meshes and stays untouched.
for (actor,comp,index,old_transform,path),transform in edits:
    actor.modify();comp.modify()
    if not comp.update_instance_transform(index,transform,True,True,True):
        raise RuntimeError('Instance update failed: '+actor.get_actor_label())
if not u.EditorLoadingAndSavingUtils.save_map(world,level):raise RuntimeError('Village map save failed')
rows=[]
for key,(actor,comp,index,old_transform,path) in enumerate(instances):
    t=comp.get_instance_transform(index,True);r=t.rotation.rotator()
    if key not in used:
        if ((t.translation-old_transform.translation).length()>.001 or
                (t.scale3d-old_transform.scale3d).length()>.001 or
                max(abs(getattr(t.rotation,a)-getattr(old_transform.rotation,a)) for a in ('x','y','z','w'))>.00001):
            raise RuntimeError('Unowned house masonry changed')
    rows.append(dict(actor=actor.get_actor_label(),index=index,mesh=path,pos=[t.translation.x,t.translation.y,t.translation.z],
        rot=[r.pitch,r.yaw,r.roll],scale=[t.scale3d.x,t.scale3d.y,t.scale3d.z],boundary_wall=key in used))
report=dict(level=level,saved=True,boundary_walls_updated=len(edits),house_masonry_preserved=len(instances)-len(edits),
    source_rule_version=new['wall_support_version'],gameplay_tested=False,instances=rows)
(batch/'saved.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if previous!=level:
    if not u.EditorLoadingAndSavingUtils.load_map(previous):raise RuntimeError('Restore map failed')
    if camera:editor.set_level_viewport_camera_info(*camera)
print(json.dumps({k:v for k,v in report.items() if k!='instances'}))
