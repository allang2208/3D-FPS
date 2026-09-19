"""Submit the three-view sheet through the existing RTX 5080 TRELLIS.2 service."""
import json
import time
from pathlib import Path
import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent
BASE = 'http://127.0.0.1:18189'
schema = requests.get(BASE + '/object_info', timeout=30).json()
workflow = {}

def node(number, kind, **overrides):
    inputs = {}
    for key, spec in schema[kind]['input']['required'].items():
        if len(spec) > 1 and 'default' in spec[1]:
            inputs[key] = spec[1]['default']
        elif isinstance(spec[0], list):
            inputs[key] = spec[0][0]
    inputs.update(overrides)
    workflow[str(number)] = {'class_type': kind, 'inputs': inputs}
    return [str(number), 0]

sheet = ROOT / 'three_views.png'
with sheet.open('rb') as source:
    uploaded = requests.post(BASE + '/upload/image', files={'image': ('handbrain_20260910_three_views.png', source, 'image/png')}, timeout=60)
uploaded.raise_for_status()
name = uploaded.json()['name']
w, h = Image.open(sheet).size
image = node(1, 'LoadImage', image=name)
views = []
for index, label in enumerate(['front', 'right', 'back']):
    cropped = node(2 + index, 'ImageCrop', image=image, x=round(index*w/3), y=0, width=round(w/3), height=round(h*0.84))
    channel = node(30 + index, 'ImageToMask', image=cropped, channel='red')
    background = node(40 + index, 'ThresholdMask', mask=channel, value=0.73)
    alpha = node(50 + index, 'JoinImageWithAlpha', image=cropped, alpha=background)
    processed = node(5 + index, 'Trellis2PreProcessImage', image=alpha, padding=24, remove_background=False, max_size=1536)
    node(20 + index, 'SaveImage', images=processed, filename_prefix='HandBrain20260910/reference_' + label)
    views.append(processed)
model = node(8, 'Trellis2LoadModel', backend='sdpa', sparse_backend='xformers', low_vram=True, keep_models_loaded=False)
mesh = node(9, 'Trellis2MeshWithVoxelMultiViewGenerator', pipeline=model, front_image=views[0], right_image=views[1], back_image=views[2], seed=20260910, pipeline_type='1024_cascade', sparse_structure_steps=20, shape_steps=24, texture_steps=24, max_num_tokens=49152)
textured = node(10, 'Trellis2PostProcessAndUnWrapAndRasterizer', mesh=mesh, bvh=['9', 1], texture_size=4096, target_face_num=500000, remesh=False, remove_floaters=False, remove_inner_faces=False)
node(11, 'Trellis2ExportMesh', trimesh=textured, filename_prefix='HandBrain20260910/handbrain_detailed_v01', file_format='glb')
(ROOT / 'workflow_api.json').write_text(json.dumps(workflow, indent=2), encoding='utf-8')
queue = requests.get(BASE + '/queue', timeout=15).json()
print('Existing running/pending:', len(queue['queue_running']), len(queue['queue_pending']))
response = requests.post(BASE + '/prompt', json={'prompt': workflow, 'client_id': 'handbrain-20260910'}, timeout=30)
result = response.json()
(ROOT / 'submission.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
(ROOT / ('submission_' + str(int(time.time())) + '.json')).write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
response.raise_for_status()
