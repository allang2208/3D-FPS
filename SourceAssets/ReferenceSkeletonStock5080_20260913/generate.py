"""Author and retrieve this candidate only; never renders, launches UE, or mutates other jobs."""
import json
import sys
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = 'http://192.168.3.142:8188'
SEED = 91379
OUT = ROOT / f'seed_{SEED}'
PREFIX = f'ReferenceSkeletonStock5080_20260913/seed_{SEED}'

def request(path, data=None, headers=None):
    with urllib.request.urlopen(urllib.request.Request(BASE + path, data=data, headers=headers or {}), timeout=60) as response:
        return json.load(response)

def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

def submit():
    OUT.mkdir(exist_ok=True)
    if (OUT / 'receipt.json').exists():
        print('Already submitted:', (OUT / 'receipt.json').read_text(), flush=True)
        return
    save(ROOT / 'service_at_submission.json', request('/system_stats'))
    queue = request('/queue')
    save(ROOT / 'queue_at_submission.json', {'running_count':len(queue['queue_running']), 'pending_count':len(queue['queue_pending'])})
    boundary = uuid.uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="reference_skeleton_stock_20260913_three_views.png"\r\nContent-Type: image/png\r\n\r\n').encode() + (ROOT / 'three_views.png').read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
    upload = request('/upload/image', body, {'Content-Type':'multipart/form-data; boundary=' + boundary})
    save(ROOT / 'upload.json', upload)
    workflow = json.loads(Path('D:/FPS3D/FPSGAME/Tools/AssetPipeline/Mechanical3D/workflows/trellis_ss64.api.json').read_text())
    for key in ['11', '12', '20', '21', '22']:
        workflow.pop(key, None)
    workflow['10']['inputs']['image'] = upload['name']
    # These rectangles derive from this 1536x1024 sheet, not the old grip layout.
    views = [
        ('side_a', 'front_image', '+Z', (0, 0, 768, 500)),
        ('side_b', 'back_image', '-Z', (768, 0, 768, 500)),
        ('front_end', 'left_image', '-X', (600, 500, 340, 524)),
    ]
    mapping = []
    for index, (name, slot, direction, rect) in enumerate(views):
        crop, preprocess = str(110 + index), str(120 + index)
        x, y, width, height = rect
        workflow[crop] = {'class_type':'ImageCrop', 'inputs':{'image':['10',0], 'x':x, 'y':y, 'width':width, 'height':height}}
        workflow[preprocess] = {'class_type':'Trellis2PreProcessImage', 'inputs':{'image':[crop,0], 'padding':24, 'remove_background':True, 'max_size':2048}}
        workflow[str(130 + index)] = {'class_type':'SaveImage', 'inputs':{'images':[preprocess,0], 'filename_prefix':PREFIX + '/condition_' + name}}
        workflow[str(140 + index)] = {'class_type':'SaveImage', 'inputs':{'images':[crop,0], 'filename_prefix':PREFIX + '/reference_' + name}}
        mapping.append({'view':name, 'node_input':slot, 'nominal_camera_direction':direction, 'crop_xywh':rect})
    inputs = workflow['4']['inputs']
    inputs.pop('right_image', None)
    inputs.update(seed=SEED, front_image=['120',0], back_image=['121',0], left_image=['122',0], front_axis='z', fill_holes=False, keep_only_shell=False)
    workflow['51']['inputs']['filename_prefix'] = PREFIX + '/raw'
    workflow['53']['inputs']['filename_prefix'] = PREFIX + '/textured_master'
    save(ROOT / 'view_mapping.json', {'sheet_size':[1536,1024], 'views':mapping, 'note':'Camera labels are generation conditions, not a measured exported mesh orientation. No host fit or dimensional claim.'})
    save(OUT / 'workflow.json', workflow)
    payload = {'client_id':'ReferenceSkeletonStock5080_20260913', 'prompt':workflow}
    save(OUT / 'request.json', payload)
    response = request('/prompt', json.dumps(payload).encode(), {'Content-Type':'application/json'})
    save(OUT / 'receipt.json', response)
    print(json.dumps(response), flush=True)

def status(fetch=False):
    pid = json.loads((OUT / 'receipt.json').read_text())['prompt_id']
    history = request('/history/' + pid).get(pid)
    if not history:
        queue = request('/queue')
        state = 'running' if any(item[1] == pid for item in queue['queue_running']) else 'pending' if any(item[1] == pid for item in queue['queue_pending']) else 'history_not_yet_available'
        print(json.dumps({'prompt_id':pid, 'state':state}), flush=True)
        return
    save(OUT / 'history.json', history)
    print(json.dumps({'prompt_id':pid, 'status':history['status']}, ensure_ascii=True), flush=True)
    if not fetch or history['status']['status_str'] != 'success':
        return
    outputs = []
    for node, value in history.get('outputs', {}).items():
        for item in value.get('images', []):
            outputs.append(dict(item, node=node))
    for name in ['raw_00001_.glb', 'textured_master_00001_.glb']:
        outputs.append({'filename':name, 'subfolder':PREFIX, 'type':'output'})
    downloads = []
    for item in outputs:
        local = OUT / Path(item['filename']).name
        url = BASE + '/view?' + urllib.parse.urlencode({k:item[k] for k in ['filename','subfolder','type']})
        if not local.exists():
            urllib.request.urlretrieve(url, local)
        downloads.append({'local_file':local.name, 'remote':item, 'bytes':local.stat().st_size})
    save(OUT / 'downloads.json', downloads)
    print(json.dumps(downloads), flush=True)

if __name__ == '__main__':
    if sys.argv[1] == 'submit':
        submit()
    else:
        status(fetch=sys.argv[1] == 'fetch')
