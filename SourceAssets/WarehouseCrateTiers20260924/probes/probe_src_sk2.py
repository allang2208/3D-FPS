import json, unreal as u
sm = u.load_asset('/Game/ColdSteelUI/Warehouse20260909/RitualV8/warehouse_chest_rigid/SkeletalMeshes/warehouse_chest_rigid')
out = {'sm_attrs': [x for x in dir(sm) if 'material' in x.lower() or 'slot' in x.lower() or 'bone' in x.lower() or 'skel' in x.lower()]}
ms = sm.get_editor_property('materials')
out['mat_count'] = len(ms)
out['mat0_attrs'] = [x for x in dir(ms[0]) if not x.startswith('_') and x not in ('assign','cast','copy','export_text','import_text','set_editor_properties','static_struct','to_dict','to_tuple','get_editor_property')]
rows=[]
for m in ms:
    row={}
    for att in ('material','slot_name','imported_material_slot_name','material_name','name'):
        try:
            v=m.get_editor_property(att); row[att]= (v.get_path_name() if hasattr(v,'get_path_name') else str(v))
        except Exception: pass
    rows.append(row)
out['rows']=rows
skel=sm.get_editor_property('skeleton')
out['skel']=skel.get_path_name()
out['skel_attrs']=[x for x in dir(skel) if 'bone' in x.lower()]
try: out['refbones']=[str(b) for b in skel.get_editor_property('bone_tree')]
except Exception as e: out['bt_err']=str(e)
open('D:/FPS3D/FPSGAME/SourceAssets/WarehouseCrateTiers20260924/probes/src_sk_slots2.json','w').write(json.dumps(out,indent=1))
