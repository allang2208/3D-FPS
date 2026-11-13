"""Import packed steel fields and save all eighteen active Zhanmadao surfaces."""
import json
import runpy
import shutil
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
recipe = runpy.run_path(str(P/'materials.py'))
D, REV = recipe['D'], recipe.get('ART_REV', recipe['REV'])
BATCH = recipe.get('BATCH', P)
E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary
catalog = json.loads((ROOT/'Content/ColdSteelData/zhanmadao-modules.json').read_text(encoding='utf-8-sig'))
temporal = json.loads((ROOT/'Content/ColdSteelData/whirlwind-temporal-materials.json').read_text(encoding='utf-8-sig'))
targets = {}
for choice, row in catalog['slots']['blade_1'].items():
    if choice not in recipe['PROFILES']:
        raise RuntimeError('Unassigned blade profile '+choice)
    for path in row['materials'].values():
        if 'M_TangDaoBladeRuneSurface' in path:
            targets[path] = choice
            targets[temporal[path]] = choice
owned = {path.split('.')[0] for path in targets}
if Path(u.Paths.project_dir()).resolve() != ROOT:
    raise RuntimeError('Use the FPSGAME host')
if u.EditorLevelLibrary.get_pie_worlds(False):
    raise RuntimeError('PIE running; preserve session')
if any(p.get_path_name() in owned or p.get_path_name().startswith(D+'/')
       for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved target assets')
receipt = {'revision': REV, 'assets': [], 'profiles': {k: v['family'] for k, v in recipe['PROFILES'].items()},
           'complete': False, 'game_tested': False, 'rune_layout_changed': False}


def record():
    text = json.dumps(receipt, ensure_ascii=False, indent=2)+'\n'
    (P/'material-receipt.json').write_text(text, encoding='utf-8')
    if BATCH != P:
        (BATCH/'material-receipt.json').write_text(text, encoding='utf-8')


def backup(path):
    disk = ROOT/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
    if disk.exists():
        target = BATCH/'BeforeAssets'/disk.relative_to(ROOT/'Content')
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists(): shutil.copy2(disk, target)


def save(asset, profile=None):
    errors = list(L.recompile_material(asset) or []) if isinstance(asset, u.Material) else []
    if errors: raise RuntimeError('Shader compilation '+str(errors))
    if not E.save_loaded_asset(asset, False): raise RuntimeError('Save failed '+asset.get_path_name())
    receipt['assets'].append(dict(asset=asset.get_path_name(), saved=True, profile=profile, compile_errors=errors))
    record()


for family in ['Flow', 'Twist', 'Feather']:
    path = D+'/Textures/T_Damascus_'+family+'_Field'
    backup(path)
    task = u.AssetImportTask()
    task.filename = str(P/'Textures'/('Damascus_'+family+'_Field.png'))
    task.destination_path, task.destination_name = path.rsplit('/', 1)
    task.automated = True; task.replace_existing = True; task.save = False; task.factory = u.TextureFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture = u.load_asset(path)
    if not texture: raise RuntimeError('Texture import failed '+family)
    texture.set_editor_properties(dict(srgb=False, compression_settings=u.TextureCompressionSettings.TC_BC7,
        lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON, max_texture_size=4096, never_stream=False,
        address_x=u.TextureAddress.TA_WRAP, address_y=u.TextureAddress.TA_WRAP,
        mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE))
    E.set_metadata_tag(texture, 'ZhanmadaoDamascusRevision', REV)
    save(texture)

for path, choice in targets.items():
    backup(path)
    material = u.load_asset(path)
    if not material: raise RuntimeError('Missing current blade surface '+path)
    recipe['apply'](material, choice)
    save(material, choice)
    print('DAMASCUS_V2_SAVED', choice, len(receipt['assets']), flush=True)
receipt['complete'] = True; record()
print('DAMASCUS_V2_ASSETS_COMPLETE', len(targets), 'MATERIALS 3 TEXTURES', flush=True)
