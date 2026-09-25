# -*- coding: utf-8 -*-
"""图标替换的备份与发布（离线）：旧 PNG 进 Before/，新 PNG 覆盖 Content，散列进 before-backup.json。"""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(r'D:\FPS3D\FPSGAME')
BEFORE = ROOT / 'SourceAssets/ToolEnhance20260925/Before'
ICONS = ROOT / 'SourceAssets/ToolEnhance20260925/Icons'
BACKUP = ROOT / 'SourceAssets/ToolEnhance20260925/before-backup.json'
PAIRS = [('axe.png', 'icon-axe.png', 'axe_upright.png'),
         ('pickaxe_upright.png', 'icon-pickaxe_upright.png', 'pickaxe_upright.png')]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


data = json.loads(BACKUP.read_text(encoding='utf-8-sig'))
entries = data['entries']
for name, backup_name, icon_name in PAIRS:
    live = ROOT / 'Content/ColdSteelData/ProductionTools' / name
    backup = BEFORE / backup_name
    shutil.copy2(live, backup)
    new = ICONS / icon_name
    entry = {'path': str(live.relative_to(ROOT)).replace('\\', '/'),
             'backup': 'SourceAssets/ToolEnhance20260925/Before/' + backup_name,
             'before_sha256': sha(backup), 'replacement_sha256': sha(new)}
    shutil.copy2(new, live)
    entry['after_sha256'] = sha(live)
    entries.append(entry)
BACKUP.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
print('entries:', len(entries))
for entry in entries[-2:]:
    print(entry['path'], entry['before_sha256'][:12], '->', entry['after_sha256'][:12])
