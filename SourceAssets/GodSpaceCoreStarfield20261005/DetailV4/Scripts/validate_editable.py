import bpy,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];f=R/'Authored/GodSpaceCore_Starfield_V4_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(f));s=bpy.context.scene;cam=s.camera
node=next(n for n in bpy.data.materials['Core_Starfield'].node_tree.nodes if n.label=='Render camera position, updated per camera')
for i,axis in enumerate('XYZ'):
 d=node.inputs[i].driver_add('default_value').driver;d.type='SCRIPTED';v=d.variables.new();v.name='camera_coord';v.type='TRANSFORMS';v.targets[0].id=cam;v.targets[0].transform_type='LOC_'+axis;v.targets[0].transform_space='WORLD_SPACE';d.expression='camera_coord'
for image in bpy.data.images:
 if image.source=='FILE':
  image.pack();image.filepath='//Textures/'+Path(image.filepath).name
s.render.filepath='//../Previews/V4_LowAngle_Daylight_Checkpoint.png'
bpy.ops.wm.save_as_mainfile(filepath=str(f));bpy.ops.wm.open_mainfile(filepath=str(f))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
report={'reopened_in_blender':bpy.app.version_string,'mesh_objects':len(meshes),'all_file_images_packed':all(i.packed_file is not None for i in bpy.data.images if i.source=='FILE'),'images':[{'name':i.name,'size':list(i.size),'packed':i.packed_file is not None} for i in bpy.data.images if i.source=='FILE'],'camera_drivers':3,'triangle_count':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes),'material_names':sorted(set(m.name for o in meshes for m in o.data.materials))}
assert report['mesh_objects']==35 and report['all_file_images_packed'] and report['triangle_count']==53888
(R/'Receipts/editable_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
