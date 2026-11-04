"""Save the newly named head, material, PBR and actual-model icon packages."""
import ast,json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
DEST='/Game/Weapons/TacticalHatchet20261101/FalconEdge20261103'
MESH_DEST='/Game/Weapons/TacticalHatchet20261101/ModulesV1'
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary
entry=json.loads((P/'falcon_edge.json').read_text('utf-8'))
icon_name='ue_tactical_hatchet_blade_1_hatchet_falcon_edge'
owned={MESH_DEST+'/'+entry['object'],DEST+'/Materials/'+entry['object'].replace('SM_','M_',1)}
owned.update(DEST+'/Textures/'+Path(p).stem for p in entry['textures'].values())
owned.add('/Game/ColdSteelData/AttachmentIcons20260913/'+icon_name)
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if owned&dirty:raise RuntimeError('Owned assets have unsaved changes; preserved')
receipt={'complete':False,'assets':[],'parts':[],'runtime_tested':False}
previous=json.loads((P/'import_receipt.json').read_text('utf-8')) if (P/'import_receipt.json').exists() else {}
source=P.parent/'ModulesV1/import_modules.py';tree=ast.parse(source.read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'save','imported','material'}],type_ignores=[]),str(source),'exec'),globals())
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
material_path=DEST+'/Materials/'+entry['object'].replace('SM_','M_',1)
saved_material=material_path+'.'+entry['object'].replace('SM_','M_',1)
mat=None
if previous and not previous.get('complete') and saved_material in previous.get('assets',[]):
    # Resume the already saved PBR batch after the mesh path restriction failure.
    mat=u.load_asset(material_path)
    if mat:receipt['assets']=previous['assets'][:]
if not mat:mat=material(entry)
ui=u.FbxImportUI();ui.import_mesh=True;ui.import_as_skeletal=False;ui.import_materials=False;ui.import_textures=False;ui.import_animations=False
ui.automated_import_should_detect_type=False;ui.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
settings=ui.static_mesh_import_data;settings.combine_meshes=True;settings.auto_generate_collision=False
settings.convert_scene=True;settings.convert_scene_unit=True;settings.generate_lightmap_u_vs=False
settings.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
mesh=imported(entry['fbx'],entry['object'],MESH_DEST,ui)
for i in range(len(mesh.static_materials)):mesh.set_material(i,mat)
nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=True;mesh.set_editor_property('nanite_settings',nanite)
if not u.TacticalHatchetImportLibrary.finalize_mesh(mesh):raise RuntimeError('Head tangent authoring failed')
u.EditorAssetLibrary.set_metadata_tag(mesh,'HatchetInterface','Factory neck below 18cm retained; grip cut 11.5cm; triangular through window; short rear beak')
save(mesh)
receipt['parts'].append({'id':entry['id'],'slot':'blade_1','mesh':mesh.get_path_name(),'material':mat.get_path_name(),
    'material_slot_names':[str(s.get_editor_property('material_slot_name')) for s in mesh.static_materials],
    'location_cm':entry['origin_cm'],'trace_base_cm':entry['trace_base_cm'],'trace_tip_cm':entry['trace_tip_cm']})
icon=imported(P/'Icons'/(icon_name+'.png'),icon_name,'/Game/ColdSteelData/AttachmentIcons20260913')
icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
icon.set_editor_property('srgb',True);icon.set_editor_property('never_stream',True)
icon.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
icon.set_editor_property('max_texture_size',1024);save(icon)
receipt['icon']=icon.get_path_name();receipt['complete']=True
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
u.log('FALCON_EDGE_SAVED')
