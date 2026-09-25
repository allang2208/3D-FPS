"""Fit a true CC0 anatomical hand surface, then derive separate thin gloves.

Run after author_equipment.py. Weapon skeletons and animations are never edited.
"""
import bpy,bmesh,json,sys
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924')
DONOR=ROOT/'Donor/BareHands'
inputs=json.loads((ROOT/'inputs.json').read_text())
report=json.loads((ROOT/'authored.json').read_text())
only=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
coords=[];tex=[];faces=[];uv=[];group=''
for line in (DONOR/'base.obj').read_text().splitlines():
    t=line.split()
    if not t:continue
    if t[0]=='v':coords.append(Vector((float(t[1]),-float(t[3]),float(t[2])))*.1)
    elif t[0]=='vt':tex.append((float(t[1]),float(t[2])))
    elif t[0]=='g':group=t[1]
    elif t[0]=='f' and group=='body':
        corners=[s.split('/') for s in t[1:]]
        faces.append(tuple(int(s[0])-1 for s in corners));uv.append([tex[int(s[1])-1] for s in corners])
skel=json.loads((DONOR/'default.mhskel').read_text(encoding='utf-8'))
sourceweights=[{} for _ in coords]
for name,values in json.loads((DONOR/'default_weights.mhw').read_text(encoding='utf-8'))['weights'].items():
    for index,w in values:sourceweights[index][name]=w
joint=lambda name:sum((coords[i] for i in skel['joints'][name]),Vector())/len(skel['joints'][name])
bonehead=lambda name:joint(skel['bones'][name]['head'])
bonetail=lambda name:joint(skel['bones'][name]['tail'])

def frame(head,tail,across):
    x=(tail-head).normalized();z=x.cross(across).normalized();y=z.cross(x).normalized()
    m=Matrix((x,y,z)).transposed().to_4x4();m.translation=head;return m
def weights(obj,v):return {obj.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>.0001}
def bones(rig):
    result={}
    for b in rig.data.bones:
        raw=rig.matrix_world@b.matrix_local
        frame=raw.to_3x3().normalized().to_4x4();frame.translation=raw.translation
        result[b.name]=frame
    return result
def mesh(name,points,polygons,ws,uvs,materials,regions):
    data=bpy.data.meshes.new(name);data.from_pydata(points,[],polygons);data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    for n in sorted({n for w in ws for n in w}):obj.vertex_groups.new(name=n)
    for i,w in enumerate(ws):
        total=sum(w.values()) or 1
        for n,v in w.items():obj.vertex_groups[n].add([i],v/total,'REPLACE')
    for n in materials:data.materials.append(bpy.data.materials.get(n) or bpy.data.materials.new(n))
    layer=data.uv_layers.new(name='UVMap')
    for p in data.polygons:
        p.use_smooth=True;p.material_index=regions[p.index]
        for li,coord in zip(p.loop_indices,uvs[p.index]):layer.data[li].uv=coord
    return obj
def bind(obj,rig):
    obj.parent=rig;obj.matrix_parent_inverse=rig.matrix_world.inverted()
    mod=obj.modifiers.new('AcceptedPose','ARMATURE');mod.object=rig
def export(obj,rig,name):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(ROOT/'Exports'/(name+'.fbx')),use_selection=True,
        object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
        bake_anim=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',path_mode='STRIP')

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Body_Equipment.blend'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');target=bones(rig);base=bpy.data.objects['Base_Body']
canonical=target.copy();deforms={};mapped={};wrist_frames={}
base.data.calc_loop_triangles()
bodypoints=[base.matrix_world@v.co for v in base.data.vertices]
bodyweights=[weights(base,v) for v in base.data.vertices]
bodytris=[tuple(t.vertices) for t in base.data.loop_triangles]
bodybvh=BVHTree.FromPolygons(bodypoints,bodytris,all_triangles=True)
for side in ('l','r'):
    S=side.upper();wrist='wrist.'+S
    src_across=bonehead('finger2-1.'+S)-bonehead('finger5-1.'+S)
    dst_across=target['index_01_'+side].translation-target['pinky_01_'+side].translation
    h=target['hand_'+side].translation;e=target['lowerarm_'+side].translation
    wrist_frames[side]=(h,(h-e).normalized())
    definitions={wrist:('hand_'+side,bonehead(wrist),bonehead('finger3-1.'+S),h,target['middle_01_'+side].translation)}
    for i in (1,2):
        for prefix,dst,start,end in [('lowerarm','lowerarm_',bonehead('lowerarm01.'+S),bonehead(wrist)),('upperarm','upperarm_',bonehead('upperarm01.'+S),bonehead('lowerarm01.'+S))]:
            targettail=h if prefix=='lowerarm' else e
            definitions[f'{prefix}0{i}.{S}']=(dst+side,start,end,target[dst+side].translation,targettail)
    for f,stem in enumerate(('thumb','index','middle','ring','pinky'),1):
        for j in (1,2,3):
            src=f'finger{f}-{j}.{S}';dst=f'{stem}_{j:02}_{side}'
            a=target[dst].translation
            if j<3:b=target[f'{stem}_{j+1:02}_{side}'].translation
            else:
                direction=(a-target[f'{stem}_02_{side}'].translation).normalized()
                projections=[(v.co-a).dot(direction) for v in base.data.vertices if weights(base,v).get(dst,0)>.5]
                length=min(.045,max(.015,max(projections,default=.023)))
                b=a+direction*length
            definitions[src]=(dst,bonehead(src),bonetail(src),a,b)
    for src,(dst,a,b,ta,tb) in definitions.items():
        scale=(tb-ta).length/max(.0001,(b-a).length)
        deforms[src]=frame(ta,tb,dst_across)@Matrix.Diagonal((scale,scale,scale,1))@frame(a,b,src_across).inverted()
        mapped[src]=dst
    for i in (1,2,3,4):
        deforms[f'metacarpal{i}.{S}']=deforms[wrist];mapped[f'metacarpal{i}.{S}']='hand_'+side

points=[];ws=[]
for p,w in zip(coords,sourceweights):
    usable={n:v for n,v in w.items() if n in deforms};total=sum(usable.values())
    points.append(sum((deforms[n]@p*v for n,v in usable.items()),Vector())/total if total else p)
    out={}
    for n,v in usable.items():out[mapped[n]]=out.get(mapped[n],0)+v/(total or 1)
    ws.append(out)
def axial(p,side):
    h,axis=wrist_frames[side];return (p-h).dot(axis)
for i,p in enumerate(points):
    if not ws[i]:continue
    side='l' if coords[i].x>0 else 'r';distance=axial(p,side)
    if -.075<distance<-.015:
        blend=min(1,max(0,(-distance-.015)/.025));blend=blend*blend*(3-2*blend)
        near,normal,ti,_=bodybvh.find_nearest(p)
        tri=bodytris[ti];a,b,c=(bodypoints[v] for v in tri)
        bc=barycentric_transform(near,a,b,c,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
        w={n:v*(1-blend) for n,v in ws[i].items()}
        for vi,f in zip(tri,bc):
            for n,v in bodyweights[vi].items():w[n]=w.get(n,0)+max(0,f)*v*blend
        ws[i]={n:v for n,v in w.items() if v>.0001}
        points[i]=p.lerp(near-normal*.0008,blend)
chosen=[]
for i,f in enumerate(faces):
    side='l' if sum(coords[v].x for v in f)>0 else 'r'
    if all(ws[v] and axial(points[v],side)>-.06 for v in f):
        if all(sum(w for n,w in ws[v].items() if n.endswith('_'+side))>.95 for v in f):chosen.append(i)
used=sorted({v for i in chosen for v in faces[i]});remap={v:i for i,v in enumerate(used)}
hp=[points[i] for i in used];hw=[ws[i] for i in used]
hf=[tuple(remap[v] for v in faces[i]) for i in chosen];huv=[uv[i] for i in chosen]
hr=[]
for f in hf:
    side='l' if sum(hp[v].x for v in f)>0 else 'r'
    hr.append(1 if sum(axial(hp[v],side) for v in f)/len(f)>-.008 else 0)
hand=mesh('AnatomicalHandsMaster',hp,hf,hw,huv,['SkinArms','SkinHands'],hr)
# One subdivision preserves the anatomical topology and rounds finger silhouettes.
bpy.ops.object.select_all(action='DESELECT');hand.select_set(True);bpy.context.view_layer.objects.active=hand
sub=hand.modifiers.new('FingerSurface','SUBSURF');sub.levels=1;bpy.ops.object.modifier_apply(modifier=sub.name)
hp=[v.co.copy() for v in hand.data.vertices];hw=[weights(hand,v) for v in hand.data.vertices]
hf=[tuple(p.vertices) for p in hand.data.polygons];huv=[[tuple(hand.data.uv_layers.active.data[i].uv) for i in p.loop_indices] for p in hand.data.polygons];hr=[p.material_index for p in hand.data.polygons]
bind(hand,rig);bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'AnatomicalHands_Master.blend'))

for key,entry in inputs.items():
    if only and key not in only:continue
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/(key+'_Equipment.blend')))
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');target=bones(rig)
    old=bpy.data.objects['Base_'+key];oldglove=bpy.data.objects['Gloves_'+key]
    delta={n:target[n]@canonical[n].inverted() for n in canonical if n in target}
    sides=tuple(report[key]['sides'])
    converted=[]
    for p,w in zip(hp,hw):
        valid={n:v for n,v in w.items() if n in delta};total=sum(valid.values())
        converted.append(sum((delta[n]@p*v for n,v in valid.items()),Vector())/(total or 1))
    # Keep the accepted forearms and body; remove only their old glove-shaped hands.
    keep=[p for p in old.data.polygons if old.data.materials[p.material_index].name!='SkinHands']
    ids=sorted({v for p in keep for v in p.vertices});remap={v:i for i,v in enumerate(ids)}
    bp=[old.matrix_world@old.data.vertices[i].co for i in ids];bw=[weights(old,old.data.vertices[i]) for i in ids]
    bf=[tuple(remap[v] for v in p.vertices) for p in keep]
    buv=[[tuple(old.data.uv_layers.active.data[i].uv) for i in p.loop_indices] for p in keep]
    br=[p.material_index for p in keep];materials=[m.name for m in old.data.materials]
    chosen=[i for i,f in enumerate(hf) if ('l' if sum(hp[v].x for v in f)>0 else 'r') in sides]
    used=sorted({v for i in chosen for v in hf[i]});rm={v:i+len(bp) for i,v in enumerate(used)}
    bp.extend(converted[i] for i in used);bw.extend(hw[i] for i in used)
    bf.extend(tuple(rm[v] for v in hf[i]) for i in chosen);buv.extend(huv[i] for i in chosen);br.extend(hr[i] for i in chosen)
    base=mesh('ReplacementBase',bp,bf,bw,buv,materials,br)
    bpy.data.objects.remove(old,do_unlink=True);base.name='Base_'+key;bind(base,rig)
    # Separate glove shell follows the same anatomical surface. It grows outward,
    # while the covered bare-hand section disappears at equip time.
    gi=[i for i in chosen if sum(axial(hp[v],'l' if hp[v].x>0 else 'r') for v in hf[i])/len(hf[i])>-.030]
    used=sorted({v for i in gi for v in hf[i]});rm={v:i for i,v in enumerate(used)}
    glove=mesh('ReplacementGloves',[converted[i] for i in used],[tuple(rm[v] for v in hf[i]) for i in gi],
        [hw[i] for i in used],[huv[i] for i in gi],['Leather'],[0]*len(gi))
    for v in glove.data.vertices:v.co+=v.normal*.0011
    bpy.ops.object.select_all(action='DESELECT');glove.select_set(True);bpy.context.view_layer.objects.active=glove
    wall=glove.modifiers.new('RealWristHem','SOLIDIFY');wall.thickness=.0016;wall.offset=-1
    bpy.ops.object.modifier_apply(modifier=wall.name)
    bpy.data.objects.remove(oldglove,do_unlink=True);glove.name='Gloves_'+key;bind(glove,rig)
    export(base,rig,'SK_'+key+'_Base');export(glove,rig,'SK_'+key+'_Gloves')
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/(key+'_Equipment.blend')))
    report[key]['anatomical_hands']='MakeHuman hm08 CC0, landmark fit to accepted finger joints'
    report[key]['counts']['base']=len(base.data.polygons);report[key]['counts']['gloves']=len(glove.data.polygons)
    print('ANATOMICAL_HANDS_AUTHORED',key,len(glove.data.polygons),flush=True)
(ROOT/'authored.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
