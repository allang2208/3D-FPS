"""Repair only the book binding's detail UVs, export, and retain editable source."""
from pathlib import Path
import bpy,json,runpy
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'AlchemyManualPersistentLeaves20261016/AlchemyManualPersistentLeaves.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False,use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
body=bpy.data.objects['SM_AlchemyManualBinding']
changed=runpy.run_path(str(ROOT/'repair_binding_uv.py'))['repair_binding_uv'](body)
mesh=body.data
mesh.calc_loop_triangles();uv=mesh.uv_layers[0].data
collapsed=0
for tri in mesh.loop_triangles:
    a,b,c=[uv[index].uv for index in tri.loops]
    collapsed+=abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))<1e-10
mesh.calc_tangents(uvmap=mesh.uv_layers[0].name)
zero_tangent=sum(loop.tangent.length<1e-4 for loop in mesh.loops)
zero_bitangent=sum(loop.bitangent.length<1e-4 for loop in mesh.loops)
report=dict(source=str(SOURCE),changed_uv=changed,vertices=len(mesh.vertices),
    triangles=len(mesh.loop_triangles),collapsed_uv_after=collapsed,
    zero_tangents_after=zero_tangent,zero_bitangents_after=zero_bitangent,rendered=False)
(ROOT/'author-receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if collapsed or zero_tangent or zero_bitangent:raise RuntimeError('Binding tangent source remains degenerate')
bpy.ops.object.select_all(action='DESELECT');body.hide_set(False);body.select_set(True)
bpy.context.view_layer.objects.active=body
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export/SM_AlchemyManualBinding.fbx'),use_selection=True,
    object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_ALL',mesh_smooth_type='FACE',use_tspace=False,
    bake_anim=False,path_mode='STRIP')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'AlchemyManualBindingTangents.blend'))
print('BOOK_BINDING_UV_REPAIRED '+json.dumps(report,ensure_ascii=False))
