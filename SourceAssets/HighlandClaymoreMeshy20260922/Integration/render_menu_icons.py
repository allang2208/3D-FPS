"""Render production inventory/workbench textures from the delivered meshes."""
import bpy,json,shutil
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent;OUT=P/'Icons';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'HighlandClaymore_Modular_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
data=json.loads((P/'exports.json').read_text(encoding='utf-8'))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    devices=[d for d in prefs.devices if d.type=='OPTIX']
    for d in prefs.devices:d.use=d in devices
    if devices:scene.cycles.device='GPU'
except Exception:pass
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
scene.world=bpy.data.worlds.new('Highland neutral menu studio');scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.2,.2,.2,1);bg.inputs['Strength'].default_value=.65
camera=bpy.data.objects.new('Menu camera blade left',bpy.data.cameras.new('Menu camera blade left'));scene.collection.objects.link(camera);scene.camera=camera
camera.data.type='ORTHO';camera.data.clip_start=.001
camera.rotation_euler=Matrix(((0,1,0),(0,0,-1),(-1,0,0))).to_euler()
lamps=[]
for name,offset,energy,size in [('Key',(.38,-.60,.35),95,.75),('Fill',(-.32,-.42,-.15),45,.65),('Rim',(.12,.28,.30),65,.5)]:
    lamp=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));scene.collection.objects.link(lamp);lamp.data.energy=energy;lamp.data.shape='DISK';lamp.data.size=size;lamps.append((lamp,Vector(offset)))
jobs=[{'mesh':data['world_mesh'],'filename':'ue_highland_claymore.png','slot':'inventory','id':'factory'}]
for row in data['parts']:
    jobs.append({'mesh':row['mesh'],'filename':'ue_highland_claymore_'+row['slot']+'_'+('false' if row['id']=='factory' else row['id'])+'.png','slot':row['slot'],'id':row['id']})
for row in jobs:
    obj=bpy.data.objects[row['mesh']]
    for other in scene.objects:
        if other.type=='MESH':other.hide_render=other!=obj
    obj.hide_set(False);obj.location=Vector();bpy.context.view_layer.update()
    points=[Vector(v) for v in obj.bound_box];center=sum(points,Vector())/8
    size=max(max(p.x for p in points)-min(p.x for p in points),max(p.z for p in points)-min(p.z for p in points))
    camera.location=center+Vector((0,-1.5,0));camera.data.ortho_scale=size/.83
    for lamp,offset in lamps:lamp.location=center+offset;lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/row['filename']);bpy.ops.render.render(write_still=True)
    print('HIGHLAND_MENU_ICON '+row['filename'],flush=True)
    if row['slot']!='inventory' and row['id']=='factory':
        shutil.copy2(OUT/row['filename'],OUT/('ue_highland_claymore_category_'+row['slot']+'.png'))
bpy.ops.wm.save_as_mainfile(filepath=str(P/'HighlandClaymore_MenuIcons_Editable.blend'))
(P/'icons.json').write_text(json.dumps({'resolution':[1024,1024],'format':'RGBA transparent PNG','orientation':'blade +Z projects left; front -Y; no mirroring','jobs':jobs,'production_only':True},indent=2),encoding='utf-8')
print('HIGHLAND_MENU_ICONS_COMPLETE',flush=True)
