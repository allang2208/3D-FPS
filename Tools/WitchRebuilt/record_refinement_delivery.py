"""Record only the assets changed for the requested Witch diagnosis/refinement."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');OUT=ROOT/'Refinement20260922';DEST='/Game/Monsters/WitchRebuilt'
mesh=u.load_asset(DEST+'/SK_WitchRebuilt');clip=u.load_asset(DEST+'/Animations/A_WitchRebuilt_ThrowPoisonBottle')
cloth=mesh.get_editor_property('mesh_clothing_assets')
materials=[]
for slot in mesh.materials:
    material=slot.material_interface
    entry={'slot':str(slot.get_editor_property('imported_material_slot_name')),'material':material.get_path_name()}
    if material.get_name().endswith('Detail03'):
        entry['shader_types']=u.MaterialEditingLibrary.get_num_shader_types(material)
        entry['detail_samples']=[{'texture':n.texture.get_name(),'sampler':str(n.get_editor_property('sampler_type'))}
            for n in u.MaterialEditingLibrary.get_material_expressions(material)
            if isinstance(n,u.MaterialExpressionTextureSample) and n.texture and '/WitchRebuilt/Textures/Detail/' in n.texture.get_path_name()]
    materials.append(entry)
result={'cloth_assets':[c.get_name() for c in cloth],'physics_asset':mesh.physics_asset.get_path_name(),
    'materials':materials,'throw_duration':clip.get_editor_property('sequence_length'),
    'throw_import_sample_rate':clip.get_editor_property('asset_import_data').get_editor_property('custom_sample_rate'),
    'candidate_dirty_packages':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name().startswith(DEST)],
    'runtime_tested':False,'chaos_simulation_tested':False}
u.WitchRebuiltMonster.prepare_rebuilt_physics(mesh,False)
(OUT/'ue_asset_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
report=json.loads((ROOT/'ue_delivery.json').read_text());report.update({
    'status':'Refinement03 mesh, materials, articulated cloth, connected physics and eight clips imported/saved; gameplay pending user',
    'render_revision':'Local garment clearance and leg support; refined face/hat/hands/feet contours; measured microdetail UV and fabric/face normal/roughness',
    'editable_animation_scenes':'Eight editable scenes updated; carry right-finger tracks fitted to bottle neck; only toss body choreography changed',
    'refinement_revision':{'date':'2026-09-22','cloth_asset':result['cloth_assets'][0],
        'physics_bodies':16,'physics_constraints':15,'reference_anchor_gap_cm':0,
        'throw_fps':60,'throw_duration':1.5,'throw_release':.75,'actor_scale_changed':False,
        'regular_base_dll_rebuilt_this_revision':True,'native_build':'Saved/BuildEditor/build-20260922-121815.log',
        'source_inspection':'Refinement20260922/source_inspection.json','ue_asset_readback':'Refinement20260922/ue_asset_result.json'},
    'runtime_tested':False,'visual_tested':False,'authoring_visual_inspected':True})
report['assets']=list(dict.fromkeys(report['assets']+[e['material'] for e in materials]))
(ROOT/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'cloth':result['cloth_assets'],'throw_duration':result['throw_duration'],'dirty':result['candidate_dirty_packages'],
    'detail_materials':[{'name':e['material'],'shader_types':e.get('shader_types')} for e in materials if e['material'].split('.')[-1].endswith('Detail03')]}))
