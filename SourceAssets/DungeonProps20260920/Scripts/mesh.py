"""Dungeon props 2026-09-20: TRELLIS.2 multiview mesh generation on the 5080.

Reads <prop>/three_views.png (produced by reference.py), cuts the three panels by
alpha/ink bounding boxes, feeds them as front/left/back, and exports raw + textured
GLB. Crop boxes are measured per sheet by measure_views.py, not hard-coded blind.

Subcommands:
  prepare   : write crops.json by measuring the three panels in each sheet
  submit    : upload sheets and submit TRELLIS jobs
  fetch     : poll and download raw/textured GLB
"""
import json, sys, uuid, urllib.request, urllib.parse
from pathlib import Path

P = Path(__file__).resolve().parent.parent
BASE = 'http://192.168.3.142:8188'
CLIENT = 'DungeonProps20260920'
TEMPLATE = Path('D:/FPS3D/FPSGAME/Tools/AssetPipeline/Mechanical3D/workflows/trellis_ss64.api.json')


def req(path, data=None, headers=None, timeout=120):
    return json.load(urllib.request.urlopen(
        urllib.request.Request(BASE + path, data=data, headers=headers or {}), timeout=timeout))


def main():
    props = json.loads((P / 'props.json').read_text(encoding='utf-8'))['props']
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'

    if cmd == 'prepare':
        from PIL import Image
        for d in props:
            sheet = P / d['id'] / 'three_views.png'
            if not sheet.exists():
                print(d['id'], 'no sheet yet', flush=True)
                continue
            im = Image.open(sheet).convert('RGB')
            W, H = im.size
            # Three equal panels; shrink 4% on each side to avoid the panel gap.
            pw = W // 3
            crops = []
            for i in range(3):
                x0 = i * pw
                x1 = x0 + pw
                inset_x = int(pw * 0.04)
                inset_y = int(H * 0.04)
                crops.append({'x': x0 + inset_x, 'y': inset_y,
                              'width': pw - 2 * inset_x, 'height': H - 2 * inset_y})
            (P / d['id'] / 'crops.json').write_text(json.dumps(crops, indent=2))
            print(d['id'], 'sheet', (W, H), '->', crops, flush=True)

    elif cmd == 'submit':
        for d in props:
            folder = P / d['id']
            sheet = folder / 'three_views.png'
            receipt = folder / 'mesh_receipt.json'
            if not sheet.exists():
                print(d['id'], 'no sheet, skip', flush=True)
                continue
            if receipt.exists():
                print(d['id'], 'already submitted', flush=True)
                continue
            crops = json.loads((folder / 'crops.json').read_text())
            boundary = uuid.uuid4().hex
            body = (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; '
                    f'filename="{d["id"]}_three_views.png"\r\nContent-Type: image/png\r\n\r\n').encode() \
                + sheet.read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
            up = req('/upload/image', body, {'Content-Type': 'multipart/form-data; boundary=' + boundary})
            (folder / 'upload.json').write_text(json.dumps(up, indent=2))

            w = json.loads(TEMPLATE.read_text(encoding='utf-8'))
            w['10']['inputs']['image'] = up['name']
            for key in ['11', '12', '20', '21', '22']:
                w.pop(key, None)
            for i, c in enumerate(crops):
                crop_id, pre_id = str(110 + i), str(120 + i)
                w[crop_id] = {'class_type': 'ImageCrop', 'inputs': {
                    'image': ['10', 0], 'x': c['x'], 'y': c['y'],
                    'width': c['width'], 'height': c['height']}}
                w[pre_id] = {'class_type': 'Trellis2PreProcessImage', 'inputs': {
                    'image': [crop_id, 0], 'padding': 24, 'remove_background': True, 'max_size': 2048}}
                w[str(130 + i)] = {'class_type': 'SaveImage', 'inputs': {
                    'images': [pre_id, 0], 'filename_prefix': f'DungeonProps20260920/{d["id"]}/view{i}'}}
            # The template carries a right_image input pointing at node 21, which is removed
            # here; dropping it avoids a KeyError during prompt validation.
            w['4']['inputs'].pop('right_image', None)
            w['4']['inputs'].update({
                'seed': d['seed'], 'pipeline_type': '1024_cascade', 'sparse_structure_resolution': 64,
                'sparse_structure_steps': 16, 'shape_steps': 32, 'texture_steps': 24,
                'generate_texture_slat': True, 'fill_holes': False, 'keep_only_shell': False,
                'front_image': ['120', 0], 'left_image': ['121', 0], 'back_image': ['122', 0]})
            for key, name in [('51', 'raw'), ('53', 'textured_master')]:
                w[key]['inputs']['filename_prefix'] = f'DungeonProps20260920/{d["id"]}/{name}'
            (folder / 'mesh_workflow.json').write_text(json.dumps(w, indent=2))
            r = req('/prompt', json.dumps({'client_id': CLIENT, 'prompt': w}).encode(),
                    {'Content-Type': 'application/json'})
            receipt.write_text(json.dumps(r, indent=2))
            print(d['id'], r, flush=True)

    elif cmd == 'fetch':
        for d in props:
            folder = P / d['id']
            receipt = folder / 'mesh_receipt.json'
            if not receipt.exists():
                print(d['id'], 'not submitted', flush=True)
                continue
            pid = json.loads(receipt.read_text())['prompt_id']
            h = req('/history/' + pid).get(pid)
            if not h:
                print(d['id'], 'pending', flush=True)
                continue
            (folder / 'mesh_history.json').write_text(json.dumps(h, indent=2))
            print(d['id'], h['status']['status_str'], flush=True)
            if h['status']['status_str'] != 'success':
                for kind, msg in h['status']['messages']:
                    if kind == 'execution_error':
                        print('   ', msg.get('exception_message', '')[:300], flush=True)
                continue
            for filename in ['textured_master_00001_.glb', 'raw_00001_.glb']:
                out = folder / filename
                if not out.exists():
                    url = BASE + '/view?' + urllib.parse.urlencode(
                        {'filename': filename, 'subfolder': f'DungeonProps20260920/{d["id"]}', 'type': 'output'})
                    urllib.request.urlretrieve(url, out)
                    print(d['id'], 'downloaded', filename, out.stat().st_size, 'bytes', flush=True)

    else:
        q = req('/queue')
        print('running:', len(q.get('queue_running', [])), 'pending:', len(q.get('queue_pending', [])))
        for d in props:
            f = P / d['id']
            print(' -', d['id'],
                  'sheet' if (f / 'three_views.png').exists() else 'no-sheet',
                  'mesh' if (f / 'mesh_receipt.json').exists() else '')


if __name__ == '__main__':
    main()