"""Publish the two approved legendary seat tiers and their passive attributes."""
from pathlib import Path
import copy, datetime, json, os

P=Path(__file__).resolve().parent
R=P.parents[2]
path=R/'Content/ColdSteelData/thunder-god-hammer-gunsmith.json'
raw=path.read_bytes();data=json.loads(raw.decode('utf-8-sig'))
options=next(c for c in data['columns'] if c['key']=='head_mount')['options']
changes=[]
for identity,key,multiplier,label in (
    ('guan_lei_seat','physical_damage_mult',1.1,'物理伤害+10%'),
    ('ji_lei_seat','attack_speed_mult',1.2,'攻击速度+20%')):
    entry=next(o for o in options if o['id']==identity)
    before=copy.deepcopy(entry)
    entry['tier']='legendary'
    entry.setdefault('stats',{})[key]=multiplier
    prefix='物理伤害' if identity=='guan_lei_seat' else '攻击速度'
    effects=entry.setdefault('effects',[])
    effects[:]=[e for e in effects if not e.get('text','').replace(' ','').startswith(prefix)]
    effects.append({'text':label,'benefit':1})
    changes.append({'id':identity,'before':before,'after':copy.deepcopy(entry)})
if path.read_bytes()!=raw:raise RuntimeError('Concurrent catalogue edit; no write performed')
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
(P/('before-'+stamp+'.json')).write_bytes(raw)
pending=path.with_name(path.name+'.seat-legendary-pending')
pending.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
os.replace(pending,path)
(P/'publication_receipt.json').write_text(json.dumps({'complete':True,'file':str(path),
    'changes':changes,'runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('THOR_LEGENDARY_SEAT_PASSIVES_PUBLISHED')
