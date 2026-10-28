"""Publish the four distinct common bodies and replace obsolete hold-duration modifiers."""
from pathlib import Path
import json,os,datetime
P=Path(__file__).parent;ROOT=Path('D:/FPS3D/FPSGAME')
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S%f')
backup=P/('Before-'+stamp);backup.mkdir(parents=True,exist_ok=True)
saved=[]
def edit(filename,mutate):
    path=ROOT/'Content/ColdSteelData'/filename;raw=path.read_bytes();data=json.loads(raw)
    mutate(data);out=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if out==raw:return
    if path.read_bytes()!=raw:raise RuntimeError('Preserving concurrent catalog edit: '+filename)
    (backup/filename).write_bytes(raw)
    temp=path.with_name(path.name+'.bowbalance.tmp');temp.write_bytes(out);os.replace(temp,path);saved.append(str(path))
STATS={
 'strong_draw':{'physical_damage_mult':1.05,'piercing_damage_mult':1.30,'stamina_mult':1.50,'charge_stamina_mult':1.50},
 'swift_limb':{'draw_speed_bonus':.35,'stamina_mult':.70,'charge_stamina_mult':.70,'shot_damage_mult':.80,'range_mult':.75},
 'heavy_limb':{'range_mult':1.20,'shot_damage_mult':1.15,'speed_mult':1.15,'draw_speed_bonus':-.30,'stamina_mult':1.50,'charge_stamina_mult':1.50},
 'steady_limb':{'spread_mult':.60,'draw_speed_bonus':.15,'nock_mult':.75,'shot_damage_mult':.85,'range_mult':.75,'stamina_mult':1.20,'charge_stamina_mult':1.20}}
DESCRIPTIONS={
 'strong_draw':'紧束弓根与连续木纹承受绷紧的拉力，为持续蓄力的穿心箭调校。',
 'swift_limb':'削薄的轻弓臂与平滑反曲弓梢相接，保留轻巧的拉放手感。',
 'heavy_limb':'宽厚木芯压合深色背衬，弓梢收束成饱满的重箭轮廓。',
 'steady_limb':'层压弓臂与收束弓根相接，纵向木纹贯穿细长的弓身。'}
HOLD_REPLACEMENTS={'waxed_linen':.90,'woven_linen_grip':.92,'slim_leather_grip':1.10,'padded_leather_grip':.80,'fast_string':1.10}
HOLD_TEXT={
 'waxed_linen':'棕色蜡麻沿握持区紧密缠绕，纤维表面压出细密防滑纹。',
 'woven_linen_grip':'交错编织的蜡麻包面贴合掌心，束线收住上下两端。',
 'slim_leather_grip':'薄革斜绕握面，压边与收尾贴伏在弓根。',
 'padded_leather_grip':'柔软皮革包裹内衬，掌心接触面圆润饱满。',
 'fast_string':'浅棕纤维捻成轻细弓弦，弓梢处以小圈固定。'}
def catalog(d):
    for column in d['columns']:
        column['options']=[p for p in column['options'] if p['id']!='woodcrafted_heavy']
        for part in column['options']:
            key=part['id'];stats=part.setdefault('stats',{})
            stats.pop('hold_mult',None)
            if key in STATS:
                part['stats']=STATS[key].copy();part['description']=DESCRIPTIONS[key]
                part.pop('special_effects',None)
            if key=='strong_draw':
                part['special_effects']=['穿心蓄势｜学会穿心箭后，满拉并蓄力至穿心就绪，穿心箭伤害 +30%。']
            if key=='steady_limb':part['name']='细枝弓体'
            if key in HOLD_REPLACEMENTS:
                part['stats']['charge_stamina_mult']=HOLD_REPLACEMENTS[key]
                part['description']=HOLD_TEXT[key]
            if key=='highland_far_peak':
                # The accepted +40% stamina cost now covers both physical bow cost channels.
                part['stats']['charge_stamina_mult']=part['stats']['stamina_mult']
    for weapon in d['weapons']:
        risers=weapon.get('part_overrides',{}).get('riser',{})
        risers.pop('woodcrafted_heavy',None)
        if 'steady_limb' in risers:
            risers['steady_limb']['name']='细枝弓体'
def bows(d):
    for bow in d.values():bow.pop('hold_seconds',None)
edit('bow-gunsmith.json',catalog);edit('bows.json',bows)
(P/'catalog-receipt.json').write_text(json.dumps({'saved':saved,'backup':str(backup),'common_bodies':STATS,
    'obsolete_hold_replacements':HOLD_REPLACEMENTS,'handmade_migration':'Normalize to heavy_limb; refund two woodworked_bow_limb on next successful Apply',
    'gameplay_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('BOW_BALANCE_V5_INSTALLED',flush=True)
