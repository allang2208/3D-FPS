"""Import revision-only room assets in the running UE editor; no map mutation."""
from pathlib import Path
import re,json
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonRoomInteriors20260921')
OUT='/Game/Dungeons/AtmosphereV2/RoomInteriors'
BASE='/Game/Dungeons/AtmosphereV2'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
phase=globals().get('ROOM_IMPORT_PHASE','authored')
reimport_names=set(globals().get('ROOM_REIMPORT_NAMES',[]))
receipt_path=ROOT/'Receipts/asset-import.json'
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {'materials':{},'meshes':{},'generated':{},'tests_run':False}

def write():receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(o):
    if not E.save_loaded_asset(o,False):raise RuntimeError('Could not save '+o.get_path_name())
def node(m,cls):return L.create_material_expression(m,cls)
def wire(a,b,pin,out=''):
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material input failed '+pin)
def output(n,p,pin=''):
    if not L.connect_material_property(n,pin,getattr(u.MaterialProperty,'MP_'+p)):raise RuntimeError('Material output failed '+p)
def scalar(m,value):
    n=node(m,u.MaterialExpressionConstant);n.r=value;return n

def texture(filename,folder,name,ch):
    path=folder+'/'+name;t=u.load_asset(path)
    if t:return t
    task=u.AssetImportTask();task.filename=str(filename);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=False;task.save=False;A.import_asset_tasks([task]);t=u.load_asset(path)
    if not t:raise RuntimeError('Texture import failed '+path)
    t.srgb=ch=='BaseColor'
    if ch=='Normal':t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP;t.flip_green_channel=True
    elif ch!='BaseColor':t.compression_settings=u.TextureCompressionSettings.TC_MASKS
    save(t);return t
def sample(m,t,ch):
    s=node(m,u.MaterialExpressionTextureSample);s.texture=t
    s.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if ch=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if ch=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS
    return s
def mesh_import(name,filename,folder):
    path=folder+'/'+name;mesh=u.load_asset(path)
    if mesh and name not in reimport_names:return mesh
    task=u.AssetImportTask();task.filename=filename;task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=name in reimport_names;task.replace_existing_settings=name in reimport_names;task.save=False
    opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
    opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=opts.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.generate_lightmap_u_vs=False;data.auto_generate_collision=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task.options=opts;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Mesh import failed '+path)
    return mesh
def finish_mesh(mesh):
    ns=mesh.get_editor_property('nanite_settings');ns.enabled=True;mesh.set_editor_property('nanite_settings',ns)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    save(mesh)

if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Gameplay is active; room import deferred without stopping current play')

if phase=='authored':
    recipes=json.loads((ROOT/'Authored/material-manifest.json').read_text())
    for name,r in recipes.items():
        path=OUT+'/Materials/M_Room_'+name;m=u.load_asset(path)
        if not m:
            m=A.create_asset('M_Room_'+name,OUT+'/Materials',u.Material,u.MaterialFactoryNew())
            for ch,prop in [('BaseColor','BASE_COLOR'),('Roughness','ROUGHNESS'),('Normal','NORMAL')]:
                t=texture(r['maps'][ch],OUT+'/Textures','T_Room_'+name+'_'+ch,ch);s=sample(m,t,ch)
                if ch=='BaseColor':
                    vc=node(m,u.MaterialExpressionVertexColor);mul=node(m,u.MaterialExpressionMultiply)
                    wire(s,mul,'A');wire(vc,mul,'B');output(mul,prop)
                else:output(s,prop,'R' if ch=='Roughness' else '')
            output(scalar(m,r['metallic']),'METALLIC')
            if name=='Canvas':m.set_editor_property('two_sided',True)
            L.layout_material_expressions(m);L.recompile_material(m);save(m)
        receipt['materials']['Room_'+name]=path;write()
    for name,color,rough,emit in [('WarmGlass',(1,.67,.36),.36,3),('Paper',(.53,.48,.34),.94,0)]:
        path=OUT+'/Materials/M_Room_'+name;m=u.load_asset(path)
        if not m:
            m=A.create_asset('M_Room_'+name,OUT+'/Materials',u.Material,u.MaterialFactoryNew())
            c=node(m,u.MaterialExpressionConstant3Vector);c.constant=u.LinearColor(*color,1);output(c,'BASE_COLOR');output(scalar(m,rough),'ROUGHNESS')
            if emit:
                e=node(m,u.MaterialExpressionConstant3Vector);e.constant=u.LinearColor(*(v*emit for v in color),1);output(e,'EMISSIVE_COLOR')
            L.recompile_material(m);save(m)
        receipt['materials']['Room_'+name]=path
    # Copy an existing textured decal into this revision, changing only its tint.
    # This never rebuilds a referenced material's expression graph.
    oil_path=OUT+'/Materials/M_Room_Oil'
    oil=u.load_asset(oil_path)
    if not oil:
        oil=E.duplicate_asset(BASE+'/NaturalPass/Materials/M_NaturalSilt',oil_path)
        if not oil:raise RuntimeError('Could not create oil decal material')
        # The graph's existing constants use parameterless constants; retain the
        # source dusty/oily tint and mask rather than altering a shared graph.
        save(oil)
    receipt['materials']['Oil']=oil_path
    receipt['materials']['Dust']=BASE+'/NaturalPass/Materials/M_NaturalDust'
    receipt['materials']['Leak']=BASE+'/NaturalPass/Materials/M_NaturalLeakVertical'
    manifest=json.loads((ROOT/'Authored/room-manifest.json').read_text())
    for entry in manifest['objects']:
        if reimport_names and entry['name'] not in reimport_names:continue
        mesh=mesh_import(entry['name'],entry['fbx'],OUT+'/Authored')
        for i,slot in enumerate(mesh.get_editor_property('static_materials')):
            key=re.sub(r'[._][0-9]{3}$','',str(slot.get_editor_property('material_slot_name')))
            path=receipt['materials'].get(key)
            if not path and key.startswith('V2_'):path=BASE+'/Materials/M_'+key.removeprefix('V2_')
            material=u.load_asset(path) if path else None
            if not material:raise RuntimeError('Unknown material slot '+key)
            mesh.set_material(i,material)
        finish_mesh(mesh);receipt['meshes'][entry['name']]=mesh.get_path_name();write()
elif phase=='generated':
    cfg=json.loads((ROOT/'assets.json').read_text())
    for prop in cfg['props']:
        if globals().get('ROOM_GENERATED_IDS') and prop['id'] not in globals()['ROOM_GENERATED_IDS']:continue
        data=json.loads((ROOT/'Generated'/prop['id']/'Game/asset-manifest.json').read_text())
        folder=OUT+'/Generated/'+prop['id'];materials={}
        for matname,channels in data['materials'].items():
            path=folder+'/Materials/'+matname;m=u.load_asset(path)
            if not m:
                m=A.create_asset(matname,folder+'/Materials',u.Material,u.MaterialFactoryNew())
                for ch,info in channels.items():
                    filename=Path(info['filename']);t=texture(filename,folder+'/Textures',filename.stem,ch);s=sample(m,t,ch)
                    output(s,{'BaseColor':'BASE_COLOR','Roughness':'ROUGHNESS','Metallic':'METALLIC','Normal':'NORMAL'}[ch],info['channel'])
                L.layout_material_expressions(m);L.recompile_material(m);save(m)
            materials[matname]=m
        mesh=mesh_import(data['name'],data['fbx'],folder)
        for i,slot in enumerate(mesh.get_editor_property('static_materials')):
            name=str(slot.get_editor_property('material_slot_name'))
            if name not in materials:raise RuntimeError('Generated slot mismatch '+name)
            mesh.set_material(i,materials[name])
        finish_mesh(mesh);receipt['generated'][prop['id']]=mesh.get_path_name();write()
else:raise RuntimeError('Unknown room import phase '+phase)
receipt['last_completed_phase']=phase;write()
print('ROOM_ASSETS_SAVED',phase,len(receipt['meshes']),len(receipt['generated']))
