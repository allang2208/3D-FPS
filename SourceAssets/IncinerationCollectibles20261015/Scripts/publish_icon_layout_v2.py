"""Requested icon-standard review and installation of the corrected geometric framing."""
from pathlib import Path
from datetime import datetime,timezone
import json,shutil
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];DATA=PROJECT/'Content/ColdSteelData'
report=json.loads((ROOT/'icon-layout-v2.json').read_text('utf-8'))
items=json.loads((DATA/'items.json').read_text('utf-8-sig'))
if report['stage']!='inventory_icons_saved':raise RuntimeError('Rendering is incomplete')
checks=[]
for row in report['icons']:
    item=items[row['id']];source=Path(row['file']);im=Image.open(source)
    width,height=im.size;gw,gh=item['grid_w'],item['grid_h']
    if im.mode!='RGBA' or im.size!=(gw*512,gh*512):raise RuntimeError('Unexpected icon dimensions/channels: '+row['id'])
    alpha=im.getchannel('A');bbox=alpha.point(lambda x:255 if x>=16 else 0).getbbox()
    if not bbox or alpha.getextrema()!=(0,255):raise RuntimeError('Unexpected transparent silhouette: '+row['id'])
    margins=[bbox[0],bbox[1],width-bbox[2],height-bbox[3]]
    error=[abs((bbox[0]+bbox[2])*.5-width*.5)/width,abs((bbox[1]+bbox[3])*.5-height*.5)/height]
    if min(margins)<=0 or max(error)>.01:raise RuntimeError('Silhouette is clipped or off-centre: '+row['id'])
    expected='vertical_centered' if gw==1 and gh>1 else 'horizontal_centered' if gh==1 and gw>1 else 'standard_inventory'
    if row['orientation']['mode']!=expected:raise RuntimeError('Unexpected orientation: '+row['id'])
    checks.append(dict(id=row['id'],name=item['name'],size=[width,height],grid=[gw,gh],rgba=True,transparent=True,
        projected_silhouette_bbox=bbox,margin_pixels=margins,centre_error_fraction=error,orientation=expected,passed=True))
backup=ROOT/'BeforeIconLayoutV2';backup.mkdir(exist_ok=True)
old=ROOT/'presentation.json'
if old.exists() and not (backup/old.name).exists():shutil.copy2(old,backup/old.name)
for row in report['icons']:
    target=DATA/items[row['id']]['icon'];saved=backup/target.name
    if target.exists() and not saved.exists():shutil.copy2(target,saved)
    shutil.copy2(row['file'],target)
    row['inventory_registered']=True
report['layout_revision']='actual_geometry_projection_v2'
(ROOT/'presentation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
audit=dict(timestamp_utc=datetime.now(timezone.utc).isoformat(),scope='User-requested inventory icon convention review',
    checked_icons=checks,geometry_source_unchanged=True,inventory_footprints_unchanged=True,
    production_icons_installed=True,game_run=False,ue_editor_launched=False,
    limitations='File/image review only; no in-game UI capture.')
(ROOT/'Receipts/icon-standard-review.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
delivery_path=ROOT/'delivery.json'
if delivery_path.exists():
    delivery=json.loads(delivery_path.read_text('utf-8'))
    delivery['icon_layout_revision']='actual_geometry_projection_v2'
    delivery['requested_icon_file_review']='Receipts/icon-standard-review.json'
    delivery_path.write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf-8')
print('ICON_LAYOUT_V2_PUBLISHED',len(checks))
for row in checks:print(row['id'],row['margin_pixels'],row['centre_error_fraction'])
