"""Spitter production: credential stays in process memory; resumable paid jobs."""
import argparse
import getpass
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('meshy_client', ROOT.parent / 'WitchMeshy20260919/meshy_pipeline.py')
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)
client.ROOT = ROOT
client.OUT = ROOT / 'Meshy'
client.SETTINGS = {'proxy':'http://127.0.0.1:7897'}
client.API = 'https://api.meshy.ai/openapi'

def job(name, endpoint, payload):
    folder = client.OUT / name
    receipt = folder / 'task.json'
    request = folder / 'request.json'
    if receipt.exists():
        task = json.loads(receipt.read_text(encoding='utf-8'))
    else:
        if request.exists():
            raise RuntimeError(name + ': submission has no receipt; recover task id before resubmitting.')
        client.balance('before_' + name)
        client.write_json(request, {'endpoint':endpoint, 'parameters':payload})
        result = client.api('POST', endpoint, payload)
        task = {'task_id':result['result'], 'endpoint':endpoint}
        client.write_json(receipt, task)
    last = None
    while True:
        result = client.api('GET', task['endpoint'] + '/' + task['task_id'])
        client.write_json(folder/'response.json', result)
        status = {'stage':name, 'task_id':task['task_id'], 'status':result['status'], 'progress':result.get('progress')}
        if status != last:
            print(json.dumps(status), flush=True)
            last = status
        if result['status'] == 'SUCCEEDED':
            count = client.download_result(folder, result)
            print(json.dumps({'stage':name,'downloaded':count,'credits':result.get('consumed_credits')}),flush=True)
            return task, result
        if result['status'] in ('FAILED','CANCELED'):
            raise RuntimeError(client.safe(result.get('task_error')))
        time.sleep(30)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--stdin-key',action='store_true')
    args=parser.parse_args()
    if args.stdin_key:
        os.environ['MESHY_API_KEY']=getpass.getpass('Meshy credential (hidden): ').strip()
    client.key_from_environment()
    library=client.api('GET','/v1/animations/library')
    client.write_json(ROOT/'animation_library.json',library)
    settings=json.loads((ROOT/'meshy_settings.json').read_text(encoding='utf-8'))
    model,_=job('body','/v1/image-to-3d',{
        **settings['model'], 'image_url':client.data_uri(ROOT/'Inputs/spitter_green_reference.png')})
    rig,_=job('rig','/v1/rigging',{'input_task_id':model['task_id'],'height_meters':1.85})
    client.balance('after_rig')
    client.write_json(ROOT/'production_status.json',{'model':model,'rig':rig,'stage':'rigged_candidate_downloaded','ue_imported':False,'tested':False})

if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'error':client.safe(str(exc))}),file=sys.stderr,flush=True)
        sys.exit(1)
    finally:
        os.environ.pop('MESHY_API_KEY',None)
