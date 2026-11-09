"""Production artwork for the factory parts, rendered from the split source meshes."""
from pathlib import Path
import json,bpy,sys
from mathutils import Vector
root=Path(__file__).resolve().parents[1];out=root/'Repair04/Icons';out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(root/'M249_Editable.blend'),use_scripts=False)
groups={'body':['Receiver'],'barrel':['Barrel'],'muzzle':['Muzzle'],'stock':['Stock'],'cover':['Cover'],
 'magnifier':['Magnifier','MagnifierGlass','MagnifierReticle'],'box':['Box'],'bipod':['BipodMount','LegLeft','LegRight'],
 'handguard':['Handguard'],'foregrip':['Foregrip'],'reargrip':['RearGrip'],'trigger':['Trigger'],'handle':['Handle'],'tray':['Tray'],'carry':['Carry']}
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=512;scene.render.resolution_y=320;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
scene.world=bpy.data.worlds.new('Factory studio');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.35,.35,.35,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
weapon='--weapon' in sys.argv
if weapon:
    groups={'weapon':[]};scene.render.resolution_x=768;scene.render.resolution_y=384
data=bpy.data.cameras.new('Parts');cam=bpy.data.objects.new('Parts',data);scene.collection.objects.link(cam);scene.camera=cam;data.type='ORTHO'
lights=[]
for name,offset,power,size in [('Key',(-.8,-.4,1),75,.8),('Fill',(.6,-.2,.4),45,.7),('Rim',(.2,.8,1),90,.6)]:
    lamp=bpy.data.lights.new(name,'AREA');lamp.energy=power;lamp.shape='DISK';lamp.size=size
    obj=bpy.data.objects.new(name,lamp);scene.collection.objects.link(obj);lights.append((obj,Vector(offset)))
for key,names in groups.items():
    selected=[bpy.data.objects['M249_'+name] for name in names]
    if weapon:selected=[o for o in scene.objects if o.type=='MESH' and o.name.startswith('M249_') and not str(o.get('mechanical_bone','')).startswith('New_')]
    for obj in scene.objects:
        if obj.type=='MESH':obj.hide_render=obj not in selected
    points=[obj.matrix_world@Vector(corner) for obj in selected for corner in obj.bound_box]
    center=(Vector(tuple(min(p[i] for p in points) for i in range(3)))+Vector(tuple(max(p[i] for p in points) for i in range(3))))*.5
    direction=Vector((-1,-.35,.40) if key!='magnifier' else (-1,-.8,.45)).normalized()
    cam.location=center+direction;cam.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
    inv=cam.rotation_euler.to_matrix().transposed();q=[inv@(p-center) for p in points]
    width=max(p.x for p in q)-min(p.x for p in q);height=max(p.y for p in q)-min(p.y for p in q)
    data.ortho_scale=max(width,height*(2. if weapon else 1.6))*1.3
    for lamp,offset in lights:
        lamp.location=center+offset;lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(out/(key+'.png'));bpy.ops.render.render(write_still=True)
print('M249_FACTORY_ART',len(groups),flush=True)
