import ast,hashlib,json,shutil
from pathlib import Path
from PIL import Image
P=Path(__file__).resolve().parent;ROOT=P.parents[1];D=ROOT/'Content/ColdSteelData'
read=lambda p:json.loads(p.read_text('utf-8-sig'))
catalog=read(D/'tactical-hatchet-modules.json');gunsmith=read(D/'tactical-hatchet-gunsmith.json')
items=read(D/'items.json');formulas=read(D/'combat-weapon-formulas.json')
errors=[];columns={};icons=[]
def require(ok,message):
    if not ok:errors.append(message)
for column in gunsmith['columns']:
    options=list(column.get('options',[]))
    if column.get('options_library'):
        lib=read(D/column['options_library'])
        if column.get('options_column'):
            options+=next(c['options'] for c in lib['columns'] if c['key']==column['options_column'])
        else:options+=lib['options']
    columns[column['key']]=[o['id'] for o in options]
    for option in options:
        require(option['id'] in catalog['slots'][column['key']],'Missing module/surface: '+option['id'])
        if column['key']=='blade_2':require(len(catalog['slots']['blade_2'][option['id']]['surface_materials'])==5,'Incomplete rune head coverage')
require('blade_2' not in catalog['module_slots'],'Surface rune erroneously adds physical mesh')
for name in ('ue_kukri','ue_tactical_hatchet'):
    require(bool(items.get(name)),'Missing item '+name)
hatchet,kukri=items['ue_tactical_hatchet'],items['ue_kukri']
comparison={k:{name:items[name].get(k) for name in ('ue_kukri','ue_tactical_hatchet')}
            for k in ('weaponType','weaponTypeTag','attack_seconds','melee_reach_cm')}
base_stamina=read(D/'stamina.json')['meleeCost']*.5
comparison['base_stamina']={name:items[name].get('melee_stamina',base_stamina) for name in ('ue_kukri','ue_tactical_hatchet')}
require(hatchet['attack_seconds']>kukri['attack_seconds'],'Axe no longer slower than kukri')
require(hatchet['melee_reach_cm']==kukri['melee_reach_cm'],'Base reach mismatch')
require(comparison['base_stamina']['ue_tactical_hatchet']>comparison['base_stamina']['ue_kukri'],'Axe stamina cost regression')
f=formulas['ue_tactical_hatchet'];k=formulas['ue_kukri']
require(f['base']>k['base'] and f['enhanceFlat']>k['enhanceFlat'],'Axe base/upgrade damage regression')
for attr in f['attrs']:
    other=next(a for a in k['attrs'] if a['key']==attr['key'])
    require(attr['base']>other['base'] and attr['perEnhance']>other['perEnhance'],'Axe attribute scaling regression')
icon_source=ROOT/'SourceAssets/OneHandAxe20261101/BladeVariants20261102/ContinuousBladesR5_20261104'
for record in read(icon_source/'icon_deployments.json'):
    src=Path(record['source']);dest=D/'AttachmentIcons20260913'/(record['key']+'.png')
    require(src.read_bytes()==dest.read_bytes(),'Undeployed final icon '+record['id'])
    with Image.open(dest) as image:
        require(image.width==image.height and image.mode=='RGBA','Wrong icon canvas '+record['id'])
        icons.append({'key':record['key'],'size':image.size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
# Re-run the original registration recipe in an isolated copy. It must preserve later runes.
author=ROOT/'SourceAssets/OneHandAxe20261101/ModulesV1'
sandbox=P/'RegistrationSandbox/Project';fake=sandbox/'SourceAssets/OneHandAxe20261101/ModulesV1'
(fake/'Before').mkdir(parents=True,exist_ok=True);data=sandbox/'Content/ColdSteelData';data.mkdir(parents=True,exist_ok=True)
for name in ('tactical-hatchet-modules.json','tactical-hatchet-gunsmith.json','shared-knife-component-options.json'):shutil.copy2(D/name,data/name)
shutil.copy2(author/'import_receipt.json',fake/'import_receipt.json')
tree=ast.parse((author/'register_modules.py').read_text('utf-8'))
for node in tree.body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='P' for t in node.targets):
        node.value=ast.Call(func=ast.Name(id='Path',ctx=ast.Load()),args=[ast.Constant(str(fake))],keywords=[])
ast.fix_missing_locations(tree);exec(compile(tree,str(author/'register_modules.py'),'exec'),{'__file__':str(fake/'register_modules.py')})
after=read(data/'tactical-hatchet-modules.json')
require(after['slots']['blade_2']==catalog['slots']['blade_2'],'Base registration erases rune recipes')
require(after['slots']['blade_1']['factory']==catalog['slots']['blade_1']['factory'],'Base registration loses factory rune carrier')
result={'passed':not errors,'errors':errors,'columns':columns,'icons':icons,'comparison':comparison,
        'formulas':{name:formulas[name] for name in ('ue_kukri','ue_tactical_hatchet')},'base_registration_preserves_runes':not errors}
(P/'catalogs.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':not errors,'errors':errors,'comparison':comparison},ensure_ascii=True))
if errors:raise SystemExit(1)
