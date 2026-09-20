import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/M16A2/UniversalAttachments20260920';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;report={}
def save(a):E.save_loaded_asset(a,False)
def import_file(file,name,folder,options=None):
 t=u.AssetImportTask();t.filename=str(file);t.destination_path=folder;t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=False
 if options:t.options=options
 A.import_asset_tasks([t]);asset=u.load_asset(folder+'/'+name)
 if not asset:raise RuntimeError('Import failed '+name)
 return asset
gpath=D+'/Materials/M_M16_HoloGlass';glass=u.load_asset(gpath) or A.create_asset('M_M16_HoloGlass',D+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(glass)
glass.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);glass.set_editor_property('two_sided',True);glass.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
def constant(value,prop):
 n=L.create_material_expression(glass,u.MaterialExpressionConstant);n.set_editor_property('r',value);L.connect_material_property(n,'',prop)
n=L.create_material_expression(glass,u.MaterialExpressionConstant3Vector);n.set_editor_property('constant',u.LinearColor(.085,.16,.18,1));L.connect_material_property(n,'',u.MaterialProperty.MP_BASE_COLOR)
for v,p in [(.07,u.MaterialProperty.MP_OPACITY),(.08,u.MaterialProperty.MP_ROUGHNESS),(.18,u.MaterialProperty.MP_SPECULAR),(0.,u.MaterialProperty.MP_METALLIC)]:constant(v,p)
L.recompile_material(glass);save(glass)
models=json.loads((O/'models.json').read_text())
for key in ['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','balanced_reargrip']:
 part=models[key];old=u.load_asset(D+'/Meshes/'+part['name']);bindings={str(s.material_slot_name):s.material_interface for s in old.static_materials}
 bindings['M16_HoloGlass']=glass;bindings['M16_FactoryGripInterface']=u.load_asset('/Game/Weapons/M16A2Migration/Materials/M_M16A2_PBR')
 options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;options.import_as_skeletal=False;options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_animations=False
 data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
 mesh=import_file(part['file'],part['name'],D+'/Meshes',options);slots=mesh.static_materials
 for i,s in enumerate(slots):
  label=str(s.material_slot_name)
  if label not in bindings:raise RuntimeError('Unbound slot '+key+'/'+label)
  s.material_interface=bindings[label];slots[i]=s
 mesh.set_editor_property('static_materials',slots);E.set_metadata_tag(mesh,'M16Refinement','Source-seated carry handle / dedicated clear glass / factory-conforming grip collar 20260920');save(mesh)
 report[key]={'asset':mesh.get_path_name(),'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials}}
sound=import_file(O/'Audio/S_M16_OriginalFire.wav','S_M16_OriginalFire','/Game/Weapons/M16A2/OriginalAudio20260920');sound.set_editor_property('volume',1.);sound.set_editor_property('pitch',1.);save(sound);report['audio']=sound.get_path_name()
skeleton=u.load_asset('/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny').skeleton;compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
for key,clip in json.loads((O/'reloads.json').read_text()).items():
 options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;options.import_mesh=False;options.import_animations=True;options.import_materials=False;options.import_textures=False;options.skeleton=skeleton
 data=options.anim_sequence_import_data;data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',120)
 anim=import_file(clip['file'],clip['name'],clip['folder'],options);anim.set_editor_property('bone_compression_settings',compression);save(anim);report[key]={'asset':anim.get_path_name(),'duration':anim.get_play_length()}
(O/'installation.json').write_text(json.dumps(report,indent=2));print('M16_REFINEMENT_IMPORTED',len(report))
