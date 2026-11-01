"""Record completed production stages from their build and import receipts."""
from pathlib import Path
import json,datetime
P=Path(__file__).resolve().parent
build_file=max(P.glob('build-*-receipt.json'),key=lambda p:p.stat().st_mtime)
build=json.loads(build_file.read_text(encoding='utf-8-sig'))
imported=json.loads((P/'import_receipt.json').read_text(encoding='utf-8-sig'))
model=json.loads((P/'model_manifest.json').read_text(encoding='utf-8-sig'))
delivery={
 'id':'zhen_ting_pommel','name':'震霆配重','weapon':'ue_thunder_god_hammer','slot':'pommel','tier':'special',
 'finished':datetime.datetime.now().astimezone().isoformat(),
 'concept':'../ZhenTingPommelConceptV1/zhen_ting_pommel_concept_v1.png',
 'editable':'ZhenTingPommelV1_Editable.blend','fbx':'Export/'+model['mesh']+'.fbx',
 'geometry_triangles':model['triangles'],'normal_map':'Textures/T_ZhenTing_MetalNormal.png',
 'icon':'zhen_ting_pommel_icon.png','icon_source':'zhen_ting_pommel_model_icon_source.png',
 'editor_build':build,'build_receipt':build_file.name,
 'saved_assets':imported.get('saved_assets',[]),'assets_saved':bool(imported.get('complete')),
 'catalog_published':bool(imported.get('catalog_published')),
 'complete':build['exit_code']==0 and bool(imported.get('complete')),
 'heavy_charge_speed_bonus':.30,'additional_lightning_count':3,'radius_cm':300,'spacing_cm':600,
 'guan_lei_horizontal_range_mult':1.5,
 'damage':'Normal/GuanLei extra waves: native lightning magic only. JiLei extra waves: existing JiLei heavy magic receipt. Original impact unchanged.',
 'gameplay_tested':False,'multiplayer_tested':False,'editor_gui_started_by_task':False,
 'notes':'Production assets and DLL saved. No gameplay, audit, visual acceptance or performance test was run.'}
(P/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'complete':delivery['complete'],'saved_assets':len(delivery['saved_assets']),'build_exit_code':build['exit_code']},ensure_ascii=False))
