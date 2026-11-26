"""Import new closed scan packages, then change only the two quarry mesh references."""
import json
import shutil
from pathlib import Path
import sys
import unreal as u

tool_dir = str(Path(__file__).resolve().parent)
if tool_dir not in sys.path:
    sys.path.insert(0, tool_dir)
from quarry_spoil_surface import apply_weathered_finish

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'SourceAssets/HillsLandscapeRepair20261117/SolidScansR9'
DEST = '/Game/WorldGeneration/TemperateHills/WhiteCliffs'
E, L, A = u.EditorAssetLibrary, u.MaterialEditingLibrary, u.AssetToolsHelpers.get_asset_tools()
CUT_PATH = DEST + '/Materials/M_LimestoneCut'


def cut_material():
    cut_path = CUT_PATH
    if E.does_asset_exist(cut_path):
        cut=u.load_asset(cut_path)
        if not isinstance(cut,u.Material):
            raise RuntimeError('Cannot load cut material '+cut_path)
    else:
        cut=A.create_asset('M_LimestoneCut',DEST+'/Materials',u.Material,u.MaterialFactoryNew())
        cut.set_editor_property('used_with_instanced_static_meshes',True)
        def node(cls):return L.create_material_expression(cut,cls)
        def connect(a,output,b,pin=''):
            if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Cut material pin '+pin)
        uv=node(u.MaterialExpressionTextureCoordinate);uv.set_editor_property('u_tiling',3.);uv.set_editor_property('v_tiling',3.)
        base=node(u.MaterialExpressionTextureSample)
        base.texture=u.load_asset('/Game/UnrealNormandy/Textures/T_StoneSurface_03A_BaseColor')
        base.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR;connect(uv,'',base,'UVs')
        mono=node(u.MaterialExpressionDesaturation);fraction=node(u.MaterialExpressionConstant);fraction.r=1.
        connect(base,'RGB',mono);connect(fraction,'',mono,'Fraction')
        power=node(u.MaterialExpressionPower);power.set_editor_property('const_exponent',.65);connect(mono,'',power,'Base')
        L.connect_material_property(power,'',u.MaterialProperty.MP_BASE_COLOR)
        normal=node(u.MaterialExpressionTextureSample)
        normal.texture=u.load_asset('/Game/UnrealNormandy/Textures/T_StoneSurface_03A_Normal')
        normal.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL;connect(uv,'',normal,'UVs')
        flat=node(u.MaterialExpressionConstant3Vector);flat.constant=u.LinearColor(0.,0.,1.,1.)
        blend=node(u.MaterialExpressionLinearInterpolate);blend.set_editor_property('const_alpha',.45)
        connect(flat,'',blend,'A');connect(normal,'RGB',blend,'B');L.connect_material_property(blend,'',u.MaterialProperty.MP_NORMAL)
        rough=node(u.MaterialExpressionConstant);rough.r=.85;L.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
        apply_weathered_finish(cut)
        errors = L.recompile_material(cut)
        if errors or not E.save_loaded_asset(cut, False):
            raise RuntimeError(f"Cut material save failed: {errors}")
    return cut


def mesh_record(mesh, row, mat, cut):
    if not isinstance(mesh, u.StaticMesh):
        raise RuntimeError('Expected a static mesh at ' + row['name'])
    box = mesh.get_bounding_box()
    size = [box.max.x - box.min.x, box.max.y - box.min.y, box.max.z - box.min.z]
    slots = list(mesh.static_materials)
    if (len(slots) != 2 or sum(str(s.material_slot_name) == 'LimestoneCut' for s in slots) != 1
            or any(s.material_interface != (cut if str(s.material_slot_name) == 'LimestoneCut' else mat)
                   for s in slots)):
        raise RuntimeError('Unexpected limestone material binding on ' + row['name'])
    if any(abs(a - b) > 1.0 for a, b in zip(size, row['size_cm'])):
        raise RuntimeError('Unexpected R9 dimensions on ' + row['name'] + ': ' + str(size))
    collision = mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')
    if not mesh.get_editor_property('nanite_settings').enabled or collision != u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE:
        raise RuntimeError('Unexpected R9 Nanite or collision settings on ' + row['name'])
    return dict(path=mesh.get_path_name().split('.')[0], size_cm=size,
                materials=[s.material_interface.get_path_name() for s in slots])


def ensure_solid_scan(label, mat):
    name = 'SM_White' + label + '_SolidR9'
    records = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
    row = next(row for row in records if row['name'] == name)
    path = DEST + '/Meshes/' + name
    if not isinstance(mat, u.Material):
        raise RuntimeError('Missing base material for ' + name)
    if E.does_asset_exist(path):
        mesh = u.load_asset(path)
        cut = u.load_asset(CUT_PATH)
        if not isinstance(cut, u.Material):
            raise RuntimeError('Missing cut material for ' + name)
        return mesh, dict(mesh_record(mesh, row, mat, cut), saved=False)

    source = OUT / (name + '.fbx')
    if not source.is_file():
        raise FileNotFoundError(source)
    cut = cut_material()
    if mat.get_editor_property('two_sided'):
        mat.modify()
        mat.set_editor_property('two_sided', False)
        if L.recompile_material(mat) or not E.save_loaded_asset(mat, False):
            raise RuntimeError('Could not save solid-scan base material ' + mat.get_path_name())
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=DEST+'/Meshes'
    task.destination_name=row['name'];task.automated=True;task.replace_existing=False;task.save=False
    opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False
    opts.import_as_skeletal=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opts.static_mesh_import_data.combine_meshes=True;opts.static_mesh_import_data.auto_generate_collision=False
    opts.static_mesh_import_data.generate_lightmap_u_vs=False
    opts.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task.options=opts;A.import_asset_tasks([task]);mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Import failed '+path)
    for i,slot in enumerate(mesh.static_materials):
        mesh.set_material(i,cut if str(slot.material_slot_name)=='LimestoneCut' else mat)
    settings=mesh.get_editor_property('nanite_settings');settings.enabled=True
    settings.fallback_percent_triangles=.5;settings.fallback_relative_error=.1
    mesh.set_editor_property('nanite_settings',settings)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    record = mesh_record(mesh, row, mat, cut)
    if not E.save_loaded_asset(mesh, False):
        raise RuntimeError('Could not save ' + path)
    return mesh, dict(record, saved=True)


def merge_cliff_slots(refs, meshes):
    updated = list(refs)
    for index, mesh in enumerate(meshes):
        if index == len(updated):
            updated.append(mesh)
            continue
        current = updated[index]
        if current and current != mesh:
            legacy = mesh.get_path_name().split('.')[0].removesuffix('_SolidR9')
            if current.get_path_name().split('.')[0] not in (legacy, legacy + '_Solid'):
                raise RuntimeError('Another quarry revision occupies slot ' + str(index) + ': ' + current.get_path_name())
        updated[index] = mesh
    return updated


def main():
    data = u.load_asset('/Game/WorldGeneration/TemperateHills/DA_TemperateHillsStreaming')
    meshes = []
    report = dict(meshes=[], cut_material=CUT_PATH)
    for label in ('CliffA', 'CliffB'):
        mat = u.load_asset(DEST + '/Materials/M_' + label)
        mesh, record = ensure_solid_scan(label, mat)
        meshes.append(mesh)
        report['meshes'].append(record)
    refs = list(data.get_editor_property('white_cliff_meshes'))
    updated = merge_cliff_slots(refs, meshes)
    report['data_asset_saved'] = refs != updated
    if report['data_asset_saved']:
        content = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir()))
        source = content / 'WorldGeneration/TemperateHills/DA_TemperateHillsStreaming.uasset'
        backup = OUT / 'DA_TemperateHillsStreaming-before-solid.uasset'
        if not backup.exists():
            shutil.copy2(source, backup)
        data.modify()
        data.set_editor_property('white_cliff_meshes', updated)
        if not E.save_loaded_asset(data, False):
            raise RuntimeError('Could not save cliff references')
    receipt = OUT / 'saved.json'
    if receipt.is_file() and not (OUT / 'saved-before-resume.json').exists():
        shutil.copy2(receipt, OUT / 'saved-before-resume.json')
    receipt.write_text(json.dumps(report, indent=2), encoding='utf-8')
    u.log('HILLS_CLOSED_QUARRY_SCANS_SAVED')


if __name__ == '__main__':
    main()
