import bpy,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent;MODEL=ROOT.parent/'SolidRepairV19'
bpy.ops.wm.open_mainfile(filepath=str(MODEL/'Staff_SolidCrystal_V19.blend'))
new=runpy.run_path(str(ROOT/'blender_quartz_material.py'))['create_quartz_material']()
old=bpy.data.materials.get('M_Staff_QuartzV19')
if old:old.user_remap(new)
bpy.ops.wm.save_as_mainfile(filepath=str(MODEL/'Staff_SolidCrystal_V19.blend'))
manifest=json.loads((MODEL/'Export/meshes.json').read_text())
for name in ('SM_Staff_Base','SM_Staff_head_crystal_false'):
    obj=bpy.data.objects[name]
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(MODEL/'Export'/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,apply_scale_options='FBX_SCALE_ALL',path_mode='AUTO',embed_textures=False)
    entry=next(e for e in manifest if e['name']==name);entry['materials']=[m.name for m in obj.data.materials if m]
(MODEL/'Export/meshes.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('STAFF_V20_BLEND_AND_FBX_SAVED')
