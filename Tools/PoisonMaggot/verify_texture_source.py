import unreal
from pathlib import Path
dest=Path('D:/FPS3D/FPSGAME/Saved/PoisonMaggot')
tex=unreal.load_asset('/Game/Monsters/PoisonMaggot/Textures/T_PoisonMaggot_BaseColor')
t=unreal.AssetExportTask();t.object=tex;t.filename=str(dest/'ue_basecolor.png');t.exporter=unreal.TextureExporterPNG();t.automated=True;t.prompt=False;t.replace_identical=True
assert unreal.Exporter.run_asset_export_task(t)
unreal.log('MAGGOT_TEXTURE_EXPORTED')
