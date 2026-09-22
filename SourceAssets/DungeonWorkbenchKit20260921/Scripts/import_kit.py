"""Import changed local meshes and create shared parameterized material families."""
from pathlib import Path
import json,re,hashlib,unreal as u
ROOT=Path(__file__).resolve().parents[1];DEST='/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit'
CFG=json.loads((ROOT/'Config/workbench.json').read_text(encoding='utf-8'));MAN=json.loads((ROOT/'Authored/manifest.json').read_text())
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Gameplay active')
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt=dict(stage='importing',meshes={},materials={},imported_meshes=[],reused_meshes=[],tests_run=False)
def write():(ROOT/'Receipts/asset-import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(o):
    if not E.save_loaded_asset(o,False):raise RuntimeError('Asset save failed '+o.get_path_name())
def node(m,cls):return L.create_material_expression(m,cls)
def link(a,p,b,t):
    if not L.connect_material_expressions(a,p,b,t):raise RuntimeError('Cannot connect '+t)
def output(a,p,prop):
    if not L.connect_material_property(a,p,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Cannot connect '+prop)
def scalar(m,name,v):
    n=node(m,u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',v);return n
def vector(m,name,v):
    n=node(m,u.MaterialExpressionVectorParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',u.LinearColor(*v,1));return n
def custom(m,code,ins,width=3):
    n=node(m,u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
    pins=[]
    for key in ins:p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
    n.set_editor_property('inputs',pins)
    for key,(a,out) in ins.items():link(a,out,n,key)
    return n
def channel(m,prop):
    p=getattr(u.MaterialProperty,'MP_'+prop);return (L.get_material_property_input_node(m,p),L.get_material_property_input_node_output_name(m,p))
def finish(m):
    E.set_metadata_tag(m,'WorkbenchKitCompleted','1');L.layout_material_expressions(m);L.recompile_material(m);save(m);return m
def usage_layer(m):
    tint=vector(m,'SurfaceTint',[1,1,1]);dust=scalar(m,'DustAmount',0);bias=scalar(m,'SurfaceRoughnessBias',0);normal=node(m,u.MaterialExpressionVertexNormalWS)
    for prop,code in [('BASE_COLOR','return lerp(C*Tint.rgb,float3(.14,.125,.105),saturate(Dust*(.25+.75*saturate(N.z))));'),
                      ('ROUGHNESS','return clamp(lerp(C+Bias,.88,saturate(Dust*(.25+.75*saturate(N.z)))),.2,.96);')]:
        original,pin=channel(m,prop)
        if not original:continue
        out=custom(m,code,{'C':(original,pin),'Tint':(tint,''),'Dust':(dust,''),'Bias':(bias,''),'N':(normal,'')},3 if prop=='BASE_COLOR' else 1)
        output(out,'',prop)
def copied_family(source,name):
    path=DEST+'/Materials/'+name;m=u.load_asset(path)
    if m:return m
    m=E.duplicate_asset(source,path)
    if not m:raise RuntimeError('Cannot create shared material '+name)
    usage_layer(m);return finish(m)
wood=copied_family('/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopBenchPolish/Materials/M_WSBench_BenchWood_R3','M_WBK_Wood')
tools=copied_family('/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopFabTools/Materials/M_WSFab_ServiceTools','M_WBK_Tools')
surface=u.load_asset(DEST+'/Materials/M_WBK_Surface')
if not surface:
    surface=A.create_asset('M_WBK_Surface',DEST+'/Materials',u.Material,u.MaterialFactoryNew());m=surface
    default='/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopBenchPolish/Textures/T_WSBench_BenchWood_'
    samples={}
    for ch in ('BaseColor','Normal','Roughness','Metallic'):
        s=node(m,u.MaterialExpressionTextureSampleParameter2D);s.set_editor_property('parameter_name',ch+'Map');s.texture=u.load_asset(default+('Roughness' if ch=='Metallic' else ch))
        s.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if ch=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if ch=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS;samples[ch]=s
    base=custom(m,'return lerp(Color.rgb,T.rgb*Color.rgb,Use);',{'Color':(vector(m,'BaseTint',[1,1,1]),''),'T':(samples['BaseColor'],''),'Use':(scalar(m,'UseBaseMap',1),'')})
    output(base,'','BASE_COLOR')
    normal=custom(m,'return normalize(lerp(float3(0,0,1),N*float3(Strength,Strength,1),Use));',{'N':(samples['Normal'],''),'Strength':(scalar(m,'NormalStrength',1),''),'Use':(scalar(m,'UseNormalMap',1),'')});output(normal,'','NORMAL')
    for ch,prop,val in [('Roughness','ROUGHNESS',.6),('Metallic','METALLIC',0)]:
        n=custom(m,'return clamp(lerp(Value,T*Scale+Bias,Use),0,1);',{'Value':(scalar(m,ch+'Value',val),''),'T':(samples[ch],'R'),'Scale':(scalar(m,ch+'Scale',1),''),'Bias':(scalar(m,ch+'Bias',0),''),'Use':(scalar(m,'Use'+ch+'Map',1),'')},1);output(n,'',prop)
    output(vector(m,'Emission',[0,0,0]),'','EMISSIVE_COLOR');output(scalar(m,'Specular',.30),'','SPECULAR');usage_layer(m);finish(m)
recipes={}
for folder,prefix in [('DungeonWorkshopDetail20260921','WSDetail'),('DungeonWorkshopTools20260921','WSTools'),('DungeonWorkshopSculpt20260921','WSSculpt'),('DungeonWorkshopSurface20260921','WSFinish'),('DungeonWorkshopBenchPolish20260921','WSBench')]:
    for key,r in json.loads((ROOT.parent/folder/'Authored/material-manifest.json').read_text()).items():recipes[prefix+'_'+key]=r
# Original bottle textures share the kit surface parent and its three usage variants.
for short,r in json.loads((ROOT/'Authored/bottle-materials.json').read_text()).items():
    key='WBKBottle_'+short;recipes[key]=r;textures={}
    for ch,filename in r['maps'].items():
        name='T_'+key+'_'+ch;path=DEST+'/Textures/'+name;t=u.load_asset(path)
        signature=hashlib.sha256(Path(filename).read_bytes()).hexdigest()
        if not t or E.get_metadata_tag(t,'WorkbenchBottleTexture')!=signature:
            task=u.AssetImportTask();task.filename=filename;task.destination_path=DEST+'/Textures';task.destination_name=name;task.automated=True;task.replace_existing=bool(t);task.save=False
            A.import_asset_tasks([task]);t=u.load_asset(path)
            if not t:raise RuntimeError('Bottle texture import failed '+name)
            t.modify();t.set_editor_property('srgb',ch=='BaseColor');t.set_editor_property('virtual_texture_streaming',False)
            t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if ch=='Normal' else u.TextureCompressionSettings.TC_BC7 if ch=='BaseColor' else u.TextureCompressionSettings.TC_MASKS)
            if ch=='Normal':t.set_editor_property('flip_green_channel',True)
            E.set_metadata_tag(t,'WorkbenchBottleTexture',signature);save(t)
        textures[ch]=t
    name='MI_'+key;path=DEST+'/Materials/BottleSources/'+name;mi=u.load_asset(path)
    if not mi:mi=A.create_asset(name,DEST+'/Materials/BottleSources',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    if E.get_metadata_tag(mi,'WorkbenchBottleSource')!=r['content_hash']:
        mi.modify();L.set_material_instance_parent(mi,surface)
        for ch in ('BaseColor','Normal','Roughness','Metallic'):
            L.set_material_instance_scalar_parameter_value(mi,'Use'+('Base' if ch=='BaseColor' else ch)+'Map',float(ch in textures))
            if ch in textures:L.set_material_instance_texture_parameter_value(mi,ch+'Map',textures[ch])
        L.set_material_instance_scalar_parameter_value(mi,'MetallicValue',r['metallic']);L.set_material_instance_scalar_parameter_value(mi,'DustAmount',0)
        L.update_material_instance(mi);E.set_metadata_tag(mi,'WorkbenchBottleSource',r['content_hash']);save(mi)
material_paths=sorted({path for e in MAN['components'] for path in e['material_paths'].values() if path})
for variant,cfg in CFG['variants'].items():
    receipt['materials'][variant]={}
    for source in material_paths:
        asset=u.load_asset(source)
        if not asset:raise RuntimeError('Required material source missing '+source)
        name=source.split('/')[-1].split('.')[0];key=re.sub(r'_R\d+$','',name.removeprefix('M_').removeprefix('MI_'))
        recipe=recipes.get(key);is_tools=name.startswith('MI_WSFab_');is_wood=key=='WSBench_BenchWood'
        # Printed/masked labels and minute exposed-edge overlays retain their original material contract.
        if not (is_tools or is_wood) and (not recipe or recipe.get('masked') or recipe.get('two_sided') or any(word in key for word in ('Labels','ToolLabels','Cut','ExposedEdge','Recess'))):
            receipt['materials'][variant][source]=source;continue
        mparent=tools if is_tools else wood if is_wood else surface
        path=DEST+'/Materials/'+variant+'/MI_WBK_'+name.removeprefix('M_').removeprefix('MI_');mi=u.load_asset(path)
        signature=hashlib.sha256(json.dumps({'source':source,'recipe':recipe,'variant':{k:cfg[k] for k in ('surface_tint','dust','roughness_bias','lamp_on','tool_wear_add')}},sort_keys=True).encode()).hexdigest()
        if mi and E.get_metadata_tag(mi,'WorkbenchKitMaterial')==signature:
            receipt['materials'][variant][source]=mi.get_path_name();continue
        if not mi:mi=A.create_asset(path.split('/')[-1],'/'.join(path.split('/')[:-1]),u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        L.set_material_instance_parent(mi,mparent)
        def set_s(k,v):L.set_material_instance_scalar_parameter_value(mi,k,v)
        def set_v(k,v):L.set_material_instance_vector_parameter_value(mi,k,u.LinearColor(*v,1))
        set_v('SurfaceTint',cfg['surface_tint']);set_s('DustAmount',cfg['dust']);set_s('SurfaceRoughnessBias',cfg['roughness_bias'])
        if is_tools:
            set_s('WearBlend',min(1,L.get_material_instance_scalar_parameter_value(asset,'WearBlend')+cfg['tool_wear_add']))
            set_s('NormalStrength',.85);set_s('RoughnessScale',.86);set_s('RoughnessBias',.055)
        elif not is_wood:
            r=recipe;set_v('BaseTint',r.get('color',r.get('color_tint',[1,1,1])));set_v('Emission',r.get('emission',[0,0,0]) if cfg['lamp_on'] else [0,0,0])
            set_s('NormalStrength',r.get('normal_strength',1));set_s('RoughnessValue',r.get('roughness',.6));set_s('MetallicValue',r.get('metallic',0))
            set_s('RoughnessScale',r.get('roughness_scale',1));set_s('RoughnessBias',r.get('roughness_bias',0))
            for ch in ('BaseColor','Normal','Roughness','Metallic'):
                present=ch in r.get('maps',{});set_s('Use'+('Base' if ch=='BaseColor' else ch)+'Map',1 if present else 0)
                if present:
                    texpath=source.split('/Materials/')[0]+'/Textures/T_'+key+'_'+ch;t=u.load_asset(texpath)
                    if not t:raise RuntimeError('Required existing texture missing '+texpath)
                    L.set_material_instance_texture_parameter_value(mi,ch+'Map',t)
        L.update_material_instance(mi);E.set_metadata_tag(mi,'WorkbenchKitMaterial',signature);save(mi);receipt['materials'][variant][source]=mi.get_path_name()
write()
for e in MAN['components']:
    name=e['name'];path=DEST+'/Meshes/'+name;mesh=u.load_asset(path)
    changed=not mesh or E.get_metadata_tag(mesh,'WorkbenchKitGeometry')!=e['content_hash']
    if changed:
        task=u.AssetImportTask();task.filename=e['fbx'];task.destination_path=DEST+'/Meshes';task.destination_name=name;task.automated=True;task.replace_existing=bool(mesh);task.replace_existing_settings=True;task.save=False
        opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False;opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        d=opt.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True;d.generate_lightmap_u_vs=False;d.auto_generate_collision=False
        d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Mesh import failed '+name)
        for i,slot in enumerate(mesh.get_editor_property('static_materials')):
            key=re.sub(r'[._][0-9]{3}$','',str(slot.get_editor_property('material_slot_name')));source=e['material_paths'].get(key)
            if not source:raise RuntimeError('Missing material mapping '+key+' for '+name)
            mesh.set_material(i,u.load_asset(receipt['materials']['InUse'][source]))
        ns=mesh.get_editor_property('nanite_settings');ns.enabled=e['triangles']>70000;mesh.set_editor_property('nanite_settings',ns)
        if e['collision']:mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        E.set_metadata_tag(mesh,'WorkbenchKitGeometry',e['content_hash']);save(mesh);receipt['imported_meshes'].append(e['id'])
    else:receipt['reused_meshes'].append(e['id'])
    receipt['meshes'][e['id']]=mesh.get_path_name();write()
receipt['stage']='assets_saved';write();print('WORKBENCH_KIT_ASSETS_SAVED '+json.dumps(dict(imported=len(receipt['imported_meshes']),reused=len(receipt['reused_meshes']),material_families=3)))
