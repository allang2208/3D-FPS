"""Actual-model icon input, following the neutral metal-framed UI standard."""
import bpy,importlib.util,json
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'ManaOrbPommel_Editable.blend'))
obj=bpy.data.objects['SM_Runebound_EmpoweredManaOrb_V2']
helper=Path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
spec=importlib.util.spec_from_file_location('icon_gray',helper);gray=importlib.util.module_from_spec(spec);spec.loader.exec_module(gray)
gray.apply_grayscale([obj]);scene=bpy.context.scene;gray.neutral_output(scene)
for mat in obj.data.materials:
    p=mat.node_tree.nodes.get('Principled BSDF')
    if p:
        for link in list(p.inputs['Emission Strength'].links):mat.node_tree.links.remove(link)
        p.inputs['Emission Strength'].default_value=0.
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.render.threads_mode='FIXED';scene.render.threads=8
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100;scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
from mathutils import Vector
center=Vector((0,0,-.071))
bpy.ops.object.camera_add(location=(.035,-.34,-.012));cam=bpy.context.object;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.179;scene.camera=cam
for loc,power,size in (((-.14,-.17,.18),5,.17),((.15,-.07,.05),3,.12),((0,.13,.09),7,.12)):
    bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.data.energy=power;light.data.size=size;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(P/'mana_orb_actual_gray.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'ManaOrbPommel_IconSource.blend'))
