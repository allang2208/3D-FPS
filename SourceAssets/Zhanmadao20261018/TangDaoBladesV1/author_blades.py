"""Fit the existing TangDao blade masters to the Zhanmadao seat and length."""
import bpy, json
import numpy as np
from pathlib import Path
from mathutils import Matrix

P=Path(__file__).resolve().parent
ROOT=P.parents[2]
OUT=P/'Export';OUT.mkdir(parents=True,exist_ok=True)
T=ROOT/'SourceAssets/TangDaoMeshy20261002'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'Zhanmadao_Modular_Editable.blend'))
base=bpy.data.objects['SM_Zhanmadao_Blade_V1']
points=np.asarray([tuple(v.co) for v in base.data.vertices])
seat_z=float(points[:,2].min())
seat=points[points[:,2]<seat_z+2e-6,:2]
target_center=(seat.min(axis=0)+seat.max(axis=0))*.5
target_size=(seat.max(axis=0)-seat.min(axis=0))*.98
tip_z=float(points[:,2].max())
rows=[]
for option,folder,blend in [
    ('yanling_edge','YanlingBlade20261002','TangDao_YanlingBlade_Editable.blend'),
    ('tengyun_dragon','TengyunBlade20261002','TangDao_TengyunBlade_Editable.blend')]:
    prefix='SM_TangDao_Blade_'+option
    source=T/folder/blend
    with bpy.data.libraries.load(str(source),link=False) as (available,loaded):
        loaded.objects=[name for name in available.objects if name.startswith(prefix+'_LOD') and name[-1:].isdigit()]
    lods=sorted(loaded.objects,key=lambda o:o.name)
    name='SM_Zhanmadao_Blade_'+option+'_V1'
    group=bpy.data.objects.new(name+'_LODGroup',None);group['fbx_type']='LodGroup'
    bpy.context.scene.collection.objects.link(group)
    original=np.asarray([tuple(v.co) for v in lods[0].data.vertices])
    lower=float(original[:,2].min());upper=float(original[:,2].max())
    source_seat=-original[original[:,2]<lower+.0002,:2]
    source_center=(source_seat.min(axis=0)+source_seat.max(axis=0))*.5
    source_size=source_seat.max(axis=0)-source_seat.min(axis=0)
    seat_scale=target_size/source_size
    mounted_base=seat_z-.0006
    length_scale=(tip_z-mounted_base)/(upper-lower)
    def deform(p):
        q=p.copy();q[:,:2]*=-1 # TangDao's approved 180-degree holding direction.
        q[:,2]=mounted_base+(p[:,2]-lower)*length_scale
        t=np.clip((q[:,2]-mounted_base)/.06,0,1)
        weight=(1-t*t*t*(t*(t*6-15)+10))[:,None]
        fitted=(q[:,:2]-source_center)*seat_scale+target_center
        q[:,:2]+=weight*(fitted-q[:,:2])
        return q
    counts=[]
    for level,obj in enumerate(lods):
        bpy.context.scene.collection.objects.link(obj)
        obj.parent=group;obj.matrix_parent_inverse=Matrix.Identity(4);obj.matrix_basis=Matrix.Identity(4)
        obj.name=name+'_LOD'+str(level);obj.data.name=obj.name
        mesh=obj.data;p=np.asarray([tuple(v.co) for v in mesh.vertices])
        normals=np.asarray([tuple(n.vector) for n in mesh.corner_normals])
        jac=np.empty((len(p),3,3));eps=1e-6
        for axis in range(3):
            delta=np.zeros(3);delta[axis]=eps
            jac[:,:,axis]=(deform(p+delta)-deform(p-delta))/(2*eps)
        indices=np.asarray([loop.vertex_index for loop in mesh.loops])
        normal_matrices=np.linalg.inv(jac).transpose(0,2,1)
        normals=np.einsum('nij,nj->ni',normal_matrices[indices],normals)
        normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
        mesh.vertices.foreach_set('co',deform(p).astype(np.float32).ravel());mesh.update()
        mesh.normals_split_custom_set(normals.tolist())
        mesh.calc_loop_triangles();counts.append(len(mesh.loop_triangles))
    bpy.ops.object.select_all(action='DESELECT');group.select_set(True)
    for obj in lods:obj.hide_set(False);obj.select_set(True)
    bpy.context.view_layer.objects.active=lods[0]
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,
        object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    transformed=deform(original)
    tip=transformed[transformed[:,2]>tip_z-2e-6].mean(axis=0)*100
    rows.append({'id':option,'mesh_name':name,'source':str(source),
        'lod_triangles':counts,'longitudinal_scale':length_scale,'rotation_about_z_deg':180,
        'seat_overlap_mm':.6,'seat_size_cm':(target_size*100).tolist(),
        'seat_scale_xy':seat_scale.tolist(),'root_transition_cm':6,
        'trace_base_cm':[float(target_center[0]*100),float(target_center[1]*100),seat_z*100],
        'trace_tip_cm':tip.tolist(),'rune_dimensions_cm':[14,12,tip_z*100],
        'material_slots':[m.name for m in lods[0].data.materials]})
    for obj in lods:obj.hide_render=True;obj.hide_set(True)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Zhanmadao_TangDaoBlades_Editable.blend'))
(P/'blade_exports.json').write_text(json.dumps({'weapon':'ue_zhanmadao','options':rows,
    'game_tested':False,'policy':'Existing LOD topology and UV retained; fitted root, rotated blade and extended length only'},
    ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ZHANMADAO_TANGDAO_BLADES_EXPORTED',flush=True)
