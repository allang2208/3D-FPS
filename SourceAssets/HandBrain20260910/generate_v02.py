import json
from pathlib import Path
import requests
root=Path(__file__).resolve().parent
base='http://127.0.0.1:18189'
out=root/'v02'
out.mkdir(exist_ok=True)
schema=requests.get(base+'/object_info',timeout=30).json()
with (root/'source.png').open('rb') as f:
    response=requests.post(base+'/upload/image',files={'image':('handbrain_source_20260910.png',f,'image/png')},timeout=30)
response.raise_for_status()
previous=json.loads((root/'workflow_api.json').read_text())
keep={'1','2','5','8','9','10','11','20','30','40','50'}
workflow={k:v for k,v in previous.items() if k in keep}
workflow['1']['inputs']['image']=response.json()['name']
workflow['2']['inputs'].update(x=0,y=0,width=720,height=670)
inputs={}
for key,spec in schema['Trellis2MeshWithVoxelGenerator']['input']['required'].items():
    if len(spec)>1 and 'default' in spec[1]: inputs[key]=spec[1]['default']
    elif isinstance(spec[0],list): inputs[key]=spec[0][0]
inputs.update(pipeline=['8',0],image=['5',0],seed=20260910,pipeline_type='1024_cascade',sparse_structure_steps=16,shape_steps=16,texture_steps=16,max_num_tokens=32768)
workflow['9']={'class_type':'Trellis2MeshWithVoxelGenerator','inputs':inputs}
workflow['10']['inputs'].update(remesh=True,target_face_num=1000000,remove_inner_faces=True,remove_floaters=True)
workflow['11']['inputs']['filename_prefix']='HandBrain20260910/handbrain_detailed_v02'
workflow['20']['inputs']['filename_prefix']='HandBrain20260910/reference_source_v02'
(out/'workflow_api.json').write_text(json.dumps(workflow,indent=2))
result=requests.post(base+'/prompt',json={'prompt':workflow,'client_id':'handbrain-v02'},timeout=30)
print(result.text)
result.raise_for_status()
(out/'submission.json').write_text(json.dumps(result.json(),indent=2))
