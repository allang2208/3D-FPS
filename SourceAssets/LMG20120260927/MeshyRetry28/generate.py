"""One new Meshy candidate from the user's new two-sided references."""
import argparse,getpass,importlib.util,json,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
source=ROOT.parents[1]/'WitchMeshy20260919/meshy_pipeline.py'
spec=importlib.util.spec_from_file_location('meshy_retry28_client',source)
client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client)
client.ROOT=ROOT;client.OUT=ROOT/'Meshy'
client.SETTINGS=json.loads((ROOT/'meshy_settings.json').read_text())
client.API=client.SETTINGS['api_base']
NAME='lmg201_new_reference_smooth_v01'

def run():
    parser=argparse.ArgumentParser()
    parser.add_argument('--prompt-key',action='store_true')
    args=parser.parse_args()
    if args.prompt_key:os.environ['MESHY_API_KEY']=getpass.getpass('Meshy API key (hidden): ').strip()
    try:
        client.submit(NAME)
        folder=client.OUT/NAME
        task=json.loads((folder/'task.json').read_text())
        previous=None
        while True:
            result=client.api('GET',task['endpoint']+'/'+task['task_id'])
            client.write_json(folder/'response.json',result)
            state={k:result.get(k) for k in ['status','progress','consumed_credits']}
            if state!=previous:print(json.dumps(state),flush=True);previous=state
            if result['status']=='SUCCEEDED':
                # The existing downloader stores the main model/texture/preview
                # outputs; include requested extra service thumbnails as files.
                download=dict(result)
                download['result']={'view_'+k:v for k,v in result.get('thumbnail_urls',{}).items()} if isinstance(result.get('thumbnail_urls'),dict) else {}
                count=client.download_result(folder,download)
                client.balance('after_'+NAME)
                client.write_json(ROOT/'delivery.json',{'status':'candidate_downloaded','task_id':task['task_id'],
                    'consumed_credits':result.get('consumed_credits'),'downloaded_files':count,
                    'model':'meshy-7.1','stage':'candidate_only','ue_imported':False,
                    'shape_prompt_supported':False,'texture_prompt':client.SETTINGS['assets'][NAME]['options']['texture_prompt'],
                    'runtime_tested':False})
                print('MESHY28_CANDIDATE_DOWNLOADED',count,flush=True);return
            if result['status'] in ['FAILED','CANCELED']:raise RuntimeError(client.safe(result.get('task_error')))
            time.sleep(30)
    finally:
        if args.prompt_key:os.environ.pop('MESHY_API_KEY',None)

if __name__=='__main__':
    try:run()
    except Exception as exc:print(json.dumps({'error':client.safe(str(exc))}),flush=True);sys.exit(1)
