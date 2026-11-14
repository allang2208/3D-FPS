"""Weathering for the foreground actors only. Structural mesh bindings are never edited."""
from pathlib import Path
import types, math
import unreal as u
ROOT=Path(__file__).resolve().parent
BASE='/Game/SceneTests/FreightCameraMatch20261113'
REVISION='freight_reference_match_20261113'
L=u.MaterialEditingLibrary
helpers=(ROOT.parent/'FacilitySurfaceUpgrade20261108/assets.py').read_text('utf8').split("GRAIN='/Game/")[0]
helpers=helpers.replace('from recipe import ROOT,BASE,REVISION,canonical,resolve','').replace("SOURCE=json.loads((ROOT/'material-inputs.json').read_text('utf8'))","SOURCE={}").replace('FacilitySurface.Owner','FreightMatch.Owner')
ctx=dict(ROOT=ROOT,BASE=BASE,REVISION=REVISION,canonical=lambda p:p.split('.')[0])
exec(compile(helpers,'scene_graph','exec'),ctx)
H=types.SimpleNamespace(**ctx)
def sample(m,name,path,kind):
    tex=u.load_asset(path)
    if not tex:raise RuntimeError(path)
    return H.node(m,'TextureSampleParameter2D',parameter_name=name,texture=tex,sampler_type=kind)
def split(m,expr,color):
    n=H.node(m,'ComponentMask',r=color,g=color,b=color,a=not color);H.wire(expr,n);return n
def crate_finish():
    m=H.own('Materials/M_CrateHandledEdges')
    L.delete_all_material_expressions(m)
    base='/Game/UndergroundTunnel/Textures/Props/WoodCrate/T_WoodCrate01a_'
    albedo=sample(m,'Boards',base+'albedo',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    normal=sample(m,'WoodRelief',base+'normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    orm=sample(m,'NativeORM',base+'ORM',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    world=H.node(m,'WorldPosition')
    pos=H.node(m,'TransformPosition',transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE);H.wire(world,pos)
    code="""float3 b=abs(p-float3(0,0,53.325));
float3 d=abs(b-float3(52.,52.,53.325));
float edge=min(max(d.x,d.y),min(max(d.x,d.z),max(d.y,d.z)));
float gr=dot(C.rgb,float3(.299,.587,.114));
float fleck=saturate((gr-.035)*3.6+.24*sin(p.z*3.4+p.y*1.9)*sin(p.x*2.7+p.z));
float topRail=min(abs(p.z-96.),abs(p.z-10.));
float facing=min(d.x,d.y);
float rail=(1.-smoothstep(.12,1.05,topRail))*(1.-smoothstep(1.,4.,facing));
float worn=saturate((1.-smoothstep(.35,2.7,edge))*.9+rail*.43)*(.38+.62*fleck)*(1.-saturate(Metal));
float3 bare=lerp(C.rgb,float3(.32,.218,.135)*(.72+1.25*gr),.70);
return float4(lerp(C.rgb,bare,worn),lerp(Rough,.63+fleck*.14,worn));"""
    out=H.custom(m,code,dict(p=pos,C=(albedo,'RGB'),Metal=(orm,'B'),Rough=(orm,'G')),4)
    H.output(split(m,out,True),'BASE_COLOR');H.output(split(m,out,False),'ROUGHNESS')
    H.output(normal,'NORMAL','RGB');H.output(orm,'METALLIC','B');H.output(orm,'AMBIENT_OCCLUSION','R')
    H.save(m);return m
def cart_finish():
    src='/Game/SceneTests/FreightSurfaceStudy20261112/Materials/M_CartCoatingWear'
    m=H.own('Materials/M_RepairCartSeamOxide',source=src)
    custom=next(n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom))
    code=(ROOT.parent/'FreightSurfaceStudy20261112/cart_coating.ush').read_text('utf8')
    code=code.replace('oxide=saturate(oxide*RustAmount);','''float drip=(1.-smoothstep(0.5,6.,abs(abs(p.y)-30.)))*(1.-smoothstep(.5,7.,abs(abs(p.x)-45.)))*smoothstep(.40,.81,area+.20*grain);
float spill=(1.-smoothstep(1.,9.,abs(abs(p.y)-28.7)))*saturate(n.z)*smoothstep(.35,.78,area+.21*grain);
oxide=saturate(max(max(oxide*.91,spill*.74),drip*.80)*RustAmount);''')
    code=code.replace('base=lerp(base,rgb*RustValue,oxide);','base=lerp(base,lerp(dot(rgb,float3(.30,.59,.11)).xxx,rgb,.62)*RustValue,oxide);')
    custom.set_editor_property('code',code)
    H.save(m);return H.instance('RepairCartSeamOxide',m,{'RustAmount':1.10,'RustValue':.81},{'PaintTint':(.135,.145,.131)})
def dust_finish():
    m=H.own('Materials/M_SettledMineralDust')
    L.delete_all_material_expressions(m);m.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    mask=sample(m,'Deposition','/Game/HospitalCorridor/Textures/Decals/T_DecalDirt_04_A',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    uv=H.node(m,'TextureCoordinate',coordinate_index=0)
    tex=u.load_asset('/Game/UndergroundTunnel/Textures/Effects/T_Noise01a')
    mode=u.MaterialSamplerType.SAMPLERTYPE_COLOR if tex.srgb else u.MaterialSamplerType.SAMPLERTYPE_MASKS
    n=H.node(m,'TextureObjectParameter',parameter_name='DustNoise',texture=tex,sampler_type=mode)
    deposition=H.custom(m,'''float2 st=UV*2.-1.;
float taper=1.-smoothstep(.48,1.,dot(st,st));
float macro=Texture2DSample(Field,FieldSampler,UV*float2(4.1,2.8)+.29).r;
float grit=Texture2DSample(Field,FieldSampler,UV*float2(72.,38.)).r;
return saturate(Density*taper*(.18+.82*A)*(.30+macro*.52+grit*.38));''',dict(UV=uv,A=(mask,'A'),Field=n,Density=H.scalar(m,'Density',.60)),1)
    H.output(deposition,'OPACITY')
    H.output(H.node(m,'VectorParameter',parameter_name='MineralTint',default_value=u.LinearColor(.24,.208,.166,1)),'BASE_COLOR')
    H.output(H.constant(m,.94),'ROUGHNESS');H.save(m);return m
def run(world,row):
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    def bind(a,mat):
        a.modify();c=a.get_component_by_class(u.StaticMeshComponent);c.modify();c.set_material(0,mat)
    bind(actors['WarehouseEntrance_Packing_RemainingCrate'],crate_finish())
    bind(actors['StationWorkshop_11_SM_SW_RepairCart'],cart_finish())
    dust=dust_finish()
    for label in ['WarehouseEntrance_Dust_PalletHalo','WarehouseEntrance_Dust_PackingWallFoot','FreightStation_WorkshopCartDust']:
        a=actors[label];c=a.get_component_by_class(u.DecalComponent);a.modify();c.modify();c.set_decal_material(dust)
    a=actors['SurfaceStudy_PackingConcreteRelief']
    relief=H.own('Materials/M_SpalledConcrete',source='/Game/SceneTests/FreightSurfaceStudy20261112/Materials/M_PackingConcreteRelief')
    relief.set_editor_property('two_sided',True);H.save(relief)
    a.modify();bind(a,relief);a.set_actor_scale3d(u.Vector(1.28,1.42,1.22))
    if 'wall_pose' in row:a.set_actor_location(u.Vector(*row['wall_pose']),False,False)
    label='Cart_WorkshopWallFootSpall'
    cart_wall=actors.get(label)
    if not cart_wall:
        api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
        cart_wall=api.spawn_actor_from_class(u.StaticMeshActor,u.Vector(8317.3,-350,38),u.Rotator(yaw=90))
        cart_wall.set_actor_label(label);cart_wall.set_folder_path('StationLine/ReferenceSurfaceStudy')
        comp=cart_wall.static_mesh_component;comp.set_static_mesh(a.static_mesh_component.static_mesh)
        comp.set_collision_profile_name('NoCollision');comp.set_cast_shadow(True)
    cart_wall.set_actor_scale3d(u.Vector(.85,.90,.76));bind(cart_wall,relief)
