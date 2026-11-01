"""M24 native formula tuning and sniper critical-class registration.

No end-of-chain multiplier, skill stacks, enhancement level or save edits.
Only the M24 JSON objects are replaced, retaining unrelated concurrent entries.
"""
import copy,json,re,math
from pathlib import Path
O=Path(__file__).resolve().parent
R=O.parents[1];D=R/'Content/ColdSteelData'
formula={'source':'M24_NATIVE_BALANCE_20261028','base':40,'enhanceFlat':2.75,
         'attrs':[{'key':'int','base':2.5,'perEnhance':.275},{'key':'wis','base':5.,'perEnhance':.4375}]}
report={'runtime_tested':False,'files':[],'common_critical_bonus':1.,'weakpoint_bonus_added':False}
def patch(name,find,change):
    p=D/name;raw=p.read_bytes();text=raw.decode('utf-8-sig')
    start=find(text);old,used=json.JSONDecoder().raw_decode(text[start:]);new=copy.deepcopy(old);change(new)
    backup=O/('before_'+name)
    if not backup.exists():backup.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
    line=text.rfind('\n',0,start)+1
    indent=re.match(r'[ \t]*',text[line:start]).group()
    newline='\r\n' if '\r\n' in text else '\n'
    replacement=json.dumps(new,ensure_ascii=False,indent=2).replace('\n','\n'+indent).replace('\n',newline)
    updated=text[:start]+replacement+text[start+used:]
    if p.read_bytes()!=raw:raise RuntimeError('Concurrent catalog edit retained: '+name)
    p.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+updated.encode('utf-8'))
    report['files'].append(name)
    return old,new
def object_start(text):return re.search(r'"ue_m24"\s*:\s*\{',text).end()-1
def weapon_start(text):
    at=re.search(r'"id"\s*:\s*"ue_m24"',text).start()
    return text.rfind('{',0,at)
before,after=patch('combat-weapon-formulas.json',object_start,lambda d:(d.clear(),d.update(formula)))
def item(d):
    d['weaponType']='sniper';d['critDamageBonus']=1.
    d['stats']=[s for s in d.get('stats',[]) if s.get('name')!='物理攻击']
patch('items.json',object_start,item)
def traits(d):
    entry={'icon':'special','text':'暴击伤害+100%。'}
    for i,t in enumerate(d['traits']):
        if '暴击伤害' in t['text']:d['traits'][i]=entry;break
    else:d['traits'].append(entry)
patch('gunsmith.json',weapon_start,traits)
svch=json.loads((D/'combat-weapon-formulas.json').read_text(encoding='utf-8-sig'))['ue_svch']
def damage(f,level,intelligence,wisdom):
    values={'int':intelligence,'wis':wisdom}
    return math.floor(f['base']+level*f['enhanceFlat']+sum(values[a['key']]*(a['base']+level*a['perEnhance']) for a in f['attrs'])+.5)
report.update(before=before,after=after,svch_reference=svch,
              calculation_scope='Native formula only, before mastery flat bonus, ammo, crafting, affixes, weakpoint and defense.',
              authoring_samples=[{'int':i,'wis':w,'enhance':l,'M24_before':damage(before,l,i,w),'M24_after':damage(after,l,i,w),'SVCH':damage(svch,l,i,w),'ratio':damage(after,l,i,w)/damage(svch,l,i,w)} for i,w in [(10,10),(30,30),(10,50)] for l in (0,5,15)])
(O/'balance_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'written':report['files'],'authoring_samples':report['authoring_samples']},ensure_ascii=False))
