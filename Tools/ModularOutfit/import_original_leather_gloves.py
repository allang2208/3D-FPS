"""Save independent glove assets, then publish only ue_original_gloves.

Run through Run-Authoring.ps1 while the project editor is closed. Existing
native meshes supply the complete current bindings and LODs; no rebind occurs.
"""
import shutil
import sys
from pathlib import Path
import unreal as u

sys.path.insert(0, str(Path(__file__).resolve().parent))
from original_leather_gloves import PROJECT as P, ROOT as R, DEST, ITEM, ICON, DESCRIPTION, PARAMETERS, read, write

E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
L = u.MaterialEditingLibrary
CFG = P/'Content/ColdSteelData/modular_outfits.json'
CATALOG = P/'Content/ColdSteelData/items.json'


def load(path):
    asset = u.load_asset(path)
    if not asset: raise RuntimeError('Missing original glove dependency: '+path)
    return asset


def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()], False):
        if not E.save_loaded_asset(asset, False): raise RuntimeError('Cannot save '+asset.get_path_name())


def duplicate(source, name, folder):
    asset = u.load_asset(folder+'/'+name)
    if asset: return asset
    E.make_directory(folder)
    asset = A.duplicate_asset(name, folder, source)
    if not asset: raise RuntimeError('Cannot create '+folder+'/'+name)
    return asset


def leather_material():
    mat = duplicate(load('/Game/Characters/ModularOutfit20260924/Materials/M_FieldGloves_Brown'), 'M_OriginalLeather', DEST+'/Materials')
    mat.modify()
    # Keep the licensed brown scan and UV construction fields; isolate this
    # equipment's adjustments from the black and fingerless glove families.
    code = (P/'SourceAssets/ModularOutfit20260925/FieldGlovesLeatherV1/field_glove_leather.hlsl').read_text(encoding='utf-8')
    code = code.replace('colored=lerp(colored,colored*.72,stitch*.8);', 'colored=lerp(colored,float3(.105,.065,.032),stitch*.32);')
    code = code.replace('Thread.xy*.55', 'Thread.xy*.70')
    code = code.replace('lerp(.42,.63,palm)+leatherRough*.24', 'lerp(.46,.61,palm)+leatherRough*.22')
    code = code.replace('gloveRough=lerp(gloveRough,.48,roll);', 'gloveRough=lerp(gloveRough,.54,roll);')
    custom = [n for n in L.get_material_expressions(mat) if isinstance(n, u.MaterialExpressionCustom)]
    if len(custom) != 1: raise RuntimeError('Unexpected leather parent graph')
    custom[0].set_editor_property('code', code)
    custom[0].set_editor_property('description', 'Original brown leather: V7 fitted glove, palm grain, warm thread and rolled cuff')
    for expr in L.get_material_expressions(mat):
        if isinstance(expr, u.MaterialExpressionScalarParameter):
            key = str(expr.get_editor_property('parameter_name'))
            if key in PARAMETERS: expr.set_editor_property('default_value', PARAMETERS[key])
    errors = L.recompile_material(mat)
    if errors: raise RuntimeError('Original glove material build failed: '+str(errors))
    save(mat)
    (R/'original_leather.hlsl').write_text(code, encoding='utf-8')
    return mat


def pickup(material):
    folder = DEST+'/Pickups'; name = 'SM_OriginalLeatherGloves_Pickup'
    E.make_directory(folder)
    task = u.AssetImportTask(); task.filename = str(R/(name+'.fbx'))
    task.destination_path = folder; task.destination_name = name
    task.automated = True; task.replace_existing = True; task.save = False
    options = u.FbxImportUI()
    options.set_editor_property('import_as_skeletal', False)
    options.set_editor_property('mesh_type_to_import', u.FBXImportType.FBXIT_STATIC_MESH)
    options.set_editor_property('automated_import_should_detect_type', False)
    options.set_editor_property('import_materials', False); options.set_editor_property('import_textures', False)
    options.static_mesh_import_data.set_editor_property('combine_meshes', True)
    options.static_mesh_import_data.set_editor_property('auto_generate_collision', True)
    task.options = options; A.import_asset_tasks([task])
    mesh = load(folder+'/'+name)
    for index in range(len(mesh.get_editor_property('static_materials'))): mesh.set_material(index, material)
    editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    settings = []
    for percent, screen in ((1.,1.),(.5,.18),(.25,.075)):
        setting = u.StaticMeshReductionSettings(); setting.percent_triangles = percent; setting.screen_size = screen; settings.append(setting)
    reduction = u.StaticMeshReductionOptions(); reduction.auto_compute_lod_screen_size = False; reduction.reduction_settings = settings
    editor.set_lods(mesh, reduction)
    save(mesh)
    return mesh


def main():
    if (R.parent/'OriginalLeatherV2/published.json').exists():
        import import_original_tailored_leather
        import_original_tailored_leather.main()
        return
    R.mkdir(parents=True, exist_ok=True)
    if not (R/'artwork.json').exists(): raise RuntimeError('Create the glove artwork before importing')
    initial = read(CFG); initial_item = read(CATALOG)[ITEM]
    before = R/'before-publication.json'
    if not before.exists(): write(before, dict(recipe=initial['items'][ITEM], item=initial_item))
    material = leather_material()
    native = initial['items']['ue_field_gloves_black']['rig_meshes']
    profiles = {}
    for name, path in native.items():
        source = load(path)
        mesh = duplicate(source, 'SK_'+name+'_OriginalLeatherV1', DEST+'/'+name)
        slots = mesh.get_editor_property('materials')
        for slot in slots: slot.set_editor_property('material_interface', material)
        mesh.set_editor_property('materials', slots)
        mesh.set_editor_property('physics_asset', None)
        E.set_metadata_tag(mesh, 'EquipmentDefinition', ITEM)
        E.set_metadata_tag(mesh, 'NativeFittedSource', path)
        save(mesh)
        profiles[name] = mesh.get_path_name()
        write(R/'Saved'/f'{name}.json', dict(mesh=mesh.get_path_name(), native_source=path, material=material.get_path_name(), runtime_tested=False))
        print('ORIGINAL_LEATHER_PROFILE_SAVED', name, flush=True)
    prop = pickup(material)
    recipe = dict(slot=3, part='gloves', material=material.get_path_name(), rig_meshes=profiles, covers=[2], appearance_family='OriginalLeatherV1')
    appearance = dict(ue_icon=ICON, world_mesh=prop.get_path_name(), world_material=material.get_path_name(), desc=DESCRIPTION)
    receipt = dict(item=ITEM, recipe=recipe, appearance=appearance, native_sources=native, parameters=PARAMETERS,
                   profiles=len(profiles), new_animations=0, source_clothes_restored=False, runtime_tested=False)
    write(R/'saved-assets.json', receipt)
    cfg = read(CFG); items = read(CATALOG)
    if cfg['items'][ITEM] != initial['items'][ITEM] or items[ITEM] != initial_item:
        raise RuntimeError('This glove item changed during production; saved assets retained without publishing')
    if cfg['items']['ue_field_gloves_black']['rig_meshes'] != native:
        raise RuntimeError('Native glove sources changed during production; saved assets retained without publishing')
    icon = P/'Content/ColdSteelData'/ICON; icon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(R/'ue_original_gloves.png', icon)
    cfg['items'][ITEM] = recipe; items[ITEM].update(appearance)
    write(CFG, cfg); write(CATALOG, items)
    write(R/'published.json', receipt)
    print('ORIGINAL_LEATHER_PUBLISHED', len(profiles), material.get_path_name(), flush=True)


if __name__ == '__main__': main()
