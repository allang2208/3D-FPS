"""Author broadblade-only guard finishes, preserving gem/bezel and native UVs."""
from pathlib import Path
import json
import sys
import unreal as u

P=Path('D:/FPS3D/FPSGAME/SourceAssets/HighlandBroadbladeGuardFinish20261106')
ROOT=P.parents[1]
sys.path.insert(0,str(P))
from seat_finish import REVISION as SEAT_REVISION, native_protection
DEST='/Game/Weapons/HighlandClaymore20260922/BroadbladeGuardFinish20261106'
REV='BroadbladeGuardFinish20261106R1'
SHARED='SharedTwoHandFinish20261101V1 '
L=u.MaterialEditingLibrary
E=u.EditorAssetLibrary
catalog_path=ROOT/'Content/ColdSteelData/highland-claymore-modules.json'
catalog=json.loads(catalog_path.read_text(encoding='utf-8-sig'))
inputs=json.loads((P/'inputs.json').read_text(encoding='utf-8'))
receipt={'complete':False,'gameplay_tested':False,'materials':[],'meshes':[]}

if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() is not None:
    raise RuntimeError('Preserving active PIE; finish asset authoring requires playback to stop.')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_path_name().startswith(DEST):
        raise RuntimeError('Preserving unsaved target '+package.get_path_name())

def record():
    (P/'saved-assets.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def save(asset,kind):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    receipt[kind].append(asset.get_path_name());record()

def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for key,value in props.items():n.set_editor_property(key,value)
    return n

def wire(src,dst,pin,channel=''):
    names=[str(x) for x in L.get_material_expression_input_names(dst)]
    norm=lambda s:s.replace(' ','').replace('_','').lower()
    actual=next((n for n in names if norm(n)==norm(pin)),None)
    if actual is None and pin=='Input' and len(names)==1:actual=names[0]
    if actual is None or not L.connect_material_expressions(src,channel,dst,actual):
        raise RuntimeError('Missing material input '+pin+' '+str(names))

def custom(m,label,code,width,links):
    n=node(m,u.MaterialExpressionCustom,desc=REV+' '+label,code=code,
           output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
    pins=[]
    for name in links:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    n.set_editor_property('inputs',pins)
    for name,(src,channel) in links.items():wire(src,n,name,channel)
    return n

def root(m,field):
    prop=getattr(u.MaterialProperty,'MP_'+field)
    src=L.get_material_property_input_node(m,prop)
    return src,str(L.get_material_property_input_node_output_name(m,prop)) if src else ''

def input_of(m,n,pin):
    for name,src in zip(L.get_material_expression_input_names(n),L.get_inputs_for_material_expression(m,n)):
        if str(name)==pin and src:
            return src,str(L.get_input_node_output_name_for_material_expression(n,src))
    raise RuntimeError('Missing input '+pin+' in '+n.get_name())

def output(src,field):
    if not L.connect_material_property(src,'',getattr(u.MaterialProperty,'MP_'+field)):
        raise RuntimeError('Missing property '+field)

donor=u.load_asset('/Game/Weapons/HighlandClaymore20260922/Materials/M_HighlandClaymoreSurface')
recipes={}
for n in L.get_material_expressions(donor):
    if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc')).startswith(SHARED):
        recipes[str(n.get_editor_property('desc'))[len(SHARED):]]=str(n.get_editor_property('code'))
(P/'finish-recipes.json').write_text(json.dumps(recipes,indent=2)+'\n',encoding='utf-8')

def add_finishes(m):
    nodes=list(L.get_material_expressions(m))
    fields={str(n.get_editor_property('desc'))[len(SHARED):]:n for n in nodes
            if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc')).startswith(SHARED)}
    if 'BASE_COLOR' in fields:
        return {f:fields[f] for f in ['BASE_COLOR','ROUGHNESS','NORMAL','METALLIC','ANISOTROPY','TANGENT']}
    mode=node(m,u.MaterialExpressionScalarParameter,parameter_name='BladeFinishMode',default_value=0.)
    mask=node(m,u.MaterialExpressionConstant,r=0.)
    pos=node(m,u.MaterialExpressionVertexInterpolator);wire(node(m,u.MaterialExpressionPreSkinnedPosition),pos,'Input')
    normal=node(m,u.MaterialExpressionVertexInterpolator);wire(node(m,u.MaterialExpressionPreSkinnedNormal),normal,'Input')
    coords=custom(m,'coordinates',recipes['surface coordinates'],3,{'P':(pos,''),'N':(normal,'')})
    uv=custom(m,'crystal atlas',recipes['crystal atlas'],2,{'P':(coords,'')})
    tex=u.load_asset('/Game/Weapons/AzureRunesword20260913/MeteoricIronRefinement20261101/T_MeteoricCrystalFieldV2')
    crystal=node(m,u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    wire(uv,crystal,'UVs')
    edge=custom(m,'edge',recipes['beveled edges'],1,{'N':(normal,'')})
    direction=custom(m,'brush',recipes['crystal brush direction'],3,{'Crystal':(crystal,'RGBA'),'N':(normal,'')})
    tangent_space=bool(m.get_editor_property('tangent_space_normal'))
    transform=node(m,u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
                   transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT if tangent_space else u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    wire(direction,transform,'Input')
    results={}
    for field in ['BASE_COLOR','ROUGHNESS','NORMAL','METALLIC','ANISOTROPY','TANGENT']:
        src,out=root(m,field);target=None
        if src and isinstance(src,u.MaterialExpressionCustom) and 'Data.' in str(src.get_editor_property('code')):
            target=src;src,out=input_of(m,target,'Base')
        if not src:
            src=node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(1,0,0,1)) if field=='TANGENT' else node(m,u.MaterialExpressionConstant,r=0.)
        links={'Base':(src,out),'Mode':(mode,'')}
        if field in ['BASE_COLOR','ROUGHNESS','NORMAL','METALLIC']:links['Mask']=(mask,'')
        if field in ['BASE_COLOR','ROUGHNESS','NORMAL']:links['P']=(coords,'')
        if field in ['BASE_COLOR','ROUGHNESS','ANISOTROPY']:links.update(Crystal=(crystal,'RGBA'),Edge=(edge,''))
        if field=='TANGENT':links['Brush']=(transform,'')
        result=custom(m,field,recipes[field],3 if field in ['BASE_COLOR','NORMAL','TANGENT'] else 1,links)
        if target:wire(result,target,'Base')
        else:output(result,field)
        results[field]=result
    return results

def protect_gem(m,fields):
    # Physical diamond/bezel footprint from JunctionBlendV5 authoring, metres
    # converted to the unchanged centimetre-local coordinate used by UE meshes.
    pos=node(m,u.MaterialExpressionVertexInterpolator);wire(node(m,u.MaterialExpressionPreSkinnedPosition),pos,'Input')
    mask=custom(m,'gem and bezel preservation',
        native_protection(m),
        1,{'P':(pos,'')})
    for field,finish in fields.items():
        base,channel=input_of(m,finish,'Base')
        consumers=[]
        for n in L.get_material_expressions(m):
            for name,src in zip(L.get_material_expression_input_names(n),L.get_inputs_for_material_expression(m,n)):
                if src==finish:consumers.append((n,str(name)))
        property_src,_=root(m,field)
        keep=node(m,u.MaterialExpressionLinearInterpolate,desc=REV+' preserve '+field)
        wire(finish,keep,'A');wire(base,keep,'B',channel);wire(mask,keep,'Alpha')
        for target,pin in consumers:wire(keep,target,pin)
        if property_src==finish:output(keep,field)

replacements={}
for path,info in inputs['materials'].items():
    # The red inlay is a separate decorative insert, not the metal body.
    if path.rsplit('.',1)[-1]=='M_Cloven_Inlay':continue
    name='M_BroadbladeGuard_'+path.rsplit('.',1)[-1].removeprefix('M_')
    target=DEST+'/Materials/'+name
    m=u.load_asset(target)
    if m:
        if E.get_metadata_tag(m,'BroadbladeGuardFinishRevision')!=REV:
            raise RuntimeError('Preserving existing unowned material '+target)
    else:
        m=E.duplicate_asset(path.split('.')[0],target)
        if not m:raise RuntimeError('Material copy failed '+path)
        fields=add_finishes(m)
        protect_gem(m,fields)
        # Route PBR through Substrate while retaining the existing wetness,
        # texture sampling, native emissions and UV-space normal data.
        slab,_=root(m,'FRONT_MATERIAL')
        if not slab:slab=node(m,u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
        for field,pin in [('BASE_COLOR','BaseColor'),('ROUGHNESS','Roughness'),('METALLIC','Metallic'),
                          ('NORMAL','Normal'),('EMISSIVE_COLOR','EmissiveColor'),('ANISOTROPY','Anisotropy'),('TANGENT','Tangent')]:
            src,out=root(m,field)
            if src:wire(src,slab,pin,out)
        output(slab,'FRONT_MATERIAL')
        errors=L.recompile_material(m)
        if errors:raise RuntimeError('Material compilation failed '+str(errors))
        E.set_metadata_tag(m,'BroadbladeGuardFinishRevision',REV)
        E.set_metadata_tag(m,'HighlandSeatFinish',SEAT_REVISION)
        E.set_metadata_tag(m,'BroadbladeGuardSource',path)
        save(m,'materials')
    replacements[path]=m

mesh_paths={}
for option,info in inputs['guards'].items():
    target=DEST+'/Meshes/SM_BroadbladeGuard_'+option
    mesh=u.load_asset(target)
    if mesh:
        if E.get_metadata_tag(mesh,'BroadbladeGuardFinishRevision')!=REV:
            raise RuntimeError('Preserving existing unowned mesh '+target)
    else:
        mesh=E.duplicate_asset(info['mesh'].split('.')[0],target)
        if not mesh:raise RuntimeError('Guard copy failed '+option)
        for index,slot in enumerate(mesh.static_materials):
            replacement=replacements.get(slot.material_interface.get_path_name())
            if replacement:mesh.set_material(index,replacement)
        E.set_metadata_tag(mesh,'BroadbladeGuardFinishRevision',REV)
        E.set_metadata_tag(mesh,'BroadbladeGuardSource',info['mesh'])
        save(mesh,'meshes')
    mesh_paths[option]=mesh.get_path_name()

# Apply only the broadblade fitting entry to the freshest catalog snapshot.
before=catalog_path.read_bytes()
data=json.loads(before.decode('utf-8-sig'))
for option,mesh_path in mesh_paths.items():
    spec=data['slots']['guard'][option]
    if spec['mesh']!=inputs['guards'][option]['mesh']:
        raise RuntimeError('Guard source changed during authoring; preserve current catalog')
    spec.setdefault('mesh_by_blade',{})['highland_broadblade']=mesh_path
if catalog_path.read_bytes()!=before:raise RuntimeError('Catalog changed concurrently')
if not (P/'catalog-before.json').exists():(P/'catalog-before.json').write_bytes(before)
catalog_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt.update(complete=True,guard_meshes=mesh_paths,scope='highland_broadblade only',geometry_changed=False)
record()
print('BROADBLADE_GUARD_FINISH_SAVED')
