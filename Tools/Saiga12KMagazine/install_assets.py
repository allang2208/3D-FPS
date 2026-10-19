"""Save the new magazine, its own UV1 mask, and inherited Saiga WS1.1 finish."""
import unreal as u,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KMagazine20261017');D='/Game/Weapons/Saiga12K/ExtendedMagazine20261017'
F=json.loads((O/'Authoring/magazine.json').read_text());E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
ED=u.GeometryScript_MeshEdits;LS=u.GeometryScript_List;R={'saved':[],'runtime_tested':False}
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
 R['saved'].append(a.get_path_name());(O/'Receipts/assets.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
 return a
task=u.AssetImportTask();task.filename=str(O/'Textures/T_Saiga12K_Ext12_Mask.png');task.destination_path=D+'/Textures';task.destination_name='T_Saiga12K_Ext12_Mask';task.automated=True;task.replace_existing=True;task.save=False;AT.import_asset_tasks([task])
mask=u.load_asset(D+'/Textures/T_Saiga12K_Ext12_Mask');mask.srgb=False;mask.compression_settings=u.TextureCompressionSettings.TC_MASKS;mask.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON;save(mask)
mi=u.load_asset(D+'/Materials/MI_Saiga12K_Ext12') if E.does_asset_exist(D+'/Materials/MI_Saiga12K_Ext12') else AT.create_asset('MI_Saiga12K_Ext12',D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
L.set_material_instance_parent(mi,u.load_asset('/Game/Weapons/Saiga12K/Refined20261017/Materials/MI_Saiga12K_Magazine'))
L.set_material_instance_texture_parameter_value(mi,'SurfaceMask',mask);L.set_material_instance_scalar_parameter_value(mi,'MaskUVChannel',1.)
L.set_material_instance_scalar_parameter_value(mi,'BeadScale',2.42/max(F['uv_per_cm']['uv0'],.0001));L.update_material_instance(mi);save(mi)
dm=u.DynamicMesh();u.GeometryScript_UVs.set_num_uv_sets(dm,2)
# Split render corners preserve factory hard edges and the exact source normals.
vertices=[u.Vector(*F['positions'][v]) for tri in F['triangles'] for v in tri]
_,ids=ED.add_vertices_to_mesh(dm,LS.convert_array_to_vector_list(vertices),True);ids=list(LS.convert_index_list_to_array(ids))
_,tids=ED.add_triangles_to_mesh(dm,LS.convert_array_to_triangle_list([u.IntVector(*ids[i:i+3]) for i in range(0,len(ids),3)]),0,True)
for fi,tid in enumerate(LS.convert_index_list_to_array(tids)):
 if tid<0:raise RuntimeError('Cannot write magazine triangle '+str(fi))
 n=[u.Vector(*v) for v in F['normals'][fi]];u.GeometryScript_Normals.set_mesh_triangle_normals(dm,tid,u.GeometryScriptTriangle(vector0=n[0],vector1=n[1],vector2=n[2]),True)
 for ch in (0,1):
  uv=[u.Vector2D(*v) for v in F['uv'+str(ch)][fi]];u.GeometryScript_UVs.set_mesh_triangle_u_vs(dm,ch,tid,u.GeometryScriptUVTriangle(uv0=uv[0],uv1=uv[1],uv2=uv[2]),True)
path=D+'/SM_Saiga12K_Ext12'
if E.does_asset_exist(path):
 mesh=u.load_asset(path);_,status=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,mesh,u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True),u.GeometryScriptMeshWriteLOD())
else:mesh,status=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,path,u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,enable_collision=False))
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot save magazine geometry')
mesh.set_editor_property('static_materials',[u.StaticMaterial(material_interface=mi,material_slot_name='Saiga12K_Magazine')])
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);options=u.StaticMeshReductionOptions();options.auto_compute_lod_screen_size=False
options.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=p,screen_size=s) for p,s in [(1.,1.),(.5,.18),(.25,.075)]];sub.set_lods(mesh,options)
E.set_metadata_tag(mesh,'MagazineAuthoring','Saiga 12K native factory upper retained; +7 cm measured arc; 12 rounds; WPN_SOCKET_Magazine cm at scale .01')
E.set_metadata_tag(mi,'WeaponSurfaceVersion','WS1.1 inherited Saiga polymer; own UV1 mask')
save(mi)
save(mesh);R.update(complete=True,mesh=mesh.get_path_name(),material=mi.get_path_name(),capacity=12,bone='WPN_SOCKET_Magazine',scale=.01)
(O/'Receipts/assets.json').write_text(json.dumps(R,indent=2),encoding='utf-8');print('SAIGA_EXT12_ASSETS_SAVED')
