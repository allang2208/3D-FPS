"""Read-only skill/config integration checks requested by the user.

Checks authored data and source registrations. Does not claim gameplay/PIE tests.
"""
import argparse
import json
import math
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
def read(path):return (ROOT/path).read_text(encoding='utf-8-sig')
def names(text):return set(re.findall(r'TEXT\("([A-Za-z][A-Za-z0-9]+)"\)',text))

def run(output):
    data=json.loads(read('Content/ColdSteelData/skills.json'))
    skills={key:value for key,value in data.items() if isinstance(value,dict) and key!='runeBlades'}
    rules=read('Source/FPSGAME/Skills/ColdSteelSkillRules.cpp')
    loader=rules.split('bool ColdSteelSkills::Migrate')[0]
    migration=rules.split('bool ColdSteelSkills::Migrate')[1].split('bool ColdSteelSkills::Validate')[0]
    dev=read('Source/FPSGAME/Development/ColdSteelDevelopmentTools.cpp')
    catalog=names(dev.split('UColdSteelStatusModel::SkillCatalog()')[1].split('return Ids;')[0])
    page=read('Source/FPSGAME/UI/ColdSteelSkillPage.cpp')
    notices=read('Source/FPSGAME/Skills/ColdSteelSkillModel.cpp')
    definitions=read('Source/FPSGAME/UI/ColdSteelProfileRuntime.cpp')+read('Source/FPSGAME/Skills/ColdSteelAdditionalMasteries.cpp')
    issues=[];rows=[]
    for key,entry in skills.items():
        row={'id':key,'name':entry.get('name'),'experience_per_level':entry.get('experiencePerLevel'),
             'level_cap':20,'numeric_fields':0,'checks':{}}
        checks=row['checks']
        checks['identity']=bool(entry.get('name') and entry.get('description'))
        checks['icon_exists']=bool(entry.get('icon')) and (ROOT/'Content/ColdSteelData'/entry['icon']).is_file()
        checks['development_catalog']=key in catalog
        checks['profile_migration']=key in names(migration)
        checks['skill_page_registration']=key in names(page)
        checks['definition_load']=key=='rifleMastery' or key in names(definitions)
        checks['upgrade_notice']=key in names(notices) or (key[0].upper()+key[1:]+'Skill') in notices
        checks['training_requirement']=isinstance(entry.get('experiencePerLevel'),int) and entry['experiencePerLevel']>0
        for field,value in entry.items():
            if isinstance(value,(int,float)) and not isinstance(value,bool):
                row['numeric_fields']+=1
                if not math.isfinite(value):issues.append(key+'.'+field+': non-finite value')
                if field not in names(loader):issues.append(key+'.'+field+': numeric key not read by definition loader')
        for name,ok in checks.items():
            if not ok:issues.append(key+': missing '+name)
        rows.append(row)
    if catalog-set(skills):issues.append('Development catalog contains unknown learnable skills: '+str(sorted(catalog-set(skills))))
    # Literal skill assets are checked against real package files. Formatted
    # paths are listed separately; this is not a cook or dependency-graph test.
    assets=set();dynamic_assets=set()
    for path in (ROOT/'Source/FPSGAME/Skills').iterdir():
        if path.suffix not in ('.h','.cpp'):continue
        for asset in re.findall(r'"(/Game/Skills/[^"\r\n]+)"',path.read_text(encoding='utf-8-sig')):
            if '%' in asset or '.' not in asset.rsplit('/',1)[-1]:dynamic_assets.add(asset);continue
            package=asset.split('.',1)[0]
            assets.add(package)
    for package in sorted(assets):
        if not (ROOT/'Content'/(package.removeprefix('/Game/')+'.uasset')).is_file():issues.append('Missing skill asset package: '+package)
    # These are deliberate equipment abilities, not unfinished levelling skills.
    special=[{'id':'runeBlades','kind':'equipment ability','entry':'Weapons/RuneOrbBladesComponent.cpp'},
             {'id':'staffLight','kind':'equipment ability','entry':'Weapons/Staff/StaffWeaponComponent.cpp'}]
    report={'scope':'data and source registrations; no game simulation','learnable_skills':len(rows),
        'equipment_abilities':special,'numeric_fields':sum(r['numeric_fields'] for r in rows),
        'issues':issues,'skills':rows,'literal_asset_packages':len(assets),
        'formatted_asset_paths':sorted(dynamic_assets),'gameplay_tested':False}
    dest=ROOT/output;dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'skills':len(rows),'numeric_fields':report['numeric_fields'],'issues':issues},ensure_ascii=False))
    return int(bool(issues))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='Saved/SkillCompletion20261013/completion.json')
    raise SystemExit(run(parser.parse_args().output))
