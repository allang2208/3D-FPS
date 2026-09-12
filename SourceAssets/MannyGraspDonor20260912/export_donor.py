"""Export unchanged locally installed Epic XR example poses for visual evaluation."""
import unreal, json
from pathlib import Path
O = Path(__file__).parent
D = O / 'Donor'
D.mkdir(exist_ok=True)
results = []
for name in ['SKM_MannyXR_right', 'SKM_MannyXR_left', 'A_MannequinsXR_Grasp_Right', 'A_MannequinsXR_Idle_Right', 'A_MannequinsXR_IndexCurl_Right', 'A_MannequinsXR_ThumbUp_Right', 'GrabAnimation']:
    folder = 'Animations' if name.startswith('A_') else 'Meshes'
    path = f'/Game/XRMannequins/{folder}/{name}'
    if name=='GrabAnimation':path='/Game/VRE/Core/GraspingHands/VRHandMeshes/Animations/GrabAnimation'
    asset = unreal.load_asset(path)
    assert asset, path
    task = unreal.AssetExportTask()
    task.object = asset
    task.filename = str(D / (name + '.fbx'))
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    options = unreal.FbxExportOption()
    options.ascii = False
    options.level_of_detail = False
    task.options = options
    ok = unreal.Exporter.run_asset_export_task(task)
    assert ok and Path(task.filename).stat().st_size > 1000, name
    item = {'asset': path, 'export': task.filename, 'class':asset.get_class().get_name()}
    if isinstance(asset, unreal.AnimSequence):
        item['duration'] = asset.get_play_length()
        item['frames'] = unreal.AnimationLibrary.get_num_frames(asset)
        item['skeleton'] = asset.get_editor_property('skeleton').get_path_name()
    results.append(item)
(O / 'donor_export.json').write_text(json.dumps(results, indent=2))
unreal.log('DONOR_EXPORT_PASS')
