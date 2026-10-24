"""Bake the saved Jason full-body clip catalog onto Kaitlin's native skeleton.

Run in FPSGAME after the native packages are installed. Existing motion timing,
sync markers and action mapping keys are carried by the native retarget batch.
This script does not publish the runtime variant or start gameplay.
"""
import hashlib
import json
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
WORK = PROJECT / 'SourceAssets/KaitlinPlayer20261023'
if not (WORK / 'kaitlin_body_uv.json').exists():
    import runpy
    runpy.run_path(str(PROJECT / 'Tools/KaitlinPlayer/capture_body_uv.py'), run_name='__main__')
DEST = '/Game/Characters/KaitlinPlayer20261023/Motion'
body = json.loads(Path(globals().get('BODY_INPUT', WORK / 'FitInputs/player_body.json')).read_text(encoding='utf-8-sig'))
native = json.loads((WORK / 'native_install_receipt.json').read_text(encoding='utf-8'))
targets = [path for path in native['skeletal_meshes'] if '/Body/SKM_MHC_Kaitlin_BodyMesh.' in path]
if len(targets) != 1:
    raise RuntimeError('Select Kaitlin native body from the saved assembly before retargeting.')
source = u.load_asset(body['body_mesh'])
target = u.load_asset(targets[0])
E, A = u.EditorAssetLibrary, u.AssetToolsHelpers.get_asset_tools()
receipt_path = WORK / 'retargeted_assets.json'
saved = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {}


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Animation authoring save failed: ' + asset.get_path_name())


def finish_compression():
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    u.SystemLibrary.execute_console_command(world, 'Editor.AsyncAssetCompilationFinishAll')


def create(name, cls, factory):
    return u.load_asset(DEST + '/Rig/' + name) or A.create_asset(name, DEST + '/Rig', cls, factory)


def rig(name, mesh):
    asset = create(name, u.IKRigDefinition, u.IKRigDefinitionFactory())
    control = u.IKRigController.get_controller(asset)
    control.set_skeletal_mesh(mesh)
    control.set_retarget_root('pelvis')
    chains = {'Spine': ('spine_01', 'spine_05'), 'Neck': ('neck_01', 'neck_02'), 'Head': ('head', 'head')}
    for side in ('l', 'r'):
        for label, first, last in (('Clavicle', 'clavicle', 'clavicle'), ('Arm', 'upperarm', 'hand'),
                                   ('Leg', 'thigh', 'foot'), ('Toe', 'ball', 'ball')):
            chains[label + '_' + side] = (first + '_' + side, last + '_' + side)
        for digit in ('thumb', 'index', 'middle', 'ring', 'pinky'):
            chains[digit + '_' + side] = (digit + '_01_' + side, digit + '_03_' + side)
    existing = {str(chain.chain_name) for chain in control.get_retarget_chains()}
    for label, (first, last) in chains.items():
        if label not in existing:
            control.add_retarget_chain(label, first, last, '')
    save(asset)
    return asset


source_rig = rig('IK_Jason_Source', source)
target_rig = rig('IK_Kaitlin_Target', target)
retargeter = create('RTG_Jason_Kaitlin', u.IKRetargeter, u.IKRetargetFactory())
controller = u.IKRetargeterController.get_controller(retargeter)
controller.set_ik_rig(u.RetargetSourceOrTarget.SOURCE, source_rig)
controller.set_ik_rig(u.RetargetSourceOrTarget.TARGET, target_rig)
controller.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE, source)
controller.set_preview_mesh(u.RetargetSourceOrTarget.TARGET, target)
if controller.get_num_retarget_ops() == 0:
    controller.add_default_ops()
controller.auto_map_chains(u.AutoMapChainType.EXACT, True)
pose = controller.create_retarget_pose('Kaitlin_Aligned', u.RetargetSourceOrTarget.TARGET)
controller.set_current_retarget_pose(pose, u.RetargetSourceOrTarget.TARGET)
controller.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET)
save(retargeter)

written = 0
for path in dict.fromkeys(body['clips'].values()):
    if path in saved:
        continue
    clip = u.load_asset(path)
    if clip.get_editor_property('skeleton') != source.skeleton:
        raise RuntimeError('Clip requires its own source rig: ' + path)
    suffix = hashlib.sha256(path.encode()).hexdigest()[:10]
    inputs = u.IKRetargetBatchOperationInputs()
    inputs.assets_to_retarget = [E.find_asset_data(path)]
    inputs.source_mesh = source
    inputs.target_mesh = target
    inputs.ik_retarget_asset = retargeter
    inputs.prefix = 'K_' + suffix + '_'
    inputs.target_path = DEST + '/Animations'
    inputs.include_referenced_assets = False
    inputs.overwrite_existing_files = False
    results = u.IKRetargetBatchOperation.run_batch_retarget(inputs)
    finish_compression()
    outputs = [data.get_asset() for data in results if str(data.asset_class_path.asset_name) == 'AnimSequence']
    if len(outputs) != 1:
        raise RuntimeError('Retarget did not produce a unique clip: ' + path)
    output = outputs[0]
    for property_name in ('enable_root_motion', 'force_root_lock', 'root_motion_root_lock', 'rate_scale'):
        value = clip.get_editor_property(property_name)
        if output.get_editor_property(property_name) != value:
            output.set_editor_property(property_name, value)
            finish_compression()
    save(output)
    finish_compression()
    saved[path] = output.get_path_name()
    receipt_path.write_text(json.dumps(saved, indent=2), encoding='utf-8')
    print('KAITLIN_CLIP_SAVED', output.get_path_name(), flush=True)
    written += 1
    if written >= 8:
        break
if all(path in saved for path in body['clips'].values()):
    (WORK / 'retargeted_clips.json').write_text(json.dumps({key: saved[path] for key, path in body['clips'].items()}, indent=2), encoding='utf-8')
print('KAITLIN_RETARGET_BATCH', written, 'saved;', len(saved), 'unique clips total')
remaining = sum(path not in saved for path in set(body['clips'].values()))
(WORK / 'retarget_status.json').write_text(json.dumps({'remaining': remaining, 'complete': remaining == 0}), encoding='utf-8')
finish_compression()
