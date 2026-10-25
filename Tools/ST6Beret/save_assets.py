"""Build and save refined beret wear, pickup, display and PBR assets."""
import json,hashlib,importlib.util,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ST6Beret20261023/SurfaceV2';DEST='/Game/Characters/ModularOutfit20260924/ST6Beret20261023/SurfaceV2'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing beret asset '+path)
    return a
def save(asset):
    if not asset.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside beret scope')
    asset.modify()
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
receipt=dict(completed=False,runtime_tested=False)
def record():(R/'saved_assets.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def textures():
    result={};E.make_directory(DEST+'/Textures')
    for family in read(R/'textures.json')['maps']:
        for channel in ('BaseColor','Normal','ORM'):
            name='T_'+family['name']+'_'+channel;task=u.AssetImportTask();task.filename=str(R/'Textures'/(name+'.png'));task.destination_path=DEST+'/Textures';task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);tex=load(DEST+'/Textures/'+name)
            for prop,value in dict(srgb=channel=='BaseColor',compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS if channel=='ORM' else u.TextureCompressionSettings.TC_DEFAULT,flip_green_channel=channel=='Normal',never_stream=False,max_texture_size=family['resolution'],compression_no_alpha=True,address_x=u.TextureAddress.TA_WRAP,address_y=u.TextureAddress.TA_WRAP).items():tex.set_editor_property(prop,value)
            save(tex);result[family['name']+'_'+channel]=tex
    return result
def material(row,tex):
    name='M_'+row['name'];folder=DEST+'/Materials';E.make_directory(folder);mat=u.load_asset(folder+'/'+name) or A.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(mat);mat.set_editor_property('use_material_attributes',True);mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_CLOTH if row['cloth'] else u.MaterialShadingModel.MSM_DEFAULT_LIT)
    def node(cls):return L.create_material_expression(mat,cls)
    def wire(a,b,pin,out=''):
        if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Beret material pin '+pin)
    def scalar(v):
        n=node(u.MaterialExpressionConstant);n.set_editor_property('r',v);return n
    def color(v):
        n=node(u.MaterialExpressionConstant3Vector);n.set_editor_property('constant',u.LinearColor(*v,1));return n
    attrs=node(u.MaterialExpressionMakeMaterialAttributes)
    if row['family']:
        samples={}
        for channel in ('BaseColor','Normal','ORM'):
            n=node(u.MaterialExpressionTextureSampleParameter2D);n.set_editor_property('parameter_name',channel);n.set_editor_property('texture',tex[row['family']+'_'+channel]);n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR);samples[channel]=n
        base=samples['BaseColor'];wire(base,attrs,'BaseColor','RGB')
        strength=node(u.MaterialExpressionMultiply);wire(samples['Normal'],strength,'A','RGB');wire(color((.65,.65,1)),strength,'B');normal=node(u.MaterialExpressionNormalize);wire(strength,normal,'VectorInput');wire(normal,attrs,'Normal')
        for out,pin in [('R','AmbientOcclusion'),('G','Roughness'),('B','Metallic')]:wire(samples['ORM'],attrs,pin,out)
        if row['cloth']:
            tint=node(u.MaterialExpressionMultiply);wire(base,tint,'A','RGB');wire(scalar(.32),tint,'B');wire(tint,attrs,'SubsurfaceColor');wire(scalar(.28),attrs,'ClearCoat')
    else:
        wire(color(row['color']),attrs,'BaseColor');wire(scalar(row['roughness']),attrs,'Roughness');wire(scalar(row['metallic']),attrs,'Metallic')
    wire(scalar(.3 if row['cloth'] else .45),attrs,'Specular')
    if not L.connect_material_property(attrs,'',u.MaterialProperty.MP_MATERIAL_ATTRIBUTES):raise RuntimeError('Beret material output')
    if L.recompile_material(mat):raise RuntimeError('Beret shader compile '+name)
    save(mat);return mat

if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('Preserve active PIE; defer beret save')
record();tex=textures();mats=[material(row,tex) for row in read(R/'materials.json')];receipt['materials']=[m.get_path_name() for m in mats];receipt['textures']={k:v.get_path_name() for k,v in tex.items()};record()
io=module('st6_static_dynamic','Tools/FieldHat/save_icon.py');static=module('st6_static_asset_writer','Tools/ChainmailPants/save_assets.py');static.DEST=DEST
d=read(R/'Authored/hat.json');receipt['wear']=static.static(io.dynamic(d),DEST+'/SM_ST6_Beret_Wear',mats);record()
center=[(min(p[i] for p in d['positions'])+max(p[i] for p in d['positions']))*.5 for i in range(3)]
dm=io.dynamic(d);u.GeometryScript_MeshTransforms.translate_mesh(dm,u.Vector(*[-v for v in center]));receipt['pickup']=static.static(dm,DEST+'/Pickups/SM_ST6_Beret_Pickup',mats);record()
display=read(R/'ue_st6_tactical_helmet-display.json');dm=io.dynamic(display);u.GeometryScript_MeshTransforms.inverse_transform_mesh(dm,u.Transform(rotation=u.Rotator(pitch=0,yaw=-90,roll=0)));receipt['icon']=static.static(dm,DEST+'/Icons/SM_ST6_Beret_Icon',mats);record()
task=u.AssetImportTask();task.filename=str(R/'ue_st6_tactical_helmet.png');task.destination_path=DEST+'/Icons';task.destination_name='T_ST6_Beret_Icon';task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);icon=load(DEST+'/Icons/T_ST6_Beret_Icon')
for prop,value in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,srgb=True).items():icon.set_editor_property(prop,value)
save(icon);receipt.update(completed=True,icon_texture=icon.get_path_name(),fit=read(R/'fit_candidate.json')['fits'],author_sha256=hashlib.sha256((R/'Authored/hat.json').read_bytes()).hexdigest(),source_triangles=len(d['triangles']),lod_count=3,attachment='static head-bone follower; no new tick or simulation');record();print('ST6_BERET_ASSETS_SAVED',receipt['wear'],flush=True)
