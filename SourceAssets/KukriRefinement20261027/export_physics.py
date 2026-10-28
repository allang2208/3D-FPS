import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'Kukri_Refinement_Editable.blend'))
for e in json.loads((P/'surfaces.json').read_text(encoding='utf-8'))['variants']:
    if 'dynamics' not in e:continue
    bpy.ops.object.select_all(action='DESELECT');obj=bpy.data.objects[e['object']]
    obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=e['fbx'],use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP',apply_unit_scale=True,add_leaf_bones=False)
