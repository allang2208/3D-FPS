"""Install the per-rifle extended-magazine option icons.

attachment-icons.md: weapon-specific icons are named
<weapon definition id>_<slot>_<option id>.png and take priority over the shared
image, so the M4/AKM PMAG magazines stop showing the QBZ-191 silhouette.

Run: UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=<this file>
"""
import unreal as u
import json
import shutil
from pathlib import Path

P = Path(__file__).parent
ICONDIR = Path(r"D:\FPS3D\FPSGAME\Content\ColdSteelData\AttachmentIcons20260913")
ICONS = {
    'ue_m4a1': P / 'Reference' / 'icon_ue_m4a1.png',
    'ue_akm': P / 'Reference' / 'icon_ue_akm.png',
    'ue_qbz191': P / 'Reference' / 'icon_ue_qbz191.png',
}

A = u.AssetToolsHelpers.get_asset_tools()
E = u.EditorAssetLibrary
report = {}
for weapon, src in ICONS.items():
    name = '%s_magazine_ext_mag' % weapon
    if not src.exists():
        report[name] = 'SOURCE MISSING ' + str(src)
        continue
    live = ICONDIR / (name + '.png')
    shutil.copy2(src, live)
    task = u.AssetImportTask()
    task.filename = str(live)
    task.destination_path = '/Game/ColdSteelData/AttachmentIcons20260913'
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    A.import_asset_tasks([task])
    asset = u.load_asset(task.destination_path + '/' + name)
    if not isinstance(asset, u.Texture2D):
        report[name] = 'IMPORT FAILED'
        continue
    E.save_loaded_asset(asset, False)
    report[name] = {
        'png': str(live),
        'texture': asset.get_path_name(),
        'weapon': weapon,
        'shared_fallback': 'magazine_ext_mag.png (QBZ-191 silhouette, unchanged)',
    }

(P / 'icon_per_weapon_receipt.json').write_text(json.dumps(report, indent=2, default=str))
u.log('EXTMAG_PER_WEAPON_ICONS ' + json.dumps(report, default=str))
