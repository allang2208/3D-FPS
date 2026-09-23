"""Read current skinned geometry in UE component centimetres for pose fitting."""
import bpy, json, numpy as np
from collections import defaultdict,Counter
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion

P=Path(__file__).resolve().parent
def matrix(t):return Matrix.LocRotScale(Vector(t['p']),Quaternion(t['q']),Vector(t['s']))

def load_geometry(variant,data):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(P/variant/'SourceArms.fbx'),use_anim=False)
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    names=[b.name for b in rig.data.bones if b.name in data['rest']]
    # FBX importer may change bone axes. Fit positions through the exported
    # reference skeleton; skinning later uses original UE matrices directly.
    a=np.array([[*(rig.matrix_world@rig.data.bones[n].matrix_local).translation,1] for n in names])
    b=np.array([data['rest'][n]['p'] for n in names])
    mapping=np.linalg.lstsq(a,b,rcond=None)[0]
    residual=float(np.max(np.linalg.norm(a@mapping-b,axis=1)))
    if residual>.02:raise RuntimeError('FBX/UE reference coordinate mismatch: '+str(residual))
    verts=[];weights=[];triangles=[]
    for obj in [o for o in bpy.context.scene.objects if o.type=='MESH']:
        start=len(verts);groups={g.index:g.name for g in obj.vertex_groups};obj.data.calc_loop_triangles()
        for v in obj.data.vertices:
            world=obj.matrix_world@v.co
            verts.append(list(np.array([*world,1])@mapping))
            weights.append({groups[g.group]:g.weight for g in v.groups if groups[g.group] in data['rest'] and g.weight>1e-6})
        triangles.extend([tuple(start+i for i in t.vertices) for t in obj.data.loop_triangles])
    # Weld coincident seam vertices for boundary detection only; source mesh,
    # UVs, normals, materials and skin weights are never modified here.
    weld={};ids=[];representative={}
    for i,p in enumerate(verts):
        key=tuple(round(float(x),4) for x in p)
        if key not in weld:weld[key]=len(weld)
        k=weld[key];ids.append(k);representative[k]=i
    edges=Counter()
    for tri in triangles:
        tri=[ids[i] for i in tri]
        for i in range(3):edges[tuple(sorted((tri[i],tri[(i+1)%3])))]+=1
    adjacency=defaultdict(set)
    for (a,b),count in edges.items():
        if count==1:adjacency[a].add(b);adjacency[b].add(a)
    remaining=set(adjacency);boundaries=[]
    while remaining:
        stack=[remaining.pop()];component=[]
        while stack:
            n=stack.pop();component.append(representative[n])
            for nxt in adjacency[n]:
                if nxt in remaining:remaining.remove(nxt);stack.append(nxt)
        if len(component)<4:continue
        group_weights=Counter()
        for i in component:group_weights.update(weights[i])
        boundaries.append({'vertices':component,'weights':group_weights.most_common(6)})
    return {'vertices':verts,'weights':weights,'triangles':triangles,'boundaries':boundaries,'reference_fit_cm':residual}

def deform(geometry,rest,world,indices):
    transforms={n:matrix(world[n])@matrix(rest[n]).inverted() for n in world}
    result=[]
    for i in indices:
        v=Vector(geometry['vertices'][i]);p=Vector();total=0.
        for n,w in geometry['weights'][i].items():p+=(transforms[n]@v)*w;total+=w
        result.append(p/total if total else v)
    return result

if __name__=='__main__':
    summary={}
    for variant in ('Standard','LongGrip'):
        data=json.loads((P/variant/'source.json').read_text());g=load_geometry(variant,data)
        (P/variant/'geometry.json').write_text(json.dumps(g,separators=(',',':')),encoding='utf-8')
        summary[variant]={'fit_cm':g['reference_fit_cm'],'boundaries':[]}
        for boundary in g['boundaries']:
            entry={'count':len(boundary['vertices']),'weights':boundary['weights'],'poses':{}}
            for clip,time in [('Idle',0),('Thrust',.58),('Overhead',1.30),('SprintOverhead',1.30)]:
                row=min(data['clips'][clip]['samples'],key=lambda r:abs(r['seconds']-time))
                points=deform(g,data['rest'],row['world'],boundary['vertices'])
                entry['poses'][clip]={'forward_cm':[min(-p.y for p in points),max(-p.y for p in points)],
                    'right_cm':[min(p.x for p in points),max(p.x for p in points)],
                    'up_cm':[min(p.z for p in points),max(p.z for p in points)]}
            summary[variant]['boundaries'].append(entry)
    (P/'opening_source.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print('ARM_OPENING_SOURCE_GEOMETRY',json.dumps(summary),flush=True)
