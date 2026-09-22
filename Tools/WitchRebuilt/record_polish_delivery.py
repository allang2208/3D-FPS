"""Read back only the edited candidate assets for the requested scoped inspection."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');DEST='/Game/Monsters/WitchRebuilt'
mesh=u.load_asset(DEST+'/SK_WitchRebuilt');clip=u.load_asset(DEST+'/Animations/A_WitchRebuilt_ThrowPoisonBottle')
cloth=mesh.get_editor_property('mesh_clothing_assets')
result={'cloth_assets':[c.get_name() for c in cloth],
    'materials':[{'slot':str(s.get_editor_property('imported_material_slot_name')),'material':s.material_interface.get_path_name()} for s in mesh.materials],
    'throw_duration':clip.get_editor_property('sequence_length'),
    'throw_import_sample_rate':clip.get_editor_property('asset_import_data').get_editor_property('custom_sample_rate'),
    'runtime_tested':False,'chaos_simulation_tested':False}
if len(cloth)!=1 or not cloth[0].get_name().startswith('WitchRebuilt_WaistDrapePolish02'):raise RuntimeError('Unexpected cloth revision: '+str(result['cloth_assets']))
(ROOT/'Polish20260922/ue_asset_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
report=json.loads((ROOT/'ue_delivery.json').read_text());report.update({
    'status':'Garment and throw polish imported and saved; authoring checks complete, gameplay and Chaos simulation pending user',
    'render_revision':'Connected outer robe, no second Solidify shell; skinned lining and sleeve-chain weights; independent softened fabric material',
    'editable_animation_scenes':'Geometry refreshed in 8 scenes; only ThrowPoisonBottle re-authored and reimported, other animation keys/exports retained',
    'polish_revision':{'date':'2026-09-22','cloth_asset':result['cloth_assets'][0],'throw_fps':60,'throw_duration':1.5,'throw_release':.75,
        'native_compile':'LiveCoding.CompileSync succeeded 2026-09-22 02:13:52 UTC; existing authoring function only',
        'regular_base_dll_rebuilt_this_revision':False,
        'source_checks':'Polish20260922/inspection_result.json','ue_asset_readback':'Polish20260922/ue_asset_result.json'},
    'runtime_tested':False,'visual_tested':False,'authoring_visual_inspected':True})
(ROOT/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'cloth':result['cloth_assets'],'throw_duration':result['throw_duration'],'sample_rate':result['throw_import_sample_rate'],'saved':True}))
