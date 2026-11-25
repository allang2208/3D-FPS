"""Local dry-surface RVT writer and height-limited receiver authoring."""
import hashlib
import unreal as u

BASE='/Game/WorldGeneration/TemperateHills/EcologyUpgrade'
COLOR=BASE+'/RVT_VillageSurface'
HEIGHT=BASE+'/RVT_VillageHeight'
TAG='HillsLocalRVT20261114'
L=u.MaterialEditingLibrary
E=u.EditorAssetLibrary

def node(mat,cls):
    n=L.create_material_expression(mat,cls);n.set_editor_property('desc',TAG);return n
def wire(a,b,pin,output=''):
    names=L.get_material_expression_input_names(b)
    if pin=='Input' and len(names)==1:pin=str(names[0])
    if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('RVT pin '+str(pin)+' '+str(names))
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('RVT save '+obj.get_path_name())
def make_caches():
    result=[]
    for path,kind in [(COLOR,u.RuntimeVirtualTextureMaterialType.BASE_COLOR_NORMAL_SPECULAR),
                      (HEIGHT,u.RuntimeVirtualTextureMaterialType.WORLD_HEIGHT)]:
        obj=u.load_asset(path) if E.does_asset_exist(path) else u.AssetToolsHelpers.get_asset_tools().create_asset(path.rsplit('/',1)[1],BASE,u.RuntimeVirtualTexture,u.RuntimeVirtualTextureFactory())
        obj.set_editor_property('material_type',kind)
        obj.set_editor_property('tile_count',4)
        obj.set_editor_property('tile_size',2)
        obj.set_editor_property('continuous_update',False)
        save(obj);result.append(obj)
    return result

def cache_zero(mat,source):
    if not E.does_asset_exist(COLOR):return source
    replace=node(mat,u.MaterialExpressionRuntimeVirtualTextureReplace)
    zero=node(mat,u.MaterialExpressionConstant);zero.set_editor_property('r',0.)
    wire(source,replace,'Default');wire(zero,replace,'VirtualTextureOutput')
    return replace


def road_surface(mat, outputs):
    from pathlib import Path
    import json
    import unreal as u
    plan=json.loads((Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))/'SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf-8'))
    def scalar_code(code, inputs, width):
        n=node(mat,u.MaterialExpressionCustom)
        n.set_editor_property('code',code)
        n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
        pins=[]
        for key in inputs:
            pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
        n.set_editor_property('inputs',pins)
        for key,value in inputs.items():
            source,channel=value if isinstance(value,tuple) else (value,'')
            wire(source,n,key,channel)
        return n
    pose=node(mat,u.MaterialExpressionVectorParameter)
    pose.set_editor_property('parameter_name','VillageRoadPose')
    pose.set_editor_property('default_value',u.LinearColor(0,0,0,0))
    # Vector parameters expose RGB and alpha on separate pins.
    local=scalar_code('float2 d=P.xy-Origin.xy; return float2(dot(d,float2(Origin.z,S)),dot(d,float2(-S,Origin.z)));',
                      {'P':node(mat,u.MaterialExpressionWorldPosition),'Origin':pose,'S':(pose,'A')},2)
    ex,ey=plan.get('surface_extent_m',plan['extent_m'])
    span=[ex*200.,ey*200.]
    uv=scalar_code('return .5+XY/float2(%f,%f);'%tuple(span),{'XY':local},2)
    def sample(asset,coord):
        t=node(mat,u.MaterialExpressionTextureSample)
        texture=u.load_asset(asset)
        if not texture:raise RuntimeError('Missing village texture '+asset)
        t.texture=texture
        t.sampler_type=(u.MaterialSamplerType.SAMPLERTYPE_ALPHA if texture.compression_settings==u.TextureCompressionSettings.TC_ALPHA else
                        u.MaterialSamplerType.SAMPLERTYPE_NORMAL if texture.compression_settings==u.TextureCompressionSettings.TC_NORMALMAP else
                        u.MaterialSamplerType.SAMPLERTYPE_MASKS if texture.compression_settings==u.TextureCompressionSettings.TC_MASKS else
                        u.MaterialSamplerType.SAMPLERTYPE_COLOR if texture.srgb else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        wire(coord,t,'UVs');return t
    mask=sample('/Game/WorldGeneration/TemperateHills/AbandonedVillage/T_VillageRoadMask',uv)
    earth_size=100.*plan['ground_dressing']['earth_tile_m']
    import runpy
    scan=runpy.run_path(str(Path(__file__).with_name('AbandonedVillage')/'village_ground_uv.py'))
    coords=lambda size:scalar_code(scan['rvt_uv'](span,size),{'XY':local},2)
    road_uv,soil_uv=coords(320.),coords(earth_size)
    road='/Game/UnrealNormandy/Textures/T_LC_GroundRockyRoad_00A_'
    soil='/Game/WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces/T_ChapelEarth_'
    h=sample(soil+'H',soil_uv)
    edge=runpy.run_path(str(Path(__file__).with_name('AbandonedVillage')/'village_road_blend.py'))
    weights=edge['build_weights'](mat,mask,uv,h,span)
    yard=runpy.run_path(str(Path(__file__).with_name('AbandonedVillage')/'smith_yard_material.py'))
    yard['bind'](mat)
    coverage=scalar_code('return max(W.x,W.y);',{'W':weights},1)
    roadway=scalar_code('return saturate(W.x/max(.0001,A));',{'W':weights,'A':coverage},1)
    result=dict(outputs)
    for name,rt,st,rc,sc in [('BASE_COLOR','Albedo','B','RGB','RGB'),('NORMAL','Normal','N','RGB','RGB'),('ROUGHNESS','RHAOM','ORM','R','G')]:
        a=sample(soil+st,soil_uv);b=sample(road+rt,road_uv)
        blend=node(mat,u.MaterialExpressionLinearInterpolate)
        wire(a,blend,'A',sc);wire(b,blend,'B',rc);wire(roadway,blend,'Alpha')
        if name=='NORMAL':
            blend=scalar_code('return normalize(float3(N.x*C-N.y*S,N.x*S+N.y*C,N.z));',{'N':blend,'C':(pose,'B'),'S':(pose,'A')},3)
        layer=node(mat,u.MaterialExpressionLinearInterpolate)
        wire(outputs[name],layer,'A');wire(blend,layer,'B');wire(coverage,layer,'Alpha');result[name]=layer
    return result

def write_dry_surface(mat,outputs):
    if not E.does_asset_exist(COLOR):return
    outputs=road_surface(mat,outputs)
    output=node(mat,u.MaterialExpressionRuntimeVirtualTextureOutput)
    wire(outputs['BASE_COLOR'],output,'BaseColor')
    wire(outputs['ROUGHNESS'],output,'Roughness')
    norm=node(mat,u.MaterialExpressionTransform)
    norm.set_editor_property('transform_source_type',u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT)
    norm.set_editor_property('transform_type',u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    wire(outputs['NORMAL'],norm,'Input');wire(norm,output,'Normal')
    pos=node(mat,u.MaterialExpressionWorldPosition)
    z=node(mat,u.MaterialExpressionComponentMask);z.set_editor_property('r',False);z.set_editor_property('g',False);z.set_editor_property('b',True)
    wire(pos,z,'Input');wire(z,output,'WorldHeight')

def receiver(material,cache):
    key=material.get_path_name()
    if key.startswith(BASE+'/Receivers/'):return material
    if key in cache:return cache[key]
    name=('MI_' if isinstance(material,u.MaterialInstanceConstant) else 'M_')+hashlib.sha1(key.encode()).hexdigest()[:12]
    dest=BASE+'/Receivers/'+name
    obj=u.load_asset(dest) if E.does_asset_exist(dest) else E.duplicate_asset(key,dest)
    cache[key]=obj
    if isinstance(obj,u.MaterialInstanceConstant):
        L.set_material_instance_parent(obj,receiver(material.get_editor_property('parent'),cache))
        L.update_material_instance(obj);save(obj);return obj
    if any(n.get_editor_property('desc')==TAG for n in L.get_material_expressions(obj)):return obj
    color=node(obj,u.MaterialExpressionRuntimeVirtualTextureSample);color.set_editor_property('virtual_texture',u.load_asset(COLOR))
    color.set_editor_property('material_type',u.RuntimeVirtualTextureMaterialType.BASE_COLOR_NORMAL_SPECULAR)
    height=node(obj,u.MaterialExpressionRuntimeVirtualTextureSample);height.set_editor_property('virtual_texture',u.load_asset(HEIGHT))
    height.set_editor_property('material_type',u.RuntimeVirtualTextureMaterialType.WORLD_HEIGHT)
    pos=node(obj,u.MaterialExpressionWorldPosition)
    blend=node(obj,u.MaterialExpressionCustom)
    blend.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
    blend.set_editor_property('code','float d=P.z-H; float rag=sin(P.x*.073+sin(P.y*.037))*2.3; return (1-smoothstep(2.0,16.0+rag,d))*smoothstep(-12.0,-2.0,d);')
    pins=[]
    for name in ('P','H'):
        p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
    blend.set_editor_property('inputs',pins);wire(pos,blend,'P');wire(height,blend,'H','WorldHeight')
    supported=node(obj,u.MaterialExpressionVirtualTextureFeatureSwitch)
    zero=node(obj,u.MaterialExpressionConstant);zero.set_editor_property('r',0.)
    wire(blend,supported,'Yes');wire(zero,supported,'No')
    attr=u.MaterialProperty.MP_MATERIAL_ATTRIBUTES
    source_attrs=L.get_material_property_input_node(obj,attr) if obj.get_editor_property('use_material_attributes') else None
    if source_attrs:
        attr_out=L.get_material_property_input_node_output_name(obj,attr)
        reader=node(obj,u.MaterialExpressionGetMaterialAttributes)
        writer=node(obj,u.MaterialExpressionSetMaterialAttributes)
        for pins in (reader,writer):
            wire(source_attrs,pins,L.get_material_expression_input_names(pins)[0],attr_out)
    for name,out in [('BASE_COLOR','BaseColor'),('ROUGHNESS','Roughness'),('NORMAL','Normal')]:
        prop=getattr(u.MaterialProperty,'MP_'+name)
        original=L.get_material_property_input_node(obj,prop)
        if source_attrs:
            index={'BASE_COLOR':0,'NORMAL':1,'ROUGHNESS':2}[name]
            read_index=u.TemperateForestAuthoringLibrary.add_surface_blend_pin(reader,index)
            write_index=u.TemperateForestAuthoringLibrary.add_surface_blend_pin(writer,index)
            if min(read_index,write_index)<0:raise RuntimeError('RVT material attribute '+name)
            original=reader;channel=L.get_material_expression_output_names(reader)[read_index]
        elif original:
            channel=L.get_material_property_input_node_output_name(obj,prop)
        else:
            original=node(obj,u.MaterialExpressionConstant3Vector if name!='ROUGHNESS' else u.MaterialExpressionConstant)
            if name=='NORMAL':original.set_editor_property('constant',u.LinearColor(0,0,1,0))
            if name=='ROUGHNESS':original.set_editor_property('r',.5)
            channel=''
        surface=color;output=out
        if name=='NORMAL':
            surface=node(obj,u.MaterialExpressionTransform)
            surface.set_editor_property('transform_source_type',u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
            surface.set_editor_property('transform_type',u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
            wire(color,surface,'Input','Normal');output=''
        mix=node(obj,u.MaterialExpressionLinearInterpolate)
        wire(original,mix,'A',channel);wire(surface,mix,'B',output);wire(supported,mix,'Alpha')
        if source_attrs:
            wire(mix,writer,L.get_material_expression_input_names(writer)[write_index])
        elif not L.connect_material_property(mix,'',prop):raise RuntimeError('RVT receiver output')
    if source_attrs and not L.connect_material_property(writer,'',attr):raise RuntimeError('RVT attributes output')
    L.recompile_material(obj);save(obj);return obj

def dress_component(comp, leaf_instance, receivers):
    mesh=comp.get_editor_property('static_mesh')
    name=mesh.get_name()
    plant=name.startswith(('SM_Grass','SM_SoftWildGrass','SM_Plant','flower_'))
    stone=name.startswith('SM_Stone_0')
    wall=name.startswith('SM_H_StoneWall_00A_Piece')
    no_shadow=(plant or stone) and str(comp.get_collision_profile_name())=='NoCollision'
    if no_shadow:comp.set_cast_shadow(False)
    rock_slots=0
    if plant or stone or wall:
        for i in range(comp.get_num_materials()):
            material=comp.get_material(i)
            if not material:continue
            if plant:comp.set_material(i,leaf_instance(material))
            elif E.does_asset_exist(COLOR):
                comp.set_material(i,receiver(material,receivers));rock_slots+=1
    return rock_slots,no_shadow
