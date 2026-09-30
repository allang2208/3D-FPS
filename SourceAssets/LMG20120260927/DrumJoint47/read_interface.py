import bpy,bmesh,json,gzip
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
O=Path(__file__).parent;D=O.parent/'Drum46';G=json.loads((D/'geometry_inputs.json').read_text());S=json.loads((D/'sources.json').read_text())
root=Matrix(G['root_blender']);mag=Matrix(G['mag_blender']);root_from_mag=root.inverted()@mag
def matrix(v):return Matrix.LocRotScale(Vector(v['p']),Quaternion((v['q'][3],*v['q'][:3])),Vector(v['s']))
with gzip.open(S['clips']['201_base_idle']['file'],'rt') as f:idle=json.load(f)[0]
relative=matrix(idle['WPN_root']['world']).inverted()@matrix(idle['WPN_SOCKET_Magazine']['world']);flip=Matrix.Diagonal((1,-1,1,1));idle_from_mag=flip@relative@flip
out={'idle_root_from_mag':list(map(list,idle_from_mag)),'bind_to_idle':list(map(list,idle_from_mag@root_from_mag.inverted()))}
for kind in ['author','saved']:
 if kind=='author':bpy.ops.wm.open_mainfile(filepath=str(D/'LMG201_Drum46.blend'),use_scripts=False)
 else:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'Inputs/CurrentDrum.fbx'),use_anim=False)
 ob=next(a for a in bpy.data.objects if a.type=='MESH');bm=bmesh.new();bm.from_mesh(ob.data)
 bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index>2],context='FACES');bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
 es=[e for e in bm.edges if e.is_boundary];out[kind+'_shell']={'faces':len(bm.faces),'boundary_count':len(es),'boundaries':[[list(idle_from_mag@(ob.matrix_world@v.co)) for v in e.verts] for e in es]};bm.free()
(O/'interface.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v if k not in ['author_shell','saved_shell'] else {x:y for x,y in v.items() if x!='boundaries'} for k,v in out.items()}))
