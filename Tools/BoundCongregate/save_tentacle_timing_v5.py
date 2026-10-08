"""Persist only the requested 3x release duration on the existing F6 monster."""
from pathlib import Path
import unreal as u,json

OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/TentacleTimingV5')
OUT.mkdir(parents=True,exist_ok=True)
BP='/Game/Monsters/BoundCongregate/BP_BoundCongregate'
report={'revision':'TentacleTimingV5','saved':False,'gameplay_tested':False}
try:
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if BP in dirty:raise RuntimeError('Preserve unsaved BoundCongregate blueprint')
    bp=u.load_asset(BP)
    if not bp:raise RuntimeError('Missing BoundCongregate blueprint')
    cdo=u.get_default_object(bp.generated_class())
    report['previous_strike_seconds']=cdo.get_editor_property('tentacle_strike_seconds')
    cdo.set_editor_property('tentacle_strike_seconds',.62/3.)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    if not u.EditorAssetLibrary.save_loaded_asset(bp,False):raise RuntimeError('Blueprint save failed')
    report.update(saved=True,blueprint=BP,strike_seconds=.62/3.,release_curve='segmented Hermite: .00/.00, .14/.06, .80/.94, 1.00/1.00',windup_seconds=cdo.get_editor_property('tentacle_windup_seconds'),wrap_seconds=cdo.get_editor_property('tentacle_wrap_seconds'),recover_seconds=cdo.get_editor_property('tentacle_recover_seconds'))
    print('BOUND_CONGREGATE_TIMING_V5_SAVED',flush=True)
except Exception as error:
    report['error']=str(error)
    raise
finally:
    (OUT/'delivery.json').write_text(json.dumps(report,indent=2),encoding='utf8')
