"""Export complete matching mannequin and clean locomotion for DCC authoring."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchFoundation20260920');OUT=ROOT/'Sources';OUT.mkdir(parents=True,exist_ok=True)
u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/Game/Characters/Mannequins'],True)
paths={'Quinn':'/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple','Walk':'/Game/Characters/Mannequins/Anims/Unarmed/Walk/MF_Unarmed_Walk_Fwd','Idle':'/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle'}
report={}
for role,path in paths.items():
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing motion source '+path)
    t=u.AssetExportTask();t.object=a;t.filename=str(OUT/(role+'.fbx'));t.automated=True;t.prompt=False;t.replace_identical=True
    t.exporter=u.SkeletalMeshExporterFBX() if role=='Quinn' else u.AnimSequenceExporterFBX()
    options=u.FbxExportOption();options.export_preview_mesh=False;t.options=options
    if not u.Exporter.run_asset_export_task(t):raise RuntimeError('Export failed '+role)
    item={'asset':path,'file':t.filename}
    if role!='Quinn':item.update({'duration':a.get_play_length(),'frames':u.AnimationLibrary.get_num_frames(a),'loop':True})
    report[role]=item
(ROOT/'source_motion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
