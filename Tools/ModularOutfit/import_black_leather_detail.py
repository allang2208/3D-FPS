"""Save reference-detailed black gloves and update their existing equipment ID."""
import hashlib
import shutil
import sys
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME')
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
import import_tailored_fingerless_candidate as native
from original_leather_gloves import read,write

R=P/'SourceAssets/BlackLeatherDetail20260928'
DEST='/Game/Characters/ModularOutfit20260924/BlackLeatherDetail20260928'
ITEM='ue_field_gloves_black'
ICON='Icons/BlackLeatherDetail20260928/ue_field_gloves_black.png'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
native.S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)


def material(group):
    folder=DEST+'/Materials/'+group;E.make_directory(folder)
    textures={}
    for channel in ('BaseColor','ORM','Normal'):
        name='T_BlackLeather_'+group+'_'+channel
        task=u.AssetImportTask();task.filename=str(R/'Textures'/group/(name+'.png'))
        task.destination_path=folder;task.destination_name=name
        task.automated=True;task.replace_existing=True;task.save=False
        A.import_asset_tasks([task]);tex=native.load(folder+'/'+name)
        tex.set_editor_property('srgb',channel=='BaseColor')
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal'
                               else u.TextureCompressionSettings.TC_MASKS if channel=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
        if channel=='Normal':tex.set_editor_property('flip_green_channel',True)
        native.save(tex);textures[channel]=tex
    name='M_BlackLeatherDetail_'+group
    mat=u.load_asset(folder+'/'+name)
    if not mat:mat=A.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
    if not L.get_material_expressions(mat):
        mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
        L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_STATIC_MESH)
        for channel,tex in textures.items():
            node=L.create_material_expression(mat,u.MaterialExpressionTextureSampleParameter2D)
            node.set_editor_property('parameter_name',channel);node.set_editor_property('texture',tex)
            node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal'
                                    else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            outputs=[('RGB',u.MaterialProperty.MP_BASE_COLOR)] if channel=='BaseColor' else [('RGB',u.MaterialProperty.MP_NORMAL)] if channel=='Normal' else [
                ('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]
            for output,prop in outputs:
                if not L.connect_material_property(node,output,prop):raise RuntimeError('Cannot connect '+group+'/'+channel)
        spec=L.create_material_expression(mat,u.MaterialExpressionScalarParameter)
        spec.set_editor_property('parameter_name','LeatherSpecular');spec.set_editor_property('default_value',.38)
        L.connect_material_property(spec,'',u.MaterialProperty.MP_SPECULAR)
        L.layout_material_expressions(mat)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Black leather material compile failed: '+str(errors))
    native.save(mat)
    return mat


def pickup(mat):
    folder=DEST+'/Pickups';name='SM_BlackLeatherDetail_Pickup';E.make_directory(folder)
    task=u.AssetImportTask();task.filename=str(R/(name+'.fbx'));task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False
    opts=u.FbxImportUI();opts.import_as_skeletal=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opts.automated_import_should_detect_type=False;opts.import_materials=False;opts.import_textures=False
    opts.static_mesh_import_data.combine_meshes=True;opts.static_mesh_import_data.auto_generate_collision=True
    task.options=opts;A.import_asset_tasks([task]);mesh=native.load(folder+'/'+name)
    for i in range(len(mesh.get_editor_property('static_materials'))):mesh.set_material(i,mat)
    editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    options=u.StaticMeshReductionOptions();options.auto_compute_lod_screen_size=False
    options.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=p,screen_size=s) for p,s in ((1.,1.),(.5,.18),(.25,.075))]
    editor.set_lods(mesh,options);E.set_metadata_tag(mesh,'EquipmentDefinition',ITEM);native.save(mesh)
    return mesh


def publish(profiles,materials,world_mesh):
    cfgpath=P/'Content/ColdSteelData/modular_outfits.json';itempath=P/'Content/ColdSteelData/items.json'
    cfg=read(cfgpath);items=read(itempath)
    previous=read(R/'before-recipe.json')
    current=cfg['items'][ITEM]
    if current!=previous and current.get('appearance_family')!='BlackLeatherDetail20260928':
        raise RuntimeError('Black-glove recipe was changed during authoring; new assets saved without replacing parallel work')
    if not (R/'before-publication.json').exists():write(R/'before-publication.json',dict(item=items[ITEM],recipe=current))
    recipe=dict(current,material='',covers=[2],appearance_family='BlackLeatherDetail20260928',
                rig_meshes={name:receipt['mesh'] for name,receipt in profiles.items()})
    item=dict(items[ITEM]);item.update(ue_icon=ICON,world_mesh=world_mesh.get_path_name(),world_material=materials['M4'].get_path_name(),
        desc='黑色全指皮革手套，手背采用柔软分区护垫、双道缝线和织物束带；掌面补强，指侧细密走线，可与上衣独立搭配。')
    icon=P/'Content/ColdSteelData'/ICON;icon.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/(ITEM+'.png'),icon)
    cfg['items'][ITEM]=recipe;items[ITEM]=item
    write(cfgpath,cfg);write(itempath,items)
    write(R/'published.json',dict(item=ITEM,item_definition=item,recipe=recipe,profiles=profiles,
        materials={k:v.get_path_name() for k,v in materials.items()},pickup=world_mesh.get_path_name(),icon=str(icon),
        stats_changed=False,new_animations=0,runtime_tested=False,refresh='next game session'))
    print('BLACK_LEATHER_DETAIL_PUBLISHED',ITEM,len(profiles),flush=True)


def main():
    commandlet='-run=' in u.SystemLibrary.get_command_line().lower()
    subsystem=None if commandlet else u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if subsystem and subsystem.get_game_world():
        raise RuntimeError('Finish the current PIE session before saving glove geometry and LOD assets')
    read(R/'artwork.json')
    materials={name:material(name) for name in ('M4','Body')}
    profiles={}
    for row in read(R/'manifest.json'):
        name=row['profile'];raw=Path(row['authored']).read_bytes();sha=hashlib.sha256(raw).hexdigest()
        record=R/'Saved'/(name+'.json');old=read(record) if record.exists() else None
        if old and old.get('sha256')==sha and E.does_asset_exist(old['mesh']):profiles[name]=old;continue
        print('BLACK_LEATHER_DETAIL_IMPORT_BEGIN',name,flush=True)
        data=read(Path(row['authored']))
        mesh=native.build_mesh(data,'SK_'+name+'_BlackLeatherDetail',[materials[row['material_group']]],['DetailedBlackLeather'],DEST)
        E.set_metadata_tag(mesh,'EquipmentDefinition',ITEM);E.set_metadata_tag(mesh,'NativeSource',row['source']);native.save(mesh)
        receipt=dict(profile=name,mesh=mesh.get_path_name(),sha256=sha,source=row['source'],
                     material_group=row['material_group'],triangles=row['triangles'],lods=3)
        write(record,receipt);profiles[name]=receipt
        print('BLACK_LEATHER_DETAIL_SAVED',name,flush=True)
    world_mesh=pickup(materials['M4'])
    publish(profiles,materials,world_mesh)


if __name__=='__main__':main()
