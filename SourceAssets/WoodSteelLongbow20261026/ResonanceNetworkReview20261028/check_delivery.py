"""Check this delivery's catalog and saved package paths; no UE or player save writes."""
from pathlib import Path
import json,re
P=Path(__file__).resolve().parent
ROOT=P.parents[2]
catalog=json.loads((ROOT/'Content/ColdSteelData/bow-gunsmith.json').read_text(encoding='utf-8-sig'))
found={};paths=set()
def walk(v):
    if isinstance(v,dict):
        if v.get('id') in ('highland_mountain_echo','highland_cadence'):found[v['id']]=v
        for child in v.values():walk(child)
    elif isinstance(v,list):
        for child in v:walk(child)
walk(catalog)
for option in found.values():
    for value in option.get('visual',{}).values():
        if isinstance(value,str) and value.startswith('/Game/'):paths.add(value)
for header in ('MountainEchoString.h','CadenceString.h'):
    s=(ROOT/'Source/FPSGAME/Weapons/Bow'/header).read_text(encoding='utf-8-sig')
    paths.update(re.findall(r'TEXT\("(/Game/[^"\r\n]+)"\)',s))
for name in ('CadenceV1','MountainEchoV13'):
    receipt=json.loads((P.parent/name/'import-receipt.json').read_text(encoding='utf-8-sig'))
    def assets(v):
        if isinstance(v,str) and v.startswith('/Game/'):paths.add(v)
        elif isinstance(v,dict):
            for child in v.values():assets(child)
        elif isinstance(v,list):
            for child in v:assets(child)
    assets(receipt)
for option in found:
    paths.add('/Game/ColdSteelData/AttachmentIcons20260913/FramedBows/bow_woodsteel_string_'+option)
rows=[{'path':a,'saved_package_exists':(ROOT/'Content'/(a.removeprefix('/Game/').split('.')[0]+'.uasset')).is_file()} for a in sorted(paths)]
cook=(ROOT/'Config/DefaultGame.ini').read_text(encoding='utf-8-sig')
report={'options':list(found),'restricted_to_highland':all(o.get('weapons')==['bow_woodsteel'] for o in found.values()),
        'cadence_passive_draw_speed':found['highland_cadence']['stats']['draw_speed_bonus'],
        'always_cook_bow_folder':'DirectoriesToAlwaysCook=(Path="/Game/Weapons/WoodSteelLongbow20261026")' in cook,
        'packages':rows,'missing_packages':[r['path'] for r in rows if not r['saved_package_exists']],
        'visual_acceptance':False,'actual_socket_transport':False}
(P/'delivery-paths.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'options':len(found),'packages':len(rows),'missing':report['missing_packages'],'cook':report['always_cook_bow_folder']},ensure_ascii=False))
raise SystemExit(0 if len(found)==2 and not report['missing_packages'] and report['always_cook_bow_folder'] else 1)
