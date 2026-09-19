"""Repair only the nine ASH static meshes from valid FBX; preserve materials."""
import unreal as u,json,math,shutil
from pathlib import Path
O=Path(__file__).parent;ROOT=O.parents[1]
if '-nullrhi' in u.SystemLibrary.get_command_line().lower().split():
 raise RuntimeError('ASH mesh finalization requires a full RHI editor; NullRHI can serialize invalid mesh bounds.')
editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
if not editor:raise RuntimeError('Run ASH mesh finalization in the full editor, not a commandlet.')
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
 raise RuntimeError('End PIE before repairing the ASH mesh build data.')
models=json.loads((O/'models.json').read_text());expected=json.loads((O/'export_bounds.json').read_text())
receipt=json.loads((O/'import.json').read_text(encoding='utf-8'))
out=ROOT/'Saved/ASH12PreviewFix';out.mkdir(exist_ok=True)
backup=O/'BeforeBoundsRepair';backup.mkdir(exist_ok=True)
A=u.AssetToolsHelpers.get_asset_tools()
report={}
def vec(v):return [float(v.x),float(v.y),float(v.z)]
def bounds(mesh):
 b=mesh.get_bounds();box=mesh.get_bounding_box()
 return {'min':vec(box.min),'max':vec(box.max),'origin':vec(b.origin),'extent':vec(b.box_extent),'radius':float(b.sphere_radius),'triangles':mesh.get_num_triangles(0)}
def matches(key,b):
 return all(math.isfinite(v) and abs(v-expected[key][edge][i])<.02 for edge in ('min','max') for i,v in enumerate(b[edge])) and math.isfinite(b['radius']) and b['radius']>.01
for key,part in models['parts'].items():
 path=receipt['meshes'][key]['mesh'];mesh=u.load_asset(path)
 if not mesh:raise RuntimeError('Missing '+path)
 before=bounds(mesh);before['fast_build']=u.ASH12AttachmentAssetTools.is_runtime_fast_build(mesh)
 materials={str(s.material_slot_name):s.material_interface for s in mesh.static_materials}
 src=ROOT/'Content'/Path(path.split('.')[0].removeprefix('/Game/')+'.uasset')
 if not (backup/src.name).exists():shutil.copy2(src,backup/src.name)
 # Reimport repopulates CachedMeshDescriptionBounds from real vertices, not
 # the invalid ExtendedBounds serialized by the earlier NullRHI rebuild.
 options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
 options.import_materials=False;options.import_textures=False;options.import_animations=False
 data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
 data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
 task=u.AssetImportTask();task.filename=part['file'];task.destination_path=path.rsplit('/',1)[0];task.destination_name=part['name']
 task.automated=True;task.replace_existing=True;task.save=False;task.options=options;A.import_asset_tasks([task])
 mesh=u.load_asset(path);slots=mesh.static_materials
 for i,s in enumerate(slots):s.material_interface=materials[str(s.material_slot_name)];slots[i]=s
 mesh.set_editor_property('static_materials',slots)
 # Old commandlet Interchange imports left this runtime-only flag serialized.
 # UE's fast-build branch does not initialize FStaticMeshRenderData::Bounds.
 u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
 settings=editor.get_lod_build_settings(mesh,0);settings.set_editor_property('recompute_normals',False)
 settings.set_editor_property('recompute_tangents',True);settings.set_editor_property('use_mikk_t_space',True)
 # A different tangent-buffer format forces both mesh and distance-field DDC
 # rebuilds. Recommitting identical imported LOD data keeps bGuidIsHash in 5.8
 # and therefore does not invalidate its corrupted cache entries.
 settings.set_editor_property('use_high_precision_tangent_basis',True)
 settings.set_editor_property('use_full_precision_u_vs',True)
 editor.set_lod_build_settings(mesh,0,settings)
 mesh.set_editor_property('positive_bounds_extension',u.Vector(0,0,0))
 mesh.set_editor_property('negative_bounds_extension',u.Vector(0,0,0))
 after=bounds(mesh);after['fast_build']=u.ASH12AttachmentAssetTools.is_runtime_fast_build(mesh)
 if not matches(key,after):raise RuntimeError('Rebuilt bounds disagree with FBX: '+key+' '+json.dumps(after))
 if not u.ASH12AttachmentAssetTools.finish_and_validate_build(mesh):raise RuntimeError('Invalid render or distance-field bounds: '+key)
 if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outer()],False):raise RuntimeError('Save failed '+key)
 report[key]={'before':before,'after':after,'matches_export':True,'path':path,'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials}}
 receipt['meshes'][key]['bounds']=after
 receipt['meshes'][key]['tangents']='High-precision tangent basis rebuilt from UV0 with MikkTSpace; preserve imported split normals'
 receipt['meshes'][key]['render_data']='Runtime fast-build disabled; full RHI rebuild with high-precision tangents/UVs bypasses corrupted render/DF DDC entries'
 (out/'repair.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print('ASH_MESH_BOUNDS_REPAIRED '+key+' '+json.dumps(after))
(O/'import.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('ASH_ALL_ATTACHMENT_BOUNDS_REPAIRED')
