"""Split the retained Meshy bow, seat its rest sideways and author elastic limbs."""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree

P=Path(__file__).parent;S=P.parent
sys.path.insert(0,str(P))
from linen_surface import author_linen
bpy.ops.wm.open_mainfile(filepath=str(P/'Source/Longbow_Original.blend'))
bpy.context.preferences.filepaths.save_version=0
src=bpy.data.objects['Source_AncientElvenLongbow'];scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
mat=src.data.materials[0];mat.name='M_WoodSteelLongbow_PBR'
for im in bpy.data.images:
    path=P/'Textures'/(im.name.split('.')[0]+'.png')
    if path.exists():im.filepath=str(path);im.reload()
scale=180./1.9071769714355469
origin=Vector((-.060,.0005,-.055))
def fitted(p):
    p=(p-origin)*scale
    return Vector((-p.x,-p.y,p.z))

bm=bmesh.new();bm.from_mesh(src.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
# Cuts follow existing collars and the root of the two transverse rest pieces.
# UV values on inserted corners are interpolated by BMesh.
for axis,value in [(2,-.129),(2,.019),(2,.023),(2,.047),(0,-.0805),(0,-.034),(2,-.878),(2,.878),(0,.118)]:
    co=Vector((0,0,0));co[axis]=value;normal=Vector((0,0,0));normal[axis]=1
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-8,
                           plane_co=co,plane_no=normal,clear_inner=False,clear_outer=False)
bm.to_mesh(src.data);bm.free()
def role(p):
    if p.x>.118-1e-7 and -.878<p.z<.878:return 'string'
    if .023<p.z<.047 and (p.x<-.0805 or p.x>-.034):return 'rest'
    if -.129<p.z<.019:return 'grip'
    return 'body'
roles=[role(f.center) for f in src.data.polygons]

def split(label,name):
    data=src.data.copy();bm=bmesh.new();bm.from_mesh(data);bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if roles[f.index]!=label],context='FACES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    boundary=[e for e in bm.edges if e.is_boundary]
    if boundary:
        fill=bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
        uv=bm.loops.layers.uv.active
        for f in fill.get('faces',[]):
            if uv:
                for loop in f.loops:
                    neighbor=next((l for l in loop.vert.link_loops if l.face!=f),None)
                    if neighbor:loop[uv].uv=neighbor[uv].uv
    bm.to_mesh(data);bm.free()
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    for v in data.vertices:v.co=fitted(v.co)
    data.update()
    return obj

body=split('body','SK_WoodSteelLongbow_Original')
grip=split('grip','SM_WoodSteelLongbow_Grip')
rest=split('rest','SM_WoodSteelLongbow_Rest')
removed_string=roles.count('string')
bpy.data.objects.remove(src,do_unlink=True)
turn=Matrix.Rotation(math.pi/2,3,'Z')
for v in rest.data.vertices:
    # Rotate around the actual handle axis, so the shelf extends toward UE -Y.
    v.co=turn@v.co
rest.data.update()
tree=BVHTree.FromObject(rest,bpy.context.evaluated_depsgraph_get())
contact,_,_,_=tree.ray_cast(Vector((-.4,3.9,20)),Vector((0,0,-1)),30)
if contact is None:raise RuntimeError('Rest support was not found at the authored arrow axis')
arrow=contact+Vector((0,0,.30))
upper=fitted(Vector((.1240,.0005,.881)))
lower=fitted(Vector((.1240,.0005,-.881)))
brace=Vector((upper.x,0,arrow.z))
anchor=Vector((-52.581,0,arrow.z))

def material(name,color,rough,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    return m
metal=material('M_WoodSteelLongbow_Steel',(.16,.17,.18),.43,.9)
leather=material('M_WoodSteelLongbow_Leather',(.045,.022,.009),.78)
linen=material('M_WoodSteelLongbow_Linen',(.32,.30,.25),.88)

# Closed internal handle core; the original leather shell remains an independent part.
core=grip.copy();core.data=grip.data.copy();scene.collection.objects.link(core);core.name='InternalHandleCore'
for v in core.data.vertices:v.co.x*=.94;v.co.y*=.94
core.data.materials.clear();core.data.materials.append(metal)
for f in core.data.polygons:f.material_index=0
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);core.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.object.join()

rigdata=bpy.data.armatures.new('WoodSteelLongbowSkeleton')
rig=bpy.data.objects.new('Armature',rigdata);scene.collection.objects.link(rig)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
root=rigdata.edit_bones.new('bow_body_root');root.head=(0,0,0);root.tail=(0,0,4)
def section(z):
    vs=[v.co for v in body.data.vertices if abs(v.co.z-z)<1.4]
    if not vs:raise RuntimeError('Missing wood section '+str(z))
    return Vector(((min(v.x for v in vs)+max(v.x for v in vs))*.5,
                   (min(v.y for v in vs)+max(v.y for v in vs))*.5,z))
chains={};heads={}
for side,z0,tip in [('upper',32.,upper),('lower',-22.,lower)]:
    points=[section(z0+(tip.z-z0)*i/4) for i in range(4)]+[tip]
    names=[side+'_%02d'%(i+1) for i in range(4)]+[side+'_tip'];chains[side]=names
    for i,name in enumerate(names):
        bone=rigdata.edit_bones.new(name);bone.head=points[i]
        bone.tail=points[i+1] if i<4 else points[i]+Vector((0,0,1 if side=='upper' else -1))
        bone.parent=rigdata.edit_bones[names[i-1] if i else 'bow_body_root'];heads[name]=list(bone.head)
bpy.ops.object.mode_set(mode='OBJECT')

def skin(obj):
    groups={name:obj.vertex_groups.new(name=name) for name in ['bow_body_root']+list(heads)}
    for v in obj.data.vertices:
        side='upper' if v.co.z>=0 else 'lower';s=1 if side=='upper' else -1
        names=chains[side];z=s*v.co.z;zs=[s*heads[n][2] for n in names]
        if z<=zs[0]:weights={'bow_body_root':1.}
        elif z<zs[0]+5:
            t=(z-zs[0])/5;t=t*t*(3-2*t);weights={'bow_body_root':1-t,names[0]:t}
        else:
            i=next((j for j in range(4) if z<zs[j+1]),4)
            if i==4:weights={names[4]:1.}
            else:
                t=max(0,min(1,(z-(zs[i]+(5 if i==0 else 0)))/(zs[i+1]-(zs[i]+(5 if i==0 else 0)))))
                t=t*t*(3-2*t);weights={names[i]:1-t,names[i+1]:t}
        for name,w in weights.items():
            if w>1e-7:groups[name].add([v.index],w,'REPLACE')
    obj.parent=rig;mod=obj.modifiers.new('Wooden limb flex','ARMATURE');mod.object=rig

bodies=[body]
for name,factor in [('Heavy',1.15),('Swift',.88),('Steady',1.06)]:
    obj=body.copy();obj.data=body.data.copy();obj.name='SK_WoodSteelLongbow_'+name;scene.collection.objects.link(obj)
    for v in obj.data.vertices:
        t=max(0,min(1,(abs(v.co.z)-28)/12));t=t*t*(3-2*t)
        v.co.y*=1+(factor-1)*t
    bodies.append(obj)
for obj in bodies:skin(obj)

parts=[grip,rest]
for name,factor,finish in [('Linen',1.,linen),('SlimLeather',.98,None),('PaddedLeather',1.025,None)]:
    obj=grip.copy();obj.data=grip.data.copy();obj.name='SM_WoodSteelLongbow_Grip_'+name;scene.collection.objects.link(obj)
    for v in obj.data.vertices:v.co.x*=factor;v.co.y*=factor
    if finish:
        obj.data.materials.clear();obj.data.materials.append(finish)
        for f in obj.data.polygons:f.material_index=0
        if name=='Linen':author_linen(obj)
    parts.append(obj)

def add_pad(name,center,size,finish):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center);obj=bpy.context.object;obj.name=name;obj.scale=size
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    obj.data.materials.append(finish)
    mod=obj.modifiers.new('Soft contact edges','BEVEL');mod.width=.045;mod.segments=3
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj
for name in ['Lined','Quick','Fork']:
    obj=rest.copy();obj.data=rest.data.copy();obj.name='SM_WoodSteelLongbow_Rest_'+name;scene.collection.objects.link(obj)
    extra=[]
    if name=='Fork':
        for side in [-1,1]:extra.append(add_pad('Leather guide',contact+Vector((0,side*.39,.13)),(1.4,.16,.30),leather))
    else:extra.append(add_pad('Contact pad',contact+Vector((0,0,.025)),(1.5,.7,.05),leather if name=='Lined' else metal))
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    for e in extra:e.select_set(True)
    bpy.context.view_layer.objects.active=obj;bpy.ops.object.join();parts.append(obj)

def append(path,name):
    with bpy.data.libraries.load(str(path),link=False) as (a,b):b.objects=[name]
    obj=b.objects[0];scene.collection.objects.link(obj);obj.data=obj.data.copy()
    obj.data.transform(obj.matrix_world);obj.parent=None;obj.matrix_world=Matrix.Identity(4)
    return obj

# The existing optical heads share one bracket interface. Move that interface to
# this bow's upper metal socket; preserve the original lens and reticle materials.
optics=[]
optics_source=S/'BowSingleLensOptics20260927/Bow_SingleLensOptics.blend'
if optics_source.exists():
    with bpy.data.libraries.load(str(optics_source),link=False) as (a,b):available=list(a.objects)
    (P/'Authoring/optic_source_objects.json').write_text(json.dumps(available),encoding='utf-8')

assets=[]
for obj in bodies+parts:
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    tri=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    if obj in bodies:rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(obj.name+'.fbx')),use_selection=True,
        object_types={'MESH','ARMATURE'} if obj in bodies else {'MESH'},axis_forward='-Y',axis_up='Z',
        apply_unit_scale=True,add_leaf_bones=False,bake_anim=False,use_tspace=True,mesh_smooth_type='FACE')
    assets.append({'name':obj.name,'skeletal':obj in bodies,'materials':[m.name for m in obj.data.materials],
        'triangles':sum(len(f.vertices)-2 for f in obj.data.polygons)})
for obj in bodies+parts:obj.hide_set(obj not in [body,grip,rest]);obj.hide_render=obj not in [body,grip,rest]
rig.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'WoodSteelLongbow_Editable.blend'))
def ue(p):return [round(p.x,5),round(-p.y,5),round(p.z,5)]
result={'assets':assets,'source_scale_cm':scale,'source_grip_origin_m':list(origin),
    'removed_baked_string_faces':removed_string,'rest_rotation_degrees':90,
    'nock_upper_cm':ue(upper),'nock_lower_cm':ue(lower),'brace_nock_cm':ue(brace),
    'draw_anchor_cm':ue(anchor),'arrow_rest_cm':ue(arrow),'bow_length_cm':180.,
    'bow_depth_cm':max(v.co.x for v in body.data.vertices)-min(v.co.x for v in body.data.vertices),
    'bone_heads_blender_cm':heads,'gameplay_tested':False}
(P/'authoring.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('WOOD_STEEL_LONGBOW_AUTHORED '+json.dumps(result))
