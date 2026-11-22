from pathlib import Path
import gc, hashlib, json, sys
import unreal as u

batch = Path(__file__).resolve().parent
host = batch / 'Host'
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve() != host:
    raise RuntimeError('Launch in the independent production project')
plan = json.loads((batch / 'plan.json').read_text())
project = Path(plan['project'])
source = project / 'SourceAssets'
result = {}
def record(name, value):
    result[name] = value
    (batch / 'authored.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    return hashlib.file_digest(p.open('rb'), 'sha256').hexdigest() if hasattr(hashlib,'file_digest') else hashlib.sha256(p.read_bytes()).hexdigest()

def make_stocks():
    root = source / 'SkeletonSniperStock20261031'
    previous = read(root / 'Review20261031/read_receipt.json')
    stem = '/Game/Weapons/SkeletonSniperStock20261031'
    sub = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    flag = 'Interchange.FeatureFlags.Import.FBX'
    prior = u.SystemLibrary.get_console_variable_int_value(flag)
    u.SystemLibrary.execute_console_command(None, flag + ' 0')
    try:
        for family in ('SVCH', 'SVD'):
            svd = family == 'SVD'
            asset = previous[family]['stock']
            mesh_name = asset['path'].rsplit('/',1)[1]
            fbx = root / 'Exports' / (mesh_name + '.fbx')
            options = u.FbxImportUI()
            options.automated_import_should_detect_type = False
            options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
            options.import_mesh = True
            options.import_as_skeletal = False
            options.import_materials = False
            options.import_textures = False
            options.import_animations = False
            imp = options.static_mesh_import_data
            imp.combine_meshes = True
            imp.auto_generate_collision = False
            imp.generate_lightmap_u_vs = False
            imp.normal_import_method = (u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS if svd else u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)
            task = u.AssetImportTask()
            task.filename = str(fbx)
            task.destination_path = stem + '/Meshes'
            task.destination_name = mesh_name
            task.factory = u.FbxFactory()
            task.options = options
            task.automated = True
            task.replace_existing = False
            task.save = False
            u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            mesh = u.load_asset(asset['path'])
            if not mesh:
                raise RuntimeError('FBX import failed: ' + str(fbx))
            slots = {m['slot']:m['asset'] for m in asset['materials']}
            if set(slots) != {str(slot.material_slot_name) for slot in mesh.static_materials}:
                raise RuntimeError('FBX material IDs differ from archived stock')
            for i, slot in enumerate(mesh.static_materials):
                material = u.load_asset(slots[str(slot.material_slot_name)])
                if not material:
                    raise RuntimeError('Could not load '+slots[str(slot.material_slot_name)])
                mesh.set_material(i, material)
            bs = sub.get_lod_build_settings(mesh, 0)
            bs.recompute_normals = False
            bs.recompute_tangents = svd
            bs.use_mikk_t_space = not svd
            bs.use_full_precision_u_vs = True
            bs.use_high_precision_tangent_basis = True
            u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
            sub.set_lod_build_settings(mesh, 0, bs)
            reductions = u.StaticMeshReductionOptions()
            reductions.auto_compute_lod_screen_size = False
            reductions.reduction_settings = [u.StaticMeshReductionSettings(percent_triangles=p, screen_size=s) for p,s in [(1.,1.),(.5,.18),(.2,.075)]]
            sub.set_lods(mesh, reductions)
            count = sub.get_lod_count(mesh)
            if count != asset['lod_count']:
                raise RuntimeError('Failed to build all published stock LODs')
            u.EditorAssetLibrary.set_metadata_tag(mesh, 'Source', str(root / ('SkeletonSniperStock_'+family+'_Editable.blend')))
            if svd:
                for i in range(count):
                    bs = sub.get_lod_build_settings(mesh, i)
                    bs.recompute_tangents = True
                    bs.use_mikk_t_space = False
                    bs.use_full_precision_u_vs = True
                    bs.use_high_precision_tangent_basis = True
                    if i == 0: bs.recompute_normals = False
                    sub.set_lod_build_settings(mesh, i, bs)
                if not u.M24ChassisAssetTools.bake_stock_tangent_basis(mesh):
                    raise RuntimeError('Final SVD basis bake failed')
            if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):
                raise RuntimeError('Could not save '+asset['path'])
            record(family,dict(package=asset['path'],source=fbx.relative_to(project).as_posix(),fbx_sha256=sha(fbx),materials=slots,lods=count,bake_stock_tangent_basis=svd,historical_sha256=asset['sha256'],commit='e85f03b82'))
            print('RESTORE_SAVED',family,flush=True)
    finally:
        u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))

def make_belt():
    sys.path.insert(0,str(project/'Tools/CombatBeltsIntegration'))
    import save_assets as assets
    root = source / 'ArcaneConduitBelt20261025/KeeperFixR2'
    scene = root / 'arcane'
    historical = read(root / 'published.json')
    materials = read(scene / 'materials.json')
    delivery = read(scene / 'delivery.json')
    rows = next(group['lods'] for group in delivery['records'] if group['body']=='Jason')
    rows = [dict(row,file=str(scene/'Geometry'/Path(row['file']).name)) for row in rows]
    hashes = [assets.sha(row['file']) for row in rows]
    if hashes != historical['assets']['pickup']['lod_source_hashes'] or hashes != historical['old_pickup_path_compatibility']['lod_source_hashes']:
        raise RuntimeError('Source geometry does not match published R2 pickup')
    assets.KEY = assets.BELTS['arcane']['key']
    assets.slots = [m['name'] for m in materials]
    assets.mats = [assets.load(p) for p in historical['assets']['materials']]
    data = assets.read(rows[0]['file'])
    offset = [-(min(p[i] for p in data['positions']) + max(p[i] for p in data['positions']))*.5 for i in range(3)]
    del data
    for version,receipt in [('KeeperFixR2',historical['assets']['pickup']),('IntegrationR1',historical['old_pickup_path_compatibility'])]:
        pkg = receipt['asset'].split('.')[0]
        assets.DEST = pkg.split('/Pickups/')[0]
        saved = assets.static(rows,pkg,offset)
        record(version,dict(package=pkg,geometry=[Path(row['file']).relative_to(project).as_posix() for row in rows],materials=historical['assets']['materials'],lods=saved['lod_count'],source_hashes=hashes,commit='10dcaa194'))
        gc.collect()
        u.SystemLibrary.collect_garbage()
        print('RESTORE_SAVED',version,flush=True)

make_stocks()
make_belt()
print('RELEASE_RESTORE_AUTHORED',len(result),flush=True)
