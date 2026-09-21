"""V2 authoring: hex icons are external; here build torch jets and eroded meteor.

Execute one stage at a time through the project MCP bridge. Never edits source packs.
"""
import json,sys,math
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve()
sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import API,LIB,TOOLS,ref,emitters,setdata,put,assignments
from build_fireball_torch_burn import setup_emitter,save,VECTOR4
from build_fireball_flames import FLOAT,VEC2,VEC3,POSITION,COLOR
from build_fireball_flight import user_parameter
from build_fireball_slow_burn import smooth
from build_fireball_impact_realistic import custom,scalar
BASE='/Game/Skills/FireMagic20260921'
DEST=BASE+'/PolishV2'
OUT=ROOT/'SourceAssets/FireMagicPolish20260921'
OUT.mkdir(parents=True,exist_ok=True)

def own(source,name):
    path=DEST+'/'+name
    a=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else u.EditorAssetLibrary.duplicate_asset(source,path)
    if not a:raise RuntimeError(source)
    return a

def material_stage():
    for number,energy in [(1,4.8),(2,3.4)]:
        mat=own('/Game/Props/RomanColumn20260915/MI_TorchSoft_Flame%02d'%number,'MI_TorchJet%02d'%number)
        LIB.set_material_instance_parent(mat,u.load_asset('/Game/Skills/Fireball/TorchBurn20260921/M_FireballTorchErosion'))
        for name,value in [('Emissive_Intensity',energy),('DepthFade',3.),('Noise_01_Speed_X',.18),('Noise_01_Speed_Y',.56),('Noises_OpacityBoost',1.15)]:
            LIB.set_material_instance_scalar_parameter_value(mat,name,value)
        LIB.update_material_instance(mat);save(mat)
    mat=own(BASE+'/M_MeteorRock','M_MeteorCrust')
    LIB.delete_all_material_expressions(mat)
    position=LIB.create_material_expression(mat,u.MaterialExpressionPreSkinnedPosition)
    local=LIB.create_material_expression(mat,u.MaterialExpressionVertexInterpolator)
    LIB.connect_material_expressions(position,'',local,str(LIB.get_material_expression_input_names(local)[0]))
    time=LIB.create_material_expression(mat,u.MaterialExpressionTime)
    field=custom(mat,'''
float3 p=Local*.092;
p+=.24*sin(p.yzx*1.6)+.13*sin(p.zxy*3.7);
float3 cell=floor(p), f=frac(p);float d1=10,d2=10;
for(int z=-1;z<=1;z++)for(int y=-1;y<=1;y++)for(int x=-1;x<=1;x++){
 float3 q=float3(x,y,z), a=cell+q;
 float3 h=frac(sin(float3(dot(a,float3(127.1,311.7,74.7)),dot(a,float3(269.5,183.3,246.1)),dot(a,float3(113.5,271.9,124.6))))*43758.5453);
 float d=length(q+h-f);if(d<d1){d2=d1;d1=d;}else d2=min(d2,d);
}
float variation=.5+.5*sin(Local.x*.31+sin(Local.z*.47)*2+Local.y*.23);
float seam=1-smoothstep(.008,.045+variation*.018,d2-d1);
float crust=.013+.047*saturate(d1)*(.7+.3*variation);
return float4(crust*float3(1,.82,.68),seam);
''',{'Local':(local,'')},u.CustomMaterialOutputType.CMOT_FLOAT4)
    base=custom(mat,'return Field.rgb;',{'Field':(field,'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
    heat=scalar(mat,'Heat',1.)
    glow=custom(mat,'return lerp(float3(2.8,.16,.008),float3(10,1.85,.08),pow(Field.a,3))*Field.a*Heat*(.92+.08*sin(Time*2.1+Local.z*.09));',{'Field':(field,''),'Time':(time,''),'Heat':(heat,''),'Local':(local,'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
    inv=LIB.create_material_expression(mat,u.MaterialExpressionEyeAdaptationInverse)
    LIB.connect_material_expressions(glow,'',inv,str(LIB.get_material_expression_input_names(inv)[0]))
    LIB.connect_material_property(base,'',u.MaterialProperty.MP_BASE_COLOR)
    LIB.connect_material_property(inv,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.connect_material_property(scalar(mat,'Roughness',.91),'',u.MaterialProperty.MP_ROUGHNESS)
    normal=u.load_asset('/Game/EasyBuildingSystem/Textures/Environment/Stylized/Tiles/T_Tile_Rock_Cracked_001_N')
    if normal:
        node=LIB.create_material_expression(mat,u.MaterialExpressionTextureSample)
        node.set_editor_property('texture',normal);node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        LIB.connect_material_property(node,'RGB',u.MaterialProperty.MP_NORMAL)
    errors=LIB.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    save(mat)

def mesh_stage():
    model=u.ModelingService
    def done(r):
        if not r.get_editor_property('success'):raise RuntimeError(r.get_editor_property('message'))
        return r
    source=u.load_asset(BASE+'/SM_MeteorRock');bounds=source.get_bounds();scale=76./max(bounds.box_extent.x*2,bounds.box_extent.y*2,bounds.box_extent.z*2)
    r=done(model.load_mesh_from_static_mesh(source.get_path_name(),0));h=r.get_editor_property('handle')
    try:
        done(model.recenter_mesh(h,'Bounds'));done(model.scale_mesh(h,u.Vector(scale,scale,scale),u.Vector()))
        done(model.remesh(h,9000,0.,True))
        # Preserve the existing boulder's identity, then erode its formerly planar crust.
        done(model.noise(h,'',3.2,.075,921));done(model.noise(h,'',.85,.38,127))
        done(model.recenter_mesh(h,'Bounds'));done(model.recompute_normals(h,52.))
        done(model.save_mesh_to_static_mesh(h,DEST+'/SM_MeteorEroded',True,False,False,True))
    finally:model.release_mesh(h)
    mesh=u.load_asset(DEST+'/SM_MeteorEroded')
    for i in range(len(mesh.get_editor_property('static_materials'))):mesh.set_material(i,u.load_asset(DEST+'/M_MeteorCrust'))
    save(mesh)

def system(name,source='/Game/Props/RomanColumn20260915/NS_TorchFlame'):
    s=own(source,name)
    for e in emitters(s):API.call_method('RemoveEmitter',(ref(s,e),))
    return s

def torch_layer(s,name,number,rate,local,spawn,update):
    setup_emitter(s,name,u.load_asset(DEST+'/MI_TorchJet%02d'%number),rate,local)
    assignments(s,name,'ParticleSpawnScript',spawn);assignments(s,name,'ParticleUpdateScript',update)

seed='frac(float(Particles.UniqueID)*.61803398875)'
variant='frac(float(Particles.UniqueID)*.41421356237)'
n='Particles.NormalizedAge';age='Particles.Age'
def surface(size,alpha,direction='float3(0,0,1)',dissolve='.03+.82*Particles.NormalizedAge'):
    envelope=smooth('0','.06',n)+'*(1-'+smooth('.46','1',n)+')'
    return {'Particles.SpriteAlignment':(VEC3,direction),'Particles.SpriteRotation':(FLOAT,'0'),
        'Particles.SpriteSize':(VEC2,size),'Particles.SpriteUVScale':(VEC2,'float2(1,1)'),
        'Particles.SubImageIndex':(FLOAT,'0'),'Particles.Color':(COLOR,f'float4(1,lerp(.68,.16,{n}),.065,{alpha}*{envelope})'),
        'Particles.DynamicMaterialParameter':(VECTOR4,f'float4({dissolve},1,1,1)'),
        'Particles.MaterialRandom':(FLOAT,variant)}

def weapon_stage():
    s=system('NS_ArmorTorchJets')
    for name,typ in [('Fade',FLOAT),('WeaponEnd',VEC3),('WeaponStartWorld',POSITION),('WeaponEndWorld',POSITION),('PreviousStart',POSITION),('PreviousEnd',POSITION),('WeaponVelocity',VEC3),('WeaponSize',FLOAT)]:user_parameter(s,name,typ)
    # Inner tongues remain rooted along the actual blade; larger outer jets keep a short world-space wake.
    position=f'User.WeaponEnd*(.16+.82*{seed})+float3(sin({variant}*6.283)*1.7,cos({variant}*6.283)*1.7,2+{age}*22)'
    inner=surface(f'float2(10+5*{seed},23+12*{variant})*User.WeaponSize','.66*saturate(User.Fade)')
    inner.update({'Particles.Position':(POSITION,position),'Particles.Velocity':(VEC3,'float3(0,0,0)')})
    torch_layer(s,'BladeRootJets',1,85,True,{'Particles.Lifetime':(FLOAT,'.28+.20*'+variant),**inner},inner)
    direction='normalize(float3(0,0,85)-User.WeaponVelocity*.09)'
    outer=surface(f'float2(16+7*{seed},35+19*{variant})*User.WeaponSize','.32*saturate(User.Fade)',direction)
    pos=f'lerp(lerp(User.PreviousStart,User.PreviousEnd,.16+.82*{seed}),lerp(User.WeaponStartWorld,User.WeaponEndWorld,.16+.82*{seed}),{variant})'
    spawn={'Particles.Lifetime':(FLOAT,'.20+.12*'+seed),'Particles.Position':(POSITION,pos),'Particles.Velocity':(VEC3,'float3(0,0,60)+User.WeaponVelocity*.055'),**outer}
    update={'Particles.Position':(POSITION,'Particles.Position+Particles.Velocity*Engine.DeltaTime'),**outer}
    torch_layer(s,'TorchStreamingWake',2,46,False,spawn,update)
    # World-space wake needs dynamic bounds, inherited from the torch system.
    save(s)

def mantle_stage():
    s=system('NS_MeteorMantle')
    user_parameter(s,'Fade',FLOAT)
    for name,number,rate,radius,sz,opacity in [('CrustFlame',1,65,32,'float2(27,48)',.64),('Updraft',2,36,27,'float2(40,90)',.25)]:
        p=f'float3(cos({variant}*6.283)*{radius},sin({variant}*6.283)*{radius},-12+{seed}*38+{age}*48)'
        common=surface(sz+f'*(.82+.3*{seed})',str(opacity)+'*saturate(User.Fade)')
        common.update({'Particles.Position':(POSITION,p),'Particles.Velocity':(VEC3,'float3(0,0,0)')})
        torch_layer(s,name,number,rate,True,{'Particles.Lifetime':(FLOAT,'.25+.25*'+seed),**common},common)
    save(s)

def trail_stage():
    s=system('NS_MeteorPlume')
    for name,typ in [('PreviousPosition',POSITION),('CurrentPosition',POSITION),('FlightDirection',VEC3),('FlightSpeed',FLOAT),('Fade',FLOAT)]:user_parameter(s,name,typ)
    for name,number,rate,size,alpha,life in [('FireWake',1,135,'float2(48,95)',.46,'.16+.12*'+seed),('RollingHeat',2,55,'float2(80,120)',.20,'.28+.15*'+seed)]:
        direction='-User.FlightDirection'
        offset=f'float3(cos({variant}*6.283),sin({variant}*6.283),0)*(8+15*{seed})'
        common=surface(f'{size}*(.75+.4*{seed})*(1-.3*{n})',str(alpha)+'*saturate(User.Fade)',direction)
        spawn={'Particles.Lifetime':(FLOAT,life),'Particles.Position':(POSITION,f'lerp(User.PreviousPosition,User.CurrentPosition,{seed})+{offset}'),
            'Particles.Velocity':(VEC3,f'{direction}*(35+40*{seed})+{offset}*1.2'),**common}
        update={'Particles.Position':(POSITION,'Particles.Position+Particles.Velocity*Engine.DeltaTime'),**common}
        torch_layer(s,name,number,rate,False,spawn,update)
    save(s)

def ground_stage():
    s=system('NS_MeteorAfterfire')
    for name in ['Radius','Fade','Spread']:user_parameter(s,name,FLOAT)
    for name,number,rate,opacity,height in [('GroundTongues',1,140,.65,32),('GroundJetWisps',2,48,.22,58)]:
        r=f'(sqrt({seed})*User.Radius*.93*User.Spread)'
        p=f'float3(cos({variant}*6.283)*{r},sin({variant}*6.283)*{r},6+{age}*{height})'
        common=surface(f'float2(28+21*{seed},50+35*{variant})',str(opacity)+'*saturate(User.Fade)')
        common.update({'Particles.Position':(POSITION,p),'Particles.Velocity':(VEC3,'float3(0,0,0)')})
        torch_layer(s,name,number,rate,True,{'Particles.Lifetime':(FLOAT,'.42+.3*'+seed),**common},common)
    save(s)

def run(stage):
    u.EditorAssetLibrary.make_directory(DEST)
    {'materials':material_stage,'mesh':mesh_stage,'weapon':weapon_stage,'mantle':mantle_stage,'trail':trail_stage,'ground':ground_stage}[stage]()
    (OUT/(stage+'-authored.json')).write_text(json.dumps({'stage':stage,'assets':DEST,'status':'authored and saved; necessary shader/Niagara compile only','tested':False},indent=2),encoding='utf8')
    print('FIRE_MAGIC_POLISH_COMPLETE',stage)
