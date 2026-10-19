"""Fit the standard blade/guard variants and shared pommel interfaces to this dao."""
import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;O=P/'Export';O.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'Zhanmadao_Modular_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
base=json.loads((P.parent/'exports.json').read_text(encoding='utf-8'))
rows=[];adapters=[]
def smooth(t):
    t=np.clip(t,0.,1.);return t*t*t*(t*(t*6.-15.)+10.)
def export(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
    loc=obj.location.copy();obj.location=Vector()
    bpy.ops.export_scene.fbx(filepath=str(O/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    obj.location=loc
specs={
 'blade_1':{
  'extended_edge':dict(width=1.,thickness=1.,extension=.18,appearance='延展刀身中段与长锋，保留原装刀根和弯曲刀尖'),
  'heavy_spine':dict(width=1.18,thickness=1.5,extension=0.,appearance='宽肩厚脊，保留原装刀根与单侧刃线'),
  'feather_edge':dict(width=.8,thickness=.78,extension=0.,appearance='收窄轻薄刀身，保留微弧刀尖与连续刀根')},
 'guard':{
  'bastion_guard':dict(reach=.020,lift=.004,thickness=1.35,appearance='加宽加厚两翼，保留原厂刀座及柄口'),
  'riposte_guard':dict(reach=.009,lift=.017,thickness=1.08,appearance='上挑护翼，保留原厂刀座及柄口'),
  'light_guard':dict(reach=-.009,lift=.002,thickness=.72,appearance='收束轻薄护翼，保留原厂刀座及柄口')}}
for slot,options in specs.items():
    label='Blade' if slot=='blade_1' else 'Guard'
    factory=bpy.data.objects['SM_Zhanmadao_'+label+'_V1']
    for option,spec in options.items():
        obj=factory.copy();obj.data=factory.data.copy();obj.name='SM_Zhanmadao_'+label+'_'+option+'_V2';obj.data.name=obj.name
        scene.collection.objects.link(obj);mesh=obj.data
        pts=np.array([tuple(v.co) for v in mesh.vertices],dtype=np.float64)
        source_normals=np.array([tuple(n.vector) for n in mesh.corner_normals],dtype=np.float64)
        def deform(points):
            q=points.copy();z=points[:,2]
            if slot=='blade_1':
                shoulder=smooth((z-.15)/.14)
                q[:,0]*=1+(spec['width']-1)*shoulder;q[:,1]*=1+(spec['thickness']-1)*shoulder
                q[:,2]+=spec['extension']*smooth((z-.18)/.86)
            else:
                lo=base['cuts_z_cm']['guard_grip']/100;hi=base['cuts_z_cm']['blade_guard']/100
                w=smooth((np.abs(points[:,0])-.028)/.026)*smooth((z-lo)/.008)*smooth((hi-z)/.035)
                q[:,0]+=np.sign(points[:,0])*spec['reach']*w
                q[:,1]*=1+(spec['thickness']-1)*w;q[:,2]+=spec['lift']*w
            return q
        jac=np.empty((len(pts),3,3));eps=1e-6
        for axis in range(3):
            delta=np.zeros(3);delta[axis]=eps;jac[:,:,axis]=(deform(pts+delta)-deform(pts-delta))/(2*eps)
        matrices=np.linalg.inv(jac).transpose(0,2,1);indices=np.array([l.vertex_index for l in mesh.loops])
        normals=np.einsum('nij,nj->ni',matrices[indices],source_normals)
        normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
        mesh.vertices.foreach_set('co',deform(pts).astype(np.float32).ravel());mesh.update()
        mesh.normals_split_custom_set(normals.tolist());export(obj)
        rows.append({'slot':slot,'option':option,'mesh':obj.name,'appearance':spec['appearance'],
                     'material_slots':[m.name for m in mesh.materials],
                     'rune_dimensions_cm':[8*spec.get('width',1),3,base['blade_tip_cm']+100*spec.get('extension',0)]})
        obj.hide_render=True;obj.hide_set(True)

# The adapter upper rim is the dao's actual lower grip cut. Its lower rim uses
# the two established shared pommel interface radii, in their catalog scales.
grip=bpy.data.objects['SM_Zhanmadao_Grip_V1'];end=min(v.co.z for v in grip.data.vertices)
unique={tuple(round(float(c),7) for c in v.co):v.co.copy() for v in grip.data.vertices if abs(v.co.z-end)<2e-6}
ring=sorted(unique.values(),key=lambda p:math.atan2(p.y,p.x));N=len(ring)
steel=bpy.data.materials.get('M_SharedGrip_Steel') or bpy.data.materials.new('M_SharedGrip_Steel');steel.use_nodes=True
bs=next(n for n in steel.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Metallic'].default_value=1;bs.inputs['Roughness'].default_value=.35
for interface,radius,scale in [('shared_sword_pommel_v1',.012*.9,.9),('frost_hilt_v1',.017,1.)]:
    verts=[];faces=[];depth=.008
    for t in [0,.2,.5,.8,1]:
        blend=t*t*(3-2*t)
        for p in ring:
            a=math.atan2(p.y,p.x);target=Vector((math.cos(a)*radius,math.sin(a)*radius,0))
            v=Vector((p.x,p.y,0)).lerp(target,blend);v.z=-depth*t;verts.append(v)
    for j in range(4):
        for i in range(N):faces.append((j*N+i,(j+1)*N+i,(j+1)*N+(i+1)%N,j*N+(i+1)%N))
    faces.extend([tuple(range(N)),tuple(reversed(range(4*N,5*N)))])
    name='SM_Zhanmadao_Adapter_'+interface+'_V2';mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.materials.append(steel);mesh.update()
    uv=mesh.uv_layers.new(name='UVMap')
    for face in mesh.polygons:
        face.use_smooth=len(face.vertices)==4
        for li in face.loop_indices:
            v=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(math.atan2(v.y,v.x)/math.tau+.5,-v.z/depth)
    obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj);export(obj)
    adapters.append({'interface':interface,'mesh':name,'depth_cm':depth*100,'scale':scale,
        'mount_cm':[0,0,base['cuts_z_cm']['grip_pommel']],'material_slots':['M_SharedGrip_Steel']})
    obj.hide_render=True;obj.hide_set(True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'Zhanmadao_CommonVariants_Editable.blend'))
(P/'variant_exports.json').write_text(json.dumps({'options':rows,'adapters':adapters,'game_tested':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ZHANMADAO_COMMON_VARIANTS_EXPORTED',flush=True)
