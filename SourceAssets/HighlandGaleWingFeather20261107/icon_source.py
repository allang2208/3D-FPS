"""Render only the production UI plate; works in a private Blender process."""
from pathlib import Path
import bpy,sys
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'Highland_GaleWing_Feather.blend'))
s=bpy.context.scene
for o in s.objects:o.hide_render=True
components=list(bpy.data.collections['01 | Atelier - editable ornamental components'].objects)
for ob in components:ob.hide_render=False;ob.hide_set(False)
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
apply_grayscale(components);neutral_output(s);s.view_settings.exposure=-1.15
w=bpy.data.worlds.new('Atelier soft room');w.use_nodes=True
n=w.node_tree.nodes.new('ShaderNodeBackground');out=next(x for x in w.node_tree.nodes if x.type=='OUTPUT_WORLD')
n.inputs[0].default_value=(.31,.31,.31,1);n.inputs[1].default_value=.44;w.node_tree.links.new(n.outputs[0],out.inputs[0]);s.world=w
target=Vector((0,0,.006))
def aim(o):o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
for name,loc,watt,sz,sz2 in [('Long silk',(-.16,-.22,.27),6,.36,.12),('Edge card',(.19,-.02,.19),5,.30,.035),('Breast fill',(.08,-.25,-.06),2,.13,.18),('Undercut',(-.21,.08,-.13),4,.24,.06)]:
    ld=bpy.data.lights.new(name,'AREA');ld.energy=watt;ld.shape='RECTANGLE';ld.size=sz;ld.size_y=sz2
    o=bpy.data.objects.new(name,ld);s.collection.objects.link(o);o.location=loc;aim(o)
d=bpy.data.cameras.new('Icon camera');cam=bpy.data.objects.new('Icon camera',d);s.collection.objects.link(cam)
cam.location=(.024,-.64,.062);aim(cam);d.type='ORTHO';d.ortho_scale=.414;s.camera=cam
s.render.engine='CYCLES';s.cycles.samples=36;s.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    for dev in prefs.devices:dev.use=dev.type=='OPTIX'
    if any(dev.use for dev in prefs.devices):s.cycles.device='GPU'
except Exception:pass
s.render.resolution_x=1024;s.render.resolution_y=650;s.render.resolution_percentage=100;s.render.film_transparent=True
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.filepath=str(P/'Icon/GaleFeather_Model.png')
bpy.ops.render.render(write_still=True)
