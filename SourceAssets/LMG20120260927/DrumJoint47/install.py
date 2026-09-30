"""Save only the corrected 201 drum joint, its finish and production icon."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];D='/Game/Weapons/LMG201/DrumJoint47';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;G=u.GeometryScript_AssetUtils
C=json.loads((O/'capture.json').read_text());M=json.loads((O/'model.json').read_text());BODY=C['assets']['Body']['asset'];TARGET=C['assets']['Drum']['asset'];WET='/Game/Weapons/LMG201/Accessories22/DA_LMG201_AttachmentWetMaterials'
R=json.loads((O/'delivery.json').read_text()) if (O/'delivery.json').exists() else {'saved':{},'backups':{},'runtime_tested':False,'animations_changed':False,'native_code_changed':False}
def record():(O/'delivery.json').write_text(json.dumps(R,indent=2))
def file(p):return P/'Content'/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(p):return hashlib.sha256(file(p).read_bytes()).hexdigest()
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing '+p)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
 R['saved'][a.get_path_name().split('.')[0]]={'sha256':sha(a.get_path_name())};record()
def backup(p):
 if p in R['backups']:return
 f=file(p);dest=O/'Before'/f.relative_to(P/'Content');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest);R['backups'][p]={'file':str(dest),'sha256':sha(p)};record()
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('PIE active; target retained')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty&{TARGET,WET}:raise RuntimeError('Unsaved target retained')
if sha(BODY)!=C['assets']['Body']['sha256']:raise RuntimeError('Host body changed since interface capture')
if sha(TARGET)!=R['saved'].get(TARGET,{}).get('sha256',C['assets']['Drum']['sha256']):raise RuntimeError('Drum changed since capture')
backup(TARGET);backup(WET)
body=load(BODY);slots={str(s.material_slot_name):s.material_interface for s in body.materials};coat=slots['M_LMG201_Magazine']
def param(key,default):
 for n in L.get_material_expressions(coat.get_base_material()):
  if isinstance(n,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter)) and str(n.get_editor_property('parameter_name'))==key:return n.get_editor_property('default_value')
 return default
def node(m,cls,**values):
 n=L.create_material_expression(m,cls)
 for k,v in values.items():n.set_editor_property(k,v)
 return n
def custom(m,code,inputs,kind):
 n=node(m,u.MaterialExpressionCustom,code=code,output_type=kind);pins=[]
 for k in inputs:
  pin=u.CustomInput();pin.set_editor_property('input_name',k);pins.append(pin)
 n.set_editor_property('inputs',pins)
 for k,v in inputs.items():L.connect_material_expressions(v,'',n,k)
 return n
name='M_LMG201_D47_AdapterCoat';p=D+'/Materials/'+name
mat=u.load_asset(p) or A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(mat)
tint=node(mat,u.MaterialExpressionVectorParameter,parameter_name='201FinishTint',default_value=param('G43_FinishTint',u.LinearColor(.0175,.021,.0255,1)))
rough=node(mat,u.MaterialExpressionScalarParameter,parameter_name='201FinishRoughness',default_value=float(param('G43_Roughness',.385)))
wet=node(mat,u.MaterialExpressionScalarParameter,parameter_name='WeaponWetness',default_value=0.)
base=custom(mat,'return Tint*(1-.12*saturate(Wet));',{'Tint':tint,'Wet':wet},u.CustomMaterialOutputType.CMOT_FLOAT3)
r=custom(mat,'return lerp(Rough,Rough*.73,saturate(Wet));',{'Rough':rough,'Wet':wet},u.CustomMaterialOutputType.CMOT_FLOAT1)
for n,prop in [(base,u.MaterialProperty.MP_BASE_COLOR),(r,u.MaterialProperty.MP_ROUGHNESS),(node(mat,u.MaterialExpressionScalarParameter,parameter_name='201Metallic',default_value=float(param('G43_Metallic',.68))),u.MaterialProperty.MP_METALLIC),(node(mat,u.MaterialExpressionScalarParameter,parameter_name='Specular',default_value=.42),u.MaterialProperty.MP_SPECULAR)]:L.connect_material_property(n,'',prop)
err=L.recompile_material(mat)
if err:raise RuntimeError('Material compilation '+str(err))
E.set_metadata_tag(mat,'FinishSource',coat.get_path_name()+' parameters; clean new adapter surface with no inherited generated-magazine normal map');save(mat)
digest=hashlib.sha256(Path(M['mesh']).read_bytes()).hexdigest();candidate=D+'/Parts/SM_D47_'+digest[:10]
source=u.load_asset(candidate)
if not source:
 opt=u.FbxImportUI();opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
 data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.remove_degenerates=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
 task=u.AssetImportTask();task.filename=M['mesh'];task.destination_path=D+'/Parts';task.destination_name=candidate.rsplit('/',1)[1];task.automated=True;task.save=False;task.factory=u.FbxFactory();task.options=opt
 flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
 try:A.import_asset_tasks([task])
 finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
 source=load(candidate)
bindings={s['name']:load(s['material']) for s in C['assets']['Drum']['slots'][:3]}
bindings.update(D47_AdapterCoat=mat,D47_ShoulderPolymer=load('/Game/Weapons/LMG201/Drum46/Materials/M_LMG201_D46_Transition'),D47_RecessInside=slots['M_LMG201_MagazineInside'])
newslots=[s.copy() for s in source.static_materials]
for i,s in enumerate(newslots):s.material_interface=bindings[str(s.material_slot_name)];newslots[i]=s
source.static_materials=newslots;sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
build=sm.get_lod_build_settings(source,0);build.remove_degenerates=False;sm.set_lod_build_settings(source,0,build);save(source)
dm,result=G.copy_mesh_from_static_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Read produced drum')
current=load(TARGET);options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[s.material_interface for s in newslots],new_material_slot_names=[s.material_slot_name for s in newslots],enable_recompute_normals=False,enable_recompute_tangents=True)
_,result=G.copy_mesh_to_static_mesh(dm,current,options,u.GeometryScriptMeshWriteLOD())
if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Write current drum')
current.static_materials=newslots;build=sm.get_lod_build_settings(current,0);build.remove_degenerates=False;sm.set_lod_build_settings(current,0,build)
current.get_editor_property('asset_import_data').scripted_add_filename(M['mesh'],0,'DrumJoint47 closed adapter in active idle frame')
E.set_metadata_tag(current,'SourceModel',M['source_blend']);E.set_metadata_tag(current,'201DrumRevision','DrumJoint47: closed adapter replaces copied factory neck; accepted shell/contact/motion retained');save(current)
table=load(WET);mapping=dict(table.get_editor_property('wet_materials'));mapping[mat.get_path_name()]=mat;table.set_editor_property('wet_materials',mapping);save(table)
icon=json.loads((O/'icon.json').read_text());iconpath='/Game/ColdSteelData/AttachmentIcons20260913/'+icon['key'];backup(iconpath)
png=P/'Content/ColdSteelData/AttachmentIcons20260913'/(icon['key']+'.png');oldpng=O/'Before'/(icon['key']+'.png')
if png.exists() and not oldpng.exists():shutil.copy2(png,oldpng)
shutil.copy2(icon['file'],png)
task=u.AssetImportTask();task.filename=str(png);task.destination_path=iconpath.rsplit('/',1)[0];task.destination_name=icon['key'];task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);tex=load(iconpath);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON);tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);save(tex)
(O/'Exports').mkdir(exist_ok=True);ex=u.AssetExportTask();ex.object=current;ex.filename=str(O/'Exports/After_Drum.fbx');ex.automated=True;ex.prompt=False;ex.replace_identical=True;ex.options=u.FbxExportOption();ex.options.level_of_detail=False;ex.options.collision=False;ex.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
if not u.Exporter.run_asset_export_task(ex):raise RuntimeError('Export saved joint')
R.update(status='saved',source_sha256=digest,mesh=TARGET,bindings={str(s.material_slot_name):s.material_interface.get_path_name() for s in current.static_materials},source_boundary_edges=M['joint_boundary_edges'],pose_frame='201 active idle; unchanged magazine socket',icon=str(png),factory_magazine_geometry_removed_from_drum=True);record();print('D47_ASSETS_SAVED',flush=True)
