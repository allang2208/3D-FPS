"""Read-only coverage of published catalogs, package files, body roles and icons."""
from pathlib import Path
import hashlib,json,re,struct
P=Path(__file__).resolve().parent
R=P.parents[2]
def read(p):return json.loads((R/p).read_text('utf-8-sig'))
checks=[]
def check(name,ok,detail=None):checks.append(dict(case=name,passed=bool(ok),detail=detail))
bench=read('Content/ColdSteelData/runebound-warhammer-gunsmith.json')
mods=read('Content/ColdSteelData/runebound-warhammer-modules.json')
check('workbench author base matches published data',bench==read('SourceAssets/RuneboundWarhammer20261022/ModulesV1/workbench.json'))
check('module author base matches published data',mods==read('SourceAssets/RuneboundWarhammer20261022/ModulesV1/catalog_base.json'))
refs=set()
def gather(v):
    if isinstance(v,str) and v.startswith('/Game/'):refs.add(v)
    if isinstance(v,dict):
        for x in v.values():gather(x)
    if isinstance(v,list):
        for x in v:gather(x)
gather(mods)
body=read('Content/ColdSteelData/player_body.json')
role='Warhammer.FullBody.FinalTollHeavy'
for name,clips in [('default',body['clips']),('kaitlin',body['body_variants']['kaitlin']['clips'])]:
    check('double-heavy fullbody role '+name,role in clips);gather(clips.get(role))
for bundle in ['FinalTollIntegrationV1','StarOathIntegrationV1','HudSymmetricCapsV3']:
    receipt=read('SourceAssets/RuneboundWarhammer20261022/'+bundle+'/delivery_receipt.json')
    check('published receipt '+bundle,receipt.get('complete'))
    gather(receipt.get('saved_assets',[]));gather(receipt.get('material',''))
    if receipt.get('icon'):
        icon=R/receipt['icon'];check('actual installed legendary icon '+bundle,icon.is_file() and hashlib.sha256(icon.read_bytes()).hexdigest()==receipt['icon_sha256'])
for ref in sorted(refs):
    package=ref.split('.')[0];path=R/('Content/'+package[len('/Game/'):]+'.uasset')
    check('saved package '+package,path.is_file() and path.stat().st_size>0)
header=(R/'Source/FPSGAME/Production/RuneboundHammerTuning.h').read_text('utf-8-sig')
check('runtime HUD selects V3','HudSymmetricCapsV3/M_RuneboundEnergyHud' in header)
ini=(R/'Config/DefaultGame.ini').read_text('utf-8-sig')
check('weapon content cook root','+DirectoriesToAlwaysCook=(Path="/Game/Weapons/RuneboundWarhammer20261022")' in ini)
for f in sorted((R/'Content/ColdSteelData/AttachmentIcons20260913').glob('ue_runebound_warhammer*.png')):
    b=f.read_bytes();size=struct.unpack('>II',b[16:24]) if b[:8]==b'\x89PNG\r\n\x1a\n' else (0,0)
    check('runtime PNG '+f.name,size[0]>0 and size[1]>0,{'pixels':size,'sha256':hashlib.sha256(b).hexdigest()})
result={'passed':all(c['passed'] for c in checks),'count':len(checks),'checks':checks,'rendered':False,'engine_assets_modified':False}
(P/'assets.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({'passed':result['passed'],'count':len(checks),'failures':[x['case'] for x in checks if not x['passed']]}))
