"""Clone the current StarMarrow charge effect and recolor emission only."""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'Tools/Fluids'))
from author_flame_armor_v2 import API, LIB, ref, setdata
from build_fireball_assets import emitters

DONOR = '/Game/Weapons/FrostCrystalSword20260915/StarMarrowCharge20261103/NS_StarMarrowDenseBladeFire'
DEST = '/Game/Skills/FlameArmor20261108/SwordChargeV8'
SYSTEM = DEST+'/NS_FlameArmorSword'
SAVED, COPIES, MATERIAL_MAP = [], {}, {}


def save(asset):
    if not u.EditorAssetLibrary.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save '+asset.get_path_name())
    SAVED.append(asset.get_path_name())


def owned(source, dest):
    if dest in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Preserve dirty target '+dest)
    asset = u.load_asset(dest) if u.EditorAssetLibrary.does_asset_exist(dest) else u.EditorAssetLibrary.duplicate_asset(source, dest)
    if asset is None:
        raise RuntimeError('Cannot copy '+source)
    return asset


def warm_material(source):
    path = source.get_path_name()
    if path in COPIES:
        return COPIES[path]
    target = owned(path, DEST+'/Materials/'+source.get_name()+'_Warm')
    COPIES[path] = target
    if isinstance(target, u.MaterialInstanceConstant):
        parent = warm_material(source.get_editor_property('parent'))
        LIB.set_material_instance_parent(target, parent)
        LIB.update_material_instance(target)
    elif isinstance(target, u.Material):
        prop = u.MaterialProperty.MP_EMISSIVE_COLOR
        nodes = list(LIB.get_material_expressions(target))
        existing_blue = next((n for n in nodes if n.get_editor_property('desc') == 'StarMarrow blue flame'), None)
        remap = existing_blue or next((n for n in nodes if n.get_editor_property('desc') == 'FlameArmor sword warm emission V8'), None)
        had_blue = existing_blue is not None
        if remap is None:
            emission = LIB.get_material_property_input_node(target, prop)
            output = str(LIB.get_material_property_input_node_output_name(target, prop))
            if emission is None:
                raise RuntimeError('Missing source emission '+path)
            remap = LIB.create_material_expression(target, u.MaterialExpressionCustom)
            pin = u.CustomInput()
            pin.set_editor_property('input_name', 'Fire')
            remap.set_editor_property('inputs', [pin])
            remap.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
            if not LIB.connect_material_expressions(emission, output, remap, 'Fire'):
                raise RuntimeError('Cannot connect warm emission '+path)
        # Replace the donor's final blue remap, preserving the texture, noise,
        # density/opacity, particle tint and its single exposure correction.
        # The edge-bed material has no blue node; its blue particle tint is
        # recolored after emission without changing any Niagara assignments.
        gain = '.85' if had_blue or u.EditorAssetLibrary.get_metadata_tag(target, 'FlameArmor.WarmGain') == '.85' else '1.'
        remap.set_editor_property('desc', 'FlameArmor sword warm emission V8')
        remap.set_editor_property('code',
            'float heat=max(Fire.r,max(Fire.g,Fire.b)); '
            'float core=saturate(min(Fire.g,Fire.b)/max(heat,0.001)); '
            'return heat*lerp(float3(1.0,0.17,0.012),float3(1.0,0.67,0.19),core)*'+gain+';')
        if not LIB.connect_material_property(remap, '', prop):
            raise RuntimeError('Cannot bind warm emission '+path)
        u.EditorAssetLibrary.set_metadata_tag(target, 'FlameArmor.WarmGain', gain)
        errors = LIB.recompile_material(target)
        if errors:
            raise RuntimeError(str(errors))
    else:
        raise RuntimeError('Unsupported source material '+path)
    u.EditorAssetLibrary.set_metadata_tag(target, 'FlameArmor.SourceMaterial', path)
    save(target)
    MATERIAL_MAP[path] = target.get_path_name()
    return target


def run():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('End PIE before copying and saving sword flame assets')
    source = u.load_asset(DONOR)
    if source is None:
        raise RuntimeError('Missing active StarMarrow charge system')
    system = owned(DONOR, SYSTEM)
    layers = []
    for name in emitters(source):
        data = json.loads(API.call_method('GetRendererData', (ref(source, name, renderer=0),)).get_editor_property('property_values'))
        path = data['Material']
        if isinstance(path, dict):
            path = path['refPath']
        material = u.load_asset(path)
        if material is None:
            raise RuntimeError('Missing renderer material '+str(path))
        warm = warm_material(material)
        setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {'Material': warm.get_path_name()})
        layers.append(name)
    if not u.RainAssetEditor.compile_rain(system, True):
        raise RuntimeError('Sword flame Niagara compilation failed')
    u.EditorAssetLibrary.set_metadata_tag(system, 'FlameArmor.Revision', 'SwordChargeWarmV8-20261108')
    save(system)
    receipt = dict(revision='SwordChargeWarmV8', donor=DONOR,
        donor_revision=u.EditorAssetLibrary.get_metadata_tag(source, 'StarMarrow.Revision'),
        saved_assets=SAVED, material_copies=MATERIAL_MAP, reused_emitters=layers,
        particle_graphs_changed=False, spawn_rates_changed=False, silhouettes_changed=False,
        source_assets_modified=False, color='orange-red edges and golden-orange hot core',
        runtime_tested=False, rendered=False)
    (OUT/'install-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('FLAME_ARMOR_SWORD_SAVED', system.get_path_name(), 'layers', layers)


if __name__ == '__main__':
    # The public production entry follows the current visible sword fire.
    # run() above remains the initial V8 copy operation for a fresh installation.
    sys.path.insert(0, str(OUT.parent/'StarMarrowRestore20261108'))
    import importlib
    import restore_warm_sword
    importlib.reload(restore_warm_sword).run()
    # Active warm swords share the measured-surface copy with other weapons.
    # Rebuild that copy after refreshing its original-structure warm donor.
    sys.path.insert(0, str(OUT.parent/'FlameArmorAllWeapons20261108'))
    import install_all_weapons
    importlib.reload(install_all_weapons).run()
