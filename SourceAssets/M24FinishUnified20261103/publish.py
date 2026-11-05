"""Unify the active M24 assembly against its current receiver, retaining UVs and identities."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).resolve().parent;D=json.loads((O/'materials_before.json').read_text())
ROOT='/Game/Weapons/M24/FinishUnified20261103';E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
R={'complete':False,'materials':{},'graphs':{},'meshes':{},'preserved':{},'runtime_tested':False,'geometry_changed':False,'animation_changed':False}
def record():(O/'publish_receipt.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
def load(p):
    a=u.load_asset(p)
    if not a:raise RuntimeError('Missing '+p)
    return a
def disk(p):return Path(u.Paths.project_content_dir())/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
def backup(p):
    dest=O/'Before'/(p.split('.')[0].removeprefix('/Game/')+'.uasset');dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():raise RuntimeError('Existing backup retained; do not replay publication '+p)
    shutil.copy2(disk(p),dest)
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def clone(src,dst):
    if E.does_asset_exist(dst):raise RuntimeError('Existing authoring destination retained '+dst)
    a=E.duplicate_asset(src,dst)
    if not a:raise RuntimeError('Duplication failed '+src)
    return a
def node(m,cls,**kw):
    n=L.create_material_expression(m,cls)
    for k,v in kw.items():n.set_editor_property(k,v)
    return n
def wire(src,dst,pin):
    a,ch=src if isinstance(src,tuple) else (src,'')
    if not L.connect_material_expressions(a,ch,dst,pin):raise RuntimeError('Cannot connect '+pin)
def custom(m,label,code,pins,size):
    n=node(m,u.MaterialExpressionCustom,description=label,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
    ins=[]
    for key in pins:
        x=u.CustomInput();x.set_editor_property('input_name',key);ins.append(x)
    n.set_editor_property('inputs',ins)
    for key,src in pins.items():wire(src,n,key)
    return n
def add_input(n,key,src):
    ins=list(n.get_editor_property('inputs'));x=u.CustomInput();x.set_editor_property('input_name',key);ins.append(x)
    n.set_editor_property('inputs',ins);wire(src,n,key)
def output(m,prop):
    p=getattr(u.MaterialProperty,'MP_'+prop)
    return L.get_material_property_input_node(m,p),str(L.get_material_property_input_node_output_name(m,p))
def scalar(m,key,v):L.set_material_instance_scalar_parameter_value(m,key,float(v))
def vector(m,key,v):L.set_material_instance_vector_parameter_value(m,key,u.LinearColor(*v[:3],1.))
def compile_save(m):
    errs=L.recompile_material(m)
    if errs:raise RuntimeError('Material compile failed '+str(errs))
    save(m);R['graphs'][m.get_path_name()]={'saved':True};record()
def fine(m):
    p=node(m,u.MaterialExpressionVertexInterpolator);n=node(m,u.MaterialExpressionVertexInterpolator)
    wire(node(m,u.MaterialExpressionPreSkinnedPosition),p,'VS');wire(node(m,u.MaterialExpressionPreSkinnedNormal),n,'VS')
    tex=node(m,u.MaterialExpressionTextureObjectParameter,parameter_name='M24FineGrain',texture=load('/Game/Weapons/WeaponSurface/Textures/T_WS_Grain'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    return custom(m,'M24 common local fine grain','float3 w=pow(abs(normalize(N)),4);w/=max(dot(w,float3(1,1,1)),.0001);float3 q=P/2.;return Texture2DSample(T,TSampler,q.yz)*w.x+Texture2DSample(T,TSampler,q.xz+float2(.37,.61))*w.y+Texture2DSample(T,TSampler,q.xy+float2(.71,.13))*w.z;',{'P':p,'N':n,'T':tex},4)
host=next(m for p,m in D['materials'].items() if 'MI_M24_Regional_host.' in p)
ref=host['parameters'];METAL=ref['vector']['FinishColor'];POLY=ref['vector']['PolymerColor']
# Regional receiver graph floors its metal roughness at .48, regardless of the unused .40 parameter.
ROUGH=.48
common={k:ref['scalar'][k] for k in ['GrainTileCm','GrainRoughness','MottleRoughness','MottleColor','Stipple','EdgeWear','EdgeHighlight','ScratchAmount','HandlingPolish','Specular','RainFlowStrength','RainBeadStrength']}
common.update(Roughness=ROUGH,SourceRoughnessWeight=.06,WeaponWetness=0.)
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; preserve current assets')
for row in list(D['meshes'].values())+[dict(path=p,sha256=m['sha256']) for p,m in D['materials'].items() if p.startswith('/Game/')]:
    if row['path'].split('.')[0] in dirty:raise RuntimeError('Unsaved source retained '+row['path'])
    if hashlib.sha256(disk(row['path']).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Concurrent source change retained '+row['path'])
for p,m in D['masters'].items():
    if m['sha256'] and hashlib.sha256(disk(p).read_bytes()).hexdigest()!=m['sha256']:raise RuntimeError('Concurrent graph change retained '+p)
if any(p.startswith(ROOT) for p in dirty):raise RuntimeError('Unsaved candidate retained')
record();mapped={};graph_cache={}
def private_graph(source,mode):
    cache=(source,mode)
    if cache in graph_cache:return graph_cache[cache]
    p=ROOT+'/Master/M_M24_'+mode+'_'+hashlib.sha1(source.encode()).hexdigest()[:8]
    m=clone(source,p)
    if mode!='carbon':
        for name in ['automatically_set_usage_in_editor','used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing']:m.set_editor_property(name,False)
    ex=L.get_material_expressions(m);cs={str(n.get_editor_property('description')):n for n in ex if isinstance(n,u.MaterialExpressionCustom)}
    if mode=='stock':
        identity=next(n for n in ex if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='SourceMetallic')
        cr=cs['WS_ColorRough'];add_input(cr,'Identity',(identity,'R'))
        code=cr.get_editor_property('code').replace('float3 base=lerp(Finish,Src,saturate(SrcW));','float metal=smoothstep(.25,.75,Identity);float ink=smoothstep(.62,.85,min(Src.r,min(Src.g,Src.b)));float3 base=lerp(lerp(float3(.018,.020,.021),Finish,metal),Src,max(saturate(SrcW),ink*.35));')
        code=code.replace('float r=Rough+(SrcR-Pivot)*SrcRW;','float r=lerp(max(Rough,.59),Rough,metal)+(SrcR-Pivot)*SrcRW;')
        cr.set_editor_property('code',code);wire((identity,'R'),cs['WS_MetalAO'],'Metal')
        import runpy
        runpy.run_path(str(O/'stock_identity.py'))['apply_stock_identity'](m,L,u)
    elif mode=='carbon':
        # The bolt is an override of the whole native body slot; keep the new receiver finish outside its weave mask.
        refcodes={c['name']:c['code'] for c in D['masters'][host['master']]['codes']}
        for key in ['M24_RegionFinish','M24_SourceMarkings']:cs[key].set_editor_property('code',refcodes[key])
        normal=output(m,'NORMAL');strength=node(m,u.MaterialExpressionScalarParameter,parameter_name='ContinuityNormalStrength',default_value=.75)
        new=custom(m,'M24 native body normal continuity','return normalize(float3(N.xy*Strength,N.z));',{'N':normal,'Strength':strength},3)
        L.connect_material_property(new,'',u.MaterialProperty.MP_NORMAL)
    elif mode=='eoth':
        color=output(m,'BASE_COLOR')[0];rough=output(m,'ROUGHNESS')[0]
        src=L.get_inputs_for_material_expression(m,color)[0];sr=L.get_inputs_for_material_expression(m,rough)[0];metal=output(m,'METALLIC')
        base=custom(m,'M24 EOTH dry shell matching','float l=dot(Src,float3(.2126,.7152,.0722));float chroma=(max(Src.r,max(Src.g,Src.b))-min(Src.r,min(Src.g,Src.b)))/max(l,.015);float keep=max(1-smoothstep(.002,.010,l),max(smoothstep(.20,.55,l),smoothstep(.45,.95,chroma)));float3 target=lerp(float3(.018,.020,.021),float3(.026,.029,.032),smoothstep(.25,.75,Metal));return lerp(target*pow(max(Src,.0001)/.04,.08),Src,keep);',{'Src':(src,'RGB'),'Metal':metal},3)
        rr=custom(m,'M24 EOTH dry roughness matching','float center=lerp(.59,.48,smoothstep(.25,.75,Metal));return clamp(center+(Source-.5)*.06+(Grain.r-.5)*.012+(Grain.g-.5)*.004,.25,.85);',{'Source':(sr,'R'),'Metal':metal,'Grain':fine(m)},1)
        wire(base,color,'Base');wire(rr,rough,'Base')
    elif mode=='thermal':
        rough=output(m,'ROUGHNESS')[0]
        dry=L.get_inputs_for_material_expression(m,rough)[0]
        rr=custom(m,'M24 thermal fine roughness','return Base+(Grain.r-.5)*.012+(Grain.g-.5)*.004;',{'Base':dry,'Grain':fine(m)},1)
        wire(rr,rough,'A');wire(node(m,u.MaterialExpressionConstant,r=ROUGH*.68),rough,'B')
    elif mode=='kv':
        cr=cs['WS_ColorRough'];code=cr.get_editor_property('code')
        code=code.replace('float3 base=lerp(Finish,Src,saturate(SrcW));','float lum=dot(Src,float3(.2126,.7152,.0722));float keep=max(1-smoothstep(.002,.010,lum),smoothstep(.20,.55,lum));float3 base=lerp(Finish,Src,max(saturate(SrcW),keep));')
        cr.set_editor_property('code',code)
    elif mode=='r01':
        for c in cs.values():
            if 'physical fine roughness' in str(c.get_editor_property('description')):c.set_editor_property('code',c.get_editor_property('code').replace('P/4.','P/2.'))
    E.set_metadata_tag(m,'M24UnifiedReference',host['master']);compile_save(m);graph_cache[cache]=m;return m
def classify(path,data):
    if any(s in path for s in ['Regional_host.','Regional_scope.']):return None
    if 'CarbonBolt.' in path:return 'carbon'
    if 'SniperStock_MeshySurface.' in path:return 'stock'
    if path.endswith('M_HK416_Eo_tech.M_HK416_Eo_tech'):return 'eoth'
    if path.endswith('M_KVScope_Body.M_KVScope_Body'):return 'kv'
    if path.endswith('M_Thermal_Graphite.M_Thermal_Graphite'):return 'thermal'
    p=data['parameters'];s=p.get('scalar',{})
    if 'R01_ToneScale' in p.get('vector',{}):return 'r01'
    if 'R01_FinishTint' in p.get('vector',{}):return 'pkm'
    if 'FinishColor' in p.get('vector',{}) and 'M24' in path:
        if 'Interior' in path or 'interior' in path or 'Marking' in path:return None
        if 'Body_Static.' in path:return 'regional'
        return 'metal' if s.get('Metallic',0)>.9 else 'polymer'
    return None
for src,data in D['materials'].items():
    mode=classify(src,data)
    if not mode:R['preserved'][src]='Current receiver/scope baseline, optical, skin, interior, marking or intentional material identity';continue
    source=load(src);p=ROOT+'/Materials/MI_M24_'+mode+'_'+hashlib.sha1(src.encode()).hexdigest()[:10]
    if isinstance(source,u.MaterialInstanceConstant):mi=clone(src,p)
    else:
        folder,name=p.rsplit('/',1);mi=A.create_asset(name,folder,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());L.set_material_instance_parent(mi,source)
    scalars={};vectors={};textures={}
    if mode in ['stock','carbon','eoth','thermal','r01']:
        L.set_material_instance_parent(mi,private_graph(data['master'],mode))
    elif mode=='regional':L.set_material_instance_parent(mi,private_graph(host['master'],'regional'))
    elif mode=='kv':L.set_material_instance_parent(mi,private_graph('/Game/Weapons/M24/Surface20261027/Materials/M_M24IronSurface','kv'))
    if mode in ['metal','polymer','stock','carbon','regional','kv']:
        scalars.update(common);vectors.update(FinishColor=METAL,EdgeColor=ref['vector']['EdgeColor'])
        if mode in ['regional','carbon']:
            scalars.update({k:v for k,v in ref['scalar'].items() if k not in ['MaskUVChannel']});vectors['PolymerColor']=POLY
        elif mode=='polymer':
            scalars['Roughness']=data['parameters']['scalar']['Roughness'];vectors['FinishColor']=POLY
        elif mode=='stock':scalars.update(SourceColorWeight=.04,Metallic=1.,EdgeMetallic=1.)
        elif mode=='kv':
            scalars.update(Metallic=1,EdgeMetallic=1,SourceColorWeight=.04,SourceRoughnessWeight=0,MaskUVChannel=0,AOStrength=0,CavityDarken=0,CavityRoughness=0)
            textures.update(SourceBaseColor='/Game/Weapons/KVScope20261019/T_KVScope_BC',SurfaceNormal='/Game/Weapons/KVScope20261019/T_KVScope_N')
        # Other materials keep their own source normals, AO/masks, UV selector and nonmetal values.
    elif mode=='r01':
        scalars.update(R01_Roughness=ROUGH,R01_SourceRoughnessWeight=.06,R01_Grain=.006,R01_Variation=.002,R02_SourceColorContrast=.08,R01_PolymerRoughness=.59,R01_PolymerSourceWeight=.06)
        vectors.update(R01_ToneScale=[v/.058 for v in METAL[:3]],R01_PolymerTint=POLY)
        textures['R01_GrainTexture']='/Game/Weapons/WeaponSurface/Textures/T_WS_Grain'
    elif mode=='pkm':
        scalars.update(R01_Roughness=ROUGH,R01_GrainRoughness=.006,R01_VariationRoughness=.002,R01_SourceRoughnessWeight=.06,R01_ColorWeight=1.)
        vectors['R01_FinishTint']=METAL
    elif mode=='thermal':scalars.update(DryRoughness=ROUGH,Metallic=1);vectors['SurfaceTint']=METAL
    for k,v in scalars.items():scalar(mi,k,v)
    for k,v in vectors.items():vector(mi,k,v)
    for k,v in textures.items():L.set_material_instance_texture_parameter_value(mi,k,load(v))
    E.set_metadata_tag(mi,'M24FinishReference','StockContinuity20261031/MI_M24_Regional_host; metal roughness floor .48')
    E.set_metadata_tag(mi,'M24FinishSource',src);L.update_material_instance(mi);save(mi);mapped[src]=mi
    R['materials'][src]={'path':mi.get_path_name(),'mode':mode,'scalars':scalars,'vectors':vectors,'textures':textures};record()
    print('M24_FINISH_MATERIAL_SAVED',mode,src,flush=True)
# Publish only bindings on the actual installed meshes, after all materials are saved.
for key,row in D['meshes'].items():
    if not any(s['material'] in mapped for s in row['slots']):continue
    if hashlib.sha256(disk(row['path']).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Concurrent mesh edit retained '+row['path'])
    mesh=load(row['path']);slots=list(mesh.materials if isinstance(mesh,u.SkeletalMesh) else mesh.static_materials)
    for i,s in enumerate(slots):
        old=row['slots'][i]
        if str(s.material_slot_name)!=old['slot'] or s.material_interface.get_path_name()!=old['material']:raise RuntimeError('Live slot changed '+row['path'])
        if old['material'] in mapped:s.material_interface=mapped[old['material']];slots[i]=s
    backup(row['path']);mesh.set_editor_property('materials' if isinstance(mesh,u.SkeletalMesh) else 'static_materials',slots);save(mesh)
    R['meshes'][row['path']]={'slots':[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in (mesh.materials if isinstance(mesh,u.SkeletalMesh) else mesh.static_materials)],'sha256':hashlib.sha256(disk(row['path']).read_bytes()).hexdigest()};record()
    print('M24_FINISH_MESH_SAVED',key,flush=True)
# Carbon-bolt runtime uses this stable material path directly, so merge the authored
# parameters and parent into it instead of changing C++ or any animation asset.
carbon=next(p for p in mapped if 'MI_M24_CarbonBolt.' in p);old=load(carbon);new=mapped[carbon]
backup(carbon);L.set_material_instance_parent(old,new.get_editor_property('parent'))
for k,v in R['materials'][carbon]['scalars'].items():scalar(old,k,v)
for k,v in R['materials'][carbon]['vectors'].items():vector(old,k,v)
L.update_material_instance(old);save(old);R['carbon_runtime_override_saved']=carbon
R['complete']=True;record();print('M24_FINISH_COMPLETE',len(R['materials']),len(R['meshes']),flush=True)
