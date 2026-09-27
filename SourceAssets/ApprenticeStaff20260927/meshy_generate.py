"""Task-local Meshy job; credentials live only in this interactive process."""
import getpass
import importlib.util
import json
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('staff_meshy_client', ROOT.parent / 'WitchMeshy20260919/meshy_pipeline.py')
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
        'should_remesh': True, 'topology': 'triangle', 'target_polycount': 16000,
        'save_pre_remeshed_model': True, 'target_formats': ['glb', 'fbx'],
        'auto_size': False,
    },
    'assets': {'staff': {'images': ['Inputs/front.png', 'Inputs/right.png', 'Inputs/back.png'], 'options': {
        'texture_prompt': 'A plain apprentice long staff made of honey brown oak. Round wooden ball head, long straight slim wooden shaft, continuous fine realistic wood grain, hand-worn satin wood, subtle tool marks, restrained shallow carved conduit grooves in upper shaft. No gemstones, metal, leather, spikes, magical glow, light baked into the texture, labels or decorations. Realistic physically based nonmetallic wood for first person closeups.'
    }}}
}


def main():
    # Pure extraction into equal view panels; no painted or regenerated pixels.
    from PIL import Image
    source = Image.open(ROOT / 'Design/apprentice_staff_three_views_v01.png').convert('RGB')
    width, height = source.size
    inputs = ROOT / 'Inputs'
    inputs.mkdir(exist_ok=True)
    rects = []
    for name, center in [('front', .205), ('right', .5), ('back', .795)]:
        half = int(width * .14)
        x = round(width * center)
        box = (x-half, 0, x+half, height)
        source.crop(box).save(inputs / (name + '.png'))
        rects.append({'view': name, 'box': box})
    client.write_json(inputs / 'views.json', {'source': 'Design/apprentice_staff_three_views_v01.png', 'size': source.size, 'views': rects})
    os.environ['MESHY_API_KEY'] = getpass.getpass('Meshy key (hidden; process only): ').strip()
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
