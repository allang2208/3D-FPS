"""Read and export the existing Fab earthwork sources for local fitting, no preview."""
from pathlib import Path
import json
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonRuinEarthwork20260921')
for folder in ('Sources','Authored','Receipts'): (ROOT/folder).mkdir(parents=True,exist_ok=True)
AA=u.get_editor_subsystem(u.EditorActorSubsystem)
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
L=u.MaterialEditingLibrary
paths={
 'ridge_a':'/Game/RuralAustralia/StaticMeshes/Rocks/Ridge_Dirt_01/SM_Ridge_Dirt_01_A_NoOverlay',
 'ridge_b':'/Game/RuralAustralia/StaticMeshes/Rocks/Ridge_Dirt_01/SM_Ridge_Dirt_01_B_NoOverlay',
 'dirt_wall':'/Game/MilitaryTrench/Assets/3D/Mil_Trench_Wall_Dirt_Straight_02/StaticMeshes/SM_Mil_Trench_Wall_Dirt_Straight_02',
 'gravel':'/Game/MilitaryTrench/Assets/3D/Ind_Con_Pile_Rubble_Gravel_Patch_01/StaticMeshes/SM_Ind_Con_Pile_Rubble_Gravel_Patch_01',
 'stone_scatter':'/Game/MilitaryTrench/Assets/3D/Mil_Trench_Debris_Pile_Rock_S/StaticMeshes/SM_Mil_Trench_Debris_Pile_Rock_S',
 'stone_patch':'/Game/MilitaryTrench/Assets/3D/Mil_Trench_Debris_Patch_Rock_S_01/StaticMeshes/SM_Mil_Trench_Debris_Patch_Rock_S_01',
 'rubble_a':'/Game/UnrealNormandy/StaticMeshes/SM_H_RubblePile_00A',
}
result={'source_assets':{},'materials':{},'editor_map':UE.get_editor_world().get_path_name(),
        'game_world_active':bool(UE.get_game_world()),'tests_run':False,'renders_run':False}
for ident,path in paths.items():
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Required source missing '+path)
    b=mesh.get_bounds()
    row={'path':path,'origin_cm':list(b.origin.to_tuple()),'extent_cm':list(b.box_extent.to_tuple()),'materials':[]}
    for slot in mesh.get_editor_property('static_materials'):
        mat=slot.material_interface
        row['materials'].append({'slot':str(slot.material_slot_name),'path':mat.get_path_name()})
        if mat.get_path_name() not in result['materials']:
            record={'class':mat.get_class().get_name()}
            if isinstance(mat,u.MaterialInstanceConstant):
                record['parent']=mat.parent.get_path_name()
                record['scalars']={str(n):L.get_material_instance_scalar_parameter_value(mat,n) for n in L.get_scalar_parameter_names(mat)}
                record['vectors']={str(n):list(L.get_material_instance_vector_parameter_value(mat,n).to_tuple()) for n in L.get_vector_parameter_names(mat)}
                record['textures']={}
                for n in L.get_texture_parameter_names(mat):
                    t=L.get_material_instance_texture_parameter_value(mat,n)
                    record['textures'][str(n)]=t.get_path_name() if t else None
            result['materials'][mat.get_path_name()]=record
    target=ROOT/'Sources'/(ident+'.fbx')
    task=u.AssetExportTask();task.object=mesh;task.filename=str(target);task.automated=True
    task.prompt=False;task.replace_identical=True;task.exporter=u.StaticMeshExporterFBX()
    opts=u.FbxExportOption();opts.ascii=False;opts.level_of_detail=False;opts.collision=False
    task.options=opts
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Source export failed '+ident)
    row['fbx']=str(target);result['source_assets'][ident]=row
actors={}
for a in AA.get_all_level_actors():
    label=a.get_actor_label()
    if label.startswith('DGN_Room_RU_') or label in ('DGN_AV2_Goddess_Candidate','DGN_Room_RU_WorkLampSource'):
        c=a.get_component_by_class(u.StaticMeshComponent)
        actors[label]={'location':list(a.get_actor_location().to_tuple()),'rotation':list(a.get_actor_rotation().to_tuple()),
          'scale':list(a.get_actor_scale3d().to_tuple()),'mesh':c.static_mesh.get_path_name() if c and c.static_mesh else None}
result['ruin_actors']=actors
(ROOT/'Sources/source-manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('EARTHWORK_SOURCES_EXPORTED',len(paths),result['editor_map'],'game_active',result['game_world_active'])
