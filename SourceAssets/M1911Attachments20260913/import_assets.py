"""Import shared parts fitted to the accepted M1911, with its own blued finish."""
import unreal as u,json,ast
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/M1911/Attachments20260913'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
# Reuse the existing material graph helper operations without running rifle imports.
tree=ast.parse((O.parent/'WeaponAttachmentFinish20260913/import_finish.py').read_text(encoding='utf-8'))
helpers={'save','node','link','output','constant','mul','clone'}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in helpers],type_ignores=[]),'<shared material helpers>','exec'))
sources=json.loads((O/'sources.json').read_text())['parts'];auth=json.loads((O/'authoring.json').read_text());textures={};report={}
for kind in ['BaseColor','ORM']:
    name='T_M1911_Attachment_'+kind;t=u.AssetImportTask();t.filename=str(O/'Textures'/(name+'.png'));t.destination_path=D+'/Textures';t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=False
    A.import_asset_tasks([t]);tex=u.load_asset(t.destination_path+'/'+name)
    tex.srgb=kind=='BaseColor';tex.compression_settings=u.TextureCompressionSettings.TC_DEFAULT if kind=='BaseColor' else u.TextureCompressionSettings.TC_MASKS
    tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
    tex.set_editor_property('address_x',u.TextureAddress.TA_MIRROR);tex.set_editor_property('address_y',u.TextureAddress.TA_MIRROR)
    save(tex);textures[kind]=tex
def coating(key,index,original,uv_index):
    path=D+'/Materials/M_M1911_'+key+'_'+str(index)
    if isinstance(original,u.MaterialInstanceConstant):
        base=original.get_base_material();m=clone(base.get_path_name(),path+'_Graph');result=clone(original.get_path_name(),path)
        values={kind:{str(n):getattr(L,'get_material_instance_'+kind+'_parameter_value')(original,n) for n in getattr(L,'get_'+kind+'_parameter_names')(base)} for kind in ['scalar','vector','texture','static_switch']}
        L.set_material_instance_parent(result,m)
        for kind,params in values.items():
            for name,value in params.items():
                if value is not None:getattr(L,'set_material_instance_'+kind+'_parameter_value')(result,name,value)
    elif original:m=clone(original.get_path_name(),path);result=m
    else:
        m=u.load_asset(path) or A.create_asset(path.rsplit('/',1)[1],D+'/Materials',u.Material,u.MaterialFactoryNew());result=m
    if E.get_metadata_tag(m,'M1911Coating')!='20260913':
        uv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=uv_index);samples={}
        for kind,tex in textures.items():
            sample=node(m,u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
            link(uv,'',sample,'UVs');samples[kind]=sample
        mask=None
        if original and key in ['holographic','panoramic_red_dot']:
            metal=L.get_material_property_input_node(m,u.MaterialProperty.MP_METALLIC)
            if metal:
                mask=node(m,u.MaterialExpressionSmoothStep,const_min=.2,const_max=.4)
                link(metal,L.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_METALLIC),mask,'Value')
        bc=L.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)
        if bc:
            lum=node(m,u.MaterialExpressionDesaturation);link(bc,L.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_BASE_COLOR),lum,'Input');link(constant(m,1),'',lum,'Fraction')
            white=node(m,u.MaterialExpressionSmoothStep,const_min=.55,const_max=.82);link(lum,'',white,'Value')
            marks=node(m,u.MaterialExpressionOneMinus);link(white,'',marks,'Input');mask=mul(m,mask,marks) if mask else marks
        for prop,sample,out in [(u.MaterialProperty.MP_BASE_COLOR,samples['BaseColor'],'RGB'),(u.MaterialProperty.MP_ROUGHNESS,samples['ORM'],'G'),(u.MaterialProperty.MP_METALLIC,samples['ORM'],'B')]:
            if mask:
                old=L.get_material_property_input_node(m,prop);oldout=L.get_material_property_input_node_output_name(m,prop)
                old=old or constant(m,0)
                blend=node(m,u.MaterialExpressionLinearInterpolate);link(old,oldout,blend,'A');link(sample,out,blend,'B');link(mask,'',blend,'Alpha');output(blend,'',prop)
            else:output(sample,out,prop)
        # UV0 normals/AO, glass, reticle, rubber and markings remain from the shared source.
        E.set_metadata_tag(m,'M1911Coating','20260913');L.recompile_material(m)
    save(m)
    if result!=m:L.update_material_instance(result);save(result)
    return result
for key,info in sources.items():
    author=auth[key];bindings={};aliases={}
    for i,slot in enumerate(info['slots']):
        original=u.load_asset(slot['material']);label=slot['slot']
        target=label in ['Holosight','Panoramic_Body','RifleMetal']
        bindings[label]=coating(key,i,original,author['uv_index']) if target else original
        exported=author['source_export_slots'][i];aliases[exported]=label;aliases[exported.replace('.','_')]=label
    bindings['M1911_AdapterSteel']=coating(key,'Adapter',None,author['uv_index'])
    name='SM_M1911_'+key;t=u.AssetImportTask();t.filename=author['file'];t.destination_path=D+'/Meshes';t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=False
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.vertex_color_import_option=u.VertexColorImportOption.REPLACE;t.options=opt;A.import_asset_tasks([t])
    mesh=u.load_asset(t.destination_path+'/'+name);slots=mesh.static_materials
    for i,slot in enumerate(slots):
        exported=str(slot.material_slot_name);label=exported if exported in bindings else aliases[exported]
        slot.material_interface=bindings[label];slot.material_slot_name=u.Name(label);slots[i]=slot
    mesh.set_editor_property('static_materials',slots);E.set_metadata_tag(mesh,'M1911AttachmentSource',info['path']);save(mesh)
    report[key]={'mesh':mesh.get_path_name(),'source':info['path'],'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots},'coating_uv':author['uv_index']}
    (O/'installed.json').write_text(json.dumps(report,indent=2));u.log('M1911_ATTACHMENT_IMPORTED '+key)
u.log('M1911_ATTACHMENT_IMPORT_COMPLETE')
