"""Read bone poses needed for recovery alignment and per-body motion fitting."""
import unreal as u, json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HumanoidKnockdown20260926')
assets=json.loads((ROOT/'imported_animations.json').read_text())
report={}
for role,data in assets.items():
    pelvis='Hips' if role in ['FatZombie','Mutant3'] else 'pelvis'
    bones=[pelvis,'Head' if pelvis=='Hips' else 'head',
           'LeftHand' if pelvis=='Hips' else 'hand_l','RightHand' if pelvis=='Hips' else 'hand_r',
           'LeftFoot' if pelvis=='Hips' else 'foot_l','RightFoot' if pelvis=='Hips' else 'foot_r']
    report[role]={}
    for info in data['clips']:
        a=u.load_asset(info['asset'])
        samples=[]
        for time in [0,a.get_play_length()*.5,a.get_play_length()]:
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(a,time,u.AnimPoseEvaluationOptions())
            sample={}
            for bone in bones:
                tr=u.AnimPoseExtensions.get_bone_pose(pose,bone,u.AnimPoseSpaces.WORLD)
                v=tr.translation;sample[bone]=[v.x,v.y,v.z]
            samples.append(sample)
        report[role][a.get_name()]=samples
        export=u.AssetExportTask();export.object=a
        export.filename=str(ROOT/(a.get_name()+'_raw.fbx'))
        export.automated=True;export.prompt=False;export.replace_identical=True
        export.exporter=u.AnimSequenceExporterFBX()
        opts=u.FbxExportOption();opts.set_editor_property('export_preview_mesh',True);export.options=opts
        if not u.Exporter.run_asset_export_task(export):raise RuntimeError('Export failed '+a.get_name())
(ROOT/'retarget_poses.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
