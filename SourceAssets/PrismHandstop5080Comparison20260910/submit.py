import json,urllib.request,uuid
from pathlib import Path
P=Path(__file__).parent;BASE='http://192.168.3.142:8188'
def request(path,data=None,headers={}):
 return json.load(urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers=headers),timeout=30))
source=P.parent/'PrismHandstop20260910/three_views_v01.png'
boundary=uuid.uuid4().hex
body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="prism_reference_20260910.png"\r\nContent-Type: image/png\r\n\r\n').encode()+source.read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
upload=request('/upload/image',body,{'Content-Type':'multipart/form-data; boundary='+boundary})
w=json.loads((P.parent/'AngledForegrip20260910/workflow_retry.json').read_text())
w['2']['inputs']['image']=upload['name']
w['10']={'class_type':'ImageCrop','inputs':{'image':['2',0],'x':25,'y':150,'width':630,'height':675}}
w['7']['inputs']['image']=['10',0];w['9']['inputs']['image']=['10',0]
w['4']['inputs']['seed']=91037
w['6']['inputs']['filename_prefix']='PrismCompare20260910/prism_raw'
w['11']={'class_type':'SaveImage','inputs':{'images':['3',0],'filename_prefix':'PrismCompare20260910/input'}}
(P/'workflow.json').write_text(json.dumps(w,indent=2))
payload={'client_id':'prism-compare-20260910','prompt':w}
assert not (P/'submitted.json').exists(),'Already submitted; query the existing task.'
r=request('/prompt',json.dumps(payload).encode(),{'Content-Type':'application/json'})
(P/'submitted.json').write_text(json.dumps(r,indent=2));print(r)
