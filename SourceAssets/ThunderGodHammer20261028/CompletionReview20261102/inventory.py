from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent;R=P.parents[2]
data=json.loads((R/'Content/ColdSteelData/thunder-god-hammer-modules.json').read_text(encoding='utf-8-sig'))
def walk(v):
    if isinstance(v,dict):
        for k,x in v.items():
            if k=='mesh' and isinstance(x,str):yield x
            else:yield from walk(x)
    elif isinstance(v,list):
        for x in v:yield from walk(x)
paths=sorted(set(walk(data)))
assets=[]
for path in paths:
    f=R/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
    assets.append(dict(asset=path,exists=f.is_file(),sha256=hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None))
config=(R/'Config/DefaultGame.ini').read_text(encoding='utf-8-sig')
result=dict(passed=all(x['exists'] for x in assets),assets=assets,
    thunder_always_cook='DirectoriesToAlwaysCook=(Path="/Game/Weapons/ThunderGodHammer20261028")' in config,
    icon_pngs_staged='DirectoriesToAlwaysStageAsUFS=(Path="ColdSteelData/AttachmentIcons20260913")' in config,
    scope='filesystem inventory only; saved asset load checks are in assets.json')
(P/'inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('CURRENT_MODULES',len(assets),'MISSING',sum(not a['exists'] for a in assets),'COOK',result['thunder_always_cook'],'ICONS_STAGED',result['icon_pngs_staged'])
