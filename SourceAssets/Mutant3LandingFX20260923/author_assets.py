"""Author a pooled ground-sector material from owned Easy Impact Frames resources.

The screen-facing demo manager is not instantiated. Only our two assets are saved.
No level, gameplay, screenshots or rendered acceptance are run.
"""
import unreal as u, json, shutil
from pathlib import Path

ROOT=Path(__file__).parent
PROJECT=Path(u.Paths.project_dir()).resolve()
DEST='/Game/Monsters/Mutant3Meshy/Effects'
FAB='/Game/Vefects/Easy_Impact_Frames/VFX/Extras/Materials/Shockwaves/M_VFX_Shockwave_01'
SOUND='/Game/Monsters/HandBrain/Audio/S_HandBrain_slam'
LIB=u.MaterialEditingLibrary
TOOLS=u.AssetToolsHelpers.get_asset_tools()
EL=u.EditorAssetLibrary
state={'state':'authoring','saved':[],'gameplay_tested':False,'visual_tested':False}

def record():
    (ROOT/'assets_saved.json').write_text(json.dumps(state,indent=2),encoding='utf-8')

def protect(path):
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if path in dirty:raise RuntimeError('Unsaved target asset: '+path)
    relative=Path(path.removeprefix('/Game/')).with_suffix('.uasset')
    src=PROJECT/'Content'/relative
    dst=ROOT/'before_content'/relative
    if src.exists() and not dst.exists():
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)

def save(asset):
    if not EL.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
    state['saved'].append(asset.get_path_name())
    record()

def author():
    master=u.load_asset(FAB)
    samples={}
    for expr in LIB.get_material_expressions(master):
        if isinstance(expr,u.MaterialExpressionTextureSampleParameter2D):
            samples[str(expr.get_editor_property('parameter_name'))]=expr
    # Use the Fab author's actual texture resources and matching sampler types.
    if 'Noise Texture' not in samples or 'Intensity Mask' not in samples:
        raise RuntimeError('Missing source shockwave texture inputs')
    name='M_Mutant3LandingWave'
    path=DEST+'/'+name
    protect(path)
    mat=u.load_asset(path) if EL.does_asset_exist(path) else TOOLS.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    LIB.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided',True)
    mat.set_editor_property('disable_depth_test',False)
    LIB.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)

    def node(cls,**values):
        n=LIB.create_material_expression(mat,cls)
        for key,value in values.items():n.set_editor_property(key,value)
        return n

    def connect(src,dst,pin,output=''):
        if isinstance(pin,int):pin=str(LIB.get_material_expression_input_names(dst)[pin])
        if not LIB.connect_material_expressions(src,output,dst,pin):
            raise RuntimeError('Material connection failed: '+pin)

    def custom(code,inputs,kind=u.CustomMaterialOutputType.CMOT_FLOAT1):
        pins=[]
        for key in inputs:
            p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
        n=node(u.MaterialExpressionCustom,code=code,inputs=pins,output_type=kind)
        for key,(src,output) in inputs.items():connect(src,n,key,output)
        return n

    def instance(index,default):
        n=node(u.MaterialExpressionPerInstanceCustomData,data_index=index,const_default_value=default)
        result=node(u.MaterialExpressionVertexInterpolator)
        connect(n,result,0)
        return result

    # The 100 cm Engine plane's local +X is the landing heading. Derive UV from
    # actual local vertices so imported UV rotation cannot turn the sector.
    position=node(u.MaterialExpressionPreSkinnedPosition)
    local_position=node(u.MaterialExpressionVertexInterpolator)
    connect(position,local_position,0)
    uv=custom('return Position.xy/100.0+.5;',{'Position':(local_position,'')},u.CustomMaterialOutputType.CMOT_FLOAT2)
    life=instance(4,0.)
    alpha=instance(3,.5)
    half_cos=instance(5,.5)
    rgb=node(u.MaterialExpressionPerInstanceCustomData3Vector,data_index=0,const_default_value=u.LinearColor(.65,.62,.56,1))
    color=node(u.MaterialExpressionVertexInterpolator)
    connect(rgb,color,0)
    noise_uv=custom('return UV*2.4+float2(Life*.22,-Life*.12);',
                    {'UV':(uv,''),'Life':(life,'')},u.CustomMaterialOutputType.CMOT_FLOAT2)
    mask_uv=custom('float2 p=(UV-.5)*2; return float2(atan2(p.y,p.x)/6.2831853+.5,saturate(length(p)));',
                   {'UV':(uv,'')},u.CustomMaterialOutputType.CMOT_FLOAT2)
    textures={}
    for key,coords in [('Noise Texture',noise_uv),('Intensity Mask',mask_uv)]:
        source=samples[key]
        tex=node(u.MaterialExpressionTextureSample,texture=source.get_editor_property('texture'),
                 sampler_type=source.get_editor_property('sampler_type'))
        connect(coords,tex,'UVs')
        textures[key]=tex
    mask=custom('''
float2 p=(UV-.5)*2;
float r=length(p);
float expansion=.10+.88*(1-pow(1-saturate(Life),2));
float noisyRadius=r+(Noise-.5)*.038;
float ring=1-smoothstep(.035,.115,abs(noisyRadius-expansion));
float sector=smoothstep(HalfCos,HalfCos+.055,p.x/max(r,.0001));
float edge=1-smoothstep(.97,1.0,r);
return saturate(ring*sector*edge*(.30+.70*Noise)*(.45+.55*Mask)*Alpha);
''',{'UV':(uv,''),'Life':(life,''),'Alpha':(alpha,''),'HalfCos':(half_cos,''),
     'Noise':(textures['Noise Texture'],'R'),'Mask':(textures['Intensity Mask'],'R')})
    fade=node(u.MaterialExpressionDepthFade,fade_distance_default=5.)
    connect(mask,fade,'Opacity')
    LIB.connect_material_property(fade,'',u.MaterialProperty.MP_OPACITY)
    LIB.connect_material_property(color,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    surface=node(u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_UNLIT)
    connect(color,surface,'Emissive Color')
    connect(fade,surface,'Opacity')
    if not LIB.connect_material_property(surface,'',u.MaterialProperty.MP_FRONT_MATERIAL):
        raise RuntimeError('Could not connect the project\'s active Substrate output')
    EL.set_metadata_tag(mat,'Source','Easy Impact Frames by Vefects: shockwave noise and intensity mask; ground sector adapted for Mutant3')
    errors=LIB.recompile_material(mat)
    if errors:raise RuntimeError('Material compile: '+str(errors))
    save(mat)
    sound_path=DEST+'/S_Mutant3PounceImpact'
    protect(sound_path)
    sound=u.load_asset(sound_path) if EL.does_asset_exist(sound_path) else EL.duplicate_asset(SOUND,sound_path)
    if not sound:raise RuntimeError('Missing slam audio')
    EL.set_metadata_tag(sound,'Source','Existing project S_HandBrain_slam; original PCM retained; Mutant3 uses 1.08-1.14 pitch and positional attenuation')
    save(sound)
    state.update({'state':'Production ground-wave material and impact sound saved',
        'source_material':FAB,'source_sound':SOUND,'duration_seconds':sound.get_editor_property('duration'),
        'source_listing':'https://www.fab.com/listings/15cb7c95-3220-43fe-8d68-c67c73e83eba',
        'scope':'Uses owned Fab shockwave textures; pooled native ground-sector presentation; no demo Blueprint or looping Niagara system'})
    record()
    print('MUTANT3_LANDING_ASSETS_SAVED '+json.dumps(state),flush=True)

try:author()
except Exception as e:
    state.update({'state':'authoring interrupted','error':str(e)})
    record()
    raise
