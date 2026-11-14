"""Finish the three local masks and seat the existing scanned fragments at their actual receivers."""
from pathlib import Path
import unreal as u
R=Path(__file__).resolve().parent
BASE='/Game/SceneTests/FreightOppositePlatform20261113'
def apply(w,req):
    E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    tasks=[]
    for file in sorted((R/'CompletionTextures').glob('*.png')):
        t=u.AssetImportTask();t.filename=str(file);t.destination_path=BASE+'/Textures';t.destination_name=file.stem+'Finish'
        t.automated=True;t.save=False;tasks.append(t)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    source_master=u.load_asset('/Game/SceneTests/FreightCartBay20261113/Materials/M_PlatformWeathering')
    for role in ['Aisle','ToeReturn','ToePipe']:
        path=BASE+'/Materials/MI_'+role+'Finish'
        mi=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(BASE+'/Materials/MI_'+role,path)
        for suffix,param in [('Color','PatinaColor'),('Rough','PatinaRoughness')]:
            tex=u.load_asset(BASE+'/Textures/T_'+role+'_'+suffix+'Finish')
            if not tex:raise RuntimeError('Finish texture missing')
            tex.modify();tex.set_editor_property('srgb',suffix=='Color')
            tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_DEFAULT if suffix=='Color' else u.TextureCompressionSettings.TC_MASKS)
            tex.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);tex.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
            if not E.save_loaded_asset(tex,False):raise RuntimeError('Texture save failed')
            L.set_material_instance_texture_parameter_value(mi,param,tex)
        if not E.save_loaded_asset(mi,False):raise RuntimeError('Material save failed')
        c=actors['OppositePlatform_'+role].get_component_by_class(u.DecalComponent);c.modify();c.set_decal_material(mi)
    # The plaster skim faces +X / +Y. Seat thin scanned reliefs flush to their current wall layers.
    adjustments=[('PipeBracket',[6480,-3034.62,247],[.69,.95,.44]),
                 ('ReturnToe',[6177.12,-2463,24],[.72,.9,.39]),
                 ('CabinetToe',[6548,-3032.28,22],[.39,.9,.41])]
    for name,pos,scale in adjustments:
        a=actors['OppositePlatform_'+name];a.modify()
        a.set_actor_location(u.Vector(*pos),False,False);a.set_actor_scale3d(u.Vector(*scale))
    return {'ground_and_skirt_finishes':3,'local_reliefs':3}
