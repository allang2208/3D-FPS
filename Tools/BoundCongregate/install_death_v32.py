"""Save the cooked V32 corpse, then switch only the live mesh's death binding."""
from pathlib import Path
import json, shutil
import unreal as u
P=Path('D:/FPS3D/FPSGAME')
OUT=P/'SourceAssets/BoundCongregateMeshy20261006/DeathV32'
BASE='/Game/Monsters/BoundCongregate';DEST=BASE+'/DeathV32'
SOURCE=BASE+'/TentacleReachV29/SK_BoundCongregate_TentacleReachV29'
E=u.EditorAssetLibrary
report=dict(complete=False,saved=[],tested=False,rendered=False,quick_melee_contacts=1)
def record():(OUT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    report['saved'].append(a.get_path_name());record()
try:
    if not json.loads((OUT/'authoring.json').read_text(encoding='utf8')).get('complete'):
        raise RuntimeError('Finish anatomical field fitting before installing')
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve PIE')
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(p.startswith(DEST) or p==SOURCE for p in dirty):raise RuntimeError('Preserve unsaved monster assets')
    live=u.load_asset(SOURCE)
    cdo=u.get_default_object(u.load_asset(BASE+'/BP_BoundCongregate').generated_class())
    if cdo.get_editor_property('visual_mesh')!=live:raise RuntimeError('Live visual changed')
    corpse=u.load_asset(DEST+'/SK_BoundCongregate_CorpseV32')
    skeleton=u.load_asset(DEST+'/SKEL_BoundCongregate_CorpseV32')
    data=u.load_asset(DEST+'/DA_BoundCongregate_CorpseV32')
    if not data.get_editor_property('corpse_mesh'):
        if not u.M14SoftBodyData.build_corpse(corpse,skeleton,data,str(OUT/'cage.json'),str(OUT/'embedding.bin')):
            raise RuntimeError('Anatomical corpse binding failed')
    # Same V29 source surface and slots: reuse the existing PBR corpse graphs
    # which already reconstruct deformed surface normals and preserve wounds.
    previous=u.load_asset(BASE+'/TentacleReachV29/Corpse/SK_BoundCongregate_CorpseV29')
    prior={str(s.get_editor_property('imported_material_slot_name')):s.get_editor_property('material_interface') for s in previous.get_editor_property('materials')}
    slots=list(corpse.get_editor_property('materials'))
    for s in slots:
        key=str(s.get_editor_property('imported_material_slot_name'))
        if key not in prior:raise RuntimeError('Missing matching corpse material '+key)
        s.set_editor_property('material_interface',prior[key])
    corpse.set_editor_property('materials',slots)
    E.set_metadata_tag(corpse,'CorpseRevision','M88 V32 continuous anatomical XPBD')
    u.SystemLibrary.execute_console_command(None,'Editor.AsyncSkinnedAssetCompilationFinishAll')
    for a in (corpse,skeleton,data):save(a)
    source_file=P/'Content/Monsters/BoundCongregate/TentacleReachV29/SK_BoundCongregate_TentacleReachV29.uasset'
    backup=OUT/'before'/source_file.name;backup.parent.mkdir(exist_ok=True)
    if not backup.exists():shutil.copy2(source_file,backup)
    u.M14SoftBodyData.bind_to_living_mesh(live,data)
    E.set_metadata_tag(live,'CorpseRevision','M88 V32 continuous anatomical XPBD')
    save(live)
    report.update(complete=True,scheme='M14 V19 continuous XPBD with M88 anatomical cage',
        corpse=corpse.get_path_name(),data=data.get_path_name(),live_mesh=live.get_path_name(),
        fallback_clip=cdo.get_editor_property('death_clip').get_path_name(),
        retained='V29 live model / 30m whip, V25 garments, accepted V28 attacks, 300 tentacle HP',
        corpse_lod='0 only; no legacy skin-weight LODs',user_testing_pending=True)
    print('BOUND_DEATH_V32_SAVED',flush=True)
except Exception as e:report['error']=str(e);raise
finally:record()
