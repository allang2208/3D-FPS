"""Prepare the scoped M249 source recovery package; never modify game assets."""
from pathlib import Path
import json,hashlib,re,subprocess,difflib

root=Path(__file__).resolve().parents[2]
out=root/'Docs/Publication/M24920261109'
out.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# Complete owned runtime additions are stored as explicit new-file patches.
# Their consumers are shared, partly unpublished hosts, so this package does
# not pretend that copying new .cpp files alone yields a buildable checkout.
owned=sorted((root/'Source/FPSGAME/Weapons').glob('M249*'))
owned+=[root/'Source/FPSGAME/Weapons/ScopeADSEyeRelief.h']
owned+=sorted((root/'Source/FPSGAME/Movement').glob('MachineGunMovementAuditCommandlet.*'))
runtime=[]
for p in owned:
    if p.suffix not in {'.cpp','.h'}:continue
    rel=p.relative_to(root).as_posix();content=p.read_text(encoding='utf-8-sig').splitlines(True)
    patch=''.join(difflib.unified_diff([],content,fromfile='/dev/null',tofile='b/'+rel,n=0))
    dest=out/'Integration/NewFiles'/(p.name+'.patch');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(patch,encoding='utf-8')
    runtime.append(dict(source=rel,sha256=sha(p),patch=dest.relative_to(root).as_posix()))

# Exact M249 branches from mixed hosts are reference sections, NOT an automatic
# patch queue. Keep local line numbers and full-host hashes for manual recovery.
path_list=out/'m249-paths-local.json'
paths=json.loads(path_list.read_text()) if path_list.exists() else [x['source'] for x in json.loads((out/'Integration/shared-host-sections.json').read_text())]
sections=[]
for raw in paths:
    rel=raw.replace('\\','/');p=root/rel
    if not rel.startswith('Source/') or p in owned or p.suffix not in {'.cpp','.h'}:continue
    lines=p.read_text(encoding='utf-8-sig').splitlines(True)
    regions=[]
    for i,line in enumerate(lines):
        if not re.search('m249|ScopeADSEyeRelief|MachineGunMovementMultiplier|RefreshWeaponTuning',line,re.I):continue
        start=i;end=i+1
        # A complete directly M249-owned if/function block, provided its opening
        # brace is on this or the following line. Combined shared expressions
        # remain short reference lines and do not copy sibling weapon branches.
        opening=line.find('{')
        if opening<0 and i+1<len(lines) and lines[i+1].strip()=='{':end=i+2;opening=0
        if opening>=0 and ('if' in line or re.search(r'\b(?:void|bool|float|FString)\b.*(?:M249|MachineGunMovementMultiplier|RefreshWeaponTuning)',line)):
            depth=sum(x.count('{')-x.count('}') for x in lines[start:end]);j=end
            while depth>0 and j<len(lines):depth+=lines[j].count('{')-lines[j].count('}');j+=1
            end=j
        elif line.rstrip().endswith(('||','&&',',','?')):
            end=min(len(lines),i+3)
        if regions and start<=regions[-1][1]:regions[-1]=(regions[-1][0],max(end,regions[-1][1]))
        else:regions.append((start,end))
    if regions:
        sections.append(dict(source=rel,host_sha256=sha(p),kind='manual-reference-not-auto-apply',regions=[dict(line=a+1,text=''.join(lines[a:b]))for a,b in regions]))
write(out/'Integration/shared-host-sections.json',sections)
write(out/'Integration/runtime-manifest.json',runtime)

data=root/'Content/ColdSteelData'
items=json.loads((data/'items.json').read_text(encoding='utf-8-sig'))
guns=json.loads((data/'gunsmith.json').read_text(encoding='utf-8-sig'))
assembly=json.loads((data/'gun-assembly.json').read_text(encoding='utf-8-sig'))
formulas=json.loads((data/'combat-weapon-formulas.json').read_text(encoding='utf-8-sig'))
config=dict(items={'ue_m249':items['ue_m249']},
    gunsmith=[x for x in guns['weapons'] if x.get('id')=='ue_m249'],
    machine_gun_traits=[dict(id=x['id'],traits=x.get('traits',[])) for x in guns['weapons'] if x.get('id') in ['ue_pkm_lowpoly','ue_lmg201']],
    classification={k:{f:items[k][f] for f in ['weaponType','weaponTypeTag']}for k in ['ue_m249','ue_pkm_lowpoly','ue_lmg201']},
    formulas={'ue_m249':formulas['ue_m249']},
    assembly=[x for x in assembly['recipes'] if x.get('output')=='ue_m249'])
write(out/'Integration/configuration-slices.json',config)

# Binary and pose geometry stay local. The inventory makes the dependency and
# license boundary explicit without publishing meshes, audio or user saves.
asset_root=root/'SourceAssets/M249Orpind20261107'
recipes=[]
for p in asset_root.rglob('*'):
    if not p.is_file():continue
    if p.suffix in {'.py','.ps1','.md','.hlsl'}:
        recipes.append(dict(path=p.relative_to(root).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
write(out/'authoring-manifest.json',recipes)
evidence=out/'Evidence';evidence.mkdir(exist_ok=True)
for folder,names in {
    'Feedback31':['install_receipt.json','saved_verification.json','runtime_verification.json','authoring.json'],
    'Review32':['input_hashes.json','audit.json'],
    'Insert30':['install_receipt.json','saved_comparison.json'],
    'Finish29':['install_receipt.json'],
    'Repair18':['install_receipt.json'],
}.items():
    for name in names:
        p=asset_root/folder/name
        if p.exists():(evidence/(folder+'_'+name)).write_bytes(p.read_bytes())
write(out/'package-status.json',dict(runtime_new_files=len(runtime),shared_hosts=len(sections),authoring_files=len(recipes),
    automatic_shared_host_patch=False,public_tree_built=False,binary_assets_published=False,
    local_runtime_unchanged=True,latest_offline_review='Review32: 20 cases; 5965 pose frames; gameplay/multiplayer not run',
    base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()))
print('M249 package:',len(runtime),'new runtime files;',len(sections),'shared host sections;',len(recipes),'authoring files')
