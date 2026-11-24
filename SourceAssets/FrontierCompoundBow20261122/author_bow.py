"""Split the supplied textured mesh and author the compound bow's game rig in centimetres."""
from pathlib import Path
import json, math, struct
import bpy, bmesh
from mathutils import Vector, Quaternion

P = Path(__file__).resolve().parent
source = next((P/'Source').glob('*.glb'))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
bpy.ops.import_scene.gltf(filepath=str(source))
src = next(o for o in scene.objects if o.type == 'MESH')
bpy.context.view_layer.objects.active = src
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
scene.unit_settings.scale_length = .01
surface = src.data.materials[0]
surface.name = 'M_Frontier_Surface'
# Extract the embedded images without re-encoding the normal or packed mask.
with source.open('rb') as stream:
    stream.seek(12)
    size, _ = struct.unpack('<II',stream.read(8))
    gltf = json.loads(stream.read(size))
    stream.read(8)
    payload = stream.read()
for name, texture in [('BaseColor',gltf['materials'][0]['pbrMetallicRoughness']['baseColorTexture']),
                      ('Normal',gltf['materials'][0]['normalTexture']),
                      ('MetalRough',gltf['materials'][0]['pbrMetallicRoughness']['metallicRoughnessTexture'])]:
    image = gltf['images'][gltf['textures'][texture['index']]['source']]
    view = gltf['bufferViews'][image['bufferView']]
    offset = view.get('byteOffset',0)
    (P/'Textures'/('T_Frontier_'+name+'.png')).write_bytes(payload[offset:offset+view['byteLength']])

def fit(x,y,z):
    return Vector((-(x-.107)*53.,-y*53.,(z+.098)*53.))

def part(p):
    x,y,z = p
    side = 'Upper' if z>0 else 'Lower'
    if x>.282 and abs(z)<.653: return 'BakedLines'
    if x>.282 and abs(z)>=.653:
        # The fork cheeks straddle the wheel and stay on the flexible limb.
        if abs(y)>.031 and abs(abs(z)-.818)<.061 and x<.455:return side+'Limb'
        return side+'Cam'
    if abs(z)>.655:return side+'Limb'
    if -.328<z<-.145 and x<-.014:return 'Stabilizer'
    if -.177<z<-.013 and x>-.014:return 'Grip'
    if .018<z<.165 and x>.119:return 'Rest'
    return 'Riser'

bm=bmesh.new();bm.from_mesh(src.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
for axis,levels in [(0,[-.014,.119,.282,.455]),(1,[-.031,.031]),(2,[-.879,-.757,-.655,-.653,-.328,-.177,-.145,-.013,.018,.165,.653,.655,.757,.879])]:
    for value in levels:
        origin=Vector((0,0,0));origin[axis]=value
        normal=Vector((0,0,0));normal[axis]=1.
        # Only cut faces straddling this plane.
        crossing=[f for f in bm.faces if min(v.co[axis] for v in f.verts)<value<max(v.co[axis] for v in f.verts)]
        edges={e for f in crossing for e in f.edges}
        bmesh.ops.bisect_plane(bm,geom=[*crossing,*edges,*{v for e in edges for v in e.verts}],
                               dist=1e-7,plane_co=origin,plane_no=normal)
bm.to_mesh(src.data);bm.free();src.data.update()
labels=[part(f.center) for f in src.data.polygons]
objects={}
for label in sorted(set(labels)-{'BakedLines'}):
    mesh=src.data.copy()
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if labels[f.index]!=label],context='FACES')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
    border=[e for e in bm.edges if e.is_boundary]
    if border:
        uv=bm.loops.layers.uv.active
        for face in bmesh.ops.holes_fill(bm,edges=border,sides=0).get('faces',[]):
            for loop in face.loops:
                neighbor=next((l for l in loop.vert.link_loops if l.face!=face),None)
                if uv and neighbor:loop[uv].uv=neighbor[uv].uv
    for v in bm.verts:v.co=fit(*v.co)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bm.to_mesh(mesh);bm.free();mesh.update()
    obj=bpy.data.objects.new(label,mesh);scene.collection.objects.link(obj)
    objects[label]=obj
bpy.data.objects.remove(src,do_unlink=True)
rig=bpy.data.objects.new('Armature',bpy.data.armatures.new('FrontierCompoundRig'))
scene.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig
rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
bones=rig.data.edit_bones
def bone(name,head,parent=None,tilt=0.):
    b=bones.new(name);b.head=head
    b.tail=b.head+Quaternion((0,1,0),math.radians(tilt))@Vector((0,0,1.5))
    if parent:b.parent=bones[parent]
    return b
bone('bow_body_root',(0,0,0))
brace=fit(.526,0.,-.055)
full=brace+Vector((-30.,0.,0.))
bone('compound_draw_end',full,'bow_body_root')
tips={};cable_points={}
for side,sign in [('upper',1),('lower',-1)]:
    limb=fit(-.09,0,sign*.655);joint=fit(.115,0,sign*.806)
    hub=fit(.409,0,sign*.815);exit_point=fit(.542,0,sign*.797)
    for suffix,pos,parent,angle in [
        ('_01',limb,'bow_body_root',-sign*6.),
        ('_02',joint,side+'_01',-sign*4.),
        ('_cam',hub,side+'_02',-sign*96.)]:
        name=side+suffix;bone(name,pos,parent)
        bone('draw_'+name,pos,parent,angle)
    bone(side+'_tip',exit_point,side+'_02')
    # A separate string-exit marker slides around the visible rim as the cam turns.
    end=fit(.516,0,sign*.883)
    bone('draw_'+side+'_tip',end,side+'_02')
    tips[side]=exit_point
    for strand,(x,y,z) in enumerate([(.355,.013,.754),(.427,-.018,.72)]):
        key=side+'_cable'+str(strand)
        pt=fit(x,y,sign*z);bone(key,pt,side+'_cam');cable_points[key]=pt
bpy.ops.object.mode_set(mode='OBJECT')
def skin(obj):
    obj.parent=rig
    mod=obj.modifiers.new('Compound draw','ARMATURE');mod.object=rig
def group(obj,name):
    return obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
for name in ('Riser','UpperLimb','LowerLimb','UpperCam','LowerCam'):
    obj=objects[name];skin(obj)
    if name.endswith('Limb'):
        side=name.removesuffix('Limb').lower()
        for v in obj.data.vertices:
            x=.107-v.co.x/53.
            w=max(0.,min(1.,(x-.06)/.12));w=w*w*(3.-2.*w)
            group(obj,side+'_01').add([v.index],1.-w,'REPLACE')
            group(obj,side+'_02').add([v.index],w,'REPLACE')
    else:
        joint='bow_body_root' if name=='Riser' else name.removesuffix('Cam').lower()+'_cam'
        group(obj,joint).add(list(range(len(obj.data.vertices))),1.,'REPLACE')

cord=bpy.data.materials.new('M_Frontier_Cord');cord.diffuse_color=(.045,.053,.051,1)
cord.use_nodes=True
bs=cord.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=cord.diffuse_color
bs.inputs['Roughness'].default_value=.76
def tube(name,start,end,radius,bindings=()):
    axis=(end-start).normalized();a=axis.cross(Vector((0,1,0))).normalized();b=axis.cross(a)
    vertices=[];faces=[];sides=8
    for center in (start,end):
        for i in range(sides):
            t=2*math.pi*i/sides
            vertices.append(center+radius*(a*math.cos(t)+b*math.sin(t)))
    for i in range(sides):
        j=(i+1)%sides;faces.append((i,j,j+sides,i+sides))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.materials.append(cord)
    obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj)
    if bindings:
        skin(obj)
        for i,joint in enumerate(bindings):group(obj,joint).add(list(range(i*sides,(i+1)*sides)),1.,'REPLACE')
    return obj
for i in range(2):
    pair=('upper_cable'+str(i),'lower_cable'+str(1-i))
    name='ControlCable'+str(i+1)
    objects[name]=tube(name,*[cable_points[k] for k in pair],.092,pair)
# Named FBX parts retain the shared grip origin; one skinned assembly drives both player views.
def export(name,items):
    bpy.ops.object.select_all(action='DESELECT')
    for o in items:o.select_set(True)
    bpy.context.view_layer.objects.active=rig if rig in items else items[0]
    bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(name+'.fbx')),use_selection=True,
        object_types={'MESH','ARMATURE'} if rig in items else {'MESH'},
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,add_leaf_bones=False,
        bake_anim=False,use_tspace=False,mesh_smooth_type='FACE')
dynamic=[objects[n] for n in ('Riser','UpperLimb','LowerLimb','UpperCam','LowerCam','ControlCable1','ControlCable2')]
# A single skinned mesh on import; editable components remain independent in the master.
copies=[]
for o in dynamic:
    c=o.copy();c.data=o.data.copy();scene.collection.objects.link(c);copies.append(c)
bpy.ops.object.select_all(action='DESELECT')
for c in copies:c.select_set(True)
bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join()
combined=bpy.context.object;combined.name='SK_Frontier_Assembly'
export(combined.name,[combined,rig]);bpy.data.objects.remove(combined,do_unlink=True)
for n in ('Grip','Rest','Stabilizer'):export('SM_Frontier_'+n,[objects[n]])
# Main string in Blender and in the inventory icon. The game draws it to the hand.
strings=[]
for side in ('upper','lower'):
    o=tube('MainString_'+side,tips[side],brace,.10)
    shape=o.shape_key_add(name='Basis');key=o.shape_key_add(name='Draw')
    for i in range(8,16):key.data[i].co+=full-brace
    skin(o);group(o,side+'_tip').add(list(range(8)),1.,'REPLACE');group(o,'bow_body_root').add(list(range(8,16)),1.,'REPLACE')
    strings.append(o)
import runpy
runpy.run_path(str(P/'author_draw_action.py'))['animate'](rig,scene)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'FrontierCompoundBow.blend'))
def ue(v):return [round(v.x,4),round(-v.y,4),round(v.z,4)]
(P/'geometry.json').write_text(json.dumps(dict(parts={k:len(v.data.polygons) for k,v in objects.items()},
    removed_baked_faces=labels.count('BakedLines'),upper=ue(tips['upper']),lower=ue(tips['lower']),
    brace=ue(brace),draw=ue(full),rest=ue(fit(.132,.038,-.055)),
    length=100.82,depth=58.84),indent=2),encoding='utf8')
# Product icon, orthographic and transparent, fitted to the owner's inventory tile.
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Euler
camera=bpy.data.cameras.new('InventoryCamera');cam=bpy.data.objects.new('InventoryCamera',camera);scene.collection.objects.link(cam)
scene.camera=cam;camera.type='ORTHO';cam.location=(48,-180,44)
center=Vector((1,0,5));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
cam.rotation_euler.rotate_axis('Z',math.radians(62))
points=[o.matrix_world@Vector(v) for o in list(objects.values())+strings for v in o.bound_box]
local=[cam.rotation_euler.to_matrix().inverted()@(v-center) for v in points]
lo=[min(v[i] for v in local) for i in range(2)];hi=[max(v[i] for v in local) for i in range(2)]
cam.location+=cam.rotation_euler.to_matrix()@Vector(((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,0))
camera.ortho_scale=max(hi[0]-lo[0],(hi[1]-lo[1])*2)*1.06;camera.clip_end=600
scene.render.engine='CYCLES';scene.cycles.samples=8;scene.render.film_transparent=True
scene.world=bpy.data.worlds.new('Icon studio');scene.world.use_nodes=True
scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.8,.8,.8,1)
scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.85
for pos,energy,size in [((40,-75,80),120000,72),((-25,50,30),82000,62)]:
    data=bpy.data.lights.new('Softbox','AREA');data.energy=energy;data.shape='DISK';data.size=size
    light=bpy.data.objects.new('Softbox',data);scene.collection.objects.link(light);light.location=pos
    light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=768;scene.render.resolution_y=384;scene.render.resolution_percentage=100
scene.render.image_settings.color_mode='RGBA';scene.render.filepath=str(P/'Export/bow_frontier_compound.png')
bpy.ops.render.render(write_still=True)
