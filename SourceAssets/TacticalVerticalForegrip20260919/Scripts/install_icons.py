"""Install requested real-model renders for the new option only."""
import json,shutil
from pathlib import Path
import unreal as u
O=Path('D:/FPS3D/FPSGAME/SourceAssets/TacticalVerticalForegrip20260919/Integration')
C=Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/AttachmentIcons20260913')
D='/Game/ColdSteelData/AttachmentIcons20260913'
report={}
for gun,weapon in [('M4','ue_m4a1'),('AKM','ue_akm'),('QBZ191','ue_qbz191'),('ASH12','ue_ash12')]:
 src=O/'Preview'/gun/'underbarrel_tactical_vertical_foregrip.png'
 name=weapon+'_underbarrel_tactical_vertical_foregrip';dst=C/(name+'.png')
 if dst.exists() or u.EditorAssetLibrary.does_asset_exist(D+'/'+name):raise RuntimeError('This new icon was already installed: '+name)
 shutil.copy2(src,dst)
 t=u.AssetImportTask();t.filename=str(dst);t.destination_path=D;t.destination_name=name;t.automated=True;t.save=False
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);tex=u.load_asset(D+'/'+name)
 if not tex:raise RuntimeError('Missing imported icon '+name)
 tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI;tex.srgb=True
 tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
 if not u.EditorAssetLibrary.save_loaded_asset(tex,False):raise RuntimeError('Icon save failed '+name)
 report[gun]={'png':str(dst),'texture':tex.get_path_name(),'render_source':str(src),'saved':True}
 (O/'icon_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('TACTICAL_GRIP_ICONS_INSTALLED '+','.join(report))
