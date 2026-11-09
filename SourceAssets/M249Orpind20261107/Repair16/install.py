"""Save the M249-only finish variants and the five revised stock interfaces."""
import unreal as u,json,hashlib,zipfile,gc
from pathlib import Path
r=Path(__file__).resolve().parent;p=r.parents[2]
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
D='/Game/Weapons/M249/FinishUnified20261108'
data=json.loads((r/'current_assets.json').read_text())
old=json.loads((r.parent/'Repair13/install_receipt.json').read_text())
origins={v:k for k,v in old['materials'].items()}
stocks=json.loads((r/'stock_exports.json').read_text())
targets={k:v for k,v in data['meshes'].items() if '/CommonParts20261108/' in k or '/CommonOptics20261108/' in k}
receipt=r/'install_receipt.json'
report=json.loads(receipt.read_text()) if receipt.exists() else dict(saved={},materials={},meshes={},stocks={},runtime_tested=False)
report['complete']=False
def record():receipt.write_text(json.dumps(report,indent=2))
def disk(path):return p/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing '+path)
    return a
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    report['saved'][a.get_path_name().split('.')[0]]=hashlib.sha256(disk(a.get_path_name()).read_bytes()).hexdigest();record()
    return a
def clone(src,dst):
    if E.does_asset_exist(dst):return load(dst)
    a=E.duplicate_asset(src,dst)
    if not a:raise RuntimeError('Clone '+src)
    return a
if '-run=' not in u.SystemLibrary.get_command_line().lower():raise RuntimeError('Stock mesh replacement requires the offline asset batch; existing editor retained')
for path in targets:
    expected=report['saved'].get(path,data['hashes'][path])
    if hashlib.sha256(disk(path).read_bytes()).hexdigest()!=expected:raise RuntimeError('Changed target retained '+path)
if not (r/'before.zip').exists():
    with zipfile.ZipFile(r/'before.zip','w',zipfile.ZIP_DEFLATED) as z:
        for path in targets:z.write(disk(path),disk(path).relative_to(p))
    (r/'before_hashes.json').write_text(json.dumps({k:data['hashes'][k] for k in targets},indent=2))
def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(src,dst,pin):
    a,out=src if isinstance(src,tuple) else (src,'')
    if not L.connect_material_expressions(a,out,dst,pin):raise RuntimeError('Connect '+pin)
def output(src,prop):
    a,out=src if isinstance(src,tuple) else (src,'')
    if not L.connect_material_property(a,out,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Output '+prop)
def custom(m,label,code,pins,size):
    n=node(m,u.MaterialExpressionCustom,description=label,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
    args=[]
    for key in pins:
        v=u.CustomInput();v.set_editor_property('input_name',key);args.append(v)
    n.set_editor_property('inputs',args)
    for key,src in pins.items():wire(src,n,key)
    return n
def scalar(m,name,value):return node(m,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
def const(m,value):
    return node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*value,1)) if isinstance(value,tuple) else node(m,u.MaterialExpressionConstant,r=value)
def original(m,prop,default):
    n=L.get_material_property_input_node(m,getattr(u.MaterialProperty,'MP_'+prop))
    return (n,L.get_material_property_input_node_output_name(m,getattr(u.MaterialProperty,'MP_'+prop))) if n else const(m,default)
def unwrap_wet(m,src):
    n=src[0] if isinstance(src,tuple) else src
    if isinstance(n,u.MaterialExpressionCustom):
        names=[str(x.get_editor_property('input_name')) for x in n.get_editor_property('inputs')]
        if names==['Base','Data']:
            children=L.get_inputs_for_material_expression(m,n)
            return children[0],children[1]
    return src,None
def compile_save(m):
    errors=list(L.recompile_material(m) or [])
    if errors:raise RuntimeError('Compile '+str(errors[:4]))
    return save(m)
ws=next(v for k,v in data['materials'].items() if 'MI_WS_CleanSatinSteel' in k)
ws_code={c['description']:c['code'] for c in ws['customs']}
beads=next(c['code'] for m in data['materials'].values() for c in m['customs'] if c['description']=='WeatherBeads')
def classify(src):
    original=origins.get(src,src).lower()
    if any(x in original for x in ('recess','titaniumtrim','champagne','redinset')):return None
    owned=src.startswith('/Game/Weapons/M249/')
    if not owned:return None
    if 'rubber' in original:return 'rubber'
    if 'polymer' in original:return 'polymer'
    if any(x in original for x in ('_stock_metal_','_muzzle_','stock_graphite','stock_steel','adapter','commonrail')):return 'metal'
    return 'mixed'
cache={}
def finish(src):
    if src in cache:return cache[src]
    role=classify(src)
    if role is None:cache[src]=load(src);return cache[src]
    info=data['materials'][src];key=hashlib.sha1(src.encode()).hexdigest()[:12]
    dst=D+'/Materials/MI_M249_'+key
    if src in report['materials']:
        cache[src]=load(report['materials'][src]['asset']);return cache[src]
    mat=clone(info['base'],D+'/Master/M_M249_'+key)
    optical='/MI_M249Optic_' in src
    rough=.70 if role=='rubber' else .55 if role=='polymer' else .44 if optical else .40 if '_muzzle_' in origins.get(src,'').lower() or 'Silencer' in origins.get(src,'') else .42
    ws_parent=any(c['description']=='WS_ColorRough' for c in info['customs'])
    if not ws_parent and E.get_metadata_tag(mat,'M249Repair16')!='complete':
        color,weather=unwrap_wet(mat,original(mat,'BASE_COLOR',(.034,.035,.037)))
        old_rough,_=unwrap_wet(mat,original(mat,'ROUGHNESS',.42))
        normal,_=unwrap_wet(mat,original(mat,'NORMAL',(0,0,1)))
        metal=original(mat,'METALLIC',0.)
        if role=='metal':metal=const(mat,1.)
        if role in ('polymer','rubber'):metal=const(mat,0.)
        metal=custom(mat,'M249 WS material identity','return smoothstep(.2,.8,Value);',{'Value':metal},1)
        pos=node(mat,u.MaterialExpressionVertexInterpolator);wire(node(mat,u.MaterialExpressionPreSkinnedPosition),pos,'VS')
        nor=node(mat,u.MaterialExpressionVertexInterpolator);wire(node(mat,u.MaterialExpressionPreSkinnedNormal),nor,'VS')
        grain=custom(mat,'WS_Grain',ws_code['WS_Grain'],{
            'P':pos,
            'N':nor,
            'Tex':node(mat,u.MaterialExpressionTextureObjectParameter,parameter_name='M249_Grain',texture=load(ws['textures']['GrainTexture']),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),
            'TileCm':scalar(mat,'M249_GrainTileCm',2.)},4)
        cr=custom(mat,'M249 unified dry colour and roughness',
            'float l=dot(Base,float3(.2126,.7152,.0722));'
            'float marks=smoothstep(.45,.75,min(Base.r,min(Base.g,Base.b)));'
            'float chroma=max(Base.r,max(Base.g,Base.b))-min(Base.r,min(Base.g,Base.b));'
            'float keep=max(marks,smoothstep(.04,.12,chroma));'
            'float interior=Interior*(1-smoothstep(.002,.008,l));'
            'float3 target=lerp(Poly,Steel,Metal);'
            'float3 finish=target*lerp(1,clamp(l/.034,.8,1.2),.06);'
            'float3 c=lerp(finish,Base,max(keep,interior));'
            'float center=lerp(PolyRough,SteelRough,Metal);'
            'float rr=clamp(center+clamp((SourceR-.45)*.06,-.025,.025)+(Grain.r-.5)*.024+(Grain.g-.5)*.010,.25,.85);'
            'return float4(c,lerp(rr,.75,interior));',
            {'Base':color,'SourceR':old_rough,'Metal':metal,'Grain':grain,
             'Poly':const(mat,(.0103,.0103,.0103) if role=='rubber' else (.019,.019,.018)),
             'Steel':const(mat,(.034,.035,.037)),
             'PolyRough':scalar(mat,'M249_PolymerRoughness',.70 if role=='rubber' else .55),
             'SteelRough':scalar(mat,'M249_SteelRoughness',rough),
             'Interior':scalar(mat,'M249_PreserveScopeInterior',1. if optical else 0.)},4)
        if weather is None:
            weather=custom(mat,'M249 single weather beads',beads,{
                'UV':node(mat,u.MaterialExpressionTextureCoordinate),'Wet':scalar(mat,'WeaponWetness',0.),
                'Scale':scalar(mat,'BeadScale',78.),'RainTime':node(mat,u.MaterialExpressionTime),
                'RainGravity':node(mat,u.MaterialExpressionVectorParameter,parameter_name='RainGravity',default_value=u.LinearColor(0,1,0,0)),
                'RainFlow':scalar(mat,'RainFlowStrength',.65),'RainBeading':scalar(mat,'RainBeadStrength',1.)},4)
        wet=custom(mat,'WS_Wet',ws_code['WS_Wet'],{'CR':cr,'Data':weather,'Metal':metal,'SurfaceResponse':scalar(mat,'M249_SurfaceResponse',4. if role=='rubber' else 3. if role=='polymer' else 1. if role=='metal' else 0.)},4)
        rgb=node(mat,u.MaterialExpressionComponentMask,r=True,g=True,b=True);wire(wet,rgb,'')
        alpha=node(mat,u.MaterialExpressionComponentMask,a=True);wire(wet,alpha,'')
        output(rgb,'BASE_COLOR');output(alpha,'ROUGHNESS');output(metal,'METALLIC')
        output(custom(mat,'WS_WetNormal',ws_code['WS_WetNormal'],{'Base':normal,'Data':weather},3),'NORMAL')
        E.set_metadata_tag(mat,'M249Repair16','complete')
    for name in ('automatically_set_usage_in_editor','used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing'):mat.set_editor_property(name,False)
    output(scalar(mat,'M249_Specular',.5),'SPECULAR')
    compile_save(mat)
    source=load(src)
    if isinstance(source,u.MaterialInstanceConstant):mi=clone(src,dst)
    elif E.does_asset_exist(dst):mi=load(dst)
    else:mi=A.create_asset(dst.rsplit('/',1)[1],D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(mi,mat)
    for n,v in info.get('scalars',{}).items():L.set_material_instance_scalar_parameter_value(mi,n,v)
    for n,v in info.get('vectors',{}).items():L.set_material_instance_vector_parameter_value(mi,n,u.LinearColor(*v))
    for n,v in info.get('textures',{}).items():
        if v:L.set_material_instance_texture_parameter_value(mi,n,load(v))
    if ws_parent:
        for n,v in {'Roughness':rough,'GrainTileCm':2.,'GrainRoughness':.012,'MottleRoughness':.005,'MottleColor':0.,'EdgeWear':.025,'EdgeHighlight':.06,'CavityDarken':.025,'CavityRoughness':.018,'ScratchAmount':0.,'HandlingPolish':0.,'Stipple':0.,'SourceRoughnessWeight':.08}.items():L.set_material_instance_scalar_parameter_value(mi,n,v)
        L.set_material_instance_vector_parameter_value(mi,'FinishColor',u.LinearColor(.034,.035,.037,1))
        L.set_material_instance_vector_parameter_value(mi,'EdgeColor',u.LinearColor(.085,.088,.092,1))
    L.update_material_instance(mi);save(mi);cache[src]=mi
    report['materials'][src]=dict(asset=mi.get_path_name(),role=role,roughness=rough,source_origin=origins.get(src,src),single_weather_layer=True);record()
    print('M249_UNIFIED_MATERIAL',key,role,flush=True)
    return mi
for rows in targets.values():
    for row in rows:finish(row['material'])
# Build the revised five meshes from new import settings at their existing paths.
# Exact paths are backed up above; no other assets are removed or rebuilt.
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for path,rows in targets.items():
        if path in report['meshes']:continue
        key=path.rsplit('/',1)[1].removeprefix('SM_M249_')
        if key in stocks and '/CommonParts20261108/' in path:
            opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
            opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
            sm=opt.static_mesh_import_data;sm.combine_meshes=True;sm.auto_generate_collision=False;sm.generate_lightmap_u_vs=False;sm.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
            t=u.AssetImportTask();t.filename=stocks[key]['fbx'];t.destination_path=path.rsplit('/',1)[0];t.destination_name=path.rsplit('/',1)[1];t.automated=True;t.replace_existing=False;t.save=False;t.options=opt;t.factory=u.FbxFactory()
            if E.does_asset_exist(path) and not E.delete_asset(path):raise RuntimeError('Cannot replace owned stock '+path)
            A.import_asset_tasks([t])
            mesh=load(path);u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
            subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
            settings=subsystem.get_lod_build_settings(mesh,0);settings.generate_lightmap_u_vs=False;settings.recompute_normals=False;settings.recompute_tangents=True
            subsystem.set_lod_build_settings(mesh,0,settings)
            if not u.ASH12AttachmentAssetTools.finish_and_validate_build(mesh):raise RuntimeError('Static mesh build incomplete '+path)
            report['stocks'][path]=stocks[key]
        else:mesh=load(path)
        materials={s['slot']:finish(s['material']) for s in rows}
        slots=list(mesh.static_materials)
        for i,slot in enumerate(slots):
            name=str(slot.get_editor_property('imported_material_slot_name'))
            if name not in materials:name=str(slot.material_slot_name)
            if name not in materials:raise RuntimeError('Unexpected imported slot '+path+' '+name)
            slot.material_interface=materials[name];slots[i]=slot
        mesh.set_editor_property('static_materials',slots);save(mesh)
        report['meshes'][path]=[dict(slot=str(s.material_slot_name),material=s.material_interface.get_path_name()) for s in mesh.static_materials];record()
        print('M249_UNIFIED_MESH_SAVED',path,flush=True);gc.collect()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
report['complete']=True;record();print('M249_REPAIR16_COMPLETE',len(report['meshes']),len(report['materials']),len(report['stocks']),flush=True)
