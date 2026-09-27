"""Finish supersampled catalog artwork and wire the existing bow migration."""
import json,hashlib,shutil
from pathlib import Path
from PIL import Image
ROOT=Path('D:/FPS3D/FPSGAME');P=Path(__file__).parent
info=json.loads((P/'authoring.json').read_text())
image=Image.open(P/'bow_dark_2x.png').convert('RGBA')
# Premultiplied alpha keeps the sub-pixel bowstring and silhouette clean.
image=image.convert('RGBa').resize(tuple(info['catalog_size']),Image.Resampling.LANCZOS).convert('RGBA')
output=ROOT/'Content/ColdSteelData/Icons/bow_dark.png';output.parent.mkdir(parents=True,exist_ok=True)
backup=ROOT/'Saved/BowInventoryIcon20260926/Before';backup.mkdir(parents=True,exist_ok=True)
if output.exists() and not (backup/'bow_dark.png').exists():shutil.copy2(output,backup/'bow_dark.png')
catalog=ROOT/'Content/ColdSteelData/bows.json'
if not (backup/'bows.json').exists():shutil.copy2(catalog,backup/'bows.json')
image.save(P/'bow_dark.png');image.save(output)
d=json.loads(catalog.read_text(encoding='utf-8-sig'));bow=d['bow_dark']
bow['ue_icon']='Icons/bow_dark.png'
# NormalizeBowState owns ue_icon. The next normal profile load updates older
# inventory instances without editing the user's save file offline.
bow['bow_presentation_revision']=max(24,bow['bow_presentation_revision'])
catalog.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(P/'install-receipt.json').write_text(json.dumps({'installed_png':str(output),'ue_icon':bow['ue_icon'],
    'revision':bow['bow_presentation_revision'],'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
    'size':list(image.size),'runtime_import':'existing FImageUtils catalog PNG path',
    'native_changes':False,'ue_editor_started':False,'gameplay_tested':False},indent=2),encoding='utf8')
print('BOW_EQUIPMENT_ICON_INSTALLED',str(output),flush=True)
