"""Finish the migrated treasure as a hollow, hinged 3D container. No renders/tests."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

HERE=Path(__file__).parent; OUT=HERE/'Authored'; OUT.mkdir(parents=True,exist_ok=True)
PREVIOUS=HERE.parent/'GamedevTreasureChest20260922/Authored'
bpy.ops.wm.open_mainfile(filepath=str(PREVIOUS/'GamedevTreasureChest_UE.blend'))
scene=bpy.context.scene
arm=bpy.data.objects['GamedevTreasureChestRig']
for obj in list(scene.objects):
    if obj!=arm:bpy.data.objects.remove(obj,do_unlink=True)
arm.animation_data_clear();arm.pose.bones['Lid'].rotation_quaternion=Quaternion()
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01;scene.render.fps=30
IRON,GOLD,INNER=range(3)
names=['Treasure_BlackIron','Treasure_AntiqueGold','Treasure_Interior']
materials=[bpy.data.materials[n] for n in names]
parts=[];pieces=[]
mapping=Matrix(((0,-.65,0,0),(.65,0,0,0),(0,0,.65,0),(0,0,0,1)))

def finish(obj,name,mat,bone='Root',bevel=0):
    obj.name=name
    if not obj.data.materials:
        obj.data.materials.append(materials[mat])
    bpy.context.view_layer.objects.active=obj
    obj.select_set(True)
    if bevel:
        mod=obj.modifiers.new('MachinedEdges','BEVEL');mod.width=bevel;mod.segments=3
        mod.affect='EDGES';mod.limit_method='ANGLE'
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.context.view_layer.update()
    obj.data.transform(mapping @ obj.matrix_world)
    obj.matrix_world=Matrix.Identity(4)
    obj.data.update()
    uv=obj.data.uv_layers.new(name='UV0_Physical') if not obj.data.uv_layers else obj.data.uv_layers[0]
    for face in obj.data.polygons:
        axis=max(range(3),key=lambda i:abs(face.normal[i]))
        for index in face.loop_indices:
            p=obj.data.vertices[obj.data.loops[index].vertex_index].co/100
            uv.data[index].uv=(p.y,p.z) if axis==0 else (p.x,p.z) if axis==1 else (p.x,p.y)
    group=obj.vertex_groups.new(name=bone);group.add(list(range(len(obj.data.vertices))),1,'REPLACE')
    obj.select_set(False);parts.append(obj);pieces.append(dict(name=name,bone=bone))
    return obj

def box(name,loc,size,mat=GOLD,bone='Root',bevel=1):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    obj=bpy.context.object;obj.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(obj,name,mat,bone,bevel)

def cylinder(name,loc,radius,depth,mat=GOLD,bone='Root',axis='Z',bevel=.4):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=radius,depth=depth,location=loc)
    obj=bpy.context.object
    if axis=='X':obj.rotation_euler.y=math.pi/2
    if axis=='Y':obj.rotation_euler.x=math.pi/2
    for face in obj.data.polygons:face.use_smooth=len(face.vertices)==4
    return finish(obj,name,mat,bone,bevel)

def curve(name,points,radius=1.25,mat=GOLD,bone='Root'):
    data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D'
    data.resolution_u=12;data.bevel_depth=radius;data.bevel_resolution=3;data.use_fill_caps=True
    spline=data.splines.new('BEZIER');spline.bezier_points.add(len(points)-1)
    for p,co in zip(spline.bezier_points,points):
        p.co=co;p.handle_left_type='AUTO';p.handle_right_type='AUTO'
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    return finish(bpy.context.object,name,mat,bone)

def raw(name,verts,faces,indices,bone='Lid',smooth=True):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces)
    for m in materials:data.materials.append(m)
    for face,mat in zip(data.polygons,indices):face.material_index=mat;face.use_smooth=smooth
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    return finish(obj,name,IRON,bone)

def arch_shell(name,x0,x1,outer_r,outer_h,inner_r,inner_h,outer_mat=IRON,inner_mat=INNER):
    # A closed-thickness arch, with an open underside; never a filled box or bottom plate.
    n=80;verts=[]
    for x in (x0,x1):
        for r,h in ((outer_r,outer_h),(inner_r,inner_h)):
            verts.extend((x,-r*math.cos(i*math.pi/n),99+h*math.sin(i*math.pi/n)) for i in range(n+1))
    def v(side,inner,i):return (side*2+inner)*(n+1)+i
    faces=[];ids=[]
    for i in range(n):
        faces += [(v(0,0,i),v(1,0,i),v(1,0,i+1),v(0,0,i+1)),
                  (v(0,1,i+1),v(1,1,i+1),v(1,1,i),v(0,1,i))]
        ids += [outer_mat,inner_mat]
        for side in (0,1):
            faces.append((v(side,0,i),v(side,0,i+1),v(side,1,i+1),v(side,1,i)));ids.append(outer_mat)
    for i in (0,n):
        faces.append((v(0,0,i),v(0,1,i),v(1,1,i),v(1,0,i)));ids.append(outer_mat)
    return raw(name,verts,faces,ids)

def end_panel(name,x0,x1):
    n=80;arc=[(-75*math.cos(i*math.pi/n),99+61*math.sin(i*math.pi/n)) for i in range(n+1)]
    verts=[(x,y,z) for x in (x0,x1) for y,z in arc]
    faces=[tuple(range(n,-1,-1)),tuple(range(n+1,2*(n+1)))];ids=[IRON,IRON]
    for i in range(n+1):
        j=(i+1)%(n+1);faces.append((i,j,n+1+j,n+1+i));ids.append(IRON)
    return raw(name,verts,faces,ids,smooth=False)

# Four real walls and a recessed floor. The cavity is 176 x 128 x 69 cm in source units.
box('Body_Floor',(0,0,18),(190,142,8),IRON,bevel=2)
for side in (-1,1):
    box('Body_FrontBack_'+str(side),(0,side*68,55),(190,6,74),IRON,bevel=1.6)
    box('Body_LeftRight_'+str(side),(side*92,0,55),(6,130,74),IRON,bevel=1.6)
    box('Lining_FrontBack_'+str(side),(0,side*64.7,57),(176,1,68),INNER,bevel=.3)
    box('Lining_LeftRight_'+str(side),(side*88.7,0,57),(1,128,68),INNER,bevel=.3)
box('Lining_RecessedFloor',(0,0,22.4),(177,129,1.2),INNER,bevel=.4)
for z in (22,84):
    for side in (-1,1):
        box('Frame_FrontBack_%s_%s'%(side,z),(0,side*74,z),(199,7,8),bevel=1.2)
        box('Frame_LeftRight_%s_%s'%(side,z),(side*98,0,z),(7,149,8),bevel=1.2)
for x in (-96,96):
    for y in (-72,72):
        box('Corner_%s_%s'%(x,y),(x,y,54),(9,9,81),bevel=1.8)
for side in (-1,1):
    box('Mouth_FrontBack_'+str(side),(0,side*70,93),(202,12,6),bevel=1)
    box('Mouth_LeftRight_'+str(side),(side*95,0,93),(12,128,6),bevel=1)
for index,(x,y) in enumerate(((-78,-56),(78,-56),(-78,56),(78,56))):
    box('Foot_'+str(index),(x,y,8),(24,22,16),bevel=3)
    box('Foot_IronPad_'+str(index),(x,y,1.5),(20,18,3),IRON,bevel=.7)

# Riveted bands and finer front scrollwork retain the old chest's identity.
for z in (22,84):
    for x in (-84,-62,-40,-18,18,40,62,84):
        for side in (-1,1):cylinder('BandRivet_%s_%s_%s'%(x,z,side),(x,side*78,z),1.65,1.5,axis='Y',bevel=.5)
for x in (-96,96):
    for z in (34,54,74):cylinder('CornerRivet_%s_%s'%(x,z),(x,-77.3,z),1.7,1.4,axis='Y')
for side in (-1,1):
    upper=[(side*x,-79,z) for x,z in ((25,56),(42,74),(65,74),(77,63),(70,55),(54,59),(57,65))]
    lower=[(side*x,-79,z) for x,z in ((25,49),(42,33),(66,34),(79,47),(65,51),(58,46))]
    curve('Scroll_Upper_'+str(side),upper,1.45)
    curve('Scroll_Lower_'+str(side),lower,1.25)
    curve('Scroll_Tendril_'+str(side),[(side*35,-79,46),(side*50,-79,52),(side*48,-79,64)],.85)

cylinder('Lock_Escutcheon',(0,-79.5,60),23,3.8,axis='Y',bevel=1)
cylinder('Lock_DarkInset',(0,-82,60),19.5,1,IRON,axis='Y',bevel=.2)
box('Lock_BrassPlate',(0,-83.4,60),(29,3.5,37),bevel=3)
for x in (-10.5,10.5):
    for z in (47,73):cylinder('LockRivet_%s_%s'%(x,z),(x,-85.4,z),1.2,1,axis='Y',bevel=.25)
cylinder('Keyhole_Round',(0,-85.4,63),3.3,1.2,INNER,axis='Y',bevel=.15)
box('Keyhole_Stem',(0,-85.5,57.5),(3.5,1.2,8),INNER,bevel=.35)
for side in (-1,1):
    x=side*103.5
    for y in (-26,26):
        box('Handle_Backplate_%s_%s'%(side,y),(x,y,60),(3,14,20),bevel=2)
        cylinder('Handle_Pin_%s_%s'%(side,y),(x+side*3,y,62),3.5,7,axis='X')
    curve('DropHandle_'+str(side),[(x+side*6,-26,62),(x+side*8,-27,43),
          (x+side*8,0,38),(x+side*8,27,43),(x+side*6,26,62)],2.65)

# The lid has a curved inner wall and thin solid end plates, no false flat underside.
arch_shell('Lid_Vault',-101,101,76,62,71.5,57.5)
end_panel('Lid_EndLeft',-101,-97.5);end_panel('Lid_EndRight',97.5,101)
for index,x in enumerate((-87,0,87)):
    width=8 if x else 9
    arch_shell('Lid_GoldStrap_'+str(index),x-width/2,x+width/2,78,64,75.8,61.8,GOLD,GOLD)
    for degrees in (12,38,64,90,116,142,168):
        t=math.radians(degrees)
        # Small rivet heads seated on the arched strap, aligned to its local normal.
        loc=(x,-78.4*math.cos(t),99+64.4*math.sin(t))
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=1,location=loc)
        obj=bpy.context.object;obj.scale=(1.35,1.35,1.35)
        for face in obj.data.polygons:face.use_smooth=True
        finish(obj,'LidStrapRivet_%s_%s'%(index,degrees),GOLD,'Lid')
for side in (-1,1):
    box('Lid_EdgeRail_'+str(side),(0,side*76.5,100),(207,5,4),bone='Lid',bevel=1)
    arch_shell('Lid_EndArch_'+str(side),side*102-2,side*102+2,77,63,73.5,59.5,GOLD,GOLD)
    x=side*103.5
    curve('Lid_EndScroll_'+str(side),[(x,-38,113),(x,-21,132),(x,4,135),(x,21,124),(x,8,114),(x,-5,120)],1.25,bone='Lid')
for x in (-62,62):
    cylinder('HingeBarrel_'+str(x),(x,76,99),5.8,32,axis='X',bevel=.75)
    box('HingeBodyPlate_'+str(x),(x,75,83),(24,4,22),bevel=1.4)
    box('HingeLidPlate_'+str(x),(x,76,109),(23,3,21),bone='Lid',bevel=1.4)
box('Lid_Latch',(0,-79.5,91),(14,4,29),bone='Lid',bevel=2)
box('Lid_LatchInset',(0,-81.7,91),(5,.6,18),IRON,'Lid',bevel=.7)
cylinder('Lid_MedallionBase',(0,0,165),25,3.6,bone='Lid',bevel=1)
cylinder('Lid_MedallionInset',(0,0,167),21,1.2,IRON,'Lid',bevel=.3)
cylinder('Lid_MedallionCore',(0,0,168),8,2.3,bone='Lid',bevel=.6)
for i in range(12):
    angle=2*math.pi*i/12
    direction=Vector((math.cos(angle),math.sin(angle),0));tangent=Vector((-math.sin(angle),math.cos(angle),0))
    points=[direction*9, direction*17+tangent*2.3, direction*21,direction*17-tangent*2.3]
    verts=[(p.x,p.y,z) for z in (167.1,168.2) for p in points]
    raw('Lid_MedallionRay_'+str(i),verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],[GOLD]*6,smooth=False)

# Join without losing per-face material slots, and bind to the unchanged imported hinge skeleton.
bpy.ops.object.select_all(action='DESELECT')
for obj in parts:obj.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join()
mesh=bpy.context.object;mesh.name='SK_GamedevTreasureChest'
tri=mesh.modifiers.new('ExportTriangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
mesh.parent=arm;mod=mesh.modifiers.new('RigidHinge','ARMATURE');mod.object=arm
scene.cursor.location=(0,0,0)
lid=arm.pose.bones['Lid'];lid.rotation_mode='QUATERNION'
axis=arm.data.bones['Lid'].matrix_local.to_3x3().inverted()@Vector((0,1,0))

def selection():
    bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=arm
def fbx(name,animated=False):
    selection();bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,
        object_types={'MESH','ARMATURE'},apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',
        axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',add_leaf_bones=False,
        bake_anim=animated,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
fbx('SK_GamedevTreasureChest')
for name,angle in [('SM_TreasureChest_Closed',0),('SM_TreasureChest_Open',-58)]:
    lid.rotation_quaternion=Quaternion(axis,math.radians(angle));bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get();data=bpy.data.meshes.new_from_object(mesh.evaluated_get(dg),depsgraph=dg)
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH'},
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',bake_anim=False)
    bpy.data.objects.remove(obj,do_unlink=True)
lid.rotation_quaternion=Quaternion();selection();scene.frame_set(1);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GamedevTreasureChest_Finished.blend'))
# Keep the same opening action with the rebuilt mesh in a separate editable source.
def ease(t):
    t=max(0,min(1,t));return t*t*(3-2*t)
for frame in range(1,32):
    t=(frame-1)/30;angle=60*ease((t-.08)/.70) if t<=.78 else 60-2*ease((t-.78)/.22)
    lid.rotation_quaternion=Quaternion(axis,-math.radians(angle));lid.keyframe_insert(data_path='rotation_quaternion',frame=frame)
arm.animation_data.action.name='A_TreasureChest_Opening'
scene.frame_start=1;scene.frame_end=31;scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GamedevTreasureChest_Finished_Opening.blend'))
record=dict(parts=pieces,triangles=len(mesh.data.polygons),rig='Unchanged Root/Lid from migrated source',
            body='Hollow walls, recessed floor and open rim',lid='Thick curved vault with inside surface and end plates',
            source_scale=.65,unit='cm',opening_animation_unchanged=True,rendered=False,tested=False)
(HERE/'authoring.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('TREASURE_REBUILT '+json.dumps({k:v for k,v in record.items() if k!='parts'}))
