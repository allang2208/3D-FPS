"""Author/save a bounded-cost navy short-pile surface from existing library maps.

Changes the hub structure's blue material slot only. Height/orientation masks
retain its blue stone underside. No world/PIE transition, render or acceptance.
"""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT=Path(__file__).parent
PROJECT=ROOT.parents[2]
DEST='/Game/Props/GodSpaceLayout20260927'
SOURCE='/Game/SubstrateMaterials/Textures/02_Upholstery/Textiles/'
L=u.MaterialEditingLibrary
TOOLS=u.AssetToolsHelpers.get_asset_tools()

def configure_carpet_density(mesh):
    slots=list(mesh.get_editor_property('static_materials'));old=None
    for slot in slots:
        if str(slot.get_editor_property('imported_material_slot_name')).lower()!='blue grey stone inlay':continue
        info=slot.get_editor_property('uv_channel_data')
        old=list(info.get_editor_property('local_uv_densities'))
        # Imported/built mesh UV data is already initialized. That internal
        # flag is not exposed by Python; only edit the supported density fields.
        info.set_editor_property('override_densities',True)
        # Density is centimetres per UV unit: use the largest physical tile
        # (90 cm), so height/colour retain enough pixels at normal view distance.
        info.set_editor_property('local_uv_densities',[90.0]*4)
        # get_editor_property returns a struct reference. The container itself
        # is read-only, but its supported density members are editable in place.
    if old is None:raise RuntimeError('Missing blue inlay streaming metadata')
    mesh.set_editor_property('static_materials',slots)
    return old

def build(apply_binding=True):
    master_path=DEST+'/Materials/M_GodSpaceNavyCarpet'
    instance_path=DEST+'/Materials/MI_GodSpaceNavyCarpet'
    mesh_path=DEST+'/Meshes/SM_GodSpaceStructure'
    texture_paths=[DEST+'/Textures/T_GodSpaceCarpet_'+c for c in ['BC','N','R']]
    relief_paths=[DEST+'/Textures/T_GodSpaceCarpetRelief_'+c for c in ['N','HAR']]
    owned=[master_path,instance_path]+texture_paths+relief_paths+([mesh_path] if apply_binding else [])
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection(owned):raise RuntimeError('Preserve unsaved target assets: '+str(dirty.intersection(owned)))
    report={'saved':[],'backups':[],'sources':[],'runtime_tested':False,'screenshots_taken':False}
    backup=PROJECT/'trash/godspace-navy-carpet-20260928'/datetime.now().strftime('%H%M%S-%f')
    backup.mkdir(parents=True,exist_ok=True)
    previous_receipt=ROOT/'Receipts/navy-carpet-saved.json'
    if previous_receipt.exists():shutil.copy2(previous_receipt,backup/'previous-receipt.json')
    for path in owned:
        src=PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset')
        if src.exists():
            dst=backup/'Content'/src.relative_to(PROJECT/'Content')
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
            report['backups'].append({'file':str(dst),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()})
    def load(path):
        asset=u.load_asset(path)
        if not asset:raise RuntimeError('Required asset missing '+path)
        return asset
    def save(asset):
        # Save exactly the authored package, including while another map is in
        # PIE. Never save a PIE world or flush unrelated dirty content/maps.
        if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
            raise RuntimeError('Cannot save '+asset.get_path_name())
        report['saved'].append(asset.get_path_name())
        (ROOT/'Receipts/navy-carpet-saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    textures={}
    for channel,path in zip(['BC','N','R'],texture_paths):
        src=load(SOURCE+'T_Carpet_01_'+channel)
        tex=u.load_asset(path) or TOOLS.duplicate_asset(path.rsplit('/',1)[1],DEST+'/Textures',src)
        if not tex:raise RuntimeError('Cannot create owned carpet texture '+channel)
        tex.set_editor_property('max_texture_size',2048)
        tex.set_editor_property('never_stream',False)
        tex.set_editor_property('srgb',channel=='BC')
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='N' else u.TextureCompressionSettings.TC_DEFAULT if channel=='BC' else u.TextureCompressionSettings.TC_GRAYSCALE)
        tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP if channel=='N' else u.TextureGroup.TEXTUREGROUP_WORLD)
        tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
        tex.set_editor_property('address_x',u.TextureAddress.TA_WRAP)
        tex.set_editor_property('address_y',u.TextureAddress.TA_WRAP)
        textures[channel]=tex
        report['sources'].append({'source':src.get_path_name(),'derived':tex.get_path_name(),'max_size':2048})
        save(tex)

    for channel,path in zip(['ReliefN','HAR'],relief_paths):
        name=path.rsplit('/',1)[1]
        task=u.AssetImportTask();task.filename=str(ROOT/'CarpetRelief'/(name+'.png'))
        task.destination_path=DEST+'/Textures';task.destination_name=name
        task.automated=True;task.replace_existing=True;task.save=False
        TOOLS.import_asset_tasks([task]);tex=load(path)
        tex.set_editor_property('max_texture_size',2048);tex.set_editor_property('never_stream',False)
        tex.set_editor_property('srgb',False);tex.set_editor_property('lod_bias',0)
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='ReliefN' else u.TextureCompressionSettings.TC_MASKS)
        tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP if channel=='ReliefN' else u.TextureGroup.TEXTUREGROUP_WORLD)
        tex.set_editor_property('address_x',u.TextureAddress.TA_WRAP);tex.set_editor_property('address_y',u.TextureAddress.TA_WRAP)
        textures[channel]=tex;save(tex)

    mat=u.load_asset(master_path) or TOOLS.create_asset('M_GodSpaceNavyCarpet',DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    for old in list(L.get_material_expressions(mat)):L.delete_material_expression(mat,old)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_CLOTH)
    mat.set_editor_property('tangent_space_normal',False)
    mat.set_editor_property('two_sided',False)
    mat.set_editor_property('use_material_attributes',True)
    def node(cls):return L.create_material_expression(mat,cls)
    attributes=node(u.MaterialExpressionMakeMaterialAttributes)
    if not L.connect_material_property(attributes,'',u.MaterialProperty.MP_MATERIAL_ATTRIBUTES):
        raise RuntimeError('Cannot connect material attributes')
    def wire(a,b,pin,output=''):
        if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Cannot connect '+pin)
    def prop(n,name,output=''):
        # MP_CustomData0 is hidden from Python. MakeMaterialAttributes exposes
        # its ClearCoat input, which the Cloth shading model interprets as fuzz.
        pin={'BASE_COLOR':'BaseColor','NORMAL':'Normal','ROUGHNESS':'Roughness',
             'METALLIC':'Metallic','SPECULAR':'Specular','SUBSURFACE_COLOR':'SubsurfaceColor',
             'AMBIENT_OCCLUSION':'AmbientOcclusion','CUSTOM_DATA0':'ClearCoat'}[name]
        wire(n,attributes,pin,output)
    def scalar(name,value):
        n=node(u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
    def vector(name,value):
        n=node(u.MaterialExpressionVectorParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',u.LinearColor(*value,1));return n
    def custom(code,inputs,width,desc):
        n=node(u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('description',desc)
        n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
        pins=[]
        for name in inputs:
            pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
        n.set_editor_property('inputs',pins)
        for name,source in inputs.items():wire(source,n,name)
        return n
    def tex_object(channel,name):
        n=node(u.MaterialExpressionTextureObjectParameter);n.set_editor_property('texture',textures[channel])
        n.set_editor_property('parameter_name',name)
        n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel in ['N','ReliefN'] else u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel=='BC' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        return n

    pos=node(u.MaterialExpressionWorldPosition)
    pos.set_editor_property('world_position_shader_offset',u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    vertex_normal=node(u.MaterialExpressionVertexNormalWS)
    camera=node(u.MaterialExpressionCameraPositionWS)
    fade=custom('return 1-smoothstep(350,1600,length(P-C));',{'P':pos,'C':camera},1,'Fade fine pile normals and seam stitches at distance')
    edging=custom('''float2 p=P.xy-float2(-2400,-1300);
float2 a=abs(p)-float2(470,4400);
float da=length(max(a,0))+min(max(a.x,a.y),0);
float2 b=abs(p-float2(0,800))-float2(3650,260);
float db=length(max(b,0))+min(max(b.x,b.y),0);
float2 c=abs(p-float2(0,2700))-float2(600,600);
float dc=length(max(c,0))+min(max(c.x,c.y),0);
float edge=max(0,-(P.z>80?dc:min(da,db)));
float bound=1-smoothstep(4,7,edge);
float aa=max(fwidth(edge),.06);
float seamLine=1-smoothstep(.07,.07+aa,abs(edge-2.4));
float dash=1-smoothstep(.27,.42,abs(frac((p.x+p.y)/.8)-.5));
return float2(bound,seamLine*dash*Fade);''',{'P':pos,'Fade':fade},2,'Navy woven binding and restrained champagne stitching inside existing metal borders')
    inputs={'Position':pos,'VertexNormal':vertex_normal,'Camera':camera,'Edge':edging,
        'Tint':vector('NavyPileColor',(.020,.052,.12)),
        'TileCm':scalar('PileTileCm',90),'DepthCm':scalar('PileReliefDepthCm',.38),
        'NormalStrength':scalar('PileNormalStrength',1.0),'FineStrength':scalar('FineNormalStrength',.65),
        'FuzzAmount':scalar('PileFuzzAmount',.20),
        'ColorTex':tex_object('BC','PileColorTexture'),'HeightTex':tex_object('HAR','PileHeightTexture'),
        'ReliefNormal':tex_object('ReliefN','PileReliefNormal'),'FineNormal':tex_object('N','PileFineNormal')}
    shader=custom((ROOT/'carpet_relief.ush').read_text(encoding='utf8'),inputs,4,'Shared-coordinate pile relief with near-only bounded POM and RNM fine fibers')
    outputs=[]
    for name,width in [('NormalWorld',3),('AO',1),('Fuzz',1),('Metallic',1),('Specular',1)]:
        out=u.CustomOutput();out.set_editor_property('output_name',name)
        out.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)));outputs.append(out)
    shader.set_editor_property('additional_outputs',outputs)
    color=node(u.MaterialExpressionComponentMask)
    for k,v in [('r',True),('g',True),('b',True),('a',False)]:color.set_editor_property(k,v)
    wire(shader,color,'');prop(color,'BASE_COLOR')
    rough=node(u.MaterialExpressionComponentMask)
    for k,v in [('r',False),('g',False),('b',False),('a',True)]:rough.set_editor_property(k,v)
    wire(shader,rough,'');prop(rough,'ROUGHNESS')
    for name,p in [('NormalWorld','NORMAL'),('AO','AMBIENT_OCCLUSION'),('Fuzz','CUSTOM_DATA0'),('Metallic','METALLIC'),('Specular','SPECULAR')]:prop(shader,p,name)
    prop(vector('PileFuzzColor',(.045,.08,.14)),'SUBSURFACE_COLOR')
    errors=list(L.recompile_material(mat))
    if errors:raise RuntimeError('Navy carpet shader compilation failed: '+str(errors))
    save(mat)
    instance=u.load_asset(instance_path) or TOOLS.create_asset('MI_GodSpaceNavyCarpet',DEST+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(instance,mat);L.update_material_instance(instance);save(instance)
    if apply_binding:
        mesh=load(mesh_path)
        changed=[]
        for index,slot in enumerate(mesh.get_editor_property('static_materials')):
            name=str(slot.get_editor_property('imported_material_slot_name')).lower()
            if name=='blue grey stone inlay':
                mesh.set_material(index,instance);changed.append(index)
        if len(changed)!=1:raise RuntimeError('Expected exactly one blue inlay material slot; found '+str(changed))
        report['previous_streaming_density']=configure_carpet_density(mesh)
        save(mesh)
        report['changed_slots']=changed
    report.update(complete=True,revision='relief-v2',shader_compile_errors=errors,material=instance.get_path_name(),
        near_texture_lookups_max=14,far_texture_lookups=3,unique_textures=4,max_texture_size=2048,
        source_variant='Carpet 01 with normal-derived registered relief',added_triangles=0,
        added_material_slots=0,parallax_steps=8,parallax_refine_steps=2,relief_depth_cm=.38,
        relief_fade_cm=[220,650],streaming_density_cm=90.0,added_translucent_layers=0,simulation=False,
        existing_marble_and_brass_preserved=True,blue_stone_underside_preserved=True,map_changed=False,
        fab_asset_downloaded=False,library_source='Existing /Game/SubstrateMaterials; source library assets unchanged')
    (ROOT/'Receipts/navy-carpet-saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('GODSPACE_NAVY_CARPET_SAVED '+json.dumps(report))
    return instance

if __name__=='__main__':build()
