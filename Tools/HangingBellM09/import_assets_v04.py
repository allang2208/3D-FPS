"""Import M09 source-preserving mesh, PBR, clips and original cues; no gameplay or renders."""
import unreal as u,json
from pathlib import Path
ROOT=Path("D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003")
MOTION=ROOT/"MotionV04";DEST="/Game/Monsters/HangingBellM09/V04"
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();ME=u.MaterialEditingLibrary
REPORT=MOTION/"Records/ue_assets_v04.json"
report=json.loads(REPORT.read_text()) if REPORT.exists() else {"saved":[],"stages":[],"tested":False}
stage=globals().get("M09_STAGE","mesh")
if not globals().get("M09_COMMANDLET",False):
 if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError("PIE active; asset writing deferred")
 if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
  raise RuntimeError("M09 target packages have unsaved changes")
def save(asset):
 if not LIB.save_loaded_asset(asset,False):raise RuntimeError("Could not save "+asset.get_path_name())
 if asset.get_path_name() not in report["saved"]:report["saved"].append(asset.get_path_name())
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
def import_file(path,name,folder,options=None,factory=None):
 t=u.AssetImportTask();t.filename=str(path);t.destination_path=folder;t.destination_name=name
 t.automated=True;t.save=False;t.replace_existing=False
 if options:t.options=options
 if factory:t.factory=factory
 AT.import_asset_tasks([t])
 if not t.imported_object_paths:raise RuntimeError("No asset imported: "+str(path))
 asset=u.load_asset(folder+"/"+name)
 if not asset:raise RuntimeError("Expected import path missing: "+folder+"/"+name)
 return asset
def fbx(kind,skeleton=None):
 o=u.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=kind
 o.import_as_skeletal=kind!=u.FBXImportType.FBXIT_STATIC_MESH
 o.import_animations=kind==u.FBXImportType.FBXIT_ANIMATION;o.import_mesh=not o.import_animations
 o.import_materials=False;o.import_textures=False
 if skeleton:o.skeleton=skeleton
 data=o.anim_sequence_import_data if o.import_animations else o.skeletal_mesh_import_data if o.import_as_skeletal else o.static_mesh_import_data
 data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
 if not o.import_animations:data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
 return o
def get_or_make(name,folder,cls,factory):
 return u.load_asset(folder+"/"+name) if LIB.does_asset_exist(folder+"/"+name) else AT.create_asset(name,folder,cls,factory)
u.SystemLibrary.execute_console_command(None,"Interchange.FeatureFlags.Import.FBX 0")
if stage=="mesh":
 path=DEST+"/SK_M09"
 if LIB.does_asset_exist(path):mesh=u.load_asset(path)
 else:
  o=fbx(u.FBXImportType.FBXIT_SKELETAL_MESH);o.create_physics_asset=True
  mesh=import_file(ROOT/"RigV03/Exports/M09_Rigged_v03.fbx","SK_M09",DEST,o,u.FbxFactory())
 for asset in [mesh,mesh.skeleton,mesh.physics_asset]:
  if asset:save(asset)
 LIB.set_metadata_tag(mesh,"Source","M09 Rig V03, full source topology preserved; authoring high-poly")
 LIB.set_metadata_tag(mesh,"Acceptance","Not tested; user gameplay and deformation review pending")
 save(mesh)
elif stage=="materials":
 textures={}
 for key,filename in [("Base","M09_BaseColor.jpg"),("ORM","M09_MetallicRoughness.jpg"),("Normal","M09_Normal.jpg")]:
  p=DEST+"/Textures/T_M09_"+key
  texture=u.load_asset(p) if LIB.does_asset_exist(p) else import_file(ROOT/"Textures"/filename,"T_M09_"+key,DEST+"/Textures")
  if key!="Base":texture.set_editor_property("srgb",False)
  if key=="Normal":
   texture.set_editor_property("compression_settings",u.TextureCompressionSettings.TC_NORMALMAP)
   texture.set_editor_property("flip_green_channel",True)
  elif key=="ORM":texture.set_editor_property("compression_settings",u.TextureCompressionSettings.TC_MASKS)
  textures[key]=texture;save(texture)
 body=get_or_make("M_M09_Body",DEST+"/Materials",u.Material,u.MaterialFactoryNew());ME.delete_all_material_expressions(body)
 body.set_editor_property("two_sided",True)
 slab=ME.create_material_expression(body,u.MaterialExpressionSubstrateShadingModels)
 for key,pin,prop,channel in [("Base","BaseColor",u.MaterialProperty.MP_BASE_COLOR,"RGB"),("Normal","Normal",u.MaterialProperty.MP_NORMAL,"RGB"),
                              ("ORM","Roughness",u.MaterialProperty.MP_ROUGHNESS,"G"),("ORM","Metallic",u.MaterialProperty.MP_METALLIC,"B")]:
  tex=ME.create_material_expression(body,u.MaterialExpressionTextureSample);tex.texture=textures[key]
  tex.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=="Normal" else u.MaterialSamplerType.SAMPLERTYPE_MASKS if key=="ORM" else u.MaterialSamplerType.SAMPLERTYPE_COLOR
  ME.connect_material_property(tex,channel,prop);ME.connect_material_expressions(tex,channel,slab,pin)
 ME.connect_material_property(slab,"",u.MaterialProperty.MP_FRONT_MATERIAL);ME.recompile_material(body);save(body)
 mesh=u.load_asset(DEST+"/SK_M09");slots=list(mesh.materials)
 for slot in slots:slot.material_interface=body
 mesh.set_editor_property("materials",slots);save(mesh)
 energy=get_or_make("M_M09_Energy",DEST+"/Materials",u.Material,u.MaterialFactoryNew());ME.delete_all_material_expressions(energy)
 energy.set_editor_property("two_sided",True)
 slab=ME.create_material_expression(energy,u.MaterialExpressionSubstrateShadingModels)
 color=ME.create_material_expression(energy,u.MaterialExpressionConstant3Vector);color.constant=u.LinearColor(.12,1.8,2.5,1)
 ME.connect_material_expressions(color,"",slab,"Emissive Color");ME.connect_material_property(color,"",u.MaterialProperty.MP_EMISSIVE_COLOR)
 ME.connect_material_property(slab,"",u.MaterialProperty.MP_FRONT_MATERIAL);ME.recompile_material(energy);save(energy)
elif stage=="motion":
 mesh=u.load_asset(DEST+"/SK_M09")
 manifest=json.loads((MOTION/"Records/motion_manifest.json").read_text())
 for role,data in manifest.items():
  name="A_M09_"+role;path=DEST+"/Animations/"+name
  if LIB.does_asset_exist(path):clip=u.load_asset(path)
  else:
   o=fbx(u.FBXImportType.FBXIT_ANIMATION,mesh.skeleton)
   o.anim_sequence_import_data.set_editor_property("use_default_sample_rate",False)
   o.anim_sequence_import_data.set_editor_property("custom_sample_rate",30)
   o.anim_sequence_import_data.set_editor_property("animation_length",u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
   clip=import_file(data["file"],name,DEST+"/Animations",o,u.FbxFactory())
  clip.set_editor_property("enable_root_motion",False);clip.set_editor_property("force_root_lock",True)
  clip.set_editor_property("loop",data["loop"]);clip.set_preview_skeletal_mesh(mesh);save(clip)
 save(mesh.skeleton)
elif stage=="fx":
 name="SM_M09_Wave";path=DEST+"/FX/"+name
 if not LIB.does_asset_exist(path):
  o=fbx(u.FBXImportType.FBXIT_STATIC_MESH);o.static_mesh_import_data.set_editor_property("auto_generate_collision",False)
  o.static_mesh_import_data.set_editor_property("combine_meshes",True)
  wave=import_file(MOTION/"FX/SM_M09_Wave.fbx",name,DEST+"/FX",o,u.FbxFactory());save(wave)
 for f in (MOTION/"Audio").glob("*.wav"):
  p=DEST+"/Audio/"+f.stem
  snd=u.load_asset(p) if LIB.does_asset_exist(p) else import_file(f,f.stem,DEST+"/Audio",factory=u.SoundFactory())
  snd.set_editor_property("volume",.7);save(snd)
else:raise RuntimeError("Unknown production stage "+stage)
if stage not in report["stages"]:report["stages"].append(stage)
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
print("M09_SAVED_STAGE "+stage+" assets="+str(len(report["saved"])))
