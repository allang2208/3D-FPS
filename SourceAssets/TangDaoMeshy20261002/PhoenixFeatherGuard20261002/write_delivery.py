"""Record actual saved assets and binary status; this does not run game checks."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
m=json.loads((P/'guard_manifest.json').read_text(encoding='utf-8'))
r=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
b=json.loads((P/'build_receipt.json').read_text(encoding='utf-8-sig'))
if not r.get('complete'):raise RuntimeError('Finish actual asset saving before delivery')
d={'weapon':m['weapon'],'slot':m['slot'],'option':m['id'],'name':m['name'],
   'complete':bool(r['complete'] and b.get('complete')),'source_created':True,'assets_saved':r['complete'],
   'native_editor_built':b.get('editor_built',False),'native_game_built':b.get('game_built',False),
   'source_blend':'TangDao_PhoenixFeatherGuard_Editable.blend','export_fbx':'Export/'+m['mesh_name']+'.fbx',
   'export_glb':'Export/'+m['mesh_name']+'.glb','mesh':r['mesh'],'saved_assets':r['assets'],
   'lod_triangles_saved':r['lod_triangles_saved'],'materials':r['materials'],'texture_resolution':m['texture_resolution'],
   'plate_width_cm':m['plate_width_cm'],'plate_height_cm':m['plate_height_cm'],'relief_height_mm':m['relief_height_mm'],
   'gemstones_per_side':m['gemstones_per_side'],'front_blade_seat_z_cm':1.4,'rear_grip_seat_z_cm':-5.,
   'gold_card_identity':'ue_tang_dao / guard / phoenix_feather','stats':{},'features':m['features'],
   'editor_launched':False,'game_launched':False,'runtime_tested':False,'acceptance_rendered':False,
   'icon_production_rendered':True,'previous_guard_preserved':True,'native_blade_runes_unchanged':True,
   'reimport_hooks_installed':True,'reference_backside':'inferred from visible phoenix/cloud ornament',
   'installation_cap_uv_repaired':True,'engine_import_messages':['Some near-zero tangents and binormals remain in the final import log'],
   'surface_visual_acceptance':'not run; user testing'}
(P/'delivery.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PHOENIX_GUARD_DELIVERY_RECORDED complete='+str(d['complete']),flush=True)
