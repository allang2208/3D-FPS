"""Author hinged QBZ sights from the current machined mesh; no preview/test run."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector, Matrix

O=Path(__file__).parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'QBZ191Machined20260913/QBZ191_Machined_Editable.blend'))
s=bpy.context.scene;rig=bpy.data.objects['SK_M4_Infima'];gun=bpy.data.objects['QBZ191_Export'];hands=bpy.data.objects['SK_Manny_Arms_Export']
root=rig.data.bones['WPN_root'].matrix_local.copy();inverse=root.inverted()
iron_indices={i for i,m in enumerate(gun.data.materials) if m.name in ['M_QBZ191_Irons_Machined','M_QBZ191_Irons_Inner']}
iron=bpy.data.materials['M_QBZ191_Irons_Machined']

def retain(mesh, predicate):
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if not predicate(f)],context='FACES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bm.to_mesh(mesh);bm.free();mesh.update()

def export(name, objects, kinds):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.export_scene.fbx(filepath=str(O/(name+'.fbx')),use_selection=True,object_types=kinds,axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)

def unwrap(ob):
    # These constant-material mechanical parts have no source atlas to retain.
    # Unwrap sidewalls as well as front faces so MikkTSpace gets valid UV axes.
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.015)
    bpy.ops.object.mode_set(mode='OBJECT')

heads=[];records=[]
s['QBZ191_SightFold']=0.0
s.id_properties_ui('QBZ191_SightFold').update(min=0.0,max=1.0,description='0 upright; 1 folded, matching the runtime 90 degree hinges')
for name,pivot,angle,rear in [('Rear',Vector((.000688,.009231,.1000)),-90,True),('Front',Vector((.000688,-.343514,.1000)),90,False)]:
    mesh=gun.data.copy()
    retain(mesh,lambda f:f.material_index in iron_indices and (((inverse@f.calc_center_median()).y>-.15)==rear))
    mesh.transform(Matrix.Translation(-pivot)@inverse)
    head=bpy.data.objects.new('SM_QBZ191_'+name+'Sight',mesh);s.collection.objects.link(head)
    unwrap(head)
    export(head.name,[head],{'MESH'})
    mesh.calc_loop_triangles()
    records.append({'name':head.name,'hinge_root_m':[pivot.x,-pivot.y,pivot.z],'axis_ue':[1,0,0],'angle_ue':-angle,'triangles':len(mesh.loop_triangles)})
    # Bone parenting uses the tail offset; cancel it so the authored hinge is
    # expressed at the WPN_root origin, exactly like the runtime socket mount.
    head.parent=rig;head.parent_type='BONE';head.parent_bone='WPN_root'
    head.matrix_parent_inverse=Matrix.Translation((0,-rig.data.bones['WPN_root'].length,0))
    head.location=pivot;head.rotation_mode='XYZ'
    driver=head.driver_add('rotation_euler',0).driver
    variable=driver.variables.new();variable.name='fold';variable.type='SINGLE_PROP'
    variable.targets[0].id_type='SCENE';variable.targets[0].id=s;variable.targets[0].data_path='["QBZ191_SightFold"]'
    driver.expression=f'fold*{math.radians(angle):.12f}'
    heads.append(head)

retain(gun.data,lambda f:f.material_index not in iron_indices)

# Fixed feet and axle pins remain at the measured rail crown while the sight
# assemblies rotate. Axles overlap their housings, leaving no floating joint.
fixed=[]
def fixed_part(name,vertices,faces,bevel=0):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata([root@Vector(v) for v in vertices],[],faces);mesh.materials.append(iron);mesh.update()
    ob=bpy.data.objects.new(name,mesh);s.collection.objects.link(ob)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    for f in bm.faces:f.smooth=True
    for e in bm.edges:e.smooth=not(e.is_manifold and e.calc_face_angle(0)>math.radians(38))
    bm.to_mesh(mesh);bm.free()
    uv=mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:
        p=inverse@mesh.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(p.x*100,p.z*100)
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    if bevel:
        mod=ob.modifiers.new('Hinge edge radius','BEVEL');mod.limit_method='ANGLE';mod.width=bevel;mod.segments=2;mod.harden_normals=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=ob.modifiers.new('Hinge face normals','WEIGHTED_NORMAL');mod.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    unwrap(ob)
    ob.vertex_groups.new(name='WPN_root').add(list(range(len(ob.data.vertices))),1,'REPLACE')
    ob.parent=rig;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
    ob.modifiers.new('Fixed rail binding','ARMATURE').object=rig;fixed.append(ob)

for name,y in [('Rear',.009231),('Front',-.343514)]:
    x=.000688;z=.1000;rail=.096473
    vertices=[(x+dx,y+dy,h) for h in [rail,z-.0006] for dy in [-.0032,.0032] for dx in [-.006,.006]]
    faces=[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]
    fixed_part(name+'_Sight_FixedFoot',vertices,faces,.00018)
    n=64;vertices=[];faces=[]
    for dx in [-.0063,.0063]:
        for i in range(n):
            a=math.tau*i/n;vertices.append((x+dx,y+.0026*math.cos(a),z+.0026*math.sin(a)))
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    fixed_part(name+'_Sight_FixedAxle',vertices,faces,.00010)

bpy.ops.object.select_all(action='DESELECT');gun.select_set(True)
for ob in fixed:ob.select_set(True)
bpy.context.view_layer.objects.active=gun;bpy.ops.object.join()
rig.data.pose_position='REST';bpy.context.view_layer.update()
export('SK_QBZ191_Manny',[rig,gun,hands],{'ARMATURE','MESH'})
rig.data.pose_position='POSE';bpy.context.view_layer.update()
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'QBZ191_Folding_Editable.blend'))
(O/'folding-sights.json').write_text(json.dumps({'source':'QBZ191Machined20260913/QBZ191_Machined_Editable.blend','rail_crown_m':.096473,'fold_duration_seconds':.18,'heads':records,'status':'authored and exported; no rendered or gameplay acceptance'},indent=2))
print('QBZ_FOLDING_EXPORTED',json.dumps(records),flush=True)
