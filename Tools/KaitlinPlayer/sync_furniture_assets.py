"""Retarget a bounded batch of changed furniture clips into owned new packages."""
import hashlib
import json
from pathlib import Path
import unreal as u

if 'FURNITURE_WORK' not in globals():
    raise RuntimeError('The initial furniture batch is retired; use complete_furniture_assets or an explicit new revision.')
P=Path('D:/FPS3D/FPSGAME'); W=Path(globals().get('FURNITURE_WORK',P/'SourceAssets/KaitlinFurniture20261024'))
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
catalog=read(W/'source_catalog.json')
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.EditorLevelLibrary.get_pie_worlds(False):
    raise RuntimeError('Keep the active game intact; finish PIE before saving animation assets.')
source=u.load_asset(catalog['body_mesh']); target=u.load_asset(catalog['target_mesh'])
rtg=u.load_asset('/Game/Characters/KaitlinPlayer20261023/Motion/Rig/RTG_Jason_Kaitlin.RTG_Jason_Kaitlin')
if not source or not target or not rtg: raise RuntimeError('Native retarget inputs unavailable.')
E=u.EditorAssetLibrary
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
saved_path=W/'saved_assets.json'; saved=read(saved_path) if saved_path.exists() else {}
dest=globals().get('FURNITURE_DEST','/Game/Characters/KaitlinPlayer20261023/FurnitureSync20261024')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
def finish(): u.SystemLibrary.execute_console_command(world,'Editor.AsyncAssetCompilationFinishAll')
count=0
for role in catalog['stale_roles']:
    if role in saved: continue
    path=catalog['clips'][role]; package=path.split('.')[0]
    source_file=P/'Content'/(package[6:]+'.uasset')
    digest=hashlib.sha256(source_file.read_bytes()).hexdigest()
    if digest!=catalog['source_sha256'][role] or package in dirty:
        raise RuntimeError('Furniture source changed or has unsaved edits: '+role)
    clip=u.load_asset(path)
    if clip.get_editor_property('skeleton')!=source.skeleton: raise RuntimeError('Unexpected source skeleton: '+role)
    prefix='KF_'+digest[:8]+'_'
    output_name=prefix+clip.get_name()
    if E.does_asset_exist(dest+'/'+output_name): raise RuntimeError('Preserve unreceipted target '+output_name)
    inputs=u.IKRetargetBatchOperationInputs()
    inputs.assets_to_retarget=[E.find_asset_data(path)]
    inputs.source_mesh=source; inputs.target_mesh=target; inputs.ik_retarget_asset=rtg
    inputs.prefix=prefix; inputs.target_path=dest
    inputs.include_referenced_assets=False; inputs.overwrite_existing_files=False
    results=u.IKRetargetBatchOperation.run_batch_retarget(inputs); finish()
    outputs=[v.get_asset() for v in results if str(v.asset_class_path.asset_name)=='AnimSequence']
    if len(outputs)!=1: raise RuntimeError('Retarget did not produce one sequence: '+role)
    asset=outputs[0]
    for key in ('enable_root_motion','force_root_lock','root_motion_root_lock','rate_scale'):
        value=clip.get_editor_property(key)
        if asset.get_editor_property(key)!=value: asset.set_editor_property(key,value); finish()
    if not E.save_loaded_asset(asset,False): raise RuntimeError('Save failed: '+role)
    finish()
    saved[role]={'asset':asset.get_path_name(),'source':path,'source_sha256':digest}
    saved_path.write_text(json.dumps(saved,indent=2),encoding='utf-8')
    print('FEMALE_FURNITURE_SAVED',role,flush=True)
    count+=1
    if count>=6: break
remaining=sum(k not in saved for k in catalog['stale_roles'])
(W/'save_status.json').write_text(json.dumps({'remaining':remaining,'complete':remaining==0}),encoding='utf-8')
(P/'SourceAssets/KaitlinPlayer20261023'/(globals().get('FURNITURE_STAGE','sync_furniture_assets')+'_status.json')).write_text(json.dumps({'remaining':remaining,'complete':remaining==0}),encoding='utf-8')
print('FEMALE_FURNITURE_BATCH',count,'saved;',remaining,'remaining',flush=True)
