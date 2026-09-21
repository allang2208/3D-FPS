"""Author the holy-light mote copy, analytic beam/pool materials and original sound.

Run in the existing UE editor through mcp_call_codex.ps1. No PIE or previews.
Set HOLY_VISUALS_ONLY=True via runpy to update only the two materials and motes.
"""
import json
from pathlib import Path
import unreal

ROOT=Path(unreal.Paths.project_dir())
DEST='/Game/Skills/HolyLight'
SOURCE='/Game/_SplineVFX/NS/NS_Spline_Holy'
api=unreal.get_default_object(unreal.NiagaraToolset_System)
lib=unreal.MaterialEditingLibrary
assets=unreal.AssetToolsHelpers.get_asset_tools()
dirty={p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(DEST+'/') for p in dirty):
    raise RuntimeError('Preserve unsaved edits in the holy-light destination before importing.')
unreal.EditorAssetLibrary.make_directory(DEST)
saved=[]
visuals_only=bool(globals().get('HOLY_VISUALS_ONLY',False))

def material(name,mask,intersection_distance):
    m=unreal.load_asset(DEST+'/'+name) or assets.create_asset(name,DEST,unreal.Material,unreal.MaterialFactoryNew())
    for e in list(lib.get_material_expressions(m)):lib.delete_material_expression(m,e)
    m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_ADDITIVE)
    m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('two_sided',True)
    m.set_editor_property('disable_depth_test',False)
    def node(cls):return lib.create_material_expression(m,cls)
    def scalar(name,value):
        n=node(unreal.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
    def connect(a,b,pin):
        if not lib.connect_material_expressions(a,'',b,pin):raise RuntimeError('Material connection failed: '+name+'/'+pin)
    uv=node(unreal.MaterialExpressionTextureCoordinate)
    depth=node(unreal.MaterialExpressionPixelDepth)
    ratio=scalar('DissolveRatio',.28)
    fade=scalar('Fade',1)
    opacity=scalar('OpacityScale',.3)
    effect_age=scalar('EffectAge',0)
    normal=node(unreal.MaterialExpressionPixelNormalWS)
    view=node(unreal.MaterialExpressionCameraVectorWS)
    expressions=[('UV',uv),('Depth',depth),('DissolveRatio',ratio),('Fade',fade),('OpacityScale',opacity),('EffectAge',effect_age),('NormalWS',normal),('ViewDir',view)]
    custom=node(unreal.MaterialExpressionCustom);custom.set_editor_property('code',mask);custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    inputs=[]
    for key,expr in expressions:
        i=unreal.CustomInput();i.set_editor_property('input_name',key);inputs.append(i)
    custom.set_editor_property('inputs',inputs)
    for key,expr in expressions:connect(expr,custom,key)
    depth_fade=node(unreal.MaterialExpressionDepthFade)
    depth_fade.set_editor_property('fade_distance_default',intersection_distance)
    connect(custom,depth_fade,'Opacity')
    color=node(unreal.MaterialExpressionVectorParameter);color.set_editor_property('parameter_name','HolyColor');color.set_editor_property('default_value',unreal.LinearColor(1,.64,.22,1))
    power=scalar('Intensity',8)
    mul=node(unreal.MaterialExpressionMultiply);connect(color,mul,'A');connect(power,mul,'B')
    exposure=node(unreal.MaterialExpressionEyeAdaptationInverse)
    connect(mul,exposure,str(lib.get_material_expression_input_names(exposure)[0]))
    if not lib.connect_material_property(exposure,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR):raise RuntimeError('Emissive connection failed')
    if not lib.connect_material_property(depth_fade,'',unreal.MaterialProperty.MP_OPACITY):raise RuntimeError('Opacity connection failed')
    lib.recompile_material(m)
    if not unreal.EditorAssetLibrary.save_loaded_asset(m,False):raise RuntimeError('Material save failed: '+name)
    saved.append(m.get_path_name())

material('M_HolyBeam', '''float h=saturate(UV.y);
// Project onto the horizontal cross-section so looking upward keeps a soft profile.
float2 n=NormalWS.xy/max(length(NormalWS.xy),.0001);
float2 v=ViewDir.xy/max(length(ViewDir.xy),.0001);
float facing=saturate(abs(dot(n,v)));
float radiusSquared=1.0-facing*facing;
float edge=(exp(-3.0*radiusSquared)-exp(-3.0))/(1.0-exp(-3.0));
// Seamless continuous variation replaces the old angular/height hash slices.
float a=UV.x*6.2831853;
float drift=.5+.25*sin(a*3.0+h*9.0-EffectAge*.65)+.25*sin(a*5.0-h*13.0+EffectAge*.4);
float base=smoothstep(0.0,max(.001,DissolveRatio),h);
float dissolve=smoothstep(0.0,.018,h)*lerp(.26+.16*drift,1.0,base);
float nearFade=smoothstep(10.0,140.0,Depth);
float topFade=1.0-smoothstep(.78,1.0,h);
return Fade*OpacityScale*edge*dissolve*nearFade*topFade;''',45)
material('M_HolyPool', '''float r=length(UV-.5);
float glow=exp(-r*r*18.0)*(1.0-smoothstep(.34,.5,r));
return Fade*OpacityScale*glow*smoothstep(10.0,90.0,Depth);''',8)

system=unreal.load_asset(DEST+'/NS_HolyLightMotes') or unreal.EditorAssetLibrary.duplicate_asset(SOURCE,DEST+'/NS_HolyLightMotes')
if not system:raise RuntimeError('Restore the licensed Holy Spline source first')
def ref(emitter,stage='',module=''):
    r=unreal.NiagaraExt_StackItemReference()
    for k,v in dict(system=system,emitter_name=emitter,script_name=stage,module_name=module).items():r.set_editor_property(k,v)
    return r
def put(stage,module,key,value,typ='/Script/Niagara.NiagaraFloat'):
    if not unreal.RainAssetEditor.set_input(system,'Detail002',stage,module,key,typ,value):raise RuntimeError('Cannot author '+module+'/'+key)
for e in api.call_method('GetSystemSummary',(system,)).get_editor_property('emitters'):
    name=str(e.get_editor_property('emitter_name'))
    if name!='Detail002':api.call_method('RemoveEmitter',(ref(name),))
top=api.call_method('GetEmitterTopology',(ref('Detail002'),))
for prop,stage,names in [('particle_spawn_script','ParticleSpawnScript',('KillParticles','MoveToNearestDistanceFieldSurface_GPU')),('particle_update_script','ParticleUpdateScript',('ScratchModule_02',))]:
    present={str(m.get_editor_property('module_name')) for m in top.get_editor_property(prop).get_editor_property('modules')}
    for name in names:
        if name in present:api.call_method('RemoveModule',(ref('Detail002',stage,name),))
put('EmitterUpdateScript','SpawnRate','SpawnRate','(HlslExpression="18.0 * saturate(User.Progress)")','/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
put('ParticleSpawnScript','InitializeParticle','Lifetime Min','(Value=0.9)')
put('ParticleSpawnScript','InitializeParticle','Lifetime Max','(Value=1.5)')
put('ParticleSpawnScript','InitializeParticle','Uniform Sprite Size','(Value=5.0)')
put('ParticleSpawnScript','InitializeParticle','Color','(R=1.0,G=0.64,B=0.22,A=0.9)','/Script/CoreUObject.LinearColor')
for key in ('AdjustHue','AdjustSaturation','AdjustValue','AdjustAlpha'):
    put('ParticleSpawnScript','InitializeParticle',key,'(Value=0)','/Script/Niagara.NiagaraBool')
put('ParticleSpawnScript','SetVariables_2CCB6F004D709661516C5F9CECCC13C6','Particles.MyOffset','(X=0,Y=0,Z=0)','/Script/CoreUObject.Vector3f')
put('ParticleUpdateScript','GravityForce','Gravity','(X=0,Y=0,Z=180)','/Script/CoreUObject.Vector3f')
# Keep the owned emitter's material, SubUV/size curves and Self lifecycle. Scale from Initial.Color.
put('ParticleUpdateScript','ScaleColor','Scale RGB','(HlslExpression="float3(User._Brightness,User._Brightness,User._Brightness)")','/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
unreal.EditorAssetLibrary.set_metadata_tag(system,'HolyLight.Source',SOURCE)
unreal.EditorAssetLibrary.set_metadata_tag(system,'HolyLight.Lifecycle','Actor-owned: .24s smooth onset, emit until 2s, at least .75s smooth fade; rising gold particles from target chest spline')
if not unreal.RainAssetEditor.compile_rain(system):raise RuntimeError('Holy-light Niagara compilation failed')
if not unreal.EditorAssetLibrary.save_loaded_asset(system,False):raise RuntimeError('Holy-light system save failed')
saved.append(system.get_path_name())
if not visuals_only:
    task=unreal.AssetImportTask();task.filename=str(ROOT/'SourceAssets/HolyLight20260920/S_HolyLightCast.wav');task.destination_path=DEST;task.destination_name='S_HolyLightCast'
    task.automated=True;task.replace_existing=True;task.save=False
    assets.import_asset_tasks([task]);wave=unreal.load_asset(DEST+'/S_HolyLightCast')
    if not isinstance(wave,unreal.SoundWave):raise RuntimeError('Holy-light sound import failed')
    wave.set_editor_property('looping',False);wave.set_editor_property('loading_behavior',unreal.SoundWaveLoadingBehavior.FORCE_INLINE)
    if not unreal.EditorAssetLibrary.save_loaded_asset(wave,False):raise RuntimeError('Holy-light sound save failed')
    saved.append(wave.get_path_name())
out={'saved':saved,'source':SOURCE,'tested':False}
record='visual-polish-authored.json' if visuals_only else 'assets-authored.json'
(ROOT/'Saved/HolyLightMigration'/record).write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out))
