"""Native-frame hard-surface rebuild. No arm or gameplay data enters this file."""
import bpy,bmesh,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KDetail20261018'
g=json.loads((P/'SourceAssets/Saiga12KRefine20261017/Authoring/gun.json').read_text());comps=json.loads((O/'Authoring/source_components.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
objects=[];mats={};records=[]
POLY={'Stock','RearGrip','Handguard','Magazine','ExtMagazine','ShellPlastic'}
def material(part):
 if part in mats:return mats[part]
 m=bpy.data.materials.new('Saiga12K_'+part);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');poly=part in POLY;interior=part=='ReceiverInterior';rubber=part=='StockPad'
 color=(.019,.019,.018,1) if poly else (.011,.011,.011,1) if rubber else (.004,.004,.004,1) if interior else (.034,.035,.037,1)
 rough=.50 if poly else .68 if rubber else .75 if interior else .36 if part=='ReceiverCover' else .31 if part=='Bolt' else .39
 if part=='Bolt':color=(.105,.108,.109,1)
 if part=='ShellBrass':color=(.35,.23,.08,1)
 if part=='ShellPlastic':color=(.19,.025,.018,1)
 bs.inputs['Base Color'].default_value=color;bs.inputs['Metallic'].default_value=0. if poly or interior or rubber else 1.;bs.inputs['Roughness'].default_value=rough;mats[part]=m;return m
def select(ob):
 bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
def mesh(name,verts,faces,parts):
 me=bpy.data.meshes.new(name);me.from_pydata([(v[0],-v[1],v[2]) for v in verts],[],[f[::-1] for f in faces]);me.update();ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob)
 names=list(dict.fromkeys(parts));[me.materials.append(material(x)) for x in names]
 for f,k in zip(me.polygons,parts):f.material_index=names.index(k)
 objects.append(ob);return ob
def clean(ob,bevel=.035,segments=3,dissolve=True):
 me=ob.data;bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
 if dissolve:bmesh.ops.dissolve_limit(bm,angle_limit=.001,verts=list(bm.verts),edges=list(bm.edges),delimit={'MATERIAL'})
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();select(ob)
 if bevel:
  mod=ob.modifiers.new('Machined radius in cm','BEVEL');mod.width=bevel;mod.segments=segments;mod.limit_method='ANGLE';mod.angle_limit=math.radians(32);mod.use_clamp_overlap=True;mod.harden_normals=True;bpy.ops.object.modifier_apply(modifier=mod.name)
 # Face-area normals replace source low-poly interpolants; only real sharp creases split.
 bm=bmesh.new();bm.from_mesh(me)
 bmesh.ops.dissolve_degenerate(bm,dist=.00001,edges=list(bm.edges))
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 for f in bm.faces:f.smooth=True
 for e in bm.edges:e.smooth=not(e.is_manifold and e.calc_face_angle() > math.radians(55))
 bm.to_mesh(me);bm.free();mod=ob.modifiers.new('Area weighted manufactured normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=50;bpy.ops.object.modifier_apply(modifier=mod.name)
 return ob
def source(name,faces,override=None,width=.035,segments=3):
 ids=sorted({v for fi in faces for v in g['triangles'][fi]});look={v:i for i,v in enumerate(ids)}
 return clean(mesh(name,[g['positions'][v] for v in ids],[[look[v] for v in g['triangles'][fi]] for fi in faces],[override or g['parts'][fi] for fi in faces]),width,segments)
def loft_polymer(part,axis,steps=80):
 # Reconstruct a smooth shell from the actual source's section envelope.
 # Interface coordinates and grip silhouette therefore stay in the native frame.
 faces=[g['triangles'][i] for i,k in enumerate(g['parts']) if k==part];points=np.array(g['positions']);q=points[np.array(faces)];lo=q[:,:,axis].min();hi=q[:,:,axis].max();other=[i for i in range(3) if i!=axis];vs=[];fs=[];rings=[];count=48
 for value in np.linspace(lo+.004,hi-.004,steps):
  sample=max(value,lo+.14) if part=='RearGrip' else value
  hits=[]
  for a,b in ((0,1),(1,2),(2,0)):
   aa=q[:,a];bb=q[:,b];den=bb[:,axis]-aa[:,axis];valid=(abs(den)>1e-9)&((aa[:,axis]-sample)*(bb[:,axis]-sample)<=0)
   if valid.any():hits.extend((aa[valid]+(bb[valid]-aa[valid])*((sample-aa[valid,axis])/den[valid])[:,None]).tolist())
  if len(hits)<3:continue
  hits=np.array(hits);mn=hits[:,other].min(0);mx=hits[:,other].max(0);mid=(mn+mx)*.5;half=(mx-mn)*.5
  if min(half)<.009:continue
  ring=[]
  for j in range(count):
   angle=2*math.pi*j/count;c=math.cos(angle);s=math.sin(angle);xy=mid+half*np.array([math.copysign(abs(c)**.52,c),math.copysign(abs(s)**.52,s)]);v=[0.,0.,0.];v[axis]=value;v[other[0]]=xy[0];v[other[1]]=xy[1];ring.append(len(vs));vs.append(v)
  rings.append(ring)
 for a,b in zip(rings,rings[1:]):
  for j in range(count):k=(j+1)%count;fs.append([a[j],a[k],b[k],b[j]])
 fs.extend([rings[0][::-1],rings[-1]]);return clean(mesh('Native '+part,vs,fs,[part]*len(fs)),0.,3,False)
def pocket(ob,name,y0,y1,z,r,x0,x1):
 # A closed capsule-shaped cutter: actual recessed wall and rim, not painted AO.
 points=[]
 for centre,start in [(y1,-math.pi/2),(y0,math.pi/2)]:
  for a in np.linspace(start,start+math.pi,25):points.append((centre+r*math.cos(a),z+r*math.sin(a)))
 n=len(points);verts=[[x,y,zz] for x in (x0,x1) for y,zz in points];faces=[list(range(n-1,-1,-1)),list(range(n,n*2))]+[[j,(j+1)%n,(j+1)%n+n,j+n] for j in range(n)]
 cut=mesh(name,verts,faces,['Handguard']*len(faces));select(ob);mod=ob.modifiers.new(name,'BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name);objects.remove(cut);bpy.data.objects.remove(cut,do_unlink=True)
def lathe(name,profile,cx,zc,xratio,part,n=64):
 vs=[];fs=[]
 for y,r in profile:
  vs.extend([[cx+xratio*r*math.sin(2*math.pi*j/n),y,zc+r*math.cos(2*math.pi*j/n)] for j in range(n)])
 for i in range(len(profile)):
  k=(i+1)%len(profile)
  for j in range(n):q=(j+1)%n;fs.append([i*n+j,i*n+q,k*n+q,k*n+j])
 return clean(mesh(name,vs,fs,[part]*len(fs)),.018,3,False)
body=sorted([c for c in comps if c['part']=='Body'],key=lambda c:len(c['faces']),reverse=True)
pin_ids={19,21,23,28,29,30,31,32,33,34,35,36,37,38,39,40}
def cylinder_x(name,bounds,part):
 lo,hi=np.array(bounds);centre=(lo+hi)*.5;ry=(hi[1]-lo[1])*.5;rz=(hi[2]-lo[2])*.5;n=40;vs=[];fs=[]
 # Rolled rim, narrow chamfer, full-depth body: preserves native head/axis position.
 for x,s in [(lo[0],.82),(lo[0]+.025,1.),(hi[0]-.025,1.),(hi[0],.82)]:
  vs.extend([[x,centre[1]+ry*s*math.sin(2*math.pi*j/n),centre[2]+rz*s*math.cos(2*math.pi*j/n)] for j in range(n)])
 for i in range(3):
  for j in range(n):k=(j+1)%n;fs.append([i*n+j,i*n+k,(i+1)*n+k,(i+1)*n+j])
 fs.extend([list(range(n-1,-1,-1)),list(range(3*n,4*n))]);return clean(mesh(name,vs,fs,[part]*len(fs)),0.,3,False)
for i,c in enumerate(body):
 if i in (2,3):continue
 if i in pin_ids:cylinder_x('Receiver pin %02d'%i,c['bounds'],'Fasteners');continue
 source('Native body %02d'%i,c['faces'],'StockPad' if i==13 else None,.09 if i==13 else .035,4 if i==13 else 3)
lathe('Rebuilt smooth barrel',[(16.476,1.291),(21.484,1.291),(23.693,.982),(56.944,.982),(57.118,.906),(57.195,1.114),(58.959,1.1804),(59.3942075,1.1804),(59.3942075,.9057),(16.476,.9057)],.08,3.953,.8419,'Barrel',96)
lathe('Rebuilt gas tube and collars',[(16.552,1.75),(16.982,1.35),(18.857,.933),(20.062,1.35),(20.23,1.1495),(35.134,1.1495),(35.349,1.367),(40.167,1.367),(40.242,.674),(40.447,1.085),(40.447,.46),(16.552,.46)],.08,6.43,.73,'GasTube',64)
section=[(-1.17,4.62),(-1.17,6.83)]+[(.08+1.25*math.cos(t),6.83+1.25*math.sin(t)) for t in np.linspace(math.pi,0,41)]+[(1.33,4.62)]
verts=[];faces=[];n=len(section)
for y,shift in [(-7.65,-.65),(-6.3,0),(16.589,0)]:verts.extend([[x,y,z+shift if z>6.8 else z] for x,z in section])
for i in range(2):
 for j in range(n-1):faces.append([i*n+j,i*n+j+1,(i+1)*n+j+1,(i+1)*n+j])
faces.extend([list(range(n-1,-1,-1)),list(range(2*n,3*n))])
cover=mesh('Continuous receiver cover',verts,faces,['ReceiverCover']*len(faces));cover.data.materials.append(material('ReceiverInterior'));select(cover)
solid=cover.modifiers.new('Real 0.7 mm rolled shell','SOLIDIFY');solid.thickness=.07;solid.offset=-1;solid.material_offset=1;solid.material_offset_rim=1;bpy.ops.object.modifier_apply(modifier=solid.name)
bpy.ops.mesh.primitive_cube_add(size=1,location=(-1.45,-8.10125,5.38));cutter=bpy.context.object;cutter.data.materials.append(material('ReceiverInterior'));cutter.dimensions=(1.76,15.2875,2.455);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);select(cover);mod=cover.modifiers.new('Native ejection window below continuous roof','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True);clean(cover,.025,3)
for part in sorted(set(g['parts'])-{'Body','ReceiverCover','ReceiverInterior'}):
 if part in ('Stock','RearGrip','Handguard'):
  ob=loft_polymer(part,2 if part=='RearGrip' else 1)
  if part=='Handguard':
   pocket(ob,'Left molded handguard recess',25.27,35.25,3.656,1.08,-1.8,-1.07);pocket(ob,'Right molded handguard recess',25.27,35.25,3.656,1.08,1.23,1.8);clean(ob,.035,3,False)
  if part=='Stock':
   panel=[(-27.077,.155),(-27.006,-.261),(-17.778,.894),(-17.346,1.395),(-17.417,1.81),(-17.992,2.139),(-26.644,.656)];n=len(panel)
   for x0,x1 in [(.879,1.5),(-1.4,-.719)]:
    verts=[[x,y,z] for x in (x0,x1) for y,z in panel];faces=[list(range(n-1,-1,-1)),list(range(n,2*n))]+[[j,(j+1)%n,(j+1)%n+n,j+n] for j in range(n)];cut=clean(mesh('Original molded stock recess',verts,faces,['Stock']*len(faces)),.04,3,False);select(ob);mod=ob.modifiers.new('Original stock panel restored','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name);objects.remove(cut);bpy.data.objects.remove(cut,do_unlink=True)
   clean(ob,.018,3,False)
  continue
 width=.12 if part=='Stock' else .085 if part in ('RearGrip','Handguard') else .05 if part=='Magazine' else .025
 source('Native '+part,[i for i,k in enumerate(g['parts']) if k==part],None,width,4)
def tree(ob):
 me=ob.data;return BVHTree.FromPolygons([v.co.copy() for v in me.vertices],[list(f.vertices) for f in me.polygons],all_triangles=False)
def rib(name,path,normals,radius,part):
 if len(path)<3:return
 vs=[];fs=[];n=8
 for i,(p,no) in enumerate(zip(path,normals)):
  tangent=(path[min(i+1,len(path)-1)]-path[max(0,i-1)]).normalized();side=tangent.cross(no).normalized();up=side.cross(tangent).normalized();rr=radius*(.12 if i in (0,len(path)-1) else .8 if i in (1,len(path)-2) else 1.)
  for j in range(n):
   v=p+side*(math.cos(j*2*math.pi/n)*rr)+up*(math.sin(j*2*math.pi/n)*rr*.55);vs.append([v.x,-v.y,v.z])
 for i in range(len(path)-1):
  for j in range(n):k=(j+1)%n;fs.append([i*n+j,i*n+k,(i+1)*n+k,(i+1)*n+j])
 fs.extend([list(range(n-1,-1,-1)),list(range((len(path)-1)*n,len(path)*n))]);clean(mesh(name,vs,fs,[part]*len(fs)),0.,3,False)
ct=tree(cover)
for x in (-.58,.74):
 pts=[];norm=[]
 for y in np.linspace(-5.8,14.0,55):
  hit,no,_,_=ct.ray_cast(Vector((x,-y,15)),Vector((0,0,-1)),20)
  if hit is not None:pts.append(hit+no*.008);norm.append(no)
 rib('Pressed cover longitudinal rib',pts,norm,.055,'ReceiverCover')
def magazine_ribs(ob,part,low):
 tr=tree(ob)
 for side in (-1,1):
  for shift in (-1.75,1.75):
   pts=[];norm=[]
   for z in np.linspace(-2.7,low,48):
    y=50.628671656-math.sqrt(max(38.165166013**2-(z-4.76056238)**2,1.))+shift
    hit,no,_,_=tr.ray_cast(Vector((side*6,-y,z)),Vector((-side,0,0)),12)
    if hit is not None:pts.append(hit+no*.006);norm.append(no)
   rib(part+' molded longitudinal edge',pts,norm,.037,part)
magazine_ribs(next(o for o in objects if o.name=='Native Magazine'),'Magazine',-11.8)
pad=next(o for o in objects if o.name=='Native body 13');pt=tree(pad)
for z in np.linspace(-3.65,3.45,13):
 pts=[];norm=[]
 for x in np.linspace(-.65,.81,16):
  hit,no,_,_=pt.ray_cast(Vector((x,34,z)),Vector((0,-1,0)),8)
  if hit is not None:pts.append(hit+no*.006);norm.append(no)
 rib('Buttpad molded traction rib',pts,norm,.032,'StockPad')
grip=next(o for o in objects if o.name=='Native RearGrip');gt=tree(grip)
# Deliberate shallow linear grip flutes, rather than sand/noise normals.
for side in (-1,1):
 for z in np.linspace(-2.8,-7.6,9):
  pts=[];norm=[]
  for y in np.linspace(-6.0,-3.0,14):
   hit,no,_,_=gt.ray_cast(Vector((side*4,-y,z)),Vector((-side,0,0)),8)
   if hit is not None:pts.append(hit+no*.004);norm.append(no)
  rib('Molded rear grip flute',pts,norm,.027,'RearGrip')
def join(label,items):
 select(items[0]);[o.select_set(True) for o in items];bpy.ops.object.join();ob=bpy.context.object;ob.name=label
 tri=ob.modifiers.new('Stable runtime triangulation','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
 bm=bmesh.new();bm.from_mesh(ob.data);tiny=[f for f in bm.faces if f.calc_area()<1e-10]
 if tiny:
  bmesh.ops.delete(bm,geom=tiny,context='FACES_ONLY');bm.to_mesh(ob.data)
 bm.free()
 if tiny:
  wn=ob.modifiers.new('Final area weighted normals','WEIGHTED_NORMAL');wn.keep_sharp=True;wn.weight=50;bpy.ops.object.modifier_apply(modifier=wn.name)
 while ob.data.uv_layers:ob.data.uv_layers.remove(ob.data.uv_layers[0])
 ob.data.uv_layers.new(name='UV0');select(ob);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(62),island_margin=.002,correct_aspect=True,scale_to_bounds=True);bpy.ops.object.mode_set(mode='OBJECT')
 uv=ob.data.uv_layers['UV0']
 for f in ob.data.polygons:
  ids=list(f.loop_indices);a,b,c=[uv.data[i].uv.copy() for i in ids];area=abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))
  if area<2e-14:
   # Preserve a valid tangent basis for subtexel bevel triangles collapsed by packing.
   centre=(a+b+c)/3;eps=.000002
   for i,delta in zip(ids,[(-eps,-eps),(eps,-eps),(0,eps)]):uv.data[i].uv=centre+Vector(delta)
 ob.data.uv_layers.new(name='UV1')
 for a,b in zip(ob.data.uv_layers['UV0'].data,ob.data.uv_layers['UV1'].data):b.uv=a.uv
 return ob
exec((P/'Tools/Saiga12KDetail/details.py').read_text(),globals())
main=join('Saiga12K_SurfaceRebuilt',objects.copy());objects=[main]
e=json.loads((P/'SourceAssets/Saiga12KMagazine20261017/Authoring/magazine.json').read_text());ext=clean(mesh('Saiga12K_Ext12_Rebuilt',e['root_positions'],e['triangles'],['ExtMagazine']*len(e['triangles'])),0.,3,False)
magazine_ribs(ext,'ExtMagazine',-17.5);magazine_detail(ext,'ExtMagazine',-17.5);ext=join('Saiga12K_Ext12_SurfaceRebuilt',[x for x in objects if x!=main])
def export(ob,key):
 me=ob.data
 for i,m in enumerate(me.materials):
  if m is None:me.materials[i]=material('ReceiverInterior')
 names=[m.name.removeprefix('Saiga12K_') for m in me.materials];uv=me.uv_layers['UV0'];payload={'positions':[[v.co.x,-v.co.y,v.co.z] for v in me.vertices],'triangles':[],'normals':[],'uv':[],'parts':[],'slot_names':names,'seated_root_cm':True};area={};uvarea={}
 for f in me.polygons:
  ids=list(f.loop_indices)[::-1];payload['triangles'].append([me.loops[i].vertex_index for i in ids]);payload['normals'].append([[me.corner_normals[i].vector.x,-me.corner_normals[i].vector.y,me.corner_normals[i].vector.z] for i in ids]);values=[[float(uv.data[i].uv.x),1-float(uv.data[i].uv.y)] for i in ids];payload['uv'].append(values);part=names[f.material_index];payload['parts'].append(part);area[part]=area.get(part,0)+f.area
  a,b,c=np.array(values);uvarea[part]=uvarea.get(part,0)+abs(float((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])))*.5
 payload['uv_per_cm']={k:math.sqrt(uvarea[k]/a) for k,a in area.items()};(O/('Authoring/'+key+'.json')).write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8')
 records.append({'key':key,'triangles':len(me.polygons),'parts':{k:payload['parts'].count(k) for k in set(payload['parts'])},'uv_per_cm':payload['uv_per_cm']})
exec((P/'Tools/Saiga12KDetail/finish_blender.py').read_text(),globals());export(main,'gun');export(ext,'ext12');ext.hide_render=True;ext.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Authoring/Saiga12K_SurfaceRebuilt.blend'),compress=True)
(O/'Receipts/geometry.json').write_text(json.dumps({'complete':True,'source_triangles':5165,'models':records,'preserved':'root cm, original grips and magazine throat, native mechanical identities; no arm edits','rebuild':'machined hard edges, rebuilt continuous barrel/gas tubes, round native receiver pins, pressed cover ribs, molded magazine ribs and grip flutes'},indent=2),encoding='utf-8');print('SAIGA_SURFACE_GEOMETRY_SAVED',[(r['key'],r['triangles']) for r in records],flush=True)
