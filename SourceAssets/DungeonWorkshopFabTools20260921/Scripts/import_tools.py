from pathlib import Path
import json,re,unreal as u
ROOT=Path(__file__).resolve().parents[1];DEST='/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopFabTools'
manifest=json.loads((ROOT/'Authored/manifest.json').read_text())
if not manifest.get('textures_ready'):raise RuntimeError('Publisher atlas has not been attached')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Stop active gameplay before tool import')
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt=dict(stage='importing',textures={},materials={},meshes={},tests_run=False,screenshots_taken=False)
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
def scalar(m,name,value):
    n=node(m,u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
def constant(m,v):n=node(m,u.MaterialExpressionConstant);n.r=v;return n
tex={}
for variant,maps in manifest['textures'].items():
    tex[variant]={}
    for channel,filename in maps.items():
        name='T_WSFab_'+variant+'_'+channel;folder=DEST+'/Textures';path=folder+'/'+name;t=u.load_asset(path)
        if not t:
            task=u.AssetImportTask();task.filename=filename;task.destination_path=folder;task.destination_name=name
            task.automated=True;task.replace_existing=False;task.save=False;A.import_asset_tasks([task]);t=u.load_asset(path)
            if not t:raise RuntimeError('Missing imported texture '+path)
            t.set_editor_property('srgb',channel=='BaseColor');t.set_editor_property('virtual_texture_streaming',False)
            if channel=='Normal':
                t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);t.set_editor_property('flip_green_channel',True)
            elif channel=='BaseColor':t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7)
            else:t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
            save(t)
        tex[variant][channel]=t;receipt['textures'][variant+'_'+channel]=t.get_path_name()
write()
master_path=DEST+'/Materials/M_WSFab_ServiceTools';m=u.load_asset(master_path)
if not m:
    m=A.create_asset('M_WSFab_ServiceTools',DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    wear=scalar(m,'WearBlend',.55)
    for channel in ('BaseColor','Normal','Roughness','Metallic'):
        samples=[]
        for variant in ('Clean','Worn'):
            s=node(m,u.MaterialExpressionTextureSample);s.texture=tex[variant][channel]
            s.sampler_type=(u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
            samples.append(s)
        mix=node(m,u.MaterialExpressionLinearInterpolate);pin='R' if channel in ('Roughness','Metallic') else ''
        link(samples[0],pin,mix,'A');link(samples[1],pin,mix,'B');link(wear,'',mix,'Alpha');result=mix
        if channel=='Normal':
            # Scale XY only, then normalize after blending the two tangent-space normals.
            xy=node(m,u.MaterialExpressionAppendVector);power=scalar(m,'NormalStrength',.85);link(power,'',xy,'A');link(power,'',xy,'B')
            xyz=node(m,u.MaterialExpressionAppendVector);link(xy,'',xyz,'A');link(constant(m,1),'',xyz,'B')
            mul=node(m,u.MaterialExpressionMultiply);link(mix,'',mul,'A');link(xyz,'',mul,'B')
            result=node(m,u.MaterialExpressionNormalize);link(mul,'',result,'VectorInput')
        elif channel=='Roughness':
            mul=node(m,u.MaterialExpressionMultiply);link(mix,'',mul,'A');link(scalar(m,'RoughnessScale',.86),'',mul,'B')
            add=node(m,u.MaterialExpressionAdd);link(mul,'',add,'A');link(scalar(m,'RoughnessBias',.055),'',add,'B')
            result=node(m,u.MaterialExpressionClamp);result.set_editor_property('min_default',.20);result.set_editor_property('max_default',.93);link(add,'',result,'')
        output(result,{'BaseColor':'BASE_COLOR','Normal':'NORMAL','Roughness':'ROUGHNESS','Metallic':'METALLIC'}[channel])
    output(constant(m,.32),'SPECULAR');L.layout_material_expressions(m);L.recompile_material(m);save(m)
for entry in manifest['objects']:
    key=entry.get('garage_material')
    if not key or key in receipt['materials']:continue
    name='MI_WSFab_'+key;folder=DEST+'/Materials';mi=u.load_asset(folder+'/'+name)
    if not mi:
        mi=A.create_asset(name,folder,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());L.set_material_instance_parent(mi,m)
    L.set_material_instance_scalar_parameter_value(mi,'WearBlend',entry['wear_blend'])
    L.update_material_instance(mi);save(mi);receipt['materials'][key]=mi.get_path_name();write()
for entry in manifest['objects']:
    name=entry['name'];folder=DEST+'/Meshes';mesh=u.load_asset(folder+'/'+name)
    if not mesh:
        task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_path=folder;task.destination_name=name
        task.automated=True;task.replace_existing=False;task.save=False
        opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False
        opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        data=opt.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
        data.transform_vertex_to_absolute=True;data.generate_lightmap_u_vs=False;data.auto_generate_collision=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(folder+'/'+name)
        if not mesh:raise RuntimeError('Mesh import failed '+name)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        slotname=re.sub(r'[._][0-9]{3}$','',str(slot.get_editor_property('material_slot_name')))
        matpath=receipt['materials'].get(entry.get('garage_material')) if slotname=='FabGarage_Atlas' else manifest['material_aliases'].get(slotname)
        mat=u.load_asset(matpath) if matpath else None
        if not mat:raise RuntimeError('Material missing '+slotname+' for '+name)
        mesh.set_material(i,mat)
    # Small tool meshes stay conventional; high-detail retained assemblies keep Nanite.
    ns=mesh.get_editor_property('nanite_settings');ns.enabled=entry['triangles']>50000;mesh.set_editor_property('nanite_settings',ns)
    save(mesh);receipt['meshes'][name]=mesh.get_path_name();write()
receipt['stage']='assets_saved';write()
print('FAB_WORKSHOP_ASSETS_SAVED '+json.dumps(dict(meshes=len(receipt['meshes']),materials=len(receipt['materials']),textures=len(receipt['textures']))))
