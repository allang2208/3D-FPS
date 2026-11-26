"""Read original demo wall placements in a background commandlet; never save the demo."""
import json
from pathlib import Path
import unreal as u

out=Path('D:/FPS3D/FPSGAME/SourceAssets/TemperateHillsVillage/DemoRevision20261114')
out.mkdir(parents=True,exist_ok=True)
report={'maps':{},'meshes':{}}
def xyz(v): return [round(v.x,4),round(v.y,4),round(v.z,4)]
for level in ('SL_Demonstration_StaticMeshes','ML_Demonstration'):
    path='/Game/UnrealNormandy/Levels/'+level
    world=u.EditorLoadingAndSavingUtils.load_map(path)
    if not world: raise RuntimeError(path)
    actors=u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
    if not any(a.get_components_by_class(u.StaticMeshComponent) for a in actors):
        desc=u.WorldPartitionBlueprintLibrary.get_actor_descs()
        if desc:
            u.WorldPartitionBlueprintLibrary.load_actors([d.guid for d in desc])
            actors=u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
    records=[]
    for actor in actors:
        for comp in actor.get_components_by_class(u.StaticMeshComponent):
            mesh=comp.static_mesh
            if not mesh or 'StoneWall' not in mesh.get_name(): continue
            name=mesh.get_name()
            if name not in report['meshes']:
                box=mesh.get_bounding_box()
                report['meshes'][name]={'path':mesh.get_path_name(),'bounds':[xyz(box.min),xyz(box.max)]}
            transforms=([comp.get_instance_transform(i,True) for i in range(comp.get_instance_count())]
                        if isinstance(comp,u.InstancedStaticMeshComponent) else [comp.get_world_transform()])
            for transform in transforms:
                rotation=transform.rotation.rotator()
                records.append({'label':actor.get_actor_label(),'mesh':name,'pos':xyz(transform.translation),
                    'rot':[rotation.pitch,rotation.yaw,rotation.roll],'scale':xyz(transform.scale3d),
                    'materials':[m.get_path_name() if m else None for m in comp.get_editor_property('override_materials')]})
    report['maps'][level]={'actors':len(actors),'walls':records}
    print('DEMO_WALLS',level,len(actors),len(records))
for asset in u.EditorAssetLibrary.list_assets('/Game/UnrealNormandy/StaticMeshes',False,False):
    if 'StoneWall' not in asset: continue
    mesh=u.load_asset(asset)
    if not isinstance(mesh,u.StaticMesh): continue
    box=mesh.get_bounding_box()
    report['meshes'][mesh.get_name()]={'path':mesh.get_path_name(),'bounds':[xyz(box.min),xyz(box.max)]}
(out/'demo-walls.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
