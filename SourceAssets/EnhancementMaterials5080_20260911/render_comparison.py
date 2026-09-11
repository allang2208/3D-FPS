import bpy,math,sys
from mathutils import Vector,Matrix
from pathlib import Path
P=Path(__file__).parent
selected='selected' in sys.argv
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=64;s.cycles.use_denoising=True;s.cycles.transmission_bounces=12
s.render.resolution_x=1800;s.render.resolution_y=1000 if selected else 1750;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('Uniform gray studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.13,.15,.17,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.55
rot=Matrix.Rotation(math.radians(14),4,'X')@Matrix.Rotation(math.radians(-28),4,'Z')
cases=[('enhancement_stone','STONE / 20K + BAKED NORMAL',-.68,0),('magic_dust','DUST / 12K + SEPARATE GLASS',.68,0)] if selected else [('enhancement_stone_baseline','STONE / 512',-.68,.70),('enhancement_stone_high','STONE / 1024 CASCADE',.68,.70),('magic_dust_baseline','DUST / 512',-.68,-.70),('magic_dust_high','DUST / 1024 CASCADE',.68,-.70)]
white=bpy.data.materials.new('Label');white.use_nodes=True
nt=white.node_tree;nt.nodes.clear();em=nt.nodes.new('ShaderNodeEmission');em.inputs['Color'].default_value=(.65,.72,.80,1);out=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(em.outputs[0],out.inputs['Surface'])
for tag,label,x,z in cases:
    before=set(bpy.context.scene.objects)
    if not selected and not list(P.glob(tag+'_textured_master*.glb')):
        bpy.ops.object.text_add(location=(x,-.2,z),rotation=(math.pi/2,0,0));txt=bpy.context.object;txt.data.body=label+'\nUNVERIFIED\nHOST OFFLINE';txt.data.align_x='CENTER';txt.data.size=.075;txt.data.materials.append(white)
        continue
    source=P/'Delivery'/(tag+'.glb') if selected else next(P.glob(tag+'_textured_master*.glb'))
    bpy.ops.import_scene.gltf(filepath=str(source))
    objects=[o for o in s.objects if o not in before and o.type=='MESH']
    points=[o.matrix_world@Vector(v) for o in objects for v in o.bound_box]
    lo=Vector(tuple(min(p[i] for p in points) for i in range(3)));hi=Vector(tuple(max(p[i] for p in points) for i in range(3)));center=(lo+hi)/2;size=max(hi-lo)
    for o in objects:
        transform=o.matrix_world.copy()
        for v in o.data.vertices:v.co=(rot@((transform@v.co-center)/size))*.94+Vector((x,0,z))
        o.matrix_world=Matrix.Identity(4)
        if 'Glass vessel' in o.name:o.visible_shadow=False
    bpy.ops.object.text_add(location=(x,-.2,z-.66),rotation=(math.pi/2,0,0));txt=bpy.context.object;txt.data.body=label;txt.data.align_x='CENTER';txt.data.size=.063;txt.data.materials.append(white)
bpy.ops.object.camera_add(location=(0,-8,-.05));cam=bpy.context.object;cam.rotation_euler=(Vector((0,0,-.05))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=2.9;s.camera=cam
for rotation,energy in [((25,-20,-25),1.4),((60,10,125),1.0),((-45,0,0),.7),((90,0,0),1.6)]:
    bpy.ops.object.light_add(type='SUN');o=bpy.context.object;o.rotation_euler=tuple(math.radians(v) for v in rotation);o.data.energy=energy;o.data.angle=.25
s.view_settings.view_transform='AgX'
tag='selected_models' if selected else 'quality_comparison'
s.render.filepath=str(P/(tag+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/(tag+'.blend')))
