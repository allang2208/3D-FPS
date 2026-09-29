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

R=P/'SourceAssets/BlackLeatherDetail20260928/StitchWearV4'
DEST='/Game/Characters/ModularOutfit20260924/BlackLeatherStitchWearV4'
ITEM='ue_field_gloves_black'
ICON='Icons/BlackLeatherStitchWearV4/ue_field_gloves_black.png'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
native.S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)


def material(group):
    from black_leather_relief_material import build
    return build(group,R,DEST,native.save,native.load,P/'Tools/ModularOutfit/black_leather_relief.ush')


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
    if current!=previous and current.get('appearance_family')!='BlackLeatherStitchWearV4':
        raise RuntimeError('Black-glove recipe was changed during authoring; new assets saved without replacing parallel work')
    if not (R/'before-publication.json').exists():write(R/'before-publication.json',dict(item=items[ITEM],recipe=current))
    recipe=dict(current,material='',covers=[2],appearance_family='BlackLeatherStitchWearV4',
                rig_meshes={name:receipt['mesh'] for name,receipt in profiles.items()})
    item=dict(items[ITEM]);item.update(ue_icon=ICON,world_mesh=world_mesh.get_path_name(),world_material=materials['M4'].get_path_name(),
        desc='黑色全指皮革手套，细粒皮革拼接短绒织物，裁片采用带压痕的细密嵌线，接缝与抓握处留有轻微摩擦痕迹；腕口为背厚内薄的柔软回折包边。')
    icon=P/'Content/ColdSteelData'/ICON;icon.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/(ITEM+'.png'),icon)
    cfg['items'][ITEM]=recipe;items[ITEM]=item
    write(cfgpath,cfg);write(itempath,items)
    write(R/'published.json',dict(item=ITEM,item_definition=item,recipe=recipe,profiles=profiles,
        materials={k:v.get_path_name() for k,v in materials.items()},pickup=world_mesh.get_path_name(),icon=str(icon),
        stats_changed=False,new_animations=0,runtime_tested=False,refresh='next game session'))
    print('BLACK_LEATHER_DETAIL_PUBLISHED',ITEM,len(profiles),flush=True)


def main(names=None,publish_result=True,import_materials=True):
    commandlet='-run=' in u.SystemLibrary.get_command_line().lower()
    subsystem=None if commandlet else u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if subsystem and subsystem.get_game_world():
        raise RuntimeError('Finish the current PIE session before saving glove geometry and LOD assets')
    read(R/'artwork.json')
    materials={name:material(name) if import_materials else native.load(DEST+'/Materials/'+name+'/M_BlackLeatherReliefCuff_'+name) for name in ('M4','Body')}
    profiles={}
    manifest=read(R/'manifest.json')
    for row in manifest:
        if names is not None and row['profile'] not in names:continue
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
    if not publish_result:
        print('BLACK_LEATHER_V4_BATCH_SAVED',list(profiles),flush=True)
        return
    for row in manifest:
        name=row['profile']
        if name in profiles:continue
        receipt=read(R/'Saved'/(name+'.json'))
        if receipt['sha256']!=hashlib.sha256(Path(row['authored']).read_bytes()).hexdigest():
            raise RuntimeError('The saved native mesh needs its current authoring revision: '+name)
        profiles[name]=receipt
    world_mesh=pickup(materials['M4'])
    publish(profiles,materials,world_mesh)


if __name__=='__main__':main()
