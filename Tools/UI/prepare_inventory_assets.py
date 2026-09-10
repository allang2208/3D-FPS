"""Copy read-only Godot definitions/icons; retain full source metadata and provenance."""
import json, pathlib, shutil, hashlib
root = pathlib.Path(__file__).resolve().parents[2]
source = pathlib.Path('E:/3d/3-dfps')
path = root / 'Content/ColdSteelData/items.json'
data = json.loads(path.read_text(encoding='utf-8'))
data['ue_m4a1'] = dict(data['fps_hk416'], id='ue_m4a1', name='M4A1', desc='当前 UE 第一人称 M4A1。使用 5.56mm 弹药。', icon='res://assets/ui/icons/equip/fps_hk416.png')
manifest = []
for key, item in data.items():
    icon = item.get('icon', '')
    if icon.startswith('res://'):
        src = source / icon[6:]
        if src.is_file() and src.suffix.lower() == '.png':
            dest = root / 'Content/ColdSteelData/Icons' / (key+'.png')
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            item['ue_icon'] = 'Icons/'+dest.name
            manifest.append(dict(source=str(src), target=str(dest.relative_to(root)), sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
(root/'Content/ColdSteelData/provenance.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'{len(data)} definitions; {len(manifest)} source icons retained')
