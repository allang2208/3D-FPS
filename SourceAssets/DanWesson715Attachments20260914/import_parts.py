"""Install the four 715 attachments and inspect their rain-material coverage."""
import ast, json
from pathlib import Path
import unreal as u
O=Path(__file__).parent;S=O.parent;ROOT=O.parents[1];D='/Game/Weapons/DanWesson715/Attachments20260914'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
auth=json.loads((O/'authoring.json').read_text());finish=json.loads((O/'finish.json').read_text())
optics=json.loads((S/'M1911CompactFit20260913/installed.json').read_text())
panoramic=json.loads((S/'M1911SculptedMount20260913/installed.json').read_text())
devices=json.loads((S/'M1911Tactical20260913/installed.json').read_text())['parts']
textures={};dry_materials={};report={'parts':{},'materials':{},'wet_materials':{},'rain_check':{}}

def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
    return asset

for kind,file in finish['textures'].items():
    t=u.AssetImportTask();t.filename=file;t.destination_path=D+'/Textures';t.destination_name=Path(file).stem;t.automated=True;t.replace_existing=True;t.save=False
    A.import_asset_tasks([t]);tex=u.load_asset(t.destination_path+'/'+t.destination_name)
    tex.srgb=kind=='BaseColor';tex.compression_settings=u.TextureCompressionSettings.TC_BC7;tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
    tex.set_editor_property('address_x',u.TextureAddress.TA_MIRROR);tex.set_editor_property('address_y',u.TextureAddress.TA_MIRROR)
    tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE);save(tex);textures[kind]=tex

def coating(source,name,mask):
    path=D+'/Materials/'+name;m=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(source,path)
    replaced=[]
    for node in L.get_material_expressions(m):
        if isinstance(node,u.MaterialExpressionTextureSample):
            tex=node.get_editor_property('texture')
            if tex and (tex.get_name().startswith('T_M1911_Attachment_') or tex.get_name().startswith('T_DW715_Attachment_')):
                kind='ORM' if tex.get_name().endswith('_ORM') else 'BaseColor'
                node.set_editor_property('texture',textures[kind]);node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR if kind=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR);replaced.append(kind)
    if not {'BaseColor','ORM'}.issubset(replaced):raise RuntimeError('Missing source coating inputs: '+source)
    E.set_metadata_tag(m,'WeaponFinishReference','/Game/Weapons/DanWesson715/MetalFinish20260914/Materials/M_DW715_Finish_Frame')
    E.set_metadata_tag(m,'DW715AttachmentFinish','Original optics/rubber/normal/AO retained; physical coating tile 0.1m')
    L.recompile_material(m);save(m);dry_materials[m.get_path_name()]=(m,mask);report['materials'][name]=dict(source=source,path=m.get_path_name(),replaced=replaced,wet_mask=mask)
    return m

bindings={
 'holographic':{'Holosight':coating(optics['holographic']['slots']['Holosight'],'M_DW715_Holographic_Body','metal'),
                'Red_Dot':u.load_asset(optics['holographic']['slots']['Red_Dot']),
                'DW715_AdapterSteel':coating(optics['holographic']['slots']['M1911_AdapterSteel'],'M_DW715_Holographic_Mount','all')},
 'panoramic_red_dot':{'Panoramic_Body':coating(panoramic['materials']['Panoramic_Body'],'M_DW715_Panoramic_Body','metal'),
                      'Panoramic_Glass':u.load_asset(panoramic['materials']['Panoramic_Glass']),
                      'Panoramic_Reticle':u.load_asset(panoramic['materials']['Panoramic_Reticle']),
                      'DW715_AdapterSteel':coating(panoramic['materials']['M1911_AdapterSteel'],'M_DW715_Panoramic_Mount','all')},
}
collar=coating(devices['laser']['collar_material'],'M_DW715_Tactical_Mount','all')
for key in ['laser','flashlight']:
    bindings[key]={'M_Tactical_'+key:coating(devices[key]['body_material'],'M_DW715_'+key+'_Body','vertex'),'M_Tactical_Collar':collar}

for key,info in auth.items():
    device=key in ['laser','flashlight'];name='SM_TacticalDevice' if device else 'SM_DW715_'+key
    t=u.AssetImportTask();t.filename=info['fbx'];t.destination_path=D+'/'+key if device else D+'/Meshes';t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=False
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    t.options=opt;A.import_asset_tasks([t]);mesh=u.load_asset(t.destination_path+'/'+name)
    if mesh is None:raise RuntimeError('Missing imported '+key)
    slots=mesh.static_materials
    for i,slot in enumerate(slots):
        exported=str(slot.material_slot_name)
        if device:label='M_Tactical_Collar' if 'Collar' in exported else 'M_Tactical_'+key
        elif 'AdapterSteel' in exported:label='DW715_AdapterSteel'
        elif key=='holographic':label='Red_Dot' if 'Reticle' in exported else 'Holosight'
        else:label='Panoramic_Glass' if 'Glass' in exported else 'Panoramic_Reticle' if 'Reticle' in exported else 'Panoramic_Body'
        slot.material_interface=bindings[key][label];slot.material_slot_name=u.Name(label);slots[i]=slot
    mesh.set_editor_property('static_materials',slots);E.set_metadata_tag(mesh,'DW715Fit','Actual barrel-shroud contacts; fixed WPN_root; no cylinder attachment');save(mesh)
    sockets={}
    for socket_name in ['Emitter','AimGuide'] if device else ['AimCenter','MountForward','MountUp']:
        socket=mesh.find_socket(socket_name)
        if socket is None:raise RuntimeError('Missing required mount socket '+key+'/'+socket_name)
        sockets[socket_name]=list(socket.relative_location.to_tuple())
    report['parts'][key]=dict(mesh=mesh.get_path_name(),slots={str(x.material_slot_name):x.material_interface.get_path_name() for x in slots},sockets_cm=sockets,coating_uv=info['uv_index'])
    u.log('DW715_ATTACHMENT_IMPORTED '+key)

tree=ast.parse((ROOT/'Tools/Weather/build_natural_weather.py').read_text(encoding='utf-8'))
names={'node','wire','prop','scalar','constant','vector','custom'}
weather={'unreal':u,'LIB':L}
exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in names],type_ignores=[]),'weather_graph_helpers','exec'),weather)
for dry,(source,mask) in dry_materials.items():
    path=D+'/Wet/M_Wet_'+source.get_name();wet=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(dry,path)
    if not E.get_metadata_tag(wet,'DW715AttachmentWet'):
        original={}
        for pname,default in [('BASE_COLOR',(.5,.5,.5)),('ROUGHNESS',.5),('NORMAL',(0,0,1))]:
            prop=getattr(u.MaterialProperty,'MP_'+pname);node=L.get_material_property_input_node(wet,prop)
            original[pname]=(node,L.get_material_property_input_node_output_name(wet,prop)) if node else weather['vector'](wet,default) if isinstance(default,tuple) else weather['constant'](wet,default)
        amount=weather['scalar'](wet,'WeaponWetness',0)
        if mask=='vertex':
            vertex=weather['node'](wet,u.MaterialExpressionVertexColor)
            amount=weather['custom'](wet,'return Wet*Metal;',dict(Wet=amount,Metal=(vertex,'R')),1,'Preserve optical aperture and rubber')
        elif mask=='metal':
            prop=u.MaterialProperty.MP_METALLIC;node=L.get_material_property_input_node(wet,prop)
            amount=weather['custom'](wet,'return Wet*saturate((Metal-.25)*2);',dict(Wet=amount,Metal=(node,L.get_material_property_input_node_output_name(wet,prop))),1,'Preserve nonmetal optical surface')
        beads=weather['custom'](wet,(ROOT/'SourceAssets/WeatherNatural20260912/WeaponBeads.hlsl').read_text(),dict(UV=weather['node'](wet,u.MaterialExpressionTextureCoordinate),Wet=amount),4,'WeatherBeads')
        weather['prop'](weather['custom'](wet,'return Base*(1-Data.a*.07);',dict(Base=original['BASE_COLOR'],Data=beads),3),'BASE_COLOR')
        weather['prop'](weather['custom'](wet,'return lerp(lerp(Base,max(.085,Base*.70),Data.a),.065,Data.b*.8);',dict(Base=original['ROUGHNESS'],Data=beads),1),'ROUGHNESS')
        weather['prop'](weather['custom'](wet,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.35)+Data.xy,Base.z));',dict(Base=original['NORMAL'],Data=beads),3),'NORMAL')
        E.set_metadata_tag(wet,'DW715AttachmentWet','1');L.recompile_material(wet);save(wet)
    report['wet_materials'][dry]=wet.get_path_name()
for path in ['/Game/Weather/RainVisibility/DA_WeatherPresentation','/Game/Weather/NaturalV2/DA_WeatherPresentation']:
    library=u.load_asset(path);mapping=dict(library.get_editor_property('wet_materials'));mapping.update({dry:u.load_asset(wet) for dry,wet in report['wet_materials'].items()});library.set_editor_property('wet_materials',mapping);save(library)
    checks=[]
    # Explicitly requested rain inspection: cover current gun and new metal
    # attachment materials. Dedicated glass and reticle assets stay optical.
    current=u.load_asset('/Game/Weapons/DanWesson715/MetalFinish20260914/SK_DW715_Manny')
    surfaces={slot.material_interface.get_path_name():slot.material_interface for slot in current.materials if 'DW715' in slot.material_interface.get_name()}
    surfaces.update({dry:pair[0] for dry,pair in dry_materials.items()})
    for dry in surfaces:
        wet=mapping.get(dry);params=[str(x) for x in L.get_scalar_parameter_names(wet)] if wet else []
        channels=[L.get_material_property_input_node(wet,getattr(u.MaterialProperty,'MP_'+name)) is not None for name in ['BASE_COLOR','ROUGHNESS','NORMAL']] if wet else []
        check=dict(dry=dry,wet=wet.get_path_name() if wet else None,parameter='WeaponWetness' in params,channels=channels);checks.append(check)
        if not wet or not check['parameter'] or not all(channels):raise RuntimeError('Incomplete requested rain integration '+dry)
    report['rain_check'][path]=checks
report['state']='Imported and saved; requested rain asset bindings/parameter connections checked. No game, render or visual acceptance test.'
(O/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('DW715_ATTACHMENTS_IMPORT_COMPLETE rain_surfaces='+str(len(surfaces)))
