import bpy
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
for name in ('JiLei_V14_Editable.blend','JiLei_V14_InspectionScene.blend'):
 bpy.ops.wm.open_mainfile(filepath=str(P/name));bpy.context.preferences.filepaths.save_version=0
 bpy.context.scene.view_layers[0].material_override=None
 bpy.ops.object.select_all(action='DESELECT')
 core=bpy.data.objects.get('01_TaperedForgedCore')
 if core:core.hide_set(False);core.select_set(True);bpy.context.view_layer.objects.active=core
 for screen in bpy.data.screens:
  for area in screen.areas:
   if area.type=='VIEW_3D':
    space=area.spaces.active;space.region_3d.view_location=Vector((-.000445,0,.916));space.region_3d.view_distance=.32
    space.region_3d.view_rotation=Vector((.35,-.8,.20)).to_track_quat('Z','Y');space.shading.type='MATERIAL'
 bpy.ops.wm.save_as_mainfile(filepath=str(P/name))
 print('OPEN_VIEW_FRAMED',name,flush=True)
