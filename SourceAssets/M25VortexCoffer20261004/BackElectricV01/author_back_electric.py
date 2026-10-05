"""Derive a socket-bound M25 effect from the existing lightning spell. No play/render tests."""
from pathlib import Path
import json, traceback
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
SOURCE = '/Game/Skills/Lightning/NS_LightningChain'
DEST = '/Game/Monsters/VortexCofferM25/VFX/NS_M25_BackElectric'
BP = '/Game/Monsters/VortexCofferM25/BP_VortexCofferM25'
REV = 'M25BackElectric20261004V1'
LIB = u.EditorAssetLibrary
api = u.get_default_object(u.NiagaraToolset_System)
record = {'revision':REV, 'source':SOURCE, 'saved':[], 'runtime_tested':False, 'rendered':False}
def receipt():
    (ROOT/'asset_receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
def ref(system, emitter):
    r = u.NiagaraExt_StackItemReference()
    r.set_editor_property('system',system)
    r.set_editor_property('emitter_name',emitter)
    return r
def put(system, emitter, stage, module, name, value, typ='/Script/Niagara.NiagaraFloat'):
    if not u.RainAssetEditor.set_input(system,emitter,stage,module,name,typ,value):
        raise RuntimeError('Author input failed: '+emitter+'/'+module+'/'+name)
def save(asset):
    if not LIB.save_loaded_asset(asset,False):
        raise RuntimeError('Save failed: '+asset.get_path_name())
    record['saved'].append(asset.get_path_name())
    receipt()
def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():
        raise RuntimeError('Wrong project')
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
        if editor and editor.get_game_world():
            raise RuntimeError('Existing editor is in PIE; preserve session, no edits performed')
    dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if DEST in dirty or BP in dirty:
        raise RuntimeError('Preserve unsaved M25 assets')
    existed=LIB.does_asset_exist(DEST)
    system=u.load_asset(DEST) if existed else LIB.duplicate_asset(SOURCE,DEST)
    if not system:
        raise RuntimeError('Missing existing lightning spell source')
    if existed and LIB.get_metadata_tag(system,'M25.ElectricRevision')!=REV:
        raise RuntimeError('Preserve unowned destination '+DEST)
    if not existed:
        LIB.set_metadata_tag(system,'M25.ElectricRevision',REV)
    emitters={str(e.get_editor_property('emitter_name')) for e in api.call_method('GetSystemSummary',(system,)).get_editor_property('emitters')}
    if 'Detail' in emitters:
        api.call_method('RemoveEmitter',(ref(system,'Detail'),))
    for emitter in ('Currency','MainPower'):
        data=u.NiagaraExt_EmitterData()
        data.set_editor_property('property_values',json.dumps({'bLocalSpace':True,'SimTarget':'CPUSim'}))
        api.call_method('SetEmitterData',(ref(system,emitter),data))
        put(system,emitter,'ParticleSpawnScript','InitializeParticle','Lifetime','(Value=2.0)')
        color='(R=0.16,G=0.40,B=1.0,A=1.0)' if emitter=='Currency' else '(R=0.68,G=0.86,B=1.0,A=1.0)'
        put(system,emitter,'ParticleSpawnScript','InitializeParticle','Color',color,'/Script/CoreUObject.LinearColor')
        for switch in ('AdjustHue','AdjustSaturation','AdjustValue','AdjustAlpha'):
            put(system,emitter,'ParticleSpawnScript','InitializeParticle',switch,'(Value=0)','/Script/Niagara.NiagaraBool')
        # Spawn count and spline normalization share Emitter.MyCount.
        put(system,emitter,'EmitterUpdateScript','SetVariables_9DEBAE38414741332A25B4ABC41D2657',
            'Emitter.MyCount','(Value=64)','/Script/Niagara.NiagaraInt32')
        width='3.0' if emitter=='Currency' else '0.85'
        put(system,emitter,'ParticleSpawnScript','InitializeParticle','Ribbon Width',
            '(HlslExpression="User._Width * '+width+'")','/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    LIB.set_metadata_tag(system,'M25.ElectricRevision',REV)
    LIB.set_metadata_tag(system,'M25.Source',SOURCE)
    LIB.set_metadata_tag(system,'M25.Presentation','White-blue core and halo; 4 pooled lanes, 64 points per emitter, no GPU Detail, continuous path drift and soft cooling')
    if not u.RainAssetEditor.bind_spline_user_object(system,'User.M25Spline'):
        raise RuntimeError('M25 Niagara compile/spline binding failed')
    save(system)
    record.update(niagara=system.get_path_name(),spline_binding='User.M25Spline',
                  emitters=2,particles_per_lane=128,max_lanes=4,max_particles_per_monster=512)
    if not hasattr(u,'M25BackElectricComponent'):
        record['stage']='effect_saved_native_binding_pending'
        receipt()
        u.log('M25_ELECTRIC_EFFECT_SAVED_NATIVE_BINDING_PENDING')
        return
    bp=u.load_asset(BP)
    if bp is None:
        raise RuntimeError('Existing M25 blueprint missing')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo=u.get_default_object(bp.generated_class())
    component=cdo.get_editor_property('back_electric')
    if component is None:
        raise RuntimeError('Native M25 electric component missing')
    # Blueprint's authored locomotion/material/mesh defaults are retained.
    component.set_editor_property('electric_enabled',True)
    component.set_editor_property('arc_asset',system)
    component.set_editor_property('brightness',24.)
    component.set_editor_property('width',1.)
    component.set_editor_property('max_draw_distance',3500.)
    LIB.set_metadata_tag(bp,'M25.ElectricRevision',REV)
    save(bp)
    record.update(stage='assets_saved',blueprint=bp.get_path_name(),runtime_tested=False)
    receipt()
    u.log('M25_BACK_ELECTRIC_ASSETS_SAVED')

try:
    main()
except Exception:
    record.update(stage='production_failed',error=traceback.format_exc())
    receipt()
    raise
