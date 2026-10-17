"""Build curved, Jason-skinned crystalline armour and eight camera clusters. No rendering."""
import json, math, random
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/IceArmor20261017/CrystalV2'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
body=read('SourceAssets/JasonPlayer20261003/Jason.json')
pos=[Vector(p) for p in body['positions']];tris=body['triangles']
bvh=BVHTree.FromPolygons(pos,tris,all_triangles=True)
bones={b['name']:Vector(b['position']) for b in body['bones']}
def tree(data):return BVHTree.FromPolygons([Vector(p) for p in data['positions']],data['triangles'],all_triangles=True)
cloth=tree(read('SourceAssets/JasonEquipmentRepair20261003/sweater.json'))
mail=tree(read('SourceAssets/JasonEquipmentRepair20261003/chainmail.json'))
steel_data=read('SourceAssets/JasonPlayer20261003/ue_steel_gauntlets_fitted.json')
steel_data['triangles']=read('SourceAssets/JasonPlayer20261003/ue_steel_gauntlets.json')['triangles']
steel=tree(steel_data)
pants=tree(read('SourceAssets/ChainmailPants20261004/Jason_ChainmailPants.json'))

def skin_weights(point):
    q,n,face,_=bvh.find_nearest(point);ids=tris[face];a,b,c=[pos[i] for i in ids]
    v0=b-a;v1=c-a;v2=q-a;den=v0.dot(v0)*v1.dot(v1)-v0.dot(v1)**2
    if abs(den)<1e-8:return body['weights'][ids[0]]
    v=(v1.dot(v1)*v2.dot(v0)-v0.dot(v1)*v2.dot(v1))/den;w=(v0.dot(v0)*v2.dot(v1)-v0.dot(v1)*v2.dot(v0))/den
    accum={}
    for vi,f in zip(ids,[max(0,1-v-w),max(0,v),max(0,w)]):
        for bi,bw in body['weights'][vi]:accum[bi]=accum.get(bi,0)+f*bw
    row=sorted(accum.items(),key=lambda t:-t[1])[:8];total=sum(w for _,w in row)
    return [[i,w/total] for i,w in row]

def blank(name,skinned=False):return {'name':name,'positions':[],'normals':[],'uv':[],'uv1':[],'uv2':[],'colors':[],'triangles':[],'weights':[],'skinned':skinned}
def add_triangle(data,verts,normal=None):
    a,b,c=[v[0] for v in verts];n=normal or (b-a).cross(c-a).normalized()
    if n.length<.1:return
    row=[]
    for p,uv,col,weight,meta in verts:
        row.append(len(data['positions']));data['positions'].append(list(p));data['normals'].append(list(n));data['uv'].append(uv);data['colors'].append(col);data['weights'].append(weight);data['uv1'].append(meta)
        data['uv2'].append([0,0])
    # Blender's outward normal follows (B-A)x(C-A). UE native MeshDescription
    # uses the opposite front-face winding; keep the outward normals and swap
    # two triangle indices at the native JSON boundary.
    data['triangles'].append([row[0],row[2],row[1]])

def sample(origin,direction,extra,stand):
    p,n,face,d=bvh.ray_cast(origin,direction,100)
    if p is None:raise RuntimeError('Anatomical surface missed: '+str(origin))
    # Start from the actual skin surface; include only outward garment surfaces.
    surface=p;normal=n
    if extra:
        cp,cn,_,cd=extra.ray_cast(origin,direction,100)
        if cp is not None and cd<d and (cp-p).length<13:surface=cp
    if normal.dot(-direction)<0:normal=-normal
    return surface+normal*stand,normal,skin_weights(p)

def panel(data,mapper,seed,zone,stand,thickness=1.2):
    rng=random.Random(seed);N=16
    # Five distinct cleavage bands. The narrow ridge is not a painted white outline.
    rings=[(.91,0.,.22),(1.,thickness*.24,.52),(.91,thickness*.77,.32),(.65,thickness,.04),(.27,thickness*1.08,.01)]
    pts=[]
    for scale,height,rim in rings:
        row=[]
        for i in range(N):
            angle=2*math.pi*i/N
            # Ordered facets with gentle asymmetric shoulders and chipped corners.
            fac=1-.07*math.sin(angle*3+seed)-.04*math.cos(angle*5-seed)
            x=math.cos(angle)*scale*fac;y=math.sin(angle)*scale*fac
            p,n,weights=mapper(x,y,stand)
            row.append((p+n*height,[x*.44+.5+seed*.137,y*.44+.5+seed*.071],
                        [rim*(.7+.3*math.sin(angle*2+seed)**2),zone,.13+.74*rng.random(),1],weights,[x*.5+.5,y*.5+.5]))
        pts.append(row)
    # Match face winding to the outward surface direction.
    centre,normal,cw=mapper(0,0,stand)
    for r in range(len(rings)-1):
        for i in range(N):
            j=(i+1)%N
            for triangle in [(pts[r][i],pts[r][j],pts[r+1][j]),(pts[r][i],pts[r+1][j],pts[r+1][i])]:
                a,b,c=[v[0] for v in triangle]
                if (b-a).cross(c-a).dot(normal)<0:triangle=tuple(reversed(triangle))
                add_triangle(data,triangle)
    mid=(centre+normal*thickness*1.1,[.5+seed*.137,.5+seed*.071],[.01,zone,.12+.65*rng.random(),1],cw,[.5,.5])
    for i in range(N):
        triangle=(pts[-1][i],pts[-1][(i+1)%N],mid)
        if (triangle[1][0]-triangle[0][0]).cross(triangle[2][0]-triangle[0][0]).dot(normal)<0:triangle=tuple(reversed(triangle))
        add_triangle(data,triangle)

def torso_map(cx,cz,rx,rz,front,extra):
    def fn(x,y,stand):return sample(Vector((cx+x*rx,70*front,cz+y*rz)),Vector((0,-front,0)),extra,stand)
    return fn
def limb_map(start,end,t,span,angle,arc,extra):
    a=bones[start];b=bones[end];axis=(b-a).normalized()
    forward=Vector((0,1,0));forward=(forward-axis*forward.dot(axis)).normalized();side=axis.cross(forward).normalized()
    def fn(x,y,stand):
        centre=a.lerp(b,t+y*span);theta=angle+x*arc;rad=forward*math.cos(theta)+side*math.sin(theta)
        return sample(centre+rad*42,-rad,extra,stand)
    return fn

assets=[]
for profile in range(3):
    torso_extra=[None,cloth,mail][profile]
    data=blank(f'SK_IceArmor_Torso_{profile}',True)
    for side in (-1,1):
        panel(data,torso_map(side*6.,125,6.,10,1,torso_extra),11+(side+1),0.,1.5,1.2)
        panel(data,torso_map(side*5.8,119,5.9,14,-1,torso_extra),21+(side+1),.25,1.6,1.3)
    for j,(z,rx,rz) in enumerate([(111,11,4.3),(102.5,9,4.1),(94.5,8,3.4)]):
        panel(data,torso_map(0,z,rx,rz,1,torso_extra),30+j,0.,1.5,.85)
    for sign in ('l','r'):
        panel(data,limb_map('upperarm_'+sign,'lowerarm_'+sign,.13,.11,0,.95,torso_extra),40+(sign=='r'),.5,1.6,1.4)
    assets.append(data)
    data=blank(f'SK_IceArmor_Arms_{profile}',True)
    for sign in ('l','r'):
        for j,t in enumerate((.32,.66)):
            panel(data,limb_map('lowerarm_'+sign,'hand_'+sign,t,.14,0,1.10,steel if profile==2 else cloth if profile==1 else None),50+j+(sign=='r')*5,.5,1.4+profile*.45,.85)
    assets.append(data)
    data=blank(f'SK_IceArmor_Legs_{profile}',True)
    for sign in ('l','r'):
        panel(data,limb_map('thigh_'+sign,'calf_'+sign,.43,.22,0,.88,pants if profile==2 else None),70+(sign=='r'),.75,1.6+profile*.4,1.25)
        for j,t in enumerate((.29,.62)):
            panel(data,limb_map('calf_'+sign,'foot_'+sign,t,.13,0,1.05,pants if profile==2 else None),80+j+(sign=='r')*5,1.,1.6+profile*.4,1.)
    assets.append(data)

# Camera coordinates: X points from the eye into the scene; Y/Z span screen.
# Positions are normalized to a 100 cm wide/high frame, with open gaps.
lens=blank('SM_IceArmor_Clusters')
clusters=[(-.42,.30,.095,.135,-.35),(.425,.26,.090,.125,.3),(-.40,-.25,.105,.135,.2),(.405,-.30,.100,.125,-.25),(-.24,.435,.115,.060,.2),(.24,.44,.100,.055,-.1),(-.44,.02,.065,.10,.3),(.44,-.015,.060,.09,-.3)]
for i,(cy,cz,ry,rz,rotation) in enumerate(clusters):
    for j in range(3):
        a=rotation+(j-1)*.32;scale=1 if j==0 else .48
        oy=(j-1)*ry*.42;oz=(j%2)*rz*.30
        def mapper(x,y,stand,cy=cy,cz=cz,ry=ry,rz=rz,a=a,scale=scale,oy=oy,oz=oz,i=i,j=j):
            yy=cy+oy+(x*ry*math.cos(a)-y*rz*math.sin(a))*scale
            zz=cz+oz+(x*ry*math.sin(a)+y*rz*math.cos(a))*scale
            depth=-(yy*yy+zz*zz)*2.5+j*.22
            return Vector((depth,yy*100,zz*100)),Vector((-1,0,0)),[]
        begin=len(lens['positions']);panel(lens,mapper,100+i*3+j,0.,0.,.22 if j else .45)
        for vi in range(begin,len(lens['positions'])):lens['uv2'][vi]=[cy+oy,cz+oz]
assets.append(lens)
chip=blank('SM_IceArmor_Chip')
v=[Vector(p) for p in [(-.5,-.8,-.15),(.5,-.4,-.2),(.6,.6,-.05),(-.3,.8,.1),(-.1,0,.55)]]
for t in [(0,1,4),(1,2,4),(2,3,4),(3,0,4),(0,3,2),(0,2,1)]:
    add_triangle(chip,[(v[i],[v[i].x+.5,v[i].y*.5+.5],[.16,0,.2,1],[],[.5,.5]) for i in t])
assets.append(chip)
for data in assets:
    data['skeleton_source']=body['source'];data['rig_bones']=[b['name'] for b in body['bones']];data['triangle_winding']='unreal_clockwise'
    (OUT/(data['name']+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    mesh=bpy.data.meshes.new(data['name']);mesh.from_pydata(data['positions'],[],[(a,c,b) for a,b,c in data['triangles']]);mesh.update()
    uv=mesh.uv_layers.new(name='IceUV');cols=mesh.color_attributes.new(name='IceAttributes',type='FLOAT_COLOR',domain='CORNER')
    for loop in mesh.loops:uv.data[loop.index].uv=data['uv'][loop.vertex_index];cols.data[loop.index].color=data['colors'][loop.vertex_index]
    ob=bpy.data.objects.new(data['name'],mesh);bpy.context.collection.objects.link(ob)
    ob.hide_set(data['skinned'] and not data['name'].endswith('_1'))
    for bone in data['rig_bones']:ob.vertex_groups.new(name=bone)
    for vi,weights in enumerate(data['weights']):
        for bi,w in weights:ob.vertex_groups[bi].add([vi],w,'REPLACE')
# Keep an editable native bind rig beside the generated surfaces. Runtime assets
# copy the exact native reference skeleton in UE; no FBX bone-axis conversion.
arm_data=bpy.data.armatures.new('Jason_IceArmor_Bind');arm=bpy.data.objects.new('Jason_IceArmor_Bind',arm_data);bpy.context.collection.objects.link(arm)
bpy.context.view_layer.objects.active=arm;arm.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for source in body['bones']:
    bone=arm_data.edit_bones.new(source['name']);bone.head=Vector(source['position']);axis=Vector(source['axes'][0]).normalized()
    bone.tail=bone.head+axis*1.5;bone.align_roll(Vector(source['axes'][2]))
    if source['parent']>=0:bone.parent=arm_data.edit_bones[body['bones'][source['parent']]['name']]
bpy.ops.object.mode_set(mode='OBJECT')
for ob in list(bpy.context.scene.objects):
    if ob.type=='MESH' and ob.name.startswith('SK_IceArmor'):
        mod=ob.modifiers.new('JasonPose','ARMATURE');mod.object=arm
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'IceArmorV2.blend'))
(OUT/'geometry-manifest.json').write_text(json.dumps({'assets':[{'name':d['name'],'vertices':len(d['positions']),'triangles':len(d['triangles'])} for d in assets],'rig':'Jason 342 bones','source':body['source'],'profile_envelopes':['skin','fitted sweater','fitted chainmail / steel gauntlets / chainmail pants'],'camera_clusters':8},indent=2),encoding='utf-8')
print('ICE_ARMOR_V2_GEOMETRY_AUTHORED',flush=True)
