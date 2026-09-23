"""PSO-only exterior mask, based on current source geometry and original UV0."""
import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;T=O/'Textures';T.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'SVDMatteDetail20260923/SVD_base_Editable.blend'))
rig=bpy.data.objects['SK_M4_Infima'];root=(rig.matrix_world@rig.data.bones['WPN_root'].matrix_local).inverted()
parts=[];counts={'exterior':0,'interior':0}
materials=[]
image=bpy.data.images.new('T_PSO_ExteriorMask',width=4096,height=4096,alpha=False);image.colorspace_settings.name='Non-Color'
for value in [0,1]:
 m=bpy.data.materials.new('PSO_MASK_'+str(value));m.use_nodes=True;n=m.node_tree.nodes;n.clear();l=m.node_tree.links
 e=n.new('ShaderNodeEmission');e.inputs['Color'].default_value=(value,value,value,1)
 out=n.new('ShaderNodeOutputMaterial');l.new(e.outputs[0],out.inputs[0]);tex=n.new('ShaderNodeTexImage');tex.image=image;n.active=tex;materials.append(m)
for name in ['SM_SVD_ScopeBody','SM_SVD_ScopeMount','SM_SVD_ScopeLens']:
 original=bpy.data.objects[name];ob=original.copy();ob.data=original.data.copy();ob.name='MASK_'+name;bpy.context.collection.objects.link(ob)
 X=root@original.matrix_world;W=original.matrix_world.copy();ob.parent=None;ob.matrix_world=W
 for mod in list(ob.modifiers):ob.modifiers.remove(mod)
 if name.endswith('Lens'):
  # Keep the repaired opaque collars; the real optical disc has its own material.
  bm=bmesh.new();bm.from_mesh(ob.data);bm.faces.ensure_lookup_table()
  bmesh.ops.delete(bm,geom=[f for f in bm.faces if 'ScopeBody' not in original.data.materials[f.material_index].name],context='FACES');bm.to_mesh(ob.data);bm.free()
 ob.data.materials.clear()
 for m in materials:ob.data.materials.append(m)
 normal_matrix=X.to_3x3().inverted().transposed()
 for f in ob.data.polygons:
  p=X@f.center;n=(normal_matrix@f.normal).normalized();radial=Vector((p.x-.0000366,0,p.z-.1023703))
  inner=(p.z>.075 and radial.length<.026 and abs(n.y)<.85 and n.dot(radial)<-.0001)
  f.material_index=0 if inner else 1;counts['interior' if inner else 'exterior']+=1
 ob.hide_render=False;parts.append(ob)
bpy.ops.object.select_all(action='DESELECT')
for ob in parts:ob.hide_set(False);ob.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1;scene.cycles.use_denoising=False
scene.render.bake.use_selected_to_active=False;scene.render.bake.use_clear=False;scene.render.bake.margin=8
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
 for device in prefs.devices:device.use=device.type=='OPTIX'
 if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
except Exception:scene.cycles.device='CPU'
bpy.ops.object.bake(type='EMIT');image.filepath_raw=str(T/'T_PSO_ExteriorMask.png');image.file_format='PNG';image.save()
(O/'mask_authoring.json').write_text(json.dumps({'source':'SVDMatteDetail20260923/SVD_base_Editable.blend','image':image.filepath_raw,'size':4096,'uv':'original structural UV0','regions':counts,'mesh_changed':False,'tests_run':False},indent=2))
print('PSO_EXTERIOR_MASK_AUTHORED',counts,flush=True)
