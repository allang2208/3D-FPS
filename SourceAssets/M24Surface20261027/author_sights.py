"""Visual game accessory from TM 9-1005-306-10 figs 2-22/23, fitted to this M24.
Dimensions are art-fit values, not manufacturing specifications.
Source frame: metres, +Y muzzle, +Z up. Export matches existing static attachments.
"""
import bpy,math,json
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).resolve().parent;X=O/'Exports';X.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene;parts=[]
def mat(name,color,metal,rough):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;return m
steel=mat('M24_IronSatin',(.028,.029,.031),1,.39)
dark=mat('M24_IronInterior',(.006,.006,.006),0,.72)
mark=mat('M24_IronMarking',(.38,.38,.36),0,.48)
def finish(ob,name,material=steel,bevel=.00016):
    ob.name=name;ob.data.materials.append(material)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        b=ob.modifiers.new('Machined edge radius','BEVEL');b.width=bevel;b.segments=2
        b.limit_method='ANGLE';b.angle_limit=math.radians(35)
        bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=b.name)
    for p in ob.data.polygons:p.use_smooth=True
    n=ob.modifiers.new('Face weighted normals','WEIGHTED_NORMAL');n.keep_sharp=True;n.weight=30
    bpy.ops.object.modifier_apply(modifier=n.name)
    parts.append(ob);return ob
def box(name,pos,size,material=steel,bevel=.00016):
    bpy.ops.mesh.primitive_cube_add(size=1,location=pos);ob=bpy.context.object;ob.dimensions=size
    return finish(ob,name,material,bevel)
def cyl(name,pos,radius,depth,axis='Z',material=steel):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=radius,depth=depth,location=pos)
    ob=bpy.context.object
    if axis=='Y':ob.rotation_euler.x=math.pi/2
    if axis=='X':ob.rotation_euler.y=math.pi/2
    return finish(ob,name,material,.00010)
def tube(name,pos,outer,inner,length,material=steel,segments=48):
    # Closed annulus with a real open bore, axis Y. Inner wall uses matte material.
    verts=[];faces=[];mats=[]
    for y,r in [(-length/2,outer),(length/2,outer),(-length/2,inner),(length/2,inner)]:
        verts.extend([(pos[0]+r*math.cos(i*2*math.pi/segments),pos[1]+y,pos[2]+r*math.sin(i*2*math.pi/segments)) for i in range(segments)])
    for i in range(segments):
        j=(i+1)%segments
        faces.extend([(i,j,segments+j,segments+i),(2*segments+j,2*segments+i,3*segments+i,3*segments+j),
                      (j,i,2*segments+i,2*segments+j),(segments+i,segments+j,3*segments+j,3*segments+i)])
        mats.extend([0,1,0,0])
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    ob=bpy.data.objects.new(name,me);s.collection.objects.link(ob);bpy.context.view_layer.objects.active=ob;ob.select_set(True)
    finish(ob,name,material,.00008);ob.data.materials.append(dark)
    # Original faces are assigned before bevel is unavailable; inner wall identified geometrically.
    for p in ob.data.polygons:
        r=((p.center.x-pos[0])**2+(p.center.z-pos[2])**2)**.5
        if r<inner+.00012:p.material_index=1
    return ob
def knob(name,pos,radius,depth,axis):
    ob=cyl(name,pos,radius,depth,axis)
    # Broad separated milling grooves, restrained silhouette at first-person distance.
    for i in range(24):
        a=2*math.pi*i/24
        if axis=='Z':p=(pos[0]+radius*math.cos(a),pos[1]+radius*math.sin(a),pos[2]);sz=(.00036,.00036,depth*.78)
        else:p=(pos[0],pos[1]+radius*math.cos(a),pos[2]+radius*math.sin(a));sz=(depth*.78,.00036,.00036)
        box(name+'_flute',p,sz,dark,.00004)
    return ob
def screw(name,pos,axis='X'):
    cyl(name,pos,.0018,.0009,axis)
    q=Vector(pos);q[0 if axis=='X' else 2]+=.00049
    sz=(.00012,.0025,.00045) if axis=='X' else (.0025,.00045,.00012)
    box(name+'_slot',q,sz,dark,.00003)
# Rear bracket: receiver-left mount, rising dovetail, horizontal windage slide and aperture.
box('Rear_receiver_side_base',(-.018,.070,.122),(.005,.049,.015))
box('Rear_vertical_carriage',(-.024,.058,.139),(.007,.017,.039))
box('Rear_elevation_guide',(-.028,.058,.140),(.002,.012,.035))
box('Rear_windage_bridge',(-.011,.057,.149),(.031,.014,.009))
box('Rear_aperture_support',(0,.055,.147),(.010,.009,.010))
cyl('Rear_elevation_spindle',(-.024,.058,.1602),.0027,.0054,'Z')
knob('Rear_elevation_drum',(-.024,.058,.164),.0062,.004,'Z')
knob('Rear_windage_drum',(-.032,.057,.151),.0055,.004,'X')
tube('Rear_aperture_stem',(0,.049,.153),.0050,.0032,.010)
tube('Rear_peep_disc',(0,.041,.153),.0115,.0032,.0022)
tube('Rear_peep_rim',(0,.0398,.153),.0117,.0108,.0008)
for y in [.050,.078]:screw('Rear_base_fastener',(-.021,y,.122))
for z in [.129,.148]:screw('Rear_guide_fastener',(-.0292,.058,z))
for i in range(9):box('Rear_elevation_index',(-.0292,.056,.128+i*.003),(.00012,.004 if i%2==0 else .002,.00022),mark,.00002)
# Front sight sits on the barrel, behind the existing suppressor shoulder.
box('Front_barrel_saddle',(0,.797,.128),(.015,.033,.004))
box('Front_dovetail_base',(0,.797,.132),(.018,.030,.004))
box('Front_hood_pedestal',(0,.797,.137),(.012,.024,.008))
tube('Front_protective_hood',(0,.797,.153),.0115,.0093,.039)
tube('Front_insert_retainer',(0,.778,.153),.0120,.0093,.003)
knob('Front_side_clamp',(-.010,.797,.135),.0045,.0025,'X')
box('Front_clamp_screw_slot',(-.0113,.797,.135),(.00015,.0065,.0007),dark,.00004)
box('Front_post',(0,.794,.1486),(.0013,.0015,.0088),dark,.00006)
# Fixed identity and actual shared aim line, in the existing static-export frame.
rear=[0.,-4.10,15.30];front=[0.,-79.40,15.30]
for ob in parts:
    bpy.context.view_layer.objects.active=ob;bpy.ops.object.select_all(action='DESELECT');ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
    tri=ob.modifiers.new('Export triangles','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
bpy.ops.object.select_all(action='DESELECT')
for ob in parts:ob.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
file=X/'SM_M24_m24_palma_iron.fbx'
bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,use_tspace=True,mesh_smooth_type='FACE')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_PalmaIron_Editable.blend'))
manifest={'key':'m24_palma_iron','file':str(file),'objects':[o.name for o in parts],
 'rear_objects':[o.name for o in parts if o.name.startswith('Rear_')],
 'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in parts),
 'sockets_ue_cm':{'SightRear':rear,'SightFront':front,'SightUp':[0,-4.10,16.30]},
 'reference':'https://usarmorment.com/pdf/sws24.pdf#page=64','dimensions':'art adaptation to selected game mesh, not real manufacturing dimensions',
 'source_frame':'metres +Y forward +Z up; FBX maps to UE cm (x,-y,z)','runtime_tested':False}
(O/'sight_authoring.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('M24_PALMA_SIGHT_EXPORTED',manifest['triangles'],flush=True)
