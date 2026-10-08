"""Derive the three standard blade modules from the continuous current blade."""
import json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

P=Path(__file__).resolve().parent;S=P.parent/'BladeV3';OUT=P/'Export'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(S/'XuanChi_BladeV3_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
factory=bpy.data.objects['SM_XuanChi_Blade_V3']
variants={
    'extended_edge':{'name':'延锋刃','width':1.,'thickness':1.,'extension_m':.18,'rune_dimensions_cm':[11,2,126]},
    'heavy_spine':{'name':'重脊刃','width':1.18,'thickness':1.50,'extension_m':0.,'rune_dimensions_cm':[12.98,2,108]},
    'feather_edge':{'name':'轻羽刃','width':.80,'thickness':.78,'extension_m':0.,'rune_dimensions_cm':[8.8,2,108]}}
def smooth(t):
    t=np.clip(t,0.,1.);return t*t*t*(t*(t*6.-15.)+10.)
def deform(points,spec):
    q=points.copy();z=points[:,2]
    # The complete buried root and ornament contact zone remain identical.
    shoulder=smooth((z-.18)/.14)
    q[:,0]*=1+(spec['width']-1)*shoulder
    q[:,1]*=1+(spec['thickness']-1)*shoulder
    # Add the extra middle length gradually, then translate the original tip
    # intact, retaining its edge and point taper instead of stretching it.
    q[:,2]+=spec['extension_m']*smooth((z-.18)/.86)
    return q

records=[]
for option,spec in variants.items():
    obj=factory.copy();obj.data=factory.data.copy()
    obj.name='SM_XuanChi_Blade_'+option+'_V1';obj.data.name=obj.name
    scene.collection.objects.link(obj);obj.hide_set(False);obj.hide_render=False
    mesh=obj.data
    points=np.array([tuple(v.co) for v in mesh.vertices],dtype=np.float64)
    source_normals=np.array([tuple(n.vector) for n in mesh.corner_normals],dtype=np.float64)
    jac=np.empty((len(points),3,3));eps=1.e-6
    for axis in range(3):
        step=np.zeros(3);step[axis]=eps
        jac[:,:,axis]=(deform(points+step,spec)-deform(points-step,spec))/(2*eps)
    normal_matrix=np.linalg.inv(jac).transpose(0,2,1)
    indices=np.array([loop.vertex_index for loop in mesh.loops])
    normals=np.einsum('nij,nj->ni',normal_matrix[indices],source_normals)
    normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1.e-12)
    mesh.vertices.foreach_set('co',deform(points,spec).astype(np.float32).ravel())
    for face in mesh.polygons:face.use_smooth=True
    mesh.update();mesh.normals_split_custom_set(normals.tolist())
    obj['option_id']=option;obj['root_unchanged_through_cm']=18.
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,
        object_types={'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    mesh.calc_loop_triangles()
    records.append({'option':option,'mesh':obj.name,'label':spec['name'],
        'visual_tip_cm':120+100*spec['extension_m'],'body_thickness_mm':8*spec['thickness'],
        'width_multiplier':spec['width'],'rune_dimensions_cm':spec['rune_dimensions_cm'],
        'source_triangles':len(mesh.loop_triangles),'interface':'xuanchi_hilt_v1',
        'trace_tip_cm':[0,0,120],'trace_note':'Range modifier is applied by the existing combat path; do not apply it a second time to the catalog trace point'})
    obj.hide_render=True;obj.hide_set(True)

factory.hide_set(False);factory.hide_render=False
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'XuanChi_CommonBlades_Editable.blend'))
receipt={'source':str(S/'XuanChi_BladeV3_Editable.blend'),'options':records,
    'material':'/Game/Weapons/XuanChiZhenYue20261004/BladeV3/Materials/M_XuanChi_SteelRelief_V3',
    'root_preserved_cm':[-1.8,18],'transition_cm':[18,32],
    'surface':'Reuse current silver BaseColor, ORM, Normal and bounded POM; original UV and split-normal boundaries retained',
    'hilt_and_grip_mount':'unchanged; retains latest 4.5 cm relative grip adjustment',
    'tests_run':False,'acceptance_render_run':False}
(P/'exports.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('XUANCHI_COMMON_BLADES_EXPORTED '+json.dumps(records,ensure_ascii=False),flush=True)
