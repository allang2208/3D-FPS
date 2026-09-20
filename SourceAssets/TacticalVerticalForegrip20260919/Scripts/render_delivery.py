"""Render requested material presentation and the actual-model attachment icon."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).resolve().parents[1]
D=O/'Integration';gun=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'M4'
P=D/'Preview'/gun;P.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(D/gun/'Source/TacticalVerticalForegrip_Integrated.blend'))
bpy.context.preferences.filepaths.save_version=0
s=bpy.context.scene
obj=bpy.data.objects['SM_TacticalVerticalForegrip']
if gun=='AKM':
 mount=Matrix(json.loads((O.parent/'VerticalGripFront20260911/akm/fits.json').read_text())['vertical']['grip_in_root'])
 obj.data.transform(mount.inverted())
 obj.data.update()
bpy.context.view_layer.update()
for ob in s.objects:
 ob.hide_render=ob!=obj
obj.hide_set(False)
s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True;s.cycles.device='CPU'
s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
s.render.resolution_x=1024;s.render.resolution_y=1024;s.render.resolution_percentage=100
s.view_settings.view_transform='AgX'
world=bpy.data.worlds.new('TacticalGrip_Studio');world.use_nodes=True
bg=world.node_tree.nodes.new('ShaderNodeBackground');bg.inputs[0].default_value=(.12,.14,.18,1);bg.inputs[1].default_value=.4
wo=world.node_tree.nodes.new('ShaderNodeOutputWorld');world.node_tree.links.new(bg.outputs[0],wo.inputs[0]);s.world=world
corners=[obj.matrix_world@Vector(v) for v in obj.bound_box]
lower=Vector(tuple(min(v[i] for v in corners) for i in range(3)));upper=Vector(tuple(max(v[i] for v in corners) for i in range(3)))
center=(lower+upper)*.5;extent=upper-lower;size=max(extent.x,extent.z)/.82
def point(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
for name,loc,power,size,color in [('Key',(.10,-.16,.12),.45,.12,(1,.94,.86)),('Fill',(-.13,-.10,.025),.22,.10,(.78,.88,1)),('Rim',(.05,.14,.07),.55,.09,(.85,.91,1))]:
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
 light=bpy.data.objects.new(name,data);s.collection.objects.link(light);light.location=loc;point(light,center)
camdata=bpy.data.cameras.new('MaterialCamera');cam=bpy.data.objects.new('MaterialCamera',camdata);s.collection.objects.link(cam);s.camera=cam;camdata.type='ORTHO';camdata.ortho_scale=.129
cam.location=center+Vector((0,.30,0));point(cam,center);camdata.ortho_scale=size
# +X forward projects left when viewed from +Y; keep the installation up axis vertical.
s.render.filepath=str(P/'underbarrel_tactical_vertical_foregrip.png');bpy.ops.render.render(write_still=True)
s.render.resolution_x=1400;s.render.resolution_y=1400
cam.location=center+Vector((.19,.28,.07));point(cam,center);camdata.ortho_scale=max(size,.135)
s.render.filepath=str(P/'TacticalVerticalForegrip_Material.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(D/gun/'TacticalVerticalForegrip_Render_Editable.blend'))
(P/'render_receipt.json').write_text(json.dumps({'renderer':'Blender Cycles','samples':48,'material_source':gun+'/Export/Textures, actual baked PBR','icon_forward':'+X projects left; +Z stays up','icon_resolution':[1024,1024],'preview':'TacticalVerticalForegrip_Material.png','background':'RGBA transparent','game_tested':False},indent=2),encoding='utf-8')
print('TACTICAL_GRIP_RENDER_COMPLETE',flush=True)
