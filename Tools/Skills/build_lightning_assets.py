"""Create project-owned lightning copies and import the two legacy cast sounds.

Run through mcp_call_codex.ps1 -PythonScript. No game or preview is started.
"""
import json
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir())
DEST = '/Game/Skills/Lightning'
SOURCE = '/Game/_SplineVFX/NS/NS_Spline_ElectricLightning'
api = unreal.get_default_object(unreal.NiagaraToolset_System)
dirty = {p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(DEST+'/') for p in dirty):
    raise RuntimeError('Unsaved edits in the lightning destination; preserve them before importing.')
unreal.EditorAssetLibrary.make_directory(DEST)
system = unreal.load_asset(DEST+'/NS_LightningChain') if unreal.EditorAssetLibrary.does_asset_exist(DEST+'/NS_LightningChain') else unreal.EditorAssetLibrary.duplicate_asset(SOURCE, DEST+'/NS_LightningChain')
if not system:
    raise RuntimeError('Restore the owned Dr.Game Free Spline VFX source first')

def ref(emitter, stage='', module=''):
    r=unreal.NiagaraExt_StackItemReference()
    for key,value in dict(system=system,emitter_name=emitter,script_name=stage,module_name=module).items():
        r.set_editor_property(key,value)
    return r

def put(emitter,stage,module,name,value,typ='/Script/Niagara.NiagaraFloat'):
    if not unreal.RainAssetEditor.set_input(system,emitter,stage,module,name,typ,value):
        raise RuntimeError('Cannot author '+emitter+'/'+module+'/'+name)

def restore_source_width(emitter):
    # Restore the pre-taper Multiply(RandomRange(1,8), User._Width) input tree.
    # Read typed values from the owned source, including its spawn-only random mode.
    original=unreal.load_asset(SOURCE)
    for path in [[],['A'],['A','Evaluation Type'],['A','Randomness Mode'],['A','Minimum'],['A','Maximum'],['A','Recalculate Random Each Loop'],['B']]:
        src=ref(emitter,'ParticleSpawnScript','InitializeParticle')
        dst=ref(emitter,'ParticleSpawnScript','InitializeParticle')
        src.set_editor_property('system',original)
        for r in (src,dst):r.set_editor_property('input_name_stack',['Ribbon Width']+path)
        value=api.call_method('GetStackInputData',(src,))
        api.call_method('SetStackInputData',(dst,value))

enum='/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum'
once=unreal.RainAssetEditor.read_input(system,'Detail','EmitterUpdateScript','EmitterState','Loop Behavior')
for emitter in ('Currency','MainPower','Detail'):
    # Retain the source's Self lifecycle; no borrowed external emitter lifecycle.
    put(emitter,'EmitterUpdateScript','EmitterState','Loop Behavior',once,enum)
    # Once + source's infinite duration spawns the ribbon only once. The runtime
    # actor destroys it at the shared hold/fade deadline; do not edit hidden Loop Duration.
    if emitter!='Detail':
        put(emitter,'ParticleSpawnScript','InitializeParticle','Lifetime','(Value=0.85)')
    color='(R=0.32,G=0.12,B=1.0,A=1.0)' if emitter=='Currency' else '(R=0.64,G=0.42,B=1.0,A=1.0)'
    put(emitter,'ParticleSpawnScript','InitializeParticle','Color',color,'/Script/CoreUObject.LinearColor')
    # User preferred the previous palette and the source's HSV variation.
    for switch in ('AdjustHue','AdjustSaturation','AdjustValue','AdjustAlpha'):
        put(emitter,'ParticleSpawnScript','InitializeParticle',switch,'(Value=-1)','/Script/Niagara.NiagaraBool')
    if emitter!='Detail':
        restore_source_width(emitter)
        # Fixed spline silhouette. Keep brightness separate from spatial jitter:
        # the original ScaleColor002 multiplies RGB by User._Brightness.
        top=api.call_method('GetEmitterTopology',(ref(emitter),))
        modules={str(m.get_editor_property('module_name')) for m in top.get_editor_property('particle_update_script').get_editor_property('modules')}
        for module in ('JitterPosition','ScaleColor002'):
            if module in modules:
                api.call_method('RemoveModule',(ref(emitter,'ParticleUpdateScript',module),))
        if 'ScaleColor' not in modules:
            api.call_method('AddModule',(ref(emitter,'ParticleUpdateScript'),unreal.load_asset('/Niagara/Modules/Update/Color/ScaleColor.ScaleColor')))
        # The default ScaleColor module scales Initial.Color, so repeated updates
        # do not compound brightness. Actor brightness also carries the fade.
        put(emitter,'ParticleUpdateScript','ScaleColor','ScaleRGB','(Value=-1)','/Script/Niagara.NiagaraBool')
        put(emitter,'ParticleUpdateScript','ScaleColor','ScaleA','(Value=-1)','/Script/Niagara.NiagaraBool')
        put(emitter,'ParticleUpdateScript','ScaleColor','Scale RGB','(HlslExpression="float3(User._Brightness, User._Brightness, User._Brightness)")','/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
        put(emitter,'ParticleUpdateScript','ScaleColor','Scale Alpha','(Value=1.0)')
unreal.EditorAssetLibrary.set_metadata_tag(system,'Lightning.Source',SOURCE)
unreal.EditorAssetLibrary.set_metadata_tag(system,'Lightning.Lifecycle','Runtime spline owner, hold 0.5s + fade 0.25s; brightness controlled per component')
unreal.EditorAssetLibrary.set_metadata_tag(system,'Lightning.WidthProfile','Previous version restored at user request: source spawn-only random width, no imposed taper')
if not unreal.RainAssetEditor.compile_rain(system):
    raise RuntimeError('Lightning Niagara compilation failed')
if not unreal.EditorAssetLibrary.save_loaded_asset(system,False):
    raise RuntimeError('Lightning system save failed')
saved=[system.get_path_name()]
for index in (() if globals().get('LIGHTNING_VISUAL_ONLY',False) else (1,2)):
    task=unreal.AssetImportTask()
    task.filename=str(ROOT/f'SourceAssets/Lightning20260920/S_LightningCast{index}.wav')
    task.destination_path=DEST;task.destination_name=f'S_LightningCast{index}'
    task.automated=True;task.replace_existing=True;task.save=False
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    wave=unreal.load_asset(DEST+f'/S_LightningCast{index}')
    if not isinstance(wave,unreal.SoundWave):
        raise RuntimeError('Cast audio import failed')
    wave.set_editor_property('looping',False)
    wave.set_editor_property('loading_behavior',unreal.SoundWaveLoadingBehavior.FORCE_INLINE)
    if not unreal.EditorAssetLibrary.save_loaded_asset(wave,False):
        raise RuntimeError('Cast audio save failed')
    saved.append(wave.get_path_name())
result={'saved':saved,'source':SOURCE,'tested':False}
out=ROOT/'Saved/LightningMigration/assets-authored.json'
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
