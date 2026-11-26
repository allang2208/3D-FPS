"""Bake the distant ring from the saved hillside PCG grass. Leaves the PCG-owned near and middle layers intact."""
from array import array
from collections import defaultdict
import json
import math
import os
from pathlib import Path
import unreal as u

FOLDER='/Game/ForestPathStudy/VillageRegion/FarGrass'
MAP='/Game/GameMaps/L_ForestPathVillage'
TAG='ForestVillage.FarGrass'
FORMS={'SM_RainforestGrassLow':'Low','SM_RainforestGrassSpreading':'Spreading',
       'SM_RainforestGrassTall':'Tall','SM_RiverDense_grass_04_03_mesh':'Sedge'}
ED=u.MaterialEditingLibrary
LIB=u.EditorAssetLibrary

def save(obj):
    if not LIB.save_loaded_asset(obj,False): raise RuntimeError('Cannot save '+obj.get_path_name())

def make_materials(source):
    LIB.make_directory(FOLDER)
    atlas_path=FOLDER+'/T_HillsFarGrass'
    if not LIB.does_asset_exist(atlas_path):
        task=u.AssetImportTask()
        task.filename=str(source/'T_HillsFarGrass.png')
        task.destination_path=FOLDER
        task.destination_name='T_HillsFarGrass'
        task.automated=True
        task.save=False
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex=u.load_asset(atlas_path)
    tex.set_editor_property('srgb',True)
    tex.set_editor_property('do_scale_mips_for_alpha_coverage',True)
    tex.set_editor_property('alpha_coverage_thresholds',u.Vector4(0,0,0,1/3))
    save(tex)
    factory=u.AssetToolsHelpers.get_asset_tools()
    name='M_HillsFarGrass'
    mat=u.load_asset(FOLDER+'/'+name) if LIB.does_asset_exist(FOLDER+'/'+name) else factory.create_asset(name,FOLDER,u.Material,u.MaterialFactoryNew())
    ED.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
    mat.set_editor_property('two_sided',True)
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('opacity_mask_clip_value',1/3)
    mat.set_editor_property('used_with_instanced_static_meshes',True)
    def node(kind,x,y):return ED.create_material_expression(mat,kind,x,y)
    def wire(a,out,c,pin):
        if not ED.connect_material_expressions(a,out,c,pin): raise RuntimeError('Cannot connect '+c.get_name()+'.'+pin)
    def bind(a,out,prop):
        if not ED.connect_material_property(a,out,prop): raise RuntimeError('Cannot bind '+str(prop))
    def scalar(key,value,x,y):
        n=node(u.MaterialExpressionScalarParameter,x,y)
        n.set_editor_property('parameter_name',key)
        n.set_editor_property('default_value',value)
        return n
    def custom(code,channels,kind,x,y):
        n=node(u.MaterialExpressionCustom,x,y)
        args=[]
        for key,_,_ in channels:
            a=u.CustomInput();a.set_editor_property('input_name',key);args.append(a)
        n.set_editor_property('inputs',args)
        n.set_editor_property('code',code)
        n.set_editor_property('output_type',kind)
        for key,a,out in channels:wire(a,out,n,key)
        return n
    atlas=node(u.MaterialExpressionTextureSample,-650,-200)
    atlas.set_editor_property('texture',tex)
    kinds=u.CustomMaterialOutputType
    color=custom('return lerp(dot(C,float3(.3,.59,.11)).xxx,C,S)*B;',
                 [('C',atlas,'RGB'),('S',scalar('GrassSaturation',.9,-650,0),''),
                  ('B',scalar('GrassBrightness',.8,-650,120),'')],kinds.CMOT_FLOAT3,-220,-200)
    # Use the current UDS sun, moon and skylight. No per-grass light loop, VSM receiver or normal map.
    light=custom("""float3 e=ResolvedView.SkyLightColor.rgb*.18;
        [unroll] for(uint i=0;i<2;++i) {
            e+=ResolvedView.AtmosphereLightIlluminanceOnGroundPostTransmittance[i].rgb*
                (.35*saturate(ResolvedView.AtmosphereLightDirection[i].z));
        }
        return C*e/PI;""",[('C',color,'')],kinds.CMOT_FLOAT3,80,-200)
    bind(light,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    # ISM's scaled native draw interval also supplies the material's soft entrance.
    # Calculate it per vertex, preserving split-screen, FOV and scalability behaviour.
    dist=node(u.MaterialExpressionDistance,-450,440)
    wire(node(u.MaterialExpressionCameraPositionWS,-800,400),'',dist,'A')
    wire(node(u.MaterialExpressionWorldPosition,-800,530),'',dist,'B')
    near=custom('float r=sqrt(GetPrimitiveData(Parameters).InstanceDrawDistanceMinMaxSquared.x); return saturate((D-r)/max(1.0,r*.025));',
                [('D',dist,'')],kinds.CMOT_FLOAT1,-210,460)
    interp=node(u.MaterialExpressionVertexInterpolator,0,450)
    wire(near,'',interp,'')
    fade=node(u.MaterialExpressionMultiply,200,300)
    wire(interp,'',fade,'A')
    wire(node(u.MaterialExpressionPerInstanceFadeAmount,0,250),'',fade,'B')
    mask=node(u.MaterialExpressionMultiply,450,180)
    wire(atlas,'A',mask,'A');wire(fade,'',mask,'B')
    bind(mask,'',u.MaterialProperty.MP_OPACITY_MASK)
    errors=ED.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    save(mat)
    for mesh,role in FORMS.items():
        name='MI_HillsFar'+role
        if role=='Sedge':
            orig=u.load_asset('/Game/WorldGeneration/TemperateHills/RiverEcologyDense/'+mesh).get_material(0)
        else:
            orig=u.load_asset('/Game/ForestPathStudy/VillageRegion/GrassCover/MI_HillsGrass'+role)
        mi=u.load_asset(FOLDER+'/'+name) if LIB.does_asset_exist(FOLDER+'/'+name) else factory.create_asset(name,FOLDER,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        ED.set_material_instance_parent(mi,mat)
        for key,param in [('GrassBrightness','Brightness'),('GrassSaturation','Saturation')]:
            ED.set_material_instance_scalar_parameter_value(mi,key,ED.get_material_instance_scalar_parameter_value(orig,param))
        ED.update_material_instance(mi)
        save(mi)

def hash01(ix,iy,salt=0):
    h=((ix*0x9e3779b1)^(iy*0x85ebca6b)^salt)&0xffffffff
    h=((h^(h>>16))*0x7feb352d)&0xffffffff
    return (h^(h>>15))/4294967296.


def smooth_unit(t):
    t=max(0.,min(1.,t))
    return t*t*(3.-2.*t)


def meadow_noise(x,y,salt):
    i,j=math.floor(x),math.floor(y)
    fx,fy=smooth_unit(x-i),smooth_unit(y-j)
    a=hash01(i,j,salt)*(1.-fx)+hash01(i+1,j,salt)*fx
    b=hash01(i,j+1,salt)*(1.-fx)+hash01(i+1,j+1,salt)*fx
    return a+(b-a)*fy


def patch_width(pos,role):
    if role=='Sedge':return 1.
    x,y=pos.x*.01,pos.y*.01
    broad=meadow_noise((.89*x+.46*y)/17.,(-.46*x+.89*y)/10.,0x46b8f331)
    edge=meadow_noise((x-.32*y)/4.8,(.32*x+y)/5.6,0x90866c5b)
    cover=smooth_unit((.75*broad+.25*edge-.36)/.36)
    # Spend the existing silhouette budget inside drifts instead of adding a card layer.
    base=.5 if role=='Tall' else .25
    chance=base*(.04+1.55*cover)
    if hash01(round(x*10),round(y*10))>=chance:return 0.
    return 1.09+.16*cover

def rebuild(world,region,*,sedge_only=False):
    actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    groups=defaultdict(list)
    specs={}
    coverage=array('I',[0])*(512*512)
    for c in region.get_components_by_class(u.InstancedStaticMeshComponent):
        mesh=c.static_mesh
        role=FORMS.get(mesh.get_name()) if mesh else None
        if not role or (sedge_only and role!='Sedge'):continue
        end=c.get_editor_property('instance_end_cull_distance')
        if end<=0:raise RuntimeError('Missing source cull distance on '+role)
        prior=specs.setdefault(role,(mesh,end))
        if prior!=(mesh,end):raise RuntimeError('Mixed grass settings for '+role)
        for i in range(c.get_instance_count()):
            pose=c.get_instance_transform(i,world_space=True)
            pos=pose.translation
            spread=patch_width(pos,role)
            if spread:
                scale=pose.scale3d
                pose.scale3d=u.Vector(scale.x*spread,scale.y*spread,scale.z)
                groups[math.floor(pos.x/12800),math.floor(pos.y/12800),role].append(pose)
                px,py=math.floor((pos.x+62400)/200),math.floor((pos.y+32000)/200)
                if role!='Sedge' and 0<=px<512 and 0<=py<512:
                    coverage[py*512+px]+=1
    if not sedge_only and not all(role in specs for role in ('Low','Spreading','Tall')):
        raise RuntimeError('Missing the baked middle grass in the persistent level')
    for a in actors.get_all_level_actors():
        if a.get_path_name().startswith(MAP+'.') and TAG in map(str,a.tags):
            actors.destroy_actor(a)
    sub=u.get_engine_subsystem(u.SubobjectDataSubsystem)
    handles=u.SubobjectDataBlueprintFunctionLibrary
    def add(actor,klass):
        parent=sub.k2_gather_subobject_data_for_instance(actor)[0]
        handle,reason=sub.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent,new_class=klass))
        obj=handles.get_associated_object(handles.get_data(handle))
        if not obj:raise RuntimeError(str(reason))
        return obj
    tiles={}
    counts=defaultdict(int)
    for (tx,ty,role),poses in sorted(groups.items()):
        key=(tx,ty)
        if key not in tiles:
            origin=u.Vector((tx+.5)*12800,(ty+.5)*12800,0)
            a=actors.spawn_actor_from_class(u.Actor,origin)
            if not a.get_path_name().startswith(MAP+'.'):raise RuntimeError('Unexpected foliage owner level')
            if not a.root_component:add(a,u.SceneComponent)
            a.root_component.set_mobility(u.ComponentMobility.STATIC)
            a.set_actor_location(origin,False,True)
            a.set_actor_label(f'Grass distance {tx} {ty}')
            a.set_editor_property('tags',[TAG])
            tiles[key]=a
        a=tiles[key]
        mesh,end=specs[role]
        c=add(a,u.InstancedStaticMeshComponent)
        c.set_mobility(u.ComponentMobility.STATIC)
        c.set_static_mesh(mesh)
        c.set_material(0,u.load_asset(FOLDER+'/MI_HillsFar'+role))
        c.set_forced_lod_model(mesh.get_num_lods())
        c.set_editor_property('override_min_lod',True)
        c.set_editor_property('min_lod',mesh.get_num_lods()-1)
        c.set_editor_property('instance_min_draw_distance',end)
        c.set_cull_distances(round(end*1.78),2*end)
        c.set_collision_profile_name('NoCollision')
        c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        c.set_editor_property('generate_overlap_events',False)
        c.set_cast_shadow(False)
        for prop in ('cast_static_shadow','cast_dynamic_shadow','cast_contact_shadow','cast_far_shadow'):
            c.set_editor_property(prop,False)
        for prop in ('visible_in_ray_tracing','affect_distance_field_lighting','affect_dynamic_indirect_lighting','receives_decals','can_ever_affect_navigation'):
            c.set_editor_property(prop,False)
        c.add_instances(poses,False,True,False)
        counts[role]+=len(poses)
    source=os.environ.get('FPS_FOREST_REFERENCE_SOURCE')
    if source and not sedge_only:
        with (Path(source)/'Grass/far_coverage.u32').open('wb') as stream:coverage.tofile(stream)
    return dict(instances=dict(counts),cells=len(tiles),components=len(groups),
                range_cm={role:[end,2*end] for role,(_,end) in specs.items()})


if __name__=='__main__':
    source=Path(os.environ['FPS_GRASS_DISTANCE_SOURCE'])
    batch=Path(os.environ['FPS_GRASS_DISTANCE_BATCH'])
    make_materials(source)
    world=u.EditorLoadingAndSavingUtils.load_map(MAP)
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    region=next(a for a in actors if isinstance(a,u.ForestVillageRegion))
    report=rebuild(world,region)
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):
        raise RuntimeError('Cannot save the grass distance layer on '+MAP)
    (batch/'baked.json').write_text(json.dumps(report,indent=2))
