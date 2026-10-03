"""Record completed production/save/build outputs; do not run acceptance tests."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
m=json.loads((P/'guard_manifest.json').read_text(encoding='utf-8'))
r=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
builds={key:{'target':target,'result':'Succeeded','log':str(P/log)} for key,target,log in
 [('editor','FPSGAMEEditor Win64 Development','build-editor-console.log'),('game','FPSGAME Win64 Development','build-game-console.log')]}
d={'weapon':'ue_tang_dao','slot':'guard','option':m['id'],'name':m['name'],'complete':r['complete'],
 'source_blend':'TangDao_XuanCloudGuard_Editable.blend','source_fbx':'Export/'+m['mesh_name']+'.fbx',
 'source_glb':'Export/'+m['mesh_name']+'.glb','textures':{'resolution':4096,'maps':['BaseColor','ORM','Normal'],'height_source':'Textures/TangDao_XuanCloudGuard_Height16.png'},
 'saved_assets':r['assets'],'mesh':r['mesh'],'lod_triangles_saved':r['lod_triangles_saved'],
 'interface':m['interface'],'location_cm':m['location_cm'],'rotation_deg':m['rotation_deg'],
 'appearance':m['features'],'stats':{},'gold_card_identity':['ue_tang_dao','guard','xuan_cloud_dragon'],
 'catalog_receipt':'catalog_receipt.json','import_receipt':'import_receipt.json','builds':builds,
 'backend_import':'UnrealEditor-Cmd Python asset batch using bridge port 8000 mutex',
 'editor_launched':False,'game_launched':False,'runtime_tested':False,
 'reference_limit':'Only supplied front/oblique reference; reverse ornament uses the same dragon/cloud composition with a fitted rear collar.',
 'native_blade_runes_unchanged':True}
(P/'delivery.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('XUAN_CLOUD_GUARD_DELIVERED '+str(len(r['assets']))+' saved assets',flush=True)
