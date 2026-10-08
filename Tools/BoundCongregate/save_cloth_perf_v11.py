"""Keep the fitted V10 garments and contacts; remove convex CCD overhead."""
from pathlib import Path
import hashlib
import json
import shutil
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
OUT=PROJECT/'SourceAssets/BoundCongregateMeshy20261006/ClothPerfV11'
PATH='/Game/Monsters/BoundCongregate/FullWhipV10/SK_BoundCongregate_FullWhipV10'
FILE=PROJECT/'Content/Monsters/BoundCongregate/FullWhipV10/SK_BoundCongregate_FullWhipV10.uasset'
report={'revision':'ClothPerfV11','saved':False,'gameplay_tested':False,'mesh':PATH,'cloth':[]}

try:
    OUT.mkdir(parents=True,exist_ok=True)
    backup=OUT/'before'/FILE.name
    backup.parent.mkdir(exist_ok=True)
    if not backup.exists():shutil.copy2(FILE,backup)
    report['backup']=str(backup)
    report['before_sha256']=hashlib.sha256(backup.read_bytes()).hexdigest()
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if PATH in dirty:raise RuntimeError('Preserve unsaved monster mesh')
    u.SystemLibrary.execute_console_command(None,'Editor.AsyncSkinnedAssetCompilation 0')
    bp=u.load_asset('/Game/Monsters/BoundCongregate/BP_BoundCongregate')
    mesh=u.get_default_object(bp.generated_class()).get_editor_property('visual_mesh')
    if mesh.get_path_name()!=PATH+'.SK_BoundCongregate_FullWhipV10':
        raise RuntimeError('Active monster mesh changed; preserve it')
    mesh.modify()
    for cloth in mesh.get_editor_property('mesh_clothing_assets'):
        configs=cloth.get_editor_property('cloth_configs')
        for config in configs.values():
            if config.get_class().get_name()!='ChaosClothConfig':continue
            previous=config.get_editor_property('bUseCCD')
            config.modify();config.set_editor_property('bUseCCD',False)
            report['cloth'].append({'asset':cloth.get_name(),'previous_ccd':previous,'ccd':False})
    if len(report['cloth'])!=4:raise RuntimeError('Expected four existing fitted garments')
    u.EditorAssetLibrary.set_metadata_tag(mesh,'ClothCollisionRevision','V11-discrete-convex-with-backstop')
    if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Mesh save failed')
    report.update(saved=True,after_sha256=hashlib.sha256(FILE.read_bytes()).hexdigest())
    print('BOUND_CONGREGATE_CLOTH_PERF_V11_SAVED',flush=True)
finally:
    (OUT/'delivery.json').write_text(json.dumps(report,indent=2),encoding='utf8')
