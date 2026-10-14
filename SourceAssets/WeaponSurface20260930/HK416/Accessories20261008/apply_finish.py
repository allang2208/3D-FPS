"""Compile/save HK416 accessory-only material variants and bind active meshes."""
import json,hashlib,shutil
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve()
if P!=Path('D:/FPS3D/FPSGAME'):raise RuntimeError('Wrong project')
C=json.loads((O/'Input/current.json').read_text());R=json.loads((O/'recipe.json').read_text())
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active PIE; no accessory assets written')
RP=O/'apply-receipt.json';receipt=json.loads(RP.read_text()) if RP.exists() else {'version':R['version'],'materials':{},'meshes':{},'graphs':{},'weather':False,'complete':False,'game_tested':False,'geometry_changed':False}
def record():RP.write_text(json.dumps(receipt,indent=2))
def load(path):
    ob=u.load_asset(path)
    if ob is None:raise RuntimeError('Missing asset '+path)
    return ob
def file(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def backup(path):
    dst=O/'Before'/(path.split('.')[0].removeprefix('/Game/')+'.uasset');dst.parent.mkdir(parents=True,exist_ok=True)
    if not dst.exists():shutil.copy2(file(path),dst)
def save(ob):
    if not u.EditorLoadingAndSavingUtils.save_packages([ob.get_outermost()],False):raise RuntimeError('Save failed '+ob.get_path_name())
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for path in R['bindings']:
    if path.split('.')[0] in dirty:raise RuntimeError('Preserve unsaved attachment '+path)
    if path not in receipt['meshes'] and hashlib.sha256(file(path).read_bytes()).hexdigest()!=C['sources'][path]:raise RuntimeError('Attachment changed during authoring '+path)
wetpath=C['weather']['path']
if wetpath.split('.')[0] in dirty:raise RuntimeError('Preserve unsaved weather table')
if any(p.startswith(R['root']) for p in dirty):raise RuntimeError('Preserve unsaved accessory finish')
def node(m,kind,**props):
    n=L.create_material_expression(m,kind)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(src,dst,pin):
    ob,out=src if isinstance(src,tuple) else (src,'')
    if not L.connect_material_expressions(ob,out,dst,pin):raise RuntimeError('Could not connect '+pin)
def custom(m,code,inputs,size=1):
    n=node(m,u.MaterialExpressionCustom,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
    pins=[]
    for name in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
    n.set_editor_property('inputs',pins)
    for name,src in inputs.items():wire(src,n,name)
    return n
def output(m,src,key):
    ob,ch=src if isinstance(src,tuple) else (src,'')
    if not L.connect_material_property(ob,ch,key):raise RuntimeError('Material output failed')
def output_node(m,key):return L.get_material_property_input_node(m,key)
def scalar(m,name,value):return node(m,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
def grain(m):
    pos=node(m,u.MaterialExpressionVertexInterpolator);nor=node(m,u.MaterialExpressionVertexInterpolator)
    wire(node(m,u.MaterialExpressionPreSkinnedPosition),pos,'VS');wire(node(m,u.MaterialExpressionPreSkinnedNormal),nor,'VS')
    tex=node(m,u.MaterialExpressionTextureObjectParameter,parameter_name='AccessoryFineGrain',
             texture=load('/Game/Weapons/HK416/SurfaceStandard20261001/Textures/T_HK416_R01_FineGrain'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    n=custom(m,(O.parent/'Refine01/FineGrain.hlsl').read_text(),{'P':pos,'N':nor,'T':tex},4)
    return custom(m,'return Detail.r-.5;',{'Detail':n})
def private_graph(t):
    key=t['base']+'|'+t['mode']
    if key in receipt['graphs']:return load(receipt['graphs'][key])
    dest=R['root']+'/Master/M_HK416_A08_'+hashlib.sha1(key.encode()).hexdigest()[:12]
    if E.does_asset_exist(dest):raise RuntimeError('Occupied material destination '+dest)
    m=E.duplicate_asset(t['base'],dest)
    if m is None:raise RuntimeError('Material clone failed')
    for name in ('used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing'):m.set_editor_property(name,False)
    if t['mode'] in ('stock','thermal'):
        rough=output_node(m,u.MaterialProperty.MP_ROUGHNESS)
        if not isinstance(rough,u.MaterialExpressionLinearInterpolate):raise RuntimeError('Unexpected source weather graph')
        wire(scalar(m,'AccessoryWetRoughness',t['scalars']['AccessoryWetRoughness']),rough,'B')
        if t['mode']=='stock':
            normal=output_node(m,u.MaterialProperty.MP_NORMAL)
            amount=scalar(m,'AccessoryNormalDetail',1.)
            refined=custom(m,'return normalize(float3(N.xy*Strength,max(N.z,.001)));',{'N':(normal,'RGB'),'Strength':amount},3)
            output(m,refined,u.MaterialProperty.MP_NORMAL)
        else:
            dry=L.get_inputs_for_material_expression(m,rough)[0]
            refined=custom(m,'return clamp(Base+Grain*2.*Amount,.12,.85);',{'Base':dry,'Grain':grain(m),'Amount':scalar(m,'AccessoryGrain',0.)})
            wire(refined,rough,'A')
    elif t['mode']=='blessed':
        color=output_node(m,u.MaterialProperty.MP_BASE_COLOR);rough=output_node(m,u.MaterialProperty.MP_ROUGHNESS)
        tint=node(m,u.MaterialExpressionVectorParameter,parameter_name='SurfaceTint',default_value=u.LinearColor(*t['vectors']['SurfaceTint'],1.))
        wire(tint,color,'Base');wire(scalar(m,'DryRoughness',t['scalars']['DryRoughness']),rough,'Rough')
        detail=grain(m);wire(detail,color,'Grain');wire(detail,rough,'Grain')
        color.set_editor_property('code','return Base*(1.0-saturate(Wet)*.07);')
        rough.set_editor_property('code','return clamp(lerp(Rough,max(.12,Rough*.76),saturate(Wet))+Grain*.014,.08,1.0);')
        output(m,scalar(m,'Metallic',t['scalars']['Metallic']),u.MaterialProperty.MP_METALLIC)
    E.set_metadata_tag(m,'HK416AccessoryFinish',R['version'])
    E.set_metadata_tag(m,'SourceGraph',t['base'])
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Material compile failed '+str(errors))
    save(m);receipt['graphs'][key]=m.get_path_name();record();return m
for key,t in R['targets'].items():
    if key in receipt['materials']:continue
    source=load(t['source'])
    if E.does_asset_exist(t['asset']):raise RuntimeError('Occupied instance destination '+t['asset'])
    if t['mode']=='existing_authored':
        mi=E.duplicate_asset(t['source'],t['asset'])
    else:
        parent=private_graph(t);folder,name=t['asset'].rsplit('/',1)
        mi=A.create_asset(name,folder,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());L.set_material_instance_parent(mi,parent)
    if mi is None:raise RuntimeError('Material instance creation failed '+t['asset'])
    for name,value in t['scalars'].items():L.set_material_instance_scalar_parameter_value(mi,name,float(value))
    for name,value in t['vectors'].items():L.set_material_instance_vector_parameter_value(mi,name,u.LinearColor(*value,1.))
    L.update_material_instance(mi);E.set_metadata_tag(mi,'HK416AccessoryFinish',R['version']);E.set_metadata_tag(mi,'SourceMaterial',t['source']);save(mi)
    receipt['materials'][key]={'path':mi.get_path_name(),'mode':t['mode'],'source':t['source'],'scalars':t['scalars'],'vectors':t['vectors']};record()
    print('HK416_ACCESSORY_MATERIAL',len(receipt['materials']),flush=True)
weather=load(wetpath);mapping=dict(weather.get_editor_property('wet_materials'))
for r in receipt['materials'].values():mapping[r['path']]=load(r['path'])
backup(wetpath);weather.set_editor_property('wet_materials',mapping);save(weather);receipt['weather']=True;record()
for path,entries in R['bindings'].items():
    if path in receipt['meshes']:continue
    mesh=load(path);slots=list(mesh.static_materials)
    for b in entries:
        s=slots[b['index']]
        if str(s.material_slot_name)!=b['slot'] or s.material_interface.get_path_name()!=b['material']:raise RuntimeError('Target binding changed '+path)
        s.material_interface=load(receipt['materials'][b['key']]['path']);slots[b['index']]=s
    backup(path);mesh.set_editor_property('static_materials',slots);E.set_metadata_tag(mesh,'HK416AccessoryFinish',R['version']);save(mesh)
    receipt['meshes'][path]={'bindings':{str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials},'saved':True};record()
    print('HK416_ACCESSORY_SAVED',path,flush=True)
manifest=O.parent/'current_surface_bindings.json'
dst=O/'Before/current_surface_bindings.json'
if not dst.exists():shutil.copy2(manifest,dst)
published=json.loads(manifest.read_text());published['accessory_revision']=R['version'];published['accessory_recipe']=str(O/'recipe.json')
for path,row in receipt['meshes'].items():published['meshes'][path]=row['bindings']
manifest.write_text(json.dumps(published,indent=2),encoding='utf-8')
receipt['complete']=True;record();print('HK416_ACCESSORY_FINISH_COMPLETE',len(receipt['materials']),len(receipt['meshes']))
