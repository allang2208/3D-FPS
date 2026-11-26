"""Read saved assembly meshes in UE; check materials, bounds, hands and cook coverage."""
import json, math
from pathlib import Path
import unreal as u

P = Path(u.Paths.project_dir()).resolve()
ROOT = P/'SourceAssets/GunAssemblyCompletion20261015'
recipes = json.loads((P/'Content/ColdSteelData/gun-assembly.json').read_text(encoding='utf-8-sig'))['recipes']
ini = (P/'Config/DefaultGame.ini').read_text(encoding='utf-8-sig')
issues = []; rows = []
for recipe in recipes:
    entries = [('body', recipe['body_mesh'], None)] + [(p['id'], p['mesh'], p['extent']) for p in recipe['parts']]
    row = {'recipe': recipe['id'], 'meshes': []}
    for part, path, expected_extent in entries:
        mesh = u.load_asset(path)
        if not isinstance(mesh, u.StaticMesh):
            issues.append(path+': not a static mesh'); continue
        bounds = mesh.get_bounds()
        extent = [bounds.box_extent.x, bounds.box_extent.y, bounds.box_extent.z]
        origin = [bounds.origin.x, bounds.origin.y, bounds.origin.z]
        if max(abs(x) for x in origin) > .1: issues.append(path+': non-centered exported mesh')
        if expected_extent and max(abs(a-b) for a,b in zip(expected_extent, extent)) > .15:
            issues.append(path+': picking extent differs from saved mesh bounds')
        materials = mesh.get_editor_property('static_materials')
        if not materials or any(s.material_interface is None for s in materials):
            issues.append(path+': unassigned material')
        dynamic, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
            mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(),
            u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL))
        triangles = dynamic.get_triangle_count()
        if triangles <= 0: issues.append(path+': empty source geometry')
        row['meshes'].append({'part': part, 'path': path, 'extent_cm': extent, 'origin_cm': origin,
                              'triangles': triangles,
                              'materials': [s.material_interface.get_path_name() if s.material_interface else None for s in materials]})
    rows.append(row)
deps = {
    'hands': '/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7',
    'ghost': '/Game/Building/GunWorkbench20260927/Assembly/M_AssemblyGhost',
    'contact_sound': '/Game/Weapons/M4HK416Audio/S_HK416_MagSeat'}
for role, path in deps.items():
    if u.load_asset(path) is None: issues.append('Missing shared '+role)
hands = u.load_asset(deps['hands'])
modifier = u.SkeletonModifier(); modifier.set_skeletal_mesh(hands)
bones = {str(n) for n in modifier.get_all_bone_names()}
grip = json.loads((P/'Content/ColdSteelData/forge-grip.json').read_text(encoding='utf-8-sig'))
for side in ('l', 'r'):
    for prefix in ('clavicle_', 'upperarm_', 'lowerarm_', 'hand_'):
        if prefix+side not in bones: issues.append('Missing hand chain '+prefix+side)
    if len(grip['hands'][side]['p']) != 3 or len(grip['hands'][side]['q']) != 4: issues.append('Invalid shared grip '+side)
for bone in grip['finger_rotations']:
    if bone not in bones: issues.append('Missing grip bone '+bone)
for directory in ('GunWorkbench20260927', 'GunAssemblyCatalog20260928', 'GunAssemblyCompletion20261015'):
    if f'+DirectoriesToAlwaysCook=(Path="/Game/Building/{directory}")' not in ini:
        issues.append('Missing cook directory '+directory)
result = {'recipe_count': len(rows), 'mesh_count': sum(len(r['meshes']) for r in rows),
          'issues': issues, 'rows': rows, 'shared_dependencies': deps, 'interactive_gameplay_tested': False}
(ROOT/'asset-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('ASSEMBLY_ASSET_CHECK', json.dumps({'recipes': len(rows), 'issues': issues}))
if issues: raise RuntimeError('Assembly asset checks failed')
