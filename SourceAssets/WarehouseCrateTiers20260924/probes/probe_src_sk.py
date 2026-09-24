import json, unreal as u
sm = u.load_asset('/Game/ColdSteelUI/Warehouse20260909/RitualV8/warehouse_chest_rigid/SkeletalMeshes/warehouse_chest_rigid')
out = {}
out['class'] = sm.get_class().get_name()
try:
    out['num_lods'] = sm.get_editor_property('num_lods')
except Exception as e: out['lod_err']=str(e)
# rendered materials per LOD
mats = []
try:
    rl = sm.get_editor_property('rendered_materials')
    for lod in rl:
        mats.append([str(m.get_editor_property('material').get_path_name()) if m and m.get_editor_property('material') else None for m in (lod or [])])
except Exception as e:
    out['rendered_err'] = str(e)
out['rendered_materials'] = mats
# skeletal_material_slots (FSkeletalMaterialSlot? names)
for attr in ('skeletal_material_slots','materials','material_slots'):
    try:
        v = getattr(sm, 'get_editor_property')(attr)
        out[attr] = [{'name': str(x.get_editor_property('imported_material_slot_name')), 'idx': x.get_editor_property('material_index'),
                      'mat': (x.get_editor_property('material').get_path_name() if x.get_editor_property('material') else None)} for x in (v or [])]
        out['_used']=attr
        break
    except Exception as e:
        out[attr+'_err']=str(e)
open('D:/FPS3D/FPSGAME/SourceAssets/WarehouseCrateTiers20260924/probes/src_sk_slots.json','w').write(json.dumps(out, indent=1))
