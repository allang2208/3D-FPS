import unreal, json
from pathlib import Path
out = Path(unreal.Paths.project_saved_dir()) / 'NurseZombie'
out.mkdir(parents=True, exist_ok=True)
base='/Game/ZombieFemale/Asset/'
mesh=unreal.load_asset(base+'Meshes/ZombieFemale_NurseOutfit')
report={'mesh':str(mesh), 'skeleton':str(mesh.get_editor_property('skeleton')), 'physics':str(mesh.get_editor_property('physics_asset')), 'bounds':str(mesh.get_bounds()),'animations':[]}
for name in ['ANMS_ZombieFemaleIdle05','ANMS_ZombieFemaleWalk01Forward','ANMS_ZombieFemaleAttackForward05']:
    a=unreal.load_asset(base+'Animations/'+name)
    item={'name':name,'class':a.get_class().get_name(),'length':a.get_play_length(),'skeleton':str(a.get_editor_property('skeleton'))}
    if isinstance(a,unreal.AnimMontage):
        item['slots']=str(a.get_editor_property('slot_anim_tracks'))
    report['animations'].append(item)
    item['frames']=unreal.AnimationLibrary.get_num_frames(a)
    a.set_preview_skeletal_mesh(mesh)
    task=unreal.AssetExportTask()
    task.object=a
    task.filename=str(out/(name+'.fbx'))
    task.automated=True
    task.prompt=False
    task.options=unreal.FbxExportOption()
    task.options.set_editor_property('export_preview_mesh',True)
    task.exporter=unreal.AnimSequenceExporterFBX()
    unreal.Exporter.run_asset_export_task(task)
(out/'source-inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('NURSE_INSPECT_OK '+json.dumps(report))
