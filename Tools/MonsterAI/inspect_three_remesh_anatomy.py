"""User-requested offline anatomy comparison; never saves production assets."""
import bpy,numpy as np,json,sys,time,gc
from pathlib import Path
from mathutils import Matrix
from mathutils.bvhtree import BVHTree

P=Path('D:/FPS3D/FPSGAME')
ROOT=P/'SourceAssets/AlienGeometry20261006/AnatomyInspection20261007'
ROOT.mkdir(parents=True,exist_ok=True)
SOURCES=json.loads((P/'SourceAssets/AlienGeometry20261006/BlenderV2/source_inputs.json').read_text(encoding='utf8'))
species=sys.argv[sys.argv.index('--')+1]
OUT=ROOT/species;OUT.mkdir(exist_ok=True)
REPORT=dict(species=species,production_assets_modified=False,source=SOURCES[species]['source'],cases={},comparisons={})
def log(s):print('ANATOMY '+species+' '+str(s),flush=True)
def write(): (OUT/'inspection.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def name_key(name):
    name=name.split('_LOD')[0]
    if species=='M10Mawcrawler':return name.split('_KeptV5')[0].replace('M10_RemeshV3','M10_OriginalSurface')
    if species=='HangingBellM09':return name.split('_RemeshV3')[0].split('_KeptV16')[0].split('_LOD')[0]
    return 'SK_LurkerM08'
def arrays(o):
    m=o.data;m.calc_loop_triangles();p=np.empty((len(m.vertices),3),np.float32);m.vertices.foreach_get('co',p.ravel())
    mat=np.asarray(o.matrix_world);p=p@mat[:3,:3].T+mat[:3,3]
    f=np.empty((len(m.loop_triangles),3),np.int32);m.loop_triangles.foreach_get('vertices',f.ravel())
    return p,f
def topology(p,f):
    p,inv=np.unique(np.round(p,6),axis=0,return_inverse=True);f=inv[f]
    edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1)
    edges,n=np.unique(edges,axis=0,return_counts=True);boundary=edges[n==1];adj={}
    for a,b in boundary:adj.setdefault(int(a),set()).add(int(b));adj.setdefault(int(b),set()).add(int(a))
    unseen=set(adj);components=[]
    while unseen:
        stack=[unseen.pop()];ids=[]
        while stack:
            i=stack.pop();ids.append(i)
            for j in adj[i]:
                if j in unseen:unseen.remove(j);stack.append(j)
        q=p[ids]
        components.append(dict(vertices=len(ids),center=q.mean(0).tolist(),extent=np.ptp(q,axis=0).tolist(),branched_vertices=sum(len(adj[i])!=2 for i in ids)))
    return dict(welded_vertices=len(p),boundary_edges=len(boundary),nonmanifold_edges=int((n>2).sum()),
        boundary_components=sorted(components,key=lambda c:-c['vertices']))
def snapshot(label):
    meshes={};entry=dict(meshes={},rigs={});scene=bpy.context.scene
    for o in list(scene.objects):
        if o.type=='ARMATURE':
            o.animation_data_clear();o.data.pose_position='REST'
            for b in o.pose.bones:b.matrix_basis=Matrix.Identity(4)
            entry['rigs'][o.name]=dict(bones=[b.name for b in o.data.bones],points={b.name:list(o.matrix_world@b.head_local) for b in o.data.bones if any(k in b.name.lower() for k in ('head','jaw','eye','crown'))})
        elif o.type=='MESH' and o.data.shape_keys:
            o.data.shape_keys.animation_data_clear()
            for k in o.data.shape_keys.key_blocks:k.value=0
    scene.frame_set(0);bpy.context.view_layer.update()
    for o in scene.objects:
        if o.type!='MESH' or o.name.startswith('SM_M10_'):continue
        p,f=arrays(o);key=name_key(o.name)
        info=dict(object=o.name,vertices=len(p),triangles=len(f),bounds=[p.min(0).tolist(),p.max(0).tolist()],materials=[m.name if m else None for m in o.data.materials],
            morphs=[k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else [],topology=topology(p,f))
        weights={g.index:g.name for g in o.vertex_groups}
        if species=='LurkerM08':
            oral=np.zeros(len(p),np.float32)
            for v in o.data.vertices:
                oral[v.index]=sum(g.weight for g in v.groups if weights[g.group] in ('head','jaw','Wolf_-Head'))
        elif species=='M10Mawcrawler' and 'OriginalSurface' in key:oral=(p[:,0]>1.45).astype(np.float32)
        else:oral=np.zeros(len(p),np.float32)
        file=OUT/(label+'__'+key+'.npz');np.savez_compressed(file,p=p,f=f,oral=oral)
        info['geometry_file']=str(file);entry['meshes'][key]=info;meshes[key]=(p,f,oral)
    entry['triangles']=sum(v['triangles'] for v in entry['meshes'].values())
    REPORT['cases'][label]=entry;write();return meshes

def compare(source,low,label):
    result={}
    for name,(p,f,oral) in source.items():
        if name not in low:result[name]=dict(missing=True);continue
        lp,lf,_=low[name];tree=BVHTree.FromPolygons(lp.tolist(),lf.tolist(),all_triangles=True)
        surface_ids=np.unique(f)
        ids=surface_ids[::max(1,len(surface_ids)//100000)];q=p[ids]
        distance=np.asarray([tree.find_nearest(v)[3] for v in q]);largest=np.argsort(distance)[-12:][::-1]
        entry=dict(sampled_vertices=len(q),source_to_reduced_cm={str(v):float(np.quantile(distance,v)*100) for v in (.5,.9,.95,.99,1.)},
            over_5mm=int((distance>.005).sum()),over_10mm=int((distance>.01).sum()),
            largest=[dict(position=q[i].tolist(),distance_cm=float(distance[i]*100)) for i in largest])
        entry['excluded_loose_vertices']=int(len(p)-len(surface_ids))
        if np.count_nonzero(oral[surface_ids]>.5):
            ids=surface_ids[oral[surface_ids]>.5];d=np.asarray([tree.find_nearest(v)[3] for v in p[ids]])
            entry['oral_vertices']=len(ids);entry['oral_distance_cm']={str(v):float(np.quantile(d,v)*100) for v in (.5,.9,.95,.99,1.)}
            entry['oral_over_5mm']=int((d>.005).sum())
            entry['oral_bounds']=[p[ids].min(0).tolist(),p[ids].max(0).tolist()]
        result[name]=entry
    REPORT['comparisons'][label]=result;write();log({label:{k:{'max_cm':v.get('source_to_reduced_cm',{}).get('1.0'),'oral_max_cm':v.get('oral_distance_cm',{}).get('1.0')} for k,v in result.items()}})

if '--compare-cached' in sys.argv:
    REPORT=json.loads((OUT/'inspection.json').read_text(encoding='utf8'))
    for label,entry in REPORT['cases'].items():
        entry['meshes']={name_key(k):v for k,v in entry['meshes'].items()}
    def cached(label):
        result={}
        for name,entry in REPORT['cases'][label]['meshes'].items():
            a=np.load(entry['geometry_file']);result[name]=(a['p'],a['f'],a['oral'])
        return result
    source=cached('source')
    for label in ('reduced','lod0','lod1','lod2','lod3'):compare(source,cached(label),label)
    write();log('CACHED COMPARISON DONE');sys.exit(0)

bpy.ops.wm.open_mainfile(filepath=str(P/SOURCES[species]['source']),load_ui=False)
source=snapshot('source');log('source recorded')
bpy.ops.wm.open_mainfile(filepath=str(P/'SourceAssets/AlienGeometry20261006/RemeshV3'/species/(species+'_RemeshV3.blend')),load_ui=False)
low=snapshot('reduced');log('reduced recorded');compare(source,low,'reduced');del low;gc.collect()
for level in range(4):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    file=P/'SourceAssets/AlienGeometry20261006/RemeshV3'/species/(species+'_LOD'+str(level)+'.fbx')
    bpy.ops.import_scene.fbx(filepath=str(file),use_anim=False)
    data=snapshot('lod'+str(level));compare(source,data,'lod'+str(level));del data;gc.collect()
REPORT['complete']=True;write();log('DONE')
