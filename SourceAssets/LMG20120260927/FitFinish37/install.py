"""Install authored body parts and finishes while keeping native rig/action assets."""
import unreal as u
import json, hashlib, shutil
from pathlib import Path

O=Path(__file__).parent;S=O.parent;PROJECT=O.parents[2];P='/Game/Weapons/LMG201/FitFinish37'
BODY='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'
WET='/Game/Weapons/LMG201/Accessories22/DA_LMG201_AttachmentWetMaterials'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils
B=u.GeometryScript_BoneWeights;M=u.GeometryScript_Materials;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;Ed=u.GeometryScript_MeshEdits
model=json.loads((O/'model.json').read_text());md=json.loads((O/'materials.json').read_text())
if md['status']!='compiled_and_saved':raise RuntimeError('Finish production incomplete')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; save deferred')
recipe=md['materials'];adapted={k:v['material'] for k,v in md['adapted'].items()}
baseline=json.loads((O/'baseline.json').read_text())
receipt={'status':'installing','backups':{},'saved':{},'animations_changed':False,'skeleton_replaced':False,'game_tested':False,'acceptance_rendered':False}
if (O/'delivery.json').exists():receipt=json.loads((O/'delivery.json').read_text())
def record():(O/'delivery.json').write_text(json.dumps(receipt,indent=2))
def file(path):return PROJECT/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(path):return hashlib.sha256(file(path).read_bytes()).hexdigest()
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing '+path)
 return a

manifest=S/'Material21/bindings.json';data=json.loads(manifest.read_text())
targets={p.split('.')[0] for p in data['meshes']}
targets.update(v['asset'].split('.')[0] for v in json.loads((S/'Accessories22/install_receipt.json').read_text())['meshes'].values())
targets.add(BODY)
# This comparison protects the concurrent asset owner, rather than judging the
# produced model. Extra static targets are captured immediately before writing.
for path in sorted(targets|{WET}):
 actual=sha(path);expected=receipt['saved'].get(path,{}).get('sha256',baseline.get(path))
 if expected and actual!=expected:raise RuntimeError('Concurrent asset change retained: '+path)
 if path not in baseline:baseline[path]=actual
(O/'baseline.json').write_text(json.dumps(baseline,indent=2))
for path in sorted(targets|{WET}):
 if path in receipt['backups']:continue
 dest=P+'/Previous/'+path.rsplit('/',1)[1]+'_PreF37'
 if E.does_asset_exist(dest):raise RuntimeError('Backup path already owned: '+dest)
 old=E.duplicate_asset(path,dest)
 if not old:raise RuntimeError('Backup failed '+path)
 save(old);dst=O/'Before'/file(path).relative_to(PROJECT/'Content');dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file(path),dst)
 receipt['backups'][path]={'asset':old.get_path_name(),'bytes':str(dst),'sha256':sha(path)};record()

def role_for(slot):
 if slot in model['material_roles']:return model['material_roles'][slot]
 if '_R30_' in slot:return 'Interior' if slot.endswith('_Interior') else 'Coat' if slot.endswith('_Steel') else 'Surface'
 if slot.startswith('M_LMG201_D35_'):
  key=slot.removeprefix('M_LMG201_D35_').removeprefix('Control')
  if key in recipe:return key
 return None
def assign(a):
 prop='materials' if isinstance(a,u.SkeletalMesh) else 'static_materials';slots=[s.copy() for s in a.get_editor_property(prop)]
 for i,s in enumerate(slots):
  name=str(s.material_slot_name);role=role_for(name);old=s.material_interface.get_path_name() if s.material_interface else None
  if role:s.material_interface=load(recipe[role])
  elif old in adapted:s.material_interface=load(adapted[old])
  slots[i]=s
 a.set_editor_property(prop,slots);return slots
def dynamic(a):
 dm,res=G.copy_mesh_from_skeletal_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if res!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read mesh '+a.get_path_name())
 return dm
def copy_to(dm,a,slots):
 opt=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
 _,res=G.copy_mesh_to_skeletal_mesh(dm,a,opt,u.GeometryScriptMeshWriteLOD())
 if res!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write mesh '+a.get_path_name())
 a.set_editor_property('materials',slots)

current=load(BODY)
if BODY not in receipt['saved']:
 path=P+'/Parts/SK_LMG201_F37_BodyParts';part_asset=u.load_asset(path)
 if not part_asset:
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=current.skeleton
  d=opt.skeletal_mesh_import_data;d.set_editor_property('update_skeleton_reference_pose',False);d.set_editor_property('use_t0_as_ref_pose',False);d.set_editor_property('preserve_smoothing_groups',True);d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
  t=u.AssetImportTask();t.filename=model['weapon_fbx'];t.destination_path=P+'/Parts';t.destination_name='SK_LMG201_F37_BodyParts';t.factory=u.FbxFactory();t.options=opt;t.automated=True;t.save=False
  flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
  try:A.import_asset_tasks([t])
  finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
  part_asset=load(path)
  if not t.imported_object_paths:raise RuntimeError('FBX import failed')
 assign(part_asset);save(part_asset);native=dynamic(current);part=dynamic(part_asset);slots=assign(current)
 replaced={i for i,s in enumerate(slots) if '_R30_' in str(s.material_slot_name) or str(s.material_slot_name) in ['M_LMG201_D35_Coat','M_LMG201_D35_Interior','M_LMG201_D35_Satin','M_LMG201_D35_Receiver']}
 _,tl,_=Q.get_all_triangle_indices(native,False);triangles=L.convert_triangle_list_to_array(tl);delete=[]
 for ti,_ in enumerate(triangles):
  mid,valid=M.get_triangle_material_id(native,ti)
  if valid and mid in replaced:delete.append(ti)
 if not delete:raise RuntimeError('No old body parts selected')
 Ed.delete_triangles_from_mesh(native,L.convert_array_to_index_list(delete,u.GeometryScriptIndexType.TRIANGLE),True)
 B.copy_bones_from_mesh(native,part,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=True))
 names={str(s.material_slot_name):i for i,s in enumerate(slots)}
 for s in part_asset.materials:
  key=str(s.material_slot_name)
  if key not in names:names[key]=len(slots);slots.append(s.copy())
 for i,s in enumerate(part_asset.materials):M.remap_material_i_ds(part,i,1000+i)
 for i,s in enumerate(part_asset.materials):M.remap_material_i_ds(part,1000+i,names[str(s.material_slot_name)])
 Ed.append_mesh(native,part,u.Transform(),True)
 candidate=u.load_asset(P+'/SK_LMG201_F37_Installed') or E.duplicate_asset(BODY,P+'/SK_LMG201_F37_Installed')
 copy_to(native,candidate,slots);save(candidate);copy_to(native,current,slots)
 full=O/'Exports/SK_LMG201_F37_Installed.fbx';current.get_editor_property('asset_import_data').scripted_add_filename(str(full),0,'FitFinish37 full installed assembly')
 E.set_metadata_tag(current,'201Revision','FitFinish37: paired receiver/cover opening, private unified coat, front interface transition; authored and saved, not runtime accepted')
 E.set_metadata_tag(current,'201DetailSource',str(O/'LMG201_FitFinish37_Editable.blend'));E.set_metadata_tag(current,'201PreviousAsset',receipt['backups'][BODY]['asset']);save(current)
 receipt['saved'][BODY]={'sha256':sha(BODY),'removed_body_triangles':len(delete),'source_fbx':str(full)};record();print('F37_BODY_SAVED',flush=True)

for path in sorted(targets-{BODY}):
 a=load(path);assign(a);save(a);receipt['saved'][path]={'sha256':sha(path)};record()
table=load(WET);wet=dict(table.get_editor_property('wet_materials'))
for old,new in adapted.items():wet[old]=load(new);wet[new]=load(new)
for new in recipe.values():wet[new]=load(new)
table.set_editor_property('wet_materials',wet);save(table);receipt['saved'][WET]={'sha256':sha(WET)};record()

bindings={}
for path in sorted(targets):
 a=load(path);slots=a.materials if isinstance(a,u.SkeletalMesh) else a.static_materials
 bindings[a.get_path_name()]={str(s.material_slot_name):s.material_interface.get_path_name() if s.material_interface else None for s in slots}
data['meshes'].update(bindings);data['current_finish_revision']='FitFinish37';manifest.write_text(json.dumps(data,indent=2));(O/'bindings.json').write_text(json.dumps(bindings,indent=2))
ex=u.AssetExportTask();ex.object=current;ex.filename=str(O/'Exports/SK_LMG201_F37_Installed.fbx');ex.automated=True;ex.prompt=False;ex.replace_identical=True;ex.options=u.FbxExportOption();ex.options.level_of_detail=False;ex.options.export_morph_targets=False;ex.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
if not u.Exporter.run_asset_export_task(ex):raise RuntimeError('Full assembly export failed')
receipt.update(status='current_201_fitfinish37_saved',finish_recipe=md['recipe'],adapted_materials=len(adapted),body_material_family=recipe,source_model=model['weapon_fbx']);record();print('F37_INSTALL_SAVED',len(receipt['saved']),flush=True)
