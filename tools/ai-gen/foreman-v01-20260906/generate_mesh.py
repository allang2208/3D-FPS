"""Single bounded local-owner ComfyUI generation; preserves request and history."""
import json, time, urllib.request, urllib.parse, uuid, subprocess, base64
from pathlib import Path
ROOT = Path(__file__).resolve().parent
HOST = 'http://192.168.3.142:8188'
def request(path, data=None):
    raw = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(HOST+path, data=raw, headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r: return json.load(r)
def upload():
    boundary=uuid.uuid4().hex
    name='foreman-apose-20260906-v01.png'
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\nContent-Type: image/png\r\n\r\n').encode()+(ROOT/'foreman-apose.png').read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
    req=urllib.request.Request(HOST+'/upload/image',data=body,headers={'Content-Type':f'multipart/form-data; boundary={boundary}'})
    with urllib.request.urlopen(req,timeout=60) as r: return json.load(r)['name']
def node(name, **inputs): return {'class_type':name,'inputs':inputs}
if __name__=='__main__':
    workflow={
      '1':node('LoadImage',image=upload()),
      '2':node('Trellis2LoadModel',modelname='microsoft/TRELLIS.2-4B',backend='sdpa',device='cuda',low_vram=True,keep_models_loaded=False,conv_backend='flex_gemm',sparse_backend='xformers',use_reconviagen=False),
      '3':node('Trellis2MeshWithVoxelGenerator',pipeline=['2',0],image=['1',0],seed=906744,pipeline_type='512',sparse_structure_steps=12,shape_steps=12,texture_steps=12,max_num_tokens=49152,max_views=1,sparse_structure_resolution=32,generate_texture_slat=True,use_tiled_decoder=True,sampler='euler',fill_holes=False,hole_iterations=1,hole_fill_algorithm='flood_fill',keep_only_shell=False),
      '4':node('Trellis2ReconstructMeshWithQuad',mesh=['3',0],remesh_band=1.0,resolution=512,remove_floaters=True,remove_inner_faces=False),
      '5':node('Trellis2SimplifyMesh',mesh=['4',0],target_face_num=30000,method='Meshlib'),
      '6':node('Trellis2UnWrapAndRasterizer',mesh=['5',0],mesh_cluster_threshold_cone_half_angle_rad=60.0,mesh_cluster_refine_iterations=0,mesh_cluster_global_iterations=1,mesh_cluster_smooth_strength=1,texture_size=2048,texture_alpha_mode='OPAQUE',double_side_material=False,bake_on_vertices=False,use_custom_normals=False,bvh=['3',1],inpainting='telea',reorient_vertices='90 degrees'),
      '7':node('Trellis2ExportMesh',trimesh=['6',0],filename_prefix='3D/foreman_20260906_v01',file_format='glb')}
    (ROOT/'mesh-workflow.json').write_text(json.dumps(workflow,indent=2),encoding='utf8')
    reply=request('/prompt',{'prompt':workflow,'client_id':'foreman-3d-20260906-v01'})
    (ROOT/'mesh-submission.json').write_text(json.dumps(reply,indent=2))
    print(json.dumps(reply),flush=True)
    pid=reply['prompt_id']
    deadline=time.time()+1800
    while time.time()<deadline:
        h=request('/history/'+pid).get(pid)
        if h:
            (ROOT/'mesh-history.json').write_text(json.dumps(h,indent=2),encoding='utf8')
            if h.get('status',{}).get('status_str')=='error':
                print(json.dumps(h.get('status')),flush=True); raise SystemExit(1)
            print(json.dumps(h.get('outputs',{})),flush=True)
            outputs=h.get('outputs',{})
            downloaded=False
            for v in outputs.values():
                for key in ('3d','mesh','meshes'):
                    for item in v.get(key,[]):
                        if isinstance(item,dict) and item.get('filename','').endswith('.glb'):
                            url=HOST+'/view?'+urllib.parse.urlencode(item)
                            with urllib.request.urlopen(url,timeout=120) as r: (ROOT/'foreman-raw.glb').write_bytes(r.read())
                            downloaded=True
                            print('Downloaded foreman-raw.glb',flush=True)
            if not downloaded:
                # This installed ExportMesh saves files without UI history outputs.
                ps="Get-ChildItem -LiteralPath 'D:\\开发文件\\ComfyUI\\output\\3D' -Filter 'foreman_20260906_v01_*.glb' | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty Name"
                encoded=base64.b64encode(ps.encode('utf-16-le')).decode()
                result=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','r5080','powershell','-NoProfile','-EncodedCommand',encoded],capture_output=True,timeout=30,check=True)
                name=result.stdout.decode('utf8','replace').strip()
                if not name.startswith('foreman_20260906_v01_') or not name.endswith('.glb') or '/' in name or '\\' in name:
                    raise RuntimeError('Export exists but remote filename could not be resolved: '+repr(name))
                query=urllib.parse.urlencode({'filename':name,'subfolder':'3D','type':'output'})
                with urllib.request.urlopen(HOST+'/view?'+query,timeout=120) as r:(ROOT/'foreman-raw.glb').write_bytes(r.read())
                print('Downloaded '+name,flush=True)
            break
        time.sleep(8)
    else: raise SystemExit('Generation still running after bounded wait; use saved prompt id.')
