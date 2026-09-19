"""Author only the V7 overflow assets. Does not edit the accepted basin water or level.

Run with UnrealEditor-Cmd -run=pythonscript -script=<this file> -unattended -NullRHI.
Material/Niagara compilation is part of authoring; no preview or runtime test is run.
"""
import json
import math
from pathlib import Path
import unreal as u

ROOT = '/Game/Props/RomanFountain20260917/OverflowV7'
M = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
API = u.get_default_object(u.NiagaraToolset_System)
RECEIPT = []
# Centimetres, already at the approved 2x scale. A short lip follows the stone;
# the free sheet then follows r=r0+vr*t, z=z0-vz*t-g*t*t/2.
FALLS = [
    dict(lip=[(160,573),(174,573),(177,568)], bottom=412, radial=45, angular=96, rows=16),
    dict(lip=[(248,429),(263,426),(268,416)], bottom=148, radial=32, angular=96, rows=24),
    dict(lip=[(392,165),(406,158),(415,140)], bottom=40, radial=20, angular=128, rows=12),
    dict(lip=[(440,41),(443,39)], bottom=20, radial=24, angular=96, rows=4),
]
for fall in FALLS:
    fall['duration'] = (math.sqrt(40**2 + 1960*(fall['lip'][-1][1]-fall['bottom']))-40)/980
    fall['landing'] = fall['lip'][-1][0] + fall['radial']*fall['duration']


def save(asset):
    if isinstance(asset, u.Material):
        errors = M.recompile_material(asset)
        if errors:
            raise RuntimeError(str(errors))
    if isinstance(asset, u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(asset):
        raise RuntimeError('Niagara compilation failed: '+asset.get_path_name())
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save '+asset.get_path_name())
    RECEIPT.append(asset.get_path_name())
    u.log('FOUNTAIN_V7_AUTHORED '+asset.get_path_name())


def node(mat, cls):
    return M.create_material_expression(mat, cls)


def wire(a, b, pin, output=''):
    if not M.connect_material_expressions(a, output, b, pin):
        raise RuntimeError('Material connection failed: '+pin)


def prop(n, name, output=''):
    if not M.connect_material_property(n, output, getattr(u.MaterialProperty, 'MP_'+name)):
        raise RuntimeError('Material output failed: '+name)


def scalar(mat, name, value):
    n = node(mat, u.MaterialExpressionScalarParameter)
    n.set_editor_property('parameter_name', name)
    n.set_editor_property('default_value', value)
    return n


def custom(mat, code, inputs, kind=1):
    n = node(mat, u.MaterialExpressionCustom)
    n.set_editor_property('code', code)
    n.set_editor_property('output_type', getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT'+str(kind)))
    pins = []
    for key in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', key)
        pins.append(pin)
    n.set_editor_property('inputs', pins)
    for key, source in inputs.items():
        wire(source, n, key)
    return n


def new_material(name):
    path = ROOT+'/'+name
    existing = u.load_asset(path) if E.does_asset_exist(path) else None
    if existing:
        return existing, False  # Never clear a graph already referenced by a saved mesh.
    E.make_directory(ROOT)
    mat = TOOLS.create_asset(name, ROOT, u.Material, u.MaterialFactoryNew())
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property('translucency_lighting_mode', u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    mat.set_editor_property('two_sided', True)
    return mat, True


def sheet_material(name, detailed):
    mat, fresh = new_material(name)
    if not fresh:
        return mat
    uv = node(mat, u.MaterialExpressionTextureCoordinate)
    meta = node(mat, u.MaterialExpressionTextureCoordinate)
    meta.set_editor_property('coordinate_index', 1)  # tier index and ballistic travel time
    time = node(mat, u.MaterialExpressionTime)
    phase = scalar(mat, 'InstancePhase', 0)
    clock = custom(mat, 'return T+Phase;', {'T':time, 'Phase':phase})
    # Integral angular frequencies avoid a seam at the rear meridian. Flow uses
    # time of flight, not linear height, so its world velocity accelerates downwards.
    field = custom(mat, '''
float a=UV.x*6.2831853;
float f=saturate(UV.y);
float travel=f*Meta.y;
float q=T-travel+Meta.x*.713;
float pulse=sin(a*19+sin(a*7)*1.1+q*12);
float warp=sin(a*11-q*7.1)+.45*sin(a*29+q*10.3);
float band=.5+.5*sin(a*31+warp*.7);
float holes=smoothstep(.23,.61,band+.19*pulse);
float coverage=lerp(1,holes,smoothstep(.1,.88,f));
float foam=pow(saturate(.5+.5*pulse),5)*(.08+.3*f);
return float4(coverage,foam,warp,pulse);
''', {'UV':uv, 'Meta':meta, 'T':clock}, 4)
    if not detailed:
        field = custom(mat, '''
float a=UV.x*6.2831853;
float f=saturate(UV.y);
float p=sin(a*23+Meta.x*1.9+(T-f*Meta.y)*9);
return float4(lerp(1,smoothstep(-.4,.4,p),f*.65),.04,0,p);
''', {'UV':uv, 'Meta':meta, 'T':clock}, 4)
    # UV-derived radial direction is in mesh local space. Transform the offset
    # as a VECTOR so rotated/moved building prefabs retain the same motion.
    displacement = custom(mat, '''
float a=UV.x*6.2831853;
float f=saturate(UV.y);
float envelope=smoothstep(0,.28,f)*(.4+.6*f);
float radial=envelope*(1.3+.65*F.z)*Amplitude;
float tangential=envelope*F.w*Amplitude*.2;
return float3(cos(a)*radial-sin(a)*tangential,
              sin(a)*radial+cos(a)*tangential,0);
''', {'UV':uv,'F':field,'Amplitude':scalar(mat,'WaveAmplitude',2.8 if detailed else .6)}, 3)
    transform = node(mat, u.MaterialExpressionTransform)
    transform.set_editor_property('transform_source_type', u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL)
    transform.set_editor_property('transform_type', u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    wire(displacement, transform, '')
    prop(transform, 'WORLD_POSITION_OFFSET')
    color = custom(mat, 'return lerp(float3(.16,.26,.29),float3(.72,.80,.81),F.y);', {'F':field}, 3)
    prop(color, 'BASE_COLOR')
    prop(scalar(mat,'Roughness',.13 if detailed else .2),'ROUGHNESS')
    prop(scalar(mat,'Specular',.5),'SPECULAR')
    normal = custom(mat, 'return normalize(float3(F.z*.19,F.w*.13,1));', {'F':field}, 3)
    prop(normal,'NORMAL')
    fresnel = node(mat,u.MaterialExpressionFresnel)
    fresnel.set_editor_property('exponent',4.0)
    alpha = custom(mat, '''
float edge=saturate((1-UV.y)*24);
return F.x*edge*min(.68,Base+Fresnel*.26+F.y*.34);
''',{'UV':uv,'F':field,'Fresnel':fresnel,'Base':scalar(mat,'OpacityBase',.22 if detailed else .32)})
    fade = node(mat,u.MaterialExpressionDepthFade)
    fade.set_editor_property('fade_distance_default',3.0)
    wire(alpha,fade,'Opacity')
    prop(fade,'OPACITY')
    # No broad white emissive or scene-colour refraction pass.
    save(mat)
    return mat


def mesh_asset(material):
    path=ROOT+'/SM_FountainOverflowV7'
    existing=u.load_asset(path) if E.does_asset_exist(path) else None
    if existing and E.get_metadata_tag(existing,'FountainV7Complete')=='2':
        return existing
    vertices=[]; normals=[]; uv0=[]; uv1=[]; triangles=[]
    for tier,fall in enumerate(FALLS):
        r0,z0=fall['lip'][-1]
        profile=[(r,z,-.08*(len(fall['lip'])-1-i)) for i,(r,z) in enumerate(fall['lip'][:-1])]
        for j in range(fall['rows']+1):
            f=j/fall['rows']; t=f*fall['duration']
            profile.append((r0+fall['radial']*t,z0-40*t-490*t*t,f))
        n=fall['angular']; start=len(vertices)
        for j,(r,z,f) in enumerate(profile):
            prev=profile[max(0,j-1)]; nxt=profile[min(len(profile)-1,j+1)]
            dr=nxt[0]-prev[0]; dz=nxt[1]-prev[1]; length=math.hypot(dr,dz)
            for i in range(n+1):
                a=math.tau*i/n; c=math.cos(a); s=math.sin(a)
                vertices.append(u.Vector(r*c,r*s,z))
                normals.append(u.Vector(-dz*c/length,-dz*s/length,dr/length))
                uv0.append(u.Vector2D(i/n,f)); uv1.append(u.Vector2D(tier,fall['duration']))
        for j in range(len(profile)-1):
            for i in range(n):
                a=start+j*(n+1)+i; b=a+n+1
                triangles.extend([u.IntVector(a,b,a+1),u.IntVector(a+1,b,b+1)])
    buffers=u.GeometryScriptSimpleMeshBuffers(vertices=vertices,normals=normals,uv0=uv0,uv1=uv1,triangles=triangles)
    mesh=u.DynamicMesh()
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(mesh,buffers,material_id=0)
    asset=existing or E.duplicate_asset('/Engine/BasicShapes/Plane',path)
    opts=u.GeometryScriptCopyMeshToAssetOptions()
    for key,value in dict(enable_recompute_normals=False,enable_recompute_tangents=True,
                          replace_materials=True,new_materials=[material],use_build_scale=False).items():
        opts.set_editor_property(key,value)
    _,outcome=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(mesh,asset,opts,u.GeometryScriptMeshWriteLOD())
    if outcome!=u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Could not create overflow mesh')
    editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    editor.remove_collisions(asset)
    settings=editor.get_lod_build_settings(asset,0)
    settings.set_editor_property('distance_field_resolution_scale',0.0)
    settings.set_editor_property('use_full_precision_u_vs',True)
    settings.set_editor_property('generate_lightmap_u_vs',False)  # UV1 is our travel-time data.
    editor.set_lod_build_settings(asset,0,settings)
    asset.set_editor_property('positive_bounds_extension',u.Vector(15,15,4))
    asset.set_editor_property('negative_bounds_extension',u.Vector(15,15,4))
    E.set_metadata_tag(asset,'FountainV7Complete','2')
    save(asset)
    # Editable, deterministic source data; no engine mesh dump or acceptance run.
    source=Path(__file__).with_name('overflow_v7_geometry.json')
    source.write_text(json.dumps({'falls':FALLS,'vertices':len(vertices),'triangles':len(triangles)},indent=2),encoding='utf-8')
    return asset


def spray_material():
    mat,fresh=new_material('M_FountainSprayV7')
    if not fresh:return mat
    M.set_material_usage(mat,u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES)
    mat.set_editor_property('two_sided',False)
    uv=node(mat,u.MaterialExpressionTextureCoordinate)
    color=node(mat,u.MaterialExpressionParticleColor)
    alpha=custom(mat,'''float2 p=(UV-.5)*2;
return pow(saturate(1-dot(p,p)),2)*.65;''',{'UV':uv})
    mul=node(mat,u.MaterialExpressionMultiply)
    wire(alpha,mul,'A');wire(color,mul,'B','A')
    fade=node(mat,u.MaterialExpressionDepthFade)
    fade.set_editor_property('fade_distance_default',2.)
    wire(mul,fade,'Opacity');prop(fade,'OPACITY')
    prop(color,'BASE_COLOR','RGB')
    prop(scalar(mat,'Roughness',.16),'ROUGHNESS')
    prop(scalar(mat,'Specular',.5),'SPECULAR')
    save(mat)
    return mat


def ref(system,emitter,script='',module='',renderer=-1):
    r=u.NiagaraExt_StackItemReference()
    for k,v in dict(system=system,emitter_name=emitter,script_name=script,module_name=module,renderer_index=renderer).items():
        r.set_editor_property(k,v)
    return r


def data(method,typ,r,values):
    d=typ();d.set_editor_property('property_values',json.dumps(values))
    API.call_method(method,(r,d))


def expr(s,e,sc,module,key,value):
    if not u.RainAssetEditor.set_input(s,e,sc,module,key,'/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression',
                                    '(HlslExpression="'+value+'")'):
        raise RuntimeError('Cannot author Niagara input '+key)


def assignments(s,e,sc,values):
    entries=[]
    for name,(typ,value) in values.items():
        p=u.NiagaraExt_SetParameterEntry()
        p.import_text('(Variable=(Name="'+name+'",Type=(ClassStructOrEnum="'+typ+'",UnderlyingType=2)))')
        entries.append(p)
    module=str(API.call_method('AddSetParametersModule',(ref(s,e,sc),entries)).get_editor_property('module_name'))
    for key,(_,value) in values.items():expr(s,e,sc,module,key,value)


def splash_system(material):
    path=ROOT+'/NS_FountainLandingSprayV7'
    existing=u.load_asset(path) if E.does_asset_exist(path) else None
    if existing and E.get_metadata_tag(existing,'FountainV7Complete')=='2':return existing
    # Reuse only the authored looping emitter scaffold, never edit the weather source.
    system=existing or E.duplicate_asset('/Game/Weather/VFX/NS_FPS_SurfaceSplashes',path)
    if not system:raise RuntimeError('Missing local surface-splash authoring scaffold')
    names=[str(x.get_editor_property('emitter_name')) for x in API.call_method('GetSystemSummary',(system,)).get_editor_property('emitters')]
    en='RainSplashes'
    for name in names:
        if name!=en:API.call_method('RemoveEmitter',(ref(system,name),))
    for sc,keep in [('EmitterUpdateScript',{'EmitterState','SpawnRate'}),('ParticleSpawnScript',{'InitializeParticle'}),('ParticleUpdateScript',{'ParticleState'})]:
        stack=API.call_method('GetScriptStackTopology',(ref(system,en,sc),))
        for module in stack.get_editor_property('modules'):
            name=str(module.get_editor_property('module_name'))
            if name not in keep:API.call_method('RemoveModule',(ref(system,en,sc,name),))
    data('SetEmitterData',u.NiagaraExt_EmitterData,ref(system,en),
         {'bLocalSpace':True,'SimTarget':'GPUComputeSim','bInterpolatedSpawning':False,
          'MaxGPUParticlesSpawnPerFrame':128})
    data('SetRendererData',u.NiagaraExt_RendererData,ref(system,en,renderer=0),
         {'Material':material.get_path_name(),'SubImageSize':{'X':1,'Y':1},'bSubImageBlend':False,
          'Alignment':'VelocityAligned','FacingMode':'FaceCamera','bCastShadows':False,
          'MaterialUserParamBinding':{'Parameter':{'Name':'None'}}})
    expr(system,en,'EmitterUpdateScript','SpawnRate','SpawnRate','clamp(User.SpawnRate,0.0,480.0)')
    FLOAT='/Script/Niagara.NiagaraFloat'; VEC2='/Script/CoreUObject.Vector2f'
    VEC3='/Script/CoreUObject.Vector3f'; POS='/Script/Niagara.NiagaraPosition'; COLOR='/Script/CoreUObject.LinearColor'
    seed='frac(float(Particles.UniqueID)*.61803398875)'
    variant='frac(float(Particles.UniqueID)*.41421356237)'
    tier='fmod(float(Particles.UniqueID),4.0)'
    def choose(values):return f'({tier}==0?{values[0]}:({tier}==1?{values[1]}:({tier}==2?{values[2]}:{values[3]})))'
    radius=choose([f"{f['landing']:.5f}" for f in FALLS])
    height=choose([f"{f['bottom']:.5f}" for f in FALLS])
    angle=f'({variant}*6.2831853)'
    age='Particles.Age'
    speed=f'(35+35*{seed})'
    upward=f'(100+75*{variant})'
    life=f'({upward}*2/980.0)'  # 0.204..0.357 s; terminates at the receiving surface
    r=f'({radius}+{age}*{speed})'
    position=f'float3(cos({angle})*{r},sin({angle})*{r},{height}+1+{upward}*{age}-490*{age}*{age})'
    velocity=f'float3(cos({angle})*{speed},sin({angle})*{speed},{upward}-980*{age})'
    fade='saturate(Particles.NormalizedAge*10)*saturate((1-Particles.NormalizedAge)*5)'
    common={'Particles.Position':(POS,position),'Particles.Velocity':(VEC3,velocity),
            'Particles.SpriteSize':(VEC2,f'float2(1.3+{seed}*1.5,3.0+{seed}*4.0)'),
            'Particles.Color':(COLOR,f'float4(.66,.77,.80,{fade})'),
            'Particles.SubImageIndex':(FLOAT,'0'),'Particles.SpriteRotation':(FLOAT,'0')}
    assignments(system,en,'ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,life),**common})
    assignments(system,en,'ParticleUpdateScript',common)
    system.set_editor_property('fixed_bounds',u.Box(min=u.Vector(-485,-485,10),max=u.Vector(485,485,450)))
    E.set_metadata_tag(system,'FountainV7Budget','rate<=480/s; life<=.3572s; approx<=172 live; max4 systems/world via actor budget')
    save(system)
    E.set_metadata_tag(system,'FountainV7Complete','2')
    E.save_loaded_asset(system,False)
    return system


def main():
    near=sheet_material('M_FountainOverflowNearV7',True)
    sheet_material('M_FountainOverflowFarV7',False)
    mesh_asset(near)
    splash_system(spray_material())
    out=Path(u.Paths.project_saved_dir())/'FountainOverflowV7'
    out.mkdir(parents=True,exist_ok=True)
    (out/'authoring.json').write_text(json.dumps({'assets':RECEIPT,'falls':FALLS,'runtime_tested':False},indent=2),encoding='utf-8')
    u.log('FOUNTAIN_V7_AUTHORING_COMPLETE (assets only; no runtime test)')


if __name__ == '__main__':
    main()
