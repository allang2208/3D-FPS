"""Read saved dependencies and directly placed editor instances for bench revisions."""
import unreal as u,json,datetime
from pathlib import Path
registry=u.AssetRegistryHelpers.get_asset_registry()
versions=['GunWorkbench20260927','GunWorkbench20260928','GunWorkbenchPolish20260928',
    'GunWorkbenchLampRestore20260928','GunWorkbenchCleared20260928','GunWorkbenchLibraryTools20260928']
result={'references':{},'editor_instances':[]}
options=u.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True)
for version in versions:
    package='/Game/Building/'+version+'/SM_GunWorkbench'
    result['references'][package]=[str(p) for p in registry.get_referencers(package,options)]
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
result['editor_world']=world.get_path_name() if world else None
for actor in (u.GameplayStatics.get_all_actors_of_class(world,u.Actor) if world else []):
    for component in actor.get_components_by_class(u.StaticMeshComponent):
        mesh=component.static_mesh
        if mesh and 'GunWorkbench' in mesh.get_path_name():
            result['editor_instances'].append({'actor':actor.get_path_name(),'mesh':mesh.get_path_name(),
                'component':component.get_path_name(),'transform':str(component.get_world_transform())})
root=Path('D:/FPS3D/FPSGAME/SourceAssets/GunWorkbenchVisibleFix20260928')
filename='references-'+datetime.datetime.now().strftime('%H%M%S')+'.json'
(root/filename).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
