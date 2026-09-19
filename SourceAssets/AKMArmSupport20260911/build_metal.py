import bpy,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'AKMAttachments20260911/AKM_Attachments_Editable.blend'))
ob=bpy.data.objects['SM_AKM_optic'];mesh=ob.data
slot=next(i for i,m in enumerate(mesh.materials) if 'AdapterSteel' in m.name)
# Per-face projected UVs at a physical scale. Keep the optic body and glass UVs intact.
uv=mesh.uv_layers.active;count=0
for p in mesh.polygons:
 if p.material_index!=slot:continue
 count+=1;axis=max(range(3),key=lambda i:abs(p.normal[i]));axes=([1,2] if axis==0 else [1,0] if axis==2 else [0,2])
 for li in p.loop_indices:
  v=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]]/.12+.5,v[axes[1]]/.025+.5)
m=bpy.data.materials.new('AKM_Soviet_MountSteel');m.use_nodes=True;n=m.node_tree.nodes;n.clear();bs=n.new('ShaderNodeBsdfPrincipled');links=m.node_tree.links;output=n.new('ShaderNodeOutputMaterial');links.new(bs.outputs['BSDF'],output.inputs['Surface'])
for kind,socket in [('Base_color','Base Color'),('Metallic','Metallic'),('Roughness','Roughness'),('Normal_OpenGL','Normal')]:
 t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(O/'Metal'/f'T_AKM_Mount_{kind}.png'));t.image.colorspace_settings.name='sRGB' if kind=='Base_color' else 'Non-Color'
 if kind=='Normal_OpenGL':normal=n.new('ShaderNodeNormalMap');links.new(t.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bs.inputs[socket])
 else:links.new(t.outputs['Color'],bs.inputs[socket])
mesh.materials[slot]=m
bpy.ops.wm.save_as_mainfile(filepath=str(O/'AKM_OpticMount_Editable.blend'))
ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.hide_set(False);ob.hide_viewport=False;ob.hide_render=False;bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
bpy.ops.export_scene.fbx(filepath=str(O/'SM_AKM_optic.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False)
(O/'metal_geometry.json').write_text(json.dumps({'adapter_polygons':count,'material_slot':slot,'vertices':len(mesh.vertices),'polygons':len(mesh.polygons),'geometry_changed':False},indent=2));print('AKM_MOUNT_BUILD_PASS')
