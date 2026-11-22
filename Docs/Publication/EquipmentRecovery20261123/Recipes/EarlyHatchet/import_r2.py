"""Rebuild only the three archived R2 sets. No catalog or icon imports."""
from pathlib import Path
import ast,json
import unreal as u
work=Path(__file__).resolve().parent
project=Path("D:/FPS3D/FPSGAME")
replay=Path("F:/FPSGAME-Recovery-Work-20261120/NovemberFurtherRecovery/BladeR2")
entry_file=project/"SourceAssets/OneHandAxe20261101/ModulesV1/import_modules.py"
DEST='/Game/Weapons/TacticalHatchet20261101/ModulesV1'
A=u.AssetToolsHelpers.get_asset_tools()
E=u.MaterialEditingLibrary
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Cannot save '+asset.get_path_name())
    saved.append(asset.get_path_name().split('.')[0])
txt=entry_file.read_text(encoding='utf-8-sig').replace("set_editor_property('two_sided',True)", "set_editor_property('two_sided',False)")
subset=[n for n in ast.parse(txt).body if isinstance(n,ast.FunctionDef) and n.name in ('imported','material')]
exec(compile(ast.Module(body=subset,type_ignores=[]),str(entry_file),'exec'),globals())
ui=u.FbxImportUI()
ui.import_mesh=True
ui.import_as_skeletal=False
ui.import_materials=False
ui.import_textures=False
ui.import_animations=False
ui.automated_import_should_detect_type=False
ui.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
settings=ui.static_mesh_import_data
settings.combine_meshes=True
settings.auto_generate_collision=False
settings.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
settings.generate_lightmap_u_vs=False
records={}
inputs=json.loads((work/'reimport-inputs.json').read_bytes())
for kind in ('SwiftCrescent','HeavyCleaver','FoldedArc'):
    entry=json.loads((replay/(kind+'.json')).read_bytes())
    entry['fbx']=inputs[kind]['mesh']
    entry['textures']={k:inputs[kind][k] for k in entry['textures']}
    for file in [entry['fbx'],*entry['textures'].values()]:
        if not Path(file).is_file():raise FileNotFoundError(file)
    saved=[]
    surface=material(entry)
    mesh=imported(entry['fbx'],entry['object'],DEST,ui)
    for i in range(len(mesh.static_materials)):mesh.set_material(i,surface)
    ns=mesh.get_editor_property('nanite_settings');ns.enabled=True;mesh.set_editor_property('nanite_settings',ns)
    if not u.TacticalHatchetImportLibrary.finalize_mesh(mesh):raise RuntimeError('Tangent finalization failed: '+kind)
    u.EditorAssetLibrary.set_metadata_tag(mesh,'ModelRevision',entry['model_revision'])
    save(mesh)
    records[kind]=dict(packages=saved,texture_inputs=entry['textures'],mesh_input=entry['fbx'])
(work/'r2-saved.json').write_text(json.dumps(records,indent=2))
u.log('EARLY_HATCHET_R2_SAVED 15')
