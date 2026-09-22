"""Locate poorly conditioned proxy triangles beneath the reported render spike."""
import bpy,re,json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
root=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');out=root/'Spike20260922'
bpy.ops.wm.open_mainfile(filepath=str(root/'Authoring/WitchRebuilt_Master.blend'))
def field(text,key):
    start=text.index(key+'=(')+len(key)+1;depth=0
    for i in range(start,len(text)):
        depth+=(text[i]=='(')-(text[i]==')')
        if depth==0:return text[start+1:i]
def vecs(s):return np.array(re.findall(r'X=([^,]+),Y=([^,]+),Z=([^\)]+)',s),dtype=float)
result={}
for layer,name in [('Lower','Witch_OriginalRobe_Render'),('Upper','Witch_UpperRobe')]:
    text=(out/('WitchRebuilt_'+layer+'Drape04.t3d')).read_text()
    verts=vecs(field(text,'Vertices'));indices=np.array(field(text,'Indices').split(','),dtype=int).reshape(-1,3)
    tri=verts[indices];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);area=np.linalg.norm(cross,axis=1)*.5
    edges=np.stack([np.linalg.norm(tri[:,i]-tri[:,(i+1)%3],axis=1) for i in range(3)],axis=1)
    altitude=2*area/np.maximum(edges.max(axis=1),1e-12)
    tree=BVHTree.FromPolygons([Vector(v) for v in verts],indices.tolist(),all_triangles=True)
    obj=bpy.data.objects[name];worst=[];distances=[]
    for v in obj.data.vertices:
        p=obj.matrix_world@v.co;p=Vector((p.x*100,-p.y*100,p.z*100));closest,normal,i,d=tree.find_nearest(p)
        a,b,c=tri[i];e0=b-a;e1=c-a;e2=np.array(p)-a
        gram=np.array([[e0@e0,e0@e1],[e0@e1,e1@e1]])
        weights=np.linalg.solve(gram,np.array([e0@e2,e1@e2]));bary=np.array([1-weights.sum(),*weights])
        worst.append({'vertex':v.index,'proxy_triangle':int(i),'distance_cm':d,'rest_cm':list(p),'plane_bary':bary.tolist(),'max_abs':float(abs(bary).max())});distances.append(d)
    result[layer]={'proxy_vertices':len(verts),'triangles':len(indices),'min_triangle_area_cm2':float(area.min()),'min_altitude_cm':float(altitude.min()),'max_aspect_ratio':float((edges.max(axis=1)/np.maximum(altitude,1e-12)).max()),'proxy_gap_max_cm':max(distances),'proxy_gap_p95_cm':float(np.percentile(distances,95)),'worst_plane_projections':sorted(worst,key=lambda x:-x['max_abs'])[:8]}
(out/'proxy_geometry.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
