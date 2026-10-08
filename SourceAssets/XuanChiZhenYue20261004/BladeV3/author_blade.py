"""Continuous blade under original ornaments; remove the old fused steel backing."""
import bpy,bmesh,json
import numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;S=P.parent/'ModelV1';O=P/'Export';O.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(S/'XuanChi_Modular_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
source=bpy.data.objects['SM_XuanChi_Guard'];old=source.data;old.calc_loop_triangles()
coords=np.array([tuple(v.co) for v in old.vertices])
lo=coords.min(axis=0);hi=coords.max(axis=0);center=(lo+hi)*.5
span=max(hi[0]-lo[0],hi[2]-lo[2])*1.15
# Trace the ornamental outline in the existing orthographic production icon.
# Each cut is outside the decorated perimeter; original ornament positions and UVs survive.
def projected(pixels):
    return np.array([[center[0]+(x-512)*span/1024,center[2]+(512-y)*span/1024] for x,y in pixels])
center_outline=[(331,551),(334,507),(369,505),(399,490),(422,466),(430,437),
 (423,375),(421,314),(426,274),(449,230),(481,184),(510,136),
 (541,184),(574,230),(594,273),(601,313),(599,373),(594,437),
 (602,467),(624,490),(658,505),(690,507),(697,551)]
left_hook=[(324,324),(341,314),(358,315),(376,325),(391,346),(402,372),
 (407,405),(416,437),(431,461),(420,485),(397,466),(382,439),
 (370,401),(361,367),(344,342)]
right_hook=[(1024-x,y) for x,y in reversed(left_hook)]
shapes=[projected(p) for p in [center_outline,left_hook,right_hook]]
q=coords[:,[0,2]]
def signed_distance(poly):
    inside=np.zeros(len(q),dtype=bool);distance=np.full(len(q),np.inf)
    for a,b in zip(poly,np.roll(poly,-1,axis=0)):
        ab=b-a;t=np.clip(((q-a)@ab)/max(float(ab@ab),1e-20),0,1)
        distance=np.minimum(distance,np.linalg.norm(q-a-t[:,None]*ab,axis=1))
        cross=((a[1]>q[:,1])!=(b[1]>q[:,1]))
        if abs(b[1]-a[1])>1e-15:
            inside^=cross&(q[:,0]<(b[0]-a[0])*(q[:,1]-a[1])/(b[1]-a[1])+a[0])
    return np.where(inside,distance,-distance)
base_z=center[2]+(512-541)*span/1024
field=base_z-coords[:,2]
for shape in shapes:field=np.maximum(field,signed_distance(shape)+.00050)
source_uv=old.uv_layers[0].data
source_normals=[Vector(n.vector) for n in old.corner_normals]
verts=[];faces=[];uvs=[];normals=[];cut_flags=[]
for tri in old.loop_triangles:
    polygon=[]
    for li in tri.loops:
        vi=old.loops[li].vertex_index
        polygon.append((Vector(coords[vi]),source_uv[li].uv.copy(),source_normals[li],float(field[vi]),False))
    clipped=[]
    for a,b in zip(polygon,polygon[1:]+polygon[:1]):
        if a[3]>=0:clipped.append(a)
        if (a[3]>=0)!=(b[3]>=0):
            t=a[3]/(a[3]-b[3]);clipped.append((a[0].lerp(b[0],t),a[1].lerp(b[1],t),a[2].lerp(b[2],t).normalized(),0,True))
    for k in range(1,len(clipped)-1):
        cs=[clipped[0],clipped[k],clipped[k+1]]
        if (cs[1][0]-cs[0][0]).cross(cs[2][0]-cs[0][0]).length<1e-13:continue
        face=[]
        for c in cs:
            face.append(len(verts));verts.append(c[0]);uvs.append(c[1]);normals.append(c[2]);cut_flags.append(float(c[4]))
        faces.append(face)
data=bpy.data.meshes.new('XuanChi_OriginalOrnaments_WithoutOldBlade')
data.from_pydata(verts,[],faces);data.update()
uv=data.uv_layers.new(name='UVMap');na=data.attributes.new('RetainedNormal','FLOAT_VECTOR','CORNER');ca=data.attributes.new('CutBoundary','FLOAT','POINT')
for v in data.vertices:ca.data[v.index].value=cut_flags[v.index]
for f in data.polygons:
    f.use_smooth=True
    for li in f.loop_indices:
        vi=data.loops[li].vertex_index;uv.data[li].uv=uvs[vi];na.data[li].vector=normals[vi]
bm=bmesh.new();bm.from_mesh(data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000003)
cut=bm.verts.layers.float['CutBoundary'];nl=bm.loops.layers.float_vector['RetainedNormal'];ul=bm.loops.layers.uv[0]
edges=[e for e in bm.edges if e.is_boundary and all(v[cut]>.5 for v in e.verts)]
inner={}
for e in edges:
    for v in e.verts:
        if v not in inner:
            p=v.co.copy();p.y=0;inner[v]=bm.verts.new(p)
for e in edges:
    loop=e.link_loops[0];a,b=loop.vert,loop.link_loop_next.vert
    if (a.co-inner[a].co).length<1e-8 and (b.co-inner[b].co).length<1e-8:continue
    f=bm.faces.new([b,a,inner[a],inner[b]]);f.material_index=1;f.normal_update()
    # Give the new steel return lip a real UV rectangle; a single atlas point
    # has no tangent basis and causes broken normal-map shading at this join.
    for l,texcoord in zip(f.loops,[(.020,.025),(.016,.025),(.016,.029),(.020,.029)]):
        l[nl]=f.normal;l[ul].uv=texcoord
# Both sides meet on a buried center seam, with no second exposed blade surface.
bmesh.ops.remove_doubles(bm,verts=list(inner.values()),dist=.0000005)
bm.to_mesh(data);bm.free();data.update()
data.normals_split_custom_set([tuple(n.vector) for n in data.attributes['RetainedNormal'].data])
guard=bpy.data.objects.new('SM_XuanChi_Guard_V3',data);scene.collection.objects.link(guard)
source.hide_render=True;source.hide_set(True)

def material(name,directory,prefix):
    m=bpy.data.materials.new(name);m.use_nodes=True;ns=m.node_tree.nodes;ls=m.node_tree.links
    bs=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
    for ch in ['BaseColor','ORM','Normal']:
        im=bpy.data.images.load(str(directory/(prefix+'_'+ch+'.png')),check_existing=True)
        im.colorspace_settings.name='sRGB' if ch=='BaseColor' else 'Non-Color'
        tx=ns.new('ShaderNodeTexImage');tx.image=im
        if ch=='BaseColor':ls.new(tx.outputs['Color'],bs.inputs['Base Color'])
        elif ch=='Normal':
            n=ns.new('ShaderNodeNormalMap');ls.new(tx.outputs['Color'],n.inputs['Color']);ls.new(n.outputs['Normal'],bs.inputs['Normal'])
        else:
            n=ns.new('ShaderNodeSeparateColor');ls.new(tx.outputs['Color'],n.inputs['Color']);ls.new(n.outputs['Green'],bs.inputs['Roughness']);ls.new(n.outputs['Blue'],bs.inputs['Metallic'])
    return m
hilt=material('M_XuanChi_Hilt_V2',P.parent/'SurfaceV2/Textures','Hilt')
blade_mat=material('M_XuanChi_SteelRelief_V3',P/'Textures','Blade');data.materials.append(hilt);data.materials.append(blade_mat)
stations=json.loads((P/'blade_profile.json').read_text())['stations']
verts=[];faces=[]
for z,w,h in stations:
    verts.extend([(x,y,z) for x,y in [(-w,0),(-w*.73,-h*.95),(0,-h),(w*.73,-h*.95),(w,0),(w*.73,h*.95),(0,h),(-w*.73,h*.95)]])
for j in range(len(stations)-1):
    for k in range(8):faces.append((j*8+k,j*8+(k+1)%8,(j+1)*8+(k+1)%8,(j+1)*8+k))
faces.extend([tuple(reversed(range(8))),tuple(range((len(stations)-1)*8,len(stations)*8))])
mesh=bpy.data.meshes.new('ContinuousBladeV3');mesh.from_pydata(verts,[],faces);mesh.materials.append(blade_mat);mesh.update()
uv=mesh.uv_layers.new(name='UVMap');custom=[]
# Average lengthwise only. Keep the center ridge and bevel boundaries crisp.
smooth={}
for f in mesh.polygons[:-2]:
    section=f.index%8
    for vi in f.vertices:smooth[(vi,section)]=smooth.get((vi,section),Vector())+f.normal
for f in mesh.polygons:
    f.use_smooth=True
    for li in f.loop_indices:
        vi=mesh.loops[li].vertex_index;co=mesh.vertices[vi].co
        if f.index<len(mesh.polygons)-2:
            uv.data[li].uv=(co.x/.11+.5,co.z/1.2);custom.append(tuple(smooth[(vi,f.index%8)].normalized()))
        else:
            uv.data[li].uv=(.025+co.x*.15,.015+co.y);custom.append(tuple(f.normal))
mesh.normals_split_custom_set(custom)
blade=bpy.data.objects.new('SM_XuanChi_Blade_V3',mesh);scene.collection.objects.link(blade)
bpy.data.objects['SM_XuanChi_Blade'].hide_render=True;bpy.data.objects['SM_XuanChi_Blade'].hide_set(True)
parts=[blade,guard]
retained=[]
for name in ['Grip','Pommel','Tassel']:
    obj=bpy.data.objects['SM_XuanChi_'+name];obj.data.materials.clear();obj.data.materials.append(hilt);retained.append(obj)
def export(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
    loc=obj.location.copy();obj.location=Vector()
    bpy.ops.export_scene.fbx(filepath=str(O/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    obj.location=loc
for obj in parts:export(obj)
bpy.ops.object.select_all(action='DESELECT')
for obj in parts+retained:
    cp=obj.copy();cp.data=obj.data.copy();scene.collection.objects.link(cp);cp.hide_set(False);cp.select_set(True);bpy.context.view_layer.objects.active=cp
bpy.ops.object.join();whole=bpy.context.object;whole.name='SM_XuanChi_Complete_V3'
scene.cursor.location=Vector();bpy.ops.object.origin_set(type='ORIGIN_CURSOR');export(whole);whole.hide_render=True
for obj in scene.objects:
    if obj.type=='MESH':obj.hide_render=obj not in parts+retained
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'XuanChi_BladeV3_Editable.blend'))
(P/'exports.json').write_text(json.dumps({'revision':'BladeV3','ue_root':'/Game/Weapons/XuanChiZhenYue20261004/BladeV3',
    'meshes':[o.name for o in parts]+[whole.name],'ornament_source':'ModelV1/XuanChi_Modular_Editable.blend',
    'guard_operation':'Remove fused blade backing outside original ornament silhouette; retained face attributes unchanged',
    'blade_root_cm':-1.8,'blade_tip_cm':120,'body_thickness_mm':8,'tip_taper_start_cm':112,
    'ornament_outline_pixel_space':center_outline,'game_tested':False},indent=2))
print('XUANCHI_BLADE_V3_GEOMETRY_EXPORTED',flush=True)
