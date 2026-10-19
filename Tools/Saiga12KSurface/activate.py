"""Activate only the saved and independently read-back Saiga revision."""
import json,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KSurface20261018'
r=json.loads((O/'Receipts/assets.json').read_text());audit=json.loads((O/'Reports/saved-assets-check.json').read_text())
if not r['complete'] or not audit['passed']:raise RuntimeError('Saved revision has unresolved issues')
def write(path,text):
 p=P/path;before=O/'SourceBefore'/path;before.parent.mkdir(parents=True,exist_ok=True)
 if not before.exists():shutil.copy2(p,before)
 p.write_text(text,encoding='utf-8')
changes={
 'Source/FPSGAME/Weapons/Saiga12KWeaponAssets.h':('Saiga12K/Refined20261017/SK_Saiga12K_Manny','Saiga12K/SurfaceRebuild20261018/SK_Saiga12K_Manny'),
 'Source/FPSGAME/Weapons/Saiga12KAttachments.h':('Saiga12K/Refined20261017/Attachments/','Saiga12K/SurfaceRebuild20261018/Attachments/'),
 'Source/FPSGAME/Weapons/TacticalDeviceVariants.h':('Saiga12K/Refined20261017/Attachments/','Saiga12K/SurfaceRebuild20261018/Attachments/'),
 'Source/FPSGAME/Weapons/FPSWeaponFXComponent.cpp':('Saiga12K/Refined20261017/Attachments/','Saiga12K/SurfaceRebuild20261018/Attachments/'),
 'Source/FPSGAME/Weapons/Saiga12KMagazineAssets.h':('Saiga12K/ExtendedMagazine20261017/SM_Saiga12K_Ext12','Saiga12K/SurfaceRebuild20261018/SM_Saiga12K_Ext12')}
for path,(before,after) in changes.items():
 text=(P/path).read_text(encoding='utf-8-sig')
 if before in text:write(path,text.replace(before,after))
 elif after not in text:raise RuntimeError('Runtime reference changed '+path)
path='Content/ColdSteelData/modular_outfits.json';d=json.loads((P/path).read_text(encoding='utf-8-sig'));old='/Game/Weapons/Saiga12K/Refined20261017/SK_Saiga12K_Manny.SK_Saiga12K_Manny';new='/Game/Weapons/Saiga12K/SurfaceRebuild20261018/SK_Saiga12K_Manny.SK_Saiga12K_Manny';d['profiles'][new]=d['profiles'][old];write(path,json.dumps(d,ensure_ascii=False,indent=2)+'\n')
(O/'Receipts/activation.json').write_text(json.dumps({'mesh':new,'source_files':list(changes),'outfit_profile_copied':True,'gameplay_numbers_unchanged':True,'runtime_tested':False},indent=2),encoding='utf-8');print('SAIGA_SURFACE_REFERENCES_UPDATED')
