"""Preserve FBX geometry/UV/normals; fill only zero source tangent vectors."""
import struct,zlib,array,json,math,hashlib
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ArcaneWorkbenchV6_20261107')
source=R/'Input/Enchantment_Workbench_V6.fbx'; data=source.read_bytes();pos=27;hdr='<IIIB';hs=13
assert data[:23]==b'Kaydara FBX Binary  \x00\x1a\x00' and struct.unpack_from('<I',data,23)[0]==7400
formats={'Y':('h',2),'C':('?',1),'I':('i',4),'F':('f',4),'D':('d',8),'L':('q',8)}
def read(n):
 global pos
 b=data[pos:pos+n];pos+=n;return b
def prop():
 start=pos;t=read(1).decode()
 if t in formats:fmt,n=formats[t];v=struct.unpack('<'+fmt,read(n))[0]
 elif t in 'SR':
  n=struct.unpack('<I',read(4))[0];v=read(n);v=v.decode('utf-8',errors='replace') if t=='S' else v
 elif t in 'fdilbc':
  n,enc,size=struct.unpack('<III',read(12));b=read(size);b=zlib.decompress(b) if enc else b
  v=array.array({'f':'f','d':'d','i':'i','l':'q','b':'b','c':'b'}[t]);v.frombytes(b);assert len(v)==n
 else:raise ValueError(t)
 return {'t':t,'v':v,'raw':data[start:pos]}
def node():
 h=read(hs);end,n,plen,nlen=struct.unpack(hdr,h)
 if end==0:return None
 name=read(nlen);props=[prop() for _ in range(n)];children=[];null=False
 while pos<end:
  ch=node()
  if ch is None:null=True
  else:children.append(ch)
 assert pos==end
 return {'n':name,'p':props,'c':children,'null':null}
roots=[]
while True:
 n=node()
 if n is None:break
 roots.append(n)
footer=data[pos:]
def child(n,name):return next(x for x in n['c'] if x['n']==name.encode())
def val(n,name):return child(n,name)['p'][0]['v']
objects=child({'c':roots},'Objects')['c']
g=next(x for x in objects if x['n']==b'Geometry' and 'SM_EnchantmentWorkbench' in str(x['p'][1]['v']))
tnode=child(child(g,'LayerElementTangent'),'Tangents');bnode=child(child(g,'LayerElementBinormal'),'Binormals')
t=tnode['p'][0]['v'];b=bnode['p'][0]['v'];normal=child(g,'LayerElementNormal');n=val(normal,'Normals');ni=val(normal,'NormalsIndex')
original_t=t.tobytes();original_b=b.tobytes()
def norm(v):return math.sqrt(sum(x*x for x in v))
def unit(v):
 length=norm(v);assert length>1e-9;return [x/length for x in v]
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
repairs=[]
for i in range(len(ni)):
 T=list(t[3*i:3*i+3]);B=list(b[3*i:3*i+3]);zt=norm(T)<1e-4;zb=norm(B)<1e-4
 if not zt and not zb:continue
 N=unit(list(n[ni[i]*3:ni[i]*3+3]))
 # In an affected corner a nonzero tangent may still be parallel to the normal.
 # Fill a valid orthonormal frame only for these 47 originally degenerate bases.
 projected=[T[k]-N[k]*sum(T[j]*N[j] for j in range(3)) for k in range(3)]
 if norm(projected)>1e-4:T=unit(projected)
 elif not zb and norm(cross(B,N))>1e-4:T=unit(cross(B,N))
 else:
  axis=min(range(3),key=lambda k:abs(N[k]));a=[0,0,0];a[axis]=1;T=unit(cross(a,N))
 new_b=unit(cross(N,T))
 if not zb and sum(new_b[k]*B[k] for k in range(3))<0:new_b=[-x for x in new_b]
 t[3*i:3*i+3]=array.array(t.typecode,T);b[3*i:3*i+3]=array.array(b.typecode,new_b)
 repairs.append({'corner':i,'tangent_filled':zt,'binormal_filled':zb})
assert len(repairs)==47
for nd in (tnode,bnode):
 p=nd['p'][0];compressed=zlib.compress(p['v'].tobytes(),9);p['raw']=p['t'].encode()+struct.pack('<III',len(p['v']),1,len(compressed))+compressed
out=bytearray(data[:27])
def write_node(n):
 start=len(out);out.extend(b'\x00'*hs);out.extend(n['n']);raw=b''.join(p['raw'] for p in n['p']);out.extend(raw)
 for c in n['c']:write_node(c)
 if n['null']:out.extend(b'\x00'*hs)
 end=len(out);out[start:start+hs]=struct.pack(hdr,end,len(n['p']),len(raw),len(n['n']))
for n in roots:write_node(n)
out.extend(b'\x00'*hs);out.extend(footer)
authored=R/'Authored';authored.mkdir(exist_ok=True);target=authored/'Enchantment_Workbench_V6_TangentFix.fbx';target.write_bytes(out)
receipt={'source':str(source),'source_sha256':hashlib.sha256(data).hexdigest(),'authored':str(target),'authored_sha256':hashlib.sha256(out).hexdigest(),'corners':len(ni),'repaired_corners':len(repairs),'tangents_filled':sum(x['tangent_filled'] for x in repairs),'binormals_filled':sum(x['binormal_filled'] for x in repairs),'preserved':'All geometry, UV, vertex normals, material IDs, collision and node transforms unchanged; only the 47 bases containing a zero vector receive an orthonormal fallback.','repairs':repairs}
(R/'Receipts/tangent-authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in receipt.items() if k!='repairs'}))