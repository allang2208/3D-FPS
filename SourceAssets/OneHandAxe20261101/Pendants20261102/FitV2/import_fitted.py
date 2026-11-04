"""Save the three fitted roots without overwriting any shared common pendant."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
if Path(u.Paths.project_dir()).resolve()!=P.parent/'ImportProject':
    raise RuntimeError('This fitted-mesh import is restricted to the isolated authoring project')
fit=json.loads((P/'fit.json').read_text('utf-8'))
DEST='/Game/Weapons/TacticalHatchet20261101/PendantsV2'
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary
receipt={'complete':False,'saved_assets':[],'parts':[],'gameplay_tested':False}
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed: '+asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name())
    (P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
name='M_TacticalHatchet_PendantCord_FitV2'
cord=u.load_asset(DEST+'/'+name) or A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
E.delete_all_material_expressions(cord)
def constant(value):
    n=E.create_material_expression(cord,u.MaterialExpressionConstant);n.set_editor_property('r',value);return n
base=E.create_material_expression(cord,u.MaterialExpressionConstant3Vector)
base.set_editor_property('constant',u.LinearColor(.035,.045,.028,1))
rough=constant(.8);metal=constant(0.)
slab=E.create_material_expression(cord,u.MaterialExpressionSubstrateShadingModels)
slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
for node,pin,prop in [(base,'BaseColor',u.MaterialProperty.MP_BASE_COLOR),(rough,'Roughness',u.MaterialProperty.MP_ROUGHNESS),(metal,'Metallic',u.MaterialProperty.MP_METALLIC)]:
    E.connect_material_expressions(node,'',slab,pin);E.connect_material_property(node,'',prop)
E.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
E.recompile_material(cord);save(cord)
editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for entry in fit['parts']:
    options=u.FbxImportUI();options.import_mesh=True;options.import_as_skeletal=False
    options.import_materials=False;options.import_textures=False;options.import_animations=False
    options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    settings=options.static_mesh_import_data;settings.combine_meshes=True;settings.auto_generate_collision=False
    settings.generate_lightmap_u_vs=False;settings.convert_scene=True;settings.convert_scene_unit=True
    settings.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_path=DEST;task.destination_name=entry['object']
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=options;task.factory=u.FbxFactory()
    A.import_asset_tasks([task]);mesh=u.load_asset(entry['mesh'])
    if not mesh or not mesh.get_static_mesh_description(0):raise RuntimeError('Persistent mesh source missing')
    original=u.load_asset(entry['source_material'])
    if not original:raise RuntimeError('Common pendant material missing')
    slots=list(mesh.static_materials)
    for i,slot in enumerate(slots):
        key=str(slot.get_editor_property('imported_material_slot_name'))
        material=cord if key==name else original
        slot.set_editor_property('material_slot_name',material.get_name())
        slot.set_editor_property('material_interface',material)
    mesh.set_editor_property('static_materials',slots)
    nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=False;mesh.set_editor_property('nanite_settings',nanite)
    build=editor.get_lod_build_settings(mesh,0);build.recompute_normals=False;build.recompute_tangents=True
    build.use_mikk_t_space=True;build.use_high_precision_tangent_basis=True;build.use_full_precision_u_vs=True
    editor.set_lod_build_settings(mesh,0,build)
    save(mesh)
    receipt['parts'].append({'id':entry['id'],'mesh':mesh.get_path_name(),'location_cm':fit['location_cm'],
        'material_slot_names':[str(s.get_editor_property('material_slot_name')) for s in mesh.static_materials],
        'materials':{str(s.get_editor_property('material_slot_name')):s.get_editor_property('material_interface').get_path_name() for s in mesh.static_materials}})

# Export the saved UE geometry for the user-requested through-hole inspection.
(P/'UEGeometry').mkdir(exist_ok=True)
catalog=json.loads((ROOT/'Content/ColdSteelData/tactical-hatchet-modules.json').read_text('utf-8'))
paths=[e['mesh'] for e in fit['parts']]+[s['mesh'] for s in catalog['slots']['pommel'].values()]
for path in paths:
    task=u.AssetExportTask();task.object=u.load_asset(path);task.filename=str(P/'UEGeometry'/(path.split('.')[-1]+'.fbx'))
    task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.StaticMeshExporterFBX();task.options=u.FbxExportOption()
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Saved geometry export failed '+path)
receipt['complete']=True
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
u.log('HATCHET_PENDANT_FIT_SAVED')
