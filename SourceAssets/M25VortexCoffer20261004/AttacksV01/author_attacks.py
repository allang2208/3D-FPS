"""Save the M25 attack component and authored combat defaults. No PIE or acceptance run."""
from pathlib import Path
import json
import traceback
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
BP_PATH = '/Game/Monsters/VortexCofferM25/BP_VortexCofferM25'
REVISION = 'M25ElectricAttacks20261004V1'
record = dict(revision=REVISION, stage='started', saved=[], runtime_tested=False, rendered=False)

def receipt():
    (ROOT/'asset_receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise RuntimeError('Wrong project')
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
        if editor and editor.get_game_world():
            raise RuntimeError('Stop PIE before saving the monster defaults')
    if not hasattr(u,'M25MagicComponent'):
        raise RuntimeError('New native M25MagicComponent must be loaded from the regular Editor build')
    bp=u.load_asset(BP_PATH)
    if bp is None:
        raise RuntimeError('Existing M25 blueprint is missing')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo=u.get_default_object(bp.generated_class())
    magic=cdo.get_editor_property('magic')
    if magic is None:
        raise RuntimeError('M25 native MagicExecution component missing')
    values=dict(attacks_enabled=True,magic_attack=60.,lightning_multiplier=1.,lance_multiplier=2.5,
        lightning_cooldown=3.,lance_cooldown=20.,lightning_windup=.55,lance_windup=1.6,
        lance_aim_lock_seconds=.25,lightning_range=1400.,lance_range=1800.,
        lance_charge_height=65.,lance_hit_radius=14.,max_lead_distance=300.)
    for key,value in values.items():
        magic.set_editor_property(key,value)
    assets=dict(charge_asset='/Game/Skills/ElectricMagic/NS_ThunderCharge',
        arc_asset='/Game/Skills/Lightning/NS_LightningChain',
        impact_asset='/Game/Skills/ElectricMagic/NS_ElectricImpact',
        lance_tube='/Game/Skills/ElectricMagic/ThunderFluxV3/SM_ThunderFluxTube',
        lance_body='/Game/Skills/ElectricMagic/ThunderFluxV3/M_ThunderFluxBody',
        lance_filaments='/Game/Skills/ElectricMagic/ThunderFluxV3/M_ThunderFluxFilaments',
        release_sound='/Game/Skills/Lightning/S_LightningCast1')
    for key,path in assets.items():
        asset=u.load_asset(path)
        if asset is None:
            raise RuntimeError('Required spell resource not available: '+path)
        magic.set_editor_property(key,asset)
    cdo.set_editor_property('stopping_distance',1050.)
    u.EditorAssetLibrary.set_metadata_tag(bp,'M25.AttackRevision',REVISION)
    if not u.EditorAssetLibrary.save_loaded_asset(bp,False):
        raise RuntimeError('M25 blueprint save failed')
    record.update(stage='assets_saved',saved=[bp.get_path_name()],component=magic.get_path_name(),
        defaults=values,spell_assets=assets,stopping_distance_cm=1050.,
        lightning_base_magic_damage=60.,lance_base_magic_damage=150.,
        cooldown_origin='release',prediction='target_velocity * remaining_locked_windup',
        damage_delivery='server_only_single_point_hit_lightning_damage_type')
    receipt()
    u.log('M25_ELECTRIC_ATTACKS_SAVED')

try:
    main()
except Exception:
    record.update(stage='production_failed',error=traceback.format_exc())
    receipt()
    raise
