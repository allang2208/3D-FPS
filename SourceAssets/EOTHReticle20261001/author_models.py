import bpy,json,importlib.util
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'HK416UniversalParts20260930';(O/'Exports').mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('eoth_geometry',S/'reticle_geometry.py');geometry=importlib.util.module_from_spec(spec);spec.loader.exec_module(geometry)
entries=json.loads((S/'authoring.json').read_text());result={}
for key,entry in entries.items():
 if entry['kind']!='eoth_holographic':continue
 source=Path(entry['fbx']).with_name(entry['name']+'_Editable.blend')
 bpy.ops.wm.open_mainfile(filepath=str(source));bpy.context.preferences.filepaths.save_version=0
 ob=bpy.data.objects[entry['name']];fit=geometry.replace_reticle(ob,entry['sockets_blender_m'])
 bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
 for child in ob.children:
  if child.name.startswith('SOCKET_'):child.select_set(True)
 file=O/'Exports'/(entry['name']+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
 bpy.ops.wm.save_as_mainfile(filepath=str(file.with_name(file.stem+'_Editable.blend')))
 result[key]={**entry,'fbx':str(file),'source_before':str(source),'reticle':fit}
(O/'authoring.json').write_text(json.dumps(result,indent=2));print('EOTH_RETICLE_PLANES_AUTHORED',len(result))
