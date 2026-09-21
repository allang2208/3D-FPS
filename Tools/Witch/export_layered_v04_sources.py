import unreal as u
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchMeshy20260919/Authoring/LayeredV04/Sources')
root.mkdir(parents=True,exist_ok=True)
mesh=u.load_asset('/Game/NiagaraExamples/Gallery/SkeletalMesh/Mannequins/Meshes/SKM_Quinn_Simple')
if not mesh:raise RuntimeError('Missing local Quinn body')
t=u.AssetExportTask();t.object=mesh;t.filename=str(root/'SKM_Quinn_Simple.fbx')
t.automated=True;t.prompt=False;t.replace_identical=True;t.exporter=u.SkeletalMeshExporterFBX();t.options=u.FbxExportOption()
if not u.Exporter.run_asset_export_task(t):raise RuntimeError('Body export failed')
for name in ['T_MaidenZombieBody3BaseColor','T_MaidenZombieBody3Normal','T_MaidenZombieBody3ORM']:
    path='/Game/ZombieFemale/Asset/Textures/Body/Zombie/'+name
    asset=u.load_asset(path)
    if not asset:continue
    task=u.AssetExportTask();task.object=asset;task.filename=str(root/(name+'.tga'))
    task.automated=True;task.prompt=False;task.replace_identical=True
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Texture export failed: '+name)
print('WITCH_V04_SOURCES_EXPORTED '+str(root))
