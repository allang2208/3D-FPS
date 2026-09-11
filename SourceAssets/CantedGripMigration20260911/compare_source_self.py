import bpy,json,itertools
from pathlib import Path
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;result={}
for weapon,variant in [('m4','canted')]+[('akm',v) for v in ['canted','vertical','prism','angled']]:
 d=O/weapon/variant;geometry=json.loads((d/'geometry.json').read_text());build=json.loads((d/('animation_build.json' if weapon=='m4' else 'build.json')).read_text());newonly=[];checked=0;perclip={}
 for clip,info in build.items():
  frames=[(float(k.rsplit('_',1)[1]),v['self']) for k,v in geometry.items() if k.rsplit('_',1)[0]==clip and v['self']]
  if not frames:continue
  bpy.ops.wm.open_mainfile(filepath=info['source']);r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
  if weapon=='m4':a=bpy.data.actions[info['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
  ob=bpy.data.objects['SK_Manny_Arms_Export'];ob.data.calc_loop_triangles();groups={g.index:g.name for g in ob.vertex_groups};faces={}
  for digit in ['index','middle','ring','pinky','thumb']:
   ids={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if groups[g.group].startswith(digit+'_') and groups[g.group].endswith('_l'))>.85};faces[digit]=[tuple(t.vertices) for t in ob.data.loop_triangles if all(i in ids for i in t.vertices)]
  perclip[clip]=[]
  for f,new in frames:
   s.frame_set(int(f),subframe=f%1);e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();v=[e.matrix_world@x.co for x in m.vertices];trees={d:BVHTree.FromPolygons(v,fs,all_triangles=True) for d,fs in faces.items()};old={a+'-'+b:len(trees[a].overlap(trees[b])) for a,b in itertools.combinations(trees,2)};e.to_mesh_clear();checked+=1
   perclip[clip].append({'frame':f,'new':new,'source':{k:v for k,v in old.items() if v}})
   if not any(old.values()):newonly.append([clip,f,new])
 result[weapon+'/'+variant]={'sampled_contact_times':checked,'new_only_times':newonly,'details':perclip};(O/'preserved_source_contacts.json').write_text(json.dumps(result,indent=2));print('SOURCE_SELF_COMPARISON',weapon,variant,checked,'new_only',newonly,flush=True)
