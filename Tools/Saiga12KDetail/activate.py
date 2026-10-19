"""Activate the saved detail revision without changing weapon mechanics."""
import json,shutil,subprocess
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KDetail20261018'
r=json.loads((O/'Receipts/assets.json').read_text());a=json.loads((O/'Reports/saved-assets-check.json').read_text())
if not r['complete'] or not a['passed']:raise RuntimeError('Saved revision has unresolved issues')
subprocess.run(['powershell.exe','-NoProfile','-File',str(P/'Tools/Saiga12KDetail/wait_builds.ps1')],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
paths=['Source/FPSGAME/Weapons/Saiga12KWeaponAssets.h','Source/FPSGAME/Weapons/Saiga12KAttachments.h','Source/FPSGAME/Weapons/TacticalDeviceVariants.h','Source/FPSGAME/Weapons/FPSWeaponFXComponent.cpp','Source/FPSGAME/Weapons/Saiga12KMagazineAssets.h']
old='Saiga12K/SurfaceRebuild20261018/';new='Saiga12K/Detail20261018/'
def write(path,text):
 p=P/path;b=O/'SourceBefore'/path;b.parent.mkdir(parents=True,exist_ok=True)
 if not b.exists():shutil.copy2(p,b)
 p.write_text(text,encoding='utf-8')
for path in paths:
 s=(P/path).read_text(encoding='utf-8-sig')
 if old not in s and new not in s:raise RuntimeError('Runtime reference changed '+path)
 write(path,s.replace(old,new))
path='Content/ColdSteelData/modular_outfits.json';d=json.loads((P/path).read_text(encoding='utf-8-sig'))
oldmesh='/Game/Weapons/'+old+'SK_Saiga12K_Manny.SK_Saiga12K_Manny';newmesh='/Game/Weapons/'+new+'SK_Saiga12K_Manny.SK_Saiga12K_Manny'
d['profiles'][newmesh]=d['profiles'][oldmesh];write(path,json.dumps(d,ensure_ascii=False,indent=2)+'\n')
icon='Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/ue_saiga12k_magazine_saiga12k_ext12.png';backup=O/'SourceBefore'/icon;backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():shutil.copy2(P/icon,backup)
shutil.copy2(O/'Preview/Ext12_Framed.png',P/icon)
(O/'Receipts/activation.json').write_text(json.dumps({'mesh':newmesh,'source_files':paths,'outfit_profile_copied':True,'gameplay_numbers_unchanged':True,'runtime_tested':False},indent=2))
print('SAIGA_DETAIL_REFERENCES_UPDATED')
