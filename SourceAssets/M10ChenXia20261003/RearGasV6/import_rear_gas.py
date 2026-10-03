"""Recover V6 smoke dependencies only; the retired attack is rebuilt through V7."""
from pathlib import Path
import json,sys,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[2]
DEST='/Game/Monsters/M10Mawcrawler/RearGasV6';REV='M10RearGasV6_20261003'
sys.path.insert(0,str(PROJECT/'Tools/Skills'))
from build_fireball_assets import API,ref,emitters,setdata,assignments
from build_fireball_flames import COLOR
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
report={'revision':REV,'saved':[],'game_tested':False,'preview_rendered':False}
def receipt():(ROOT/'asset_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf8')
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing '+path)
    return a
def save(a):
    E.set_metadata_tag(a,'M10.RearGasRevision',REV)
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    if a.get_path_name() not in report['saved']:report['saved'].append(a.get_path_name())
    receipt()
def copy(source,name):
    path=DEST+'/'+name
    if E.does_asset_exist(path):
        a=load(path)
        if E.get_metadata_tag(a,'M10.RearGasRevision')!=REV:raise RuntimeError('Preserving unowned '+path)
        return a
    a=E.duplicate_asset(source,path)
    if not a:raise RuntimeError('Cannot duplicate '+source)
    E.set_metadata_tag(a,'M10.RearGasRevision',REV);return a

if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Preserving active PIE')
if any(str(p.get_name()).startswith('/Game/Monsters/M10Mawcrawler') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserving unsaved M10 assets')
try:
    # Duplicate the complete V21 simulation, including frozen birth attributes,
    # the clamped atlas age, bounds mode and persistent density material.
    source='/Game/Monsters/HundredEyedSlag/SmokeVisibilityFixV21'
    material=copy(source+'/M_SlagPersistentBodySmoke','M_M10GreenPersistentSmoke')
    L.recompile_material(material)
    if not u.PoisonMaggotMonster.compile_material_assets([material]):raise RuntimeError('Smoke material compile failed')
    save(material)
    system=copy(source+'/NS_SlagBodySmoke','NS_M10RearPoisonGas')
    emitter='BodyRisingSoot'
    a='max(0,Particles.Age)'
    fade=f'saturate((User.SmokeLifetime-{a})/max(.01,User.SmokeLifetime-User.SmokeHoldTime))'
    green=f'float4(.055,.22,.018,.65*saturate({a}/.45)*({fade}*{fade}*(3-2*{fade})))'
    for script in ('ParticleSpawnScript','ParticleUpdateScript'):
        # Duplicated packages need not carry authoring metadata. In that case
        # append a color-only assignment after the copied simulation modules.
        assignments(system,emitter,script,{'Particles.Color':(COLOR,green)})
    setdata('SetRendererData',u.NiagaraExt_RendererData,ref(system,emitter,renderer=0),{'Material':material.get_path_name()})
    if not u.RainAssetEditor.compile_rain(system):raise RuntimeError('Green smoke compile failed')
    save(system)
    view=copy('/Game/Monsters/HundredEyedSlag/WorldSmokeV19/M_SlagMistBlindView','M_M10GasBlindView')
    custom=next(n for n in L.get_material_expressions(view) if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('description'))=='Slag in-smoke defocus, distortion and soot film')
    code=(PROJECT/'SourceAssets/HundredEyedSlagMeshy20260930/WorldSmokeV19/blind_view.hlsl').read_text(encoding='utf8')
    code=code.replace('float3(.018,.014,.012)','float3(.035,.16,.015)').replace('float3(0.018, 0.014, 0.012)','float3(.035,.16,.015)')
    # Whitespace in the source is author formatting, not a shader interface.
    import re
    code=re.sub(r'float3 soot\s*=\s*float3\([^;]+;', 'float3 soot = float3(.035,.16,.015);',code)
    custom.set_editor_property('code',code);L.recompile_material(view)
    if not u.PoisonMaggotMonster.compile_material_assets([view]):raise RuntimeError('Green blindness material compile failed')
    save(view)
    report.update(stage='assets_saved',smoke=system.get_path_name(),blind_material=view.get_path_name(),scope='V6 smoke source only; V7 owns the active rear attack and V8/V10 override appearance and diffusion')
    receipt();u.log('M10_REAR_GAS_V6_ASSETS_SAVED')
except Exception:
    report.update(stage='production_failed',error=traceback.format_exc());receipt();raise
