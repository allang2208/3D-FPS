from pathlib import Path
import unreal as u
folder=Path('D:/FPS3D/FPSGAME/SourceAssets/DragonBreath20261013/JetFixR4')
texture=u.load_asset('/Game/_SplineVFX/_GenericSource/Texture/T_Vfx_Stamp_FireFlame_88')
task=u.AssetExportTask();task.object=texture;task.filename=str(folder/'fire-flame-source.tga');task.automated=True;task.prompt=False;task.replace_identical=True
assert u.Exporter.run_asset_export_task(task)
print('DRAGON_FLAME_SOURCE_EXPORTED '+str(folder/'fire-flame-source.tga'))
