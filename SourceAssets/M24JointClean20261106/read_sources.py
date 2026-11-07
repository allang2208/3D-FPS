from pathlib import Path
import unreal as u,json,hashlib
O=Path(__file__).resolve().parent
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
targets={};sources={}
for kind in ('Native','Advanced'):
    for family,folder,name in [('target','CarbonSpine20261104','SM_M24_CarbonSpine_'),('source','ReceiverGripRebuild20261031','SM_M24_ReceiverStock_')]:
        p='/Game/Weapons/M24/'+folder+'/Meshes/'+name+kind
        if p in dirty:raise RuntimeError('Unsaved asset retained '+p)
        a=u.load_asset(p);f=Path(u.Paths.project_content_dir())/(p[6:]+'.uasset')
        row={'path':p,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in a.static_materials}}
        (targets if family=='target' else sources)[kind.lower()]=row
        if family=='source':
            t=u.AssetExportTask();t.object=a;t.filename=str(O/'Inputs'/(kind+'.fbx'));t.exporter=u.StaticMeshExporterFBX();t.options=u.FbxExportOption();t.options.level_of_detail=False;t.options.collision=False;t.automated=True;t.prompt=False;t.replace_identical=True
            if not u.Exporter.run_asset_export_task(t):raise RuntimeError('Source export '+kind)
(O/'current.json').write_text(json.dumps(targets,indent=2))
(O/'sources.json').write_text(json.dumps(sources,indent=2))
pie=u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor() if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() else False
print('M24_JOINT_SOURCES',list(sources),'PIE',pie)
