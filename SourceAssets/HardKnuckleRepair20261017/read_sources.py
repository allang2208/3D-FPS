"""Read the actual glove and runtime wrist skins; no scene or gameplay run."""
import json, hashlib
from pathlib import Path
import unreal as u

O = Path(__file__).parent
R = O.parents[1]
OUT = O / 'Read'
OUT.mkdir(exist_ok=True)
config = json.loads((R / 'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
recipe = config['items']['ue_hardknuckle_gloves']
G, Q, B, L = u.GeometryScript_AssetUtils, u.GeometryScript_MeshQueries, u.GeometryScript_BoneWeights, u.GeometryScript_List

def xyz(v): return [v.x, v.y, v.z]

def read(path, key, full=False):
    mesh = u.load_asset(path)
    if not mesh: raise RuntimeError('Missing mesh ' + path)
    dm, status = G.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Cannot read ' + path)
    _, vs, _ = Q.get_all_vertex_positions(dm, False)
    _, fs, _ = Q.get_all_triangle_indices(dm, False)
    ps = [xyz(v) for v in L.convert_vector_list_to_array(vs)]
    ts = [xyz(v) for v in L.convert_triangle_list_to_array(fs)]
    _, boneinfo = B.get_all_bones_info(dm)
    names = {b.index: str(b.name) for b in boneinfo}
    bones = {str(b.name): {'index': b.index, 'parent': b.parent_index,
             'position': xyz(b.world_transform.translation),
             'axes': [xyz(b.world_transform.transform_location(v) - b.world_transform.translation)
                      for v in (u.Vector(1,0,0), u.Vector(0,1,0), u.Vector(0,0,1))]}
             for b in boneinfo}
    wrists = [bones['hand_' + side]['position'] for side in ('l','r') if 'hand_' + side in bones]
    near = [any(sum((x-y)**2 for x,y in zip(p,w)) < 225 for w in wrists) for p in ps]
    selected = list(range(len(ts))) if full else [i for i,f in enumerate(ts) if all(near[v] for v in f)]
    ids = sorted({v for i in selected for v in ts[i]})
    remap = {v:i for i,v in enumerate(ids)}
    d = dict(source=path, skeleton=mesh.skeleton.get_path_name(), bones=bones,
             positions=[ps[i] for i in ids], triangles=[], uv=[], normals=[], triangle_materials=[], weights=[],
             materials=[s.material_interface.get_path_name() for s in mesh.materials],
             material_slots=[str(s.material_slot_name) for s in mesh.materials])
    for fi in selected:
        fi = int(fi)
        d['triangles'].append([remap[int(v)] for v in ts[fi]])
        a,b,c,_ = Q.get_triangle_u_vs(dm,0,fi)
        _,a0,b0,c0,_ = Q.get_triangle_normals(dm,fi)
        d['uv'].append([[v.x,v.y] for v in (a,b,c)])
        d['normals'].append([xyz(v) for v in (a0,b0,c0)])
        material, _ = u.GeometryScript_Materials.get_triangle_material_id(dm,fi)
        d['triangle_materials'].append(material)
    for vi in ids:
        _, ws, valid = B.get_vertex_bone_weights(dm,vi)
        if not valid: raise RuntimeError('Missing skin weight')
        d['weights'].append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
    file = OUT / (key + '.json')
    file.write_text(json.dumps(d,separators=(',',':')))
    print('GLOVE_SOURCE_READ', key, len(ids), len(selected), flush=True)
    return str(file)

inventory=[]
cache={}
for source, p in config['profiles'].items():
    profile=p['rig_profile']
    if profile not in recipe['rig_meshes']: continue
    base=p.get('native_bare_skin',p['base'])
    key=profile+'_'+hashlib.sha256(base.encode()).hexdigest()[:8]
    if base not in cache: cache[base]=read(base,key)
    inventory.append(dict(profile=profile,source=source,skin=base,file=cache[base],covers=p.get('glove_covers',[]),glove=recipe['rig_meshes'][profile]))
read(recipe['rig_meshes']['M4'],'current_glove_M4',True)
(O/'inventory.json').write_text(json.dumps(inventory,indent=2))
print('GLOVE_SOURCES_COMPLETE',len(cache),flush=True)
