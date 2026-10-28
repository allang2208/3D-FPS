"""Update the owned linen source, then rebuild only the two fitted optical heads."""
import bpy,sys
from pathlib import Path
P=Path(__file__).parent.parent
sys.path.insert(0,str(P))
from linen_surface import author_linen
bpy.ops.wm.open_mainfile(filepath=str(P/'WoodSteelLongbow_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
obj=bpy.data.objects['SM_WoodSteelLongbow_Grip_Linen'];obj.hide_set(False)
author_linen(obj)
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,use_tspace=True)
obj.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'WoodSteelLongbow_Editable.blend'))
exec(compile((P/'author_optics.py').read_text(encoding='utf8'),str(P/'author_optics.py'),'exec'),{'__file__':str(P/'author_optics.py')})
