"""Install a region-masked carbon finish on the accepted M24 regional mother material."""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parents[1];D='/Game/Weapons/M24/CarbonBolt20261029'
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
R={'complete':False,'saved':[],'runtime_tested':False}
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    R['saved'].append(a.get_path_name());(O/'install_receipt.json').write_text(json.dumps(R,indent=2))
if any(p.get_name().startswith(D) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Unsaved carbon-bolt edits retained')
def load(p):
    a=u.load_asset(p)
    if not a:raise RuntimeError('Missing '+p)
    return a
name='T_M24_CarbonWeaveMask';t=u.AssetImportTask();t.filename=str(O/'Textures'/(name+'.png'))
t.destination_path=D+'/Textures';t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=False
A.import_asset_tasks([t]);tex=load(t.destination_path+'/'+name)
tex.set_editor_property('srgb',False);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON);save(tex)
path=D+'/Materials/M_M24CarbonBoltSurface'
master=load(path) if E.does_asset_exist(path) else E.duplicate_asset('/Game/Weapons/M24/Surface20261027/Materials/M_M24RegionalSurface',path)
if E.get_metadata_tag(master,'M24CarbonRecipe')!='OriginalBoltTwillV1':
    nodes=L.get_material_expressions(master)
    customs={str(n.get_editor_property('description')):n for n in nodes if isinstance(n,u.MaterialExpressionCustom)}
    sample=L.create_material_expression(master,u.MaterialExpressionTextureSampleParameter2D)
    sample.set_editor_property('parameter_name','CarbonWeaveMask');sample.set_editor_property('texture',tex)
    sample.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    def add_input(node,name):
        pins=list(node.get_editor_property('inputs'));pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
        node.set_editor_property('inputs',pins)
        if not L.connect_material_expressions(sample,'RGB',node,name):raise RuntimeError('Carbon input '+name)
    cr=customs['WS_ColorRough'];add_input(cr,'Carbon')
    code=cr.get_editor_property('code')
    old='return float4(max(base,0.),clamp(r,.05,1.));'
    if old not in code:raise RuntimeError('M24 dry finish return changed; retain current graph')
    cr.set_editor_property('code',code.replace(old,
        'float cf=saturate(Carbon.r);\n'
        'float3 fiber=lerp(float3(.012,.014,.016),float3(.031,.034,.038),saturate(Carbon.g));\n'
        'fiber*=lerp(.92,1.04,Carbon.b);\n'
        'base=lerp(base,fiber,cf);r=lerp(r,lerp(.36,.27,Carbon.g)+.015*Carbon.b,cf);\n'+old))
    ma=customs['WS_MetalAO'];add_input(ma,'Carbon')
    ma.set_editor_property('code',ma.get_editor_property('code').replace('return float4(metal,ao,0,0);','return float4(metal*(1-saturate(Carbon.r)),ao,0,0);'))
    # The shared source normal remains intact. Wetness runs after this dry finish.
    E.set_metadata_tag(master,'M24CarbonRecipe','OriginalBoltTwillV1')
master.set_editor_property('automatically_set_usage_in_editor',False)
master.set_editor_property('used_with_skeletal_mesh',True);master.set_editor_property('used_with_morph_targets',True)
errors=list(L.recompile_material(master) or [])
if errors:raise RuntimeError('Carbon material compile: '+str(errors[:5]))
save(master)
path=D+'/Materials/MI_M24_CarbonBolt'
mi=load(path) if E.does_asset_exist(path) else E.duplicate_asset('/Game/Weapons/M24/Surface20261027/Materials/MI_M24_Body',path)
L.set_material_instance_parent(mi,master);L.set_material_instance_texture_parameter_value(mi,'CarbonWeaveMask',tex)
L.update_material_instance(mi);save(mi)
icons=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
dest='/Game/UI/AttachmentIcons20260913/FramedFirearms'
mapping={'ue_m24_category_bolt':'false','ue_m24_bolt_false':'false','bolt_m24_carbon_light_bolt':'m24_carbon_light_bolt',
         'ue_m24_bolt_m24_carbon_light_bolt':'m24_carbon_light_bolt'}
for key,source in mapping.items():
    target=icons/(key+'.png');shutil.copy2(O/'Icons'/(source+'.png'),target)
    t=u.AssetImportTask();t.filename=str(target);t.destination_path=dest;t.destination_name='T_'+key
    t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);a=load(dest+'/'+t.destination_name)
    for prop,value in {'lod_group':u.TextureGroup.TEXTUREGROUP_UI,'compression_settings':u.TextureCompressionSettings.TC_EDITOR_ICON,
        'srgb':True,'never_stream':True,'mip_gen_settings':u.TextureMipGenSettings.TMGS_NO_MIPMAPS,'max_texture_size':1024}.items():a.set_editor_property(prop,value)
    save(a)
R.update(complete=True,material=mi.get_path_name(),icons=mapping,geometry_changed=False,source_actions_changed=False)
(O/'install_receipt.json').write_text(json.dumps(R,indent=2));print('M24_CARBON_BOLT_ASSETS_SAVED',len(R['saved']))
