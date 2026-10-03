"""Save a desaturated local smoke bloom and a subtler olive blindness film."""
from pathlib import Path
import json,re,sys,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[2]
DEST='/Game/Monsters/M10Mawcrawler/LocalGasV8';REV='M10LocalGasV8_20261003'
sys.path.insert(0,str(PROJECT/'Tools/Skills'))
from build_fireball_assets import assignments,put
from build_fireball_flames import COLOR
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
report={'revision':REV,'saved':[],'runtime_tested':False,'preview_rendered':False}
def receipt():(ROOT/'asset_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf8')
def copy(source,name):
    path=DEST+'/'+name
    if E.does_asset_exist(path):
        asset=u.load_asset(path)
        if E.get_metadata_tag(asset,'M10.LocalGasRevision')!=REV:raise RuntimeError('Preserving unowned '+path)
        return asset
    asset=E.duplicate_asset(source,path)
    if not asset:raise RuntimeError('Cannot duplicate '+source)
    E.set_metadata_tag(asset,'M10.LocalGasRevision',REV);return asset
def save(asset):
    E.set_metadata_tag(asset,'M10.LocalGasRevision',REV)
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());receipt()
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Preserving active PIE')
if any(str(p.get_name()).startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserving unsaved local gas assets')
try:
    # Preserve the authored density/age, frozen world-space births and the
    # expanding puff simulation; append or update only its final color override.
    system=copy('/Game/Monsters/M10Mawcrawler/RearGasV6/NS_M10RearPoisonGas','NS_M10LocalPoisonGas')
    a='max(0,Particles.Age)'
    fade=f'saturate((User.SmokeLifetime-{a})/max(.01,User.SmokeLifetime-User.SmokeHoldTime))'
    tint=f'float4(.13,.16,.10,.46*saturate({a}/.45)*({fade}*{fade}*(3-2*{fade})))'
    for script in ('ParticleSpawnScript','ParticleUpdateScript'):
        assignments(system,'BodyRisingSoot',script,{'Particles.Color':(COLOR,tint)})
    # Local puffs overlap more than the old moving jet. Emit five per second
    # instead of eight, while keeping the shared runtime stop/start parameter.
    put(system,'BodyRisingSoot','EmitterUpdateScript','SpawnRate','SpawnRate',
        '(HlslExpression="max(0,User.EmissionRate)*.625")','/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    if not u.RainAssetEditor.compile_rain(system):raise RuntimeError('Local gas Niagara compile failed')
    save(system)
    view=copy('/Game/Monsters/M10Mawcrawler/RearGasV6/M_M10GasBlindView','M_M10LocalGasBlindView')
    node=next(n for n in L.get_material_expressions(view) if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('description'))=='Slag in-smoke defocus, distortion and soot film')
    code=str(node.get_editor_property('code'))
    code=re.sub(r'float3 soot\s*=\s*float3\([^;]+;', 'float3 soot = float3(.070,.085,.052);',code)
    code=re.sub(r'grime\s*\*\s*\.78', 'grime * .58',code)
    node.set_editor_property('code',code);L.recompile_material(view)
    if not u.PoisonMaggotMonster.compile_material_assets([view]):raise RuntimeError('Local gas view material compile failed')
    save(view)
    report.update(stage='assets_saved',smoke=system.get_path_name(),blind_material=view.get_path_name(),world_color=[.13,.16,.10],particle_alpha=.46,
        blind_film_color=[.070,.085,.052],blind_film_mix=.58,blur_and_distortion_preserved=True,
        native_radius_cm=320,effective_niagara_radius_cm=480,rise_cm_per_second=12,horizontal_drift_cm_per_second=0,emission_rate_per_second=5,maximum_emitted_particles=30,
        exposure='shared visible-core radius expansion and wall occlusion; local to each frozen birth position',cooldown_seconds=12,emission_seconds=6,hold_seconds=8,fade_seconds=1.5)
    receipt();u.log('M10_LOCAL_GAS_V8_ASSETS_SAVED')
except Exception:
    report.update(stage='production_failed',error=traceback.format_exc());receipt();raise
