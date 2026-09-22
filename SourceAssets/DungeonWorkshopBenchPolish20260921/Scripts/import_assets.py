"""Create an independent workbench material/mesh revision; never rebuild live graphs."""
from pathlib import Path
import json,re,unreal as u
ROOT=Path(__file__).resolve().parents[1];DEST='/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopBenchPolish'
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('End active gameplay before asset import')
manifest=json.loads((ROOT/'Authored/manifest.json').read_text());recipes=json.loads((ROOT/'Authored/material-manifest.json').read_text())
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt=dict(stage='importing',materials={},textures={},meshes={},tests_run=False,screenshots_taken=False)
def write():(ROOT/'Receipts/asset-import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(o):
    if not E.save_loaded_asset(o,False):raise RuntimeError('Save failed '+o.get_path_name())
def node(m,cls):return L.create_material_expression(m,cls)
def link(a,pin,b,target):
    names=list(L.get_material_expression_input_names(b))
    if target not in names and len(names)==1:target=names[0]
    if not L.connect_material_expressions(a,pin,b,target):raise RuntimeError('Material connection '+target)
def output(n,prop,pin=''):
    if not L.connect_material_property(n,pin,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Material output '+prop)
def scalar(m,v):n=node(m,u.MaterialExpressionConstant);n.r=v;return n
def color(m,v):n=node(m,u.MaterialExpressionConstant3Vector);n.set_editor_property('constant',u.LinearColor(*v,1));return n
def custom(m,code,inputs,width=3):
    n=node(m,u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
    pins=[]
    for key in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    n.set_editor_property('inputs',pins)
    for key,(source,outputpin) in inputs.items():link(source,outputpin,n,key)
    return n
def texture(filename,key,ch):
    name='T_WSBench_'+key+'_'+ch;folder=DEST+'/Textures';t=u.load_asset(folder+'/'+name)
    if not t:
        task=u.AssetImportTask();task.filename=filename;task.destination_path=folder;task.destination_name=name;task.automated=True;task.replace_existing=False;task.save=False
        A.import_asset_tasks([task]);t=u.load_asset(folder+'/'+name)
        if not t:raise RuntimeError('Texture import failed '+name)
        t.set_editor_property('srgb',ch=='BaseColor');t.set_editor_property('virtual_texture_streaming',False)
        t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if ch=='Normal' else u.TextureCompressionSettings.TC_BC7 if ch=='BaseColor' else u.TextureCompressionSettings.TC_MASKS)
        if ch=='Normal':t.set_editor_property('flip_green_channel',True)
        save(t)
    receipt['textures'][key+'_'+ch]=t.get_path_name();return t
def sample(m,t,ch):
    n=node(m,u.MaterialExpressionTextureSample);n.texture=t
    n.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if ch=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if ch=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS
    return n
for key,r in recipes.items():
    name='M_WSBench_'+key+('_R3' if key=='BenchWood' else '');folder=DEST+'/Materials';m=u.load_asset(folder+'/'+name)
    if not m:
        m=A.create_asset(name,folder,u.Material,u.MaterialFactoryNew());channels={}
        for ch,filename in r.get('maps',{}).items():
            s=sample(m,texture(filename,key,ch),ch);result=s;pin='R' if ch in ('Roughness','Metallic') else ''
            if ch=='BaseColor':
                result=custom(m,'return C * Tint;',{'C':(s,''),'Tint':(color(m,r.get('color_tint',[1,1,1])), '')})
            elif ch=='Roughness':
                result=custom(m,'return clamp(R * Scale + Bias, .27, .94);',{'R':(s,'R'),'Scale':(scalar(m,r.get('roughness_scale',1)),''),'Bias':(scalar(m,r.get('roughness_bias',0)), '')},1);pin=''
            elif ch=='Normal':
                result=custom(m,'return normalize(N * float3(Strength,Strength,1));',{'N':(s,''),'Strength':(scalar(m,r.get('normal_strength',1)), '')})
            channels[ch]=(result,pin)
        if r.get('worktop'):
            uv=node(m,u.MaterialExpressionTextureCoordinate);uv.set_editor_property('coordinate_index',1)
            noise=sample(m,texture(r['imperfection'],'BenchUse','Mask'),'Mask')
            scaled=custom(m,'return P * float2(2.1,1.7);',{'P':(uv,'')},2);link(scaled,'',noise,'UVs')
            masks=custom(m,'''
float2 p=float2(Local.x,1-Local.y);
float2 a=(p-float2(.43,2.79))/float2(.23,.38);
float2 b=(p-float2(1.84,3.84))/float2(.43,.18);
float oil=max(exp(-dot(a,a)*2.2),exp(-dot(b,b)*2.8)) * saturate(Noise*.90+.10);
float2 h1=(p-float2(.875,2.55))/float2(.085,.78);
float2 h2=(p-float2(1.77,3.435))/float2(.72,.08);
float hand1=exp(-h1.x*h1.x-h1.y*h1.y*h1.y*h1.y);
float hand2=exp(-h2.y*h2.y-h2.x*h2.x*h2.x*h2.x);
return float3(oil,max(hand1,hand2),Noise);
''',{'Local':(uv,''),'Noise':(noise,'R')})
            vertex=node(m,u.MaterialExpressionVertexColor)
            channels['BaseColor']=(custom(m,'return C * V.rgb * lerp(1,.63,W.x) * lerp(1,1.085,W.y);',{'C':channels['BaseColor'],'V':(vertex,''),'W':(masks,'')}),'')
            channels['Roughness']=(custom(m,'return clamp(R-W.y*.14-W.x*.10+(W.z-.5)*.045,.32,.9);',{'R':channels['Roughness'],'W':(masks,'')},1),'')
        for ch,(n,pin) in channels.items():output(n,{'BaseColor':'BASE_COLOR','Normal':'NORMAL','Roughness':'ROUGHNESS','Metallic':'METALLIC'}[ch],pin)
        if 'color' in r:output(color(m,r['color']),'BASE_COLOR')
        if 'emission' in r:output(color(m,r['emission']),'EMISSIVE_COLOR')
        if 'Roughness' not in channels:output(scalar(m,r.get('roughness',.6)),'ROUGHNESS')
        if 'Metallic' not in channels:output(scalar(m,r.get('metallic',0)),'METALLIC')
        output(scalar(m,.28 if key=='BenchWood' else .32),'SPECULAR');L.layout_material_expressions(m);L.recompile_material(m);save(m)
    receipt['materials'][key]=m.get_path_name();write()
for e in manifest['objects']:
    name=e['name'];folder=DEST+'/Meshes';mesh=u.load_asset(folder+'/'+name)
    if not mesh:
        task=u.AssetImportTask();task.filename=e['fbx'];task.destination_path=folder;task.destination_name=name;task.automated=True;task.replace_existing=False;task.save=False
        opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False;opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        d=opt.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True;d.generate_lightmap_u_vs=False;d.auto_generate_collision=False
        d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(folder+'/'+name)
        if not mesh:raise RuntimeError('Mesh import failed '+name)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        key=re.sub(r'[._][0-9]{3}$','',str(slot.get_editor_property('material_slot_name')))
        path=manifest['material_aliases'].get(key) or receipt['materials'].get(key.removeprefix('WSBench_'))
        mat=u.load_asset(path) if path else None
        if not mat:raise RuntimeError('Missing material '+key)
        mesh.set_material(i,mat)
    ns=mesh.get_editor_property('nanite_settings');ns.enabled=False;mesh.set_editor_property('nanite_settings',ns)
    if e['collision']:mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    save(mesh);receipt['meshes'][name]=mesh.get_path_name();write()
receipt['stage']='assets_saved';write();print('BENCH_POLISH_ASSETS_SAVED '+json.dumps(dict(meshes=len(receipt['meshes']),materials=len(receipt['materials']))))
