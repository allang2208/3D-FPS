import unreal as u, json
from pathlib import Path
assert Path(u.Paths.project_dir()).resolve()==Path('D:/FPS3D/FPSGAME').resolve()
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
print('world',str(ed.get_editor_world()),'game_world',str(ed.get_game_world()))
print('target exists',u.EditorAssetLibrary.does_asset_exist('/Game/Building/ArcaneWorkbenchV6_20261107/Meshes/SM_ArcaneWorkbench_V6'))
for name,keys in [('StaticMesh',['socket','bounds','material','description']),('StaticMeshEditorSubsystem',['collision','lod','nanite']),('Material',['refraction','transluc','shading']),('MaterialEditingLibrary',['compil','error','input']),('MeshDescription',['vertex','polygon'])]:
 c=getattr(u,name,None); print(name,[x for x in dir(c) if any(k in x.lower() for k in keys)])
print('socket doc',u.StaticMeshSocket.__doc__)
print('fbx doc',u.FbxStaticMeshImportData.__doc__)
print('refraction modes',dir(u.RefractionMode) if hasattr(u,'RefractionMode') else None)
print('translucency modes',dir(u.TranslucencyLightingMode))
print('dirty target packages',[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if 'ArcaneWorkbenchV6_' in p.get_path_name() or 'DA_VoxelBuildPalette' in p.get_path_name()])