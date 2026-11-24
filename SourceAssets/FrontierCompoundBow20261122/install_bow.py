"""Install this bow's saved packages, then activate only its catalog records."""
import argparse
import codecs
import copy
import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('project', type=Path)
parser.add_argument('batch', type=Path)
args = parser.parse_args()
project, batch = args.project.absolute(), args.batch.absolute()
source = Path(__file__).resolve().parent
content = project/'Content'
data = content/'ColdSteelData'
host = batch/'Host/Content'
weapon = 'bow_frontier_compound'
folder = 'Weapons/FrontierCompoundBow'
stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
before = batch/'Before'/stamp
edits = {}
files = {}
read = lambda path: json.loads(path.read_bytes().decode('utf-8-sig'))
digest = lambda blob: hashlib.sha256(blob).hexdigest()
vec = lambda v: ','.join(format(round(x,4), 'g') if abs(x) >= .0001 else '0' for x in v)
geo = read(source/'geometry.json')
imported = read(batch/'import.json')
assets = dict(imported['packages'])
assets.update(read(batch/'part-icons.json'))
expected = {'SK_Frontier_Assembly', 'SK_Frontier_Assembly_Skeleton',
            'SM_Frontier_Grip', 'SM_Frontier_Rest','SM_Frontier_Stabilizer',
            'M_Frontier_Surface','M_Frontier_Cord','T_Frontier_BaseColor',
            'T_Frontier_Normal','T_Frontier_MetalRough', weapon}
part_keys = {slot: weapon+'_'+slot+'_false' for slot in ('riser','grip','arrow_rest')}
if set(assets) != expected.union(part_keys.values()):
    raise ValueError('Incomplete staging package ledger')
for name, asset in assets.items():
    path = asset.split('.')[0].removeprefix('/Game/')
    allowed = (path.startswith(folder+'/') or path == 'ColdSteelData/Icons/'+weapon
               or path == 'ColdSteelData/AttachmentIcons20260913/FramedBows/'+name and name in part_keys.values())
    if not allowed or '..' in path or asset != '/Game/'+path+'.'+name:
        raise ValueError('Unexpected package '+asset)
    for ext in ('.uasset','.uexp','.ubulk','.uptnl'):
        origin = (host/path).with_suffix(ext)
        if ext == '.uasset' or origin.exists():
            files[(Path(path)).with_suffix(ext)] = origin
    if name == weapon or name in part_keys.values():
        location = source/'Export' if name == weapon else source/'Export/PartIcons'
        files[Path(path+'.png')] = location/(name+'.png')

def new_bow(base):
    out = copy.deepcopy(base)
    out.update(id=weapon,name='边境复合弓',ue_icon='Icons/'+weapon+'.png',price=1450,
        desc='边境巡守使用的短身复合弓。拉弦时，上下偏心轮随弓臂一起运动，两根控制缆在轮组之间联动。按住左键搭箭拉弓，松开射箭，按 R 可缓收。箭支取自已装备的箭袋。',
        full_damage=69, critDamageBonus=.5, bow_hip_spread=.04375, bow_damage_revision=2, bow_traits_revision=4,
        bow_innate_draw_speed_bonus=.25, bow_innate_hip_spread_mult=1,
        bow_part_slots='riser,grip,string,arrow_rest,sight,stabilizer,arrow',
        bow_part_riser_mesh=assets['SK_Frontier_Assembly'],bow_part_string_material=assets['M_Frontier_Cord'],
        bow_part_grip_mesh=assets['SM_Frontier_Grip'],bow_part_arrow_rest_mesh=assets['SM_Frontier_Rest'],
        bow_part_stabilizer_mesh=assets['SM_Frontier_Stabilizer'],bow_part_stabilizer_scale=1,
        bow_part_stabilizer_rods=0,bow_part_stabilizer_material='',
        bow_part_sight_mesh='',bow_ads_sight_cm='',bow_part_sight_material='',bow_part_sight_rods=0,
        bow_scope_magnification=1,bow_fit_shared_contact=1,bow_reference_brace_cm=base['brace_nock_cm'],
        bow_reference_draw_cm=base['draw_anchor_cm'],bow_length_cm=geo['length'],bow_depth_cm=geo['depth'],
        nock_upper_cm=vec(imported['anchors']['upper_tip']),nock_lower_cm=vec(imported['anchors']['lower_tip']),
        draw_anchor_cm=vec(imported['anchors']['compound_draw_end']),brace_nock_cm=vec(geo['brace']),
        arrow_rest_cm=vec(geo['rest']),bow_scale=1)
    return out

def new_gunsmith(catalog, base):
    factory = {
        'riser': ('SK_Frontier_Assembly','原装双轮弓体','上下弓臂、偏心轮与控制缆构成一套联动组件。'),
        'grip': ('SM_Frontier_Grip','原装边境握把','贴合边境弓身的独立握把。'),
        'arrow_rest': ('SM_Frontier_Rest','原装边境箭台','与边境弓身侧面贴合的箭台。')}
    patches = {}
    base_rest = [float(n) for n in base['arrow_rest_cm'].split(',')]
    delta = [v-old for v,old in zip(geo['rest'],base_rest)]
    for col in catalog['columns']:
        slot = col['key']
        variants = [('false',col['factory_visual'])]
        variants += [(o['id'],o.get('visual',{})) for o in col['options']
                     if not o.get('weapons') or weapon in o['weapons']]
        for choice,visual in variants:
            entry = {}
            if slot in factory:
                mesh, label, description = factory[slot]
                prefix = 'bow_part_'+slot+'_'
                fields = {prefix+'mesh': assets[mesh],prefix+'scale':1}
                if choice == 'false' or slot != 'grip':
                    fields[prefix+'material'] = ''
                if slot == 'arrow_rest':
                    fields['arrow_rest_cm'] = vec(geo['rest'])
                entry['visual'] = fields
                entry['appearance'] = description
                if choice=='false':
                    entry.update(name=label,description=description)
            elif slot=='string' and choice=='false':
                entry.update(name='原装复合弓弦',description='主弦连接两侧轮缘，搭箭点跟随拉弦手。',
                             visual={'bow_part_string_material':assets['M_Frontier_Cord'],'bow_part_string_rods':2})
            elif slot=='sight':
                if choice=='false':
                    entry.update(name='不安装瞄具',description='通过箭台沿箭杆方向瞄准。',
                        visual={'bow_part_sight_mesh':'','bow_ads_sight_cm':'','bow_part_sight_rods':0,
                                'bow_scope_magnification':1,'bow_ads_rest_cm':'63,10,-12'})
                elif visual.get('bow_ads_sight_cm'):
                    aim = [float(x) for x in visual['bow_ads_sight_cm'].split(',')]
                    entry['visual'] = {'bow_part_sight_location_cm':vec(delta),
                                       'bow_ads_sight_cm':vec([v+d for v,d in zip(aim,delta)])}
            if entry:
                patches.setdefault(slot,{})[choice]=entry
    categories = dict(part_keys,string='bow_dark_category_string',sight='bow_dark_category_sight')
    icons = dict(part_keys,string='bow_dark_string_false',sight='bow_dark_sight_no_sight')
    return {'id':weapon,'shared_icon_weapon':'bow_dark','category_icon_sources':categories,
            'factory_icon_sources':icons,'part_overrides':patches,'traits':[
            {'icon':'special','text':'暴击伤害+50%'},{'icon':'special','text':'拉弓速度+25%'},
            {'icon':'special','text':'双轮联动：拉弓与缓收时，弓臂、轮组和弦缆同步运动。'},
            {'icon':'mechanic','text':'无声射击：拉弓、放箭与箭矢命中不会通过声音引起怪物警觉。'}]}

def stage_text(path, operation):
    raw = path.read_bytes()
    old = raw.decode('utf-8-sig')
    newline = '\r\n' if '\r\n' in old else '\n'
    new = operation(old.replace('\r\n','\n')).replace('\n',newline)
    encoded = (codecs.BOM_UTF8 if raw.startswith(codecs.BOM_UTF8) else b'')+new.encode('utf8')
    if encoded != raw:
        edits[path] = (raw,encoded)

def add_record(path,section,record):
    def splice(text):
        original = json.loads(text)
        if section is None:
            old = original.get(record['id'])
            end = text.rindex('}')
            addition = json.dumps({record['id']:record},ensure_ascii=False,indent=2)[2:-2]
        else:
            old = next((x for x in original[section] if x['id']==record['id']),None)
            match = re.search(r'(?m)^  "'+re.escape(section)+r'"\s*:\s*(?=\[)',text)
            _, after = json.JSONDecoder().raw_decode(text,match.end())
            end = after-1
            addition = '\n'.join('    '+line for line in json.dumps(record,ensure_ascii=False,indent=2).splitlines())
        if old is not None:
            if old != record:
                raise RuntimeError('Preserving an existing different record '+record['id'])
            return text
        at = len(text[:end].rstrip())
        result = text[:at]+',\n'+addition+text[at:]
        decoded = json.loads(result)
        if section is None:
            assert decoded.pop(record['id']) == record
        else:
            assert decoded[section].pop() == record
        assert decoded == original
        return result
    stage_text(path,splice)

bows = data/'bows.json'
base = read(bows)['bow_dark']
add_record(bows,None,new_bow(base))
smith = data/'bow-gunsmith.json'
add_record(smith,'weapons',new_gunsmith(read(smith),base))
recipes = data/'woodworking-recipes.json'
recipe = copy.deepcopy(next(r for r in read(recipes)['recipes'] if r['id']=='woodwork_bow_woodsteel'))
recipe.update(id='woodwork_'+weapon,output={'item':weapon,'count':1})
add_record(recipes,'recipes',recipe)
wood = data/'woodworking.json'
pattern = copy.deepcopy(next(r for r in read(wood)['patterns'] if r['id']=='bow_woodsteel_limb'))
pattern.update(id=weapon+'_limb',name='弓 · 边境复合弓',craftRecipe=recipe['id'],
               description='完成边境复合弓的工件，加工达标后返回木工台领取成品。')
add_record(wood,'patterns',pattern)
def cook(s):
    header = '[/Script/UnrealEd.ProjectPackagingSettings]'
    line = '+DirectoriesToAlwaysCook=(Path="/Game/'+folder+'")'
    if header not in s:
        raise ValueError('Missing packaging settings')
    return s if line in s.splitlines() else s.replace(header,header+'\n'+line,1)
stage_text(project/'Config/DefaultGame.ini',cook)

published = {}
for rel, origin in files.items():
    target = content/rel
    sha = digest(origin.read_bytes())
    if target.exists() and digest(target.read_bytes()) != sha:
        raise RuntimeError('Preserving different installed asset '+str(rel))
    published[rel.as_posix()] = sha
for rel, origin in files.items():
    target = content/rel
    if target.exists():
        continue
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent,delete=False,suffix='.installing') as f:
        temp = Path(f.name)
    try:
        shutil.copyfile(origin,temp)
        # On Windows rename fails if a parallel author has created the destination.
        os.rename(temp,target)
    finally:
        temp.unlink(missing_ok=True)

for path,(old,new) in edits.items():
    archive = before/path.relative_to(project)
    archive.parent.mkdir(parents=True,exist_ok=True)
    archive.write_bytes(old)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False,suffix='.installing') as f:
        f.write(new)
        temp = Path(f.name)
    try:
        if path.read_bytes() != old:
            raise RuntimeError('Catalog changed during activation. Rerun on the latest data: '+str(path))
        os.replace(temp,path)
    finally:
        temp.unlink(missing_ok=True)
receipt = batch/'published.json'
if edits or not receipt.exists():
    document = {'weapon':weapon,'displayName':'边境复合弓','source':str(source),'asset_files':published,
        'staging_import':str(batch/'import.json'),'factory_icon_import':str(batch/'part-icons.json'),
        'shared_file_backups':str(before),'edited':{str(path.relative_to(project)):{
            'before':digest(old),'after':digest(new)} for path,(old,new) in edits.items()},
        'basis':['https://www.worldarchery.sport/sport/equipment/compound','https://bowtecharchery.com/technology/'],
        'in_game_tested':False}
    receipt.write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(f'Installed {len(assets)} UE packages and {len(files)-len(assets)} associated files for {weapon}.')
