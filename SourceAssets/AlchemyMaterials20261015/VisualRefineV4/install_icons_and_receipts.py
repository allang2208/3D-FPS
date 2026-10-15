"""Publish the three saved revisions at existing item/icon identities."""
from pathlib import Path
from datetime import datetime,timezone
import json,shutil
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent;PROJECT=BASE.parents[1]
def read(p):return json.loads(p.read_text('utf-8-sig'))
def write(p,obj):
 target=ROOT/'Before/ActiveReceipts'/p.relative_to(BASE);target.parent.mkdir(parents=True,exist_ok=True)
 if p.exists() and not target.exists():shutil.copy2(p,target)
 p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n','utf8')
saved=read(ROOT/'Receipts/ue-import.json')
if saved['stage']!='assets_saved':raise RuntimeError('Save refined meshes in the main project first')
candidate=read(ROOT/'presentation.json');current=read(BASE/'presentation.json')
models=read(ROOT/'model_manifest.json');active_models=read(BASE/'model_manifest.json')
assets=read(BASE/'Receipts/ue-import.json');catalog=read(PROJECT/'Content/ColdSteelData/items.json')
for icon in candidate['icons']:
 identity=icon['id'];item=catalog[identity]
 source=ROOT/'Icons'/Path(icon['file']).name
 target=PROJECT/'Content/ColdSteelData'/item['ue_icon']
 if [item['grid_w'],item['grid_h']]!=[icon['grid_w'],icon['grid_h']]:raise RuntimeError('Preserve changed footprint '+identity)
 # Keep the stable paths already embedded in player/shared-inventory snapshots.
 shutil.copy2(source,target)
 icon['file']=str(target);icon['ue_icon']=item['ue_icon'];icon['inventory_registered']=True
 current['icons']=[icon if row['id']==identity else row for row in current['icons']]
 candidate['production_icons_preserved']=False
for key,model in models['assets'].items():
 model['active_authoring_recipe']=str(ROOT/'Scripts/author_models.py')
 model['active_material_recipe']=str(ROOT/'Scripts/import_assets.py')
 active_models['assets'][key]=model
active_models['active_visual_refinement']=str(ROOT/'delivery.json')
for mesh in saved['meshes']:
 assets['meshes']=[mesh if old['item_id']==mesh['item_id'] else old for old in assets['meshes']]
for field in ('materials','textures'):
 assets[field]=list(dict.fromkeys(assets[field]+saved[field]))
assets['active_visual_refinement']=str(ROOT/'Receipts/ue-import.json')
current['stage']='inventory_icons_saved';candidate['stage']='inventory_icons_installed'
write(BASE/'model_manifest.json',active_models);write(BASE/'presentation.json',current);write(BASE/'Receipts/ue-import.json',assets)
write(ROOT/'presentation.json',candidate)
delivery=dict(stage='refinement_assets_and_icons_installed',completed_utc=datetime.now(timezone.utc).isoformat(),
              item_ids=[i['id'] for i in candidate['icons']],meshes=saved['meshes'],materials=saved['materials'],icons=candidate['icons'],
              changes=['Clearer glass surfaces and sharper crystal facet normals','Wide labels sized for the actual package faces','Lower crystal-jar icon camera and controlled studio reflections'],
              stabilizer_grid=[1,2],stable_item_mesh_paths=True,stable_item_icon_paths=True,loot_changed=False,
              native_code_changed=False,new_native_build_required=False,tests_run=False,game_started=False,gui_editor_started=False)
write(ROOT/'delivery.json',delivery)
print('REFINEMENT_INSTALLED meshes=%d icons=%d'%(len(saved['meshes']),len(candidate['icons'])))
