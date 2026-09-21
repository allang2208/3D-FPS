"""Author fireball-only copies of owned Niagara examples and import the original impact cue.

Run in UnrealEditor-Cmd -run=pythonscript -unattended -multiprocess -NullRHI.
Asset creation/compilation only; no game, preview or acceptance run.
"""
import json
from pathlib import Path
import sys
import unreal

ROOT=Path(unreal.Paths.project_dir())
DEST='/Game/Skills/Fireball'
API=unreal.get_default_object(unreal.NiagaraToolset_System)
LIB=unreal.MaterialEditingLibrary
TOOLS=unreal.AssetToolsHelpers.get_asset_tools()
CREATED=[]

def ref(system,emitter,script='',module='',renderer=-1):
    r=unreal.NiagaraExt_StackItemReference()
    for k,v in dict(system=system,emitter_name=emitter,script_name=script,module_name=module,renderer_index=renderer).items():r.set_editor_property(k,v)
    return r

def emitters(s):
    return [str(e.get_editor_property('emitter_name')) for e in API.call_method('GetSystemSummary',(s,)).get_editor_property('emitters')]

def duplicate(source,name):
    asset=unreal.load_asset(DEST+'/'+name) if unreal.EditorAssetLibrary.does_asset_exist(DEST+'/'+name) else unreal.EditorAssetLibrary.duplicate_asset(source,DEST+'/'+name)
    if not asset:raise RuntimeError('Missing authoring source '+source)
    return asset

def save(a):
    if isinstance(a,unreal.NiagaraSystem) and not unreal.RainAssetEditor.compile_rain(a):raise RuntimeError('Niagara compile failed '+a.get_path_name())
    if not unreal.EditorAssetLibrary.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    CREATED.append(a.get_path_name());unreal.log('FIREBALL_AUTHORED '+a.get_path_name())

def setdata(method,typ,r,values):
    d=typ();d.set_editor_property('property_values',json.dumps(values));API.call_method(method,(r,d))

def put(s,e,script,module,name,value,typ='/Script/Niagara.NiagaraFloat'):
    if not unreal.RainAssetEditor.set_input(s,e,script,module,name,typ,value):raise RuntimeError('Cannot set '+e+'/'+module+'/'+name)

def assignments(s,e,script,values):
    tag='Fireball.Assignments.'+e+'.'+script
    module=unreal.EditorAssetLibrary.get_metadata_tag(s,tag)
    if not module:
        entries=[]
        for name,(typ,expr) in values.items():
            entry=unreal.NiagaraExt_SetParameterEntry();entry.import_text('(Variable=(Name="'+name+'",Type=(ClassStructOrEnum="'+typ+'",UnderlyingType=2)))');entries.append(entry)
        module=str(API.call_method('AddSetParametersModule',(ref(s,e,script),entries)).get_editor_property('module_name'))
        unreal.EditorAssetLibrary.set_metadata_tag(s,tag,module)
    for name,(typ,expr) in values.items():put(s,e,script,module,name,'(HlslExpression="'+expr+'")','/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')

def material():
    m=duplicate('/Game/NiagaraExamples/Materials/MI_FireBall_8x8','MI_FireballCore')
    names={str(n) for n in LIB.get_scalar_parameter_names(m)}
    for key,value in [('Near Fade Distance',10),('Depth Fade Distance',4),('Emissive Gain',2),('Opacity Gain',.8)]:
        if key in names:LIB.set_material_instance_scalar_parameter_value(m,key,value)
    LIB.update_material_instance(m);save(m);return m

def core(m):
    source=unreal.load_asset('/Game/NiagaraExamples/FX_Misc/NS_Fire')
    source_emitters=emitters(source)
    loop=None;mode=None
    for e in source_emitters:
        top=API.call_method('GetEmitterTopology',(ref(source,e),))
        modules=top.get_editor_property('emitter_update_script').get_editor_property('modules')
        if any(str(v.get_editor_property('module_name'))=='EmitterState' for v in modules):
            loop=unreal.RainAssetEditor.read_input(source,e,'EmitterUpdateScript','EmitterState','Loop Behavior')
            mode=unreal.RainAssetEditor.read_input(source,e,'EmitterUpdateScript','EmitterState','Life Cycle Mode')
            break
    if not loop or not mode:raise RuntimeError('No source loop configuration in NS_Fire')
    s=duplicate('/Game/NiagaraExamples/FX_Misc/NS_Fire','NS_FireballCore')
    en='FireballCore'
    if en not in emitters(s):API.call_method('AddEmitter',(s,unreal.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'),en))
    for e in emitters(s):
        if e!=en:API.call_method('RemoveEmitter',(ref(s,e),))
    setdata('SetEmitterData',unreal.NiagaraExt_EmitterData,ref(s,en),{'bLocalSpace':True})
    setdata('SetRendererData',unreal.NiagaraExt_RendererData,ref(s,en,renderer=0),{'Material':m.get_path_name(),'SubImageSize':{'X':8,'Y':8},'bSubImageBlend':True})
    put(s,en,'EmitterUpdateScript','EmitterState','Life Cycle Mode',mode.replace('NewEnumerator0','NewEnumerator1').replace('"System"','"Self"'),'/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    put(s,en,'EmitterUpdateScript','EmitterState','Loop Behavior',loop,'/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    top=API.call_method('GetEmitterTopology',(ref(s,en),))
    modules=top.get_editor_property('emitter_update_script').get_editor_property('modules')
    for mod in modules:
        name=str(mod.get_editor_property('module_name'))
        if 'SpawnBurst' in name:API.call_method('RemoveModule',(ref(s,en,'EmitterUpdateScript',name),))
    if not any(str(v.get_editor_property('module_name'))=='SpawnRate' for v in modules):API.call_method('AddModule',(ref(s,en,'EmitterUpdateScript'),unreal.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
    put(s,en,'EmitterUpdateScript','SpawnRate','SpawnRate','(Value=4)')
    f='/Script/Niagara.NiagaraFloat';v='/Script/CoreUObject.Vector2f';pos='/Script/Niagara.NiagaraPosition';col='/Script/CoreUObject.LinearColor'
    assignments(s,en,'ParticleSpawnScript',{'Particles.Lifetime':(f,'.65'),'Particles.Position':(pos,'float3(0,0,0)'),'Particles.SpriteSize':(v,'float2(34,34)'),'Particles.Color':(col,'float4(1,.65,.3,.85)')})
    assignments(s,en,'ParticleUpdateScript',{'Particles.Position':(pos,'float3(0,0,0)'),'Particles.SpriteSize':(v,'float2(34,34) * (1.0 + .06*sin(Particles.Age*12.0))'),'Particles.Color':(col,'float4(1,.65,.3,.85 * saturate(Particles.NormalizedAge*7) * saturate((1-Particles.NormalizedAge)*5))')})
    s.set_editor_property('fixed_bounds',unreal.Box(min=unreal.Vector(-65,-65,-65),max=unreal.Vector(65,65,65)))
    save(s)

def trail(m):
    s=duplicate('/Game/NiagaraExamples/FX_Weapons/Trails/NS_RocketTrail','NS_FireballTrail')
    en='RocketTrail'
    if en not in emitters(s):raise RuntimeError('RocketTrail source emitter changed: '+str(emitters(s)))
    for e in emitters(s):
        if e!=en:API.call_method('RemoveEmitter',(ref(s,e),))
    setdata('SetRendererData',unreal.NiagaraExt_RendererData,ref(s,en,renderer=0),{'Material':m.get_path_name(),'SubImageSize':{'X':8,'Y':8},'bSubImageBlend':True})
    f='/Script/Niagara.NiagaraFloat';v='/Script/CoreUObject.Vector2f';col='/Script/CoreUObject.LinearColor'
    assignments(s,en,'ParticleSpawnScript',{'Particles.Lifetime':(f,'.22'),'Particles.SpriteSize':(v,'float2(24,24)'),'Particles.Color':(col,'float4(1,.42,.08,.65)')})
    assignments(s,en,'ParticleUpdateScript',{'Particles.SpriteSize':(v,'float2(24,24)*(1-Particles.NormalizedAge*.7)'),'Particles.Color':(col,'float4(1,.42,.08,.55*(1-Particles.NormalizedAge))')})
    save(s)

def explosion():
    s=duplicate('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small','NS_FireballExplosion')
    names=emitters(s);unreal.log('FIREBALL_EXPLOSION_SOURCE '+str(names))
    for en in names:
        if any(x in en.lower() for x in ['debris','ground','postprocess','decal','camera']):API.call_method('RemoveEmitter',(ref(s,en),))
    save(s)

def shockwave():
    name='M_FireballShockwave'
    m=unreal.load_asset(DEST+'/'+name) if unreal.EditorAssetLibrary.does_asset_exist(DEST+'/'+name) else TOOLS.create_asset(name,DEST,unreal.Material,unreal.MaterialFactoryNew())
    LIB.delete_all_material_expressions(m)
    m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_ADDITIVE);m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('two_sided',True);m.set_editor_property('disable_depth_test',False)
    uv=LIB.create_material_expression(m,unreal.MaterialExpressionTextureCoordinate)
    opacity=LIB.create_material_expression(m,unreal.MaterialExpressionScalarParameter);opacity.set_editor_property('parameter_name','Opacity');opacity.set_editor_property('default_value',1)
    shape=LIB.create_material_expression(m,unreal.MaterialExpressionCustom);shape.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    shape.set_editor_property('code','float r=length((UV-.5)*2); return exp(-abs(r-.91)*55)*saturate(1-r)*10*Alpha;')
    pins=[]
    for name in ['UV','Alpha']:
        pin=unreal.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    shape.set_editor_property('inputs',pins);LIB.connect_material_expressions(uv,'',shape,'UV');LIB.connect_material_expressions(opacity,'',shape,'Alpha')
    color=LIB.create_material_expression(m,unreal.MaterialExpressionConstant3Vector);color.set_editor_property('constant',unreal.LinearColor(4,.52,.035))
    LIB.connect_material_property(color,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR);LIB.connect_material_property(shape,'',unreal.MaterialProperty.MP_OPACITY)
    LIB.recompile_material(m);save(m)

def audio():
    task=unreal.AssetImportTask();task.set_editor_property('filename',str(ROOT/'SourceAssets/Fireball20260914/fireball_hit.wav'))
    task.set_editor_property('destination_path',DEST);task.set_editor_property('destination_name','S_FireballImpact')
    task.set_editor_property('automated',True);task.set_editor_property('replace_existing',True);task.set_editor_property('save',True)
    TOOLS.import_asset_tasks([task])
    a=unreal.load_asset(DEST+'/S_FireballImpact')
    if not a:raise RuntimeError('Fireball impact import failed')
    save(a)

if __name__ == '__main__':
    m=material();core(m);trail(m);explosion();shockwave();audio()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_fireball_flames import build as build_flames
    build_flames()
    from build_fireball_flight import build as build_flight
    build_flight()
    from build_fireball_slow_burn import build as build_slow_burn
    build_slow_burn()
    from build_fireball_outer_flame import build as build_outer_flame
    build_outer_flame()
    from build_fireball_fluid_burn import build as build_fluid_burn
    build_fluid_burn()
    from build_fireball_impact_realistic import build as build_impact_realistic
    build_impact_realistic()
    # Latest combustion replaces the old fluid body at the same runtime paths.
    from build_fireball_torch_burn import run as build_torch_burn
    for stage in ('materials', 'install_core', 'install_trail'):
        build_torch_burn(stage)
    out=ROOT/'SourceAssets/Fireball20260914';out.mkdir(parents=True,exist_ok=True)
    (out/'created-assets.json').write_text(json.dumps(CREATED,indent=2),encoding='utf-8')
    unreal.log('FIREBALL_ASSETS_CREATED')
