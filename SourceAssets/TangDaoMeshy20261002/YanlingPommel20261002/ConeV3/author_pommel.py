"""One regular octagonal cone with seated, bevelled zigzag armour ribbons."""
import bpy,bmesh,json,math,sys,numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from surface_recipe import height,PANEL,frieze
NAME='SM_TangDao_Pommel_yanling_breaker_ConeV3'
MATS=['M_TangDaoYanlingConeV3_Steel','M_TangDaoYanlingConeV3_Gilt','M_TangDaoYanlingConeV3_Lacquer']
UE='/Game/Weapons/TangDao20261002/YanlingPommel20261002/ConeV3'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
verts=[];faces=[];uvfaces=[];smooths=[];mats=[]

def add(v,fs,uv=None,sm=False,mat=1):
    base=len(verts);verts.extend([tuple(p) for p in v])
    for j,f in enumerate(fs):
        faces.append([base+i for i in f]);smooths.append(sm);mats.append(mat)
        uvfaces.append(uv[j] if uv is not None else [(.52+.40*v[i][0]/.09,.58+.34*(-v[i][2]/.165)) for i in f])

def loft(rings,sm=True,mat=1,us=None,vs=None):
    n=len(rings[0]);v=[p for r in rings for p in r];fs=[list(range(n-1,-1,-1))];uv=[]
    us=us if us is not None else np.linspace(.03,.97,n,endpoint=False)
    vs=vs if vs is not None else np.linspace(.03,.46,len(rings))
    uv.append([(us[i],vs[0]) for i in fs[0]])
    for j in range(len(rings)-1):
        for i in range(n):
            k=(i+1)%n;fs.append([j*n+i,j*n+k,(j+1)*n+k,(j+1)*n+i])
            end=us[k] if k else .97
            uv.append([(us[i],vs[j]),(end,vs[j]),(end,vs[j+1]),(us[i],vs[j+1])])
    fs.append([(len(rings)-1)*n+i for i in range(n)]);uv.append([(us[i],vs[-1]) for i in range(n)])
    add(v,fs,uv,sm,mat)

# Exact original attachment, then short deterministic machined transition.
spec=json.loads((P.parents[1]/'interfaces.json').read_text(encoding='utf-8'))['parts']['pommel']
raw=spec['cut_boundary_loops_local_m'][0];n=len(raw)
center=Vector((-.0030715,.000018,0));rings=[]
lengths=[math.hypot(raw[(i+1)%n][0]-p[0],raw[(i+1)%n][1]-p[1]) for i,p in enumerate(raw)]
arc=np.r_[0,np.cumsum(lengths[:-1])]/sum(lengths)
area=sum(p[0]*raw[(i+1)%n][1]-raw[(i+1)%n][0]*p[1] for i,p in enumerate(raw))
direction=1 if area>0 else -1
a0=math.atan2((raw[0][1]-center.y)/.024882,(raw[0][0]-center.x)/.025445)
levels=[(.0015,1),(0,1),(-.0015,1.025),(-.0035,1.025),(-.0043,.98),(-.0118,.94),(-.0124,.98),(-.0145,.98),(-.0163,.86)]
for j,(z,scale) in enumerate(levels):
    q=max(0,min(1,(-z-.0015)/.0028));q=q*q*(3-2*q)
    shift=max(0,min(1,(-z-.0043)/.0102))
    rr=[]
    for i,(x,y,_) in enumerate(raw):
        a=a0+direction*2*math.pi*arc[i]
        xx=((x-center.x)*(1-q)+.025445*math.cos(a)*q)*scale+center.x*(1-shift)
        yy=((y-center.y)*(1-q)+.024882*math.sin(a)*q)*scale+center.y*(1-shift)
        rr.append((xx,yy,z))
    rings.append(rr)
loft(rings,us=.03+.94*arc)

def tube(points,width,depth,engrave=True):
    pts=[Vector(p) for p in points];nr=32;vs=[];uvs=[];fs=[]
    lengths=[(pts[(i+1)%len(pts)]-p).length for i,p in enumerate(pts)]
    arc=np.r_[0,np.cumsum(lengths[:-1])]/sum(lengths)
    for j,p in enumerate(pts):
        tangent=(pts[(j+1)%len(pts)]-pts[(j-1)%len(pts)]).normalized()
        radial=Vector((tangent.z,0,-tangent.x)).normalized()
        for k in range(nr):
            a=2*math.pi*k/nr;ca,sa=math.cos(a),math.sin(a)
            # Raised engraved clouds are part of the ring skin, not detached.
            h=float(frieze(np.asarray(arc[j]),np.asarray(k/nr))[0])*.000028 if engrave else 0
            vs.append(p+radial*(ca*(width/2+h))+Vector((0,sa*(depth/2+h),0)))
    for j in range(len(pts)):
        for k in range(nr):
            jj=(j+1)%len(pts);kk=(k+1)%nr
            fs.append([j*nr+k,j*nr+kk,jj*nr+kk,jj*nr+k])
            u=.03+.94*arc[j];un=.03+.94*arc[jj] if jj else .97
            v=.03+.43*k/nr;vn=.03+.43*(k+1)/nr
            uvs.append([(u,v),(u,vn),(un,vn),(un,v)])
    add(vs,fs,uvs,True,1)

# Compact rounded octagon follows the reference ring, not a spiky wire frame.
corners=[Vector((.0255*math.sin(math.radians(22.5+i*45)),0,-.0340+.0183*math.cos(math.radians(22.5+i*45)))) for i in range(8)]
path=[]
for j,p in enumerate(corners):
    a=p+(corners[(j-1)%8]-p).normalized()*.0032
    b=p+(corners[(j+1)%8]-p).normalized()*.0032
    for t in np.linspace(0,1,12,endpoint=False):path.append((1-t)**2*a+2*t*(1-t)*p+t*t*b)
tube(path,.0072,.0108)
for y in [-.00455,.00455]:tube([(p[0],y,p[2]) for p in path],.00085,.00085,False)

BASE_Z=-.0550;TIP_Z=-.1630;R=.0356
base=[Vector((R*math.cos(math.radians(22.5+i*45)),R*math.sin(math.radians(22.5+i*45)),BASE_Z)) for i in range(8)]
tip=Vector((0,0,TIP_Z))
def plane(k,s,t,off=0):
    a,b=base[k],base[(k+1)%8]
    normal=(b-a).cross(tip-a).normalized()
    if normal.dot(Vector((a.x,a.y,0)))<0:normal=-normal
    return (a*(1-s)+b*s)*(1-t)+tip*t+normal*off,normal

# Wide end directly against ring. All eight faces are planar triangles that
# taper strictly to the single apex; no second shoulder or diamond belly.
body=[];ff=[];uu=[];norms=[];N=144
for k in range(8):
    start=len(body);rows=[]
    for r in range(N+1):
        count=N-r;row=[]
        for c in range(count+1):
            s=c/count if count else .5;t=r/N
            h=float(height(np.asarray(s),np.asarray(t))) if .035<t<.59 else 0
            p,normal=plane(k,s,t,h);row.append(len(body));body.append(tuple(p));norms.append(normal)
        rows.append(row)
    for r in range(N):
        m=N-r
        for c in range(m):
            f=[rows[r][c],rows[r][c+1],rows[r+1][c]];ff.append(f)
            uv=[(c/m,1-r/N),((c+1)/m,1-r/N),(c/(m-1) if m>1 else .5,1-(r+1)/N)];uu.append(uv)
            if c<m-1:
                f=[rows[r][c+1],rows[r+1][c+1],rows[r+1][c]];ff.append(f)
                uu.append([((c+1)/m,1-r/N),((c+1)/(m-1),1-(r+1)/N),(c/(m-1),1-(r+1)/N)])
add(body,ff,uu,True,0)
# Closed back face has the same perimeter vertices/samples as cone faces.
cap=[]
for k in range(8):
    for c in range(N):cap.append(tuple(plane(k,c/N,0)[0]))
cap.append((0,0,BASE_Z));nc=len(cap)-1
add(cap,[[i,(i+1)%nc,nc] for i in range(nc)],sm=False,mat=0)

def offset(poly,d):
    area=sum(p[0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*p[1] for i,p in enumerate(poly))
    pts=[Vector(p) for p in poly];sign=1 if area>0 else -1;out=[]
    for i,p in enumerate(pts):
        a=(p-pts[i-1]).normalized();b=(pts[(i+1)%len(pts)]-p).normalized()
        na=Vector((a.y,-a.x))*sign;nb=Vector((b.y,-b.x))*sign
        q=(na+nb).normalized();factor=min(2.6,1/max(.25,q.dot(na)))
        out.append(p+q*(d*factor))
    return out

def ribbon(k,poly,width=.0029,depth=.0016,lift=.00012):
    # Closed bevelled extrusion in the actual facet plane, continuous around
    # every miter. It replaces disconnected rectangular/tube shield segments.
    a,b=base[k],base[(k+1)%8];ex=(b-a).normalized();normal=plane(k,.5,.2)[1];ey=normal.cross(ex).normalized()
    points=[plane(k,s,t)[0] for s,t in poly]
    polygon=[((p-a).dot(ex),(p-a).dot(ey)) for p in points]
    rings=[];bevel=.00032
    for d,z in [(width/2,lift),(width/2,lift+depth-bevel),(width/2-bevel,lift+depth),(-width/2+bevel,lift+depth),(-width/2,lift+depth-bevel),(-width/2,lift)]:
        rings.append([a+ex*p.x+ey*p.y+normal*z for p in offset(polygon,d)])
    n=len(poly);v=[p for ring in rings for p in ring];fs=[]
    for j in range(len(rings)):
        jj=(j+1)%len(rings)
        for i in range(n):fs.append([j*n+i,j*n+(i+1)%n,jj*n+(i+1)%n,jj*n+i])
    add(v,fs,sm=False,mat=1)

for k in range(8):
    ribbon(k,PANEL)
    # Rear pierced crown tabs are thick, supported chevrons seated on facets.
    if k%2==0:ribbon(k,[(.20,.01),(.80,.01),(.72,.12),(.50,.165),(.28,.12)],.00225,.0014,.00165)

# Machined polygonal cap supports the full cone base, with bright bevel edges.
caprings=[]
for z,r in [(BASE_Z+.0032,R*.94),(BASE_Z+.0014,R*1.013),(BASE_Z-.0004,R*1.013),(BASE_Z-.002,R*.975)]:
    caprings.append([(r*math.cos(math.radians(22.5+i*45)),r*math.sin(math.radians(22.5+i*45)),z) for i in range(8)])
loft(caprings,sm=False,vs=[.62,.66,.69,.73])

# Small red lacquer lozenges use a dielectric surface with an actual gold rim.
for sign in [-1,1]:
    y=sign*.0244
    diamond=[(-.0043,y,-.0075),(0,y,-.0040),(.0043,y,-.0075),(0,y,-.0110)]
    loft([diamond,[(x,yy+sign*.00030,z) for x,yy,z in diamond]],sm=False,mat=2)
    ex=Vector((1,0,0));ey=Vector((0,0,1));origin=Vector((0,y+sign*.00034,0));normal=Vector((0,sign,0))
    polygon=[(p[0],p[2]) for p in diamond];rings=[]
    for d,z in [(.00035,0),(.00035,.00022),(-.00035,.00022),(-.00035,0)]:
        rings.append([origin+ex*p.x+ey*p.y+normal*z for p in offset(polygon,d)])
    n=4;v=[p for ring in rings for p in ring];fs=[]
    for j in range(4):
        for i in range(n):fs.append([j*n+i,j*n+(i+1)%n,((j+1)%4)*n+(i+1)%n,((j+1)%4)*n+i])
    add(v,fs,sm=False,mat=1)

mesh=bpy.data.meshes.new(NAME);mesh.from_pydata(verts,[],faces);mesh.update();layer=mesh.uv_layers.new(name='UVMap')
for poly,uvs in zip(mesh.polygons,uvfaces):
    poly.use_smooth=smooths[poly.index];poly.material_index=mats[poly.index]
    for loop,co in zip(poly.loop_indices,uvs):layer.data[loop].uv=co
bm=bmesh.new();bm.from_mesh(mesh)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00000020)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
for e in bm.edges:
    if e.is_manifold and e.calc_face_angle()>.58:e.smooth=False
bm.to_mesh(mesh);bm.free();mesh.update()
for family,name in zip(['Steel','Gilt','Lacquer'],MATS):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;nt=mat.node_tree
    bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
    for key in ['BaseColor','ORM','Normal']:
        im=bpy.data.images.load(str(P/'Textures'/f'TangDao_YanlingConeV3_{family}_{key}.png'))
        im.colorspace_settings.name='sRGB' if key=='BaseColor' else 'Non-Color'
        node=nt.nodes.new('ShaderNodeTexImage');node.image=im
        if key=='BaseColor':nt.links.new(node.outputs[0],bs.inputs['Base Color'])
        elif key=='ORM':
            sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(node.outputs[0],sep.inputs[0]);nt.links.new(sep.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
        else:
            nm=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(node.outputs[0],nm.inputs['Color']);nt.links.new(nm.outputs[0],bs.inputs['Normal'])
    mesh.materials.append(mat)
obj=bpy.data.objects.new(NAME+'_LOD0',mesh);bpy.context.scene.collection.objects.link(obj);obj.select_set(True);bpy.context.view_layer.objects.active=obj
mod=obj.modifiers.new('Manufactured edge micro bevels','BEVEL');mod.width=.00012;mod.segments=2;mod.limit_method='ANGLE';mod.angle_limit=.78;bpy.ops.object.modifier_apply(modifier=mod.name)
mod=obj.modifiers.new('Planar facets and smooth machined ring','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=25;bpy.ops.object.modifier_apply(modifier=mod.name)
group=bpy.data.objects.new(NAME+'_LODGroup',None);group['fbx_type']='LodGroup';bpy.context.scene.collection.objects.link(group);obj.parent=group;lods=[obj]
for level,ratio in [(1,.52),(2,.23)]:
    lod=obj.copy();lod.data=obj.data.copy();bpy.context.scene.collection.objects.link(lod);lod.name=NAME+'_LOD'+str(level);bpy.context.view_layer.objects.active=lod
    dec=lod.modifiers.new('Distance LOD','DECIMATE');dec.ratio=ratio;bpy.ops.object.modifier_apply(modifier=dec.name);lods.append(lod)
bpy.ops.object.select_all(action='DESELECT');group.select_set(True)
for lod in lods:lod.select_set(True)
bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(NAME+'.fbx')),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False,mesh_smooth_type='FACE',use_tspace=True)
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(P/'Export'/(NAME+'.glb')),use_selection=True,export_format='GLB')
for lod in lods[1:]:lod.hide_set(True);lod.hide_render=True
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'TangDao_YanlingConeV3_Editable.blend'))
counts=[]
for lod in lods:lod.data.calc_loop_triangles();counts.append(len(lod.data.loop_triangles))
appearance='环侧宽端直接收向尖端的八面锥；连续折线鎏金甲框、后段小型龙云浮雕、锻钢水波纹与磨亮棱线。'
m={'id':'yanling_breaker','name':'破锋燕翎配重锤','weapon':'ue_tang_dao','slot':'pommel','interface':'tang_dao_hilt_v1',
 'ue_root':UE,'mesh_name':NAME,'mesh':UE+'/Meshes/'+NAME+'.'+NAME,'materials':{name:UE+'/Materials/'+name+'.'+name for name in MATS},
 'location_cm':[0,0,-22.7],'rotation_deg':[0,0,0],'scale':[1,1,1],'lod_triangles':counts,
 'length_cm':16.45,'head_base_diameter_cm':7.12,'cone_base_z_cm':BASE_Z*100,'cone_tip_z_cm':TIP_Z*100,
 'cone_profile':'regular octagonal planar cone; maximum width at ring-side base, monotonic taper to one apex',
 'relief_height_mm':[.14,.27],'pbr_resolution':{'Steel':4096,'Gilt':4096,'Lacquer':512},'source_revision':'ConeV3',
 'revision':'TangDaoYanlingPommelConeV3_20261002','appearance':appearance,
 'effects_text':['八面收尖锥体 · 连续折线鎏金甲框','后段龙云浮雕 · 分区锻钢与古金材质'],
 'features':['单一八面收尖锥形','紧凑圆角八角环','连续倒角折线甲框','贴面镂空冠饰','后段小型龙云实体浮雕','钢层水波微刻','分材质反光与粗糙度','原握柄精确安装座'],
 'stats':{},'runtime_tested':False}
(P/'pommel_manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('YANLING_CONE_V3_AUTHORED '+str(counts),flush=True)
