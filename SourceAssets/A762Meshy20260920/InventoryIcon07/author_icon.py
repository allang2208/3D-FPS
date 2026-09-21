"""Produce the missing catalog PNG from accepted A762 geometry, no gameplay scene."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Accessories05/A762_AccessoryReady_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima']
body=[o for o in bpy.context.selected_objects if o.type=='MESH' and o.name!='SK_Manny_Arms_Export']
assert body,'Missing saved export selection'
r.data.pose_position='POSE';s.frame_set(0);bpy.context.view_layer.update()
root_inv=(r.matrix_world@r.pose.bones['WPN_root'].matrix).inverted()
dg=bpy.context.evaluated_depsgraph_get();created=[];source_names=[]
for ob in body:
    ev=ob.evaluated_get(dg);me=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=dg)
    me.materials.clear()
    for slot in ob.material_slots:me.materials.append(slot.material)
    me.transform(root_inv@ob.matrix_world)
    copy=bpy.data.objects.new('Icon_'+ob.name,me);s.collection.objects.link(copy)
    created.append(copy);source_names.append(ob.name)
auth=json.loads((O.parent/'Accessories05/authoring.json').read_text())
for key in ['RearSight','FrontSight']:
    ob=next(o for o in bpy.data.objects if o.type=='MESH' and o.data.name=='SM_A762_'+key);me=ob.data.copy()
    h=auth['meshes'][key]['hinge_ue'];me.transform(Matrix.Translation((h[0],-h[1],h[2])))
    copy=bpy.data.objects.new('Icon_'+key,me);s.collection.objects.link(copy);created.append(copy)
for ob in list(bpy.data.objects):
    if ob not in created:bpy.data.objects.remove(ob,do_unlink=True)
for c in bpy.data.collections:c.hide_render=False;c.hide_viewport=False
points=[ob.matrix_world@v.co for ob in created for v in ob.data.vertices]
lo=Vector(tuple(min(v[i] for v in points) for i in range(3)));hi=Vector(tuple(max(v[i] for v in points) for i in range(3)));center=(lo+hi)*.5
camera_data=bpy.data.cameras.new('A762_CatalogCamera');camera=bpy.data.objects.new('A762_CatalogCamera',camera_data);s.collection.objects.link(camera);s.camera=camera
camera.location=center+Vector((2.3,0,.14));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.type='ORTHO'
s.render.resolution_x=768;s.render.resolution_y=320;s.render.resolution_percentage=100
camera_data.ortho_scale=max(hi.y-lo.y,(hi.z-lo.z)*(768/320))/.90
camera_data.lens=55
def light(name,offset,power,size):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);s.collection.objects.link(ob);ob.location=center+Vector(offset);ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
light('Key',(1.0,-.5,1.1),30,1.5);light('Fill',(1,.9,.25),18,1.4);light('Edge',(-.7,.3,.8),45,1.2)
s.world=bpy.data.worlds.new('A762_IconWorld');s.world.use_nodes=True
wn=s.world.node_tree.nodes;wn.clear();bg=wn.new('ShaderNodeBackground');wo=wn.new('ShaderNodeOutputWorld');s.world.node_tree.links.new(bg.outputs['Background'],wo.inputs['Surface'])
bg.inputs['Color'].default_value=(.55,.62,.72,1);bg.inputs['Strength'].default_value=.35
s.render.use_compositing=False;s.render.use_sequencer=False
s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='OPTIX'
    if any(d.type=='OPTIX' for d in prefs.devices):s.cycles.device='GPU'
except Exception:pass
s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='8'
s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=.2
s.render.filepath=str(O/'ue_a762.png')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'A762_CatalogIcon_Editable.blend'))
print('ICON_RENDER_SETUP',s.render.engine,[(o.name,len(o.data.materials)) for o in created[:5]],flush=True)
bpy.ops.render.render(write_still=True)
(O/'authoring.json').write_text(json.dumps({'source':'Accessories05/A762_AccessoryReady_Editable.blend','source_objects':source_names,'size':[768,320],'bounds_m':[list(lo),list(hi)],'png':'ue_a762.png','role':'base catalog fallback; live configured icons remain generated in UE'},indent=2),encoding='utf-8')
print('A762_CATALOG_ICON_AUTHORED',flush=True)
