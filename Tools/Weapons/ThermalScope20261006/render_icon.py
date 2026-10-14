"""Produce the shared monochrome icon source from the actual authored master."""
import bpy,importlib.util
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parents[3];O=P/'SourceAssets/ThermalScopeRuntime20261007';O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'SourceAssets/ThermalScope20261006/Model/ThermalScope_Editable.blend'))
helper=Path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
spec=importlib.util.spec_from_file_location('gray',helper);gray=importlib.util.module_from_spec(spec);spec.loader.exec_module(gray)
gray.apply_grayscale([o for o in bpy.context.scene.objects if o.type=='MESH'])
target=Vector((-.002,0,.028))
def look(ob):ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(-.042,.25,.05));cam=bpy.context.object;look(cam);cam.data.type='ORTHO';cam.data.ortho_scale=.145;bpy.context.scene.camera=cam
for p,power,size in [((.09,.07,.17),16,.13),((-.10,.03,.075),10,.09),((0,-.1,.13),20,.10)]:
    bpy.ops.object.light_add(type='AREA',location=p);lamp=bpy.context.object;lamp.data.energy=power;lamp.data.size=size;look(lamp)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=48;s.render.resolution_x=s.render.resolution_y=1024;s.render.resolution_percentage=100
s.render.film_transparent=True;s.world=bpy.data.worlds.new('Thermal icon studio');s.world.color=(.15,.15,.15);s.view_settings.view_transform='AgX';gray.neutral_output(s)
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.filepath=str(O/'thermal-icon-source.png')
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'ThermalIcon_Editable.blend'))
bpy.ops.render.render(write_still=True)
print('THERMAL_ICON_SOURCE_SAVED '+s.render.filepath,flush=True)
