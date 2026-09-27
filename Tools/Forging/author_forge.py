"""Author the forge tools and a native V7 cylindrical grip. No renders or game runs."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Matrix, Vector
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/ForgeInteraction20260927'
OUT.mkdir(parents=True,exist_ok=True)
DATA=ROOT/'Content/ColdSteelData/forge-grip.json'
sys.path.insert(0,str(Path(__file__).resolve().parent))
from forge_stroke import apply_stroke
DONOR=ROOT/'SourceAssets/MannyGraspDonor20260912'
native=json.loads((ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/M4_original.json').read_text())
skin=json.loads((ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/Authored/M4.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(DONOR/'Final/m4/vertical/A_M4_Vertical_idle.blend'))
bpy.context.scene.frame_set(0)
rig=bpy.data.objects['SK_M4_Infima']
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
pose={b.name:b.matrix.copy() for b in rig.pose.bones}
# Recover the coordinate conversion from the actual shared reference skeleton.
names=['upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r']
a=np.array([list(rest[n].translation) for n in names]); b=np.array([native['bones'][n]['position'] for n in names])/100
ac=a-a.mean(0);bc=b-b.mean(0);uu,ss,vh=np.linalg.svd(ac.T@bc)
rotation=vh.T@uu.T  # Reflection is legitimate between Blender and UE coordinates.
conv=Matrix(rotation.tolist()).to_4x4();conv.translation=Vector((b.mean(0)-rotation@a.mean(0)).tolist())
def native_matrix(n):
    v=native['bones'][n];m=Matrix([Vector(x).normalized() for x in v['axes']]).transposed().to_4x4();m.translation=Vector(v['position'])/100;return m
nrest={n:native_matrix(n) for n in native['bones']}
reflection=Matrix.Diagonal((-1,1,1,1))
fit=json.loads((DONOR/'Opening/0.8/aligned_fit.json').read_text())
grip=pose['WPN_root']@Matrix(fit['grip_in_root'])
left=[n for n in pose if n.endswith('_l') and n.startswith(('index','middle','ring','pinky','thumb'))]
donor_right={n[:-1]+'r':reflection@(pose[n]@rest[n].inverted())@reflection@rest[n[:-1]+'r'] for n in ['hand_l']+left}
data={'source':'MannyGraspDonor20260912 vertical / accepted V7 native skeleton',
      'arms':'/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7',
      'grip_radius_cm':[1.40,1.20],
      'hammer_contact_cm':[6.8,0,21.0], 'hands':{},'finger_rotations':{}}
apply_stroke(data)
data['station_layout']={'body_origin_cm':[29,-34,146],'hammer_axis':[.45,.893,0],
    'tong_axis':[-.30,.954,0],'elbow_pole_cm':[32,-10,-29],
    'work_yaw':180,'quench_origin_cm':[56,-30,73],'quench_pitch':-62}
data['grip_roll_deg']={'r':150,'l':0}
def transform(m):
    q=m.to_quaternion().normalized();return {'p':[v*100 for v in m.translation],'q':[q.x,q.y,q.z,q.w]}
posed={}
for side,src,tool in [('l',pose,grip),('r',donor_right,reflection@grip@reflection)]:
    hand='hand_'+side
    # Transform pose deltas into the native skeleton, retaining native inverse binds.
    for n in [hand]+[v for v in nrest if v.endswith('_'+side) and v.startswith(('index','middle','ring','pinky','thumb'))]:
        posed[n]=conv@(src[n]@rest[n].inverted())@conv.inverted()@nrest[n]
    # A positive-Z cylinder, centered between the four fingers and opposing thumb.
    cylinder=tool@Matrix.Translation((0,0,-.06))
    # Conjugate axis reflection to maintain a right-handed tool frame in UE.
    axis_fix=Matrix.Diagonal((1,-1,1,1)) if conv.determinant()<0 else Matrix.Identity(4)
    nt=conv@cylinder@axis_fix
    # A fixed 150-degree right grasp supports the native elbow hinge. The former
    # 180-degree grasp forced an overhand wrist / reversed elbow compensation.
    data['hands'][side]=transform(Matrix.Rotation(math.radians(data['grip_roll_deg'][side]),4,'Z')@nt.inverted()@posed[hand])
    for n in posed:
        if n==hand or not n.endswith('_'+side):continue
        parent=next(k for k,v in native['bones'].items() if v['index']==native['bones'][n]['parent'])
        local=posed[parent].inverted()@posed[n]
        data['finger_rotations'][n]=transform(local)['q']
# Fit the accepted curl to the actual tool sections. This is an authoring solve:
# rotations only, bounded about the accepted grip, with native lengths unchanged.
# The tongs are two narrow reins, not a second full-diameter hammer handle.
from mathutils import Quaternion
by_index={v['index']:n for n,v in native['bones'].items()}
ordered=sorted(nrest,key=lambda n:native['bones'][n]['index'])
parent_of={n:by_index.get(native['bones'][n]['parent']) for n in ordered}
nlocal={n:nrest[parent_of[n]].inverted()@nrest[n] if parent_of[n] else nrest[n] for n in ordered}
positions=np.asarray(skin['positions'],dtype=float)*.01
inverse={n:np.asarray(nrest[n].inverted(),dtype=float) for n in nrest}
for side in ('r','l'):
    h=data['hands'][side];wrist=Matrix.LocRotScale(Vector(h['p'])*.01,Quaternion((h['q'][3],*h['q'][:3])),Vector((1,1,1)))
    rotations={n:Quaternion((q[3],*q[:3])) for n,q in data['finger_rotations'].items() if n.endswith('_'+side)}
    base={n:q.copy() for n,q in rotations.items()};deltas={n:[0.,0.] for n in rotations}
    for digit in ('thumb','index','middle','ring','pinky'):
        ids=[i for i,w in enumerate(skin['weights']) if sum(v for n,v in w.items() if n.startswith(digit) and n.endswith('_'+side))>.65]
        if not ids:continue
        ids=ids[::max(1,len(ids)//400)]
        points=np.concatenate([positions[ids],np.ones((len(ids),1))],axis=1)
        influences={n:np.array([skin['weights'][i].get(n,0.) for i in ids]) for n in nrest}
        influences={n:w for n,w in influences.items() if w.max()>0}
        mapped={n:points@inverse[n].T for n in influences}
        # Preserve the accepted metacarpal fan; close phalanges around the tool.
        chain=[n for n in ordered if n in rotations and n.startswith(digit) and 'metacarpal' not in n]
        def cost():
            p={};fallback=wrist@nrest['hand_'+side].inverted()
            for n in ordered:
                if n=='hand_'+side:p[n]=wrist
                elif n in rotations:p[n]=p[parent_of[n]]@Matrix.LocRotScale(nlocal[n].translation,rotations[n],Vector((1,1,1)))
                else:p[n]=fallback@nrest[n]
            skinned=sum((mapped[n]@np.asarray(p[n],dtype=float).T)*w[:,None] for n,w in influences.items())[:,:3]
            active=skinned[np.abs(skinned[:,2])<.078]
            if len(active)==0:return 1.
            if side=='r':
                sd=(np.sqrt((active[:,0]/.014)**2+(active[:,1]/.012)**2)-1)*.012
            else:
                sd=np.minimum(*[(np.sqrt(((active[:,0]-s*.008)/.0038)**2+(active[:,1]/.0035)**2)-1)*.0035 for s in (-1,1)])
            nearest=float(sd.min());penetration=np.maximum(0,-sd-.0005)
            deviation=sum(y*y+z*z for n,(y,z) in deltas.items() if n in chain)
            return (nearest-.0007)**2+15*float(np.mean(penetration**2))+deviation*1.2e-5
        for iteration in range(9):
            for n in chain:
                for axis in range(2):
                    best=cost();angle=deltas[n][axis];chosen=angle
                    for candidate in (angle-math.radians(2),angle+math.radians(2)):
                        if abs(candidate)>math.radians(22):continue
                        deltas[n][axis]=candidate;y,z=deltas[n]
                        rotations[n]=base[n]@Quaternion((0,1,0),y)@Quaternion((0,0,1),z)
                        score=cost()
                        if score<best:best=score;chosen=candidate
                    deltas[n][axis]=chosen;y,z=deltas[n]
                    rotations[n]=base[n]@Quaternion((0,1,0),y)@Quaternion((0,0,1),z)
        for n in chain:
            q=rotations[n].normalized();data['finger_rotations'][n]=[q.x,q.y,q.z,q.w]
data['grasp_authoring']='Accepted cylindrical donor, bounded native finger rotation fit against ellipse / paired tong reins; no bone scaling'
DATA.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')

bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
bpy.context.preferences.filepaths.save_version=0
materials={}
for name,color,metal,rough in [('AgedSteel',(.05,.044,.036),.7,.78),('StruckFace',(.15,.14,.12),.9,.59),('AshHandle',(.11,.065,.026),0,.68),('HotBlank',(.16,.05,.014),.7,.8),('Guide',(.95,.24,.025),0,.6)]:
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    materials[name]=m
def co(p):return Vector((p[0],-p[1],p[2]))*.01
def mesh(name,points,faces,mat):
    d=bpy.data.meshes.new(name);d.from_pydata([co(p) for p in points],[],[tuple(reversed(f)) for f in faces]);d.update()
    o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);d.materials.append(materials[mat]);return o
def bevel(o,width=.08):
    mod=o.modifiers.new('Forged edge radius','BEVEL');mod.width=width*.01;mod.segments=3
    mod=o.modifiers.new('Weighted working normals','WEIGHTED_NORMAL');mod.keep_sharp=True
def box(name,center,size,mat,r=.08):
    p=[tuple(center[i]+size[i]*sign[i]/2 for i in range(3)) for sign in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    o=mesh(name,p,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat);bevel(o,r);return o
def loft(name,rings,mat,axis='Z',segments=24):
    p=[]
    for t,a,b in rings:
        for j in range(segments):
            u=j*math.tau/segments
            p.append((a*math.cos(u),b*math.sin(u),t) if axis=='Z' else (t,a*math.cos(u),21+b*math.sin(u)))
    faces=[]
    for k in range(len(rings)-1):
        for j in range(segments):faces.append((k*segments+j,k*segments+(j+1)%segments,(k+1)*segments+(j+1)%segments,(k+1)*segments+j))
    faces += [tuple(reversed(range(segments))),tuple((len(rings)-1)*segments+j for j in range(segments))]
    o=mesh(name,p,faces,mat)
    for f in o.data.polygons:f.use_smooth=len(f.vertices)==4
    return o
def export(name,objects):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:
        bpy.context.view_layer.objects.active=ob
        for mod in list(ob.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
        ob.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();o=bpy.context.object;o.name=name
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT')
    color=o.data.color_attributes.new(name='Wear',type='FLOAT_COLOR',domain='CORNER')
    for poly in o.data.polygons:
        wear=.8 if o.data.materials[poly.material_index].name=='StruckFace' else .08
        for li in poly.loop_indices:color.data[li].color=(wear,0,0,1)
    tri=o.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH'},apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_NONE',axis_forward='-Y',axis_up='Z',use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=True,bake_anim=False)
    o.hide_set(True);return o
hammer=[]
hammer.append(loft('Oval ash handle',[(-11,1.75,1.40),(-9,1.70,1.33),(-5,1.42,1.21),(0,1.40,1.20),(5,1.45,1.22),(13,1.55,1.26),(19,1.52,1.25),(23.4,1.45,1.20)],'AshHandle'))
hammer.append(box('Forged eye block',(.0,0,21),(6,4.9,5.3),'AgedSteel',.23))
hammer.append(box('Flat striking head',(4.75,0,21),(3.7,4.8,4.8),'AgedSteel',.20))
hammer.append(box('Mushroomed striking face',(6.55,0,21),(.5,4.65,4.65),'StruckFace',.10))
# Cross peen: rectangular loft tapering across X, rounded over at its narrow end.
pts=[]
for x,hy,hz in [(-2.7,2.4,2.5),(-5.7,2.0,.9),(-7.1,1.9,.45)]:pts += [(x,-hy,21-hz),(x,hy,21-hz),(x,hy,21+hz),(x,-hy,21+hz)]
peen=mesh('Cross peen',pts,[(0,3,2,1),(8,9,10,11)]+[(k+j,k+(j+1)%4,k+4+(j+1)%4,k+4+j) for k in (0,4) for j in range(4)],'AgedSteel');bevel(peen,.16);hammer.append(peen)
hammer.append(box('Steel eye wedge',(0,0,23.67),(.35,2.25,.3),'StruckFace',.035))
ho=export('SM_ForgeHammer',hammer)
# Closed flat-bit tongs: local Z runs from hand to the jaw; origin is the held handle.
parts=[]
for sign in (-1,1):
    rings=[(-8,.35,.35),(0,.38,.35),(11,.5,.42),(15,.55,.42),(20,.42,.36)]
    ob=loft('Tong reins',rings,'AgedSteel',segments=12)
    for v in ob.data.vertices:
        z=v.co.z*100;v.co.x+=sign*(.80 if z<10 else .80*(20-z)/10)*.01
    parts.append(ob)
    parts.append(box('Flat tong jaw',(sign*.75,0,23.2),(.55,2.0,6.4),'StruckFace',.09))
parts.append(box('Tong hinge',(0,0,15.5),(2.3,1.6,2.6),'AgedSteel',.3))
parts.append(box('Hinge rivet',(0,-.91,15.5),(1.0,.3,1.0),'StruckFace',.25))
to=export('SM_ForgeTongs',parts)
for stage in range(3):
    # Sword blank rests on the anvil: origin at its supported center, tang on -X.
    pts=[]
    for x,width in [(-31,1.2),(-22,1.2),(-21,2.6),(-8,2.55),(16,2.35),(25,1.65),(30,.08)]:
        w=width*(1+.12*(2-stage));h=.95
        pts.extend([(x,-w,0),(x,w,0),(x,w,h*.4),(x,0,h),(x,-w,h*.4)])
    faces=[tuple(reversed(range(5))),tuple(range(30,35))]
    faces.extend((i*5+j,i*5+(j+1)%5,(i+1)*5+(j+1)%5,(i+1)*5+j) for i in range(6) for j in range(5))
    o=mesh('Blank',pts,faces,'HotBlank');bevel(o,.07);export('SM_ForgeBlank'+str(stage),[o])
# A true open ring, not an opaque square or decal: world-space heat/aim guide.
p=[];f=[]
for rad in (1.65,1.85):
    for j in range(48):p.append((rad*math.cos(j*math.tau/48),rad*math.sin(j*math.tau/48),0))
for j in range(48):f.append((j,(j+1)%48,48+(j+1)%48,48+j))
export('SM_ForgeRing',[mesh('Heat ring',p,f,'Guide')])
export('SM_ForgeSpark',[box('Hot scale',(0,0,0),(.6,.075,.075),'Guide',.01)])

# Editable native V7 skin/rig alongside the tool, with the authored gripping hands.
for o in bpy.context.scene.objects:o.hide_set(True)
mirror=Matrix.Diagonal((1,-1,1,1))
arm=bpy.data.armatures.new('V7_M4_NativeForge');rig=bpy.data.objects.new('V7_M4_NativeForge',arm);bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for n,v in sorted(native['bones'].items(),key=lambda x:x[1]['index']):
    eb=arm.edit_bones.new(n);m=mirror@nrest[n]@mirror;eb.matrix=m;eb.length=.025
    if v['parent']>=0:
        parent=next(k for k,d in native['bones'].items() if d['index']==v['parent']);eb.parent=arm.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT')
ob=mesh('Accepted_BareArms_V7',skin['positions'],skin['triangles'],'AshHandle')
ob.data.materials.clear();m=bpy.data.materials.new('V7 skin source material');m.diffuse_color=(.36,.21,.14,1);ob.data.materials.append(m)
for n in native['bones']:ob.vertex_groups.new(name=n)
for i,w in enumerate(skin['weights']):
    for n,value in w.items():ob.vertex_groups[n].add([i],value,'REPLACE')
mod=ob.modifiers.new('Native inverse binds','ARMATURE');mod.object=rig
for n in posed:
    if n.startswith(('index','middle','ring','pinky','thumb')):
        q=data['finger_rotations'][n];local=(nrest[next(k for k,v in native['bones'].items() if v['index']==native['bones'][n]['parent'])].inverted()@nrest[n]);
        from mathutils import Quaternion
        pm=Matrix.LocRotScale(local.translation,Quaternion((q[3],q[0],q[1],q[2])),Vector((1,1,1)))
        rig.pose.bones[n].matrix_basis=(mirror@local@mirror).inverted()@(mirror@pm@mirror)
ho.hide_set(False);to.hide_set(False)
# Keep source motion and the runtime supported-wrist solver in the same authoring path.
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from forge_arm_pose import bake_motion
bake_motion(scene,rig,ho,to,nrest,data)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ForgeTools_V7_Grasp.blend'))
(OUT/'provenance.json').write_text(json.dumps({'geometry':'Original parametric forge tools authored for FPSGAME','grip':'Existing licensed Manny grasp donor; V7 native skeleton retained','materials':'Existing project wrought iron and Normandy wood; no downloaded external assets','scale':'UE cm; FBX_SCALE_NONE','runtime_tested':False},indent=2),encoding='utf8')
print('FORGE_AUTHORED',str(OUT),flush=True)
