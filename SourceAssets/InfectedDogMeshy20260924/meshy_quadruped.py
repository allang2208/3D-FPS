"""Produce a Meshy quadruped rig without replacing the source or UE assets."""
import argparse
import json
import time
from pathlib import Path

from meshy_pipeline import api, download_result, safe, write_json, ROOT

OUT = ROOT / 'Meshy'
SOURCE_TASK = '01a0d354-0532-73e3-816b-0ba74bfd089d'
REMESH_NAME = 'candidate01_quad50k'
RIG_NAME = 'candidate01_quadruped_rig'


def balance(label):
    result = api('GET', '/v1/balance')
    write_json(OUT / f'balance_{label}.json', result)
    print(json.dumps({'balance_label': label, **result}), flush=True)


def create_task(name, endpoint, payload):
    folder = OUT / name
    receipt = folder / 'task.json'
    if receipt.exists():
        return json.loads(receipt.read_text(encoding='utf-8'))
    if (folder / 'request.json').exists():
        raise RuntimeError('A submission is already recorded without a task ID. Recover it before retrying POST.')
    balance('before_' + name)
    write_json(folder / 'request.json', {
        'endpoint': endpoint, 'parameters': payload,
        'schema_source': 'https://docs.meshy.ai/openapi.json',
        'purpose': 'User requested Meshy quadruped-template rigging of candidate01',
    })
    try:
        result = api('POST', endpoint, payload)
    except Exception as error:
        write_json(folder / 'submission_error.json', {'error': safe(str(error)), 'type': type(error).__name__})
        raise
    task = {'asset': name, 'endpoint': endpoint, 'task_id': result['result']}
    write_json(receipt, task)
    print(json.dumps({'submitted': task}), flush=True)
    return task


def finish_task(task):
    folder = OUT / task['asset']
    while True:
        result = api('GET', task['endpoint'] + '/' + task['task_id'])
        write_json(folder / 'response.json', result)
        print(json.dumps({'asset': task['asset'], 'status': result['status'],
                          'progress': result.get('progress'),
                          'animation_type': result.get('animation_type'),
                          'credits': result.get('consumed_credits')}, ensure_ascii=False), flush=True)
        if result['status'] == 'SUCCEEDED':
            count = download_result(folder, result)
            balance('after_' + task['asset'])
            write_json(folder / 'production_receipt.json', {
                'stage': 'downloaded_service_output', 'task_id': task['task_id'],
                'downloaded_files': count, 'consumed_credits': result.get('consumed_credits'),
                'requested_template': 'quadruped' if task['asset'] == RIG_NAME else None,
                'ue_imported': False, 'animation_or_visual_testing_performed': False,
            })
            print(json.dumps({'completed': task['asset'], 'downloaded': count}), flush=True)
            return result
        if result['status'] in ('FAILED', 'CANCELED'):
            balance('after_' + task['asset'])
            print(json.dumps({'task_error': safe(result.get('task_error'))}, ensure_ascii=False), flush=True)
            raise RuntimeError('Meshy task did not succeed; no replacement task was submitted.')
        time.sleep(30)


def run():
    remesh = create_task(REMESH_NAME, '/v1/remesh', {
        'input_task_id': SOURCE_TASK, 'topology': 'quad', 'target_polycount': 50000,
        'target_formats': ['glb', 'fbx'],
    })
    finish_task(remesh)
    rig = create_task(RIG_NAME, '/v1/rigging', {
        'input_task_id': remesh['task_id'],
        'animation_type': 'quadruped', 'height_meters': 1.0,
        'name': 'InfectedDog Candidate01 Quadruped',
    })
    finish_task(rig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['run', 'balance'])
    args = parser.parse_args()
    if args.command == 'balance':
        balance('quadruped_current')
    else:
        run()
