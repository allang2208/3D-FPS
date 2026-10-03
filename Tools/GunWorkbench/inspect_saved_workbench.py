"""User-requested, read-only comparison of saved workbench definitions and meshes."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/GunWorkbenchVisibleFix20260928');ROOT.mkdir(parents=True,exist_ok=True)
def path(obj):return obj.get_path_name() if obj else None
palette=u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
result={'project':u.Paths.project_dir(),'palette':path(palette),'entries':[],'meshes':{}}
for i,e in enumerate(palette.get_editor_property('components')):
    identity=str(e.get_editor_property('id'))
    if 'workbench' not in identity:continue
    result['entries'].append({'index':i,'id':identity,'name':str(e.get_editor_property('display_name')),
        'mesh':path(e.get_editor_property('mesh')),'actor_class':str(e.get_editor_property('actor_class')),
        'surface':path(e.get_editor_property('surface'))})
versions=['GunWorkbench20260927','GunWorkbench20260928','GunWorkbenchPolish20260928',
          'GunWorkbenchLampRestore20260928','GunWorkbenchCleared20260928','GunWorkbenchLibraryTools20260928']
for version in versions:
    mesh=u.load_asset('/Game/Building/'+version+'/SM_GunWorkbench')
    if not mesh:continue
    result['meshes'][version]={'path':path(mesh),'render_triangles':mesh.get_num_triangles(0),
        'render_vertices':mesh.get_num_vertices(0),'sections':mesh.get_num_sections(0),
        'bounds':str(mesh.get_bounding_box()),'import_source':list(mesh.get_editor_property('asset_import_data').extract_filenames()),
        'materials':[{'slot':str(s.material_slot_name),'asset':path(s.material_interface)} for s in mesh.get_editor_property('static_materials')]}
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem);game=editor.get_game_world()
result['pie_active']=bool(game);result['instances']=[]
for world in [game,editor.get_editor_world()]:
    if not world:continue
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.VoxelBuildPrefabActor):
        for comp in actor.get_components_by_class(u.StaticMeshComponent):
            mesh=comp.static_mesh
            if mesh and ('GunWorkbench' in path(mesh) or 'WBStandalone_Workbench' in path(mesh)):
                result['instances'].append({'actor':path(actor),'mesh':path(mesh),'transform':str(comp.get_world_transform())})
(ROOT/'saved-assets.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('WORKBENCH_SAVED_STATE '+json.dumps({'entries':result['entries'],'versions':{k:{p:v[p] for p in ['render_triangles','render_vertices','sections','import_source']} for k,v in result['meshes'].items()}},ensure_ascii=False))
