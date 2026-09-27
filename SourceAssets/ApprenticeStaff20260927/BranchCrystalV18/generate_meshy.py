"""Task-local Meshy generation. Key stays in process memory, never in files."""
import getpass
import importlib.util
import json
import os
from pathlib import Path
import time
from PIL import Image

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('staff_meshy', ROOT.parents[1] / 'WitchMeshy20260919/meshy_pipeline.py')
client = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(client)
client.ROOT = ROOT
client.OUT = ROOT / 'Meshy'
client.SETTINGS = {
    'proxy': 'http://127.0.0.1:7897',
    'common': {
        'ai_model': 'meshy-7.1', 'geometry_resolution': 'standard',
        'should_texture': True, 'enable_pbr': True, 'texture_resolution': '4k',
        'image_enhancement': False, 'remove_lighting': True,
        'should_remesh': True, 'topology': 'triangle', 'target_polycount': 24000,
        'save_pre_remeshed_model': True, 'target_formats': ['glb', 'fbx'], 'auto_size': False,
    },
    'assets': {'staff': {'images': ['Inputs/front.png', 'Inputs/right.png', 'Inputs/back.png'], 'options': {
        'texture_prompt': 'Rustic apprentice staff, bare weathered brown natural tree branch, longitudinal bark cracks and small natural branch knots. No winding vines or wrapping on the middle or lower shaft. Only a few tan rough hemp rope coils, knot and short frayed ends immediately below the clear colorless faceted quartz crystal at the very top. Realistic wood and hemp fibers, subtle wear. No metal, ball, gold, emission, runes, labels, baked light or shadows. Preserve all reference proportions. Physically based nonmetallic materials for close first person viewing.'
    }}}
}

def main():
    # Split the generated sheet into input panels; no pixels are repainted.
    im = Image.open(ROOT / 'Design/staff_three_views.png').convert('RGB')
    rects = []
    for index, name in enumerate(('front', 'right', 'back')):
        box = (round(im.width * index / 3) + 2, 0, round(im.width * (index + 1) / 3) - 2, im.height)
        im.crop(box).save(ROOT / 'Inputs' / (name + '.png'))
        rects.append({'view': name, 'box': box})
    client.write_json(ROOT / 'Inputs/views.json', {'source': 'Design/staff_three_views.png', 'size': im.size, 'views': rects,
        'design_constraint': 'Top rope only; no lower wrapping or vine. Hidden views are inferred.'})
    try:
        client.key_from_environment()
    except RuntimeError:
        os.environ['MESHY_API_KEY'] = getpass.getpass('Meshy key (hidden): ').strip()
    try:
        client.submit('staff')
        task = json.loads((client.OUT / 'staff/task.json').read_text())
        while True:
            result = client.api('GET', task['endpoint'] + '/' + task['task_id'])
            client.write_json(client.OUT / 'staff/response.json', result)
            print(json.dumps({'status': result['status'], 'progress': result.get('progress')}, ensure_ascii=False), flush=True)
            if result['status'] == 'SUCCEEDED':
                count = client.download_result(client.OUT / 'staff', result)
                client.balance('after_staff')
                print(json.dumps({'downloaded': count, 'task_id': task['task_id'], 'credits': result.get('consumed_credits')}), flush=True)
                break
            if result['status'] in ('FAILED', 'CANCELED'):
                raise RuntimeError(client.safe(result.get('task_error')))
            time.sleep(30)
    finally:
        os.environ.pop('MESHY_API_KEY', None)

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'error': client.safe(str(exc))}, ensure_ascii=False), flush=True)
        raise SystemExit(1)
