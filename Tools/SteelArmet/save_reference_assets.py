"""Save rigid head attachment, item meshes, model-derived icon and visor texture."""
import json,hashlib,sys,importlib.util
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SteelArmet20261019';O=R/'ReferenceMatchV5';DEST='/Game/Characters/ModularOutfit20260924/SteelArmet20261019/ReferenceMatchV5'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
def module(name,path):
    s=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
dynamic=module('armet_dynamic','Tools/BlueMageSetIcons/save_icons.py').dynamic
static_io=module('armet_static','Tools/ChainmailPants/save_assets.py');static_io.DEST=DEST
def save(asset):
    if not asset or not asset.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside armet asset scope')
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
def texture(file,name):
    source_sha=hashlib.sha256(file.read_bytes()).hexdigest()
    t=u.AssetImportTask();t.filename=str(file);t.destination_path=DEST+'/Textures';t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=False
    A.import_asset_tasks([t]);tex=u.load_asset(DEST+'/Textures/'+name)
    for k,v in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,srgb=True).items():tex.set_editor_property(k,v)
    tex.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);tex.set_editor_property('address_y',u.TextureAddress.TA_CLAMP);E.set_metadata_tag(tex,'SteelArmetSourceSHA',source_sha);save(tex);return tex.get_path_name()
def materials():
    L=u.MaterialEditingLibrary;folder=DEST+'/Materials';E.make_directory(folder);result=[]
    def node(m,kind,**props):
        n=L.create_material_expression(m,kind)
        for k,v in props.items():n.set_editor_property(k,v)
        return n
    def wire(a,b,pin,out=''):
        if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material connection failed '+pin)
    def output(a,prop,pin=''):
        if not L.connect_material_property(a,pin,prop):raise RuntimeError('Material output failed '+str(prop))
    for family in ('Steel','Leather'):
        path=folder+'/M_Armet_'+family;m=u.load_asset(path) or A.create_asset('M_Armet_'+family,folder,u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(m)
        coord=node(m,u.MaterialExpressionTextureCoordinate,u_tiling=1. if family=='Steel' else 2.,v_tiling=1. if family=='Steel' else 2.)
        for ch in ('BaseColor','Normal','ORM'):
            name='T_Armet_'+family+'_'+ch;t=u.AssetImportTask();t.filename=str(O/'Textures'/(name+'.png'));t.destination_path=DEST+'/Textures';t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);tex=u.load_asset(DEST+'/Textures/'+name)
            tex.set_editor_property('srgb',ch=='BaseColor');tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if ch=='Normal' else u.TextureCompressionSettings.TC_MASKS if ch=='ORM' else u.TextureCompressionSettings.TC_DEFAULT);tex.set_editor_property('flip_green_channel',ch=='Normal');save(tex)
            sample=node(m,u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if ch=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if ch=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR);wire(coord,sample,'UVs')
            if ch=='BaseColor':output(sample,u.MaterialProperty.MP_BASE_COLOR,'RGB')
            elif ch=='Normal':
                strength=.65 if family=='Steel' else 1.;scale=node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(strength,strength,1,1));mul=node(m,u.MaterialExpressionMultiply);wire(sample,mul,'A','RGB');wire(scale,mul,'B');norm=node(m,u.MaterialExpressionNormalize);wire(mul,norm,'VectorInput');output(norm,u.MaterialProperty.MP_NORMAL)
            else:
                for pin,prop in [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]:output(sample,prop,pin)
        errors=L.recompile_material(m)
        if errors:raise RuntimeError(str(errors))
        save(m);result.append(m)
    for name,color,metal,rough in [('WorkedEdges',(.40,.42,.44),1,.43),('DarkenedSteel',(.20,.22,.24),1,.48),('WaxedStitch',(.085,.065,.042),0,.84)]:
        m=u.load_asset(folder+'/M_Armet_'+name) or A.create_asset('M_Armet_'+name,folder,u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(m);c=node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*color,1));output(c,u.MaterialProperty.MP_BASE_COLOR)
        for value,prop in [(metal,u.MaterialProperty.MP_METALLIC),(rough,u.MaterialProperty.MP_ROUGHNESS)]:output(node(m,u.MaterialExpressionConstant,r=value),prop)
        errors=L.recompile_material(m)
        if errors:raise RuntimeError(str(errors))
        save(m);result.append(m)
    return result
def main():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        level=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if level and level.is_in_play_in_editor():raise RuntimeError('Preserve current play session')
    E.make_directory(DEST)
    source=json.loads((O/'authored.json').read_text())
    if not source.get('completed') or source.get('geometry_revision')!='reference-profile-v5':raise RuntimeError('Reference V5 Blender model incomplete')
    if not json.loads((O/'visor.json').read_text()).get('completed'):raise RuntimeError('Reference visor incomplete')
    old=json.loads((O/'saved_assets.json').read_text()) if (O/'saved_assets.json').exists() else {}
    receipt=dict(completed=False,runtime_tested=False,saved=old.get('saved',{}))
    def record():(O/'saved_assets.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    record()
    mats=materials();matpaths=[m.get_path_name() for m in mats]
    for key,file,path in [('mesh','helmet.json','SM_SteelArmet'),('pickup','helmet.json','Pickups/SM_SteelArmet_Pickup'),('icon','display.json','Icons/SM_SteelArmet_Icon')]:
        raw=(O/'Authored'/file).read_bytes();sha=hashlib.sha256(raw).hexdigest();asset=u.load_asset(DEST+'/'+path)
        if not asset or E.get_metadata_tag(asset,'SteelArmetSourceSHA')!=sha:
            d=json.loads(raw);dm=dynamic(d);result=static_io.static(dm,DEST+'/'+path,mats);asset=u.load_asset(result)
            E.set_metadata_tag(asset,'SteelArmetSourceSHA',sha);E.set_metadata_tag(asset,'EquipmentDefinition','ue_steel_armet');save(asset)
        receipt['saved'][key]=dict(asset=asset.get_path_name(),sha256=sha);record();print('STEEL_ARMET_SAVED',key,flush=True)
    receipt.update(mesh=receipt['saved']['mesh']['asset'],pickup=receipt['saved']['pickup']['asset'],icon=receipt['saved']['icon']['asset'],materials=matpaths,
        icon_texture=texture(O/'ue_steel_armet.png','T_SteelArmet_Icon'),visor_texture=texture(O/'Textures/T_SteelArmet_Visor.png','T_SteelArmet_Visor'),fits=json.loads((R/'fit.json').read_text())['fits'],source_revision='ReferenceMatchV5',completed=True)
    receipt['visor_sha256']=E.get_metadata_tag(u.load_asset(receipt['visor_texture']),'SteelArmetSourceSHA')
    record();print('STEEL_ARMET_ASSETS_SAVED',flush=True)
if __name__=='__main__':main()
