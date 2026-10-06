"""Area-weighted material reference from the actual RSH upper rail UVs."""
import json,numpy as np
from PIL import Image
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'RSH12Integration20261003'
part=next(x for x in json.loads((S/'canonical_parts.json').read_text()) if x['name']=='2_l')
verts=np.array(part['verts']);uv=np.array(part['uv']);samples=[];areas=[];cursor=0
for face in part['faces']:
    p=verts[face];t=uv[cursor:cursor+len(face)];cursor+=len(face)
    for i in range(1,len(face)-1):
        tri=p[[0,i,i+1]];area=np.linalg.norm(np.cross(tri[1]-tri[0],tri[2]-tri[0]))*.5
        if area>0:samples.append(t[[0,i,i+1]].mean(axis=0));areas.append(area)
uv=np.array(samples);areas=np.array(areas);out={}
for key,file in [('base_color','DefaultMaterial_albedo.jpg'),('roughness','DefaultMaterial_roughness.jpg'),('metallic','DefaultMaterial_metallic.jpg')]:
    im=np.asarray(Image.open(S/'Original/Extracted/textures'/file).convert('RGB'),dtype=float)/255
    h,w=im.shape[:2];pixels=im[np.minimum(h-1,((1-uv[:,1]%1)*h).astype(int)),np.minimum(w-1,((uv[:,0]%1)*w).astype(int))]
    if key=='base_color':pixels=np.where(pixels<=.04045,pixels/12.92,((pixels+.055)/1.055)**2.4)
    out[key]=np.average(pixels,axis=0,weights=areas).tolist()
out['reference']='RSH12 2_l rail area-weighted UV0 source PBR; linear color, original roughness/metallic'
(O/'finish_reference.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
