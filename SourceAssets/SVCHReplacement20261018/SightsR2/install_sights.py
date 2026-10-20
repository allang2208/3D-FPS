"""Install a private sight revision, preserving the accepted replacement contacts."""
import unreal as u,json,copy,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
ROOT='/Game/Weapons/SVCH/Replacement20261018/SightsR2';MESH=ROOT+'/SK_SVCH_SightsR2';DONOR='/Game/Weapons/SVCH/Replacement20261018/SK_SVCH_Replacement';PROFILE='/Game/Weapons/SVCH/Replacement20261018/DA_SVCH_ReplacementGrip'
receipt={'complete':False,'saved':[],'profile_preserved':PROFILE,'source_animations_modified':False,'V9_modified':False,'runtime_tested':False}
def record():(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing '+path)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
 receipt['saved'].append(a.get_path_name());record()
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve current PIE; install once it has ended')
if E.does_asset_exist(MESH):raise RuntimeError('SightsR2 already exists; do not replace an existing revision')
donor=load(DONOR);load(PROFILE);recipe=json.loads((O/'material_recipe.json').read_text())
materials={str(s.material_slot_name):s.material_interface for s in donor.materials}
mat=load(ROOT+'/Materials/M_SVCH_DetailedSights') if E.does_asset_exist(ROOT+'/Materials/M_SVCH_DetailedSights') else A.create_asset('M_SVCH_DetailedSights',ROOT+'/Materials',u.Material,u.MaterialFactoryNew())
L.delete_all_material_expressions(mat);L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
def c(value):n=L.create_material_expression(mat,u.MaterialExpressionConstant);n.r=value;return n
def mathnode(cls,inputs):
 n=L.create_material_expression(mat,cls)
 for name,(src,output) in inputs.items():L.connect_material_expressions(src,output,n,name)
 return n
textures={};samples={}
for kind in ('albedo','normal','roughness','metallic','AO'):
 tex=load(recipe['source_texture_root']+kind);textures[kind]=tex.get_path_name();n=L.create_material_expression(mat,u.MaterialExpressionTextureSample);n.texture=tex;n.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind=='albedo' else u.MaterialSamplerType.SAMPLERTYPE_MASKS;samples[kind]=n
color=mathnode(u.MaterialExpressionMultiply,{'A':(samples['albedo'],'RGB'),'B':(c(recipe['color_multiplier']),'')});L.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
metal=mathnode(u.MaterialExpressionMultiply,{'A':(samples['metallic'],'R'),'B':(c(recipe['metallic_multiplier']),'')});L.connect_material_property(metal,'',u.MaterialProperty.MP_METALLIC)
rough=mathnode(u.MaterialExpressionMultiply,{'A':(samples['roughness'],'R'),'B':(c(recipe['roughness_scale']),'')});rough=mathnode(u.MaterialExpressionAdd,{'A':(rough,''),'B':(c(recipe['roughness_offset']),'')});L.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
normal=L.create_material_expression(mat,u.MaterialExpressionCustom);normal.set_editor_property('code','return normalize(float3(N.xy * 0.85, N.z));');normal.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3);ci=u.CustomInput();ci.set_editor_property('input_name','N');normal.set_editor_property('inputs',[ci]);L.connect_material_expressions(samples['normal'],'RGB',normal,'N');L.connect_material_property(normal,'',u.MaterialProperty.MP_NORMAL);L.connect_material_property(samples['AO'],'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
L.layout_material_expressions(mat);L.recompile_material(mat);save(mat);materials['SVCH_New_FactorySights']=mat
options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False;options.create_physics_asset=False;options.skeleton=donor.skeleton;options.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
task=u.AssetImportTask();task.filename=str(O/'SK_SVCH_SightsR2.fbx');task.destination_path=ROOT;task.destination_name='SK_SVCH_SightsR2';task.automated=True;task.save=False;task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=load(MESH);slots=list(mesh.materials)
for i,slot in enumerate(slots):
 name=str(slot.material_slot_name)
 if name=='SVCH_New_FactorySights_001':
  name='SVCH_New_FactorySights';slot.material_slot_name=name
 slot.material_interface=materials[name];slots[i]=slot
mesh.set_editor_property('materials',slots);editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);editor.set_lod_build_settings(mesh,0,editor.get_lod_build_settings(donor,0));E.set_metadata_tag(mesh,'SVCHSightRevision','R2: detailed diopter, curved front hood, preserved body/V9/contacts, single-mesh FBX bind');save(mesh)
arm_materials={i for i,s in enumerate(slots) if str(s.material_slot_name).startswith('MI_Manny_')}
helper=P/'SourceAssets/SVCHRefinement20261018/install_arm_correctives.py';code=helper.read_text().replace('if s>=9','if s in arm_materials');exec(compile(code,str(helper),'exec'),{'__file__':str(helper),'TARGET_MESH':MESH,'RECEIPT_PATH':O/'arm_correctives_receipt.json','arm_materials':arm_materials})
source=json.loads((O/'authoring_receipt.json').read_text());mod=u.SkeletonModifier();mod.set_skeletal_mesh(mesh);ref=mod.get_bone_transform('WPN_root',True);calibration={}
for key,p in source['landmarks_component_cm'].items():
 v=u.MathLibrary.inverse_transform_direction(ref,u.Vector(*p)) if key=='SightUp' else u.MathLibrary.inverse_transform_location(ref,u.Vector(*p));calibration[key]=[v.x,v.y,v.z]
(O/'calibration.json').write_text(json.dumps(calibration,indent=2));del mod
table=P/'Content/ColdSteelData/modular_outfits.json';text=table.read_text(encoding='utf-8-sig');data=json.loads(text);entry=copy.deepcopy(data['profiles'][donor.get_path_name()]);entry['hide_source_materials']=sorted(arm_materials);entry['shirt_covers']=sorted(arm_materials);data['profiles'][mesh.get_path_name()]=entry
if table.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Preserve parallel outfit update; resume table registration separately')
table.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');receipt.update(complete=True,mesh=mesh.get_path_name(),arm_slots=sorted(arm_materials),materials=[str(s.material_slot_name) for s in slots],texture_references=textures,fbx_sha256=hashlib.sha256((O/'SK_SVCH_SightsR2.fbx').read_bytes()).hexdigest());record();print('SVCH_SIGHTS_R2_SAVED',mesh.get_path_name(),flush=True)
import runpy
runpy.run_path(str(O/'collect_saved_geometry.py'))
