"""Tailor actual glove junctions; retain the solved native sleeve fold field."""
import ast,sys,copy,json,math,hashlib,bpy,bmesh,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
sys.path.insert(0,str(Path(__file__).parent))
from combat3_cuff_solver import P,R,C,read,write,unit,normals,cuff_weights,strip_sleeve_finger_weights
from combat2_details import sew
def glove_cut(rig):
    source=next(row['file'] for row in read(C/'captured.json')['rows'] if row['key']=='Glove_'+rig);g=read(source);p=np.array(g['positions']);f=np.array(g['triangles']);materials=np.array(g['triangle_materials']);webbing={i for i,name in enumerate(g['material_slots']) if 'Webbing' in name};ids=set(np.unique(f[np.isin(materials,list(webbing))]).tolist());result={};record={}
    for side in ['l','r']:
        w=np.array(g['bones']['hand_'+side]['position']);axis=unit(w-np.array(g['bones']['lowerarm_'+side]['position']));sideids=[i for i,ws in enumerate(g['weights']) if sum(v for n,v in ws.items() if n.endswith('_'+side))>.5]
        if not sideids:continue
        dist=-(p[sideids]-w)@axis;strap=[float(d) for i,d in zip(sideids,dist) if i in ids and 0<d<6];end=max(strap,default=1.8);cut=max(2.3,end+.5);overlap=float(dist.max()-cut)
        if overlap<1.:raise RuntimeError('Insufficient native glove overlap '+rig+' '+side+' '+str(overlap))
        result[side]=cut;record[side]=dict(cut_cm=cut,strap_end_cm=end,nominal_overlap_cm=overlap)
    return result,record
def transport(name,q):
    data=np.load(C/'Simulation'/(name+'.npz'));before=data['before'];after=data['after'];tri=data['triangles'];tree=BVHTree.FromPolygons(before.tolist(),tri.tolist(),all_triangles=True);moved=q.copy();distances=[]
    for i,p in enumerate(q):
        hit=tree.find_nearest(Vector(p));ids=tri[hit[2]];distances.append(hit[3]);moved[i]+=np.array(barycentric_transform(hit[0],*[Vector(v) for v in before[ids]],*[Vector(v) for v in after[ids]]))-np.array(hit[0])
    return moved,float(max(distances))
def tailor(rig):
    file=C/'Authored'/f'shirt_fp_{rig}.json';previous=read(file)
    if previous.get('cloth_production',{}).get('glove_tailoring')=='measured-native-strap-v1':return
    cuts,contact=glove_cut(rig);row=next(x for x in read(C/'captured.json')['rows'] if x['key']=='Native_'+rig);native=read(row['file']);out=C/'Authored/TailoredBlank';out.mkdir(exist_ok=True)
    tree=ast.parse((P/'Tools/ST6SleeveRepair/author.py').read_text(encoding='utf-8'));code='\n'.join(ast.unparse(n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['unit','smooth','normals','build'])
    code=code.replace('w - lower * 1.0','w - lower * CUFF_CUT[side]').replace('w - lower * 3.8','w - lower * 4.4').replace('dist[face].mean() < 3.8','dist[face].mean() < 4.4')
    code=code.replace('0.34 + 0.25 * (1 - cuff) + folds','0.34 + 0.75 * (1 - cuff)').replace('along / 25','along / 8').replace('coords[:, 0] *= 1.5','coords[:, 0] *= 4.6875').replace('dist[face] / 25','dist[face] / 8').replace('length / 25','length / 8').replace('thickness / 25','thickness / 8')
    code=code.replace('if not faces:',"faces=[face for face in faces if all(sum(value for name,value in s['weights'][i].items() if name.startswith(('upperarm','lowerarm','hand_','thumb','index','middle','ring','pinky')))>.25 for i in face)]\n        if not faces:")
    ns=dict(json=json,copy=copy,math=math,hashlib=hashlib,Path=Path,bpy=bpy,bmesh=bmesh,np=np,Vector=Vector,read=read,OUT=out,CUFF_CUT=cuts);exec(compile(code,'measured_cuff_cut','exec'),ns);ns['build'](dict(profile=rig,file=row['file']))
    d=read(out/(rig+'.json'));byname={b['name']:b['index'] for b in previous['bones']};d['bones']=previous['bones'];d['source']=previous['source'];d['rig']=rig;d['weights']=[[[byname[n],w] for n,w in ws.items()] for ws in d['weights']];d['material_slots']=['CombatRipstop','CombatCuff','CombatLining'];dest='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR3/Materials/';d['materials']=[dest+'M_'+m for m in d['material_slots']]
    p=np.array(d['positions']);f=np.array(d['triangles']);outerids=np.concatenate([np.arange(part['first_vertex'],part['first_vertex']+part['vertices']//2) for part in d['parts']]);remap=np.full(len(p),-1,dtype=int);remap[outerids]=np.arange(len(outerids));tri=remap[f[(remap[f]>=0).all(1)]];q=p[outerids].copy();moved,distance=transport('FP_'+rig,q);new=p.copy();new[outerids]=moved;normal=normals(moved,tri)
    for part in d['parts']:
        side=part['name'][-1];start=part['first_vertex'];count=part['vertices']//2;ids=np.arange(start,start+count);w=np.array(native['bones']['hand_'+side]['position']);axis=unit(w-np.array(native['bones']['lowerarm_'+side]['position']));dist=-(p[ids]-w)@axis;cuff_weights(d,ids,dist,side)
        for i in ids:d['weights'][int(i+count)]=copy.deepcopy(d['weights'][int(i)])
        local=remap[ids];new[ids+count]=moved[local]-normal[local]*.12
    d['positions']=new.tolist();d['normals']=normals(new,f)[f].tolist();sew(d);d['materials']=[m.replace('CombatShirtR2','CombatShirtR3') for m in d['materials']];d['cloth_production']=dict(previous['cloth_production'],glove_tailoring='measured-native-strap-v1',contact=contact,max_fold_transfer_distance_cm=distance,paired_facing_weights=True)
    backup=C/'BeforeTailor';backup.mkdir(exist_ok=True)
    if not (backup/file.name).exists():write(backup/file.name,previous)
    strip_sleeve_finger_weights(d);write(file,d);write(C/'Review'/(rig+'-tailored.json'),dict(native=rig,contact=contact,max_fold_transfer_distance_cm=distance,gameplay_tested=False));print('CUFF_TAILORED_TO_NATIVE_GLOVE',rig,contact,flush=True)
if __name__=='__main__':
    rigs=sys.argv[sys.argv.index('--')+1].split(',')
    for rig in rigs:tailor(rig)
