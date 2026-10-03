"""Save M10 radial gas growth and the requested lunge/turn defaults. No game run."""
from pathlib import Path
import json,sys,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[2]
DEST='/Game/Monsters/M10Mawcrawler/CombatPaceV10';REV='M10CombatPaceV10_20261003'
BP='/Game/Monsters/M10Mawcrawler/BP_M10Mawcrawler'
sys.path.insert(0,str(PROJECT/'Tools/Skills'))
from build_fireball_assets import API,assignments
from build_fireball_flames import FLOAT,VEC2,POSITION
from build_fireball_flight import user_parameter
E=u.EditorAssetLibrary
report={'revision':REV,'saved':[],'runtime_tested':False,'preview_rendered':False}
def receipt():(ROOT/'asset_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def save(asset):
    E.set_metadata_tag(asset,'M10.CombatPaceRevision',REV)
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());receipt()
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Preserving active PIE')
for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if str(p.get_name()).startswith(DEST) or str(p.get_name())==BP:raise RuntimeError('Preserving unsaved '+p.get_name())
try:
    path=DEST+'/NS_M10LocalPoisonGas'
    if E.does_asset_exist(path):
        system=u.load_asset(path)
        if E.get_metadata_tag(system,'M10.CombatPaceRevision')!=REV:raise RuntimeError('Preserving unowned '+path)
    else:
        system=E.duplicate_asset('/Game/Monsters/M10Mawcrawler/LocalGasV8/NS_M10LocalPoisonGas',path)
        if not system:raise RuntimeError('Cannot duplicate local gas')
        E.set_metadata_tag(system,'M10.CombatPaceRevision',REV)
    variables=str(API.call_method('GetUserVariables',(system,)).export_text())
    if 'User.DiffusionSpeed' not in variables:user_parameter(system,'DiffusionSpeed',FLOAT)
    a='max(0,Particles.Age)'
    n='saturate(Particles.NormalizedAge*User.DiffusionSpeed)'
    seed='frac(float(Particles.UniqueID)*.61803398875+.137)'
    var='frac(float(Particles.UniqueID)*.41421356237+.273)'
    other='frac(float(Particles.UniqueID)*.75487766623+.413)'
    angle=f'({other}*6.2831853)'
    spread=f'float3(cos({angle}),sin({angle}),({var}-.5)*.35)*User.Radius*(.022+.060*sqrt({n}))*(.6+.4*{var})'
    roll=f'float3(sin({a}*.48+{other}*6.283),cos({a}*.43+{seed}*6.283),sin({a}*.35+{var}*6.283)*.4)*User.Radius*.025*saturate({a}*.6)'
    values={
        'Particles.Position':(POSITION,f'Particles.MistBirthPosition+Particles.MistBirthDrift*{a}+float3(0,0,.45*{a}*{a})+{spread}+{roll}'),
        'Particles.SpriteSize':(VEC2,f'User.Radius*(.38+.43*sqrt({n}))*(.94+.12*{other})*float2(1,1.12)')}
    for script in ('ParticleSpawnScript','ParticleUpdateScript'):
        tag='Fireball.Assignments.BodyRisingSoot.'+script
        own_tag='M10.CombatPaceAssignments.'+script
        module=E.get_metadata_tag(system,own_tag)
        if module:E.set_metadata_tag(system,tag,module)
        else:E.remove_metadata_tag(system,tag)
        # The V8 color-only override is retained. Own just the final growth node.
        assignments(system,'BodyRisingSoot',script,values)
        E.set_metadata_tag(system,own_tag,E.get_metadata_tag(system,tag))
    if not u.RainAssetEditor.compile_rain(system):raise RuntimeError('M10 radial gas compilation failed')
    save(system)
    bp=u.load_asset(BP)
    if not bp:raise RuntimeError('Missing M10 blueprint')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo=u.get_default_object(bp.generated_class())
    settings={'moving_turn_speed':36.,'pivot_turn_speed':30.,'turn_acceleration':97.5,'bite_lunge_distance':150.,
              'bite_trigger_range':450.,'mouth_reach':150.}
    for key,value in settings.items():cdo.set_editor_property(key,value)
    save(bp)
    report.update(stage='assets_saved',smoke=system.get_path_name(),blueprint=bp.get_path_name(),settings=settings,
        native_radius_cm=480,effective_niagara_radius_cm=720,diffusion_speed=1.5,
        growth='normalized age multiplied by 1.5 for both visuals and dense-core exposure',
        animation_sync='turn cadence follows measured angular speed; existing clips and foot lock retained',
        lunge_window_seconds=[.52,.70],lunge_collision='swept capsule and walkable-floor support',
        emission_seconds=6,hold_seconds=8,fade_seconds=1.5,color='preserved LocalGasV8')
    receipt();u.log('M10_COMBAT_PACE_V10_ASSETS_SAVED')
except Exception:
    report.update(stage='production_failed',error=traceback.format_exc());receipt();raise
