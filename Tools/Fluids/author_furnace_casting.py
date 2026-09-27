"""Import/save the repaired furnace casting effect, without opening an editor or PIE.

Primary liquid is one 2,112-triangle surface (continuous tube + horizontal mould pool).
Niagara only supplies bounded ballistic droplets. CPU detail tokens cannot erase liquid.
Run after build_furnace_casting_mesh.py; preserve older failed assets as source history.
"""
import datetime
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
OUT = ROOT / 'SourceAssets/FurnaceCasting20260926'
DEST = '/Game/Fluids/FurnaceCasting20260926'
sys.path[:0] = [str(ROOT / 'Tools/Skills'), str(ROOT / 'Tools/Fluids')]
from furnace_material_graph import node, wire, prop, scalar, custom

E, L, A = u.EditorAssetLibrary, u.MaterialEditingLibrary, u.AssetToolsHelpers.get_asset_tools()
SAVED = []
TAG = 'FurnaceCasting20260926.v2'

def save(asset):
    if isinstance(asset, u.Material):
        L.recompile_material(asset)
    if isinstance(asset, u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(asset):
        raise RuntimeError('Niagara compilation failed: ' + asset.get_path_name())
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save: ' + asset.get_path_name())
    SAVED.append(asset.get_path_name())
    print('FURNACE_CASTING_SAVED', asset.get_path_name(), flush=True)

def own_material(name):
    path = DEST + '/' + name
    m = u.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name, DEST, u.Material, u.MaterialFactoryNew())
    if not m:
        raise RuntimeError(path)
    return m

def c(m, value):
    n = node(m, u.MaterialExpressionConstant)
    n.set_editor_property('r', value)
    return n

def solid_material(name, pool):
    m = own_material(name)
    if E.get_metadata_tag(m, TAG) == 'complete':
        return m
    # These are new task-owned graphs; stable version metadata makes rebuilds idempotent.
    m.set_editor_property('blend_mode', u.BlendMode.BLEND_MASKED)
    m.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    m.set_editor_property('two_sided', True)
    uv = node(m, u.MaterialExpressionTextureCoordinate)
    clock = node(m, u.MaterialExpressionTime)
    start = scalar(m, 'CastingStartTime', 0)
    start.set_editor_property('use_custom_primitive_data', True)
    start.set_editor_property('primitive_data_index', 0)
    seed = scalar(m, 'CastingSeed', .5)
    seed.set_editor_property('use_custom_primitive_data', True)
    seed.set_editor_property('primitive_data_index', 1)
    rate = scalar(m, 'CastingTimeRate', 1)
    rate.set_editor_property('use_custom_primitive_data', True)
    rate.set_editor_property('primitive_data_index', 2)
    offset = scalar(m, 'CastingAgeOffset', 0)
    offset.set_editor_property('use_custom_primitive_data', True)
    offset.set_editor_property('primitive_data_index', 3)
    age = custom(m, 'return max(0,(T-Start)*Rate+Offset);', {'T': clock, 'Start': start, 'Rate':rate, 'Offset':offset})
    field = custom(m, '''
float2 q=UV*float2(8,5);
float w=sin(q.x*3.1-Age*18+Seed*6.28 + .8*sin(q.y*4+Age*4));
float v=sin(q.x*7.7-q.y*4.1-Age*27)*.22;
return saturate(.5+.35*w+v);
''', {'UV': uv, 'Age': age, 'Seed': seed})
    heat = custom(m, 'return 1-smoothstep(3.5,5.4,Age);', {'Age': age}) if pool else c(m, 1)
    emissive = custom(m, '''
float3 hot=lerp(float3(1,.19,.012),float3(1,.72,.19),F);
float3 warm=lerp(float3(.35,.006,.001),hot,Heat*Heat);
return warm*(.05+16*Heat)*(.72+.28*F);
''', {'F': field, 'Heat': heat}, 3)
    base = custom(m, 'return lerp(float3(.085,.046,.024),float3(.38,.19,.055),F);', {'F': field}, 3)
    rough = custom(m, 'return .20+.12*F+(1-Heat)*.12;', {'F': field, 'Heat': heat})
    normal = custom(m, 'return normalize(float3(.12*sin(UV.x*48-Age*18),.10*cos(UV.y*31+Age*9),1));', {'UV': uv, 'Age': age}, 3)
    slab = node(m, u.MaterialExpressionSubstrateShadingModels)
    slab.set_editor_property('shading_model_override', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for output, pin, value in [('BASE_COLOR','BaseColor',base), ('METALLIC','Metallic',c(m,.82)),
                                ('ROUGHNESS','Roughness',rough), ('NORMAL','Normal',normal),
                                ('EMISSIVE_COLOR','Emissive Color',emissive)]:
        prop(m, value, output)
        wire(value, slab, pin)
    prop(m, slab, 'FRONT_MATERIAL')
    if pool:
        # Runtime swaps this cooled surface and the ingot in the same 5 Hz update.
        mask = custom(m, 'return step(.4777,Age);', {'Age':age})
        offset = custom(m, '''
float fill=smoothstep(.4777,3.2,Age);
float edge=saturate(1-pow(abs(UV.x-.5)*2,6))*saturate(1-pow(abs(UV.y-.5)*2,6));
float r=length((UV-.5)*float2(1.8,1));
float ripple=.15*sin(r*44-Age*20)*exp(-r*3)*edge*Heat;
return float3(0,0,-3.8*(1-fill)-1.25*(1-Heat)+ripple);
''', {'UV':uv, 'Age':age, 'Heat':heat}, 3)
    else:
        mask = custom(m, 'float travel=UV.x*.4776727; return step(travel,Age)*(1-step(3.2+travel,Age));', {'UV':uv,'Age':age})
        n = node(m, u.MaterialExpressionVertexNormalWS)
        offset = custom(m, '''
float fill=smoothstep(.4777,3.2,Age);
float3 pulse=N*(.11*sin(UV.x*55-Age*24)+.04*sin(UV.x*113-Age*39))*sin(UV.x*3.14159265);
return pulse+float3(0,0,-3.8*(1-fill)*smoothstep(.85,1,UV.x));
''', {'N':n,'UV':uv,'Age':age},3)
    prop(m, mask, 'OPACITY_MASK')
    prop(m, offset, 'WORLD_POSITION_OFFSET')
    E.set_metadata_tag(m, TAG, 'complete')
    save(m)
    return m

def spark_material():
    m = own_material('M_CastingDroplet')
    if E.get_metadata_tag(m, TAG) == 'complete':
        return m
    m.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE)
    m.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('used_with_niagara_sprites', True)
    m.set_editor_property('two_sided', True)
    uv = node(m, u.MaterialExpressionTextureCoordinate)
    color = node(m, u.MaterialExpressionParticleColor)
    alpha = custom(m, 'float2 q=(UV-.5)*2;return saturate(1-dot(q,q))*Alpha;', {'UV':uv,'Alpha':(color,'A')})
    emissive = custom(m, 'return Tint*12;', {'Tint':(color,'RGB')},3)
    prop(m, emissive, 'EMISSIVE_COLOR')
    prop(m, alpha, 'OPACITY')
    slab = node(m, u.MaterialExpressionSubstrateShadingModels)
    slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_UNLIT)
    wire(emissive,slab,'Emissive Color'); wire(alpha,slab,'Opacity')
    prop(m,slab,'FRONT_MATERIAL')
    E.set_metadata_tag(m,TAG,'complete');save(m)
    return m

def import_mesh(stream, pool):
    name = 'SM_FurnaceCastingSurface'
    options = u.FbxImportUI()
    options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    options.import_mesh=True; options.import_as_skeletal=False
    options.import_materials=False; options.import_textures=False
    data=options.static_mesh_import_data
    data.combine_meshes=True;data.auto_generate_collision=False
    data.generate_lightmap_u_vs=False;data.transform_vertex_to_absolute=True
    data.convert_scene=True;data.convert_scene_unit=True
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task=u.AssetImportTask()
    task.filename=str(OUT/(name+'.fbx'));task.destination_path=DEST;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False;task.options=options;task.factory=u.FbxFactory()
    A.import_asset_tasks([task])
    mesh=u.load_asset(DEST+'/'+name)
    if not mesh:raise RuntimeError('Casting FBX import failed')
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        label=str(slot.get_editor_property('material_slot_name'))
        if label=='CastingStream':mesh.set_material(i,stream)
        elif label=='CastingPool':mesh.set_material(i,pool)
        else:raise RuntimeError('Unexpected casting slot '+label)
    save(mesh)
    return mesh

def sparks(mat):
    from build_fireball_assets import API, ref, setdata, put, assignments
    from build_fireball_flames import FLOAT, VEC2, VEC3, POSITION, COLOR
    from build_fireball_flight import user_parameter
    from author_furnace_tap_metal import ensure_emitter
    name='NS_CastingDroplets';path=DEST+'/'+name;emitter='FurnaceCastingDropletEmitter'
    s=u.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,DEST,u.NiagaraSystem,u.NiagaraSystemFactoryNew())
    existing=str(API.call_method('GetUserVariables',(s,)).export_text())
    for p in ['Flow','SparkGate','DetailReduction','ImpactHeight']:
        if 'User.'+p not in existing:user_parameter(s,p,FLOAT)
    for script in ['ParticleSpawnScript','ParticleUpdateScript','EmitterUpdateScript']:
        E.remove_metadata_tag(s,'Fireball.Assignments.'+emitter+'.'+script)
    ensure_emitter(s,emitter)
    put(s,emitter,'EmitterUpdateScript','SpawnRate','SpawnRate',
        '(HlslExpression="12*saturate(User.Flow)*saturate(User.SparkGate)*(1-saturate(User.DetailReduction))")',
        '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    setdata('SetRendererData',u.NiagaraExt_RendererData,ref(s,emitter,renderer=0),{
        'Material':mat.get_path_name(),'MaterialUserParamBinding':{'Parameter':{'Name':'None'}},
        'SubImageSize':{'X':1,'Y':1},'bSubImageBlend':False,'Alignment':'Unaligned','FacingMode':'FaceCamera',
        'CutoutTexture':None,'bUseMaterialCutoutTexture':False,'bCastShadows':False,
        'bEnableCameraDistanceCulling':True,'MinCameraDistance':0,'MaxCameraDistance':3500})
    seed='frac(float(Particles.UniqueID)*.61803398875)'
    var='frac(float(Particles.UniqueID)*.41421356237)'
    a='Particles.Age';n='Particles.NormalizedAge'
    position=f'float3(45+cos({seed}*6.2831853)*(12+20*{var})*{a},sin({seed}*6.2831853)*(12+20*{var})*{a},User.ImpactHeight+(48+35*{var})*{a}-300*{a}*{a})'
    life=f'((48+35*{var})/300)'  # end on the real surface, no old-position clamp
    color=f'float4(1,.36+.3*(1-{n}),.035,(1-{n})*(1-{n}))'
    common={'Particles.Position':(POSITION,position),'Particles.Velocity':(VEC3,'float3(0,0,0)'),
        'Particles.SpriteSize':(VEC2,f'float2(.45,.75)*(.75+{var}*.5)'),
        'Particles.SpriteRotation':(FLOAT,'0'),'Particles.SpriteUVScale':(VEC2,'float2(1,1)'),
        'Particles.Color':(COLOR,color)}
    assignments(s,emitter,'ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,life),**common})
    assignments(s,emitter,'ParticleUpdateScript',common)
    E.set_metadata_tag(s,TAG,'Ballistic droplets only; liquid surface is an independent mesh')
    save(s)
    return s

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(p.startswith(DEST+'/') for p in dirty):raise RuntimeError('Unsaved casting target packages; preserve them')
    E.make_directory(DEST)
    stream=solid_material('M_CastingStream',False)
    pool=solid_material('M_CastingPool',True)
    mat=spark_material();mesh=import_mesh(stream,pool);ns=sparks(mat)
    result={'saved':SAVED,'mesh':mesh.get_path_name(),'niagara':ns.get_path_name(),
        'geometry':json.loads((OUT/'geometry.json').read_text(encoding='utf8')),
        'timing_seconds':{'stream_stop':3.2,'last_liquid_arrival':3.6777,'solid_ingot':5.4},
        'primitive_data':{'0':'world game start time','1':'per-event seed'},
        'budget':{'casting_components':4,'triangles_per_cast':2112,'droplet_rate':12,'droplet_max_lifetime':.277,'ingot_components_max':32},
        'status':'authored_compiled_saved','runtime_tested':False,'visually_tested':False}
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    (OUT/('receipt-'+stamp+'.json')).write_text(json.dumps(result,indent=2),encoding='utf8')
    (OUT/'assets.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print('FURNACE_CASTING_COMPLETE',flush=True)

if __name__=='__main__':main()
