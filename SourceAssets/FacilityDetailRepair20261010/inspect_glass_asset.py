from pathlib import Path
import json,unreal as u
ROOT=Path(__file__).resolve().parent
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
system=u.load_asset('/Game/NiagaraExamples/FX_Weapons/Impacts/NS_Impact_Glass')
report=dict(playing=bool(ed.get_game_world()),world=ed.get_editor_world().get_path_name(),
    dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
    system=system.get_path_name(),methods=[n for n in dir(system) if 'emitter' in n.lower()])
t=u.AssetExportTask();t.object=system;t.filename=str(ROOT/'Receipts/glass-system.t3d');t.automated=True;t.prompt=False
t.exporter=u.ObjectExporterT3D();report['exported']=u.Exporter.run_asset_export_task(t)
(ROOT/'Receipts/glass-source.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
