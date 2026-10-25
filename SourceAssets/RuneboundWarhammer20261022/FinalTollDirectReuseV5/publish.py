"""Install new packages and update only the four Final Toll body role leaves."""
import json,runpy,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
data=json.loads((P/'authored.json').read_text('utf-8'))
if not data.get('complete'):raise RuntimeError('Authoring incomplete')
saved=[]
for row in data['saved']:
    rel=Path(row['asset'].split('.')[0][6:]).with_suffix('.uasset')
    src=Path(data['author_project'])/'Content'/rel;dst=ROOT/'Content'/rel
    if dst.exists() and dst.read_bytes()!=src.read_bytes():raise RuntimeError('Preserve existing new motion '+str(dst))
    if not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    saved.append(str(dst))
path=ROOT/'Content/ColdSteelData/player_body.json';before=path.read_bytes();value=json.loads(before.decode('utf-8-sig'))
owned=[]
for variant,scope in [('Default',['clips']),('kaitlin',['body_variants','kaitlin','clips'])]:
    node=value
    for k in scope:node=node[k]
    for role,stem in [('Warhammer.FullBody.FinalTollHeavy','A_FinalToll_DirectReuseBodyV5_'),('Warhammer.FullBody.FinalTollCharge','A_FinalToll_ChargeBodyV5_')]:
        if role in node and not any(s in node[role] for s in ('/FinalTollNormalLeadV4/','/FinalTollDirectReuseV5/')):
            raise RuntimeError('Preserve changed role '+variant+' '+role)
        name=stem+variant;node[role]='/Game/Weapons/RuneboundWarhammer20261022/FinalTollDirectReuseV5/'+name+'.'+name
        owned.append(tuple(scope+[role]))
commit=runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit']
result=commit(path,before,value,owned_paths=owned,producer=__file__)
builds=json.loads((P/'build_receipt.json').read_text('utf-8-sig')) if (P/'build_receipt.json').exists() else []
built={x['target'] for x in builds if x['exit_code']==0}
(P/'published.json').write_text(json.dumps({'saved':saved,'body_roles':result,'complete':True,'tested':False,
    'native_build_required':not {'FPSGAMEEditor','FPSGAME'}.issubset(built),'builds':builds},indent=2),encoding='utf-8')
print('Five native motion packages installed and four body role leaves published')
