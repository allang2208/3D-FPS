"""Author an 8.3 m entrance standard segment with spatially coherent history.

Only the first north/south tile spans are replaced. Remaining source meshes,
materials, transforms and all layout/gameplay data are preserved.
"""
import bpy
import bmesh
import json
import math
import random
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored/NaturalPass';OUT.mkdir(exist_ok=True)
SOURCE=ROOT/'Authored/DungeonAtmosphereV2_Structure.blend'
BACKUP=OUT/'DungeonAtmosphereV2_Structure_PreNaturalPass.blend'
if not BACKUP.exists():shutil.copy2(SOURCE,BACKUP)
bpy.ops.wm.open_mainfile(filepath=str(BACKUP))
for image in bpy.data.images:
    if image.filepath.startswith('//'):image.filepath=str(SOURCE.parent/image.filepath[2:])
scene=bpy.context.scene
recipes=json.loads((OUT/'material-manifest.json').read_text())
mats=[]
for name,maps in recipes.items():
    mat=bpy.data.materials.new('V2_'+name);mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;p=n.get('Principled BSDF')
    for channel,pin in [('BaseColor','Base Color'),('Roughness','Roughness'),('Normal','Normal')]:
        tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(maps[channel],check_existing=True)
        tex.image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color';out=tex.outputs['Color']
        if channel=='Normal':
            normal=n.new('ShaderNodeNormalMap');l.new(out,normal.inputs['Color']);out=normal.outputs['Normal']
        l.new(out,p.inputs[pin])
    mats.append(mat)

GLAZE,MORTAR,CORE,REPAIR,SALT=range(5)
groups={};stats={'tile_positions':0,'intact_tiles':0,'fractured_tiles':0,'retained_fragments':0,'removed_fragments':0,'floor_fragments':0,'repair_positions':0}
def group(name):return groups.setdefault(name,{'v':[],'f':[],'m':[],'uv':[]})
def raw_face(g,vs,material,uv):
    start=len(g['v']);g['v'].extend(vs);g['f'].append(tuple(range(start,start+len(vs))));g['m'].append(material);g['uv'].append(uv)
def area(p):return abs(sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p)))*.5)
def inset(p,distance):
    cx=sum(x for x,z in p)/len(p);cz=sum(z for x,z in p)/len(p)
    out=[]
    for x,z in p:
        radius=math.hypot(x-cx,z-cz);factor=max(.60,1-distance/max(.001,radius));out.append((cx+(x-cx)*factor,cz+(z-cz)*factor))
    return out
def jagged(p,r,amount=.0022):
    cx=sum(x for x,z in p)/len(p);cz=sum(z for x,z in p)/len(p);out=[]
    for i,(x,z) in enumerate(p):
        xx,zz=p[(i+1)%len(p)];length=math.hypot(xx-x,zz-z);count=max(1,int(length/.018))
        for j in range(count):
            t=j/count;px=x+(xx-x)*t;pz=z+(zz-z)*t
            cut=r.uniform(amount*.1,amount) if j else amount*.2;radius=max(.001,math.hypot(px-cx,pz-cz))
            out.append((px+(cx-px)*cut/radius,pz+(cz-pz)*cut/radius))
    return out
def clip(p,nx,nz,c):
    result=[]
    for i,a in enumerate(p):
        b=p[(i+1)%len(p)];va=a[0]*nx+a[1]*nz-c;vb=b[0]*nx+b[1]*nz-c
        if va<=0:result.append(a)
        if (va<0)!=(vb<0):
            t=va/(va-vb);result.append((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t))
    return result
def fracture(rect,r):
    x0,z0,x1,z1=rect
    sites=[(r.uniform(x0,x1),r.uniform(z0,z1)) for _ in range(r.randrange(5,10))];result=[]
    for sx,sz in sites:
        p=[(x0,z0),(x1,z0),(x1,z1),(x0,z1)]
        for tx,tz in sites:
            if (sx,sz)==(tx,tz):continue
            p=clip(p,tx-sx,tz-sz,(tx*tx+tz*tz-sx*sx-sz*sz)*.5)
            if len(p)<3:break
        if len(p)>=3 and area(p)>.00008:result.append(jagged(inset(p,.00006),r,.00018))
    return result
def atlas_uv(poly,rect,cell):
    x0,z0,x1,z1=rect;row,col=divmod(cell,8)
    return [((col+.035+.93*(x-x0)/(x1-x0))/8,1-(row+.035+.93*(z1-z)/(z1-z0))/8) for x,z in poly]

debris=group('SM_Natural_SurfaceDebris')
def fallen_piece(poly,rect,cell,x,y,r,flip=False):
    cx=sum(p[0] for p in poly)/len(poly);cz=sum(p[1] for p in poly)/len(poly)
    angle=r.uniform(-math.pi,math.pi);co=math.cos(angle);si=math.sin(angle)
    scale=r.uniform(.60,1.0);thick=r.uniform(.005,.009);slope=r.uniform(-.035,.035)
    local=[((px-cx)*scale,(pz-cz)*scale) for px,pz in poly]
    baseline=.002-min(q[0]*slope for q in local)
    bottom=[(x+u*co-v*si,y+u*si+v*co,baseline+u*slope) for u,v in local]
    top=[(px,py,pz+thick) for px,py,pz in bottom]
    uv=atlas_uv(poly,rect,cell)
    raw_face(debris,top,CORE if flip else GLAZE,uv if not flip else [(p[0]*8,p[1]*8) for p in poly])
    raw_face(debris,list(reversed(bottom)),CORE,[(p[0]*8,p[1]*8) for p in reversed(poly)])
    for i in range(len(poly)):
        j=(i+1)%len(poly);raw_face(debris,[bottom[i],bottom[j],top[j],top[i]],CORE,[(0,0),(.05,0),(.05,.03),(0,.03)])
    stats['floor_fragments']+=1

def wall(name,a,b,fixed,inside,seed):
    g=group(name);r=random.Random(seed);north=inside==-1;lost=[]
    def face(vs,material,uv=None):
        coords=uv or [(x/.7,z/.7) for x,d,z in vs]
        if inside==1:vs=list(reversed(vs));coords=list(reversed(coords))
        raw_face(g,[(x,fixed+inside*d,z) for x,d,z in vs],material,coords)
    def prism(p,front,back,mat=GLAZE,rect=None,cell=0,tilt=0,side=CORE):
        cx=sum(x for x,z in p)/len(p)
        top=[(x,front+(x-cx)*tilt,z) for x,z in p]
        face(top,mat,atlas_uv(p,rect,cell) if mat==GLAZE else None)
        for i in range(len(p)):
            j=(i+1)%len(p);x,z=p[i];xx,zz=p[j]
            face([top[j],top[i],(x,back,z),(xx,back,zz)],side)
    def bed(x,z):return .1238+.0012*math.sin(x*19+z*31)+.0008*math.sin(x*47-z*21)
    def stress(x,z):
        if north:
            main=math.exp(-((x-3.8)/.65)**2-((z-.96)/.35)**2)
            foot=.35*math.exp(-((x-6.95)/.48)**2-((z-.25)/.16)**2)
            return max(main,foot)+.065*math.sin(x*24+z*18)*math.sin(x*9-z*27)
        return math.exp(-((x-1.5)/.45)**2-((z-.66)/.27)**2)+.065*math.sin(x*16+z*25)
    # World-continuous mineral bed: no per-tile mortar texture resets.
    nx=math.ceil((b-a)/.045);nz=32
    for i in range(nx):
        for j in range(nz):
            x0=a+(b-a)*i/nx;x1=a+(b-a)*(i+1)/nx;z0=.155+j*1.435/nz;z1=.155+(j+1)*1.435/nz
            face([(x0,bed(x0,z0),z0),(x1,bed(x1,z0),z0),(x1,bed(x1,z1),z1),(x0,bed(x0,z1),z1)],MORTAR)
    for row in range(9):
        z=.24+row*.158
        for col in range(math.ceil((b-a)/.31)):
            left=a+col*.31+.003;right=min(a+(col+1)*.31-.003,b-.003)
            if right-left<.035:continue
            x=(left+right)*.5;rect=(left,z-.076,right,z+.076);x0,z0,x1,z1=rect
            stats['tile_positions']+=1
            if not north and col in (10,11,12) and row in (2,3,4,5):
                stats['repair_positions']+=1;continue
            damp=north and abs(x-3.8)<.62 and z<1.4
            cell=r.randrange(32,40) if damp else r.randrange(0,32)
            if not north and col in (11,12) and row==6:cell=r.randrange(56,64)
            potential=max(stress(px,pz) for px,pz in [(x,z),(x0,z0),(x1,z1),(x0,z1),(x1,z0)])
            front=.144+r.uniform(-.001,.001)
            if potential>.28:
                parts=fracture(rect,r)
                removed=[stress(sum(px for px,pz in p)/len(p),sum(pz for px,pz in p)/len(p))+r.uniform(-.12,.12)>.52 for p in parts]
                if not any(removed):
                    stats['intact_tiles']+=1
                    face([(a+col*.31,.139,z-.079),(min(a+(col+1)*.31,b),.139,z-.079),(min(a+(col+1)*.31,b),.139,z+.079),(a+col*.31,.139,z+.079)],MORTAR)
                    p=[(x0,z0),(x1,z0),(x1,z1),(x0,z1)]
                    if r.random()<.45:cell=r.randrange(48,56)
                    prism(p,front,.135,GLAZE,rect,cell)
                    continue
                stats['fractured_tiles']+=1
                # A mosaic of compressed adhesive and older crumbly mineral bed
                # remains after detachment. Some cells retain no comb ridges.
                coverage=r.random()
                if coverage>.34:
                    skin=inset([(x0,z0),(x1,z0),(x1,z1),(x0,z1)],r.uniform(.004,.019))
                    skin=jagged(skin,r)
                    prism(skin,.1265,.122,MORTAR,side=MORTAR)
                if .2<coverage<.70:
                    for k in range(r.randrange(7,14)):
                        qx=x0+.008+(x1-x0-.016)*k/13
                        start=z0+r.uniform(.004,.06);end=z1-r.uniform(.004,.045)
                        direction=.24*math.sin(x*2.2+z*1.3)
                        for s in range(5):
                            za=start+(end-start)*s/5;zb=start+(end-start)*(s+1)/5
                            xa=max(x0+.005,min(x1-.005,qx+(za-z)*direction+math.sin(za*8+x)*.008))
                            xb=max(x0+.005,min(x1-.005,qx+(zb-z)*direction+math.sin(zb*8+x)*.008))
                            if r.random()<.12:continue
                            depth=.1268 if coverage>.34 else .1248
                            face([(xa-.003,depth,za),(xa,depth+.0008,za),(xb,depth+.0008,zb),(xb-.003,depth,zb)],MORTAR)
                            face([(xa,depth+.0008,za),(xa+.003,depth,za),(xb+.003,depth,zb),(xb,depth+.0008,zb)],MORTAR)
                for p,is_removed in zip(parts,removed):
                    cx=sum(px for px,pz in p)/len(p);cz=sum(pz for px,pz in p)/len(p)
                    if is_removed:
                        lost.append((p,rect,cell));stats['removed_fragments']+=1;continue
                    # Adhesive footprint bonds each retained ceramic island to
                    # the bed; ceramic is approximately 8 mm thick, not a slab.
                    prism(inset(p,.0002),.136,.122,MORTAR,side=MORTAR)
                    prism(p,front,.135,GLAZE,rect,cell,tilt=r.uniform(-.001,.001))
                    stats['retained_fragments']+=1
            else:
                stats['intact_tiles']+=1
                face([(a+col*.31,.139,z-.079),(min(a+(col+1)*.31,b),.139,z-.079),(min(a+(col+1)*.31,b),.139,z+.079),(a+col*.31,.139,z+.079)],MORTAR)
                bevel=r.uniform(.0007,.0015)
                p=[(x0+bevel,z0),(x1-bevel,z0),(x1,z0+bevel),(x1,z1-bevel),(x1-bevel,z1),(x0+bevel,z1),(x0,z1-bevel),(x0,z0+bevel)]
                if potential>.12 and r.random()<.4:p=jagged(p,r);cell=r.randrange(40,48)
                if potential>.09 and r.random()<.13:cell=r.randrange(48,56)
                prism(p,front,.135,GLAZE,rect,cell,tilt=r.uniform(-.003,.003))
    if not north:
        # A single continuous repair skim with trowelled edges, plus two newer
        # tiles above it. The rectangle has a construction cause.
        p=[(3.104,.478),(3.41,.476),(3.65,.481),(4.026,.478),(4.031,.65),(4.025,.9),(4.029,1.109),(3.78,1.106),(3.43,1.114),(3.101,1.107)]
        prism(p,.142,.122,REPAIR,side=MORTAR)
        for i in range(4):
            qx=3.18+i*.19
            face([(qx,.1426,.56),(qx+.003,.1429,.57),(qx+.07,.1428,1.03),(qx+.064,.1425,1.02)],REPAIR)
    else:
        # Sparse mineral deposits collect at the lower edge of the wet region.
        for i in range(34):
            x=r.gauss(3.8,.40);z=r.uniform(.18,.36)
            if not a<x<b:continue
            rx=r.uniform(.006,.022);rz=r.uniform(.002,.006)
            p=[(x+math.cos(j*math.tau/7)*rx*r.uniform(.75,1),z+math.sin(j*math.tau/7)*rz*r.uniform(.75,1)) for j in range(7)]
            prism(p,.1455,.140,SALT,side=SALT)
    # Same removed ceramic polygons feed the floor fragments, with their exact
    # glaze UVs retained. The centre walking strip stays clear.
    r.shuffle(lost)
    for p,rect,cell in lost[:42 if north else 27]:
        center=3.8 if north else 1.5
        fx=max(a+.1,min(b-.1,r.gauss(center,.42 if north else .3)))
        fy=fixed+inside*r.uniform(.24,.64)
        fallen_piece(p,rect,cell,fx,fy,r,flip=r.random()<.31)
    for i in range(22 if north else 14):
        center=3.8 if north else 1.5;cx=r.gauss(center,.46);cy=fixed+inside*r.uniform(.2,.66)
        size=r.uniform(.004,.016);p=[(math.cos(j*math.tau/5)*size,math.sin(j*math.tau/5)*size*.6) for j in range(5)]
        fallen_piece(p,(-size,-size,size,size),r.randrange(32),cx,cy,r,True)

wall('NorthNatural',0,8.3,4,-1,921311)
wall('SouthNatural',0,4.4,0,1,921312)

def create_mesh(name,g):
    data=bpy.data.meshes.new(name+'_Data');data.from_pydata(g['v'],[],g['f']);data.update()
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    for m in mats:data.materials.append(m)
    uv=data.uv_layers.new(name='UVMap')
    for f,mi,coords in zip(data.polygons,g['m'],g['uv']):
        f.material_index=mi
        for li,co in zip(f.loop_indices,coords):uv.data[li].uv=co
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000005);bm.to_mesh(data);bm.free()
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    mod=obj.modifiers.new('Fine ceramic edge light','BEVEL');mod.width=.00035;mod.segments=2;mod.limit_method='ANGLE';mod.angle_limit=.8
    bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=obj.modifiers.new('Export tangents','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj

exports=[]
for key,original in [('NorthNatural','SM_V2_Corridor_North_Tiles'),('SouthNatural','SM_V2_Corridor_South_Tiles')]:
    old=bpy.data.objects[original]
    bm=bmesh.new();bm.from_mesh(old.data)
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.calc_center_median().x<8.35],context='FACES')
    bm.to_mesh(old.data);bm.free()
    new=create_mesh(key,groups[key])
    bpy.ops.object.select_all(action='DESELECT');new.select_set(True);old.select_set(True);bpy.context.view_layer.objects.active=old
    bpy.ops.object.join()
    exports.append((old,'SM_Natural_'+original.removeprefix('SM_V2_'),'DGN_AV2_'+original.removeprefix('SM_V2_'),True))
decor=create_mesh('SM_Natural_SurfaceDebris',debris)
exports.append((decor,decor.name,'DGN_AV2_Natural_SurfaceDebris',False))
manifest=[]
for obj,name,label,collision in exports:
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    file=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    manifest.append({'name':name,'fbx':str(file),'actor_label':label,'collision':collision,'replace_actor_mesh':collision,
        'materials':[m.name for m in obj.data.materials],'triangles':len(obj.data.polygons)})
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
history={'scope_m':{'north':[0,8.3],'south':[0,4.4]},'seed':921311,
    'causes':[{'type':'ceiling_joint_leak','wall':'north','x':3.8,'damage_z':.96},
              {'type':'impact','wall':'south','x':1.5,'damage_z':.66},
              {'type':'maintenance_skim_and_two_replacement_tiles','wall':'south','x_range':[3.1,4.03]}],
    'gameplay_tests':False,'runtime_random_generation':False}
(OUT/'geometry-manifest.json').write_text(json.dumps({'objects':manifest,'stats':stats,'history':history},indent=2),encoding='utf-8')
print('NATURAL_SEGMENT_AUTHORED',json.dumps(stats))
