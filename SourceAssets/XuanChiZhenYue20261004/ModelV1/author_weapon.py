"""Retain Meshy hilt/tassel; build an explicit thin steel blade and module interfaces."""
import bpy,bmesh,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent;OUT=P/'Export';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'XuanChi_Original_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
src=next(o for o in scene.objects if o.type=='MESH');mesh=src.data;mesh.calc_loop_triangles()
source_mat=mesh.materials[0];source_mat.name='M_XuanChi_Hilt'
points=np.array([tuple(v.co) for v in mesh.vertices]);source_z=points[:,2].copy()
LANDMARKS=np.array([-.960027,-.665,-.55,-.224,-.14,.008,.948954])
TARGETS=np.array([-.695,-.40,-.30,-.05,0,.155,1.20])
def fit(p):
    q=p.copy();z=p[:,2];grip=np.clip((z+.56)/.02,0,1)*(1-np.clip((z+.23)/.02,0,1))
    scale=.78*(1-grip)+.58*grip
    tail=z<-.665;scale[tail]=.83
    q[:,0]=(p[:,0]+.000402)*scale;q[:,1]=(p[:,1]-.00055)*scale
    q[:,2]=np.interp(z,LANDMARKS,TARGETS);return q
uv=mesh.uv_layers[0].data
normals=np.array([tuple(n.vector) for n in mesh.corner_normals])
eps=1e-6;jac=np.empty((len(points),3,3))
for k in range(3):
    d=np.zeros(3);d[k]=eps;jac[:,:,k]=(fit(points+d)-fit(points-d))/(2*eps)
indices=np.array([l.vertex_index for l in mesh.loops]);inv=np.linalg.pinv(jac).transpose(0,2,1)
normals=np.einsum('nij,nj->ni',inv[indices],normals);normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-9)
positions=fit(points)
texnode=next(n for n in source_mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image and n.image.colorspace_settings.name=='sRGB')
image=texnode.image;pixels=np.empty(len(image.pixels),dtype=np.float32);image.pixels.foreach_get(pixels);pixels=pixels.reshape(image.size[1],image.size[0],4)
def triangle_color(tri):
    v=sum((uv[i].uv for i in tri.loops),Vector((0,0)))/3
    return pixels[min(image.size[1]-1,max(0,int(v.y*image.size[1]))),min(image.size[0]-1,max(0,int(v.x*image.size[0]))),:3]

def is_red(tri):
    c=triangle_color(tri)
    return c[0]>.12 and c[0]>c[1]*1.35 and c[0]>c[2]*1.3

def clip(poly,cut,above):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[0].z-cut)*(1 if above else -1);db=(b[0].z-cut)*(1 if above else -1)
        if da>=0:out.append(a)
        if (da>=0)!=(db>=0):
            t=da/(da-db);out.append(tuple(x.lerp(y,t) for x,y in zip(a,b)))
    return out
tail_source=np.array([-.642,-.690,-.706,-.757,-.795,-.846,-.904,-.960027])
tail_z=np.interp(tail_source,LANDMARKS,TARGETS)
anchor=Vector((0,0,float(tail_z[0])))
tail_guides=[[0,0,float((z-tail_z[0])*100)] for z in tail_z]
parts={};rows=[]
def make_source_part(slot,lower,upper,pivot):
    verts=[];faces=[];corners=[]
    for tri in mesh.loop_triangles:
        zs=source_z[list(tri.vertices)]
        tail=bool(zs.mean()<-.665 or (zs.mean()<-.625 and is_red(tri)))
        if (slot=='tassel')!=tail:continue
        if zs.max()<lower or zs.min()>upper:continue
        poly=[(Vector(positions[mesh.loops[i].vertex_index]),uv[i].uv.copy(),Vector(normals[i])) for i in tri.loops]
        if slot!='tassel':
            poly=clip(poly,float(np.interp(lower,LANDMARKS,TARGETS)),True)
            if poly:poly=clip(poly,float(np.interp(upper,LANDMARKS,TARGETS)),False)
        for k in range(1,len(poly)-1):
            t=[poly[0],poly[k],poly[k+1]]
            if (t[1][0]-t[0][0]).cross(t[2][0]-t[0][0]).length<1e-12:continue
            face=[]
            for corner in t:face.append(len(verts));verts.append(corner[0]-pivot);corners.append(corner)
            faces.append(face)
    name='SM_XuanChi_'+slot.title();data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.materials.append(source_mat);data.update()
    layer=data.uv_layers.new(name='UVMap');ns=data.attributes.new('PreservedNormal','FLOAT_VECTOR','CORNER')
    for f in data.polygons:
        f.use_smooth=True
        for li in f.loop_indices:
            corner=corners[data.loops[li].vertex_index];layer.data[li].uv=corner[1];ns.data[li].vector=corner[2]
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=0.0000003)
    if slot!='tassel':
        cuts=[float(np.interp(z,LANDMARKS,TARGETS))-pivot.z for z in [lower,upper]]
        edges=[e for e in bm.edges if e.is_boundary and any(all(abs(v.co.z-z)<2e-6 for v in e.verts) for z in cuts)]
        if edges:
            filled=bmesh.ops.holes_fill(bm,edges=edges,sides=0)['faces'];nl=bm.loops.layers.float_vector['PreservedNormal'];ul=bm.loops.layers.uv[0]
            for f in filled:
                f.smooth=False;f.normal_update()
                for l in f.loops:l[nl]=f.normal;l[ul].uv=(.505,.325)
    bm.to_mesh(data);bm.free();data.update();data.normals_split_custom_set([tuple(n.vector) for n in data.attributes['PreservedNormal'].data])
    if slot=='tassel':
        skin=data.uv_layers.new(name='TasselSkin')
        for l in data.loops:
            z=data.vertices[l.vertex_index].co.z+pivot.z
            # The jade and its suspension beads are rigid links; silk blends along its length.
            index=int(np.clip(np.searchsorted(-tail_z,-z)-1,0,6));blend=float(np.clip((tail_z[index]-z)/max(1e-7,tail_z[index]-tail_z[index+1]),0,1))
            if tail_z[3]<=z<=tail_z[2]:index=2;blend=0
            elif tail_z[4]<=z<tail_z[3]:index=3;blend=0
            if index==6:blend=0
            skin.data[l.index].uv=(index,blend)
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=pivot;parts[slot]=obj
    rows.append({'slot':slot,'mesh':name,'location_cm':[float(x*100) for x in pivot],'triangles':sum(len(f.vertices)-2 for f in data.polygons)})
    print('XUANCHI_PART '+slot+' '+str(rows[-1]['triangles']),flush=True)
make_source_part('guard',-.224,.010,Vector())
make_source_part('grip',-.55,-.224,Vector((0,0,-.05)))
make_source_part('pommel',-.69,-.55,Vector((0,0,-.30)))
make_source_part('tassel',-2,-.625,anchor)

def mapped_material(name,prefix):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
    for key in ['BaseColor','Normal','ORM']:
        im=bpy.data.images.load(str(P/'Textures'/(prefix+key+'.png')),check_existing=True);im.colorspace_settings.name='sRGB' if key=='BaseColor' else 'Non-Color';t=n.new('ShaderNodeTexImage');t.image=im
        if key=='BaseColor':l.new(t.outputs['Color'],bs.inputs['Base Color'])
        elif key=='Normal':b=n.new('ShaderNodeNormalMap');l.new(t.outputs['Color'],b.inputs['Color']);l.new(b.outputs['Normal'],bs.inputs['Normal'])
        else:
            s=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],s.inputs['Color']);l.new(s.outputs['Green'],bs.inputs['Roughness']);l.new(s.outputs['Blue'],bs.inputs['Metallic'])
    return mat
blade_mat=mapped_material('M_XuanChi_Blade','Blade_')
verts=[];faces=[];stations=np.linspace(.154,1.20,241)
for z in stations:
    # Keep the original bronze langet and reinforced steel collar intact.
    # The rebuilt blade enters the collar with a short overlapping shoulder.
    w=float(np.interp(z,[.154,.20,.88,1.035,1.15,1.19,1.20],[.040,.042,.038,.032,.019,.005,.00003]));h=float(np.interp(z,[.154,.20,.95,1.16,1.2],[.0055,.0045,.0032,.0016,.00004]))
    verts.extend([(x,y,float(z)) for x,y in [(-w,0),(-w*.72,-h*.60),(0,-h),(w*.72,-h*.60),(w,0),(w*.72,h*.60),(0,h),(-w*.72,h*.60)]])
for j in range(len(stations)-1):
    for k in range(8):faces.append((j*8+k,j*8+(k+1)%8,(j+1)*8+(k+1)%8,(j+1)*8+k))
faces.extend([tuple(reversed(range(8))),tuple(range((len(stations)-1)*8,len(stations)*8))])
data=bpy.data.meshes.new('SM_XuanChi_Blade');data.from_pydata(verts,[],faces);data.materials.append(blade_mat);data.update();uvl=data.uv_layers.new(name='UVMap')
for f in data.polygons:
    f.use_smooth=False
    for li in f.loop_indices:
        p=data.vertices[data.loops[li].vertex_index].co;uvl.data[li].uv=(p.x/.11+.5,(p.z-.09)/1.11)
obj=bpy.data.objects.new('SM_XuanChi_Blade',data);scene.collection.objects.link(obj);parts['blade_1']=obj
rows.append({'slot':'blade_1','mesh':obj.name,'location_cm':[0,0,0],'triangles':sum(len(f.vertices)-2 for f in data.polygons),'trace_base_cm':[0,0,12],'trace_tip_cm':[0,0,120],'rune_dimensions_cm':[11,2,108]})
# Source pommel converters retain the shared library's lower mounting diameters.
adapters={}
metal=bpy.data.materials.new('M_XuanChi_Mount');metal.use_nodes=True;bs=next(n for n in metal.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.25,.16,.065,1);bs.inputs['Metallic'].default_value=.95;bs.inputs['Roughness'].default_value=.38
for kind,bottom in [('frost_hilt_v1',.017),('shared_sword_pommel_v1',.012)]:
    name='SM_XuanChi_Adapter_'+kind;vs=[];fs=[]
    for z,r in [(0,.019),(-.003,.019),(-.008,bottom)]:
        for i in range(48):a=i*math.tau/48;vs.append((math.cos(a)*r,math.sin(a)*r,z))
    for j in range(2):
        for i in range(48):fs.append((j*48+i,j*48+(i+1)%48,(j+1)*48+(i+1)%48,(j+1)*48+i))
    fs.extend([tuple(reversed(range(48))),tuple(range(96,144))]);d=bpy.data.meshes.new(name);d.from_pydata(vs,[],fs);d.materials.append(metal);d.update();d.uv_layers.new(name='UVMap')
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.hide_render=True;adapters[kind]={'mesh':name,'depth_cm':.8,'scale':.9 if kind=='shared_sword_pommel_v1' else 1}
    parts['adapter_'+kind]=o
def export(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o;loc=o.location.copy();o.location=Vector()
    bpy.ops.export_scene.fbx(filepath=str(OUT/(o.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    o.location=loc
for o in parts.values():export(o)
# Whole-weapon fallback for consumers which do not use the modular assembly.
bpy.ops.object.select_all(action='DESELECT')
for k,o in parts.items():
    if not k.startswith('adapter_'):
        cp=o.copy();cp.data=o.data.copy();scene.collection.objects.link(cp);cp.select_set(True);bpy.context.view_layer.objects.active=cp
bpy.ops.object.join();whole=bpy.context.object;whole.name='SM_XuanChi_Complete';scene.cursor.location=Vector();bpy.ops.object.origin_set(type='ORIGIN_CURSOR');export(whole);whole.hide_render=True
src.hide_render=True;src.hide_set(True)
for k,o in parts.items():o.hide_render=k.startswith('adapter_')
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'XuanChi_Modular_Editable.blend'))
manifest={'weapon':'ue_xuanchi_zhenyue','ue_root':'/Game/Weapons/XuanChiZhenYue20261004','parts':rows,'adapters':adapters,'world_mesh':whole.name,'arms_mesh':'/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms.SK_FrostSword_Arms','animation_folder':'/Game/Weapons/AzureRunesword20260913','tassel_guides_cm':tail_guides,'tassel_collision_capsules_cm':[[0,0,8,0,0,34,2.4],[0,0,46,0,0,155,5.1],[-10,0,40,10,0,40,3.0]],'blade_rebuilt':True,'rigid_length_cm':160,'tested':False}
(P/'exports.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print('XUANCHI_AUTHOR_COMPLETE',flush=True)
