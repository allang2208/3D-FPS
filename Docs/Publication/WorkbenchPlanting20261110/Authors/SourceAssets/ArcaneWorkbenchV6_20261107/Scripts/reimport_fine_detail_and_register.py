import unreal as u, json
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ArcaneWorkbenchV6_20261107')
assert Path(u.Paths.project_dir()).resolve()==R.parents[1].resolve()
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ed.get_game_world() is not None: raise RuntimeError('PIE still running; no import performed')
if ed.get_editor_world() is None and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower(): raise RuntimeError('No editor world or commandlet; no import performed')
P='/Game/Building/ArcaneWorkbenchV6_20261107/Meshes'
N='SM_ArcaneWorkbench_V6'
E=u.EditorAssetLibrary
import shutil,datetime,re
old=u.load_asset(P+'/'+N)
if old is None:raise RuntimeError('Expected previous imported mesh')
if old.get_outermost() in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('Mesh contains unsaved edits')
(R/'Before').mkdir(exist_ok=True)
shutil.copy2(R.parents[1]/'Content/Building/ArcaneWorkbenchV6_20261107/Meshes/SM_ArcaneWorkbench_V6.uasset',R/'Before/SM_ArcaneWorkbench_before_fine_detail_fix.uasset')
opts=u.FbxImportUI()
opts.set_editor_property('import_mesh',True)
opts.set_editor_property('import_as_skeletal',False)
opts.set_editor_property('mesh_type_to_import',u.FBXImportType.FBXIT_STATIC_MESH)
opts.set_editor_property('automated_import_should_detect_type',False)
opts.set_editor_property('import_materials',False)
opts.set_editor_property('import_textures',False)
d=opts.static_mesh_import_data
settings={'combine_meshes':True,'auto_generate_collision':False,'one_convex_hull_per_ucx':True,'convert_scene':True,'force_front_x_axis':False,'convert_scene_unit':True,'transform_vertex_to_absolute':True,'bake_pivot_in_vertex':False,'import_uniform_scale':1.0,'reorder_material_to_fbx_order':True,'generate_lightmap_u_vs':False,'build_nanite':False,'remove_degenerates':False}
for k,v in settings.items(): d.set_editor_property(k,v)
d.set_editor_property('import_rotation',u.Rotator(0,0,0))
d.set_editor_property('import_translation',u.Vector(0,0,0))
d.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)
t=u.AssetImportTask()
t.set_editor_property('filename',str(R/'Authored/Enchantment_Workbench_V6_TangentFix.fbx'))
t.set_editor_property('destination_path',P)
t.set_editor_property('destination_name',N)
t.set_editor_property('automated',True)
t.set_editor_property('replace_existing',True)
t.set_editor_property('replace_existing_settings',True)
t.set_editor_property('save',False)
t.set_editor_property('options',opts)
t.set_editor_property('factory',u.FbxFactory())
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
m=u.load_asset(P+'/'+N)
if m is None: raise RuntimeError('Mesh import failed: '+str(t.imported_object_paths))
b=m.get_bounds(); agg=m.get_editor_property('body_setup').get_editor_property('agg_geom')
receipt={'stage':'mesh_imported','paths':list(t.imported_object_paths),'settings':settings,'import_rotation':[0,0,0],'import_translation':[0,0,0],'coordinate_policy':str(d.get_editor_property('coordinate_system_policy')),'bounds_origin':[b.origin.x,b.origin.y,b.origin.z],'bounds_extent':[b.box_extent.x,b.box_extent.y,b.box_extent.z],'material_slots': [{'slot':i,'name':str(s.material_slot_name),'imported':str(s.get_editor_property('imported_material_slot_name'))} for i,s in enumerate(m.static_materials)],'simple_collisions':sum(len(agg.get_editor_property(k)) for k in ['sphere_elems','box_elems','sphyl_elems']),'convex_collisions':len(agg.get_editor_property('convex_elems')),'tests_run':False}
if len(m.static_materials)!=28: raise RuntimeError('Wrong material slot count')
if receipt['convex_collisions']!=2: raise RuntimeError('Did not retain 2 authored UCX hulls')
desc=m.get_static_mesh_description(0)
if desc.get_triangle_count()!=143134:raise RuntimeError('Fine-detail triangles still lost: '+str(desc.get_triangle_count()))
recipe=json.loads((R/'Input/UE_Material_Recipe.json').read_text(encoding='utf-8'))
def canon(v):return re.sub('[^a-z0-9]','',str(v).lower())
bindings={canon(x['material_name']):u.load_asset('/Game/Building/ArcaneWorkbenchV6_20261107/Materials/'+x['ue_safe_name']) for x in recipe['materials']}
for i,slot in enumerate(m.static_materials):
 mat=bindings[canon(slot.get_editor_property('imported_material_slot_name'))]
 if mat is None:raise RuntimeError('Material missing')
 m.set_material(i,mat)
m.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
receipt.update({'source_fbx':str(R/'Authored/Enchantment_Workbench_V6_TangentFix.fbx'),'source_triangles':desc.get_triangle_count(),'source_vertices':desc.get_vertex_count(),'all_materials_bound':all(m.get_material(i) for i in range(28))})
if not E.save_loaded_asset(m,False): raise RuntimeError('Mesh save failed')
(R/'Receipts/mesh-import-final.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt))

points=[]
for i in range(8):
 v=desc.get_vertex_position(u.VertexID(i));points.append([v.x,v.y,v.z])
(R/'Receipts/imported-geometry.json').write_text(json.dumps({'first_vertices':points,'vertices':desc.get_vertex_count(),'triangles':desc.get_triangle_count()},indent=2),encoding='utf-8')
finish=R/'Scripts/finish_integration_v6.py'
exec(compile(finish.read_text(encoding='utf-8'),str(finish),'exec'),{'__name__':'__main__'})