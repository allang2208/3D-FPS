"""Switch only Saiga runtime references after the refined packages are saved."""
import json,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KRefine20261017'
receipt=json.loads((O/'Receipts/assets.json').read_text(encoding='utf-8-sig'))
if not receipt['complete']:raise RuntimeError('Refined packages are not yet saved')
def write(path,text):
 p=P/path;backup=O/'SourceBefore'/path;backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():shutil.copy2(p,backup)
 p.write_text(text,encoding='utf-8')
replacements={
 'Source/FPSGAME/Weapons/Saiga12KWeaponAssets.h':('Saiga12K/Integrated20261017/SK_Saiga12K_Manny','Saiga12K/Refined20261017/SK_Saiga12K_Manny'),
 'Source/FPSGAME/Weapons/Saiga12KAttachments.h':('Saiga12K/Common20261017/Meshes/SM_Saiga12K_','Saiga12K/Refined20261017/Attachments/SM_Saiga12K_'),
 'Source/FPSGAME/Weapons/TacticalDeviceVariants.h':('Saiga12K/Common20261017/Meshes/SM_Saiga12K_','Saiga12K/Refined20261017/Attachments/SM_Saiga12K_'),
 'Source/FPSGAME/Weapons/FPSWeaponFXComponent.cpp':('Saiga12K/Common20261017/Meshes/SM_Saiga12K_','Saiga12K/Refined20261017/Attachments/SM_Saiga12K_')}
for path,(before,after) in replacements.items():
 text=(P/path).read_text(encoding='utf-8-sig')
 if before in text:write(path,text.replace(before,after))
 elif after not in text:raise RuntimeError('Saiga runtime reference changed '+path)
path='Content/ColdSteelData/modular_outfits.json';data=json.loads((P/path).read_text(encoding='utf-8-sig'))
old='/Game/Weapons/Saiga12K/Integrated20261017/SK_Saiga12K_Manny.SK_Saiga12K_Manny'
new='/Game/Weapons/Saiga12K/Refined20261017/SK_Saiga12K_Manny.SK_Saiga12K_Manny'
data['profiles'][new]=data['profiles'][old]
write(path,json.dumps(data,ensure_ascii=False,indent=2)+'\n')
(O/'Receipts/activation.json').write_text(json.dumps({'mesh':new,'attachment_root':'/Game/Weapons/Saiga12K/Refined20261017/Attachments','source':list(replacements),'outfit_profile_copied':True,'automatic_fire_and_factory_8_round_magazine_preserved':True,'runtime_tested':False},indent=2),encoding='utf-8')
print('SAIGA_REFINED_REFERENCES_SAVED')
