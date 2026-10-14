import json
from pathlib import Path
import unreal as u
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/DragonBreath20261013/RealisticJetV5');OUT.mkdir(parents=True,exist_ok=True)
src='/Game/Realistic_Starter_VFX_Pack_Vol2'
out={'game_world':str(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()),'source':src+'/Particles/Fire/P_flamethrower','textures':{}}
for name in ['T_Fire_F','T_Fire_B']:
    t=u.load_asset(src+'/Textures/'+name)
    task=u.AssetExportTask();task.object=t;task.filename=str(OUT/(name+'.tga'));task.automated=True;task.prompt=False;task.replace_identical=True
    assert u.Exporter.run_asset_export_task(task)
    out['textures'][name]={'path':t.get_path_name(),'srgb':t.get_editor_property('srgb')}
for name in ['M_Fire_C','M_Spark_A']:
    m=u.load_asset(src+'/Materials/'+name)
    task=u.AssetExportTask();task.object=m;task.filename=str(OUT/(name+'.t3d'));task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.ObjectExporterT3D()
    assert u.Exporter.run_asset_export_task(task)
(OUT/'source.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('DRAGON_NATIVE_SOURCE '+json.dumps(out))
