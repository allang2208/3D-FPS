"""Import and save the new sight mesh; keep the accepted grip profile intact."""
import unreal as u,json,copy,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
ROOT='/Game/Weapons/SVCH/Replacement20261018/RealSights20261019'
MESH=ROOT+'/SK_SVCH_RealFoldingSights'
DONOR='/Game/Weapons/SVCH/Replacement20261018/SightsR2/ElbowFit/SK_SVCH_SightsR2_ElbowFit'
PROFILE='/Game/Weapons/SVCH/Replacement20261018/SightsR2/ElbowFit/DA_SVCH_ElbowFitGrip'
receipt={'complete':False,'saved':[],'profile_preserved':PROFILE,'source_animations_changed':False,'V9_changed':False,'runtime_tested':False}
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
 receipt['saved'].append(a.get_path_name());(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing '+p)
 return a
if E.does_asset_exist(MESH):raise RuntimeError('Preserve saved revision; resume only unfinished stage')
donor=load(DONOR);load(PROFILE)
materials={str(s.material_slot_name):s.material_interface for s in donor.materials}
task=u.AssetImportTask();task.filename=str(O/'T_SVCH_SightCoating.png');task.destination_path=ROOT+'/Textures';task.destination_name='T_SVCH_SightCoating';task.automated=True;task.save=False;A.import_asset_tasks([task])
tex=load(ROOT+'/Textures/T_SVCH_SightCoating');tex.set_editor_property('srgb',False);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS);save(tex)
mat=A.create_asset('M_SVCH_RealFoldingSights',ROOT+'/Materials',u.Material,u.MaterialFactoryNew());L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
vc=L.create_material_expression(mat,u.MaterialExpressionVertexColor)
sample=L.create_material_expression(mat,u.MaterialExpressionTextureSample);sample.texture=tex;sample.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS
L.connect_material_property(vc,'RGB',u.MaterialProperty.MP_BASE_COLOR)
metal=L.create_material_expression(mat,u.MaterialExpressionConstant);metal.r=.65;L.connect_material_property(metal,'',u.MaterialProperty.MP_METALLIC)
def custom(code,kind,connections):
 n=L.create_material_expression(mat,u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('output_type',kind);inputs=[]
 for name,src,out in connections:
  ci=u.CustomInput();ci.set_editor_property('input_name',name);inputs.append(ci)
 n.set_editor_property('inputs',inputs)
 for name,src,out in connections:L.connect_material_expressions(src,out,n,name)
 return n
rough=custom('return saturate(R + (T.b - 0.5)*0.06);',u.CustomMaterialOutputType.CMOT_FLOAT1,[('R',vc,'A'),('T',sample,'RGB')]);L.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
normal=custom('return normalize(float3((T.xy-0.5)*2.0,1.0));',u.CustomMaterialOutputType.CMOT_FLOAT3,[('T',sample,'RGB')]);L.connect_material_property(normal,'',u.MaterialProperty.MP_NORMAL)
L.layout_material_expressions(mat);L.recompile_material(mat);save(mat)
materials['SVCH_New_FactorySights']=mat
options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False;options.create_physics_asset=False;options.skeleton=donor.skeleton
options.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
options.skeletal_mesh_import_data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
task=u.AssetImportTask();task.filename=str(O/'SK_SVCH_RealFoldingSights.fbx');task.destination_path=ROOT;task.destination_name='SK_SVCH_RealFoldingSights';task.automated=True;task.save=False;task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=load(MESH);slots=list(mesh.materials)
for i,s in enumerate(slots):
 name=str(s.material_slot_name)
 if name.startswith('SVCH_New_FactorySights'):name='SVCH_New_FactorySights';s.material_slot_name=name
 s.material_interface=materials[name];slots[i]=s
mesh.set_editor_property('materials',slots);editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);editor.set_lod_build_settings(mesh,0,editor.get_lod_build_settings(donor,0));save(mesh)
arm_materials={i for i,s in enumerate(slots) if str(s.material_slot_name).startswith('MI_Manny_')}
helper=P/'SourceAssets/SVCHRefinement20261018/install_arm_correctives.py';code=helper.read_text().replace('if s>=9','if s in arm_materials');exec(compile(code,str(helper),'exec'),{'__file__':str(helper),'TARGET_MESH':MESH,'RECEIPT_PATH':O/'arm_correctives_receipt.json','arm_materials':arm_materials})
source=json.loads((O/'authoring_receipt.json').read_text());mod=u.SkeletonModifier();mod.set_skeletal_mesh(mesh);ref=mod.get_bone_transform('WPN_root',True);cal={}
for key,p in source['landmarks_component_cm'].items():
 v=u.MathLibrary.inverse_transform_direction(ref,u.Vector(*p)) if key=='SightUp' else u.MathLibrary.inverse_transform_location(ref,u.Vector(*p));cal[key]=[v.x,v.y,v.z]
(O/'calibration.json').write_text(json.dumps(cal,indent=2));del mod
table=P/'Content/ColdSteelData/modular_outfits.json';text=table.read_text(encoding='utf-8-sig');data=json.loads(text);entry=copy.deepcopy(data['profiles'][donor.get_path_name()]);entry['hide_source_materials']=sorted(arm_materials);data['profiles'][mesh.get_path_name()]=entry
if table.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Preserve concurrent outfit update')
table.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt.update(complete=True,mesh=mesh.get_path_name(),profile=PROFILE,fbx_sha256=hashlib.sha256((O/'SK_SVCH_RealFoldingSights.fbx').read_bytes()).hexdigest(),arm_slots=sorted(arm_materials))
(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2));print('SVCH_REAL_SIGHTS_SAVED',mesh.get_path_name(),flush=True)
