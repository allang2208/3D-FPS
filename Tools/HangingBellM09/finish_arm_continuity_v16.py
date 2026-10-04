"""Keep the original closed torso, remove misplaced detached slivers and finish arms."""
import bpy,bmesh,json
import numpy as np
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003')
OUT=ROOT/'ArmContinuityV16'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Authoring/M09_ContinuousArms_V16.blend'))
report={'removed_detached_arm_slivers':{},'body_surface':'Original V13 closed surface, misassigned detached pieces removed'}
for side in ('L','R'):
    ob=bpy.data.objects['M09_SmallArm_'+side];bm=bmesh.new();bm.from_mesh(ob.data)
    unseen=set(bm.verts);components=[]
    while unseen:
        start=unseen.pop();stack=[start];component=[start]
        while stack:
            v=stack.pop()
            for edge in v.link_edges:
                other=edge.other_vert(v)
                if other in unseen:unseen.remove(other);stack.append(other);component.append(other)
        components.append(component)
    components.sort(key=len,reverse=True);slivers=[v for c in components[1:] for v in c]
    report['removed_detached_arm_slivers'][side]={'components':len(components)-1,'vertices':len(slivers)}
    if slivers:bmesh.ops.delete(bm,geom=slivers,context='VERTS')
    bm.to_mesh(ob.data);bm.free()
# Reuse the original closed body shell; do not adopt the intermediate front
# retessellation, whose partial boundary reconstruction introduced open edges.
# Capture this scene's canonical materials before appending creates .001 copies.
body_materials=[bpy.data.materials['M09_Body_SourcePBR'],
                bpy.data.materials['M09_Closure_SourcePBR']]
with bpy.data.libraries.load(str(ROOT/'CrownClawV15/Authoring/M09_Rigged_ClawV15.blend')) as (src,dst):
    dst.objects=['M09_Body_RootBand']
source=dst.objects[0];body=bpy.data.objects['M09_Body_RootBand'];body.data=source.data.copy()
for index,material in enumerate(body_materials):body.data.materials[index]=material
bpy.data.objects.remove(source,do_unlink=True)
diag=np.load(OUT/'Records/M09_Body_RootBand.npz');components=diag['components'];pos=diag['positions']
remove=[]
for key,count in zip(*np.unique(components,return_counts=True)):
    if count>2000:continue
    ids=np.flatnonzero(components==key);q=pos[ids]
    if q[:,2].min()>.65 and q[:,2].max()<1.3 and q[:,1].mean()<-.26:remove.extend(ids.tolist())
bm=bmesh.new();bm.from_mesh(body.data);bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm,geom=[bm.verts[i] for i in remove],context='VERTS')
bm.to_mesh(body.data);bm.free()
groups=[g.name for g in body.vertex_groups];small={i for i,n in enumerate(groups) if n.startswith('small_') or n.startswith('smallfinger_')}
spine=body.vertex_groups.get('spine_03')
rows=[];values=[]
for vertex in body.data.vertices:
    extra=sum(g.weight for g in vertex.groups if g.group in small)
    if extra>0:
        previous=sum(g.weight for g in vertex.groups if g.group==spine.index)
        rows.append(vertex.index);values.append(previous+extra)
for i in small:body.vertex_groups[i].remove(rows)
quant=np.rint(np.array(values)*1024).astype(np.int32);rows=np.array(rows)
for q in np.unique(quant):
    if q>0:spine.add(rows[quant==q].tolist(),float(q)/1024,'REPLACE')
report['removed_wrong_body_vertices']=len(remove);report['decoupled_body_vertices']=len(rows)
report['scope']='Small arm geometry, local arm/body skin; other organs, rig and physics unchanged'
(OUT/'Records/final_surface_cleanup.json').write_text(json.dumps(report,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Authoring/M09_ContinuousArms_V16.blend'),compress=True)
print('M09_CONTINUITY_FINISHED',flush=True)
