"""Explicitly requested Boss mesh/material inspection, entirely outside Unreal."""
import sys,json,math
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Scripts'))
from lookdev import bind
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
stage=args[0] if args else 'after'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authored/Dungeon_BossPumpHall.blend'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
report=dict(stage=stage,mesh_count=len(objects),triangles=sum(len(o.data.polygons) for o in objects),
    triangles_by_mesh={o.name:len(o.data.polygons) for o in objects},
    original_node_materials=sum(m.use_nodes for m in bpy.data.materials),
    original_image_bindings=sum(sum(n.type=='TEX_IMAGE' and n.image is not None for n in m.node_tree.nodes) for m in bpy.data.materials if m.node_tree),
    uv_missing=[o.name for o in objects if not o.data.uv_layers],
    nonfinite_vertices=[o.name for o in objects if any(not math.isfinite(v) for p in o.data.vertices for v in p.co)],
    bindings=bind(),scope='Blender source geometry/material inspection; no UE or gameplay tests')
(ROOT/'Receipts'/('model-inspection-'+stage+'.json')).write_text(json.dumps(report,indent=2))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type=='OPTIX'
    scene.cycles.device='GPU'
except Exception:scene.cycles.device='CPU'
scene.cycles.max_bounces=6
scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Boss inspection ambient');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.2,.25,.3,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.15
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=1.25
cfg=json.loads((ROOT/'Config/rooms.json').read_text())['rooms'][0]
for i,l in enumerate(cfg['lights']):
    lamp=bpy.data.lights.new('Preview fixture '+str(i),'AREA');lamp.energy=l['lumens']*.22
    lamp.shape='RECTANGLE';lamp.size=1.1;lamp.size_y=.3;lamp.color=(1,.67,.36) if l['warm'] else (.72,.84,1)
    obj=bpy.data.objects.new(lamp.name,lamp);scene.collection.objects.link(obj);obj.location=l['at'];obj.location.z-=.13
# Wide low-energy ceiling bounce makes details readable in this Blender inspection rig.
for x,y in [(-7,10),(7,17),(0,24)]:
    lamp=bpy.data.lights.new('Inspection bounce','AREA');lamp.energy=850;lamp.size=6;lamp.color=(.68,.76,.85)
    obj=bpy.data.objects.new(lamp.name,lamp);scene.collection.objects.link(obj);obj.location=(x,y,7.9)
camera=bpy.data.cameras.new('Boss review camera');obj=bpy.data.objects.new(camera.name,camera);scene.collection.objects.link(obj);scene.camera=obj
out=ROOT/'Previews';out.mkdir(exist_ok=True)
views=[('overview',(-.2,1.2,2.3),(0,16,3.2),19),('pump',(-1.2,6.0,2.2),(-4.7,11.1,1.7),34),('gallery',(-8.2,8.0,4.9),(-12.4,16.0,3.6),28),('receiver',(4.5,16.3,2.2),(7.5,19.4,1.8),45),('gauge',(-6.7,9.1,1.4),(-6.28,9.98,1.23),50),('atmosphere',(-1.3,2,1.9),(0,16,3.1),20)]
views=[v for v in views if v[0]!='atmosphere']+[
    ('pipe',(-2.2,8.8,4.4),(-4.32,11.44,4.37),62),
    ('cable',(-7.65,8.3,3.2),(-5.2,9.7,2.35),38),
    ('ceiling',(-6.4,8.2,6.9),(-10,10.25,8.20),23),
    ('atmosphere',(-1.3,2,1.9),(0,16,3.1),20)]
if len(args)>1:views=[v for v in views if v[0] in args[1:]]
for name,pos,target,lens in views:
    scene.view_settings.exposure=1.25
    review_light=None
    if name=='ceiling':
        scene.view_settings.exposure=.4
        lamp=bpy.data.lights.new('Ceiling detail inspection fill','AREA');lamp.energy=90;lamp.size=3
        review_light=bpy.data.objects.new(lamp.name,lamp);scene.collection.objects.link(review_light);review_light.location=(-8,9.8,7.2)
        review_light.rotation_euler=(Vector((-10,10,8.23))-review_light.location).to_track_quat('-Z','Y').to_euler()
    if name=='atmosphere':
        scene.cycles.samples=64;scene.view_settings.exposure=.40
        for light in bpy.data.lights:
            if light.name.startswith('Inspection bounce'):light.energy=180
    obj.location=pos;obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler();camera.lens=lens;camera.clip_end=140
    scene.render.filepath=str(out/(stage+'-'+name+'.png'));bpy.ops.render.render(write_still=True)
    if review_light:bpy.data.objects.remove(review_light,do_unlink=True)
if stage!='before':
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/Dungeon_BossPumpHall_Lookdev.blend'))
print('BOSS_SOURCE_INSPECTION',json.dumps(report),flush=True)
