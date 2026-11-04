"""Keep the original crystal PBR; expose red color and polished crystal modes."""
from pathlib import Path
import json
import shutil
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
REV = 'MagicCrystalSword20261101V1'
PATH = '/Game/Weapons/FrostCrystalSword20260915/GuardsSmooth20260915/M_FrostCrystalSword_SeamlessBronze'
ICON_ROOT = '/Game/ColdSteelData/AttachmentIcons20260913/'
ICON_IDS = ['ue_frost_crystal_sword_blade_material_red_magic_crystal',
            'ue_frost_crystal_sword_blade_material_high_energy_magic_crystal']
targets = [PATH] + [ICON_ROOT + name for name in ICON_IDS]
if u.EditorLevelLibrary.get_pie_worlds(False):
    raise RuntimeError('PIE is running; preserve the current session')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_path_name() in targets:
        raise RuntimeError('Unsaved target: ' + package.get_path_name())

material = u.load_asset(PATH)
if not material: raise RuntimeError('Missing original crystal material')
disk = ROOT / 'Content' / (PATH.removeprefix('/Game/') + '.uasset')
backup = P / 'BeforeAssets' / disk.relative_to(ROOT / 'Content')
backup.parent.mkdir(parents=True, exist_ok=True)
if not backup.exists(): shutil.copy2(disk, backup)

# These nodes precede the existing wetness layer. Rune overlays remain separate.
codes = {
    'BASE_COLOR': '''if(Mode>7.5 && Mode<8.5)
{
    // Preserve texture luminance/detail and neutral or bronze inlays.
    float peak=max(Base.g,Base.b);
    float crystal=smoothstep(.035,.20,(peak-Base.r)/max(peak,.001));
    float3 ruby=float3(peak,Base.r*.42,Base.r*.55);
    return lerp(Base,ruby,crystal);
}
return Base;''',
    'ROUGHNESS': '''if(Mode>8.5 && Mode<9.5)return min(Base,clamp(.085+Base*.12,.09,.18));
return Base;''',
    'NORMAL': '''if(Mode>8.5 && Mode<9.5)return normalize(float3(Base.xy*.45,Base.z));
return Base;''',
    'METALLIC': 'return Base;',
    'ANISOTROPY': 'return Base;',
    'TANGENT': 'return Base;',
}
found = set()
for node in L.get_material_expressions(material):
    desc = str(node.get_editor_property('desc'))
    if isinstance(node, u.MaterialExpressionCustom) and desc.startswith('SharedTwoHandFinish20261101V1 '):
        field = desc.removeprefix('SharedTwoHandFinish20261101V1 ')
        if field in codes:
            node.set_editor_property('code', '// ' + REV + '\n' + codes[field])
            found.add(field)
if found != set(codes): raise RuntimeError('Missing original finish inputs: ' + str(set(codes) - found))
errors = L.recompile_material(material)
if errors: raise RuntimeError('Crystal shader compile failed: ' + str(errors))
E.set_metadata_tag(material, 'MagicCrystalSwordRevision', REV)
if not E.save_loaded_asset(material, False): raise RuntimeError('Crystal material save failed')

saved_icons = []
for name in ICON_IDS:
    target = ICON_ROOT + name
    icon = u.load_asset(target) if E.does_asset_exist(target) else E.duplicate_asset(
        ICON_ROOT + 'ue_rune_sword_blade_material_frost_crystal', target)
    if not icon or not E.save_loaded_asset(icon, False): raise RuntimeError('Icon save failed: ' + name)
    saved_icons.append(target)
(P / 'material-receipt.json').write_text(json.dumps({
    'revision': REV, 'saved_material': PATH, 'saved_icons': saved_icons,
    'modes': {'factory': 0, 'red_magic_crystal': 8, 'high_energy_magic_crystal': 9},
    'red_changes': ['base_color'], 'polished_changes': ['roughness', 'normal'],
    'shader_compile_errors': list(errors), 'gameplay_tested': False,
}, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print('MAGIC_CRYSTAL_MATERIAL_SAVED', PATH)
