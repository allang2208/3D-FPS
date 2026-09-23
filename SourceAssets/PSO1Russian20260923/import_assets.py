"""Install the three fitted PSO assemblies, finish/rain pairs and option icons."""
import unreal as u,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/PSO1Russian20260923');P='/Game/Weapons/PSO1Russian20260923'
src=json.loads((O/'sources.json').read_text());spec=json.loads((O/'authoring.json').read_text())
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt=json.loads((O/'import_receipt.json').read_text()) if (O/'import_receipt.json').exists() else {'status':'importing','textures':{},'materials':{},'meshes':{},'icons':{},'tests_run':False}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(P+'/') or p.endswith('_optic_pso1_4x') for p in dirty):raise RuntimeError('Unsaved PSO target packages; preserve editor state')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve the play session')

def record():
    (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed: '+obj.get_path_name())
def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def link(value,target,pin):
    n,channel=value if isinstance(value,tuple) else (value,'')
    if not L.connect_material_expressions(n,channel,target,pin):raise RuntimeError('Connection failed: '+pin)
def output(value,prop):
    n,channel=value if isinstance(value,tuple) else (value,'')
    if not L.connect_material_property(n,channel,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Output failed: '+prop)
def constant(m,value):
    return node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*value,1)) if isinstance(value,(list,tuple)) else node(m,u.MaterialExpressionConstant,r=value)
def material(name):
    path=P+'/Materials/'+name
    m=u.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,P+'/Materials',u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(m)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    return m
def sample(m,texture,normal=False):
    return node(m,u.MaterialExpressionTextureSample,texture=texture,
      sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_COLOR if texture.srgb else u.MaterialSamplerType.SAMPLERTYPE_MASKS if texture.compression_settings==u.TextureCompressionSettings.TC_MASKS else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE if texture.compression_settings==u.TextureCompressionSettings.TC_GRAYSCALE else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
def finish(m,reference):
    E.set_metadata_tag(m,'WeaponFinishReference',reference)
    E.set_metadata_tag(m,'PSO1_Source','LeroyCake CC BY 4.0; corrected source UV0/full normal; host coating and private side interface')
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Material compilation: '+str(errors))
    save(m);receipt['materials'][m.get_name()]={'asset':m.get_path_name(),'saved':True};record()

normal=u.load_asset('/Game/Weapons/SVDDragunov20260922/Textures/T_SVD_pso_normal')
glass=u.load_asset('/Game/Weapons/SVDDragunov20260922/Complete20260923/Materials/M_SVD_OpticalGlass')
if not normal or not glass:raise RuntimeError('Missing source structural normal/glass')
wetmap={}
beads=(O.parent/'WeatherNatural20260912/WeaponBeads.hlsl').read_text().replace(
 'return float4(slope,beads,saturate(Wet));','float coverage=saturate(Wet*20.0); return float4(slope*coverage,beads*coverage,saturate(Wet));')
def custom(m,code,inputs,size,label):
    n=node(m,u.MaterialExpressionCustom,code=code,description=label,
      output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
    values=[]
    for name in inputs:
        item=u.CustomInput();item.set_editor_property('input_name',name);values.append(item)
    n.set_editor_property('inputs',values)
    for name,value in inputs.items():link(value,n,name)
    return n
def wet_copy(dry,shell):
    path=P+'/Materials/'+dry.get_name()+'_Wet'
    # This revision keeps stable texture paths: a repeat texture import also
    # updates its existing wet graph. A different graph design gets a new revision.
    if E.does_asset_exist(path):
        wetmap[dry.get_path_name()]=u.load_asset(path);return
    wet=E.duplicate_asset(dry.get_path_name(),path)
    if not wet:raise RuntimeError('Cannot duplicate dry surface')
    originals={}
    for prop,default in [('BASE_COLOR',(.03,.03,.03)),('ROUGHNESS',.4),('NORMAL',(0,0,1))]:
        n=L.get_material_property_input_node(wet,getattr(u.MaterialProperty,'MP_'+prop))
        originals[prop]=(n,L.get_material_property_input_node_output_name(wet,getattr(u.MaterialProperty,'MP_'+prop))) if n else constant(wet,default)
    amount=node(wet,u.MaterialExpressionScalarParameter,parameter_name='WeaponWetness',default_value=0.)
    if shell:
        region=node(wet,u.MaterialExpressionVertexColor)
        amount=custom(wet,'return saturate(Wet)*Region;',{'Wet':amount,'Region':(region,'R')},1,'PSO exterior wetness')
    data=custom(wet,beads,{'UV':node(wet,u.MaterialExpressionTextureCoordinate),'Wet':amount},4,'WeatherBeads')
    output(custom(wet,'return Base*(1-Data.a*.065);',{'Base':originals['BASE_COLOR'],'Data':data},3,'PSO water film'),'BASE_COLOR')
    output(custom(wet,'return lerp(lerp(Base,max(.12,Base*.76),Data.a),.085,Data.b*.72);',{'Base':originals['ROUGHNESS'],'Data':data},1,'PSO wet roughness'),'ROUGHNESS')
    output(custom(wet,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.12)+Data.xy*.55,Base.z));',{'Base':originals['NORMAL'],'Data':data},3,'PSO water beads'),'NORMAL')
    finish(wet,dry.get_path_name());wetmap[dry.get_path_name()]=wet

flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for host,info in spec['hosts'].items():
    completed=all('M_PSO1_'+host+suffix in receipt['materials'] for suffix in ['_Shell','_Adapter','_Shell_Wet','_Adapter_Wet'])
    if completed:
        shell=u.load_asset(P+'/Materials/M_PSO1_'+host+'_Shell')
        adapter=u.load_asset(P+'/Materials/M_PSO1_'+host+'_Adapter')
        for dry in [shell,adapter]:wetmap[dry.get_path_name()]=u.load_asset(dry.get_path_name().split('.')[0]+'_Wet')
    else:
        textures={}
        for kind,filename in info['textures'].items():
            task=u.AssetImportTask();task.filename=filename;task.destination_path=P+'/Textures';task.destination_name=Path(filename).stem
            task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
            tex=u.load_asset(task.destination_path+'/'+task.destination_name)
            if not tex:raise RuntimeError('Missing imported texture '+filename)
            tex.srgb=kind=='BaseColor';tex.compression_settings=u.TextureCompressionSettings.TC_BC7
            tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON;tex.lod_bias=0;tex.max_texture_size=4096;save(tex)
            textures[kind]=tex;receipt['textures'][tex.get_name()]={'asset':tex.get_path_name(),'saved':True};record()
        reference=src['a762_finish']['reference'] if host=='A762' else src['textures'][host+'_BaseColor']['asset']
        shell=material('M_PSO1_'+host+'_Shell')
        output((sample(shell,textures['BaseColor']),'RGB'),'BASE_COLOR')
        packed=sample(shell,textures['ORM']);output((packed,'R'),'AMBIENT_OCCLUSION');output((packed,'G'),'ROUGHNESS');output((packed,'B'),'METALLIC')
        output((sample(shell,normal,True),'RGB'),'NORMAL');finish(shell,reference)
        adapter=material('M_PSO1_'+host+'_Adapter')
        if host=='A762':
            f=src['a762_finish'];output(constant(adapter,f['color']),'BASE_COLOR');output(constant(adapter,f['metallic']),'METALLIC')
            grain=sample(adapter,u.load_asset(src['textures']['A762_Grain']['asset']))
            rough=custom(adapter,'return Center+(Grain-.5)*.018;',{'Center':constant(adapter,f['roughness']),'Grain':(grain,'R')},1,'A762 50mm coating')
            output(rough,'ROUGHNESS')
        else:
            output((sample(adapter,u.load_asset(src['textures'][host+'_BaseColor']['asset'])),'RGB'),'BASE_COLOR')
            if host=='PKM':
                packed=sample(adapter,u.load_asset(src['textures']['PKM_ORM']['asset']))
                output((packed,'R'),'AMBIENT_OCCLUSION');output((packed,'G'),'ROUGHNESS');output((packed,'B'),'METALLIC')
            else:
                for prop,role in [('METALLIC','Metallic'),('ROUGHNESS','Roughness')]:
                    output((sample(adapter,u.load_asset(src['textures']['AKM_'+role]['asset'])),'R'),prop)
        finish(adapter,reference)
        wet_copy(shell,True);wet_copy(adapter,False)
    opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opts.import_materials=False;opts.import_textures=False;opts.import_animations=False
    data=opts.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task=u.AssetImportTask();task.filename=str(O/'Exports'/(info['mesh']+'.fbx'));task.destination_path=P+'/'+host;task.destination_name=info['mesh']
    task.options=opts;task.factory=u.FbxFactory();task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
    mesh=u.load_asset(task.destination_path+'/'+task.destination_name)
    if not mesh:raise RuntimeError('Static mesh import failed '+host)
    slots=list(mesh.static_materials)
    for i,slot in enumerate(slots):
        name=str(slot.material_slot_name)
        if 'Shell' in name:slot.material_interface=shell
        elif 'Adapter' in name:slot.material_interface=adapter
        elif 'OpticalGlass' in name:slot.material_interface=glass
        else:raise RuntimeError('Unmapped imported material slot '+name)
        slots[i]=slot
    mesh.set_editor_property('static_materials',slots)
    for name,location in info['sockets_cm'].items():
        socket=mesh.find_socket(name)
        if not socket:
            socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',name);mesh.add_socket(socket)
        socket.relative_location=u.Vector(*location);socket.relative_rotation=u.Rotator(0,0,0)
    E.set_metadata_tag(mesh,'PSO1_Host',host);E.set_metadata_tag(mesh,'PSO1_Mount','WPN_root; yaw 90; scale .01; measured receiver side interface')
    save(mesh)
    receipt['meshes'][host]={'asset':mesh.get_path_name(),'saved':True,'size_cm':list((mesh.get_bounds().box_extent*2).to_tuple()),
     'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials},
     'aim_center_cm':list(mesh.find_socket('AimCenter').relative_location.to_tuple())}
    record();print('PSO1_HOST_IMPORTED',host)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))

name='DA_PSO1_WetMaterials';path=P+'/'+name
table=u.load_asset(path) if E.does_asset_exist(path) else None
if not table:
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeatherPresentationAssets)
    table=A.create_asset(name,P,u.WeatherPresentationAssets,factory)
table.set_editor_property('wet_materials',wetmap);save(table)
receipt['wet_materials']={k:v.get_path_name() for k,v in table.get_editor_property('wet_materials').items()}
for key,info in json.loads((O/'icons.json').read_text()).items():
    task=u.AssetImportTask();task.filename=info['output'];task.destination_path='/Game/ColdSteelData/AttachmentIcons20260913';task.destination_name=key
    task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
    tex=u.load_asset(task.destination_path+'/'+key)
    if not tex:raise RuntimeError('Icon import failed '+key)
    tex.srgb=True;tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI;tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    save(tex);receipt['icons'][key]={'asset':tex.get_path_name(),'saved':True};record()
receipt['status']='Assets and three per-weapon icons imported and saved; runtime/visual acceptance not run'
record();print('PSO1_IMPORT_COMPLETE')
