from pathlib import Path
import unreal as u
root=Path('D:/FPS3D/FPSGAME/SourceAssets/JasonFaceRepair20261003')
for name in ['MF_skin_bakedInputs','MF_skin_bentNormalsAO','MF_skin_animated','MF_skin_scalability']:
    obj=u.load_asset('/Game/AsianMale_Jason/Demo/MetaHumans/Common/Lookdev_UHM/Skin/Material_Functions/'+name)
    task=u.AssetExportTask();task.object=obj;task.filename=str(root/(name+'.t3d'))
    task.exporter=u.ObjectExporterT3D();task.automated=True;task.prompt=False;task.replace_identical=True
    print(name+' '+str(u.Exporter.run_asset_export_task(task)))
tex=u.load_asset('/Game/AsianMale_Jason/Texture/T_head_maskDown02')
task=u.AssetExportTask();task.object=tex;task.filename=str(root/'T_head_maskDown02.png')
task.exporter=u.TextureExporterPNG();task.automated=True;task.prompt=False;task.replace_identical=True
print('mask '+str(u.Exporter.run_asset_export_task(task)))
