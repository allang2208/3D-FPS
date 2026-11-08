import json, pathlib, unreal

ROOT = pathlib.Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/ConversationCombatReview20261108/assets-readback.json'
rows = []

def check(name, passed, **detail):
    rows.append(dict(case=name, passed=bool(passed), **detail))

def load(path):
    asset = unreal.load_asset(path)
    check('saved asset loads', bool(asset), path=path)
    return asset

def find_conical(value):
    if isinstance(value, dict):
        if 'conical_seat' in value and isinstance(value['conical_seat'], dict):
            yield value['conical_seat']
        for child in value.values():
            yield from find_conical(child)
    elif isinstance(value, list):
        for child in value:
            yield from find_conical(child)

for catalog in ['warhammer-modules.json', 'runebound-warhammer-modules.json', 'thunder-god-hammer-modules.json']:
    data = json.loads((ROOT / 'Content/ColdSteelData' / catalog).read_text(encoding='utf-8-sig'))
    options = list(find_conical(data))
    check('host conical catalog entry', len(options) == 1, catalog=catalog)
    for entry in options:
        mesh = load(entry['mesh'])
        if mesh:
            check('conical mesh has geometry', mesh.get_num_lods() > 0, path=mesh.get_path_name())
        for path in entry.get('materials', {}).values():
            material = load(path)
            if material and isinstance(material, unreal.Material):
                normal = unreal.MaterialEditingLibrary.get_material_property_input_node(material, unreal.MaterialProperty.MP_NORMAL)
                # NullRHI has no compiled shader texture list. Read the saved
                # normal input expression directly instead of a render resource.
                textures = unreal.MaterialEditingLibrary.get_used_textures(material)
                if normal and isinstance(normal, unreal.MaterialExpressionTextureSample):
                    texture = normal.get_editor_property('texture')
                    if texture and texture not in textures:
                        textures.append(texture)
                normals = [t for t in textures if t.get_editor_property('compression_settings') == unreal.TextureCompressionSettings.TC_NORMALMAP]
                check('saved normal map connected', bool(normal) and bool(normals), material=path,
                      normals=[dict(path=t.get_path_name(), width=t.blueprint_get_size_x(), height=t.blueprint_get_size_y()) for t in normals])

paths = [
    '/Game/Audio/TwoHandInspect/S_TwoHandInspect_Air_01',
    '/Game/Audio/TwoHandInspect/S_TwoHandInspect_Air_02',
    '/Game/Weapons/ThunderGodHammer20261028/RecallAudioV1/S_GuanLei_RecallCatch',
    '/Game/Weapons/TacticalHatchet20261101/Animations/A_TacticalHatchet_PairAttack3KH',
    '/Game/Weapons/SteelWarhammer20261014/QuickCombatLeftWristV7/A_Warhammer_QuickCombat',
    '/Game/Skills/LightningHaste20261019/NS_LightningHasteArc',
    '/Game/Weapons/FrostCrystalSword20260915/StarMarrowCharge20261103/NS_StarMarrowDenseBladeFire',
    '/Game/Skills/FlameArmor20261108/LocalFollowV10/NS_FlameArmorWeapon',
    '/Game/Skills/FlameArmor20261108/LocalFollowV10/NS_FlameArmorHammer',
    '/Game/Skills/FlameArmor20261108/SwordRestoreV11/NS_FlameArmorSword',
    '/Game/Skills/FlameArmor20261107/CampfireV6/NS_FlameArmorArrow',
]
try:
    for path in paths:
        asset = load(path)
        if isinstance(asset, unreal.NiagaraSystem):
            rows[-1]['require_current_frame_data'] = asset.get_editor_property('require_current_frame_data')
        if isinstance(asset, unreal.SoundWave):
            check('audio contains duration', asset.get_editor_property('duration') > 0, path=path, duration=asset.get_editor_property('duration'))
finally:
    OUT.write_text(json.dumps(dict(passed=all(r['passed'] for r in rows), saved_asset_readback=True,
                                   rendered=False, cases=rows), ensure_ascii=False, indent=2), encoding='utf-8')
unreal.log('CONVERSATION_ASSET_READBACK ' + str(OUT))
