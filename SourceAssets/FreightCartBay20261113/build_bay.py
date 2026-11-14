"""Assemble the registered surfaces and the collision-free architectural reveal in the station bay."""
from pathlib import Path
import json, types
import unreal as u
ROOT=Path(__file__).resolve().parent
BASE='/Game/SceneTests/FreightCartBay20261113'
PROD=ROOT.parents[1]
E=u.EditorAssetLibrary
L=u.MaterialEditingLibrary
helper=(ROOT.parent/'FacilitySurfaceUpgrade20261108/assets.py').read_text('utf8').split("GRAIN='/Game/")[0]
helper=helper.replace('from recipe import ROOT,BASE,REVISION,canonical,resolve','').replace("SOURCE=json.loads((ROOT/'material-inputs.json').read_text('utf8'))","SOURCE={}").replace('FacilitySurface.Owner','CartBay.Owner')
scope=dict(ROOT=ROOT,BASE=BASE,REVISION='freight_cart_bay_01',canonical=lambda s:s.split('.')[0])
exec(compile(helper,'cart_bay_material_nodes','exec'),scope)
H=types.SimpleNamespace(**scope)
def import_file(name,mesh=False):
    folder=BASE+('/Meshes' if mesh else '/Textures')
    path=folder+'/'+name
    if E.does_asset_exist(path):return u.load_asset(path)
    task=u.AssetImportTask();task.filename=str(ROOT/(name+('.fbx' if mesh else '.png')))
    task.destination_path=folder;task.destination_name=name;task.automated=True;task.save=False
    if mesh:
        opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opts.import_as_skeletal=False;opts.import_mesh=True;opts.import_textures=False;opts.import_materials=False
        data=opts.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.convert_scene=True;data.convert_scene_unit=True;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_COMPUTE_NORMALS
        task.options=opts;task.factory=u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Import failed '+path)
    if not mesh:
        asset.modify();asset.set_editor_property('srgb',False);asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
        asset.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);asset.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+path)
    return asset
def sample(m,name,texture,mode):
    return H.node(m,'TextureSampleParameter2D',parameter_name=name,texture=texture,sampler_type=mode)
def mask_sampler(texture):
    if texture.get_editor_property('srgb'):return u.MaterialSamplerType.SAMPLERTYPE_COLOR
    return u.MaterialSamplerType.SAMPLERTYPE_MASKS if texture.get_editor_property('compression_settings')==u.TextureCompressionSettings.TC_MASKS else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
def dado_material():
    m=H.own('Materials/M_DressedConcreteDado')
    L.delete_all_material_expressions(m)
    donor='/Game/Dungeons/WallUpgrade20260924/Textures/T_Wall_'
    c=u.load_asset(donor+'BaseColor');orm=u.load_asset(donor+'ORM');normal=u.load_asset(donor+'Normal')
    col=sample(m,'OriginalConcreteScan',c,mask_sampler(c))
    masks=sample(m,'ConcreteORM',orm,mask_sampler(orm))
    n=sample(m,'ConcreteSurfaceNormal',normal,u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    color=H.custom(m,'float l=dot(C,float3(.2126,.7152,.0722));return lerp(C,l.xxx,.48)*float3(.82,.80,.76)+.024;',dict(C=(col,'RGB')),3)
    rough=H.custom(m,'return lerp(.62,.94,R);',dict(R=(masks,'G')),1)
    H.output(color,'BASE_COLOR');H.output(n,'NORMAL','RGB');H.output(rough,'ROUGHNESS');H.output(masks,'AMBIENT_OCCLUSION','R')
    return H.save(m)
def coat(kind,tex):
    m=H.own('Materials/M_'+kind+'Weathering')
    L.delete_all_material_expressions(m)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);m.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL)
    world=H.node(m,'WorldPosition')
    uvcode='return (P.xy-float2(8317.,-600.))/400.;' if kind=='Platform' else 'return (P.yz-float2(-548.,0.))/float2(432.,236.);'
    uv=H.custom(m,uvcode,{'P':world},2)
    s=sample(m,'RegisteredMasks',tex,u.MaterialSamplerType.SAMPLERTYPE_MASKS);H.wire(uv,s,'UVs')
    # Only the local opacity blends the overlay with the existing world surface. Do not overwrite its fine normals.
    inputs={k:(s,k) for k in ['R','G','B','A']}
    if kind=='Platform':
        expr="""float seam=R*.79, rubber=G*.81, dust=B*.66, patch=A*.082;
float w=seam+rubber+dust+patch;
float3 c=(float3(.023,.021,.018)*seam+float3(.048,.044,.040)*rubber+float3(.32,.284,.230)*dust+float3(.245,.227,.202)*patch)/max(.0001,w);
Rough=(seam*.85+rubber*.48+dust*.96+patch*.75)/max(.0001,w);
return float4(c,1.-(1.-seam)*(1.-rubber)*(1.-dust)*(1.-patch));"""
    else:
        expr="""float streak=R*.49, foot=B*.0+G*.62, veil=B*.34;
float w=streak+foot+veil;
float3 c=(float3(.083,.075,.063)*streak+float3(.22,.185,.144)*foot+float3(.28,.25,.21)*veil)/max(.0001,w);
Rough=(streak*.62+foot*.92+veil*.82)/max(.0001,w);
return float4(c,1.-(1.-streak)*(1.-foot)*(1.-veil));"""
    out=H.custom(m,expr,inputs,4,extra=[('Rough',1)])
    col=H.node(m,'ComponentMask',r=True,g=True,b=True,a=False);H.wire(out,col)
    alpha=H.node(m,'ComponentMask',r=False,g=False,b=False,a=True);H.wire(out,alpha)
    H.output(col,'BASE_COLOR');H.output(alpha,'OPACITY');H.output(out,'ROUGHNESS','Rough')
    return H.save(m)
def apply(world,row):
    if world.get_path_name().split('.')[0]!='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject':raise RuntimeError('Wrong level')
    if row.get('load_only'):
        get=lambda sub:u.load_asset(BASE+'/'+sub)
        mesh=get('Meshes/SM_WorkshopDadoBay');stone=get('Materials/M_DressedConcreteDado')
        floor=get('Materials/M_PlatformWeathering');wall=get('Materials/M_WorkshopWallWeathering')
    else:
        mesh=import_file('SM_WorkshopDadoBay',True)
        stone=dado_material()
        floor=coat('Platform',import_file('T_CartBayFloorMasks'))
        wall=coat('WorkshopWall',import_file('T_CartBayWallMasks'))
    if not all([mesh,stone,floor,wall]):raise RuntimeError('Missing authored asset')
    lookup={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    def placed(label,cls,pos,rotation):
        a=lookup.get(label)
        if not a:
            a=api.spawn_actor_from_class(cls,u.Vector(*pos),rotation)
            if not a:raise RuntimeError('Cannot place '+label)
            a.set_actor_label(label);a.set_folder_path('StationLine/ReferenceSurfaceStudy/CartBay')
        return a
    a=placed('CartBay_ConcreteDadoAndCoping',u.StaticMeshActor,(8317.,-332.,0.),u.Rotator())
    c=a.static_mesh_component;c.modify();c.set_static_mesh(mesh);c.set_material(0,stone)
    c.set_collision_profile_name('NoCollision');c.set_editor_property('can_ever_affect_navigation',False);c.set_cast_shadow(True)
    # The earlier spall was centred on the bare wall. Move the relief onto the newly exposed face.
    chip=lookup['Cart_WorkshopWallFootSpall'];chip.modify()
    chip.set_actor_location(u.Vector(8321.87,-341.,18.),False,False)
    for label,mat,pos,rot,size in [('CartBay_PlatformJointRubberDust',floor,(8517.,-400.,.09),u.Rotator(pitch=-90),(0.135,200.,200.)),
                                     ('CartBay_DripAndToe',wall,(8320.,-332.,118.),u.Rotator(yaw=180),(3.95,216.,118.))]:
        a=placed(label,u.DecalActor,pos,rot);c=a.get_component_by_class(u.DecalComponent);c.modify();c.set_decal_material(mat)
        c.set_editor_property('decal_size',u.Vector(*size));c.set_editor_property('fade_screen_size',.0001);c.set_editor_property('sort_order',8)
    p,e=lookup['StationWorkshop_11_SM_SW_RepairCart'].get_actor_bounds(False)
    a=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor) if a.get_actor_label()=='CartBay_ConcreteDadoAndCoping')
    (ROOT/'installed.json').write_text(json.dumps(dict(wall_bounds=[v.to_tuple() for v in a.get_actor_bounds(False)],cart_center=p.to_tuple(),floor_extent_cm=[400,400],tread_cm=82),indent=2),'utf8')
