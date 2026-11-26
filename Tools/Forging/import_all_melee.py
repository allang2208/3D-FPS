"""Save three one-handed blanks, then install their profile and missing recipes."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
SRC = ROOT / 'SourceAssets/ForgeAllMelee20261024'
DEST = '/Game/Props/ForgeInteraction20260927/SingleHanded20261024'
E = u.EditorAssetLibrary
if any(p.get_path_name().startswith(DEST + '/') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Unsaved one-handed blank packages; preserve current editor work')
steel = u.load_asset('/Game/Props/ForgeInteraction20260927/M_ForgeHotSteel')
guide = u.load_asset('/Game/Props/ForgeInteraction20260927/HammerRefine20261024/SM_ForgeHammerGuide')
if steel is None or guide is None:
    raise RuntimeError('The existing hot steel or readable forge guide is unavailable')
saved = []
for row in json.loads((SRC / 'authored.json').read_text(encoding='utf-8'))['assets']:
    target = row['mesh']
    mesh = u.load_asset(target) if E.does_asset_exist(target) else None
    if mesh is None:
        options = u.FbxImportUI()
        options.automated_import_should_detect_type = False
        options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
        options.import_mesh = True; options.import_as_skeletal = False
        options.import_materials = False; options.import_textures = False
        data = options.static_mesh_import_data
        data.combine_meshes = True; data.auto_generate_collision = False
        data.generate_lightmap_u_vs = False
        data.convert_scene = True; data.convert_scene_unit = True
        data.transform_vertex_to_absolute = True
        data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        data.vertex_color_import_option = u.VertexColorImportOption.REPLACE
        task = u.AssetImportTask()
        task.filename = row['file']; task.destination_path = DEST
        task.destination_name = target.rsplit('/', 1)[-1]
        task.automated = True; task.replace_existing = False; task.save = False
        task.options = options; task.factory = u.FbxFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh = u.load_asset(target)
    if mesh is None:
        raise RuntimeError('Import failed: ' + target)
    mesh.modify(); mesh.set_material(0, steel)
    if not E.save_loaded_asset(mesh, False):
        raise RuntimeError('Save failed: ' + target)
    saved.append(mesh.get_path_name())

# Re-read the shared configuration after imports; preserve unrelated recipes,
# existing costs and the preceding hammer refinement.
blank_path = ROOT / 'Content/ColdSteelData/forge-blanks.json'
recipe_path = ROOT / 'Content/ColdSteelData/forging-recipes.json'
blank_raw = blank_path.read_text(encoding='utf-8-sig')
recipe_raw = recipe_path.read_text(encoding='utf-8-sig')
blanks, recipes = json.loads(blank_raw), json.loads(recipe_raw)
plan = json.loads((SRC / 'recipe_plan.json').read_text(encoding='utf-8'))
blanks['profiles']['single_handed'] = json.loads((SRC / 'single_handed_profile.json').read_text(encoding='utf-8'))
by_id = {r['id']: r for r in recipes['recipes']}
by_output = {r['output']: r for r in recipes['recipes']}
added = []
for recipe in plan['additions']:
    if recipe['id'] in by_id:
        if by_id[recipe['id']] != recipe:
            raise RuntimeError('Recipe changed during authoring: ' + recipe['id'])
        continue
    if recipe['output'] in by_output:
        raise RuntimeError('A different recipe already crafts ' + recipe['output'])
    recipes['recipes'].append(recipe); added.append(recipe['id'])
recipes['_comment'] = '当前近战武器按 blank 选择双手剑、长刀、战锤或单手刀剑的三阶段工胚；敲击面、提示圈与淬火接触共用对应工胚数据。mold 显示所选成品，品质沿用统一锻造结算。'
if blank_path.read_text(encoding='utf-8-sig') != blank_raw or recipe_path.read_text(encoding='utf-8-sig') != recipe_raw:
    raise RuntimeError('Forge configuration changed during installation; assets saved, configuration preserved')
for name, raw in [('forge-blanks.before.json', blank_raw), ('forging-recipes.before.json', recipe_raw)]:
    if not (SRC / name).exists(): (SRC / name).write_text(raw, encoding='utf-8')
blank_path.write_text(json.dumps(blanks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
recipe_path.write_text(json.dumps(recipes, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
receipt = {'saved': saved, 'profile_installed': 'single_handed', 'recipes_added': added,
           'coverage': plan['coverage'], 'rendered': False, 'runtime_tested': False}
(SRC / 'import_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
u.log('ALL_MELEE_FORGE_SAVED assets=%d recipes_added=%d total=%d' % (len(saved), len(added), len(plan['coverage'])))
