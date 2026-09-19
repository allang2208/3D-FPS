import json, urllib.request, urllib.error, uuid, sys
from pathlib import Path
P=Path(__file__).parent
BASE='http://192.168.3.142:8188'
def req(path,data=None,headers=None):
    return json.load(urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers=headers or {}),timeout=60))
def save(name,data):
    (P/name).write_text(json.dumps(data,indent=2),encoding='utf-8')
if sys.argv[1]=='submit':
    if (P/'receipt.json').exists():
        print((P/'receipt.json').read_text());sys.exit()
    boundary=uuid.uuid4().hex
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="phantom_rear_grip_20260913.jpg"\r\nContent-Type: image/jpeg\r\n\r\n').encode()+(P/'reference.jpg').read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
    up=req('/upload/image',body,{'Content-Type':'multipart/form-data; boundary='+boundary})
    save('upload.json',up)
    w=json.loads(Path('D:/FPS3D/FPSGAME/Tools/AssetPipeline/Mechanical3D/workflows/pixal_singleview.api.json').read_text())
    w['10']['inputs']['image']=up['name']
    w['11']={'class_type':'ImageCrop','inputs':{'image':['10',0],'x':450,'y':55,'width':260,'height':400}}
    w['20']['inputs']['image']=['11',0]
    w['21']={'class_type':'SaveImage','inputs':{'images':['20',0],'filename_prefix':'PhantomRearGripPixal20260913/input'}}
    w['51']['inputs']['filename_prefix']='PhantomRearGripPixal20260913/raw'
    w['53']['inputs']['filename_prefix']='PhantomRearGripPixal20260913/textured_master'
    save('workflow.json',w)
    try: r=req('/prompt',json.dumps({'client_id':'PhantomRearGripPixal20260913','prompt':w}).encode(),{'Content-Type':'application/json'})
    except urllib.error.HTTPError as e: print(e.read().decode());raise
    save('receipt.json',r);print(json.dumps(r))
else:
    pid=json.loads((P/'receipt.json').read_text())['prompt_id']
    h=req('/history/'+pid)
    if pid in h:
        save('history.json',h[pid]);print(json.dumps(h[pid]))
    else: print(json.dumps(req('/queue')))
