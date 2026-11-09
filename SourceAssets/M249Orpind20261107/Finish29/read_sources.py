import unreal as u,json
from pathlib import Path
r=Path(__file__).resolve().parent
report={}
for name,path in {
    'metallic':'/Game/Weapons/M4/SurfaceStandard20261001/Textures/T_M4_R01_Magazine_Light_Metallic',
    'colour':'/Game/Weapons/M4InfimaV3/Magazine_Light_BaseColor',
    'roughness':'/Game/Weapons/M4/SurfaceStandard20261001/Textures/T_M4_R01_Magazine_Light_Roughness',
}.items():
    a=u.load_asset(path);t=u.AssetExportTask();t.object=a;t.filename=str(r/(name+'.tga'));t.automated=True;t.prompt=False;t.exporter=u.TextureExporterTGA()
    if not u.Exporter.run_asset_export_task(t):raise RuntimeError('Source export '+path)
    report[name]=t.filename
s=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for name in ('SM_m249_side_mag_30','SM_m249_side_mag_45'):
    m=u.load_asset('/Game/Weapons/M249/SideMagazine20261108/Meshes/'+name)
    report[name]={'uv_channels':s.get_num_uv_channels(m,0)}
(r/'sources.json').write_text(json.dumps(report,indent=2))
print('M249_FINISH29_SOURCES',report,flush=True)
