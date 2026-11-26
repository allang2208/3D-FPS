"""Install the village-only earth material and reproject both themes on the final hillside."""
import json,os,sys
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).resolve().parent))
import author_trail_cover_materials as art
import author_trail_cover_level as level
import author_grass_distance as sedge
import landscape_themes as themes

ed=art.ed
lib=art.lib
src=art.src
folder=art.ref+'/VillageLoess'

def finish_source():
    if (src/'wall-grass.json').is_file():return src
    resources=themes.preset('HillsLandscape')['resources']
    if Path(resources['terrain_source']).parent.name==src.name:
        return src.parent/resources['village_finish_source']
    return src

def texture(ch,comp):
    name='T_VillageLoess_'+ch
    task=u.AssetImportTask();task.filename=str(finish_source()/'Loess'/(name+'.png'))
    task.destination_name=name;task.destination_path=folder;task.automated=True;task.replace_existing=True
    art.tools.import_asset_tasks([task]);tex=u.load_asset(folder+'/'+name)
    tex.set_editor_property('srgb',ch=='B');tex.set_editor_property('compression_settings',getattr(u.TextureCompressionSettings,'TC_'+comp))
    tex.set_editor_property('never_stream',False);art.save(tex);return tex

def configure(mat,node,scans):
    pins=list(node.get_editor_property('inputs'))
    sources=art.inputs(mat,node)
    for key in ('P','V','Eye','Albedo','Nrm','Data','Wet'):
        if not any(str(p.get_editor_property('input_name'))==key for p in pins):
            p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
    node.set_editor_property('inputs',pins)
    for key,cls in [('P',u.MaterialExpressionWorldPosition),('V',u.MaterialExpressionCameraVectorWS),('Eye',u.MaterialExpressionCameraPositionWS)]:
        n=sources.get(key) or art.node(mat,cls);art.wire(n,'',node,key)
    for key,(tex,sampler) in scans.items():
        n=sources.get(key) or art.node(mat,u.MaterialExpressionTextureObject)
        n.set_editor_property('texture',tex);n.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+sampler))
        art.wire(n,'',node,key)
    rain=sources.get('Wet') or art.node(mat,u.MaterialExpressionCollectionParameter)
    rain.set_editor_property('collection',u.load_asset('/Game/Weather/Materials/MPC_FPS_Weather'));rain.set_editor_property('parameter_name','WeatherWetness');art.wire(rain,'',node,'Wet')
    outputs=[]
    for name,kind in [('GrassNormal','FLOAT3'),('GrassRoughness','FLOAT1'),('GrassAO','FLOAT1')]:
        o=u.CustomOutput();o.set_editor_property('output_name',name);o.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_'+kind));outputs.append(o)
    node.set_editor_property('additional_outputs',outputs);node.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    node.set_editor_property('desc','R32 village loess');node.set_editor_property('code',Path(__file__).with_name('village_loess.ush').read_text(encoding='utf-8-sig'))

def surfaces():
    lib.make_directory(folder)
    scans={'Albedo':(texture('B','DEFAULT'),'COLOR'),'Nrm':(texture('N','NORMALMAP'),'NORMAL'),'Data':(texture('ARH','MASKS'),'MASKS')}
    master=u.load_asset(art.ref+'/M_ForestReferenceMesh')
    node=next(n for n in ed.get_material_expressions(master) if n.get_editor_property('desc') in ('R20 Quixel pe1jvwp0 village turf','R32 village loess'))
    configure(master,node,scans)
    from author_village_forest_floor import bind, import_mask, NAME
    mask_path=folder+'/'+NAME
    mask_source=themes.preset('HillsLandscape')['resources'].get('village_forest_floor_source')
    if lib.does_asset_exist(mask_path):
        bind(master,art.asset(mask_path))
    elif mask_source:
        bind(master,import_mask(themes.source_root().resolve().parent/mask_source))
    art.compile_mat(master)
    detail=art.asset(folder+'/M_VillageLoessDetail') if lib.does_asset_exist(folder+'/M_VillageLoessDetail') else art.tools.create_asset('M_VillageLoessDetail',folder,u.Material,u.MaterialFactoryNew())
    detail.set_editor_property('used_with_instanced_static_meshes',True);detail.set_editor_property('used_with_nanite',True)
    node=next((n for n in ed.get_material_expressions(detail) if n.get_editor_property('desc')=='R32 village loess'),None) or art.node(detail,u.MaterialExpressionCustom)
    configure(detail,node,scans)
    for name,prop in [('', 'BASE_COLOR'),('GrassNormal','NORMAL'),('GrassRoughness','ROUGHNESS'),('GrassAO','AMBIENT_OCCLUSION')]:
        if not ed.connect_material_property(node,name,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError(prop)
    art.compile_mat(detail)
    return detail

def stable_entry():
    # The stable's original decal covers 36 by 44 m. Its cart and hoof tracks begin on the town road.
    original='/Game/WorldGeneration/TemperateHills/VillageStable/GroundDetailR4/M_StableYardSoil'
    variant=folder+'/M_StableYardLoessBlend'
    mat=u.load_asset(variant) if lib.does_asset_exist(variant) else lib.duplicate_asset(original,variant)
    tag='Village stable entrance wear'
    node=next((n for n in ed.get_material_expressions(mat) if n.get_editor_property('desc')==tag),None)
    if not node:
        weights=ed.get_material_property_input_node(mat,u.MaterialProperty.MP_OPACITY)
        if not isinstance(weights,u.MaterialExpressionTextureSample):raise RuntimeError('Missing original stable traffic mask')
        if weights.get_editor_property('texture').get_name()!='T_StableGroundWeights':raise RuntimeError('Unexpected stable atlas')
        uv=art.node(mat,u.MaterialExpressionTextureCoordinate)
        node=art.node(mat,u.MaterialExpressionCustom)
        pins=[]
        for name in ('UV','Coverage'):
            pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
        node.set_editor_property('inputs',pins);node.set_editor_property('desc',tag)
        node.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
        art.wire(uv,'',node,'UV');art.wire(weights,'R',node,'Coverage')
    node.set_editor_property('code','''float2 metres=float2(27.,3.)+UV*float2(36.,44.);
float along=smoothstep(6.,15.,metres.y+.38*sin(metres.x*1.13)+.24*sin(metres.y*2.9));
float entry=smoothstep(38.,47.,metres.x);
return Coverage*lerp(1.,lerp(.18,1.,along),entry);''')
    if not ed.connect_material_property(node,'',u.MaterialProperty.MP_OPACITY):raise RuntimeError('Stable entrance opacity')
    art.compile_mat(mat)
    return mat

def install():
    detail=surfaces()
    world=level.save.load_map(level.village)
    if not u.get_editor_subsystem(u.LevelEditorSubsystem).set_current_level_by_name('L_ForestPathVillage'):raise RuntimeError('Persistent level required')
    actors=level.actor_list();reg=next(a for a in actors if isinstance(a,u.ForestVillageRegion))
    reg.set_editor_property('village_loess_detail',detail)
    reg.set_editor_property('village_stable_entry_wear',stable_entry())
    cfg=json.loads((src/'hill.json').read_text())
    if not reg.install_grass_cover(str(finish_source()/'Grass/near_grass.u8'),True):raise RuntimeError('Near grass mask update failed')
    if not reg.install_hill_site(str(src),u.IntPoint(*cfg['site_min_m']),cfg['village_datum_cm']):raise RuntimeError('Settlement bake')
    if not reg.bake_reference_surface(str(src),art.asset(art.ref+'/MI_ForestReference')):raise RuntimeError('Ground mesh/collision bake')
    templates=[c for a in actors if isinstance(a,u.PCGVolume) and '/L_ForestPathForest.' in a.get_path_name() for c in a.get_components_by_class(u.InstancedStaticMeshComponent)]
    if not templates:raise RuntimeError('Missing canopy templates')
    for name in ('HillsLandscape','RoadLandscape'):
        theme=themes.preset(name)
        points=themes.point_input(theme,None)
        if not reg.bake_vegetation(points,templates,name):raise RuntimeError('Theme reprojection '+name)
    shores=sedge.rebuild(world,reg,sedge_only=True)
    count,cells=level.place_meadows(world)
    field=art.tex('T_ContinuousMeadowField',art.ref+'/ContinuousMeadow','BC7',False)
    for key in ('address_x','address_y'):field.set_editor_property(key,u.TextureAddress.TA_CLAMP)
    field.set_editor_property('compression_no_alpha',False);art.save(field)
    if not level.save.save_map(world,level.village):raise RuntimeError('Map save')
    (art.batch/'authored.json').write_text(json.dumps(dict(map=level.village,fine_grass=count,cells=cells,shores=shores,pools=sum(isinstance(a,u.ForestVillagePoolSurface) and a.get_path_name().startswith(level.village+'.') for a in level.actor_list())),indent=2))
if __name__=='__main__':install()
