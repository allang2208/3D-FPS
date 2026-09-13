"""Export original EBS tool animation inputs without editing their assets."""
import json
from pathlib import Path
import unreal

ROOT=Path(unreal.Paths.project_dir())
OUT=ROOT/'SourceAssets/InfectedMiner20260913/Reference'
OUT.mkdir(parents=True,exist_ok=True)
lib=unreal.EditorAssetLibrary
base='/Game/EasyBuildingSystem/Mannequin'
mesh=unreal.load_asset(base+'/Mesh/SK_Mannequin')
rows=[]

def export(asset,name,animation=False):
    task=unreal.AssetExportTask()
    task.object=asset
    task.filename=str(OUT/(name+'.fbx'))
    task.automated=True
    task.prompt=False
    task.options=unreal.FbxExportOption()
    task.options.set_editor_property('export_preview_mesh',animation)
    task.exporter=unreal.AnimSequenceExporterFBX() if animation else unreal.SkeletalMeshExporterFBX()
    if not unreal.Exporter.run_asset_export_task(task):
        raise RuntimeError('Export failed: '+name)

export(mesh,'EBS_Mannequin')
for name in ['A_Mannequin_Axe_Act','A_Mannequin_Axe_Idle','A_Mannequin_Axe_Walk','A_Mannequin_PickAxe_Act']:
    asset=unreal.load_asset(base+'/Animations/'+name)
    export(asset,name,True)
    rows.append({'name':name,'source':asset.get_path_name(),'seconds':asset.get_play_length(),
                 'frames':unreal.AnimationLibrary.get_num_frames(asset),'skeleton':asset.get_editor_property('skeleton').get_path_name()})
(OUT/'default-tools.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
unreal.log('MINER_DEFAULT_TOOLS_EXPORTED '+json.dumps(rows))
