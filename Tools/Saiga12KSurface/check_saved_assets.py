"""Independent saved-package readback for the user's requested overall review."""
import unreal as u,json,sys,math
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KSurface20261018';D='/Game/Weapons/Saiga12K/SurfaceRebuild20261018'
sys.path.insert(0,str(P/'Tools/Saiga12KSurface'));from mesh_contract import arm_contract
C=json.loads((O/'Reports/baseline.json').read_text());receipt=json.loads((O/'Receipts/assets.json').read_text());R={'checks_requested_by_user':True,'assets':{},'issues':[],'engine_play_tested':False}
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;LS=u.GeometryScript_List;BW=u.GeometryScript_BoneWeights;ML=u.MathLibrary;L=u.MaterialEditingLibrary
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
mesh=u.load_asset(D+'/SK_Saiga12K_Manny');arms=arm_contract(mesh);R['arm_contract_unchanged']=arms==C['arms'];R['arm_triangles']=arms['triangle_count'];R['correctives']=len(arms['morphs'])
if not R['arm_contract_unchanged']:R['issues'].append('Native arm/bone/morph/UV contract differs')
for key,bindings in receipt['bindings'].items():
 path=receipt['mesh'] if key=='native' else receipt['ext12'] if key=='ext12' else D+'/Attachments/SM_Saiga12K_'+key;a=u.load_asset(path)
 if not a:R['issues'].append('Missing '+path);continue
 slots=a.materials if key=='native' else a.static_materials;row={'path':a.get_path_name(),'slots':{},'bounds_radius':a.get_bounds().sphere_radius if key!='native' else None};R['assets'][key]=row
 row['lod_count']=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(a) if key=='native' else SM.get_lod_count(a)
 for s in slots:
  name=str(s.material_slot_name);m=s.material_interface
  if not m:R['issues'].append(key+': null material '+name);continue
  if key=='native' and not name.startswith('Saiga12K_'):continue
  value={'material':m.get_path_name(),'base':m.get_base_material().get_path_name(),'scalars':{},'textures':{}};row['slots'][name]=value
  if bindings.get(name)!=m.get_path_name():R['issues'].append(key+': binding changed '+name)
  if 'WorldGridMaterial' in m.get_path_name() or 'DefaultMaterial' in m.get_path_name():R['issues'].append(key+': fallback material '+name)
  if isinstance(m,u.MaterialInstanceConstant):
   scalars={str(n) for n in L.get_scalar_parameter_names(m)}
   for n in ('GrainRoughness','MottleRoughness','MottleColor','Stipple','R01_GrainRoughness','R01_MottleRoughness','Metallic','Roughness','MaskUVChannel'):
    if n in scalars:value['scalars'][n]=L.get_material_instance_scalar_parameter_value(m,n)
   for n,v in value['scalars'].items():
    if n in ('GrainRoughness','MottleRoughness','MottleColor','Stipple','R01_GrainRoughness','R01_MottleRoughness') and abs(v)>1e-7:R['issues'].append(key+': residual grain '+name+'/'+n)
   for n in ('SurfaceNormal','SurfaceMask'):
    if n not in {str(x) for x in L.get_texture_parameter_names(m)}:continue
    t=L.get_material_instance_texture_parameter_value(m,n)
    if t:value['textures'][n]={'path':t.get_path_name(),'srgb':t.srgb,'compression':str(t.compression_settings),'never_stream':t.never_stream,'flip_green':t.flip_green_channel if n=='SurfaceNormal' else None}
    if key in ('native','ext12'):
     if not t or '/SurfaceRebuild20261018/Textures/' not in t.get_path_name():R['issues'].append(key+': wrong rebuilt texture '+name+'/'+n)
     elif t.srgb:R['issues'].append(key+': data texture uses sRGB '+name+'/'+n)
     elif n=='SurfaceNormal' and (not t.flip_green_channel or t.compression_settings!=u.TextureCompressionSettings.TC_NORMALMAP):R['issues'].append(key+': normal convention/compression '+name)
 if key not in ('native','ext12'):
  old=u.load_asset(C['assets'][key]['path'])
  def bounds_values(asset):
   b=asset.get_bounds();return [b.origin.x,b.origin.y,b.origin.z,b.box_extent.x,b.box_extent.y,b.box_extent.z,b.sphere_radius]
  row['geometry_bounds_unchanged']=bounds_values(a)==bounds_values(old);row['lod_count_unchanged']=row['lod_count']==SM.get_lod_count(old)
  if not row['geometry_bounds_unchanged'] or not row['lod_count_unchanged']:R['issues'].append(key+': accessory geometry/LOD changed')
# Export the actual saved gun in its seated pose for offline appearance inspection.
dm,st=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD());_,bones=BW.get_all_bones_info(dm);names=[str(b.name) for b in bones];byname={str(b.name):b for b in bones}
local=u.AnimationLibrary.get_bone_poses_for_frame(u.load_asset('/Game/Weapons/AKMIntegration/SourceMatched/A_AKM_idle'),names,0,False,mesh);pose={}
for b,t in zip(bones,local):pose[str(b.name)]=t if b.parent_index<0 else t.multiply(pose[names[b.parent_index]])
root=pose['WPN_root'];_,vp,_=Q.get_all_vertex_positions(dm,False);vp=list(LS.convert_vector_list_to_array(vp));_,tp,_=Q.get_all_triangle_indices(dm,False);tp=list(LS.convert_triangle_list_to_array(tp));mats=list(mesh.materials)
def root_position(v,b):
 p=ML.inverse_transform_location(root,ML.transform_location(pose[b],ML.inverse_transform_location(byname[b].world_transform,v)));return [p.x*100,p.y*100,p.z*100]
def root_normal(v,b):
 p=ML.inverse_transform_direction(root,ML.transform_direction(pose[b],ML.inverse_transform_direction(byname[b].world_transform,v)));return [p.x,p.y,p.z]
out={'positions':[],'triangles':[],'parts':[],'normals':[],'uv':[]};mapping={};counts={};weights={};wrongbones=[]
for ti,t in enumerate(tp):
 mid,ok=u.GeometryScript_Materials.get_triangle_material_id(dm,ti);name=str(mats[mid].material_slot_name)
 if not name.startswith('Saiga12K_'):continue
 part=name.removeprefix('Saiga12K_');bone='WPN_SOCKET_Magazine' if part in ('Magazine','ShellBrass','ShellPlastic') else 'WPN_bolt' if part=='Bolt' else 'WPN_Trigger' if part=='Trigger' else 'WPN_root';ids=[]
 for vi in (t.x,t.y,t.z):
  if vi not in mapping:
   mapping[vi]=len(out['positions']);out['positions'].append(root_position(vp[vi],bone));_,ws,_=BW.get_vertex_bone_weights(dm,vi);ws=[w for w in ws if w.weight>0.]
   if len(ws)!=1 or names[ws[0].bone_index]!=bone or abs(ws[0].weight-1.)>1e-6:wrongbones.append(vi)
  ids.append(mapping[vi])
 out['triangles'].append(ids);out['parts'].append(part);out['normals'].append([root_normal(n,bone) for n in Q.get_triangle_normals(dm,ti) if isinstance(n,u.Vector)][:3]);out['uv'].append([[v.x,v.y] for v in Q.get_triangle_u_vs(dm,0,ti)[:3]]);counts[part]=counts.get(part,0)+1
R['saved_gun_triangles']=len(out['triangles']);R['mechanical_bone_mismatches']=len(wrongbones);R['gun_part_triangles']=counts
if wrongbones:R['issues'].append('Mechanical bone assignment differs')
(O/'Authoring/saved_ue_gun.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8');R['complete']=True;R['passed']=not R['issues'];(O/'Reports/saved-assets-check.json').write_text(json.dumps(R,indent=2),encoding='utf-8');print('SAIGA_SAVED_ASSET_CHECK',R['passed'],len(R['assets']),R['issues'])
