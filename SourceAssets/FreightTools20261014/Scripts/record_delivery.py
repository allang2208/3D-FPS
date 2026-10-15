"""Record saved production outputs; this does not open or test any model or game."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys
ROOT=Path(__file__).resolve().parents[1]
def read(path):return json.loads(path.read_text(encoding='utf8'))
models=read(ROOT/'model_manifest.json')
imported=read(ROOT/'Receipts/ue-import.json')
installed=read(ROOT/'Receipts/installation.json')
if models['stage']!='sources_and_exports_saved' or imported['stage']!='staged_assets_saved' or installed['stage']!='assets_installed':
    raise RuntimeError('Production stages are not yet complete')
result={'stage':'models_and_ue_assets_saved','timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'Model asset phase only','assets':[],'installed_package_count':len(installed['packages']),
        'native_code_changed':False,'interactive_editor_started':False,'preview_rendered':False,
        'visual_review_performed':False,'runtime_tested':False,'inventory_registered':False,
        'loot_tables_changed':False,'recipes_changed':False}
for key,m in models['assets'].items():
    ue=next(v for v in imported['meshes'] if v['item_id']==m['id'])
    result['assets'].append({'id':m['id'],'name':m['name'],'source':m['source'],'fbx':m['fbx'],'glb':m['glb'],
        'ue_mesh':ue['path'],'ue_material':ue['material'],'triangles_lod0':m['triangles_lod0'],
        'editable_parts':m['source_components'],'dimensions_cm':m['actual_dimensions_cm'],
        'collision_hulls':m['collision_hulls'],'textures':m['textures'],'texture_resolution':4096,
        'nanite':True,'fallback_geometry':'100 percent','texture_uv_channel':'SurfaceAtlas'})
if (ROOT/'presentation.json').exists():
    presentation=read(ROOT/'presentation.json')
    result['preview_rendered']=presentation.get('stage')=='views_and_icons_saved'
    result['visual_review_performed']='--visual-review' in sys.argv
    result['inventory_icons_prepared']=len(presentation.get('icons',[]))==3
    result['preview_boards']=presentation.get('boards',[])
    result['icons']=presentation.get('icons',[])
    icon_report={'stage':'icons_saved','renderer':'Blender Cycles','transparent':True,'inventory_registered':False,'icons':result['icons']}
    (ROOT/'inventory_icons.json').write_text(json.dumps(icon_report,ensure_ascii=False,indent=2),encoding='utf8')
(ROOT/'delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'stage':result['stage'],'models':len(result['assets']),'packages':result['installed_package_count'],
    'parts':sum(x['editable_parts'] for x in result['assets']),'triangles':sum(x['triangles_lod0'] for x in result['assets'])},ensure_ascii=False))
