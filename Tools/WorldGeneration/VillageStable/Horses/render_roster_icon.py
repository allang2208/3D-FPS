"""Render the navigation subject from the same Warhorse Lite source used by the stable."""
import bpy
from mathutils import Vector
from pathlib import Path
root = Path(__file__).resolve().parents[4]
source = root / "SourceAssets/HillsVillageStable/HorsesR7/Originals/WarhorseLite.glb"
dest = root / "Content/ColdSteelUI/Icons/Navigation/horse_subject.png"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source))
scene = bpy.context.scene
rig = next(obj for obj in scene.objects if obj.type == "ARMATURE")
rig.animation_data_clear()
points = [obj.matrix_world @ v.co for obj in scene.objects if obj.type == "MESH" for v in obj.data.vertices]
def joint(name):
    return rig.matrix_world @ rig.data.bones[name].head_local
forward = joint("mouth_socket") - joint("pelvis")
forward.z = 0
forward.normalize()
side = Vector((0,0,1)).cross(forward)
eye = (side + forward*.40 + Vector((0,0,.17))).normalized()
camera_data = bpy.data.cameras.new("Navigation")
camera = bpy.data.objects.new("Navigation",camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
orientation = (-eye).to_track_quat("-Z","Y")
right,up = orientation @ Vector((1,0,0)), orientation @ Vector((0,1,0))
x = [p.dot(right) for p in points]; y = [p.dot(up) for p in points]
centre = right*((min(x)+max(x))*.5) + up*((min(y)+max(y))*.5)
camera.location = centre + eye*12
camera.rotation_euler = orientation.to_euler()
camera_data.type = "ORTHO"
camera_data.ortho_scale = max(max(x)-min(x),max(y)-min(y))*1.07
scene.render.engine = "BLENDER_WORKBENCH"
s=scene.display.shading
s.light="STUDIO";s.color_type="SINGLE";s.single_color=(.58,.61,.65)
s.show_shadows=True;s.show_cavity=True;s.cavity_type="BOTH";s.show_specular_highlight=True
scene.render.film_transparent=True
scene.render.resolution_x=scene.render.resolution_y=512;scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG";scene.render.image_settings.color_mode="RGBA"
scene.render.filepath=str(dest)
bpy.ops.render.render(write_still=True)
