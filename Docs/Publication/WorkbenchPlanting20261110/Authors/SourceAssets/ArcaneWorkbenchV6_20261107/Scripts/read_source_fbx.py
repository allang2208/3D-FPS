"""Read binary FBX author transforms and anchors; no rendering or game execution."""
import struct,zlib,json,array
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ArcaneWorkbenchV6_20261107')
f=(R/'Input/Enchantment_Workbench_V6.fbx').open('rb')
assert f.read(23)==b'Kaydara FBX Binary  \x00\x1a\x00'
version=struct.unpack('<I',f.read(4))[0]
wide=version>=7500
hdr='<QQQB' if wide else '<IIIB'; hs=struct.calcsize(hdr)
formats={'Y':('h',2),'C':('?',1),'I':('i',4),'F':('f',4),'D':('d',8),'L':('q',8)}
def prop():
 t=f.read(1).decode()
 if t in formats:
  fmt,n=formats[t]; return struct.unpack('<'+fmt,f.read(n))[0]
 if t in 'SR':
  n=struct.unpack('<I',f.read(4))[0]; b=f.read(n); return b.decode('utf-8',errors='replace') if t=='S' else b
 if t in 'fdilbc':
  n,enc,size=struct.unpack('<III',f.read(12)); b=f.read(size); b=zlib.decompress(b) if enc else b
  a=array.array({'f':'f','d':'d','i':'i','l':'q','b':'b','c':'b'}[t]);a.frombytes(b); assert len(a)==n;return a
 raise ValueError(t)
def node():
 h=f.read(hs)
 if len(h)!=hs:return None
 end,n,plen,nlen=struct.unpack(hdr,h)
 if end==0:return None
 name=f.read(nlen).decode(); p=[prop() for i in range(n)]; children=[]
 while f.tell()<end:
  c=node()
  if c:children.append(c)
 return {'n':name,'p':p,'c':children}
root=[]
while True:
 a=node()
 if a is None:break
 root.append(a)
f.close()
def child(n,name):return next(x for x in n['c'] if x['n']==name)
objects=child({'c':root},'Objects')['c']
summary={'version':version,'global_settings': [{ 'name':x['p'][0],'value':x['p'][4:]} for x in child(child({'c':root},'GlobalSettings'),'Properties70')['c']], 'models':[], 'geometry':[]}
for n in objects:
 if n['n']=='Model':
  props=child(n,'Properties70')['c']
  summary['models'].append({'id':n['p'][0],'name':n['p'][1],'type':n['p'][2],'properties':{p['p'][0]:p['p'][4:] for p in props}})
 if n['n']=='Geometry':
  v=child(n,'Vertices')['p'][0]; verts=list(zip(v[::3],v[1::3],v[2::3]))
  polys=child(n,'PolygonVertexIndex')['p'][0]
  summary['geometry'].append({'id':n['p'][0],'name':n['p'][1],'vertices':len(verts),'polygons':sum(x<0 for x in polys),'min':[min(x[i] for x in verts) for i in range(3)],'max':[max(x[i] for x in verts) for i in range(3)],'first_vertices':verts[:8]})
  if len(verts)>100:
   mats=child(child(n,'LayerElementMaterial'),'Materials')['p'][0];groups={}; face=[];idx=0
   for p in polys:
    face.append(p if p>=0 else -p-1)
    if p<0:
     groups.setdefault(mats[idx],set()).update(face);idx+=1;face=[]
   summary['geometry'][-1]['material_geometry']={str(k):{'n':len(ids),'min':[min(verts[x][i] for x in ids) for i in range(3)],'max':[max(verts[x][i] for x in ids) for i in range(3)],'centroid':[sum(verts[x][i] for x in ids)/len(ids) for i in range(3)]} for k,ids in groups.items()}
(R/'Receipts/source-geometry.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))