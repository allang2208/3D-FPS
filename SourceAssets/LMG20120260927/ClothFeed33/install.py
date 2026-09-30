"""Save the optional cloth feed and ten reload assets without launching PIE."""
import unreal as u,json,gzip,hashlib,shutil,runpy
from pathlib import Path
O=Path(__file__).parent;PROJECT=O.parents[2];P='/Game/Weapons/LMG201/ClothFeed33';BODY='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;M=u.GeometryScript_Materials;Ed=u.GeometryScript_MeshEdits
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; no asset changes made')
props=json.loads((O/'props.json').read_text());motion=json.loads((O/'motion.json').read_text())
receipt=json.loads((O/'delivery.json').read_text()) if (O/'delivery.json').exists() else {'status':'installing','saved':{},'backups':{},'tested':False,'old_assets_deleted':False}
def record():(O/'delivery.json').write_text(json.dumps(receipt,indent=2))
def file(p):return PROJECT/'Content'/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(p):return hashlib.sha256(file(p).read_bytes()).hexdigest()
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
def backup(p):
 if p in receipt['backups']:return
 dest=P+'/Previous/'+p.rsplit('/',1)[1]+'_PreCloth33';old=E.duplicate_asset(p,dest)
 if not old:raise RuntimeError('Cannot preserve '+p)
 save(old);target=O/'Before'/file(p).relative_to(PROJECT/'Content');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file(p),target)
 receipt['backups'][p]={'asset':old.get_path_name(),'bytes':str(target),'sha256':sha(p)};record()
def dynamic(a):
 dm,out=G.copy_mesh_from_skeletal_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if out!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+a.get_path_name())
 return dm
def copy_to(dm,a,slots):
 opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
 _,out=G.copy_mesh_to_skeletal_mesh(dm,a,opts,u.GeometryScriptMeshWriteLOD())
 if out!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write '+a.get_path_name())
 a.set_editor_property('materials',slots)
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if BODY in dirty or any(s['destination'] in dirty for s in motion['clips'].values()):raise RuntimeError('Target has unsaved changes; preserve editor state')
current=u.load_asset(BODY)
if BODY not in receipt['saved']:
 if 'Surface32' not in str(E.get_metadata_tag(current,'201Revision')):raise RuntimeError('Complete Surface32 before merging cloth props')
 backup(BODY)
 dest=P+'/Parts/SK_LMG201_Cloth33_Props';part=u.load_asset(dest)
 if not part:
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
  opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=current.skeleton
  si=opt.skeletal_mesh_import_data;si.set_editor_property('update_skeleton_reference_pose',False);si.set_editor_property('use_t0_as_ref_pose',False);si.set_editor_property('preserve_smoothing_groups',True);si.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;si.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
  task=u.AssetImportTask();task.filename=props['fbx'];task.destination_path=P+'/Parts';task.destination_name='SK_LMG201_Cloth33_Props';task.factory=u.FbxFactory();task.options=opt;task.automated=True;task.replace_existing=False;task.save=False
  flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
  try:A.import_asset_tasks([task])
  finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
  part=u.load_asset(dest)
  if not part or not task.imported_object_paths:raise RuntimeError('Cloth prop import failed')
 mats=json.loads((O.parent/'Install30/materials.json').read_text())['materials'];rolepaths={'Cloth':mats['Cloth'],'Belt':mats['Surface'],'Interior':mats['Interior']}
 ps=[s.copy() for s in part.materials]
 for s in ps:s.material_interface=u.load_asset(rolepaths[props['roles'][str(s.material_slot_name)]])
 part.set_editor_property('materials',ps);save(part)
 native,added=dynamic(current),dynamic(part);slots=[s.copy() for s in current.materials];offset=len(slots);slots.extend(ps)
 B.copy_bones_from_mesh(added,native,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=True))
 for i in range(len(ps)-1,-1,-1):M.remap_material_i_ds(added,i,i+offset)
 Ed.append_mesh(native,added,u.Transform(),True)
 candidate=u.load_asset(P+'/SK_LMG201_Cloth33_Installed') or E.duplicate_asset(BODY,P+'/SK_LMG201_Cloth33_Installed')
 if not candidate:raise RuntimeError('Cannot create cloth candidate')
 copy_to(native,candidate,slots);save(candidate)
 full=O/'Exports/SK_LMG201_Cloth33_Installed.fbx';ex=u.AssetExportTask();ex.object=candidate;ex.filename=str(full);ex.automated=True;ex.prompt=False;ex.replace_identical=True;ex.options=u.FbxExportOption();ex.options.level_of_detail=False;ex.options.export_morph_targets=False;ex.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
 if not u.Exporter.run_asset_export_task(ex):raise RuntimeError('Full assembly source export failed')
 copy_to(native,current,slots);current.get_editor_property('asset_import_data').scripted_add_filename(str(full),0,'Surface32 + optional ClothFeed33')
 E.set_metadata_tag(current,'201Revision','Surface32 + ClothFeed33: original smoothed body; optional woven pouch and segmented belt; native V7 arms unchanged')
 E.set_metadata_tag(current,'201ClothFeedSource',str(O/'LMG201_Cloth33_Editable.blend'));save(current)
 receipt['saved'][BODY]={'asset':current.get_path_name(),'sha256':sha(BODY),'candidate':candidate.get_path_name(),'source_fbx':str(full),'pouch_material':mats['Cloth']};record();print('CLOTH33_BODY_SAVED',flush=True)

for key,spec in motion['clips'].items():
 path=spec['destination']
 if path in receipt['saved']:continue
 clip=u.load_asset(path)
 if not clip:clip=E.duplicate_asset(spec['source'],path)
 if not clip:raise RuntimeError('Cannot create '+path)
 with gzip.open(spec['keys'],'rt',encoding='utf8') as f:tracks=json.load(f)
 c=clip.get_editor_property('controller');c.open_bracket('201 cloth feed: complete native PKM FK adaptation',False)
 try:
  c.remove_all_bone_tracks(False);c.set_frame_rate(u.FrameRate(numerator=spec['fps'],denominator=1),False);c.set_number_of_frames(u.FrameNumber(value=spec['frames']-1),False)
  for n,rows in tracks.items():
   if not c.add_bone_curve(n,False):raise RuntimeError('Cannot create track '+n)
   if not c.set_bone_track_keys(n,[u.Vector(*v[:3]) for v in rows],[u.Quat(*v[3:7]) for v in rows],[u.Vector(*v[7:10]) for v in rows],False):raise RuntimeError('Cannot write '+n)
 finally:c.close_bracket(False)
 clip.set_preview_skeletal_mesh(current)
 E.set_metadata_tag(clip,'201ReloadRevision','ClothFeed33: source-video phases, complete PKM FK, mirrored working arm, contact fit, grip-family return')
 E.set_metadata_tag(clip,'NativeAnimationDonor',motion['donor']);E.set_metadata_tag(clip,'NativeAnimationDonorSHA256',motion['donor_sha256']);E.set_metadata_tag(clip,'201AuthoringSource',spec['keys'])
 u.AKMAnimationAuditLibrary.finish_animation_compression(clip);save(clip)
 receipt['saved'][path]={'sha256':sha(path),'keys':spec['frames'],'seconds':spec['seconds'],'family':key,'source':spec['keys']};record();print('CLOTH33_ANIMATION_SAVED',key,flush=True)

icon=json.loads((O/'icon.json').read_text());iconpath='/Game/ColdSteelData/AttachmentIcons20260913/'+icon['key']
if iconpath not in receipt['saved']:
 dst=PROJECT/'Content/ColdSteelData/AttachmentIcons20260913'/(icon['key']+'.png');shutil.copy2(icon['file'],dst)
 task=u.AssetImportTask();task.filename=str(dst);task.destination_path=iconpath.rsplit('/',1)[0];task.destination_name=icon['key'];task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);tex=u.load_asset(iconpath)
 if not tex:raise RuntimeError('Cannot import cloth icon')
 tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON);tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);save(tex)
 receipt['saved'][iconpath]={'sha256':sha(iconpath)};record()
bindings=O.parent/'Material21/bindings.json';bd=json.loads(bindings.read_text());bd['meshes'][current.get_path_name()]={str(s.material_slot_name):s.material_interface.get_path_name() for s in current.materials};bindings.write_text(json.dumps(bd,indent=2))
runpy.run_path(str(O/'catalog.py'),run_name='__main__')
receipt.update(status='assets_and_catalog_saved',phases=motion['phases'],reference_video=motion['reference_video'],donor=motion['donor'],donor_sha256=motion['donor_sha256'],original_magazine_retained=True,retired_metal_box_restored=False,runtime_tested=False);record()
print('CLOTH33_ASSETS_COMPLETE',flush=True)
