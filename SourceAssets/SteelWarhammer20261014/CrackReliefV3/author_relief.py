"""Bake original fracture relief/PBR maps, not a preview or acceptance render."""
import heapq,json,math
from pathlib import Path
import numpy as np
from scipy.spatial import Voronoi,cKDTree
from scipy.ndimage import distance_transform_edt,gaussian_filter,zoom
from PIL import Image,ImageDraw

P=Path(__file__).resolve().parent;N=2048;SEED=141046
rng=np.random.default_rng(SEED)
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def noise(res):
    data=rng.random((res,res),dtype=np.float32)
    return zoom(data,N/res,order=1)[:N,:N]

# Large fractured slabs outside, small crushed chips immediately below the head.
grid=np.array([(x,y) for x in np.arange(-1.2,1.21,.17) for y in np.arange(-1.2,1.21,.17)])
grid+=rng.uniform(-.065,.065,grid.shape)
theta=rng.uniform(0,2*np.pi,38);radius=np.sqrt(rng.random(38))*.18
points=np.vstack([grid,np.column_stack([np.cos(theta)*radius,np.sin(theta)*radius])])
vor=Voronoi(points);vertices=vor.vertices
graph={i:[] for i,v in enumerate(vertices) if np.linalg.norm(v)<1.05}
edges=[]
for pair in vor.ridge_vertices:
    if len(pair)!=2 or min(pair)<0:continue
    a,b=pair
    if a not in graph or b not in graph:continue
    length=np.linalg.norm(vertices[a]-vertices[b])
    graph[a].append((b,length));graph[b].append((a,length));edges.append((a,b))

# Irregular interconnected fracture paths on the slab graph; no equal-angle spokes.
start=min(graph,key=lambda i:np.linalg.norm(vertices[i]))
selected={}
for angle,length in zip((.19,1.24,2.49,3.42,4.82,5.63),(.72,.49,.66,.56,.78,.58)):
    goal=np.array([math.cos(angle),math.sin(angle)])*length
    target=min(graph,key=lambda i:np.linalg.norm(vertices[i]-goal))
    distance={start:0.};previous={};queue=[(0.,start)]
    while queue:
        d,a=heapq.heappop(queue)
        if d>distance[a]:continue
        if a==target:break
        for b,span in graph[a]:
            inward=max(0,np.linalg.norm(vertices[a])-np.linalg.norm(vertices[b]))
            cost=d+span+inward*2.5
            if cost<distance.get(b,1e9):
                distance[b]=cost;previous[b]=a;heapq.heappush(queue,(cost,b))
    b=target
    while b in previous:
        a=previous[b];selected[tuple(sorted((a,b)))]=1.;b=a
for a,b in edges:
    r=np.linalg.norm((vertices[a]+vertices[b])*.5)
    if r<.20 or (r<.32 and rng.random()<.45):selected.setdefault(tuple(sorted((a,b))),.62)
# Small side failures attach to existing paths, instead of floating twig strokes.
branch_nodes={v for e in selected for v in e}
for a in list(branch_nodes):
    if np.linalg.norm(vertices[a])<.24 or rng.random()>.23:continue
    options=[b for b,_ in graph[a] if tuple(sorted((a,b))) not in selected and np.linalg.norm(vertices[b])<.75]
    if options:selected[tuple(sorted((a,int(rng.choice(options)))))]=.35

line=Image.new('L',(N,N));width_map=Image.new('F',(N,N));depth_map=Image.new('F',(N,N))
draw=ImageDraw.Draw(line);width_draw=ImageDraw.Draw(width_map);depth_draw=ImageDraw.Draw(depth_map)
segments=[]
for (a,b),strength in selected.items():
    start_point,end_point=vertices[a],vertices[b]
    span=np.linalg.norm(end_point-start_point)
    tangent=(end_point-start_point)/max(span,1e-6);normal=np.array([-tangent[1],tangent[0]])
    count=max(5,int(span/.007));jitter=rng.normal(0,.0016,count)
    jitter[0]=jitter[-1]=0
    samples=np.linspace(start_point,end_point,count)+jitter[:,None]*normal
    for u,v in zip(samples[:-1],samples[1:]):
        r=np.linalg.norm((u+v)*.5)
        taper=float(1-smooth(.20,.82,r))
        radius_px=max(.42,(.0005+.0024*taper)*N/2*strength*rng.uniform(.75,1.2))
        pixel=[tuple((p*.5+.5)*(N-1)) for p in (u,v)]
        draw.line(pixel,fill=255,width=1)
        width_draw.line(pixel,fill=radius_px,width=1)
        depth_draw.line(pixel,fill=(.30+1.15*taper)*strength,width=1)
    segments.append({'a':start_point.tolist(),'b':end_point.tolist(),'weight':strength})

mask=np.asarray(line)>0
distance,index=distance_transform_edt(~mask,return_indices=True)
distance=distance.astype(np.float32)
width=np.asarray(width_map)[index[0],index[1]]
depth=np.asarray(depth_map)[index[0],index[1]]
del index
y,x=np.mgrid[-1:1:complex(N),-1:1:complex(N)].astype(np.float32)
r=np.sqrt(x*x+y*y)
coarse=noise(25);medium=noise(140);fine=noise(620)
broken=1-smooth(.16,.235+(coarse-.5)*.045,r)
chip_width=width*(1.7+medium*2.7)
cavity=1-smooth(width*.20,width*1.10,distance)
bevel=1-smooth(width*.6,chip_width+1.5,distance)
chips=(1-smooth(chip_width,chip_width+3.5,distance))*(.25+.75*medium)
height=-depth*(cavity*.72+bevel*.28)

# The centre is a set of individually tilted, chipped pieces, not a flat dark disk.
labels=cKDTree(points).query(np.column_stack([x.ravel(),y.ravel()]),workers=4)[1].reshape(N,N)
offset=rng.uniform(-1.5,.6,len(points)).astype(np.float32)
tilt=rng.uniform(-2.5,2.5,(len(points),2)).astype(np.float32)
slabs=offset[labels]+tilt[labels,0]*(x-points[labels,0])+tilt[labels,1]*(y-points[labels,1])
height+=broken*(slabs-.85)*(1-bevel*.55)
height+=(fine-.5)*.12*(broken+bevel*.5)
height=gaussian_filter(height.astype(np.float32),.65)
# Millimetre-scale fragment bevels in a 3.96 m decal; physical normal gradients.
dy,dx=np.gradient(height,396./N)
normal=np.stack([-dx,dy,np.ones_like(dx)],axis=-1)
normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
alpha=np.maximum(cavity*.70,np.maximum(bevel*.42,broken*.52))
alpha=np.maximum(alpha,chips*.14)* (1-smooth(.79,.92,r))
alpha*=smooth(0,.025,np.minimum.reduce([x+1,1-x,y+1,1-y]))
# Neutral stone shading stays semi-transparent so the receiving floor still reads.
grey=.49+(coarse-.5)*.05+(fine-.5)*.08
grey=grey*(1-cavity*.60)+chips*.075*(1-cavity)
grey+=broken*(slabs*.025)
colour=np.stack([grey*1.015,grey,grey*.97],axis=-1)
rough=np.clip(.76+fine*.20+bevel*.04,0,1)
packed=np.stack([alpha,cavity,rough,np.clip((height+4)/6,0,1)],axis=-1)
def save(name,data):Image.fromarray(np.rint(np.clip(data,0,1)*255).astype(np.uint8)).save(P/name)
save('T_WarhammerFractureColor.png',colour)
save('T_WarhammerFractureNormal.png',normal*.5+.5)
save('T_WarhammerFractureMasks.png',packed)
np.save(P/'FractureHeightCM.npy',height)
recipe={'resolution':N,'seed':SEED,'source':'Original offline Voronoi fracture height field',
    'physical_width_cm':396,'normal_convention':'DirectX','maps':{
        'Color':'sRGB stone grains, cavity and chipped edge color',
        'Normal':'linear DirectX normal from physical height gradient',
        'Masks':'R coverage; G cavity; B roughness; A normalized source height'},
    'segments':segments,'gameplay_modified':False,'preview_rendered':False,'runtime_tested':False}
(P/'authored.json').write_text(json.dumps(recipe,indent=2),encoding='utf-8')
print('WARHAMMER_FRACTURE_MAPS_AUTHORED '+json.dumps({'maps':3,'resolution':N,'segments':len(segments)}))
