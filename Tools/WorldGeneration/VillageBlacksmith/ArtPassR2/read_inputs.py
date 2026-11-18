"""Read the nine shipped meshes and village reference bindings; export local review inputs."""
import json,shutil
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/ArtPassR2'
(OUT/'Inputs').mkdir(parents=True,exist_ok=True)
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
S=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
names=['OakTable','OakShelf','TimberBed','OakStool','IronStock','AbandonedTimber','HearthPad','BlacksmithSign','ClosedPlaque']
meshes=['/Game/WorldGeneration/TemperateHills/VillageBlacksmith/Meshes/SM_Village'+n for n in names]
meshes+=['/Game/UnrealNormandy/StaticMeshes/SM_H_OldWall_00A',
         '/Game/WorldGeneration/TemperateHills/OldChapel/Meshes/SM_ChapelPew',
         '/Game/WorldGeneration/TemperateHills/OldChapel/Meshes/SM_ChapelYardWallA',
         '/Game/Props/CastingStation20260926/SM_CastingStation']
report={'meshes':{},'textures':{}}
texture_paths=set()
def xyz(v):return [v.x,v.y,v.z]
for path in meshes:
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError(path)
    b=mesh.get_bounding_box()
    row=dict(min=xyz(b.min),max=xyz(b.max),lod_count=S.get_lod_count(mesh),
             collision_count=S.get_simple_collision_count(mesh),slots=[])
    for slot in mesh.get_editor_property('static_materials'):
        mat=slot.material_interface
        item=dict(slot=str(slot.material_slot_name),material=mat.get_path_name() if mat else None,textures=[])
        if mat:
            for n in L.get_material_expressions(mat.get_base_material()):
                if not isinstance(n,u.MaterialExpressionTextureSample):continue
                tex=n.get_editor_property('texture')
                if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and isinstance(mat,u.MaterialInstanceConstant):
                    tex=L.get_material_instance_texture_parameter_value(mat,n.get_editor_property('parameter_name')) or tex
                if isinstance(tex,u.Texture2D):item['textures'].append(tex.get_path_name());texture_paths.add(tex.get_path_name())
        row['slots'].append(item)
    report['meshes'][path]=row
    if 'VillageBlacksmith' in path:
        rel=Path(path.replace('/Game/','Content/')+'.uasset');backup=OUT/'Before'/rel
        backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():shutil.copy2(ROOT/rel,backup)
        task=u.AssetExportTask();task.object=mesh;task.filename=str(OUT/'Inputs'/(mesh.get_name()+'.fbx'))
        task.exporter=u.StaticMeshExporterFBX();task.automated=True;task.prompt=False;task.replace_identical=True
        if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Mesh export '+path)
for path in sorted(texture_paths):
    # Reference texture export for local review only; licensed project sources stay in the project.
    tex=u.load_asset(path);target=OUT/'Inputs'/(tex.get_name()+'.png')
    task=u.AssetExportTask();task.object=tex;task.filename=str(target)
    task.exporter=u.TextureExporterPNG();task.automated=True;task.prompt=False;task.replace_identical=True
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Texture export '+path)
    report['textures'][path]=dict(file=str(target),srgb=tex.get_editor_property('srgb'),
        compression=str(tex.get_editor_property('compression_settings')),
        size=[tex.blueprint_get_size_x(),tex.blueprint_get_size_y()])
(OUT/'inputs.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('VILLAGE_ART_INPUTS_EXPORTED '+str(len(report['meshes'])))
