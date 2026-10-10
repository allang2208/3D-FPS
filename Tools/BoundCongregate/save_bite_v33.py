"""Save absolute M-88 bite tuning; retain live mesh, attacks and death binding."""
from pathlib import Path
import unreal as u, json, shutil
P=Path('D:/FPS3D/FPSGAME');OUT=P/'SourceAssets/BoundCongregateMeshy20261006/BiteV33'
PATH='/Game/Monsters/BoundCongregate/BP_BoundCongregate'
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active PIE')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if PATH in dirty:raise RuntimeError('Preserve unsaved monster Blueprint')
bp=u.load_asset(PATH);cdo=u.get_default_object(bp.generated_class())
before=json.loads((OUT/'before-pose.json').read_text(encoding='utf8'))
values=dict(bite_trigger_range=350.,bite_reach=235.,bite_contact_seconds=.56)
for key,value in values.items():
    current=float(cdo.get_editor_property(key))
    if min(abs(current-before['tuning'][key]),abs(current-value))>.001:raise RuntimeError('Concurrent tuning change: '+key)
if cdo.get_editor_property('bite_clip').get_path_name()!=before['clip']:raise RuntimeError('Bite animation changed')
source=P/'Content/Monsters/BoundCongregate/BP_BoundCongregate.uasset'
backup=OUT/'before'/source.name;backup.parent.mkdir(exist_ok=True)
if not backup.exists():shutil.copy2(source,backup)
for key,value in values.items():cdo.set_editor_property(key,value)
u.EditorAssetLibrary.set_metadata_tag(bp,'BiteRevision','M88 V33 235cm mouth reach, 0.54-0.65s contact window')
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not u.EditorAssetLibrary.save_loaded_asset(bp,False):raise RuntimeError('Blueprint save failed')
report=dict(saved=True,blueprint=PATH,values=values,contact_window_seconds=[.54,.65],
    mouth_reach_before_cm=before['tuning']['bite_reach'],
    retained={key:cdo.get_editor_property(key).get_path_name() for key in ('visual_mesh','bite_clip','flurry_clip','death_clip')},
    gameplay_tested=False,rendered=False)
(OUT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('BOUND_BITE_V33_SAVED '+json.dumps(values),flush=True)
