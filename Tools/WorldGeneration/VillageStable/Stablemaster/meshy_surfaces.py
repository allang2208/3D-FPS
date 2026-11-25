"""Read original embedded Meshy atlases, keeping the PBR channel conventions explicit."""
import io,json,sys
from pathlib import Path
from PIL import Image

PROJECT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(PROJECT/'Tools/VillageHerbalist'))
from prepare_surface import glb_chunks

ROOT=PROJECT/'SourceAssets/HillsVillageStable/StablemasterMeshyR3'
OUT=ROOT/'Authoring'
def prepare(role):
    gltf,buf=glb_chunks(ROOT/role/(role+'.glb'))
    def read_tex(info):
        entry=gltf['textures'][info['index']]
        image=gltf['images'][entry['source']]
        v=gltf['bufferViews'][image['bufferView']];start=v.get('byteOffset',0)
        return Image.open(io.BytesIO(buf[start:start+v['byteLength']]))
    result=[]
    for idx,m in enumerate(gltf['materials']):
        pbr=m.get('pbrMetallicRoughness',{}); prefix=f'Stablemaster_{role}_{idx}'; files={}
        for key,ref in [('Color',pbr.get('baseColorTexture')),('Normal',m.get('normalTexture'))]:
            if ref:
                im=read_tex(ref);path=OUT/f'T_{prefix}_{key}.png';im.save(path);files[key]=path.name
        if 'Color' not in files:raise ValueError('Missing Meshy albedo on '+role)
        mr=pbr.get('metallicRoughnessTexture');ao=m.get('occlusionTexture')
        if mr or ao:
            packed=read_tex(mr).convert('RGB') if mr else None
            occlusion=read_tex(ao).convert('RGB').getchannel('R') if ao else None
            size=packed.size if packed else occlusion.size
            white=Image.new('L',size,255)
            orm=Image.merge('RGB',(occlusion.resize(size) if occlusion else white,packed.getchannel('G') if packed else white,packed.getchannel('B') if packed else white))
            path=OUT/f'T_{prefix}_ORM.png';orm.save(path);files['ORM']=path.name
        result.append(dict(index=idx,name='M_'+prefix,role=role,files=files,color=pbr.get('baseColorFactor',[1,1,1,1]),rough=pbr.get('roughnessFactor',1.),metal=pbr.get('metallicFactor',1.),occlusion=bool(ao),two_sided=m.get('doubleSided',False),alpha=m.get('alphaMode','OPAQUE'),cutoff=m.get('alphaCutoff',.5)))
    return result

if __name__=='__main__':
    OUT.mkdir(exist_ok=True)
    (OUT/'surfaces.json').write_text(json.dumps(prepare('Head')+prepare('Body'),indent=2))
