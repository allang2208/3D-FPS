from pathlib import Path
import json,struct,copy
P=Path(__file__).resolve().parent
R=P.parents[2]
O=P/'generated';O.mkdir(exist_ok=True)
base={'modern':R/'assets/models/modern_zombie/modern_zombie_v02.glb',**{k:R/('assets/models/humanoid_variants/'+k+'_zombie_v02.glb') for k in ['miner','runner']}}
def recolor(source,png,target):
 raw=source.read_bytes();n=struct.unpack_from('<I',raw,12)[0];j=json.loads(raw[20:20+n]);before=copy.deepcopy(j);binary=raw[28+n:];payload=bytearray(binary)
 payload.extend(b'\0'*(-len(payload)%4));offset=len(payload);data=png.read_bytes();payload.extend(data)
 j['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(data)})
 j['images'].append({'bufferView':len(j['bufferViews'])-1,'mimeType':'image/png'})
 j['textures'].append({'source':len(j['images'])-1})
 j['materials'][0]['pbrMetallicRoughness']['baseColorTexture']={'index':len(j['textures'])-1}
 j['buffers'][0]['byteLength']=len(payload)
 for key in ['nodes','meshes','skins','animations','accessors']:assert j[key]==before[key]
 assert payload[:len(binary)]==binary
 enc=json.dumps(j,separators=(',',':')).encode();enc+=b' '*(-len(enc)%4);payload.extend(b'\0'*(-len(payload)%4))
 target.write_bytes(struct.pack('<III',0x46546c67,2,28+len(enc)+len(payload))+struct.pack('<II',len(enc),0x4e4f534a)+enc+struct.pack('<II',len(payload),0x004e4942)+payload)
 return {'clips':len(j['animations']),'geometry_rig_animation_exact':True}
sources={};report={}
for k,source in base.items():
 sources[k]=str(source)
 variant=O/(k+'-original-variant.glb')
 recolor(source,R/('assets/models/zombie_skin_variants/'+k+'_albedo.png'),variant)
 sources[k+'-variant']=str(variant)
 for suffix,input_path in [('',source),('-variant',variant)]:
  name=k+suffix;report[name]=recolor(input_path,P/(name+'-albedo.png'),O/(name+'-unified.glb'))
(P/'sources.json').write_text(json.dumps(sources),encoding='utf-8')
(O/'preservation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('RICH_REBUILD_PASS six materials, original mesh/rig/animations preserved')
