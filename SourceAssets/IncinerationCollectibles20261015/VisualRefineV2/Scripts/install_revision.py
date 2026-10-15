"""Install fresh UE packages at stable mesh identities, then publish their matching icons."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent;PROJECT=ROOT.parents[2]
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def preserve(p):
    dest=ROOT/'Before/Main'/p.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True)
    if p.exists() and not dest.exists():shutil.copy2(p,dest)
    return dest
def save(p,value):
    preserve(p);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assets=read(ROOT/'Receipts/ue-import.json');icons=read(ROOT/'presentation.json');models=read(ROOT/'model_manifest.json')
if assets['stage']!='staged_assets_saved' or icons['stage']!='inventory_icons_saved':raise RuntimeError('Complete asset save and matching icons first')
expected=read(ROOT/'Before/original-mesh-hashes.json')
for rel,digest in expected.items():
    p=PROJECT/rel
    if not p.exists() or sha(p)!=digest:raise RuntimeError('Preserve concurrent mesh revision: '+rel)
source=ROOT/'UEImportHost/Content/Items/IncinerationCollectibles20261015'
files=sorted(p for p in source.rglob('*') if p.suffix in ('.uasset','.uexp','.ubulk'))
plans=[]
for p in files:
    target=PROJECT/'Content/Items/IncinerationCollectibles20261015'/p.relative_to(source)
    if target.exists() and str(target.relative_to(PROJECT)) not in expected:raise RuntimeError('Preserve existing new-revision package: '+str(target))
    plans.append((p,target))
for p,target in plans:
    preserve(target);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
installed=dict(stage='assets_installed',stable_mesh_paths=True,new_material_path='/Game/Items/IncinerationCollectibles20261015/V2',
    packages=[dict(path=str(t),sha256=sha(t)) for _,t in plans],completed_utc=datetime.now(timezone.utc).isoformat())
save(ROOT/'Receipts/installation.json',installed)
catalog=read(PROJECT/'Content/ColdSteelData/items.json')
for row in icons['icons']:
    item=catalog[row['id']]
    if [item['grid_w'],item['grid_h']]!=[row['grid_w'],row['grid_h']]:raise RuntimeError('Preserve changed inventory footprint')
    target=PROJECT/'Content/ColdSteelData'/item['ue_icon'];preserve(target);shutil.copy2(row['file'],target)
    row['inventory_registered']=True
    row['ue_icon']=item['ue_icon']
for key,row in models['assets'].items():
    row['active_authoring_recipe']=str(ROOT/'Scripts/author_models.py')
    row['active_material_recipe']=str(ROOT/'Scripts/prepare_surfaces.py')
models['active_visual_revision']='VisualRefineV2';icons['active_visual_revision']='VisualRefineV2'
save(BASE/'model_manifest.json',models);save(BASE/'presentation.json',icons);save(ROOT/'presentation.json',icons)
save(BASE/'Receipts/ue-import.json',assets)
p=PROJECT/'Config/DefaultGame.ini';raw=p.read_text('utf-8-sig');entry='+DirectoriesToAlwaysCook=(Path="/Game/Items/IncinerationCollectibles20261015/V2")'
if entry not in raw:
    preserve(p);p.write_text(raw.replace('[/Script/UnrealEd.ProjectPackagingSettings]','[/Script/UnrealEd.ProjectPackagingSettings]\n'+entry,1),encoding='utf-8')
report=dict(stage='visual_refinement_installed',completed_utc=datetime.now(timezone.utc).isoformat(),
    items=[row['id'] for row in models['assets'].values()],ue_assets=assets['meshes'],
    icons=icons['icons'],stable_item_mesh_paths=True,stable_item_icon_paths=True,inventory_footprints_changed=False,
    native_code_changed=False,native_build_required=False,loot_changed=False,rarities_or_prices_changed=False,
    gui_editor_launched=False,game_run=False,multiplayer_tested=False,
    requested_visual_review='Receipts/visual-review.json')
save(ROOT/'delivery.json',report)
active=read(BASE/'delivery.json');active['active_visual_revision']=str(ROOT/'delivery.json');active['active_artifact_source']=str(ROOT/'model_manifest.json')
for row in active.get('items',[]):
    current=next((m for m in models['assets'].values() if m['id']==row['id']),None)
    if current:row['triangles']=current['triangles_lod0']
active['active_asset_installation']=str(ROOT/'Receipts/installation.json')
active['requested_visual_review']=str(ROOT/'Receipts/visual-review.json')
save(BASE/'delivery.json',active)
print('DETAIL_REVISION_INSTALLED',len(plans),len(icons['icons']))
