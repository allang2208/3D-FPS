import json,struct,io
from pathlib import Path
from PIL import Image,ImageChops,ImageStat
O=Path(__file__).parent;S=O.parent/'BenelliM4Super9020261006';raw=(S/'Original/glb.glb').read_bytes()
n=struct.unpack_from('<I',raw,12)[0];d=json.loads(raw[20:20+n]);binary=raw[28+n:]
def accessor(i):
    a=d['accessors'][i];v=d['bufferViews'][a['bufferView']];off=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',8)
    return [struct.unpack_from('<2f',binary,off+k*stride) for k in range(min(4,a['count']))]
rows={}
for m in d['materials']:
    if m['name'] not in ('TTI_Benelli_M4','matchsaverz','12gauge'):continue
    data={}
    for key,t in [('base',m['pbrMetallicRoughness']['baseColorTexture']),('normal',m['normalTexture'])]:
        im=d['images'][d['textures'][t['index']]['source']];v=d['bufferViews'][im['bufferView']];o=v.get('byteOffset',0)
        img=Image.open(io.BytesIO(binary[o:o+v['byteLength']])).convert('RGB')
        stem={'TTI_Benelli_M4':('TTI_Benelli_M4_BaseColor_brand_friendly','TTI_Benelli_M4_Normal_brand_friendly'),'12gauge':('12gauge_BaseColor_red','12gauge_Normal_brand_friendly'),'matchsaverz':('matchsaverz_BaseColor_black_brand_friendly','matchsaverz_Normal')}[m['name']][key=='normal']
        original=Image.open(S/'Original/Source/textures'/(stem+'.png')).convert('RGB').resize(img.size)
        (O/'SourceReference').mkdir(exist_ok=True)
        (O/'SourceReference'/(m['name']+'_'+key+'.png')).write_bytes(binary[o:o+v['byteLength']])
        a=img.resize((256,256));b=original.resize((256,256))
        data[key]={'file':im.get('name'),'transform':t.get('extensions'),'source_difference':ImageStat.Stat(ImageChops.difference(a,b)).mean,'source_rotated_difference':ImageStat.Stat(ImageChops.difference(a,b.transpose(Image.Transpose.ROTATE_180))).mean}
        data[key]['flip_x_difference']=ImageStat.Stat(ImageChops.difference(a,b.transpose(Image.Transpose.FLIP_LEFT_RIGHT))).mean
        data[key]['flip_y_difference']=ImageStat.Stat(ImageChops.difference(a,b.transpose(Image.Transpose.FLIP_TOP_BOTTOM))).mean
    mesh=next(x for x in d['meshes'] if any(p['material']==d['materials'].index(m) for p in x['primitives']))
    data['raw_uv']=accessor(mesh['primitives'][0]['attributes']['TEXCOORD_0']);rows[m['name']]=data
(O/'gltf_mapping.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
