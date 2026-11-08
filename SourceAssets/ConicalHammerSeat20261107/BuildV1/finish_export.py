"""Re-export FBX after glTF's mesh cleanup, using the saved baked models."""
import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'ConicalHammerSeats_Editable.blend'))
for obj in list(bpy.context.scene.objects):
    if obj.type!='MESH':continue
    obj.hide_set(False);obj.hide_render=False
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    obj.data.validate(clean_customdata=False);obj.data.update()
    bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='COPY',embed_textures=False)
    bpy.ops.export_scene.gltf(filepath=str(P/'Export'/(obj.name+'.glb')),use_selection=True,export_format='GLB',export_materials='EXPORT')
    obj.hide_set(True);obj.hide_render=True
bpy.data.objects['SM_SteelWarhammer_ConicalSeat_V1'].hide_set(False)
bpy.data.objects['SM_SteelWarhammer_ConicalSeat_V1'].hide_render=False
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'ConicalHammerSeats_Editable.blend'))
print('CONICAL_SEAT_FINAL_EXPORT_SAVED',flush=True)
