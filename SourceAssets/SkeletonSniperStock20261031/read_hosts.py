import bpy,json
import numpy as np
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).resolve().parent;S=O.parent
sources={'M24':S/'M24ReloadFlow20261028/M24_ReloadFlow_Editable.blend','SVD':S/'SVDStockAdapter20260923/SVD_StockModular_Editable.blend','SVCH':S/'SVCHReplacement20261018/RealSights20261019/SVCH_RealFoldingSights_Editable.blend'}
report={}
for key,path in sources.items():
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE' and o.data.bones.get('WPN_root'))
    rig.data.pose_position='REST';root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local
    row=dict(source=str(path),rig=rig.name,root_world=list(map(list,root)),objects=[])
    for ob in bpy.data.objects:
        if ob.type!='MESH' or any(t in ob.name.lower() for t in ('arm','hand','manny')):continue
        vs=np.array([list(ob.matrix_world@v.co) for v in ob.data.vertices]);local=np.array([list(root.inverted()@ob.matrix_world@v.co) for v in ob.data.vertices])
        mats=[m.name if m else '' for m in ob.data.materials]
        row['objects'].append(dict(name=ob.name,vertices=len(vs),materials=mats,world_bounds=[vs.min(0).tolist(),vs.max(0).tolist()],root_bounds=[local.min(0).tolist(),local.max(0).tolist()]))
        if (key=='M24' and ob.name=='M24_base') or (key=='SVD' and 'Stock' in ob.name) or (key=='SVCH' and any('stock' in m.lower() for m in mats)):
            np.savez_compressed(O/'Inputs'/(key+'_'+ob.name+'.npz'),vertices=vs,root_vertices=local,faces=np.array([list(p.vertices) for p in ob.data.polygons],dtype=object),material_ids=np.array([p.material_index for p in ob.data.polygons]))
    report[key]=row
(O/'Inputs/hosts.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(O/'Original/Meshy_AI_Adjustable_Tactical_R_1031040412_texture.glb'))
ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');ob.name='SkeletonSniperStock_Meshy_Master'
for im in bpy.data.images:
    if im.name in ('normal','texture_0','texture_0_metallic_roughness'):im.filepath=str(O/'Textures'/(im.name+'.png'))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'SkeletonSniperStock_Meshy_Master.blend'))
print('HOST_AUTHORING_INPUTS_SAVED',flush=True)
