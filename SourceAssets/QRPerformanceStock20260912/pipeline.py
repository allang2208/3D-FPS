"""Produce a new QR stock from three separate image conditions on RTX 5080."""
import json,urllib.request,urllib.parse,uuid,sys,time,subprocess,base64
from pathlib import Path
from PIL import Image
P=Path(__file__).parent;BASE='http://192.168.3.142:8188';REMOTE='QRPerformanceStock20260912';TAG='qr_performance_stock'
def req(path,data=None,headers=None):
 return json.load(urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers=headers or {}),timeout=45))
def save(name,value):(P/name).write_text(json.dumps(value,indent=2),encoding='utf-8')
def defaults(info,name):
 r={}
 for k,v in info[name]['input']['required'].items():
  if len(v)>1 and 'default' in v[1]:r[k]=v[1]['default']
  elif isinstance(v[0],list):r[k]=v[0][0]
 return r
def submit():
 receipt=P/(TAG+'_submitted.json')
 if receipt.exists():print(receipt.read_text());return
 save('service.json',req('/system_stats'));info=req('/object_info');save('nodes.json',info)
 source=P/'model_views.png';width,height=Image.open(source).size
 # Layout follows the actual reference sheet: wide sides and a narrow end view.
 cuts=[0,round(width*.413),round(width*.585),width];bounds=[{'role':role,'crop':[cuts[i],0,cuts[i+1]-cuts[i],height]} for i,role in enumerate(['left_side','rear_end','right_side'])];save('view_crops.json',bounds)
 boundary=uuid.uuid4().hex;filename='qr_performance_stock_20260912.png'
 body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{filename}"\r\nContent-Type: image/png\r\n\r\n').encode()+source.read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
 up=req('/upload/image',body,{'Content-Type':'multipart/form-data; boundary='+boundary});save('upload.json',up)
 w={'1':{'class_type':'Trellis2LoadModel','inputs':defaults(info,'Trellis2LoadModel')},'2':{'class_type':'LoadImage','inputs':{'image':up['name']}}}
 w['1']['inputs'].update(low_vram=True,keep_models_loaded=False,backend='sdpa',sparse_backend='xformers',conv_backend='flex_gemm',modelname='microsoft/TRELLIS.2-4B')
 for i,view in enumerate(bounds):
  x,y,cw,ch=view['crop'];w[str(10+i)]={'class_type':'ImageCrop','inputs':{'image':['2',0],'x':x,'y':y,'width':cw,'height':ch}}
  w[str(30+i)]={'class_type':'Trellis2PreProcessImage','inputs':{'image':[str(10+i),0],'padding':24,'remove_background':True,'max_size':2048}}
  w[str(20+i)]={'class_type':'SaveImage','inputs':{'images':[str(30+i),0],'filename_prefix':f'{REMOTE}/{TAG}_view{i}'}}
 p=defaults(info,'Trellis2MeshWithVoxelMultiViewGenerator');p.update(pipeline=['1',0],front_image=['30',0],right_image=['31',0],back_image=['32',0],pipeline_type='1024_cascade',seed=91283,sparse_structure_steps=16,shape_steps=32,texture_steps=24,max_num_tokens=999999,generate_texture_slat=True,fill_holes=False)
 w['4']={'class_type':'Trellis2MeshWithVoxelMultiViewGenerator','inputs':p}
 w['5']={'class_type':'Trellis2MeshWithVoxelToTrimesh','inputs':{'mesh':['4',0],'reorient_vertices':'90 degrees'}}
 w['6']={'class_type':'Trellis2ExportMesh','inputs':{'trimesh':['5',0],'filename_prefix':f'{REMOTE}/{TAG}_raw_geometry','file_format':'glb'}}
 w['7']={'class_type':'Trellis2OvoxelExportToGLB','inputs':{'mesh':['4',0],'resolution':1024,'texture_size':4096,'target_face_num':200000}}
 w['8']={'class_type':'Trellis2ExportMesh','inputs':{'trimesh':['7',0],'filename_prefix':f'{REMOTE}/{TAG}_textured_master','file_format':'glb'}}
 save('generation_workflow.json',w);r=req('/prompt',json.dumps({'client_id':REMOTE,'prompt':w}).encode(),{'Content-Type':'application/json'});r['submitted_at']=time.time();save(TAG+'_submitted.json',r);print(json.dumps(r),flush=True)
def collect():
 pid=json.loads((P/(TAG+'_submitted.json')).read_text())['prompt_id'];h=req('/history/'+pid)
 if pid not in h:print('Generation running or queued',flush=True);return
 h=h[pid];save('generation_history.json',h)
 if h['status']['status_str']!='success':print(json.dumps(h['status']),flush=True);return
 files=[]
 def walk(x):
  if isinstance(x,dict):
   if 'filename' in x:files.append(x)
   else:
    for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(h['outputs'])
 # Mesh exporters write files without including them in the Comfy UI history.
 command=f"Get-ChildItem -LiteralPath 'D:/开发文件/ComfyUI/output/{REMOTE}' -File -Filter '*.glb' | Select-Object -ExpandProperty Name | ConvertTo-Json -Compress"
 encoded=base64.b64encode(command.encode('utf-16le')).decode();raw=subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=5','r5080','powershell','-NoProfile','-EncodedCommand',encoded],timeout=45)
 names=json.loads(raw.decode('utf-8-sig').strip() or '[]')
 if isinstance(names,str):names=[names]
 files.extend({'filename':n,'subfolder':REMOTE,'type':'output'} for n in names);save('outputs.json',files)
 for f in files:
  name=Path(f['filename']).name;dest=P/name
  if not dest.exists():urllib.request.urlretrieve(BASE+'/view?'+urllib.parse.urlencode({'filename':f['filename'],'subfolder':f.get('subfolder',''),'type':f.get('type','output')}),dest)
  print('Downloaded',name,flush=True)
 print('GENERATION_COMPLETE',flush=True)
if __name__=='__main__':(submit if sys.argv[1]=='submit' else collect)()
