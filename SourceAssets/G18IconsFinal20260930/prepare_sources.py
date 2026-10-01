"""Read model topology/materials needed to author isolated production icons."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];S=O.parent/'G18Integration20260929'
bpy.ops.wm.open_mainfile(filepath=str(S/'Single/G18_single_Editable.blend'))
rig=bpy.data.objects['SK_G18_Manny'];inv=rig.data.bones['WPN_root'].matrix_local.inverted();ob=bpy.data.objects['G18_G18']
mesh=ob.data;parent=list(range(len(mesh.vertices)))
def root(i):
    while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
    return i
for edge in mesh.edges:
    a,b=map(root,edge.vertices);parent[a]=b
groups={}
for v in mesh.vertices:groups.setdefault(root(v.index),[]).append(v.index)
rows=[]
for ids in groups.values():
    if len(ids)<5:continue
    points=[inv@mesh.vertices[i].co for i in ids];weights={}
    for i in ids:
        for g in mesh.vertices[i].groups:weights[ob.vertex_groups[g.group].name]=weights.get(ob.vertex_groups[g.group].name,0)+g.weight
    rows.append({'ids_count':len(ids),'first':ids[0],'lo':[min(p[j] for p in points) for j in range(3)],'hi':[max(p[j] for p in points) for j in range(3)],'weights':weights})
(O/'source_parts.json').write_text(json.dumps({'root_inverse':[list(r) for r in inv],'islands':rows},indent=2))
print('TOPOLOGY_SOURCE',json.dumps(rows),flush=True)
for file in [O.parent/'G18TacticalFit20260930/Exports/SM_G18_laser_Editable.blend',O.parent/'G18AttachmentRepair20260930/Exports/SM_G18_holographic_Editable.blend',O.parent/'G18MuzzleFit20260930/Exports/SM_G18_tactical_suppressor_Editable.blend']:
    bpy.ops.wm.open_mainfile(filepath=str(file))
    print('MATERIAL_SOURCE',str(file),json.dumps([{ 'name':m.name,'nodes':[(n.type,n.image.filepath if n.type=='TEX_IMAGE' and n.image else '') for n in m.node_tree.nodes] if m.use_nodes else []} for m in bpy.data.materials]),flush=True)
