"""Read the newly imported source pack and export review copies only.

Does not retarget, edit, save or bind any Unreal asset.
"""
import unreal as u
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'SourceFBX';OUT.mkdir(exist_ok=True)
PACK='/Game/ZombieAnimationPack'
mesh=u.load_asset(PACK+'/Demo/EpicContent/Mannequin_UE5/Meshes/SK_Manny_Simple')
if mesh is None:raise RuntimeError('Source mannequin not found')
paths=u.EditorAssetLibrary.list_assets(PACK+'/Animations',True,False)
inventory=[];selected=[]
for path in sorted(paths):
    clip=u.load_asset(path)
    if not isinstance(clip,u.AnimSequence):continue
    row={'name':clip.get_name(),'asset':clip.get_path_name(),'seconds':clip.get_play_length(),
         'skeleton':clip.get_editor_property('skeleton').get_path_name(),
         'additive':str(clip.get_editor_property('additive_anim_type')),
         'root_motion':bool(clip.get_editor_property('enable_root_motion')),
         'force_root_lock':bool(clip.get_editor_property('force_root_lock'))}
    inventory.append(row)
    if '/Mannequin_UE5/' in path and any(clip.get_name().startswith('anim_'+p) for p in ['Walk_','Run_','Attack_','Idle_','Burst_']):
        selected.append((clip,row))
(ROOT/'inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf-8')

def export(asset,mesh_export=False):
    path=OUT/(asset.get_name()+'.fbx')
    task=u.AssetExportTask();task.object=asset;task.filename=str(path)
    task.automated=True;task.prompt=False;task.replace_identical=True
    task.exporter=u.SkeletalMeshExporterFBX() if mesh_export else u.AnimSequenceExporterFBX()
    options=u.FbxExportOption();options.ascii=False;options.level_of_detail=False;options.collision=False
    options.export_preview_mesh=False;task.options=options
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed: '+asset.get_path_name())
    return str(path)

mesh_file=export(mesh,True)
for clip,row in selected:
    row['fbx']=export(clip)
    u.log('ZOMBIE_REVIEW_EXPORTED '+clip.get_name())
report={'pack':PACK,'mesh':mesh.get_path_name(),'mesh_fbx':mesh_file,
        'source_assets_changed':False,'formal_spitter_assets_changed':False,
        'total_sequences':len(inventory),'selected':[r for _,r in selected]}
(ROOT/'export_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('ZOMBIE_REVIEW_EXPORT_COMPLETE '+str(len(selected)))
