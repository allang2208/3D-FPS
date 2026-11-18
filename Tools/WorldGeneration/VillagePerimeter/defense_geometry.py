"""Author centimetre-scale oak gates, forged fittings and masonry fracture clusters."""
import json, math, importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'SourceAssets/VillageDefenses20261117'
spec=importlib.util.spec_from_file_location('wall_geometry',Path(__file__).with_name('wall_geometry.py'))
wall=importlib.util.module_from_spec(spec);spec.loader.exec_module(wall)

def beam(m,a,b,width,depth,slot):
    # Bevelled timber with grain UVs following the length, regardless of its angle.
    a=list(a);b=list(b);d=[b[i]-a[i] for i in range(3)];length=math.sqrt(sum(v*v for v in d));d=[v/length for v in d]
    side=[d[2],0,-d[0]];w=width/2;h=depth/2;e=min(1.1,w*.15,h*.15)
    shape=[(-w+e,-h),(w-e,-h),(w,-h+e),(w,h-e),(w-e,h),(-w+e,h),(-w,h-e),(-w,-h+e)]
    rings=[[[p[i]+side[i]*x+(y if i==1 else 0) for i in range(3)] for x,y in shape] for p in (a,b)]
    first=len(m.groups[slot]['vertices']);m.solid(rings,slot)
    data=m.groups[slot]
    offset=m.rng.random()*5
    for i in range(first,len(data['vertices'])):
        q=[data['vertices'][i][j]-a[j] for j in range(3)]
        data['uv0'][i]=[sum(q[j]*side[j] for j in range(3))/95+offset,sum(q[j]*d[j] for j in range(3))/130]

def gate(width,seed):
    m=wall.Mesh(seed)
    for slot in ('Oak','Iron'):m.groups[slot]={k:[] for k in ('vertices','normals','uv0','uv1','triangles')}
    count=round(width/23);step=width/count
    for i in range(count):
        x=(i+.5)*step;top=213+m.rng.uniform(-1.5,1.5)
        beam(m,(x,0,12),(x,0,top),step-.65,10,'Oak')
        # Shallow splits in a few planks are geometry, never full-width holes.
        if i%4==1:beam(m,(x+step*.2,-5.18,150),(x+step*.18,-5.18,190),.3,.18,'Iron')
    for z in (42,112,184):
        beam(m,(7,8,z),(width-7,8,z),17,12,'Oak')
        beam(m,(1,-6.4,z),(width-5,-6.4,z),6,2.4,'Iron')
        for x in range(14,int(width-6),30):
            m.stone(x-1.2,x+1.2,-9,-6,z-1.3,z+1.3,'Iron')
    beam(m,(16,17,46),(width-16,17,180),16,8,'Oak')
    # Inset hinge barrels leave the 59 cm wall-pier setback unobstructed.
    for z in (43,184):
        beam(m,(3,-10,z-11),(3,-10,z+11),8,8,'Iron')
    beam(m,(width-24,-11,92),(width-24,-11,116),3,3,'Iron')
    for z in (92,116):beam(m,(width-30,-9,z),(width-18,-9,z),3,5,'Iron')
    m.collision(0,width,-10,21,12,215)
    return m.data()

def chunk(seed):
    m=wall.Mesh(seed)
    m.block(-40,40,-21,21,-24,24)
    for side in (-1,1):
        for row in range(2):
            for col in range(2):
                x=-48+col*48
                m.stone(x,x+49,side*22-9,side*22+9,-26+row*26,1+row*26,'YardField' if col else 'YardSlate')
    m.collision(-45,45,-27,27,-24,24);return m.data()

def shard():
    m=wall.Mesh(13);m.groups['Oak']={k:[] for k in ('vertices','normals','uv0','uv1','triangles')}
    beam(m,(-25,0,-47),(25,0,47),30,14,'Oak');m.collision(-35,35,-7,7,-48,48);return m.data()

def hinge_mount():
    m=wall.Mesh(351);m.groups['Iron']={k:[] for k in ('vertices','normals','uv0','uv1','triangles')}
    for z in (42,184):
        beam(m,(-49,-10,z),(4,-10,z),8,6,'Iron')
        beam(m,(-43,-10,z-16),(-43,-10,z+16),12,5,'Iron')
        for dz in (-11,11):m.stone(-45,-41,-15,-12,z+dz-2,z+dz+2,'Iron')
    return m.data()

def mirrored(data):
    import copy
    result=copy.deepcopy(data)
    for group in result['groups'].values():
        # Mesh.solid shares ring/cap lists across triangle corners. Deepcopy keeps
        # that aliasing: mutating each occurrence flips some points an even
        # number of times and leaves long fans across the hinge. Copy each corner.
        group['vertices']=[[-v[0],v[1],v[2]] for v in group['vertices']]
        group['normals']=[[-n[0],n[1],n[2]] for n in group['normals']]
        group['triangles']=[[tri[0],tri[2],tri[1]] for tri in group['triangles']]
    for box in result['collision_boxes']:box['center'][0]=-box['center'][0]
    return result

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    source={'GateWide':gate(428,661),'GateNarrow':gate(328,773),'StoneChunkA':chunk(31),'StoneChunkB':chunk(59),'WoodShard':shard()}
    source['GateHingeMount']=hinge_mount();source['GateHingeMountRight']=mirrored(source['GateHingeMount'])
    source['GateWideRight']=mirrored(source['GateWide']);source['GateNarrowRight']=mirrored(source['GateNarrow'])
    (OUT/'defense-mesh-source.json').write_text(json.dumps(source,separators=(',',':')),encoding='utf-8')
    (OUT/'design.json').write_text(json.dumps({'units':'cm','gate_leaf_widths':[428,328],'gate_height':215,'ground_clearance':12,'center_gap':6,'hinge_setbacks_from_exit_center':[431,331],'materials':['existing Normandy oak PBR','existing rusted iron PBR','chapel fieldstone PBR'],'health':{'wall':1200,'pier':1600,'double_gate':900,'ruined_wall':350,'ruined_pier':500},'repaired_height_multiplier':1.25},indent=2),encoding='utf-8')
    print({name:data['triangles'] for name,data in source.items()})
