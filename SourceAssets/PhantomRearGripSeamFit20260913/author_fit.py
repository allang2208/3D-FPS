import bpy,bmesh,json,sys
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).parent;OLD=P.parent/'PhantomRearGripIntegration20260913'
geo=json.loads((OLD/'geometry_sources.json').read_text())
family=sys.argv[sys.argv.index('--')+1]
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=geo[family]['source'])
rig=bpy.data.objects['SK_M4_Infima'];rig.data.pose_position='REST';bpy.context.view_layer.update()
inv=(rig.matrix_world@rig.data.bones['WPN_root'].matrix_local).inverted()
def create(name,verts,faces):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);return ob
body=[];factory=None
for ob in list(bpy.context.scene.objects):
    if ob.type!='MESH' or 'Manny' in ob.name:continue
    if family=='M4' and not (ob.name.startswith('M4_') and ob.name.endswith('_Export')):continue
    if family=='AKM' and ob.name not in ['AKM_Soviet_Native','AKM_FactoryMagazine_Preview']:continue
    if family=='QBZ191' and ob.name not in bpy.data.collections['QBZ_LOW'].objects:continue
    verts=[inv@ob.matrix_world@v.co for v in ob.data.vertices];faces=[list(f.vertices) for f in ob.data.polygons]
    if (family=='M4' and ob.name=='M4_Grip Default Unreal_Export') or (family=='QBZ191' and ob.name=='QBZ_PistolGrip'):
        factory=create('FactoryMountReference',verts,faces);continue
    if family=='AKM' and ob.name=='AKM_Soviet_Native':
        adj=[[] for v in verts]
        for e in ob.data.edges:a,b=e.vertices;adj[a].append(b);adj[b].append(a)
        seen=set();groups=[]
        for i in range(len(verts)):
            if i in seen:continue
            ids=set([i]);stack=[i];seen.add(i)
            while stack:
                for j in adj[stack.pop()]:
                    if j not in seen:seen.add(j);ids.add(j);stack.append(j)
            groups.append(ids)
        ids=groups[7];factory=create('FactoryMountReference',verts,[f for f in faces if all(v in ids for v in f)])
        bm=bmesh.new();bm.from_mesh(factory.data);bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(factory.data);bm.free()
        faces=[f for f in faces if not all(v in ids for v in f)]
    body.append(create('Receiver_'+ob.name,verts,faces))
keep=set(body+[factory])
for ob in list(bpy.context.scene.objects):
    if ob not in keep:bpy.data.objects.remove(ob,do_unlink=True)
with bpy.data.libraries.load(str(OLD/family/'PhantomRearGrip_Fitted_Editable.blend'),link=False) as (a,b):b.objects=['SM_PhantomRearGrip']
grip=b.objects[0];bpy.context.collection.objects.link(grip);grip.hide_set(False);grip.hide_render=False
factory.hide_render=True;factory.hide_set(True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16
scene.world=bpy.data.worlds.new('FitWorld');scene.world.use_nodes=True;next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs[0].default_value=(.16,.19,.23,1)
scene.render.resolution_x=900;scene.render.resolution_y=750;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
def mat(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);return m
gray=mat('Receiver clay',(.24,.28,.32));blue=mat('Grip diagnostic',(.09,.32,.5))
for ob in body:ob.data.materials.clear();ob.data.materials.append(gray)
grip.data.materials.clear();grip.data.materials.append(blue)
target=Vector((0,.02,-.015))
bpy.ops.object.camera_add(location=(.5,.02,-.015));camera=bpy.context.object;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=.19;scene.camera=camera
for loc,power,size in [((.3,-.15,.4),30,.4),((-.2,.2,.2),20,.3)]:
    bpy.ops.object.light_add(type='AREA',location=loc);lamp=bpy.context.object;lamp.data.energy=power;lamp.data.shape='DISK';lamp.data.size=size;lamp.rotation_euler=(target-lamp.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(P/(family+'_before.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/(family+'_Assembly_Editable.blend')))
print('ASSEMBLY_READY',family,flush=True)
