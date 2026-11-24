"""Publish the saved packages first, then atomically switch only the three Frontier catalog entries."""
from pathlib import Path
import hashlib, json, os, shutil, sys, tempfile

project,batch=map(Path,sys.argv[1:3])
src=Path(__file__).resolve().parent
owned='/Game/Weapons/FrontierCompoundBow/CommonModsR1/'
catalog=project/'Content/ColdSteelData/bow-gunsmith.json'
def digest(b):return hashlib.sha256(b).hexdigest()
def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,suffix='.frontier-staging',delete=False) as f:
        f.write(data);temp=Path(f.name)
    try:os.replace(temp,path)
    finally:temp.unlink(missing_ok=True)
def setup_options(options,assets,aim):
    grips={
        'waxed_linen':('WaxWrap','琥珀棕蜡麻带沿原厂握把斜绕，细压边收进上下端套。'),
        'woven_linen_grip':('WovenWrap','石墨色编织面上穿过蓝灰交叉纹，两端压入深色包边。'),
        'slim_leather_grip':('SlimHide','赤褐薄革顺着掌面收紧，侧面留有双排浅色短针脚。'),
        'padded_leather_grip':('PaddedHide','炭灰软革分成四道掌垫沟槽，侧边缝线接入端套。')}
    cords={
        'fast_string':('FastLine','琥珀色示踪纱与深灰细股交缠，搭箭区两侧各留一道识别环。'),
        'steady_twist_string':('LockTwist','蓝灰三股紧捻，搭箭区用炭黑护线收束，配成对的蓝灰识别环。'),
        'softcore_hold_string':('Softcore','橄榄灰和深灰四股交织，较长的中央护线与双道浅色标记相接。')}
    optics={
        'bow_clearfield_2x':('Clearfield2x',2,'短镜圈留出开阔视野，青色细环、浅刻度与双臂镂空侧座相接。'),
        'bow_farwatch_4x':('Farwatch4x',4,'纵槽长遮光罩接入深灰镜座，铜色标环与带筋护圈区分前后缘。')}
    def use(slot,part,visual,appearance):
        entry=options[slot].setdefault(part,{})
        entry.update(visual=visual,appearance=appearance,description=appearance)
    for key,(asset,desc) in grips.items():
        use('grip',key,{'bow_part_grip_mesh':assets['SM_Frontier_'+asset],'bow_part_grip_material':'',
                        'bow_part_grip_scale':1,'bow_part_grip_rods':0,'bow_part_grip_location_cm':'0,0,0','bow_part_grip_rotation_deg':'0,0,0'},desc)
    for key,(asset,desc) in cords.items():
        use('string',key,{'bow_part_string_mesh':assets['SK_Frontier_'+asset],'bow_part_string_rods':0,
                          'bow_part_string_material':assets['M_FrontierMods_Surface'],'bow_part_string_scale':1,
                          'bow_part_string_location_cm':'0,0,0','bow_part_string_rotation_deg':'0,0,0','bow_part_string_hide_slot':''},desc)
    for key,(asset,power,desc) in optics.items():
        use('sight',key,{'bow_part_sight_mesh':assets['SM_Frontier_'+asset],'bow_part_sight_material':'',
                         'bow_part_sight_location_cm':'0,0,0','bow_part_sight_rotation_deg':'0,0,0','bow_part_sight_scale':1,
                         'bow_part_sight_rods':0,'bow_ads_sight_cm':','.join(f'{v:.3f}' for v in aim),
                         'bow_ads_sight_distance_cm':60,'bow_scope_magnification':power},desc)
assets=json.loads((batch/'imported.json').read_text(encoding='utf8'))
parts=json.loads((src/'parts.json').read_text(encoding='utf8'))
for key in parts['meshes']:
    if not assets.get(key,'').startswith(owned):raise ValueError('Incomplete import '+key)
old=catalog.read_bytes();bom=b'\xef\xbb\xbf' if old.startswith(b'\xef\xbb\xbf') else b''
text=old.decode('utf-8-sig');eol='\r\n' if '\r\n' in text else '\n';text=text.replace('\r\n','\n')
doc=json.loads(text);row=next(w for w in doc['weapons'] if w['id']=='bow_frontier_compound')
def formatted(value):return '\n    '.join(json.dumps(value,ensure_ascii=False,indent=2).splitlines())
before=formatted(row)
setup_options(row['part_overrides'],assets,parts['aim_cm'])
if text.count(before)!=1:raise ValueError('Unknown catalog layout')
new=bom+text.replace(before,formatted(row)).replace('\n',eol).encode('utf8')
receipt=batch/'published.json'
if not receipt.exists() and new!=old:
    backup=batch/'Before'/'bow-gunsmith.json';backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(old)
installed={}
for package in assets.values():
    if not package.startswith(owned):raise RuntimeError('Unexpected package '+package)
    rel=Path(package.split('.')[0][6:]+'.uasset')
    base=batch/'Host'/'Content'/rel
    for file in [base,*[p for p in base.parent.glob(base.stem+'.*') if p.suffix in ('.ubulk','.uptnl','.uexp')]]:
        dest=project/'Content'/rel.parent/file.name;blob=file.read_bytes()
        if dest.exists():
            if dest.read_bytes()!=blob:raise RuntimeError('Versioned target exists with different content: '+str(dest))
        else:atomic(dest,blob)
        installed[dest.relative_to(project).as_posix()]=digest(blob)
if new!=old:
    if catalog.read_bytes()!=old:raise RuntimeError('Catalog changed during publication; rerun to merge.')
    atomic(catalog,new)
if not receipt.exists() or new!=old:
    receipt.write_text(json.dumps(dict(weapon=row['id'],catalog=catalog.relative_to(project).as_posix(),
        before_catalog_sha256=digest(old),catalog_sha256=digest(new),before_catalog='Before/bow-gunsmith.json',
        slots=['sight','string','grip'],packages=installed,editable=str(src/'Frontier_CommonMods.blend'),
        runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf8')
print('Published',len(installed),'packages and nine Frontier slot overrides')
