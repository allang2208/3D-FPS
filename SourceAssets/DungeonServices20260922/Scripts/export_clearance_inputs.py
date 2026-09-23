"""Export the loaded meshes required by the user's ceiling/pipe inspection."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
snapshot=globals().get('SCENE_SNAPSHOT','scene-before.json');suffix=globals().get('EXPORT_SUFFIX','')
data=json.loads((ROOT/'Sources'/snapshot).read_text())
AA=u.get_editor_subsystem(u.EditorActorSubsystem)
actors={a.get_actor_label():a for a in AA.get_all_level_actors()}
rows=[]
for entry in data['actors']:
    label=entry['label']
    if not any(k in label for k in ('Ceiling','Fixture','Vault','ConcreteSupports','ServicePipes','CableTray','HangingCables')):continue
    actor=actors.get(label)
    if not actor:continue
    for c in actor.get_components_by_class(u.StaticMeshComponent):
        if not c.static_mesh:continue
        dest=ROOT/'Sources'/(label+suffix+'.fbx')
        task=u.AssetExportTask();task.object=c.static_mesh;task.filename=str(dest)
        task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.StaticMeshExporterFBX()
        task.options=u.FbxExportOption()
        task.options.set_editor_property('level_of_detail',False)
        task.options.set_editor_property('collision',False)
        if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed '+label)
        rows.append(dict(actor=label,fbx=str(dest),mesh=c.static_mesh.get_path_name()))
(ROOT/'Sources'/('clearance-inputs'+suffix+'.json')).write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('CLEARANCE_INPUTS_EXPORTED',len(rows))
