"""Save a private 201 feed rig and current native arms; never edit shared rest."""
import unreal as u,json,re
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/LMG20120260927/BeltFeed08');P='/Game/Weapons/LMG201/BeltFeed08';R='/Game/Weapons/LMG201/Production20260927'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils;M=u.GeometryScript_Materials;B=u.GeometryScript_BoneWeights
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; 201 belt-feed assets not changed')
receipt={'status':'importing','animations':{},'materials':{},'runtime_tested':False,'visual_tested':False,'private_skeleton':True}
if (O/'import_receipt.json').exists():receipt=json.loads((O/'import_receipt.json').read_text())
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
def save(a):
 if not a or not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+str(a))
def dynamic(a):
 dm,result=G.copy_mesh_from_skeletal_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Surface copy failed '+a.get_path_name())
 return dm
base=u.load_asset(R+'/SK_LMG201_Manny');slots=[s.copy() for s in base.materials];slotids={str(s.material_slot_name):i for i,s in enumerate(slots)}
private=u.load_asset(P+'/SK_LMG201_FeedSkeleton') or E.duplicate_asset(base.skeleton.get_path_name(),P+'/SK_LMG201_FeedSkeleton')
private.add_compatible_skeleton(base.skeleton);save(private)
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 if not receipt.get('mesh'):
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=private
  data=opt.skeletal_mesh_import_data
  for key,value in {'update_skeleton_reference_pose':False,'use_t0_as_ref_pose':False,'preserve_smoothing_groups':True,'normal_import_method':u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,'normal_generation_method':u.FBXNormalGenerationMethod.MIKK_T_SPACE}.items():data.set_editor_property(key,value)
  task=u.AssetImportTask();task.filename=str(O/'Exports/SK_LMG201_BeltFeed.fbx');task.destination_path=P;task.destination_name='SK_LMG201_BeltFeed';task.options=opt;task.factory=u.FbxFactory();task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;A.import_asset_tasks([task])
  mesh=u.load_asset(P+'/SK_LMG201_BeltFeed')
  if not mesh or not task.imported_object_paths:raise RuntimeError('201 feed surface import failed')
  mapping={};newslots=mesh.materials
  for i,s in enumerate(newslots):
   key=str(s.material_slot_name)
   # Blender's appended donor can suffix identical existing material datablocks.
   original=re.sub(r'_[0-9]{3}$','',key)
   if original in slotids:key=original
   if key not in slotids:
    mat=None
    if key=='M_LMG201_MagazineInside':mat=slots[slotids['M_LMG201_Inside']].material_interface
    elif key.startswith('M_LMG201_Feed__'):
     parent=slots[slotids['M_LMG201_ReceiverReferenceCover' if key.endswith('Paint') else 'M_LMG201_ReceiverReferenceHardware']].material_interface
     mat=u.load_asset(P+'/Materials/'+key) or A.create_asset(key,P+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
     u.MaterialEditingLibrary.set_material_instance_parent(mat,parent)
     if key.endswith('Copper'):color=(.31,.13,.038)
     elif key.endswith('Case'):color=(.19,.16,.085)
     else:color=(.017,.021,.026) if key.endswith('Paint') else (.022,.026,.031)
     u.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mat,'FinishColor',u.LinearColor(*color,1));save(mat);receipt['materials'][key]=mat.get_path_name()
    if not mat:raise RuntimeError('Missing 201 material '+key)
    s.material_interface=mat;slotids[key]=len(slots);slots.append(s.copy())
   mapping[i]=slotids[key];s.material_interface=slots[slotids[key]].material_interface;newslots[i]=s
  mesh.materials=newslots
  weapon=dynamic(mesh);arms=dynamic(base)
  armids={i for i,s in enumerate(base.materials) if str(s.material_slot_name).startswith('M_LMG201_MannySkin_')}
  for i in range(len(base.materials)):
   if i not in armids:M.delete_triangles_by_material_id(arms,i,True)
  # Re-index the retained exact native weights against the private extended rig.
  B.copy_bones_from_mesh(weapon,arms,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=True))
  for i in mapping:M.remap_material_i_ds(weapon,i,1000+i)
  for i,target in mapping.items():M.remap_material_i_ds(weapon,1000+i,target)
  u.GeometryScript_MeshEdits.append_mesh(weapon,arms,u.Transform(),True)
  options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
  _,result=G.copy_mesh_to_skeletal_mesh(weapon,mesh,options,u.GeometryScriptMeshWriteLOD())
  if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('201 private native-arm assembly failed')
  E.set_metadata_tag(mesh,'FeedRevision','BeltFeed08: private lid/box/belt bones; actual Skin07 native arms preserved')
  save(private);save(mesh);receipt['mesh']=mesh.get_path_name();receipt['skeleton']=private.get_path_name();record()
 else:mesh=u.load_asset(receipt['mesh'])
 auth=json.loads((O/'motion_authoring.json').read_text())
 for key,d in auth['animations'].items():
  if key in receipt['animations']:continue
  name='A_LMG201_'+key;opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.skeleton=private;opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False
  opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
  task=u.AssetImportTask();task.filename=str(O/'Exports'/(name+'.fbx'));task.destination_path=P+'/Animations';task.destination_name=name;task.options=opt;task.factory=u.FbxFactory();task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;A.import_asset_tasks([task])
  clip=u.load_asset(P+'/Animations/'+name)
  if not clip or not task.imported_object_paths:raise RuntimeError('201 feed animation import failed '+name)
  clip.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));save(clip)
  receipt['animations'][key]={'asset':clip.get_path_name(),'seconds':clip.get_play_length()};record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
receipt['status']='imported_and_saved';record();print('201_BELTFEED_ASSETS_SAVED',len(receipt['animations']))
