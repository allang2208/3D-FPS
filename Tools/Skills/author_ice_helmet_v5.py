"""Author the approved continuous first-person ice helmet. No render or game run."""
import json,math
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/IceArmor20261017/HelmetV5';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
# The inner contour is an actual hole. Coordinates are normalized camera rays,
# not a transparent center polygon. The bottom center dips below the aim area.
right=[(0,.76),(.30,.77),(.58,.81),(.71,.74),(.78,.57),(.81,.30),(.82,.02),(.79,-.24),(.75,-.49),(.74,-.65),(.60,-.77),(.28,-.79),(0,-.84)]
contour=[Vector(p) for p in right+[(-x,y) for x,y in right[-2:0:-1]]]
def outline(t):
    j=int(t)%len(contour);f=t-math.floor(t)
    a,b,c,d=[contour[k%len(contour)] for k in (j-1,j,j+1,j+2)]
    return .5*((2*b)+(-a+c)*f+(2*a-5*b+4*c-d)*f*f+(-a+3*b-3*c+d)*f*f*f)
# Expansion away from the open face / distance from eye in cm / frost / depth.
# Front and back surfaces form one closed, thick cross section around the hole.
sections=[(0,42,.68,.20),(.025,40.8,.88,.40),(.10,38.8,.36,.72),(.28,35.1,.08,1),(.58,30.5,.24,1),(1.02,26.5,.68,.78),(1.10,29.4,.65,.74),(.64,34.1,.24,1),(.28,39.0,.14,.92),(.06,44.4,.38,.56),(0,45.0,.55,.22)]
N=128;S=len(sections);points=[];attributes=[]
for i in range(N):
    theta=i*2*math.pi/N;inner=outline(i*len(contour)/N)
    for j,(expansion,depth,frost,thickness) in enumerate(sections):
        ray=inner*(1+expansion*.50)
        # Broad, continuous cleavage planes: no detached shards or jagged holes.
        cleavage=(math.acos(math.cos(theta*9+.25))/math.pi-.5)*.34
        actual_depth=depth+cleavage*math.sin(math.pi*j/(S-1))
        points.append(Vector((actual_depth-42,ray.x*50*actual_depth/42,ray.y*50*actual_depth/42)))
        uv=[ray.x*.5+.5,ray.y*.5+.5]
        attributes.append((uv,[i/N,j/(S-1)],[max(.0,min(1,frost*(.90+.10*math.cos(theta*5)**2))),0,thickness,1]))
triangles=[]
for i in range(N):
    nxt=(i+1)%N;center=sum((points[i*S+j]+points[nxt*S+j] for j in range(S)),Vector())/(2*S)
    for j in range(S):
        nj=(j+1)%S
        for ids in ((i*S+j,nxt*S+j,nxt*S+nj),(i*S+j,nxt*S+nj,i*S+nj)):
            a,b,c=(points[k] for k in ids);normal=(b-a).cross(c-a)
            if normal.dot((a+b+c)/3-center)<0:ids=(ids[0],ids[2],ids[1])
            triangles.append(ids)
# Smooth the broad inner bowl while retaining the tight faceted bevels.
smooth=[Vector() for _ in points]
for a,b,c in triangles:
    n=(points[b]-points[a]).cross(points[c]-points[a])
    for k in (a,b,c):smooth[k]+=n
for n in smooth:n.normalize()
data={'name':'SM_IceHelmet_FirstPerson','positions':[],'normals':[],'uv':[],'uv1':[],'uv2':[],'colors':[],'triangles':[],'weights':[],'skinned':False,'triangle_winding':'unreal_clockwise'}
for ids in triangles:
    a,b,c=(points[k] for k in ids);face=(b-a).cross(c-a).normalized();row=[]
    for k in ids:
        j=k%S;blend=.28 if 2<=j<=8 else .08;n=(face*(1-blend)+smooth[k]*blend).normalized()
        uv,meta,color=attributes[k];row.append(len(data['positions']))
        data['positions'].append(list(points[k]));data['normals'].append(list(n));data['uv'].append(uv);data['uv1'].append(uv);data['uv2'].append(meta);data['colors'].append(color);data['weights'].append([])
    # UE front face is clockwise, opposite Blender's outward cross-product rule.
    data['triangles'].append([row[0],row[2],row[1]])
(OUT/(data['name']+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
mesh=bpy.data.meshes.new(data['name']);mesh.from_pydata(data['positions'],[],[(a,c,b) for a,b,c in data['triangles']]);mesh.update()
for key,channel in (('uv','IceSurface'),('uv1','Formation'),('uv2','HelmetSection')):
    layer=mesh.uv_layers.new(name=channel)
    for loop in mesh.loops:layer.data[loop.index].uv=data[key][loop.vertex_index]
colors=mesh.color_attributes.new(name='FrostThickness',type='FLOAT_COLOR',domain='CORNER')
for loop in mesh.loops:colors.data[loop.index].color=data['colors'][loop.vertex_index]
obj=bpy.data.objects.new(data['name'],mesh);bpy.context.collection.objects.link(obj)
obj['reference']='FirstPersonDesignV5/ice-helmet-first-person-v2.png';obj['native_camera_distance_cm']=42
obj['aperture']='Open geometry, central view contains no polygons';obj['winding']='Blender outward; JSON clockwise for UE'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'IceHelmetV5.blend'))
(OUT/'authoring-manifest.json').write_text(json.dumps({'mesh':data['name'],'triangles':len(data['triangles']),'vertices':len(data['positions']),'camera_distance_cm':42,'rim_front_back_cm':[42,45],'cavity_depth_cm':[26.5,45],'central_open_region_ndc':{'left':-.68,'right':.68,'bottom':-.62,'top':.62},'reference':obj['reference'],'rendered':False},indent=2),encoding='utf-8')
print('ICE_HELMET_V5_AUTHORED',flush=True)
