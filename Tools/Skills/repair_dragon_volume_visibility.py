"""V8R1 targeted repair of rotated streaking and flame exposure."""
import json,sys
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Tools/Skills'))
if not hasattr(u,'RainAssetEditor'):u.RainAssetEditor=u.DragonBreathAuthorLibrary
from build_fireball_assets import LIB,ref,setdata,put

DEST='/Game/Skills/DragonBreath20261013/VolumeV8'
GRID='Grid3D_Gas_Master_Emitter'
REVISION='DragonBreathVolumeV8R1_20261014'


def exposure_material():
    eal=u.EditorAssetLibrary;tools=u.AssetToolsHelpers.get_asset_tools()
    basepath=DEST+'/M_DragonVolumeFlame_R1'
    base=u.load_asset(basepath) if eal.does_asset_exist(basepath) else tools.duplicate_asset('M_DragonVolumeFlame_R1',DEST,u.load_asset('/NiagaraFluids/Materials/Grid3D/M_3DGas_Base'))
    if eal.get_metadata_tag(base,'DragonVolume.Exposure')!='R1':
        emission=LIB.get_material_property_input_node(base,u.MaterialProperty.MP_EMISSIVE_COLOR)
        if not emission:raise RuntimeError('Native gas material has no emissive input')
        inverse=LIB.create_material_expression(base,u.MaterialExpressionEyeAdaptationInverse)
        pin=str(LIB.get_material_expression_input_names(inverse)[0])
        if not LIB.connect_material_expressions(emission,'',inverse,pin):raise RuntimeError('Could not connect volume exposure')
        if not LIB.connect_material_property(inverse,'',u.MaterialProperty.MP_EMISSIVE_COLOR):raise RuntimeError('Could not bind volume emission')
        eal.set_metadata_tag(base,'DragonVolume.Exposure','R1')
    mipath=DEST+'/MI_DragonVolumeFlame_R1'
    mi=u.load_asset(mipath) if eal.does_asset_exist(mipath) else tools.duplicate_asset('MI_DragonVolumeFlame_R1',DEST,u.load_asset('/NiagaraFluids/Materials/Grid3D/Instances/MI_3DGas_Base'))
    LIB.set_material_instance_parent(mi,base)
    # This solver exports RG16F (R=density, G=temperature), with positions in
    # the component's rotated local grid. Do not inherit the legacy sampler
    # (temperature in B) or legacy transform from the general gas material.
    for name,value in [('Use Legacy Transform',False),('UseLegacyVolumeSample',False),('Use Blackbody Curve',True)]:
        LIB.set_material_instance_static_switch_parameter_value(mi,name,value)
    LIB.update_material_instance(mi)
    errors=LIB.recompile_material(base)
    if errors:raise RuntimeError(str(errors))
    compiler=u.DragonBreathAuthorLibrary if hasattr(u,'DragonBreathAuthorLibrary') else u.PoisonMaggotMonster
    if not compiler.compile_material_assets([base,mi]):raise RuntimeError('Volume material compilation failed')
    for asset in [base,mi]:
        if not eal.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
    return mi


def apply(system):
    # UE's streak offset is calculated from world velocity but added to grid
    # indices. With a rotated grid it can write in the opposite direction.
    changes=[{'emitter':GRID,'module':'Grid3D_Gas_InitializeParticleSource','input':name,'value':value}
             for name,value in [('Use Streaking','(Value=-1)'),('Max Streak Samples','(Value=1)')]]
    if hasattr(u,'DragonBreathAuthorLibrary'):
        if not u.DragonBreathAuthorLibrary.configure_fluid_inputs(system,json.dumps(changes)):
            raise RuntimeError('Could not disable rotated-grid streaking')
    else:
        # The external editor API cannot assign static NiagaraBool inputs in
        # UE 5.8. A single sample also removes every displaced streak sample.
        put(system,GRID,'EmitterSpawnScript','Grid3D_Gas_InitializeParticleSource','Max Streak Samples','(Value=1)','/Script/Niagara.NiagaraInt32')
    setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(system,'ParticleSourceEmitter'),{'InterpolatedSpawnMode':'NoInterpolation'})
    mi=exposure_material()
    setdata('SetRendererData',u.NiagaraExt_RendererData,ref(system,GRID,renderer=1),{'Material':mi.get_path_name()})
    u.EditorAssetLibrary.set_metadata_tag(system,'DragonBreath.Revision',REVISION)
    return mi


def run():
    if not hasattr(u,'DragonBreathAuthorLibrary') and u.EditorLevelLibrary.get_game_world():
        raise RuntimeError('Stop PIE before saving the active Dragon Breath asset')
    s=u.load_asset(DEST+'/NS_DragonVolume')
    if not s:raise RuntimeError('Missing active volume')
    mi=apply(s)
    if not u.RainAssetEditor.compile_rain(s,True):raise RuntimeError('Volume full compile failed')
    if not u.EditorAssetLibrary.save_loaded_asset(s,False):raise RuntimeError('Volume save failed')
    out=ROOT/'SourceAssets/DragonBreath20261013/VolumeV8R1_20261014';out.mkdir(parents=True,exist_ok=True)
    receipt={'revision':REVISION,'stage':'assets_saved','asset':s.get_path_name(),'material':mi.get_path_name(),
             'changes':['grid streaks disabled','correct non-interpolated source spawn','explicit RG temperature and local-grid material sampling','single emissive exposure compensation'],
             'native_gameplay_changed':False,'gameplay_tested':False,'visual_acceptance':False}
    (out/'delivery.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    (out.parent/'asset-authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('DRAGON_VOLUME_R1_SAVED '+s.get_path_name())


if __name__=='__main__':run()
