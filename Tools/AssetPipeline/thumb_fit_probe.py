"""Read-only numerical probe of WRAD thumb fitting. No production writes."""
import importlib.util
import json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/ArmsRepair20260909/ThumbProbe'
OUT.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('repair',ROOT/'Tools/AssetPipeline/repair_arms_skinning.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets/ArmsRepair20260909/SK_ArmsRepair_anatomy.blend'))
target=bpy.data.objects['SK_AKM_Viewmodel']
sr,sm=mod.load_source_mesh()
report={}
for side in ('l','r'):
    sh,sb,sl,sw=mod.anatomical_frame(sr,side,True)
    th,tb,tl,tw=mod.anatomical_frame(target,side,False)
    sc=[mod.head(sr,f'finger_thumb{j}.{side}') for j in (1,2,3)]
    tc=[mod.head(target,f'thumb_0{j}_{side}') for j in (1,2,3)]
    sn=(sc[1]-sc[0]).cross(sc[0]-sh).normalized()
    tn=(tc[1]-tc[0]).cross(tc[0]-th).normalized()
    sy=(sc[1]-sc[0]).normalized();sx=sy.cross(sn).normalized();sz=sx.cross(sy).normalized()
    ty=(tc[1]-tc[0]).normalized();tx=ty.cross(tn).normalized();tz=tx.cross(ty).normalized()
    sbone=Matrix((sx,sy,sz)).transposed();tbone=Matrix((tx,ty,tz)).transposed()
    palm=tb@Matrix.Diagonal(Vector((tw/sw,tl/sl,tw/sw)))@sb.transposed()
    tscale=(tc[1]-tc[0]).length/(sc[1]-sc[0]).length
    thumb=tbone@sbone.transposed()*tscale
    palm_rotation=tb@sb.transposed()
    thumb_rotation=tbone@sbone.transposed()
    aligned_sn=sn if sn.dot(sb.col[2])>=0 else -sn
    aligned_tn=tn if tn.dot(tb.col[2])>=0 else -tn
    aligned_sx=sy.cross(aligned_sn).normalized();aligned_sz=aligned_sx.cross(sy).normalized()
    aligned_tx=ty.cross(aligned_tn).normalized();aligned_tz=aligned_tx.cross(ty).normalized()
    aligned_sbone=Matrix((aligned_sx,sy,aligned_sz)).transposed()
    aligned_tbone=Matrix((aligned_tx,ty,aligned_tz)).transposed()
    aligned_thumb_rotation=aligned_tbone@aligned_sbone.transposed()
    row={'source_matrix_world':list(map(list,sr.matrix_world)), 'target_matrix_world':list(map(list,target.matrix_world)),
        'source_palm':{'origin':list(sh),'length':sl,'width':sw,'basis':list(map(list,sb))},
        'target_palm':{'origin':list(th),'length':tl,'width':tw,'basis':list(map(list,tb))},
        'source_thumb':[list(p) for p in sc], 'target_thumb':[list(p) for p in tc],
        'source_thumb_normal_dot_palm':sn.dot(sb.col[2]),'target_thumb_normal_dot_palm':tn.dot(tb.col[2]),
        'relative_thumb_vs_palm_rotation_degrees':palm_rotation.rotation_difference(thumb_rotation).angle*180/3.141592653589793 if hasattr(palm_rotation,'rotation_difference') else palm_rotation.to_quaternion().rotation_difference(thumb_rotation.to_quaternion()).angle*180/3.141592653589793,
        'mapped_thumb_root_by_palm':list(th+palm@(sc[0]-sh)),
        'actual_thumb_root':list(tc[0]),
        'palm_thumb_root_gap':(th+palm@(sc[0]-sh)-tc[0]).length,
        'palm_scales':[tw/sw,tl/sl,tw/sw],'thumb_scale':tscale,
        'basis_determinants':[sb.determinant(),tb.determinant(),sbone.determinant(),tbone.determinant()],
        'hemisphere_corrected_relative_rotation_degrees':palm_rotation.to_quaternion().rotation_difference(aligned_thumb_rotation.to_quaternion()).angle*180/3.141592653589793,
        'half_weight_old_rotation_blend_singular_values':np.linalg.svd(np.array((palm_rotation+thumb_rotation)*.5),compute_uv=False).tolist(),
        'half_weight_corrected_rotation_blend_singular_values':np.linalg.svd(np.array((palm_rotation+aligned_thumb_rotation)*.5),compute_uv=False).tolist(),
        'pose_bones':{}}
    for clip,frame in [('idle',1),('reload',52),('reload_empty',75)]:
        mod.set_pose(target,clip,frame)
        row['pose_bones'][clip] = {f'thumb_0{j}_{side}':{'parent':target.pose.bones[f'thumb_0{j}_{side}'].parent.name,
            'local_euler':list(target.pose.bones[f'thumb_0{j}_{side}'].matrix_basis.to_euler()),
            'local_scale':list(target.pose.bones[f'thumb_0{j}_{side}'].matrix_basis.to_scale())} for j in (1,2,3)}
    report[side]=row
(OUT/'thumb_fit_probe.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('THUMB_FIT_PROBE_COMPLETE '+json.dumps(report))
