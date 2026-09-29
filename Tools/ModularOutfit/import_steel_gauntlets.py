"""Save full native steel gauntlets, then register their independent item."""
import hashlib
import shutil
import sys
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from original_leather_gloves import read,write
import import_tailored_fingerless_candidate as native
import install_steel_metal_liner as metal_liner

R=P/'SourceAssets/MetalGauntlet20260927/SteelGauntletV1'
DEST='/Game/Characters/ModularOutfit20260924/SteelGauntletV1'
ITEM='ue_steel_gauntlets'
ICON='Icons/MetalGauntlet20260927/ue_steel_gauntlets.png'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary


def material():
    folder=DEST+'/Materials';E.make_directory(folder);textures={}
    for label in ('BaseColor','ORM','Normal'):
        name='T_SteelGauntlet_'+label
        task=u.AssetImportTask();task.filename=str(R/'Textures'/(name+'.png'))
        task.destination_path=folder;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False
        A.import_asset_tasks([task]);tex=native.load(folder+'/'+name)
        tex.set_editor_property('srgb',label=='BaseColor')
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if label=='Normal' else u.TextureCompressionSettings.TC_MASKS if label=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
        if label=='Normal':tex.set_editor_property('flip_green_channel',True)
        native.save(tex);textures[label]=tex
    mat=u.load_asset(folder+'/M_SteelGauntlet')
    if not mat:mat=A.create_asset('M_SteelGauntlet',folder,u.Material,u.MaterialFactoryNew())
    for expr in list(L.get_material_expressions(mat)):L.delete_material_expression(mat,expr)
    L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_STATIC_MESH)
    for label in textures:
        node=L.create_material_expression(mat,u.MaterialExpressionTextureSampleParameter2D)
        node.set_editor_property('parameter_name',label);node.set_editor_property('texture',textures[label])
        node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if label=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if label=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        outputs=[('RGB',u.MaterialProperty.MP_BASE_COLOR)] if label=='BaseColor' else [('RGB',u.MaterialProperty.MP_NORMAL)] if label=='Normal' else [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]
        for channel,prop in outputs:
            if not L.connect_material_property(node,channel,prop):raise RuntimeError('Steel material connection failed '+label)
    L.layout_material_expressions(mat)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Steel material build failed '+str(errors))
    native.save(mat)
    return mat


def pickup(liner,steel):
    folder=DEST+'/Pickups';name='SM_SteelGauntlet_Pickup';E.make_directory(folder)
    task=u.AssetImportTask();task.filename=str(R/(name+'.fbx'));task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False
    opts=u.FbxImportUI();opts.import_as_skeletal=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opts.automated_import_should_detect_type=False;opts.import_materials=False;opts.import_textures=False
    opts.static_mesh_import_data.combine_meshes=True;opts.static_mesh_import_data.auto_generate_collision=True
    task.options=opts;A.import_asset_tasks([task]);mesh=native.load(folder+'/'+name)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        mesh.set_material(i,steel if 'SteelGauntlet' in str(slot.material_slot_name) else liner)
    editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    options=u.StaticMeshReductionOptions();options.auto_compute_lod_screen_size=False;settings=[]
    for percent,screen in ((1.,1.),(.5,.18),(.25,.075)):
        value=u.StaticMeshReductionSettings();value.percent_triangles=percent;value.screen_size=screen;settings.append(value)
    options.reduction_settings=settings;editor.set_lods(mesh,options);native.save(mesh)
    return mesh


def publish(receipt):
    cfgpath=P/'Content/ColdSteelData/modular_outfits.json';itempath=P/'Content/ColdSteelData/items.json'
    cfg=read(cfgpath);items=read(itempath)
    if set(cfg['items']['ue_original_gloves']['rig_meshes'])!=set(receipt['profiles']):
        raise RuntimeError('The active native profile set changed; preserve saved assets before publishing')
    before=R/'before-publication.json'
    if not before.exists():write(before,dict(item=items.get(ITEM),recipe=cfg['items'].get(ITEM)))
    recipe=dict(slot=3,part='gloves',material='',covers=[2],appearance_family='SteelGauntletV1',
                rig_meshes={name:row['mesh'] for name,row in receipt['profiles'].items()})
    item=dict(items.get(ITEM,items['ue_original_gloves']))
    item.update(id=ITEM,name='钢甲护手',type='手套',category='equipment',equipSlot='gloves',
        desc=metal_liner.DESCRIPTION,
        ue_icon=ICON,icon_fallback='甲',world_mesh=receipt['pickup'],world_material='')
    icon=P/'Content/ColdSteelData'/ICON;icon.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(R/'ue_steel_gauntlets.png',icon)
    cfg['items'][ITEM]=recipe;items[ITEM]=item
    write(cfgpath,cfg);write(itempath,items)
    write(R/'published.json',dict(receipt,item=ITEM,item_definition=item,recipe=recipe,icon=str(icon),
        refresh='next game session',runtime_tested=False))
    print('STEEL_GAUNTLETS_PUBLISHED',ITEM,len(receipt['profiles']),flush=True)


def main():
    editor_world=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor_world and editor_world.get_game_world():
        raise RuntimeError('Finish the current PIE session before importing steel gauntlets; asset authoring APIs reject play mode')
    read(R/'artwork.json')
    entries=read(R/'manifest.json');steel=material()
    grey_metal=metal_liner.material()
    liners={group:grey_metal for group in ('M4','Body')}
    profiles={}
    for row in entries:
        name=row['profile'];raw=Path(row['authored']).read_bytes();sha=hashlib.sha256(raw).hexdigest()
        record=R/'Saved'/(name+'.json');old=read(record) if record.exists() else None
        if old and old.get('sha256')==sha and E.does_asset_exist(old['mesh']):
            metal_liner.bind_skeletal(native.load(old['mesh']),grey_metal)
            profiles[name]=old;continue
        d=read(Path(row['authored']))
        mesh=native.build_mesh(d,'SK_'+name+'_SteelGauntletV1',[liners[row['liner_material_group']],steel],['LeatherLiner','ArticulatedSteel'],DEST)
        E.set_metadata_tag(mesh,'EquipmentDefinition',ITEM);E.set_metadata_tag(mesh,'NativeSource',row['native_source']);native.save(mesh)
        profiles[name]=dict(mesh=mesh.get_path_name(),sha256=sha,lods=3,triangles=row['triangles'],sides=row['sides'])
        write(record,profiles[name]);print('STEEL_GAUNTLET_PROFILE_SAVED',name,flush=True)
    prop=pickup(liners['M4'],steel)
    receipt=dict(profiles=profiles,steel_material=steel.get_path_name(),liner_materials={k:v.get_path_name() for k,v in liners.items()},
        pickup=prop.get_path_name(),new_animations=0,runtime_tested=False)
    write(R/'saved-assets.json',receipt);publish(receipt)


if __name__=='__main__':main()
