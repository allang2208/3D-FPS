"""Author V8 volumetric Dragon Breath from Epic's native 3D gas template.

Only the independent VolumeV8 package is written. No simulation or visual test.
Requires the isolated DragonBreathAuthor editor module (background commandlet).
"""
import json,sys
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Tools/Skills'))
if not hasattr(u,'DragonBreathAuthorLibrary'):
    raise RuntimeError('Run this author in SourceAssets/DragonBreath20261013/AuthorHost/DragonBreathAuthor.uproject')
u.RainAssetEditor=u.DragonBreathAuthorLibrary
from build_fireball_assets import API,ref,setdata
from build_fireball_flames import FLOAT,VEC3,POSITION
from dragon_fluid_source import build_sources

SOURCE='/NiagaraFluids/Templates/Gas/3D/Systems/Grid3D_Gas_SimpleParticleSource'
DEST='/Game/Skills/DragonBreath20261013/VolumeV8/NS_DragonVolume'
OUT=ROOT/'SourceAssets/DragonBreath20261013/VolumeV8R6_20261015'
REVISION='DragonBreathVolumeV8R6_20261015'
GRID='Grid3D_Gas_Master_Emitter'
INT='/Script/Niagara.NiagaraInt32'
BOOL='/Script/Niagara.NiagaraBool'


def configure(system):
    changes=[]
    def val(module,name,text):changes.append({'emitter':GRID,'module':module,'input':name,'value':text})
    def number(module,name,value):val(module,name,f'(Value={value})')
    def expr(module,name,text):changes.append({'emitter':GRID,'module':module,'input':name,'expression':text})
    q='Grid3D_Gas_QualityOverrides'
    expr(q,'Resolution Max Axis','User.ResolutionMaxAxis')
    expr(q,'Override.Resolution Max Axis','User.ResolutionMaxAxis')
    number(q,'Pressure Solve Iterations',8);number(q,'Override.Pressure Solve Iterations',8)
    number(q,'Attribute Resolution Multiplier',1);number(q,'Override.Attribute Resolution Multiplier',1)
    init='Grid3D_Gas_InitializeEmitter'
    expr(init,'World Size','User.WorldSpaceSize')
    number(init,'Internal Scale Multiplier',1)
    up='Grid3D_Gas_UpdateEmitter'
    number(up,'Compensate For Actor Motion',-1)
    number(up,'Draw Guides',0)
    val(up,'Local Pivot','(X=0,Y=0,Z=0)')
    source='Grid3D_Gas_InitializeParticleSource'
    number(source,'Use Radius Falloff',-1)
    # Native streak splats offset grid indices using WORLD-space velocity.
    # One sample prevents backwards/lateral streaks when the caster turns.
    # The scalar splat shader ignores the static bool; disabling it instead
    # substitutes MaxStreakSamples=100. Keep the input path enabled, capped at 1.
    number(source,'Use Streaking',-1)
    number(source,'Max Streak Samples',1)
    number(source,'Streak Rate',1)
    number(source,'Attributes Comp Mode',1)
    # Keep the template's additive weighted velocity injection.
    number(source,'Velocity Comp Mode',0)
    render='Grid3D_Gas_MaterialControls'
    # Restore the pre-R5 thickness. R6 refines emission RGB separately.
    val(render,'Temperature Range','(X=.35,Y=5.3)')
    expr(render,'Density Gain','.18*saturate(User.Strength)')
    number(render,'Density Albedo',.13)
    expr(render,'Temperature Color Gain','.4*saturate(User.Strength)')
    expr(render,'Temperature Opacity Gain','1.25*saturate(User.Strength)')
    number(render,'Apply Color Grid To Smoke',0)
    # Static world geometry can constrain the gas; the existing nine CPU rays
    # additionally bound invisible source travel on dynamic level geometry.
    number('Grid3D_ComputeBoundary','Use Global Distance Field Collisions',-1)
    number('Grid3D_RigidMesh_FindColliders','FindColliders',0)
    number('Grid3D_Gas_Buoyancy','TemperatureBuoyancy',.055)
    number('DissipateVector','DissipationRate',.35)
    adv='Grid3D_Advect_FluidAttribute'
    number(adv,'Dissipation Rate Density',1.4)
    number(adv,'Dissipation Rate Temperature',1.65)
    number(adv,'Subtraction Amount Density',.04)
    number(adv,'Subtraction Amount Temperature',.10)
    turbulence='Grid3D_Turbulence001'
    val(turbulence,'Turbulence Gain','(X=190,Y=190,Z=190)')
    val(turbulence,'Turbulence Frequency','(X=.12,Y=.12,Z=.12)')
    number(turbulence,'Turbulence Speed',.8)
    number('Grid3D_SmallScaleForce','Gain',15)
    number('Grid3D_VorticityConfinementForce','VorticityMult',2.6)
    if not u.DragonBreathAuthorLibrary.configure_fluid_inputs(system,json.dumps(changes)):
        raise RuntimeError('Fluid configuration incomplete; asset not saved')
    return changes


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    eal=u.EditorAssetLibrary
    template=u.load_asset(SOURCE)
    # Plugin templates are loadable before the commandlet asset registry has
    # enumerated their content. Duplicate the loaded UObject directly.
    system=u.load_asset(DEST) if eal.does_asset_exist(DEST) else u.AssetToolsHelpers.get_asset_tools().duplicate_asset('NS_DragonVolume',DEST.rsplit('/',1)[0],template)
    if not system:raise RuntimeError('Missing native fluid template')
    u.DragonBreathAuthorLibrary.prepare_fluid_stack(system)
    defaults=[('Range',FLOAT,'(Value=500)'),('HalfAngle',FLOAT,'(Value=.785398163)'),
              ('Strength',FLOAT,'(Value=1)'),('EmissionScale',FLOAT,'(Value=1)'),
              ('CellSize',FLOAT,'(Value=7.3046875)'),('Origin',POSITION,'(X=0,Y=0,Z=0)'),
              ('Forward',VEC3,'(X=1,Y=0,Z=0)'),('Side',VEC3,'(X=0,Y=1,Z=0)'),
              ('Up',VEC3,'(X=0,Y=0,Z=1)'),('WorldSpaceSize',VEC3,'(X=760,Y=935,Z=525)'),
              ('ResolutionMaxAxis',INT,'(Value=128)'),('DrawBounds',BOOL,'(Value=0)')]
    defaults += [(f'Ray{i}',FLOAT,'(Value=500)') for i in range(9)]
    # Preserve the runtime query interface. Hit normals are available for later
    # surface refinements, while this version delegates gas collision to GDF.
    defaults += [(f'HitNormal{i}',VEC3,'(X=-1,Y=0,Z=0)') for i in range(9)]
    values=[{'name':'User.'+name,'type':typ,'value':value} for name,typ,value in defaults]
    if not u.DragonBreathAuthorLibrary.set_fluid_user_defaults(system,json.dumps(values)):
        raise RuntimeError('Could not install typed fluid user defaults')
    build_sources(system)
    changes=configure(system)
    from build_dragon_volume_color import flame_material as build_flame_material
    flame_material=build_flame_material()
    # Renderer 0 is the template's debug slice, not its visible gas surface.
    setdata('SetRendererData',u.NiagaraExt_RendererData,ref(system,GRID,renderer=0),{'bIsEnabled':False})
    setdata('SetRendererData',u.NiagaraExt_RendererData,ref(system,GRID,renderer=1),
            {'StepFactor':.75,'LightingDownsampleFactor':2.,'ShadowStepFactor':3.,'Material':flame_material.get_path_name()})
    system.set_editor_property('fixed_bounds',u.Box(min=u.Vector(-1100,-1400,-700),max=u.Vector(1100,1400,700)))
    eal.set_metadata_tag(system,'DragonBreath.Revision',REVISION)
    eal.set_metadata_tag(system,'DragonBreath.Source',SOURCE)
    if not u.DragonBreathAuthorLibrary.compile_rain(system,True):
        raise RuntimeError('Niagara full compile failed; asset not saved')
    if not eal.save_loaded_asset(system,False):raise RuntimeError('Volume save failed')
    receipt={'revision':REVISION,'stage':'assets_saved','asset':system.get_path_name(),'saved_assets':[system.get_path_name(),flame_material.get_path_name(),flame_material.get_editor_property('parent').get_path_name()],
             'template':SOURCE,'renderer':'NiagaraVolumeRenderer','visible_flame_sprites':0,
             'source_rate':360,'source_max_lifetime':.8,'visual_tail_seconds':.65,
             'grid_max_axis_by_quality':[80,96,128,160,160],'remote_grid_max_axis':80,
             'pressure_iterations':8,'material_step_factor':.75,'runtime_tested':False,'rendered':False,
             'original_fireball_and_campfire_modified':False,'gameplay_changed':False,
             'shape_baseline':'pre-R5 Volume V8 R4','restored_shape_from':'trash/DragonBreathR5Layered20261015',
             'color_temperature_range':[.35,160.],'color_gain':.4,
             'runtime_loading_modified':False,'visual_acceptance':False,
             'defaults':defaults,'configured_inputs':changes}
    (OUT/'delivery.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    (OUT.parent/'asset-authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('DRAGON_VOLUME_V8_SAVED '+system.get_path_name())


if __name__=='__main__':run()
