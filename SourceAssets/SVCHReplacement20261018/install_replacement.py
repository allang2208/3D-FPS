"""Save isolated replacement assets and native-arm routing without running a game."""
import unreal as u
import json,hashlib,copy
from pathlib import Path
O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve();ROOT='/Game/Weapons/SVCH/Replacement20261018'
MESH=ROOT+'/SK_SVCH_Replacement';PROFILE=ROOT+'/DA_SVCH_ReplacementGrip'
DONOR='/Game/Weapons/SVCH/Refined20261018/R8Surface/SK_SVCH_R8Surface'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt={'complete':False,'saved':[],'runtime_tested':False,'animations_modified':False,'native_V9_modified':False}
def checkpoint():(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
 receipt['saved'].append(a.get_path_name());checkpoint()
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing '+p)
 return a
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active game')
if E.does_asset_exist(MESH):raise RuntimeError('Replacement already exists; preserve saved work')
source=json.loads((O/'authoring_receipt.json').read_text());donor=load(DONOR)
materials={str(s.material_slot_name):s.material_interface for s in donor.materials if str(s.material_slot_name).startswith('MI_Manny_')}
for identity,row in source['materials'].items():
 name='M_'+identity;mat=A.create_asset(name,ROOT+'/Materials',u.Material,u.MaterialFactoryNew())
 if not mat:raise RuntimeError('Material creation failed '+name)
 L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
 if 'color' in row:
  for kind in ('color','normal'):
   path=row[kind];tn='T_'+identity+('_BC' if kind=='color' else '_N');task=u.AssetImportTask();task.filename=path;task.destination_path=ROOT+'/Textures';task.destination_name=tn;task.automated=True;task.save=False;A.import_asset_tasks([task]);tex=load(ROOT+'/Textures/'+tn)
   tex.set_editor_property('srgb',kind=='color');tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON if kind=='color' else u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP)
   tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_DEFAULT if kind=='color' else u.TextureCompressionSettings.TC_NORMALMAP)
   if kind=='normal':tex.set_editor_property('flip_green_channel',False)
   save(tex);node=L.create_material_expression(mat,u.MaterialExpressionTextureSample,-600,0 if kind=='color' else 200);node.texture=tex;node.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind=='color' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL
   L.connect_material_property(node,'RGB',u.MaterialProperty.MP_BASE_COLOR if kind=='color' else u.MaterialProperty.MP_NORMAL)
 else:
  node=L.create_material_expression(mat,u.MaterialExpressionConstant3Vector,-500,0);node.constant=u.LinearColor(*row['base_color'],1.);L.connect_material_property(node,'',u.MaterialProperty.MP_BASE_COLOR)
 for key,prop in [('roughness',u.MaterialProperty.MP_ROUGHNESS),('metallic',u.MaterialProperty.MP_METALLIC)]:
  node=L.create_material_expression(mat,u.MaterialExpressionConstant,-300,400 if key=='roughness' else 500);node.r=row[key];L.connect_material_property(node,'',prop)
 L.recompile_material(mat);save(mat);materials[identity]=mat
options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False;options.create_physics_asset=False;options.skeleton=donor.skeleton;options.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
task=u.AssetImportTask();task.filename=str(O/'SK_SVCH_Replacement.fbx');task.destination_path=ROOT;task.destination_name='SK_SVCH_Replacement';task.automated=True;task.save=False;task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=load(MESH)
slots=list(mesh.materials)
for i,s in enumerate(slots):s.material_interface=materials[str(s.material_slot_name)];slots[i]=s
mesh.set_editor_property('materials',slots)
editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);settings=editor.get_lod_build_settings(donor,0);settings.recompute_normals=False;settings.recompute_tangents=True;editor.set_lod_build_settings(mesh,0,settings)
E.set_metadata_tag(mesh,'Source','Sketchfab b3bb922bdf1a481a96b9e2940b2d26fc / FamousUnityHubSoldier; source package identifies MWIII KV Inhibitor; platform license Free Standard')
save(mesh)
arm_materials={i for i,s in enumerate(slots) if str(s.material_slot_name).startswith('MI_Manny_')}
code=(O.parent/'SVCHRefinement20261018/install_arm_correctives.py').read_text().replace('if s>=9','if s in arm_materials')
exec(compile(code,'install_native_correctives','exec'),{'__file__':str(O.parent/'SVCHRefinement20261018/install_arm_correctives.py'),'TARGET_MESH':MESH,'RECEIPT_PATH':O/'arm_correctives_receipt.json','arm_materials':arm_materials})
factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile);profile=A.create_asset('DA_SVCH_ReplacementGrip',ROOT,u.WeaponGripProfile,factory)
if not profile.set_shared_clips_from_json((O/'profile_replacement.json').read_text()):raise RuntimeError('Cannot author contact profile')
E.set_metadata_tag(profile,'ContactMethod','R11 source; whole-arm registration only at clavicles; wrist/finger locals and mechanical clocks preserved');save(profile)
mod=u.SkeletonModifier();mod.set_skeletal_mesh(mesh);ref=mod.get_bone_transform('WPN_root',True)
calibration={}
for key,p in source['landmarks_component_cm'].items():
 v=u.Vector(*p)
 v=u.MathLibrary.inverse_transform_direction(ref,v) if key=='SightUp' else u.MathLibrary.inverse_transform_location(ref,v)
 calibration[key]=[v.x,v.y,v.z]
(O/'calibration.json').write_text(json.dumps(calibration,indent=2));del mod
table=P/'Content/ColdSteelData/modular_outfits.json';data=json.loads(table.read_text(encoding='utf-8-sig'));entry=copy.deepcopy(data['profiles'][donor.get_path_name()]);entry['hide_source_materials']=sorted(arm_materials);entry['shirt_covers']=sorted(arm_materials);data['profiles'][mesh.get_path_name()]=entry;table.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt.update(complete=True,mesh=mesh.get_path_name(),profile=profile.get_path_name(),materials=[str(s.material_slot_name) for s in slots],arm_slots=sorted(arm_materials),outfit_profile=entry,fbx_sha256=hashlib.sha256((O/'SK_SVCH_Replacement.fbx').read_bytes()).hexdigest(),profile_source_sha256=hashlib.sha256((O/'profile_replacement.json').read_bytes()).hexdigest());checkpoint();print('SVCH_REPLACEMENT_ASSETS_SAVED',MESH,flush=True)
