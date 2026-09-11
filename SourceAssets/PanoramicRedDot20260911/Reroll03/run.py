import sys,json,uuid,time,urllib.request,urllib.parse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent.parent))
from pipeline import req,defaults
P=Path(__file__).parent;REMOTE='PanoramicRedDot20260911/Reroll03'
def submit(mode):
 receipt=P/(mode+'_receipt.json')
 if receipt.exists():print(receipt.read_text());return
 info=req('/object_info');(P/'nodes.json').write_text(json.dumps(info))
 boundary=uuid.uuid4().hex
 body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="panoramic_reroll03_white.png"\r\nContent-Type: image/png\r\n\r\n').encode()+(P/'reference_white.png').read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
 up=req('/upload/image',body,{'Content-Type':'multipart/form-data; boundary='+boundary})
 w={'2':{'class_type':'LoadImage','inputs':{'image':up['name']}},'3':{'class_type':'Trellis2PreProcessImage','inputs':{'image':['2',0],'padding':64,'remove_background':True,'max_size':2048}},'9':{'class_type':'SaveImage','inputs':{'images':['3',0],'filename_prefix':REMOTE+'/segmented_input'}}}
 if mode.startswith('generate'):
  model=defaults(info,'Trellis2LoadModel');model.update(low_vram=True,keep_models_loaded=False,backend='sdpa',sparse_backend='xformers',conv_backend='flex_gemm',modelname='microsoft/TRELLIS.2-4B')
  w['1']={'class_type':'Trellis2LoadModel','inputs':model}
  v=defaults(info,'Trellis2MeshWithVoxelGenerator');v.update(pipeline=['1',0],image=['3',0],pipeline_type='1024_cascade',seed=91144,sparse_structure_steps=16,shape_steps=32,texture_steps=24,max_num_tokens=999999,generate_texture_slat=True,fill_holes=False)
  v['fill_holes']=mode=='generate_filled'
  w['4']={'class_type':'Trellis2MeshWithVoxelGenerator','inputs':v}
  w['5']={'class_type':'Trellis2MeshWithVoxelToTrimesh','inputs':{'mesh':['4',0],'reorient_vertices':'90 degrees'}}
  w['6']={'class_type':'Trellis2ExportMesh','inputs':{'trimesh':['5',0],'filename_prefix':REMOTE+'/reroll03_raw','file_format':'glb'}}
  w['7']={'class_type':'Trellis2OvoxelExportToGLB','inputs':{'mesh':['4',0],'resolution':1024,'texture_size':2048,'target_face_num':100000}}
  w['8']={'class_type':'Trellis2ExportMesh','inputs':{'trimesh':['7',0],'filename_prefix':REMOTE+'/reroll03_textured_master','file_format':'glb'}}
  if mode=='generate_filled':
   for key in ['6','8']:w[key]['inputs']['filename_prefix']=w[key]['inputs']['filename_prefix'].replace('reroll03_','reroll03_filled_')
 (P/(mode+'_workflow.json')).write_text(json.dumps(w,indent=2))
 r=req('/prompt',json.dumps({'prompt':w,'client_id':'panoramic-reroll03'}).encode(),{'Content-Type':'application/json'});r['submitted_at']=time.time();receipt.write_text(json.dumps(r,indent=2));print(r)
def status(mode):
 pid=json.loads((P/(mode+'_receipt.json')).read_text())['prompt_id'];h=req('/history/'+pid)
 if pid not in h: print('running or queued');return
 h=h[pid];(P/(mode+'_history.json')).write_text(json.dumps(h,indent=2));print(h['status'])
 for value in h.get('outputs',{}).values():
  for img in value.get('images',[]):
   url='http://192.168.3.142:8188/view?'+urllib.parse.urlencode(img)
   urllib.request.urlretrieve(url,P/img['filename']);print('downloaded',img['filename'])
if __name__=='__main__':(submit if sys.argv[1]=='submit' else status)(sys.argv[2])
