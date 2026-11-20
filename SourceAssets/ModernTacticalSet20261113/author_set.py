"""Tactical System 01: isolated native-scale Blender authoring, no rendering/tests.

Run in Blender background with -- part (vest, helmet, gloves, pants, boots, assembly).
Centimetre UE coordinates are reflected in Y and converted to metres on creation.
Existing fit foundations are read only. All output belongs to this task directory.
"""
import bpy, bmesh, json, math, sys, hashlib
from pathlib import Path
from collections import defaultdict
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
for folder in ['Models','Exports','Textures','SurfaceSources','Receipts']:
    (ROOT/folder).mkdir(exist_ok=True)
PART=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'vest'
SOURCES={}
def read(path):
    path=Path(path); raw=path.read_bytes(); SOURCES[str(path)]=hashlib.sha256(raw).hexdigest()
    return json.loads(raw.decode('utf-8-sig'))
def unit(v):
    v=np.array(v,dtype=float);return v/max(np.linalg.norm(v),1e-12)
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def uvpt(p):return (float(p[0])*.01,-float(p[1])*.01,float(p[2])*.01)
def nativept(p):return np.array([p[0]*100,-p[1]*100,p[2]*100])
def write_json(path,data):Path(path).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

PALETTE={
 'RangerNylon':([.49,.375,.268],.78,'weave'),
 'RangerRipstop':([.54,.421,.301],.84,'ripstop'),
 'CharcoalStretch':([.347,.257,.181],.86,'weave'),
 'CharcoalLeather':([.289,.210,.154],.60,'leather'),
 'MattePolymer':([.323,.259,.200],.62,'polymer'),
 'OliveComposite':([.515,.399,.291],.73,'polymer'),
 'BlackRubber':([.170,.144,.119],.80,'rubber'),
 'OliveWebbing':([.421,.319,.223],.85,'webbing'),
 'StitchThread':([.591,.469,.344],.86,'thread'),
 'Gunmetal':([.182,.170,.155],.44,'metal')}

def save_map(path,values,color=False):
    values=np.asarray(values,np.float32)
    if color:values=np.where(values<=.04045,values/12.92,((values+.055)/1.055)**2.4)
    if values.ndim==2:values=np.repeat(values[:,:,None],3,axis=2)
    h,w,_=values.shape
    pixels=np.ones((h,w,4),np.float32);pixels[:,:,:3]=np.clip(values[:,:,:3],0,1)
    img=bpy.data.images.new(path.stem,width=w,height=h,alpha=False,float_buffer=False)
    img.colorspace_settings.name='sRGB' if color else 'Non-Color'
    img.pixels.foreach_set(pixels.ravel());img.filepath_raw=str(path);img.file_format='PNG';img.save()
    bpy.data.images.remove(img)

def surface_maps():
    # Existing green maps and these warm earth materials use the same UE paths.
    revision=ROOT/'Textures'/'earth-brown-v3-srgb.json'
    if revision.is_file():return
    size=1024
    yy,xx=np.mgrid[0:size,0:size].astype(np.float32);x=xx/size;y=yy/size
    # Periodic analytic fields: the same field drives microheight and normal.
    noise=sum(np.sin(2*math.pi*(a*x+b*y)+c)*w for a,b,c,w in [(17,11,.2,.23),(31,-21,1.3,.16),(93,53,.7,.08),(173,-121,2.4,.035)])
    for key,(color,rough,kind) in PALETTE.items():
        freq=96 if kind!='webbing' else 128
        warp=2*math.pi*x*freq+.20*np.sin(2*math.pi*(5*y+2*x))
        weft=2*math.pi*y*freq+.24*np.sin(2*math.pi*(3*x-2*y))
        weave=.63*np.cos(warp)*np.cos(weft)+.24*np.cos(2*warp)+.13*np.cos(2*weft)
        h=.0015*noise
        if kind in ['weave','ripstop','webbing','thread']:
            h+=.00165*weave+.00032*np.sin(2*warp)
            if kind=='webbing':h+=.003*np.cos(2*math.pi*x*32)
            if kind=='ripstop':
                grids=np.exp(-(np.sin(math.pi*x*12)/.12)**2)+np.exp(-(np.sin(math.pi*y*12)/.12)**2)
                h+=.0021*grids
        elif kind=='leather':h+=.004*np.sin(2*math.pi*x*83+np.sin(2*math.pi*y*37))*np.sin(2*math.pi*y*71+np.sin(2*math.pi*x*29))
        elif kind in ['polymer','rubber']:h+=.001*np.sin(2*math.pi*(x*157+y*103))
        elif kind=='metal':h+=.0005*np.sin(2*math.pi*x*211)
        dx=(np.roll(h,-1,axis=1)-np.roll(h,1,axis=1))/(2*8/size)
        dy=(np.roll(h,-1,axis=0)-np.roll(h,1,axis=0))/(2*8/size)
        normals=np.stack([-dx,-dy,np.ones_like(h)],axis=2);normals/=np.linalg.norm(normals,axis=2)[:,:,None]
        base=np.array(color)[None,None,:]*(1+noise[:,:,None]*.10+weave[:,:,None]*(.022 if kind in ['weave','ripstop','webbing'] else .003))
        roughness=np.clip(rough+noise*.045,0,1);metal=np.full_like(h,1 if kind=='metal' else 0)
        occlusion=np.clip(.97+noise*.025,0,1)
        save_map(ROOT/'Textures'/f'{key}_BaseColor.png',base,True)
        save_map(ROOT/'Textures'/f'{key}_NormalGL.png',normals*.5+.5)
        save_map(ROOT/'Textures'/f'{key}_Roughness.png',roughness)
        save_map(ROOT/'Textures'/f'{key}_Metallic.png',metal)
        save_map(ROOT/'Textures'/f'{key}_ORM.png',np.stack([occlusion,roughness,metal],axis=2))
        np.savez_compressed(ROOT/'SurfaceSources'/f'{key}_height_cm.npz',height_cm=h,span_cm=8.0)
        print('SURFACE_SAVED',key,flush=True)
    write_json(revision,{'palette':'earth brown','tile_cm':8})

def materials():
    result={}
    for key,(col,rough,kind) in PALETTE.items():
        m=bpy.data.materials.new('TS01_'+key);m.use_nodes=True;m.diffuse_color=(*col,1)
        nodes=m.node_tree.nodes;links=m.node_tree.links;bs=nodes.get('Principled BSDF')
        for channel in ['BaseColor','NormalGL','Roughness','Metallic']:
            tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(ROOT/'Textures'/f'{key}_{channel}.png'),check_existing=True)
            if channel!='BaseColor':tex.image.colorspace_settings.name='Non-Color'
            if channel=='NormalGL':
                normal=nodes.new('ShaderNodeNormalMap');links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs[0],bs.inputs['Normal'])
            else:links.new(tex.outputs['Color'],bs.inputs[{'BaseColor':'Base Color','Roughness':'Roughness','Metallic':'Metallic'}[channel]])
        if kind in ['weave','ripstop','webbing','thread']:bs.inputs['Sheen Weight'].default_value=.12
        m['PhysicalTile_cm']=8.0;m['NormalConvention']='OpenGL; flip green for Unreal';result[key]=m
    return result

def rig_from(bones):
    arm=bpy.data.armatures.new('Jason_NativeRig_TS01');rig=bpy.data.objects.new(arm.name,arm);bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    reflect=Matrix.Diagonal((1,-1,1))
    for b in bones:
        eb=arm.edit_bones.new(b['name']);axes=Matrix(b['axes']).transposed()
        for i in range(3):axes.col[i]=axes.col[i].normalized()
        mat=(reflect@axes@reflect).to_4x4();mat.translation=Vector(uvpt(b['position']));eb.matrix=mat;eb.length=.025
    names={b['index']:b['name'] for b in bones}
    for b in bones:
        if b['parent'] in names:arm.edit_bones[b['name']].parent=arm.edit_bones[names[b['parent']]]
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False);rig.show_in_front=False;rig.display_type='WIRE'
    return rig

class WeightSurface:
    def __init__(self,data,faces=None):
        self.p=np.asarray(data['positions']);self.f=np.asarray(data['triangles'] if faces is None else faces,dtype=np.int32);self.w=data['weights']
        self.tree=BVHTree.FromPolygons(self.p.tolist(),self.f.tolist(),all_triangles=True)
    def weights(self,p):
        q,n,fi,dist=self.tree.find_nearest(Vector(p));ids=self.f[fi];a,b,c=self.p[ids]
        v0=b-a;v1=c-a;v2=np.array(q)-a;den=(v0@v0)*(v1@v1)-(v0@v1)**2
        if abs(den)<1e-12:coeff=[1,0,0]
        else:
            v=((v1@v1)*(v2@v0)-(v0@v1)*(v2@v1))/den;w=((v0@v0)*(v2@v1)-(v0@v1)*(v2@v0))/den
            coeff=np.clip([1-v-w,v,w],0,1);coeff/=sum(coeff)
        out=defaultdict(float)
        for vi,fac in zip(ids,coeff):
            for bi,w in self.w[int(vi)]:out[int(bi)]+=float(w*fac)
        pairs=sorted(out.items(),key=lambda q:-q[1])[:8];total=sum(w for _,w in pairs)
        return [(bi,w/total) for bi,w in pairs if w>1e-7]

def set_weights(ob,weights):
    ids={bi for ws in weights for bi,w in ws};groups={bi:ob.vertex_groups.new(name=BONES[bi]['name']) for bi in ids}
    for i,ws in enumerate(weights):
        for bi,w in ws:groups[bi].add([i],float(w),'REPLACE')
    ob.parent=RIG;mod=ob.modifiers.new('NativeSkeleton','ARMATURE');mod.object=RIG

def bind(ob,source=None,bone=None):
    if bone is not None:ws=[[(BONE_IDS[bone],1.)]]*len(ob.data.vertices)
    elif PART=='vest':ws=[carrier_weights(nativept(v.co)) for v in ob.data.vertices]
    else:ws=[(source or BODY_SURFACE).weights(nativept(v.co)) for v in ob.data.vertices]
    set_weights(ob,ws)

def apply(ob,name):
    bpy.context.view_layer.objects.active=ob;ob.select_set(True);bpy.ops.object.modifier_apply(modifier=name);ob.select_set(False)

def mesh(name,points,faces,material,thickness=0,bevel=0,bone=None,source=None,do_bind=True,recalc=True,outward=None,radial_center=None):
    data=bpy.data.meshes.new(name);data.from_pydata([uvpt(p) for p in points],[],faces);data.update();ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob)
    data.materials.append(MATS[material])
    if recalc:
        bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        if outward is not None:
            direction=Vector((outward[0],-outward[1],outward[2]))
            if sum(f.normal.dot(direction)*f.calc_area() for f in bm.faces)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
        if radial_center is not None:
            center=Vector(uvpt(radial_center))
            if sum(f.normal.dot(f.calc_center_median()-center)*f.calc_area() for f in bm.faces)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
        bm.to_mesh(data);bm.free()
    for poly in data.polygons:poly.use_smooth=True
    # Object-space planar projection in centimetres, one UV repeat = 8 cm.
    uv=data.uv_layers.new(name='Physical8cm')
    for poly in data.polygons:
        dominant=max(range(3),key=lambda i:abs(poly.normal[i]));axes=[i for i in range(3) if i!=dominant]
        for li in poly.loop_indices:
            p=nativept(data.vertices[data.loops[li].vertex_index].co);uv.data[li].uv=(p[axes[0]]/8,p[axes[1]]/8)
    if thickness:
        mod=ob.modifiers.new('ActualMaterialThickness','SOLIDIFY');mod.thickness=thickness*.01;mod.offset=-1;mod.use_even_offset=False;apply(ob,mod.name)
    if bevel:
        mod=ob.modifiers.new('ManufacturedSoftEdges','BEVEL');mod.width=bevel*.01;mod.segments=3;apply(ob,mod.name)
    if do_bind:bind(ob,source,bone)
    OBJECTS.append(ob);return ob

def grid(name,fn,nu,nv,mat,**kwargs):
    pts=[fn(i/nu,j/nv) for j in range(nv+1) for i in range(nu+1)];faces=[]
    for j in range(nv):
        for i in range(nu):a=j*(nu+1)+i;faces.append([a,a+1,a+nu+2,a+nu+1])
    return mesh(name,pts,faces,mat,**kwargs)

def tube(name,path,radius,mat,sides=6,closed=False,bone=None,source=None):
    path=np.asarray(path);path=path[np.r_[True,np.linalg.norm(np.diff(path,axis=0),axis=1)>1e-5]]
    if closed and np.linalg.norm(path[0]-path[-1])<1e-5:path=path[:-1]
    n=len(path);pts=[];previous=None
    for i,p in enumerate(path):
        tangent=unit(path[(i+1)%n]-path[(i-1)%n]) if closed else unit(path[min(i+1,n-1)]-path[max(i-1,0)])
        axis=np.array([0,0,1.]) if abs(tangent[2])<.94 else np.array([0,1.,0])
        u=unit(np.cross(tangent,axis)) if previous is None else unit(previous-tangent*np.dot(previous,tangent))
        if np.linalg.norm(u)<.5:u=unit(np.cross(tangent,axis))
        v=np.cross(tangent,u);previous=u
        for k in range(sides):pts.append(p+radius*(u*math.cos(math.tau*k/sides)+v*math.sin(math.tau*k/sides)))
    faces=[]
    for i in range(n if closed else n-1):
        for k in range(sides):faces.append([i*sides+k,i*sides+(k+1)%sides,((i+1)%n)*sides+(k+1)%sides,((i+1)%n)*sides+k])
    if not closed:faces.extend([list(reversed(range(sides))),list(range((n-1)*sides,n*sides))])
    return mesh(name,pts,faces,mat,bone=bone,source=source)

def box(name,center,size,mat,bevel=.15,basis=None,bone=None,source=None):
    basis=np.eye(3) if basis is None else np.asarray(basis);center=np.asarray(center)
    pts=[center+basis@np.array([x*size[0]*.5,y*size[1]*.5,z*size[2]*.5]) for x in [-1,1] for y in [-1,1] for z in [-1,1]]
    return mesh(name,pts,[[0,1,3,2],[4,6,7,5],[0,4,5,1],[2,3,7,6],[0,2,6,4],[1,5,7,3]],mat,bevel=bevel,bone=bone,source=source)

def stitch(name,path,source=None,bone=None,pitch=.30):
    path=np.asarray(path);dist=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))];length=dist[-1]
    if length<.05:return
    points=[];faces=[]
    for start in np.arange(0,length-pitch*.9,pitch):
        arc=np.linspace(start,start+pitch*.60,4);line=np.array([[np.interp(a,dist,path[:,k]) for k in range(3)] for a in arc]);first=len(points)
        for j,q in enumerate(line):
            tangent=unit(line[min(j+1,3)]-line[max(j-1,0)]);u=unit(np.cross(tangent,[0,0,1] if abs(tangent[2])<.95 else [0,1,0]));v=np.cross(tangent,u)
            for k in range(4):points.append(q+.025*(u*math.cos(k*math.pi/2)+v*math.sin(k*math.pi/2)))
        for j in range(3):
            for k in range(4):faces.append([first+j*4+k,first+j*4+(k+1)%4,first+(j+1)*4+(k+1)%4,first+(j+1)*4+k])
    if points:mesh(name,points,faces,'StitchThread',source=source,bone=bone)

def native_mesh(name,d,material_map,weights=None,face_filter=None):
    points=np.array(d['positions']);faces=np.array(d['triangles']);indices=np.arange(len(faces)) if face_filter is None else np.flatnonzero(face_filter)
    used=np.unique(faces[indices]);remap=np.full(len(points),-1,np.int32);remap[used]=np.arange(len(used))
    data=bpy.data.meshes.new(name);data.from_pydata([uvpt(p) for p in points[used]],[],remap[faces[indices]].tolist());data.update();ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob)
    keys=list(dict.fromkeys(material_map.values()))
    for k in keys:data.materials.append(MATS[k])
    uv=data.uv_layers.new(name='Physical8cm')
    mats=d.get('triangle_materials',[0]*len(faces))
    for poly,fi in zip(data.polygons,indices):
        poly.material_index=keys.index(material_map.get(mats[fi],keys[0]));poly.use_smooth=True
        dominant=max(range(3),key=lambda i:abs(poly.normal[i]));ax=[i for i in range(3) if i!=dominant]
        for corner,li in enumerate(poly.loop_indices):
            if fi<d.get('authored_cloth_faces',0):
                uv.data[li].uv=d['uv'][fi][corner]
            else:
                p=points[used[data.loops[li].vertex_index]];uv.data[li].uv=(p[ax[0]]/8,p[ax[1]]/8)
    if 'normals' in d:
        data.normals_split_custom_set([(n[0],-n[1],n[2]) for fi in indices for n in d['normals'][int(fi)]])
    ws=d['weights'] if weights is None else weights;set_weights(ob,[ws[int(i)] for i in used])
    OBJECTS.append(ob);return ob

# Jason trunk sections, with the abducted arms excluded. Surface coordinates
# continue around each flank so that overlapping sew lines share one shape.
TRUNK_Z=[102,105,108,111,114,117,120,123,126,129,132,135,138,141,144]
TRUNK_X=[14.3,13.9,13.6,13.7,14.0,14.3,14.8,15.4,16.0,16.5,16.5,16.7,17.9,18.0,17.3]
FRONT_Y=[13.94,13.81,13.85,13.98,13.95,13.72,13.39,13.24,13.34,13.13,12.29,10.84,9.03,5.36,2.60]
REAR_Y=[-7.14,-6.77,-6.87,-7.19,-7.58,-8.06,-8.49,-9.01,-10.01,-10.89,-11.13,-11.29,-11.23,-10.85,-10.13]

def section(z):
    radius=np.interp(z,TRUNK_Z,TRUNK_X)+1.6
    near=np.interp(z,TRUNK_Z,FRONT_Y);far=np.interp(z,TRUNK_Z,REAR_Y)
    return radius,(near+far)*.5,(near-far)*.5

def carrier_weights(point):
    x,y,z=point
    if 'CARRIER_SURFACE' in globals():
        if z>139:
            anchor=point
        else:
            side=1 if y>section(z)[1] else -1
            anchor=[x,CARRIER_SURFACE.front(x,z,side),z]
        return BODY_SURFACE.weights(anchor)
    levels=[90.4,97.3,105.1,114.1,133.9]
    high=min(4,max(1,int(np.searchsorted(levels,z))))
    t=float(smooth(levels[high-1],levels[high],z))
    shoulder=.34*float(smooth(134,145,z)*smooth(6,14,abs(x)))
    pairs=[(BONE_IDS[f'spine_{high:02d}'],(1-t)*(1-shoulder)),
           (BONE_IDS[f'spine_{high+1:02d}'],t*(1-shoulder)),
           (BONE_IDS['clavicle_l' if x>0 else 'clavicle_r'],shoulder)]
    return [(i,w) for i,w in pairs if w>1e-7]

def front(x,z,side=1,offset=1.6):
    if 'CARRIER_SURFACE' in globals():return CARRIER_SURFACE.carrier(x,z,side,offset)
    rx,cy,ry=section(z)
    t=min(abs(x)/rx,.985)
    base_offset=1.7 if 'CARRIER_SURFACE' in globals() else offset
    y=cy+side*(ry+base_offset)*(1-t**2.6)**(1/2.6)
    if 'CARRIER_SURFACE' in globals():
        y=side*max(side*y,side*CARRIER_SURFACE.front(x,z,side)+CARRIER_SURFACE.front_clearance(x,z,side,base_offset))
    p=np.array([x,y,z])
    if 'CARRIER_SURFACE' in globals():
        p=CARRIER_SURFACE.project(p,1.85)
        p+=CARRIER_SURFACE.normal(p)*(offset-base_offset)
    return p

def torso(theta,z,offset=1.3):
    rx,cy,ry=section(z);s=math.sin(theta);c=math.cos(theta)
    p=np.array([(rx+offset-1.6)*math.copysign(abs(s)**(2/2.6),s),
                cy+(ry+offset)*math.copysign(abs(c)**(2/2.6),c),z])
    return CARRIER_SURFACE.flank(p,offset+.35) if 'CARRIER_SURFACE' in globals() else p

def build_vest():
    global CARRIER_SURFACE
    sys.path.insert(0,str(ROOT))
    from carrier_surface import CarrierSurface
    CARRIER_SURFACE=CarrierSurface(BODY)
    for side,label in [(1,'Front'),(-1,'Rear')]:
        def panel(u,v):
            a=u*2-1;top=137.5+3.8*abs(a)**1.6;z=103.8+(top-103.8)*v
            half=min(section(z)[0]*.92,np.interp(z,[103,117,126,136,142],[16.,16.,15.9,11.7,11.2]));x=a*half
            p=front(x,z,side,1.7);p[1]+=side*.15*math.sin(v*math.pi)*math.sin(u*math.pi);return p
        grid(f'Vest_{label}_ShapedCarrier',panel,40,44,'RangerNylon',thickness=1.15,outward=(0,side,0))
        boundary=[panel(u,0) for u in np.linspace(0,1,48)]+[panel(1,v) for v in np.linspace(0,1,45)]+[panel(u,1) for u in np.linspace(1,0,48)]+[panel(0,v) for v in np.linspace(1,0,45)]
        tube('BoundEdge_'+label,boundary,.22,'OliveWebbing',8,True)
        for edge in [0,1]:stitch('PanelStitch_'+label+str(edge),[panel(edge*.97+.015,v)+[0,side*.14,0] for v in np.linspace(.02,.98,85)])
        # Each separated webbing cell leaves a genuine opening for attachment.
        rows=[121.8,125.7,129.6] if side==1 else [108,112,116,120,124,128]
        for ri,z in enumerate(rows):
            for ci,x in enumerate(np.arange(-12,13,4.0)):
                if z>128 and abs(x)>10:continue
                grid(f'MOLLE_{label}_{ri}_{ci}',lambda u,v,x=x,z=z:front(x+(u-.5)*3.85,z+(v-.5)*2.20,side,2.10+.18*math.sin(math.pi*u)),8,3,'OliveWebbing',thickness=.11,outward=(0,side,0))
                for end in [-1,1]:
                    stitch(f'MOLLE_Bartack_{label}_{ri}_{ci}_{end}',[front(x+end*1.72,z+t,side,2.18) for t in np.linspace(-.94,.94,16)],pitch=.18)
        grid('LoopPatch_'+label,lambda u,v:front((u-.5)*13,132.5+v*3.3,side,2.35),32,12,'CharcoalStretch',thickness=.10,outward=(0,side,0))
    for s in [-1,1]:
        grid('SoftArmor_Cummerbund_'+str(s),lambda u,v:torso(s*(.78+1.60*u),104.7+v*13.2,1.4),48,16,'RangerNylon',thickness=.85,radial_center=(0,1.5,111))
        for z in [107.0,111,115]:
            grid('SideWebbing_'+str((s,z)),lambda u,v,z=z:torso(s*(.76+1.64*u),z+(v-.5)*2.25,1.62),52,3,'OliveWebbing',thickness=.1,radial_center=(0,1.5,z))
        # Broad continuous shoulder bridge and padded contact underside.
        bridge=CARRIER_SURFACE.strap(s)
        grid('ShoulderStrap_'+str(s),bridge,10,38,'OliveWebbing',thickness=.45,outward=(0,0,1))
        def padding(u,v):
            t=.08+.84*v;q=bridge(.06+.88*u,t);return q-np.array([0,math.cos(math.pi*t),math.sin(math.pi*t)])*.46
        grid('ShoulderSpacerPad_'+str(s),padding,10,34,'CharcoalStretch',thickness=.3,outward=(0,0,1))
        for u in [.08,.92]:stitch('ShoulderStitch_'+str((s,u)),[bridge(u,v)+[0,0,.1] for v in np.linspace(.02,.98,90)])
        center=front(s*10.8,137.4,1,2.45)
        # Open buckle perimeter, crossbar and separate release tongue.
        for x in [-2.15,2.15]:box('QuickReleaseSide_'+str((s,x)),center+[x,.15,0],[.65,.65,5.1],'MattePolymer',.16)
        for z in [-2.2,2.2]:box('QuickReleaseBar_'+str((s,z)),center+[0,.15,z],[4.6,.65,.65],'MattePolymer',.16)
        box('ReleaseTongue_'+str(s),center+[0,.42,0],[2.8,.45,2.2],'MattePolymer',.18)
    for i,x in enumerate([-8.9,0,8.9]):
        # Closed, rounded fabric bellows conform to the same curved front panel.
        rings=[];faces=[];segments=40
        for z,width,depth in [(104.3,3.4,1.9),(104.8,3.9,2.7),(106,4.13,3.0),(113,4.2,3.15),(117.7,4.1,2.9),(118.4,3.85,2.55)]:
            for j in range(segments):
                a=math.tau*j/segments;s=math.sin(a);c=math.cos(a)
                px=x+width*math.copysign(abs(s)**.48,s)
                rings.append(front(px,z,1,1.85+depth*(1+math.copysign(abs(c)**.54,c))*.5))
        for j in range(5):
            for k in range(segments):
                a=j*segments+k;b=j*segments+(k+1)%segments;faces.append([a,b,b+segments,a+segments])
        faces.extend([list(reversed(range(segments))),list(range(5*segments,6*segments))])
        mesh('FabricBellows_'+str(i),rings,faces,'RangerNylon')
        def flap(u,v):
            a=2*u-1;z=114.25+.70*abs(a)**2+v*(4.85-.70*abs(a)**2)
            return front(x+a*(4.17-.18*(1-v)**3),z,1,4.94+.32*math.sin(v*math.pi))
        grid('RoundedPocketFlap_'+str(i),flap,24,12,'RangerRipstop',thickness=.16,outward=(0,1,0))
        stitch('FlapTopstitch_'+str(i),[flap(u,.065)+[0,.035,0] for u in np.linspace(.035,.965,42)])
        for edge in [.04,.96]:
            stitch('FlapSideTopstitch_'+str((i,edge)),[flap(edge,v)+[0,.04,0] for v in np.linspace(.05,.95,36)])
        for edge in [-1,1]:
            stitch('BellowsFold_'+str((i,edge)),[front(x+edge*3.85,z,1,4.65) for z in np.linspace(105.2,114.2,40)],pitch=.27)
        tube('PocketMouthBinding_'+str(i),[front(x+u*3.85,118.4,1,3.1) for u in np.linspace(-1,1,40)],.09,'OliveWebbing',8)
        grid('FoldedPullTab_'+str(i),lambda u,v:front(x+(u-.5)*1.4,113.1+2*v,1,5.05+.22*math.sin(math.pi*v)),6,10,'OliveWebbing',thickness=.14,outward=(0,1,0))
    def handle(u,v):
        arch=math.sin(math.pi*v)
        return front(14*v-7,135+1.5*arch+(u-.5)*2.2,-1,2.6+1.2*arch)
    grid('RearDragHandle',handle,4,36,'OliveWebbing',thickness=.30,outward=(0,-1,0))

def build_helmet():
    head=read(PROJECT/'SourceAssets/JasonPlayer20261003/head_geometry.json');hp=np.array(head['positions']);upper=hp[(hp[:,2]>163)&(hp[:,2]<175.5)]
    rx=max(abs(upper[:,0]).max()+1.1,10.4);cy=(np.percentile(upper[:,1],98)+np.percentile(upper[:,1],2))*.5;ry=(np.percentile(upper[:,1],98)-np.percentile(upper[:,1],2))*.5+1.5
    ry=max(ry,12.5);cz=165.8;rz=max(hp[:,2].max()+1.15-cz,10.7)
    def shell(theta,t):
        edge=164.4+2.0*abs(math.sin(theta))**5-4.2*max(0,-math.cos(theta))**2
        phi=.0001+(math.acos(np.clip((edge-cz)/rz,-1,1))-.0001)*t
        return np.array([rx*math.sin(phi)*math.sin(theta),cy+ry*math.sin(phi)*math.cos(theta),cz+rz*math.cos(phi)])
    pts=[shell(math.tau*i/96,j/32) for j in range(33) for i in range(96)];faces=[]
    for j in range(32):
        for i in range(96):a=j*96+i;b=j*96+(i+1)%96;faces.append([a,b,b+96,a+96])
    # Collapse top pole to avoid a ring-shaped hole.
    pts=pts[96:]+[[0,cy,cz+rz]];faces=[[v-96 for v in f] for f in faces[96:]];pole=len(pts)-1
    faces.extend([[pole,i,(i+1)%96] for i in range(96)])
    mesh('Helmet_ContinuousCompositeShell',pts,faces,'OliveComposite',thickness=.72,bone='head',radial_center=(0,cy,cz))
    tube('Helmet_BoundRim',[shell(t,1) for t in np.linspace(0,math.tau,144,endpoint=False)],.32,'MattePolymer',8,True,bone='head')
    for theta in [0,.9,-.9,math.pi]:
        grid('Helmet_LoopPatch_'+str(theta),lambda u,v,theta=theta:shell(theta+(u-.5)*.44,.48+v*.24)+unit(shell(theta,.6)-[0,cy,cz])*.13,12,10,'OliveWebbing',thickness=.08,bone='head',radial_center=(0,cy,cz))
        for t in [.505,.698]:
            edge=[]
            for a in np.linspace(theta-.195,theta+.195,30):
                q=shell(a,t);edge.append(q+unit(q-[0,cy,cz])*.17)
            stitch('HelmetPatchStitch_'+str((theta,t)),edge,bone='head',pitch=.34)
    for side in [-1,1]:
        points=[shell(side*t,.93)+np.array([side*.35,0,.15]) for t in np.linspace(.70,2.35,40)]
        for z in [-.72,.72]:tube('AccessoryRail_'+str((side,z)),[p+[0,0,z] for p in points],.40,'MattePolymer',8,bone='head')
        for i in range(8):
            t=.70+1.65*i/7;p=shell(side*t,.93)+np.array([side*.43,0,.15]);tube('RailWeb_'+str((side,i)),[p+[0,0,-.7],p+[0,0,.7]],.31,'MattePolymer',8,bone='head')
        for i,t in enumerate([.73,2.31]):
            p=shell(side*t,.93)+np.array([side*.70,0,.15]);ring=[p+np.array([0,.39*math.cos(a),.39*math.sin(a)]) for a in np.linspace(0,math.tau,20,endpoint=False)];tube('RailBolt_'+str((side,i)),ring,.10,'Gunmetal',6,True,bone='head')
        for t in [.72,2.35]:
            anchor=shell(side*t,1)+[0,0,-.25];chin=np.array([side*4.0,cy+8.0,151.8]);mid=np.array([side*7.6,cy+4.0 if t<1 else cy-3.0,155.8]);path=np.array([anchor,mid,chin])
            grid('FourPointChinStrap_'+str((side,t)),lambda u,v,path=path:np.array([np.interp(v,[0,.53,1],path[:,k]) for k in range(3)])+np.array([(u-.5)*1.4,0,0]),3,22,'OliveWebbing',thickness=.15,bone='head')
        p=np.array([side*7.6,cy+4,155.8]);box('ChinStrapAdjuster_'+str(side),p,[1.9,.6,2.4],'MattePolymer',.2,bone='head')
    grid('ChinCup',lambda u,v:np.array([(u-.5)*8.3,cy+8.0+1.0*math.sin(math.pi*u),151.5+(v-.5)*2.5+.35*math.cos(math.tau*u)]),24,8,'CharcoalLeather',thickness=.28,bone='head')
    # Central shroud is a framed recess with open center and mounting pads.
    y=cy+ry*.99+.4;z=169.1
    for x in [-2.3,2.3]:box('ShroudSide_'+str(x),[x,y,z],[.7,.85,5.2],'MattePolymer',.16,bone='head')
    for dz in [-2.2,2.2]:box('ShroudCrossbar_'+str(dz),[0,y,z+dz],[4.7,.85,.65],'MattePolymer',.15,bone='head')
    for x in [-3.2,3.2]:
        box('ShroudMount_'+str(x),[x,y-.3,z-1.1],[1.5,.8,1.7],'OliveComposite',.35,bone='head')
        tube('ShroudBolt_'+str(x),[[x+.28*math.cos(a),y+.19,z-1.1+.28*math.sin(a)] for a in np.linspace(0,math.tau,20,endpoint=False)],.09,'Gunmetal',6,True,bone='head')
    for i,t in enumerate(np.linspace(0,math.tau,7,endpoint=False)):
        grid('InternalComfortPad_'+str(i),lambda u,v,t=t:shell(t+(u-.5)*.45,.61+v*.21)-unit(shell(t,.72)-[0,cy,cz])*1.05,10,7,'CharcoalStretch',thickness=.45,bone='head')

def build_gloves():
    original=read(PROJECT/'SourceAssets/JasonPlayer20261003/ue_original_gloves.json');fitted=read(PROJECT/'SourceAssets/JasonPlayer20261003/ue_original_gloves_fitted.json')
    d={**original,'positions':fitted['positions'],'weights':fitted['weights']};surf=WeightSurface(d)
    ob=native_mesh('Gloves_ContinuousNativeShell',d,{0:'RangerNylon'})
    ob.data.materials.append(MATS['CharcoalLeather']);ob.data.materials.append(MATS['CharcoalStretch'])
    frames={}
    for side in ['l','r']:
        bpos=lambda n:np.array(BONES[BONE_IDS[n+'_'+side]]['position'])
        wrist=bpos('hand');forward=unit(bpos('middle_01')-wrist);across=unit(bpos('index_01')-bpos('pinky_01'));normal=unit(np.cross(across,forward))
        if normal[1]>0:normal=-normal
        across=unit(np.cross(forward,normal));frames[side]=(wrist,forward,across,normal)
    for poly in ob.data.polygons:
        center=nativept(poly.center);side='l' if center[0]>0 else 'r';w,f,a,n=frames[side]
        normal=np.array([poly.normal.x,-poly.normal.y,poly.normal.z]);poly.material_index=0 if normal@n>.05 else 1
        if (center-w)@f<.3:poly.material_index=2
    def project(point,normal,extra=.15):
        q,n,fi,dist=surf.tree.ray_cast(Vector(point+normal*5),Vector(-normal),10)
        if q is None:q,n,fi,dist=surf.tree.find_nearest(Vector(point+normal*1.0))
        return np.array(q)+normal*extra
    for side in ['l','r']:
        wrist,forward,across,n=frames[side];basis=np.column_stack([across,n,forward])
        for finger in ['index','middle','ring','pinky']:
            joint=np.array(BONES[BONE_IDS[finger+'_01_'+side]]['position']);p=project(joint,n,.25)
            def guard(u,v):
                a=math.tau*u;radius=v
                point=joint+across*(.95*radius*math.cos(a))+forward*(1.12*radius*math.sin(a))
                return project(point,n,.17+.49*(1-radius**2)**1.35)
            rings=[guard(i/24,v) for v in np.linspace(.125,1,8) for i in range(24)]
            pole=len(rings);rings.append(guard(0,0));faces=[[pole,i,(i+1)%24] for i in range(24)]
            for j in range(7):
                for i in range(24):
                    a=24*j+i;b=24*j+(i+1)%24;faces.append([a,b,b+24,a+24])
            mesh('KnuckleGuard_'+finger+'_'+side,rings,faces,'MattePolymer',thickness=.09,source=surf,outward=n)
            for k in [1,2]:
                start=np.array(BONES[BONE_IDS[f'{finger}_{k:02d}_{side}']]['position']);end=np.array(BONES[BONE_IDS[f'{finger}_{k+1:02d}_{side}']]['position'])
                direction=unit(end-start);a=unit(np.cross(direction,n));bn=np.column_stack([a,n,direction]);p=project((start+end)*.5,n,.15)
                box(f'FingerPad_{finger}_{side}_{k}',p,[1.05,.33,max(.75,np.linalg.norm(end-start)*.54)],'OliveWebbing',.20,bn,source=surf)
        center=project(wrist+forward*3.0,n,.13)
        box('DorsalYoke_'+side,center,[5.1,.35,3.7],'RangerRipstop',.65,basis,source=surf)
        center=project(wrist-forward*.1,n,.25)
        box('WristHookLoopClosure_'+side,center,[5.3,.40,2.6],'OliveWebbing',.42,basis,source=surf)
        outline=[project(wrist+forward*(.2+v*2.2)+across*s*2.6,n,.27) for s in [-1,1] for v in np.linspace(0,1,25)]
        for s in [-1,1]:stitch('WristClosureStitch_'+side+str(s),[project(wrist+forward*(.2+v*2.0)+across*s*2.3,n,.32) for v in np.linspace(0,1,35)],source=surf)
        # Palm reinforcement remains thin to retain the native grip envelope.
        p=project(wrist+forward*3.8,-n,.06)
        box('SuedePalmReinforcement_'+side,p,[4.4,.16,3.6],'CharcoalLeather',.65,np.column_stack([across,-n,forward]),source=surf)
    ob['Source']='Current Jason native-fit tactical glove foundation; new material zones and segmented protection'

def build_pants(bootfit=False):
    root=PROJECT/'SourceAssets/ST6LowerSet20261018';d=read(root/'Jason_ST6Trousers_Garment.json')
    # Keep each footwear-specific hem and tailor its central rise identically.
    if bootfit:
        full=read(root/'Jason_ST6Trousers_ST6BootsFit.json')
        # The authored garment occupies the same prefix as its native-body wrapper.
        if len(full['positions'])>=len(d['positions']):
            d['positions']=full['positions'][:len(d['positions'])];d['weights']=full['weights'][:len(d['positions'])];d['normals']=full['normals'][:len(d['triangles'])]
    mats={0:'Gunmetal',1:'RangerRipstop',2:'MattePolymer',3:'StitchThread',4:'RangerNylon',5:'CharcoalStretch'}
    sys.path.insert(0,str(ROOT))
    from trouser_gusset import tailor
    tailor(d,BONE_IDS,cut=True)
    ob=native_mesh('Trousers_ContinuousNativeWaistAndLegs',d,mats)
    detail=read(PROJECT/'SourceAssets/ST6LowerDetail20261024/Authored/Jason_pants.json')
    tailor(detail,BONE_IDS)
    native_mesh('Trousers_CargoPleatsAndConstructionStitches',detail,mats)
    ob['Source']='Native waistband with a recut earth-brown stretch gusset and graduated pelvic support'
    # Additional shaped knee ridges follow the actual existing knee shield.
    surf=WeightSurface(d)
    for side,sg in [('l',1),('r',-1)]:
        for k,z in enumerate([44.8,47,49.2]):
            path=[]
            for x in np.linspace(sg*12.2-3.2,sg*12.2+3.2,26):
                q,n,fi,dist=surf.tree.ray_cast(Vector((x,40,z)),Vector((0,-1,0)),50)
                if q is not None:path.append(np.array(q)+[0,.16,0])
            if len(path)>1:tube('KneeFlexRidge_'+side+str(k),path,.12,'MattePolymer',6,source=surf)
    return d

def build_boots():
    sys.path.insert(0,str(ROOT))
    from refine_boots import build
    return build(globals())

def build_boots_r2_reference():
    donor=read(PROJECT/'SourceAssets/ST6LowerSet20261018/Jason_ST6Boots_Garment.json');surf=WeightSurface(donor)
    levels=np.array([1.8,2.6,3.8,5.2,7.0,9.5,12,16,21,26,28.5])
    rx=np.array([5.4,5.65,5.85,5.7,5.3,4.8,4.75,5.0,5.7,6.1,6.15]);ry=np.array([15.4,15.5,14.7,12.8,10.2,7.4,5.65,5.5,5.9,6.25,6.3]);cy=np.array([7.4,7.4,7.0,5.3,3.3,.5,-2.0,-2.65,-2.8,-2.8,-2.8])
    tilt=math.atan2(2.00392146,12.92064786)
    def surface(t,z,sg):
        xr=np.interp(z,levels,rx);yr=np.interp(z,levels,ry);yc=np.interp(z,levels,cy)
        # Superelliptic toe, anatomically tapered heel, soft ankle compression.
        a=math.sin(t);b=math.cos(t);power=1.0 if z>10 else .83
        x=xr*math.copysign(abs(a)**power,a)*(1-.12*max(0,-b));y=yc+yr*math.copysign(abs(b)**power,b)
        fold=.11*math.sin(z*2.8+1.7*math.sin(t))*math.exp(-((z-12)/4)**2)
        x+=fold*a;y+=fold*b
        return np.array([sg*(14.798+math.cos(tilt)*x+math.sin(tilt)*y),-2.45465-math.sin(tilt)*x+math.cos(tilt)*y,z])
    for side,sg in [('l',1),('r',-1)]:
        zs=np.linspace(1.8,28.5,70);pts=[surface(t,z,sg) for z in zs for t in np.linspace(0,math.tau,96,endpoint=False)];faces=[]
        for j in range(len(zs)-1):
            for i in range(96):faces.append([j*96+i,j*96+(i+1)%96,(j+1)*96+(i+1)%96,(j+1)*96+i])
        ob=mesh('Boot_ContinuousToeAnkleShaft_'+side,pts,faces,'RangerNylon',thickness=.22,source=surf,radial_center=(sg*14.798,-2.45,14))
        ob.data.materials.append(MATS['CharcoalLeather'])
        for poly in ob.data.polygons:
            c=nativept(poly.center);poly.material_index=1 if c[2]<8.8 or c[1]<-6.1 else 0
        # Separate rubber sole uses the same footprint as the continuous upper.
        solepts=[];solefaces=[]
        for z,scale in [(.35,1.01),(.60,1.025),(1.25,1.035),(1.8,1.028),(2.35,1.01)]:
            for t in np.linspace(0,math.tau,96,endpoint=False):
                p=surface(t,2.0,sg);p[:2]=np.array([sg*14.798,4.0])+(p[:2]-[sg*14.798,4.0])*scale;p[2]=z+.25*max(0,math.cos(t))**4;solepts.append(p)
        for j in range(4):
            for i in range(96):solefaces.append([j*96+i,j*96+(i+1)%96,(j+1)*96+(i+1)%96,(j+1)*96+i])
        solefaces.extend([list(reversed(range(96))),list(range(384,480))]);mesh('Boot_LayeredOutsole_'+side,solepts,solefaces,'BlackRubber',source=surf)
        for z in [.8,1.4,2.05]:tube('OutsoleLayer_'+side+str(z),[surface(t,2.0,sg)*[1,1,0]+[0,0,z] for t in np.linspace(0,math.tau,100,endpoint=False)],.13,'BlackRubber',6,True,source=surf)
        tube('Boot_PaddedCuff_'+side,[surface(t,28.5,sg) for t in np.linspace(0,math.tau,100,endpoint=False)],.32,'CharcoalStretch',10,True,source=surf)
        stitch('Boot_WeltStitch_'+side,[surface(t,2.55,sg)+[0,0,.12] for t in np.linspace(0,math.tau,180)],source=surf,pitch=.32)
        for flank in [-1,1]:
            grid('Boot_QuarterFacing_'+side+str(flank),lambda u,v,flank=flank:surface(flank*(.62+.46*u),8.0+v*19.2,sg)+[sg*flank*.12,.10,0],10,38,'CharcoalLeather',thickness=.13,source=surf)
            for edge in [.03,.97]:stitch('Boot_QuarterStitch_'+side+str((flank,edge)),[surface(flank*(.62+.46*edge),8+v*19.1,sg)+[sg*flank*.18,.15,0] for v in np.linspace(.02,.98,100)],source=surf)
        grid('Boot_HeelCounter_'+side,lambda u,v:surface(math.pi+(u-.5)*1.9,3.0+v*10.0,sg)+[0,-.22,0],30,24,'CharcoalLeather',thickness=.17,source=surf)
        def toe_seam(t):
            a=(t-.5)*2.65;z=5.35+2.1*math.sin(math.pi*t)**1.5
            return surface(a,z,sg)+np.array([sg*.12*math.sin(a),.15*math.cos(a),.025])
        stitch('ToeCapDoubleNeedle_'+side,[toe_seam(t) for t in np.linspace(0,1,120)],source=surf,pitch=.34)
        stitch('ToeCapDoubleNeedleReturn_'+side,[toe_seam(t)+[0,0,.22] for t in np.linspace(0,1,120)],source=surf,pitch=.34)
        grid('Boot_BellowsTongue_'+side,lambda u,v:surface((u-.5)*.83,6.0+v*21.5,sg)+[0,.35,0],16,44,'CharcoalStretch',thickness=.23,source=surf)
        # Real hollow eyelets and separate crossed lace cords.
        rows=[]
        for i,z in enumerate(np.linspace(7.0,26.8,9)):
            row=[]
            for flank in [-1,1]:
                p=surface(flank*.53,z,sg)+[0,.35,0];row.append(p)
                ring=[p+np.array([.31*math.cos(a),.12*math.sin(a),.31*math.sin(a)]) for a in np.linspace(0,math.tau,20,endpoint=False)]
                tube('Boot_Eyelet_'+side+str((i,flank)),ring,.095,'Gunmetal',6,True,source=surf)
            rows.append(row)
        for i in range(8):
            for direction in [0,1]:
                a=np.array(rows[i][direction]);b=np.array(rows[i+1][1-direction]);path=[a*(1-t)+b*t+np.array([0,.35*math.sin(math.pi*t),0]) for t in np.linspace(0,1,12)]
                tube('Boot_Lace_'+side+str((i,direction)),path,.105,'OliveWebbing',6,source=surf)
        for loop in [-1,1]:
            p=(np.array(rows[-1][0])+rows[-1][1])*.5+[0,.6,0];path=[p+[loop*1.4*math.sin(a),.18*math.sin(2*a),1.2*(1-math.cos(a))] for a in np.linspace(0,math.tau,36)]
            tube('Boot_LaceBow_'+side+str(loop),path,.105,'OliveWebbing',6,source=surf)
        grid('Boot_HeelPullLoop_'+side,lambda u,v:surface(math.pi+(u-.5)*.23,25+4.5*v,sg)+[0,-.7*math.sin(math.pi*v),0],4,20,'OliveWebbing',thickness=.14,source=surf)
        for j,y in enumerate(np.linspace(-5,20,10)):
            for k,x in enumerate([-3.45,0,3.45]):
                if (j in [0,9]) and k==1:continue
                c=np.array([sg*(14.798+math.cos(tilt)*x+math.sin(tilt)*y),-2.45465-math.sin(tilt)*x+math.cos(tilt)*y,.17]);basis=np.array([[sg*math.cos(tilt),sg*math.sin(tilt),0],[-math.sin(tilt),math.cos(tilt),0],[0,0,1]])
                box('Boot_TreadLug_'+side+str((j,k)),c,[2.2,1.85,.55],'BlackRubber',.17,basis,source=surf)
        ob['Construction']='One continuous ring loft from toe through ankle to shaft; inward wall and closed cuff rim'

def save_part(name):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in OBJECTS:ob.select_set(True)
    RIG.select_set(True);bpy.context.view_layer.objects.active=OBJECTS[0]
    blend=ROOT/'Models'/f'{name}.blend';fbx=ROOT/'Exports'/f'{name}.fbx';glb=ROOT/'Exports'/f'{name}.glb'
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
    bpy.context.scene['Stage']='Editable model candidate; UE import and gameplay acceptance not performed'
    bpy.context.scene['Concept']=str(ROOT/'Design/TacticalSystem01_Concept.png')
    # Set a useful material-preview opening state without rendering a frame.
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':area.spaces.active.shading.color_type='MATERIAL';area.spaces.active.overlay.show_floor=False
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',path_mode='COPY',embed_textures=True)
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_animations=False,export_skins=True,export_all_influences=True)
    counts=[]
    for ob in OBJECTS:
        ob.data.calc_loop_triangles();counts.append(dict(name=ob.name,vertices=len(ob.data.vertices),triangles=len(ob.data.loop_triangles)))
    write_json(ROOT/'Receipts'/f'{name}.json',dict(name=name,blend=str(blend),fbx=str(fbx),glb=str(glb),objects=counts,total_triangles=sum(x['triangles'] for x in counts),source_hashes=SOURCES,engine_imported=False,tested=False,rendered=False))
    print('MODEL_SAVED',name,'objects',len(OBJECTS),'triangles',sum(x['triangles'] for x in counts),flush=True)

def assembly():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    shared_rig=None
    for path in sorted((ROOT/'Models').glob('0*.blend')):
        if path.stem=='04_TacticalTrousers':continue
        collection=bpy.data.collections.new(path.stem);bpy.context.scene.collection.children.link(collection)
        with bpy.data.libraries.load(str(path),link=False) as (data_from,data_to):data_to.objects=list(data_from.objects)
        for ob in data_to.objects:
            if ob is not None:collection.objects.link(ob)
        local_rigs=[ob for ob in data_to.objects if ob is not None and ob.type=='ARMATURE']
        if shared_rig is None and local_rigs:shared_rig=local_rigs[0]
        for ob in data_to.objects:
            if ob is None or ob.type!='MESH':continue
            for modifier in ob.modifiers:
                if modifier.type=='ARMATURE':modifier.object=shared_rig
            ob.parent=shared_rig
        for rig in local_rigs:
            if rig!=shared_rig:bpy.data.objects.remove(rig,do_unlink=True)
    # Optional fitting reference for the user's own inspection; never exported.
    ref=read(PROJECT/'SourceAssets/JasonPlayer20261003/Jason.json')
    ref_collection=bpy.data.collections.new('REFERENCE_ONLY_JasonBody');bpy.context.scene.collection.children.link(ref_collection)
    verts=[uvpt(p) for p in ref['positions']];faces=[f for f,m in zip(ref['triangles'],ref['triangle_materials']) if m==2]
    data=bpy.data.meshes.new('NativeBody_FitReference');data.from_pydata(verts,[],faces);data.update()
    ob=bpy.data.objects.new(data.name,data);ref_collection.objects.link(ob);ob.hide_render=True;ob.hide_set(True)
    ob['Usage']='Optional fit reference only. Hidden by default; excluded from every component export.'
    bpy.context.scene['Stage']='Five component model candidates in native reference pose. No UE import or animation acceptance.'
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Models/TacticalSystem01_Assembly.blend'))
    write_json(ROOT/'Receipts/delivery.json',dict(stage='concept plus five editable model candidates',models=[str(p) for p in sorted((ROOT/'Models').glob('*.blend'))],exports=[str(p) for p in sorted((ROOT/'Exports').glob('*')) if p.is_file()],engine_imported=False,gameplay_registered=False,runtime_tested=False,acceptance_rendered=False))
    print('ASSEMBLY_SAVED',flush=True)

if __name__=='__main__':
    if PART=='assembly':assembly()
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);surface_maps();MATS=materials();OBJECTS=[]
        BODY=read(PROJECT/'SourceAssets/JasonPlayer20261003/Jason.json');BONES=BODY['bones'];BONE_IDS={b['name']:b['index'] for b in BONES};RIG=rig_from(BONES)
        bodyfaces=np.array(BODY['triangles']);visible=np.array(BODY['triangle_materials'])==2
        BODY_SURFACE=WeightSurface(BODY,bodyfaces[visible])
        if PART=='vest':build_vest();save_part('01_KevlarVest')
        elif PART=='helmet':build_helmet();save_part('02_TacticalHelmet')
        elif PART=='gloves':build_gloves();save_part('03_TacticalGloves')
        elif PART=='pants':build_pants();save_part('04_TacticalTrousers')
        elif PART=='pants_boot':build_pants(True);save_part('04_TacticalTrousers_BootTuck')
        elif PART=='boots':build_boots();save_part('05_TacticalBoots')
        else:raise ValueError(PART)
