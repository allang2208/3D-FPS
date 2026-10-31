"""Independent before-publication geometry assembly using the exported FBX meshes."""
import bpy,json,sys,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
from placements import placements
D=R/'Audit/proposed';D.mkdir(parents=True,exist_ok=True)
BEFORE=R.parent/'RefinementV2/Audit/after'
original=json.loads((BEFORE/'components.json').read_text('utf8'))
manifest=json.loads((R/'assembly.json').read_text('utf8'));bykey={x['key']:x for x in manifest['meshes']}
changes={r['actor']:r for r in placements()};rows=[];meshes={}
bpy.ops.wm.read_factory_settings(use_empty=True)
for r in original['components']:
    if r['actor'] not in changes:
        rows.append(r);(D/(r['key']+'.json')).write_bytes((BEFORE/(r['key']+'.json')).read_bytes());meshes[r['key']]=original['meshes'][r['key']];continue
    p=changes[r['actor']];entry=bykey[p['key']];key=hashlib.sha1(entry['fbx'].encode()).hexdigest()[:16]
    if key not in meshes:
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        bpy.ops.import_scene.fbx(filepath=entry['fbx'],use_custom_normals=True)
        ob=next(o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith('UCX_'))
        # FBX import gives Blender metres. Engine uses centimetres and reversed Y.
        ps=[ob.matrix_world@v.co for v in ob.data.vertices]
        vertices=[[v.x*100,-v.y*100,v.z*100] for v in ps]
        ob.data.calc_loop_triangles();triangles=[list(reversed(t.vertices)) for t in ob.data.loop_triangles]
        mats=[t.material_index for t in ob.data.loop_triangles]
        blob=dict(path=entry['asset'],vertices=vertices,triangles=triangles,materials=mats)
        (D/(key+'.json')).write_text(json.dumps(blob,separators=(',',':')),encoding='utf8')
        meshes[key]=dict(path=entry['asset'],triangles=len(triangles),vertices=len(vertices),slots=[m.name for m in ob.data.materials])
    import math
    yaw=math.radians(p['rotation']['yaw']);s=p['scale'];axes=[[s[0]*math.cos(yaw),s[0]*math.sin(yaw),0],[-s[1]*math.sin(yaw),s[1]*math.cos(yaw),0],[0,0,s[2]]]
    raw=json.loads((D/(key+'.json')).read_text());vs=raw['vertices'];loc=p['position_cm']
    world=[[loc[i]+sum(v[j]*axes[j][i] for j in range(3)) for i in range(3)] for v in vs]
    bounds=[[fn(v[i] for v in world) for i in range(3)] for fn in (min,max)]
    updated=dict(r,key=key,mesh=entry['asset'],transform=dict(origin=loc,axes=axes),bounds_cm=bounds,slots=meshes[key]['slots'])
    rows.append(updated)
(D/'components.json').write_text(json.dumps(dict(map=original['map'],phase='proposed',components=rows,meshes=meshes,containers=original['containers']),indent=2),encoding='utf8')
print('PROPOSED_GEOMETRY_PREPARED',len(rows))
