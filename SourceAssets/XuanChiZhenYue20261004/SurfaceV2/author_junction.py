"""Morph the actual collar section into the blade section with shared planar UV."""
import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;S=P.parent/'ModelV1';O=P/'Export';O.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(S/'XuanChi_Modular_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
guard=bpy.data.objects['SM_XuanChi_Guard'];old=guard.data
coords=np.array([tuple(v.co) for v in old.vertices]);z=coords[:,2];join=float(z.max())
upper=z>.10
stations=np.linspace(.10,join,32)
ws=[];hs=[]
for h in stations:
    q=coords[np.abs(z-h)<.003]
    ws.append(max(.035,float(np.max(np.abs(q[:,0])))) if len(q) else .04)
    hs.append(max(.0045,float(np.max(np.abs(q[:,1])))) if len(q) else .006)
def deform(p):
    result=p.copy();zz=p[:,2];a=np.clip((zz-.103)/(.151-.103),0,1);a=a*a*(3-2*a)
    halfw=np.interp(zz,stations,ws);xx=np.clip(p[:,0]/halfw,-1,1)*.040
    ax=np.abs(xx)/.04
    yy=np.where(ax<=.72,1-ax*(.4/.72),.6*(1-ax)/.28)*.0045*np.sign(p[:,1])
    result[:,0]=p[:,0]*(1-a)+xx*a;result[:,1]=p[:,1]*(1-a)+yy*a
    return result
new=deform(coords)
normals=np.array([tuple(v.vector) for v in old.corner_normals]);loopvi=np.array([l.vertex_index for l in old.loops])
eps=1e-6;J=np.zeros((len(coords),3,3))
for k in range(3):
    delta=np.zeros(3);delta[k]=eps;J[:,:,k]=(deform(coords+delta)-deform(coords-delta))/(2*eps)
transformed=np.einsum('nij,nj->ni',np.linalg.pinv(J).transpose(0,2,1)[loopvi],normals)
transformed/=np.maximum(np.linalg.norm(transformed,axis=1,keepdims=True),1.e-9)
for f in old.polygons:
    for li in f.loop_indices:
        vi=old.loops[li].vertex_index;co=new[vi]
        if co[2]<.145:continue
        if all(abs(coords[k,2]-join)<1.e-6 for k in f.vertices):target=np.array([0.,0.,1.])
        else:
            slope=.0045*(.4/(.72*.04) if abs(co[0])<=.0288 else .6/(.28*.04))
            target=np.array([np.sign(co[0])*slope,np.sign(coords[vi,1]),0.])
            target/=max(np.linalg.norm(target),1.e-9)
        a=min(1.,max(0.,(co[2]-.145)/.006));transformed[li]=transformed[li]*(1-a)+target*a
        transformed[li]/=max(np.linalg.norm(transformed[li]),1.e-9)
for vi,p in enumerate(new):old.vertices[vi].co=p
old.update();old.normals_split_custom_set(transformed.tolist())
def mat(name,family):
    m=bpy.data.materials.new(name);m.use_nodes=True;ns=m.node_tree.nodes;ls=m.node_tree.links;bs=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
    for ch in ['BaseColor','ORM','Normal']:
        im=bpy.data.images.load(str(P/'Textures'/(family+'_'+ch+'.png')),check_existing=True);im.colorspace_settings.name='sRGB' if ch=='BaseColor' else 'Non-Color'
        tx=ns.new('ShaderNodeTexImage');tx.image=im
        if ch=='BaseColor':ls.new(tx.outputs['Color'],bs.inputs['Base Color'])
        elif ch=='Normal':n=ns.new('ShaderNodeNormalMap');ls.new(tx.outputs['Color'],n.inputs['Color']);ls.new(n.outputs['Normal'],bs.inputs['Normal'])
        else:
            n=ns.new('ShaderNodeSeparateColor');ls.new(tx.outputs['Color'],n.inputs['Color']);ls.new(n.outputs['Green'],bs.inputs['Roughness']);ls.new(n.outputs['Blue'],bs.inputs['Metallic'])
    return m
hilt=mat('M_XuanChi_Hilt_V2','Hilt');blade_mat=mat('M_XuanChi_SteelRelief_V2','Blade')
# Localized shared coordinates at the collar; the rest retains its original atlas.
old.materials.clear();old.materials.append(hilt);old.materials.append(blade_mat)
uv=old.uv_layers[0].data
for f in old.polygons:
    if min(old.vertices[i].co.z for i in f.vertices)>=.149:
        f.material_index=1
        for li in f.loop_indices:
            co=old.vertices[old.loops[li].vertex_index].co;uv[li].uv=(co.x/.11+.5,co.z/1.2)
    else:f.material_index=0
guard.name='SM_XuanChi_Guard_V2'
bpy.data.objects['SM_XuanChi_Blade'].hide_render=True
verts=[];faces=[];zs=np.linspace(join-.00003,1.20,241)
for h in zs:
    w=float(np.interp(h,[join,.18,.30,.88,1.035,1.15,1.19,1.20],[.040,.040,.042,.038,.032,.019,.005,.00003]));th=float(np.interp(h,[join,.30,.95,1.16,1.2],[.0045,.0045,.0032,.0016,.00004]))
    verts.extend([(x,y,float(h)) for x,y in [(-w,0),(-w*.72,-th*.6),(0,-th),(w*.72,-th*.6),(w,0),(w*.72,th*.6),(0,th),(-w*.72,th*.6)]])
for j in range(len(zs)-1):
    for k in range(8):faces.append((j*8+k,j*8+(k+1)%8,(j+1)*8+(k+1)%8,(j+1)*8+k))
faces.extend([tuple(reversed(range(8))),tuple(range((len(zs)-1)*8,len(zs)*8))])
mesh=bpy.data.meshes.new('BladeV2');mesh.from_pydata(verts,[],faces);mesh.materials.append(blade_mat);mesh.update();uv=mesh.uv_layers.new(name='UVMap')
for f in mesh.polygons:
    for li in f.loop_indices:
        co=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(co.x/.11+.5,co.z/1.2)
blade=bpy.data.objects.new('SM_XuanChi_Blade_V2',mesh);scene.collection.objects.link(blade)
parts=[guard,blade]
for name in ['Grip','Pommel']:
    obj=bpy.data.objects['SM_XuanChi_'+name];obj.name+='_'+ 'V2';obj.data.materials.clear();obj.data.materials.append(hilt);parts.append(obj)
tail=bpy.data.objects['SM_XuanChi_Tassel'];tail.data.materials.clear();tail.data.materials.append(hilt)
def export(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
    loc=obj.location.copy();obj.location=Vector()
    bpy.ops.export_scene.fbx(filepath=str(O/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    obj.location=loc
for obj in parts:export(obj)
bpy.ops.object.select_all(action='DESELECT')
for obj in parts+[tail]:
    cp=obj.copy();cp.data=obj.data.copy();scene.collection.objects.link(cp);cp.select_set(True);bpy.context.view_layer.objects.active=cp
bpy.ops.object.join();whole=bpy.context.object;whole.name='SM_XuanChi_Complete_V2';scene.cursor.location=Vector();bpy.ops.object.origin_set(type='ORIGIN_CURSOR');export(whole);whole.hide_render=True
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'XuanChi_SurfaceV2_Editable.blend'))
(P/'exports.json').write_text(json.dumps({'revision':'SurfaceV2','ue_root':'/Game/Weapons/XuanChiZhenYue20261004/SurfaceV2','meshes':[x.name for x in parts]+[whole.name],'junction_z_cm':join*100,'blade_depth_cm':.032,'tested':False},indent=2))
print('XUANCHI_V2_JUNCTION_AND_MESHES_EXPORTED',flush=True)
