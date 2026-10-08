"""Derive three fitted ornate guards; retain the central interface and native UVs."""
import json
from pathlib import Path
import bpy
import numpy as np

P=Path(__file__).resolve().parent
OUT=P/'Export';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'BladeV3/XuanChi_BladeV3_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
factory=bpy.data.objects['SM_XuanChi_Guard_V3']
variants={
    'bastion_guard':{'name':'壁垒护手','reach':.026,'lift':.005,'thickness':1.35,
        'appearance':'宽翼厚铜护手 · 保留云螭浮雕与中央玉饰'},
    'riposte_guard':{'name':'反击护手','reach':.010,'lift':.022,'thickness':1.08,
        'appearance':'上挑云钩双翼 · 保留云螭浮雕与中央玉饰'},
    'light_guard':{'name':'轻量护手','reach':-.012,'lift':.004,'thickness':.72,
        'appearance':'收翼薄铜护手 · 保留云螭浮雕与中央玉饰'}}

def smooth(t):
    t=np.clip(t,0,1);return t*t*t*(t*(t*6-15)+10)

def deform(points,spec):
    q=points.copy();w=smooth((np.abs(points[:,0])-.045)/.055)
    q[:,0]+=np.sign(points[:,0])*spec['reach']*w
    q[:,1]*=1+(spec['thickness']-1)*w
    q[:,2]+=spec['lift']*w
    return q

rows=[]
for option,spec in variants.items():
    obj=factory.copy();obj.data=factory.data.copy()
    obj.name='SM_XuanChi_Guard_'+option+'_V1';obj.data.name=obj.name
    bpy.context.scene.collection.objects.link(obj)
    obj.hide_set(False);obj.hide_render=False
    mesh=obj.data;points=np.array([tuple(v.co) for v in mesh.vertices],dtype=np.float64)
    normals=np.array([tuple(n.vector) for n in mesh.corner_normals],dtype=np.float64)
    jac=np.empty((len(points),3,3));eps=1.e-6
    for axis in range(3):
        step=np.zeros(3);step[axis]=eps
        jac[:,:,axis]=(deform(points+step,spec)-deform(points-step,spec))/(2*eps)
    matrices=np.linalg.inv(jac).transpose(0,2,1)
    indices=np.array([l.vertex_index for l in mesh.loops])
    normals=np.einsum('nij,nj->ni',matrices[indices],normals)
    normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1.e-12)
    mesh.vertices.foreach_set('co',deform(points,spec).astype(np.float32).ravel())
    mesh.update();mesh.normals_split_custom_set(normals.tolist())
    obj['option_id']=option;obj['unchanged_center_half_width_cm']=4.5
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,
        object_types={'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
    mesh.calc_loop_triangles()
    rows.append(dict(option=option,mesh=obj.name,label=spec['name'],appearance=spec['appearance'],
        source_triangles=len(mesh.loop_triangles),interface='xuanchi_hilt_v1',
        outer_wing_reach_delta_cm=100*spec['reach'],outer_wing_lift_cm=100*spec['lift'],
        outer_wing_thickness_multiplier=spec['thickness']))
    obj.hide_render=True;obj.hide_set(True)
factory.hide_set(False);factory.hide_render=False
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'XuanChi_CommonGuards_Editable.blend'))
(P/'exports.json').write_text(json.dumps({
    'source':'../BladeV3/XuanChi_BladeV3_Editable.blend','options':rows,
    'unchanged_center_half_width_cm':4.5,'wing_transition_cm':[4.5,10.0],
    'surface':'Retained native UV, split-normal boundaries, bright copper/jade PBR and silver buried return lip',
    'mount':'Retain the current 4.5 cm grip correction',
    'game_tested':False,'acceptance_render_run':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('XUANCHI_COMMON_GUARDS_EXPORTED',len(rows),flush=True)
