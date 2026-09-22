import unreal as u
from pathlib import Path
out=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921/Spike20260922')
mesh=u.load_asset('/Game/Monsters/WitchRebuilt/SK_WitchRebuilt')
print('Exporters',[n for n in dir(u) if 'Exporter' in n and ('Text' in n or 'T3D' in n or 'Object' in n)])
for cloth in mesh.get_editor_property('mesh_clothing_assets'):
    for prop in ('LodData','UsedBoneNames'):
        try:print(prop,str(cloth.get_editor_property(prop))[:200])
        except Exception as e:print(str(e))
    task=u.AssetExportTask();task.object=cloth;task.filename=str(out/(cloth.get_name()+'.t3d'))
    task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.ObjectExporterT3D()
    print(cloth.get_name(),u.Exporter.run_asset_export_task(task),list(task.errors))
