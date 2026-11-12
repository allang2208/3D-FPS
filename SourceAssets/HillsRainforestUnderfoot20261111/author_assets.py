from datetime import datetime
from pathlib import Path
import importlib.util
import json
import runpy
import shutil
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
BATCH=ROOT/'SourceAssets/HillsRainforestUnderfoot20261111'
BASE='/Game/WorldGeneration/TemperateHills'
DEST=BASE+'/WetForest/Underfoot'
DATA=BASE+'/DA_TemperateHillsStreaming'
GROUND=[BASE+'/M_TemperateGround',BASE+'/PebbleShore/M_PebbleShoreGround']
POND=BASE+'/WetForest/M_ForestPond'
GRASSES=('LowSward','RibbonGrass','BankSedge')
SCANS=('ForestTwig01','ForestTwig02','MossyForestBoulder')
E=u.EditorAssetLibrary
L=u.MaterialEditingLibrary
AT=u.AssetToolsHelpers.get_asset_tools()
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
spec=importlib.util.spec_from_file_location('forest_wet_materials',ROOT/'Tools/WorldGeneration/forest_wet_materials.py')
wet=importlib.util.module_from_spec(spec)
spec.loader.exec_module(wet)
understory=runpy.run_path(str(ROOT/'Tools/WorldGeneration/temperate_understory_wind.py'))
saved=[]

if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and u.EditorLevelLibrary.get_pie_worlds(False):
    raise RuntimeError('Finish PIE before updating the loaded forest palette')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in [DATA,POND,*GROUND] or p.startswith(DEST+'/') for p in dirty):
    raise RuntimeError('Unsaved forest target package is open')
backup=BATCH/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
for pkg in [DATA,POND,*GROUND]:
    src=ROOT/'Content'/(pkg[6:]+'.uasset')
    if src.exists():
        dst=backup/(pkg[6:]+'.uasset');dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)


def save(obj):
    if isinstance(obj,u.Material):
        errors=L.recompile_material(obj)
        if errors:raise RuntimeError(obj.get_path_name()+' '+str(errors))
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Could not save '+obj.get_path_name())
    saved.append(obj.get_path_name())
    return obj


def load_file(src,dest,name,cls):
    t=u.AssetImportTask()
    for prop,value in dict(filename=str(src),destination_path=dest,destination_name=name,
                           automated=True,replace_existing=True,save=False).items():
        t.set_editor_property(prop,value)
    AT.import_asset_tasks([t])
    objs=[o for o in t.get_objects() if isinstance(o,cls)]
    if len(objs)!=1:raise RuntimeError(str(src)+' import: '+str(objs))
    obj=objs[0]
    if not dest.startswith('/Temp/') and obj.get_path_name().split('.')[0]!=dest+'/'+name:
        if not E.rename_loaded_asset(obj,dest+'/'+name):raise RuntimeError('Failed to name '+name)
    return obj


def material(name):
    path=DEST+'/'+name
    mat=E.load_asset(path) if E.does_asset_exist(path) else AT.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    mat.set_editor_property('used_with_instanced_static_meshes',True)
    return mat


def set_material(mesh,mat):
    slots=mesh.get_editor_property('static_materials')
    if not slots:
        slot=u.StaticMaterial();slot.set_editor_property('material_interface',mat)
        slot.set_editor_property('material_slot_name','Surface');mesh.set_editor_property('static_materials',[slot])
    else:
        for i in range(len(slots)):mesh.set_material(i,mat)


def geometry(name,mat,dest=DEST):
    existing=dest==DEST and E.does_asset_exist(dest+'/'+name)
    package='/Temp/ForestUnderfootAuthoring' if existing else dest
    mesh=load_file(BATCH/'Prepared'/(name+'.glb'),package,name,u.StaticMesh)
    set_material(mesh,mat)
    if existing:
        target=E.load_asset(dest+'/'+name)
        set_material(target,mat)
        if SM.set_lod_from_static_mesh(target,0,mesh,0,True)!=0:raise RuntimeError('Could not refresh '+name)
        return target
    return mesh


grass=material('M_FoldedForestBlade')
grass.set_editor_property('two_sided',True)
grass.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
grass.set_editor_property('shading_model',u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
grass.set_editor_property('max_world_position_offset_displacement',2.5)
def node(cls,key):return wet.node(grass,cls,key)
uv=node(u.MaterialExpressionTextureCoordinate,'BladeUV')
trait=node(u.MaterialExpressionTextureCoordinate,'BladeTrait')
trait.set_editor_property('coordinate_index',1)
rand=node(u.MaterialExpressionPerInstanceRandom,'BladeVariation')
p,weather,_=wet.common(grass)
color=wet.custom(grass,'BladePigment','''
float h=saturate(UV.y);
float vein=1-abs(UV.x*2-1);
float3 young=lerp(float3(.024,.069,.014),float3(.10,.20,.042),Traits.x);
float3 tip=lerp(young*1.26,float3(.18,.25,.061),.25*Traits.x);
float3 c=lerp(young*.50,tip,smoothstep(0,.91,h));
float ribs=.035*cos(UV.x*33)+.05*smoothstep(.72,.99,vein);
return c*(1+ribs)*lerp(.86,1.10,R)*lerp(1.,.78,saturate(W.x));
''',{'UV':uv,'Traits':trait,'R':rand,'W':weather},3)
wet.connect(grass,'BASE_COLOR',color)
wet.connect(grass,'SUBSURFACE_COLOR',wet.custom(grass,'BladeLight','return C*float3(.52,.68,.37);',{'C':color},3))
wet.connect(grass,'ROUGHNESS',wet.custom(grass,'BladeRough','return lerp(.68,.39,saturate(W.x));',{'W':weather}))
dither=node(u.MaterialExpressionMaterialFunctionCall,'InstanceDither')
dither.set_editor_property('material_function',u.load_asset('/Engine/Functions/Engine_MaterialFunctions02/Utility/DitherTemporalAA'))
wet.wire(node(u.MaterialExpressionPerInstanceFadeAmount,'InstanceFade'),dither,L.get_material_expression_input_names(dither)[0])
wet.connect(grass,'OPACITY_MASK',dither)
understory['apply_blade'](wet,grass)
save(grass)
def foliage(kind,mat):
    mesh=geometry('SM_'+kind,mat)
    for level in (1,2):
        helper=geometry('SM_'+kind+'_LOD'+str(level),mat,'/Temp/ForestUnderfootAuthoring')
        if SM.set_lod_from_static_mesh(mesh,level,helper,0,True)!=level:raise RuntimeError('LOD copy '+kind)
    if not SM.set_lod_screen_sizes(mesh,[1.,.052,.020]):raise RuntimeError('LOD screen sizes '+kind)
    SM.remove_collisions(mesh)
    return save(mesh)


palette=[foliage(kind,grass) for kind in GRASSES]
herb=material('M_JungleGinger')
herb.set_editor_property('two_sided',True)
herb.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
herb.set_editor_property('shading_model',u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
herb.set_editor_property('opacity_mask_clip_value',.32)
herb.set_editor_property('max_world_position_offset_displacement',2.5)
channels={}
for suffix,compression,srgb,sampler in [('B-O','TC_DEFAULT',True,'COLOR'),('N','TC_NORMALMAP',False,'NORMAL'),('ORT','TC_MASKS',False,'MASKS')]:
    src=BATCH/'JungleGinger'/'Textures'/('T_sgbms_2K_'+suffix+'.png')
    tex=load_file(src,DEST+'/Textures','T_JungleGinger_'+suffix.replace('-',''),u.Texture2D)
    tex.set_editor_property('compression_settings',getattr(u.TextureCompressionSettings,compression))
    tex.set_editor_property('srgb',srgb);save(tex)
    n=wet.node(herb,u.MaterialExpressionTextureSample,'Leaf'+sampler)
    n.set_editor_property('texture',tex);n.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+sampler))
    channels[suffix]=n
c,n,ort=(channels[k] for k in ('B-O','N','ORT'))
wet.connect(herb,'BASE_COLOR',c)
wet.connect(herb,'SUBSURFACE_COLOR',wet.custom(herb,'LeafTransmit','return C*lerp(.33,.73,T);',{'C':c,'T':(ort,'B')},3))
wet.connect(herb,'NORMAL',n);wet.connect(herb,'AMBIENT_OCCLUSION',(ort,'R'))
pos,w,_=wet.common(herb)
wet.connect(herb,'ROUGHNESS',wet.custom(herb,'LeafWetness','return max(.22,R*lerp(1.,.62,saturate(W.x)));',{'R':(ort,'G'),'W':w}))
d=wet.node(herb,u.MaterialExpressionMaterialFunctionCall,'LeafDither')
d.set_editor_property('material_function',u.load_asset('/Engine/Functions/Engine_MaterialFunctions02/Utility/DitherTemporalAA'))
wet.wire(wet.node(herb,u.MaterialExpressionPerInstanceFadeAmount,'LeafFade'),d,L.get_material_expression_input_names(d)[0])
mask=wet.node(herb,u.MaterialExpressionMultiply,'LeafMask');wet.wire((c,'A'),mask,'A');wet.wire(d,mask,'B')
wet.connect(herb,'OPACITY_MASK',mask)
wind=wet.node(herb,u.MaterialExpressionCollectionParameter,'LeafWind')
wind.set_editor_property('collection',u.load_asset(wet.MPC));wind.set_editor_property('parameter_name','ForestWind')
wet.connect(herb,'WORLD_POSITION_OFFSET',wet.custom(herb,'LeafSway',
    understory['LEAF_SWAY'],
    {'Local':wet.node(herb,u.MaterialExpressionPreSkinnedPosition,'LeafLocal'),'W':wind,'P':pos,'T':wet.node(herb,u.MaterialExpressionTime,'LeafTime')},3))
save(herb)
herbs=[foliage('JungleGinger'+v,herb) for v in ('D','E')]


def scan(kind):
    mat=material('M_'+kind)
    for suffix,compression,srgb,sampler in [
        ('B','TC_DEFAULT',True,'SAMPLERTYPE_COLOR'),('N','TC_NORMALMAP',False,'SAMPLERTYPE_NORMAL'),
        ('ORM','TC_MASKS',False,'SAMPLERTYPE_MASKS')]:
        src=next((BATCH/kind/'Textures').glob('*_'+suffix+'.png'))
        tex=load_file(src,DEST+'/Textures','T_'+kind+'_'+suffix,u.Texture2D)
        tex.set_editor_property('compression_settings',getattr(u.TextureCompressionSettings,compression))
        tex.set_editor_property('srgb',srgb);save(tex)
        sample=wet.node(mat,u.MaterialExpressionTextureSample,kind+suffix)
        sample.set_editor_property('texture',tex);sample.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,sampler))
        if suffix=='B':wet.connect(mat,'BASE_COLOR',sample)
        if suffix=='N':wet.connect(mat,'NORMAL',sample)
        if suffix=='ORM':
            wet.connect(mat,'AMBIENT_OCCLUSION',(sample,'R'))
            wet.connect(mat,'METALLIC',(sample,'B'))
            param=wet.node(mat,u.MaterialExpressionCollectionParameter,kind+'Weather')
            param.set_editor_property('collection',u.load_asset(wet.MPC));param.set_editor_property('parameter_name','RainforestWeather')
            wet.connect(mat,'ROUGHNESS',wet.custom(mat,'SurfaceRoughness','return max(.19,Dry*lerp(1.,.65,saturate(W.x)));',{'Dry':(sample,'G'),'W':param}))
    save(mat)
    mesh=geometry('SM_'+kind,mat)
    SM.remove_collisions(mesh)
    if kind=='MossyForestBoulder':
        if SM.add_simple_collisions(mesh,u.ScriptCollisionShapeType.NDOP26)<0:raise RuntimeError('Boulder collision')
    return save(mesh)


twigs=[scan(kind) for kind in SCANS[:2]]
boulder=scan(SCANS[2])
for path in GROUND:
    terrain=E.load_asset(path);wet.apply_ground(terrain);save(terrain)
pond=E.load_asset(POND);wet.apply_water(pond);save(pond)
da=E.load_asset(DATA)
da.set_editor_property('rainforest_grass',palette)
da.set_editor_property('rainforest_twigs',twigs)
da.set_editor_property('rainforest_bank_boulder',boulder)
da.set_editor_property('rainforest_herbs',herbs)
save(da)
(BATCH/'Receipts/saved.json').write_text(json.dumps(saved,indent=2),encoding='utf8')
u.log('FOREST_UNDERFOOT_SAVED '+str(len(saved)))
