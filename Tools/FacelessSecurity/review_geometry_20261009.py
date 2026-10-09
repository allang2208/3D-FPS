"""Requested review of the latest cap shell and sleeve binding integrity."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri
B=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008');R=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurityReview20261009')
R.mkdir(parents=True,exist_ok=True)
report={'game_tested':False,'rendered':False}
bpy.ops.wm.open_mainfile(filepath=str(B/'V14/Authoring/SecurityServiceCap_Anatomical_V14.blend'))
shell=bpy.data.objects['SewnBandVisor_Source_V14'];me=shell.data
bm=bmesh.new();bm.from_mesh(me)
report['hat_shell']={'vertices':len(me.vertices),'faces':len(me.polygons),
    'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),
    'zero_area_faces':sum(f.calc_area()<1e-12 for f in bm.faces),'signed_volume_cm3':bm.calc_volume(signed=True)*1e6}
bm.free();me.calc_loop_triangles();p=[v.co.copy() for v in me.vertices];tris=[tuple(t.vertices) for t in me.loop_triangles]
tree=BVHTree.FromPolygons(p,tris,all_triangles=True);pairs=[]
for a,b in tree.overlap(tree):
    if a>=b or set(tris[a])&set(tris[b]):continue
    hit=False
    for ia,ib in [(a,b),(b,a)]:
        t=tris[ia];other=[p[i] for i in tris[ib]]
        for j in range(3):
            start=p[t[j]];direction=p[t[(j+1)%3]]-start
            if direction.length<1e-8:continue
            cross=intersect_ray_tri(*other,direction,start,True)
            if cross is not None:
                u=(cross-start).dot(direction)/direction.length_squared
                if 1e-5<u<1-1e-5:hit=True;break
        if hit:break
    if hit:pairs.append((a,b))
report['hat_shell']['nonadjacent_intersections']=len(pairs)
report['hat_shell']['intersection_examples']=pairs[:12]
# Check crown/band overlap at the crown's base around the full circumference.
gap=[]
for i in range(360):
    a=2*math.pi*i/360;z=1.750;alpha=(z-1.748)/(.018)
    crown_r=(.090+.003*alpha,.107+.004*alpha);band_inner=(.092-.003,.109-.003);band_outer=(.092,.109)
    radius=lambda xy:1/math.sqrt((math.sin(a)/xy[0])**2+(math.cos(a)/xy[1])**2)
    gap.append(min(radius(crown_r)-radius(band_inner),radius(band_outer)-radius(crown_r)))
report['hat_crown_band_min_overlap_mm']=min(gap)*1000
bpy.ops.wm.open_mainfile(filepath=str(B/'V13/Authoring/FacelessSecurity_V13.blend'))
rig=bpy.data.objects['root'];report['sleeve_weights']={}
for name in ['Security_OutfitBody','Security_Uniform_SewnNeck_V11','Security_Cuff_l','Security_Cuff_r']:
    o=bpy.data.objects[name];rows=[];bad=0;missing=0;nonfinite=0
    for v in o.data.vertices:
        row={o.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-7};rows.append(row)
        total=sum(row.values());bad+=abs(total-1)>1e-5;missing+=any(n not in rig.data.bones for n in row)
        nonfinite+=any(not math.isfinite(c) for c in v.co)
    entry={'unnormalized':bad,'missing_bone_refs':missing,'nonfinite_vertices':nonfinite}
    if name!='Security_OutfitBody':
        count=len(rows)//2;entry['paired_weight_mismatches']=sum(any(abs(rows[i].get(n,0)-rows[i+count].get(n,0))>1e-5 for n in rows[i].keys()|rows[i+count].keys()) for i in range(count))
    report['sleeve_weights'][name]=entry
(R/'geometry.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SECURITY_REVIEW_GEOMETRY '+json.dumps(report),flush=True)
