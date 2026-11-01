import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).resolve().parent
def extract(m,rig):
 transform=rig.matrix_world.inverted()@m.matrix_world
 skin_slots={i for i,x in enumerate(m.data.materials) if x and ('SkinV9' in x.name or 'Manny' in x.name)}
 if not skin_slots:skin_slots=set(range(len(m.data.materials)))
 faces=[p for p in m.data.polygons if p.material_index in skin_slots]
 weights={v.index:{m.vertex_groups[g.group].name:g.weight for g in v.groups} for v in m.data.vertices}
 uv=m.data.uv_layers[0];keys={};positions={};shapes={k.name:{} for k in m.data.shape_keys.key_blocks}
 for p in faces:
  side='l' if sum(x for vi in p.vertices for n,x in weights[vi].items() if n.endswith('_l'))>sum(x for vi in p.vertices for n,x in weights[vi].items() if n.endswith('_r')) else 'r'
  us=[tuple(round(x,5) for x in uv.data[i].uv) for i in p.loop_indices]
  key=(side,tuple(sorted(us)));keys[key]={us[i]:vi for i,vi in enumerate(p.vertices)}
 for vi in {v for p in faces for v in p.vertices}:
  positions[vi]=np.array(transform@m.data.vertices[vi].co)
  for k in m.data.shape_keys.key_blocks:shapes[k.name][vi]=np.array(transform@k.data[vi].co)
 return {'tri':keys,'pos':positions,'shapes':shapes,'weights':weights,'count':len(faces)}
samples={}
for label in ('m24','baseline'):
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/(label+'.fbx')),use_anim=False)
 rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');m=next(o for o in bpy.data.objects if o.type=='MESH');samples[label]=extract(m,rig)
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24ReloadRefine20261028/M24_ReloadRefine_Editable.blend'),use_scripts=False)
samples['author']=extract(bpy.data.objects['M24_V9_BareArms'],bpy.data.objects['M24_V9_Rig'])
out={}
for label in ('baseline','author'):
 a=samples['m24'];b=samples[label];matches=set(a['tri'])&set(b['tri']);mapping={}
 for key in matches:
  for uv,vi in a['tri'][key].items():mapping[vi]=b['tri'][key][uv]
 common=set(a['shapes'])&set(b['shapes'])
 out[label]={'skin_triangles':a['count'],'reference_skin_triangles':b['count'],'uv_triangles_matched':len(matches),'skin_vertices_matched':len(mapping),
  'position_max_mm':max(float(np.linalg.norm(a['pos'][v]-b['pos'][w])*1000) for v,w in mapping.items()),
  'weight_max_delta':max(abs(a['weights'][v].get(n,0)-b['weights'][w].get(n,0)) for v,w in mapping.items() for n in set(a['weights'][v])|set(b['weights'][w])),
  'missing_shapes':sorted(set(b['shapes'])-set(a['shapes'])),
  'morph_position_max_mm':max(float(np.linalg.norm(a['shapes'][n][v]-b['shapes'][n][w])*1000) for n in common for v,w in mapping.items())}
(O/'mesh_comparison.json').write_text(json.dumps(out,indent=2));print('M24_V9_COMPARISON',json.dumps(out),flush=True)
