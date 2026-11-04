"""Reimport only the corrected axe mesh in the existing editor and save it."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
ROOT='/Game/Weapons/TacticalHatchet20261101'
package=ROOT+'/SM_TacticalHatchet'
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if package in dirty:raise RuntimeError('Axe mesh has unsaved editor changes; preserved without reimport')
ui=u.FbxImportUI()
ui.import_mesh=True;ui.import_as_skeletal=False
ui.import_materials=False;ui.import_textures=False;ui.import_animations=False
settings=ui.static_mesh_import_data
settings.combine_meshes=True;settings.auto_generate_collision=True
settings.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
settings.generate_lightmap_u_vs=False
task=u.AssetImportTask()
task.filename=str(P.parent/'Export/SM_TacticalHatchet.fbx')
task.destination_path=ROOT;task.destination_name='SM_TacticalHatchet'
task.automated=True;task.replace_existing=True;task.save=False
task.options=ui;task.factory=u.FbxFactory()
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
mesh=u.load_asset(package)
if not mesh or not task.imported_object_paths:raise RuntimeError('Corrected FBX was not imported')
mat=u.load_asset(ROOT+'/Materials/M_TacticalHatchet')
for i in range(len(mesh.static_materials)):mesh.set_material(i,mat)
nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=True
mesh.set_editor_property('nanite_settings',nanite)
if not u.TacticalHatchetImportLibrary.finalize_mesh(mesh):raise RuntimeError('Tangent authoring failed')
if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('Corrected mesh save failed')
b=mesh.get_bounding_box()
r={'saved':True,'mesh':mesh.get_path_name(),'material':mesh.get_material(0).get_path_name(),
   'nanite_enabled':mesh.get_editor_property('nanite_settings').enabled,
   'bounds_cm':{'min':[b.min.x,b.min.y,b.min.z],'max':[b.max.x,b.max.y,b.max.z]},
   'change':'Original corner normals captured before deforming vertices; transformed exactly once',
   'gameplay_tested':False}
(P/'mesh_save_receipt.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print('HATCHET_NORMALS_SAVED '+json.dumps(r))
