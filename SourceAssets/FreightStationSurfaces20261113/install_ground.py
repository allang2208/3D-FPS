"""Apply separate non-colliding projections to the station's actual floor levels and tiled wall feet."""
from pathlib import Path
import json,random,math
import unreal as u
ROOT=Path(__file__).resolve().parent
BASE='/Game/SceneTests/FreightStationSurfaces20261113'
STOCK='/Game/SceneTests/FreightStationUnifiedPatina20261111/Materials/MI_'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
def textures(names):
    tasks=[];out={}
    folder=BASE+'/Textures'
    for name in sorted(names):
        for suffix in ['Color','Rough']:
            leaf='T_'+name+'_'+suffix;path=folder+'/'+leaf
            if not E.does_asset_exist(path):
                t=u.AssetImportTask();t.filename=str(ROOT/'Textures'/(leaf+'.png'));t.destination_path=folder;t.destination_name=leaf;t.automated=True;t.save=False
                tasks.append(t)
    if tasks:u.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    for name in sorted(names):
        out[name]=[]
        for suffix in ['Color','Rough']:
            leaf='T_'+name+'_'+suffix
            tex=u.load_asset(folder+'/'+leaf)
            if not tex:raise RuntimeError('Import failed '+leaf)
            tex.modify()
            tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_DEFAULT if suffix=='Color' else u.TextureCompressionSettings.TC_MASKS)
            tex.set_editor_property('srgb',suffix=='Color')
            tex.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);tex.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
            if not E.save_loaded_asset(tex,False):raise RuntimeError('Texture save failed '+leaf)
            out[name].append(tex)
    return out
def instances(rows):
    master=u.load_asset('/Game/SceneTests/FreightCartBay20261113/Materials/M_PlatformWeathering')
    if not master:raise RuntimeError('Approved platform master unavailable')
    result={};folder=BASE+'/Materials'
    for name,tex in textures({r['texture'] for r in rows}).items():
        leaf='MI_'+name;path=folder+'/'+leaf
        mi=u.load_asset(path) if E.does_asset_exist(path) else u.AssetToolsHelpers.get_asset_tools().create_asset(leaf,folder,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        if not mi:raise RuntimeError('Cannot create '+leaf)
        mi.modify();L.set_material_instance_parent(mi,master)
        for param,asset in zip(['PatinaColor','PatinaRoughness'],tex):
            L.set_material_instance_texture_parameter_value(mi,param,asset)
            if L.get_material_instance_texture_parameter_value(mi,param)!=asset:raise RuntimeError('Cannot bind '+param+' on '+name)
        if not E.save_loaded_asset(mi,False):raise RuntimeError('Cannot save '+name)
        result[name]=mi
    return result
def ceramic():
    # Each span runs on an original ceramic face. Exclude doorways and the approved cart bay.
    spans=[('South',1,234,6169,10936,-1),('NorthW',1,-3034,6175,8025,1),('NorthE',1,-3034,8345,10936,1),
           ('WestN',0,6176,-3032,-1560,1),('WestS',0,6176,-1240,228,1),
           ('AccessSouth',1,-1186,5878,6162,-1),('AccessNorth',1,-1614,5878,6162,1),
           ('ServiceW',0,7971,-3332,-3053,1),('ServiceE',0,8399,-3332,-3053,-1),
           ('LinkN',1,-1552,5465,5855,1),('LinkS',1,-1248,5465,5855,-1)]
    rng=random.Random(7318);rows=[]
    def put(key,axis,coord,side,h,z,width,height,material):
        pos=[coord,h,z] if axis==0 else [h,coord,z]
        yaw=(180 if side>0 else 0) if axis==0 else (-90 if side>0 else 90)
        rows.append(dict(label=key,kind='wall',texture=material,pos=pos,yaw=yaw,size=[2.7,width/2,height/2]))
    for name,axis,coord,lo,hi,side in spans:
        div=math.ceil((hi-lo)/430)
        for i in range(div):
            a=lo+(hi-lo)*i/div;b=lo+(hi-lo)*(i+1)/div;mid=(a+b)/2;width=(b-a)*rng.uniform(.72,.94)
            put(name+'Toe'+str(i),axis,coord,side,mid,rng.uniform(21,27),width,rng.uniform(45,53),'DustWall')
            if rng.random()<.52:
                h=rng.uniform(a+21,b-21)
                put(name+'Seep'+str(i),axis,coord,side,h,rng.uniform(97,108),rng.uniform(13,27),rng.uniform(70,96),'LeakSoft')
    return rows
def apply(w):
    floor=json.loads((ROOT/'floor-plan.json').read_text('utf8'));wall=ceramic()
    mats=instances(floor)
    for r in wall:
        if r['texture'] not in mats:
            mats[r['texture']]=u.load_asset(STOCK+r['texture'])
            if not mats[r['texture']]:raise RuntimeError('Wall coat unavailable '+r['texture'])
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    for r in floor+wall:
        is_floor=r['kind']=='floor'
        rot=u.Rotator(pitch=-90) if is_floor else u.Rotator(yaw=r['yaw'])
        label='StationSurface_'+r['label'];loc=u.Vector(*r['pos'])
        a=actors.get(label)
        if not a:
            a=api.spawn_actor_from_class(u.DecalActor,loc,rot);a.set_actor_label(label)
            a.set_folder_path('StationLine/StationSurface/'+('Ground' if is_floor else 'TileSkirts'))
        a.modify();a.set_actor_location_and_rotation(loc,rot,False,False)
        c=a.get_component_by_class(u.DecalComponent);c.modify();c.set_decal_material(mats[r['texture']])
        c.set_editor_property('decal_size',u.Vector(*r['size']));c.set_editor_property('sort_order',1)
        c.set_editor_property('fade_screen_size',.002 if is_floor else .003)
    return dict(floor_projections=len(floor),floor_finishes=len({r['texture'] for r in floor}),wall_foot_projections=len(wall))
