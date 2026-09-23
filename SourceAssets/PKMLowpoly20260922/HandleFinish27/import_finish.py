"""Import seated handle hardware and author a restrained PKM-only matte finish.

Run via the existing editor bridge when an editor is open, otherwise commandlet.
The existing dry/wet assets and their mappings are retained, including optics.
"""
import unreal as u, json, sys, shutil
from pathlib import Path

O=Path(__file__).parent;R=O.parent
P='/Game/Weapons/PKMLowpoly20260922'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
project=Path(u.Paths.project_dir()).resolve()
is_commandlet='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not is_commandlet:
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('PKM27: stop PIE before replacing the PKM mesh/materials')

mesh=u.load_asset(P+'/Accessories14/SK_PKM_Manny_Modular')
skeleton=mesh.skeleton
if not skeleton.get_path_name().startswith(P+'/'):
    raise RuntimeError('PKM private skeleton required')
targets=[]
for directory in [P+'/Finish20/Materials',P+'/OpticMount23/Materials']:
    for path in E.list_assets(directory,recursive=False,include_folder=False):
        mat=u.load_asset(path)
        if not isinstance(mat,u.Material):continue
        category=str(E.get_metadata_tag(mat,'PKM20_Category'))
        if category=='metal' or mat.get_name().startswith('M_PKM23_Mount_'):
            targets.append(mat)

# Protect any user-authored unsaved change to these exact target packages.
# Unrelated dirty assets are neither saved nor touched.
target_packages={a.get_path_name().split('.')[0] for a in [mesh,skeleton]+targets}
if not is_commandlet:
    conflict=target_packages & {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if conflict:raise RuntimeError('PKM27 target assets have unsaved edits: '+str(sorted(conflict)))

backup=O/'BeforeImport'
for asset in [mesh,skeleton]+targets:
    package=asset.get_path_name().split('.')[0]
    source=project/'Content'/(package.removeprefix('/Game/')+'.uasset')
    destination=backup/source.relative_to(project/'Content')
    if source.exists() and not destination.exists():
        destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)

sys.path.insert(0,str(R/'Belt08'))
from material_binding import capture_bindings,bind_materials
bindings=capture_bindings(mesh)
(O/'materials_before.json').write_text(json.dumps({k:v.get_path_name() for k,v in bindings.items()},indent=2))
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False
opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=skeleton
d=opt.skeletal_mesh_import_data
d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
d.set_editor_property('update_skeleton_reference_pose',False)
d.set_editor_property('use_t0_as_ref_pose',False);d.set_editor_property('preserve_smoothing_groups',True)
task=u.AssetImportTask();task.filename=str(O/'Exports/SK_PKM_Manny_Modular.fbx')
task.destination_path=P+'/Accessories14';task.destination_name='SK_PKM_Manny_Modular'
task.options=opt;task.factory=u.FbxFactory();task.automated=True
task.replace_existing=True;task.replace_existing_settings=True;task.save=False
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
try:
    u.SystemLibrary.execute_console_command(None,flag+' 0');A.import_asset_tasks([task])
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
mesh=u.load_asset(P+'/Accessories14/SK_PKM_Manny_Modular')
if not mesh or not task.imported_object_paths:raise RuntimeError('PKM27 skeletal mesh import failed')
binding_report=bind_materials(mesh,{},bindings)
E.set_metadata_tag(mesh,'PKMHandleRevision','HandleFinish27; fasteners 80/81 follow PKM_CarryHandle; seated 0.45 mm caps')

def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())

save(mesh);save(mesh.skeleton)
report={'mesh':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),'mesh_saved':True,
        'materials':[],'bindings':binding_report,'game_tested':False,'animations_reimported':False}
receipt=O/'import_receipt.json'
receipt.write_text(json.dumps(report,indent=2))
micro=(R/'Finish20/MicroFinish.hlsl').read_text()
micro=micro.replace('return float4(saturate(scratch),f.noise(P*.65),smoothstep(.50,.82,f.noise(P*.23+7)),0);',
'''// Submillimeter coating grain fades when smaller than the pixel footprint.
float footprint=max(length(ddx(P)),length(ddy(P)));
float grain=lerp(.5,f.noise(P*16.0+31),1-saturate(footprint*16.0));
return float4(saturate(scratch),f.noise(P*.65),smoothstep(.50,.82,f.noise(P*.23+7)),grain);''')
rough=(O/'MatteRoughness.hlsl').read_text();color=(O/'MatteColor.hlsl').read_text()
before={}
for mat in targets:
    custom={str(n.get_editor_property('description')):n for n in L.get_material_expressions(mat)
            if isinstance(n,u.MaterialExpressionCustom)}
    names=['PKM20 physical micro finish','PKM20 varied roughness','PKM20 restrained scuffs']
    if any(n not in custom for n in names):
        raise RuntimeError('Expected PKM finish graph missing: '+mat.get_path_name())
    before[mat.get_path_name()]={n:str(custom[n].get_editor_property('code')) for n in names}
    for name,code in zip(names,[micro,rough,color]):custom[name].set_editor_property('code',code)
    for node in L.get_material_expressions(mat):
        if isinstance(node,u.MaterialExpressionScalarParameter) and str(node.get_editor_property('parameter_name'))=='PKM_MicroScratchStrength':
            node.set_editor_property('default_value',.42)
    E.set_metadata_tag(mat,'PKM27_Finish','Satin matte coating; retained source normal/AO/paint and wet layer; restrained scuffs')
    errors=[str(v) for v in L.recompile_material(mat)]
    if errors:raise RuntimeError('Material compilation failed: '+mat.get_path_name()+' '+str(errors))
    save(mat)
    report['materials'].append({'asset':mat.get_path_name(),'saved':True,'compiler_errors':errors})
    receipt.write_text(json.dumps(report,indent=2))
    print('PKM27_MATTE_SAVED',mat.get_name(),flush=True)
previous=O/'material_graphs_before.json'
if not previous.exists():previous.write_text(json.dumps(before,indent=2))
report['saved']=True;report['weather_mapping_preserved']=True
receipt.write_text(json.dumps(report,indent=2))
print('PKM27_COMPLETE',json.dumps({'mesh_saved':True,'materials_saved':len(report['materials']),
    'receipt':str(receipt),'game_tested':False}),flush=True)
