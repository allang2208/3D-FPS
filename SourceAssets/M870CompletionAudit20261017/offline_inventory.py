"""Requested M870 catalog/reference audit; does not launch UE or alter saves."""
import json,re
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
d=json.loads((P/'Content/ColdSteelData/gunsmith.json').read_text(encoding='utf-8-sig'))
w=next(x for x in d['weapons'] if x['id']=='ue_m870');rows=[]
def check(name,passed,detail=None):rows.append(dict(case=name,passed=bool(passed),detail=detail))
for slot in w['allowed']:
    options=w['options'].get(slot,[]);ids=[x['id'] for x in options]
    check('slot '+slot,options and len(ids)==len(set(ids)) and 'false' in ids,ids)
check('retired reargrip absent','reargrip' not in w['allowed'] and 'reargrip' not in w['options'])
tube=next(x for x in w['options']['magazine'] if x['id']=='m870_tube_extension')
trigger=next(x for x in w['options']['trigger'] if x['id']=='m870_lightweight_trigger_kit')
check('requested extension and trigger stats',tube['stats']=={'mag_delta':3} and trigger['stats']=={'fire_interval_mult':.75,'recoil_mult':.95,'stability_mult':1.05})
check('requested base hip spread',abs(w['base']['spread_mult']-2.25*.55)<1e-9)
registry=(P/'Source/FPSGAME/Characters/FPSPreloadAssetRegistry.gen.h').read_text(encoding='utf-8-sig')
paths=sorted(set(re.findall(r'TEXT\("(/Game/Weapons/M870/[^"%]+)"\)',registry)))
for path in paths:check('preload asset '+path,(P/'Content'/(path.removeprefix('/Game/')+'.uasset')).is_file())
# Per-recipe references constructed at runtime do not appear as full literals in
# the global preload registry. Include the active optic bodies and fitted seats.
for option in w['options']['optic']:
    kind=option['id']
    if kind=='false':continue
    for part in (kind,'OpticSeat_'+kind):
        check('fitted optic '+part,(P/'Content/Weapons/M870/Optics20261016/Meshes'/('SM_M870_'+part+'.uasset')).is_file())
for part in ('lpvo_ring','thermal_selector'):
    check('optic moving part '+part,(P/'Content/Weapons/M870/Optics20261016/Meshes'/('SM_M870_'+part+'.uasset')).is_file())
for empty in ('normal','empty'):
    for count in range(1,8):
        part=f'A_M870_loader_{empty}_{count}'
        check('loader action '+part,(P/'Content/Weapons/M870/Speedloader20261016/Animations'/(part+'.uasset')).is_file())
animations=sorted(f.stem for f in (P/'Content/Weapons/M870/Tactical20261015/Animations').glob('*.uasset'))
for role in ('idle','equip','fire','reload_continuous','reload_full','inspect','walk','run','sprint_enter','sprint_loop','sprint_exit','cycle','quick_melee'):
    check('native action '+role,('A_M870_'+role) in animations)
for icon in ('trigger_m1911_lightweight_fast','magazine_super90_extended_tube','category_trigger'):
    check('shared icon '+icon,(P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'/(icon+'.png')).is_file())
ini=(P/'Config/DefaultGame.ini').read_text(encoding='utf-8-sig')
check('cook includes M870 root','+DirectoriesToAlwaysCook=(Path="/Game/Weapons/M870")' in ini)
report={'mode':'offline catalog and file references only','checks':len(rows),'failures':sum(not r['passed'] for r in rows),
        'results':rows,'animation_assets':animations,'runtime_executed':False}
(O/'offline-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'checks':len(rows),'failures':report['failures'],'failed':[r for r in rows if not r['passed']]},ensure_ascii=False))
