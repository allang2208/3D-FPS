"""Focused source-skin audit and camera renders requested by the user."""
import bpy, bmesh, json, math, sys
from pathlib import Path
from collections import defaultdict, Counter
from mathutils import Vector

P=Path(__file__).parent
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
revision=args[0] if args else 'ForwardGroupFlowV40'
files={'ForwardGroupFlowV40':'AzureRunesword_ForwardGroupFlowV40.blend',
       'AnchoredArmFlowV41':'AzureRunesword_AnchoredArmFlowV41.blend',
       'ReferenceReplicaV36':'AzureRunesword_ReferenceReplicaV36.blend'}
source=P.parent/revision/files[revision]
out=P/('Review_'+revision);out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source))
s=bpy.context.scene;r=bpy.data.objects['SK_RuneSword_Rig']
arms=bpy.data.objects['SK_Manny_Arms_Export'];blade=bpy.data.objects['RuneSword_Blade']
action=bpy.data.actions['A_RuneSword_Inspect'];r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
for ob in s.objects:
    ob.hide_render=ob not in (r,arms,blade)
    if ob in (r,arms,blade):ob.hide_set(False);ob.hide_viewport=False
arms.color=(.48,.63,.74,1);blade.color=(.58,.38,.12,1)
s.render.engine='BLENDER_WORKBENCH'
s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT'
s.display.shading.show_shadows=True;s.display.shading.show_cavity=True
s.display.shading.cavity_type='BOTH';s.display.shading.show_backface_culling=True
s.display.shading.background_type='WORLD';s.world.color=(.04,.05,.065)
s.render.resolution_x=960;s.render.resolution_y=540;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG';s.render.film_transparent=False
camera_data=bpy.data.cameras.new('AuditCamera');camera=bpy.data.objects.new('AuditCamera',camera_data);s.collection.objects.link(camera)
camera.location=(0,0,0);camera.rotation_euler=(math.pi/2,0,0)
camera_data.sensor_fit='VERTICAL';camera_data.sensor_height=24
camera_data.lens=24/(2*math.tan(math.radians(75/2)));camera_data.clip_start=.005;s.camera=camera
canonical={};welded={};originals=defaultdict(list)
for v in arms.data.vertices:
    key=tuple(round(c*1000000) for c in v.co)
    index=canonical.setdefault(key,len(canonical));welded[v.index]=index;originals[index].append(v.index)
edge_counts=Counter(tuple(sorted((welded[a],welded[b]))) for poly in arms.data.polygons for a,b in poly.edge_keys if welded[a]!=welded[b])
adj=defaultdict(set)
for (a,b),count in edge_counts.items():
    if count==1:adj[a].add(b);adj[b].add(a)
groups=[];seen=set()
for seed in adj:
    if seed in seen:continue
    todo=[seed];part=[];seen.add(seed)
    while todo:
        at=todo.pop();part.append(at)
        for n in adj[at]:
            if n not in seen:seen.add(n);todo.append(n)
    if len(part)<3:continue
    part=sorted({original for index in part for original in originals[index]})
    weights=Counter()
    for index in part:
        for weight in arms.data.vertices[index].groups:
            weights[arms.vertex_groups[weight.group].name]+=weight.weight
    center=sum((arms.data.vertices[i].co for i in part),Vector())/len(part)
    groups.append({'vertices':part,'count':len(part),'rest_center':list(center),
                   'weights':weights.most_common(6)})
groups.sort(key=lambda g:g['count'],reverse=True)
report={'source':str(source),'revision':revision,'fps':s.render.fps,'range':list(action.frame_range),
        'rig_transform':[list(row) for row in r.matrix_world],
        'mesh_vertices':len(arms.data.vertices),'boundaries':groups,'samples':[]}
times=[0.,.15,.25,.30,.35,.45,.55,.65,1.0,1.65,2.35,2.45,2.60,2.80,2.90]
for t in times:
    f=t*s.render.fps;s.frame_set(int(f),subframe=f-int(f))
    dg=bpy.context.evaluated_depsgraph_get();ev=arms.evaluated_get(dg);mesh=ev.to_mesh()
    borders=[]
    for k,g in enumerate(groups):
        points=[ev.matrix_world@mesh.vertices[i].co for i in g['vertices']]
        center=sum(points,Vector())/len(points)
        visible=[v for v in points if v.y>.005 and abs(v.x)<v.y*math.tan(math.radians(37.5))*16/9 and abs(v.z)<v.y*math.tan(math.radians(37.5))]
        borders.append({'boundary':k,'center':list(center),'in_frustum_vertices':len(visible),
                        'min_y':min(v.y for v in points),'max_y':max(v.y for v in points)})
    ev.to_mesh_clear()
    report['samples'].append({'time':t,'boundaries':borders,
       'bones':{n:[list(row) for row in r.pose.bones[n].matrix] for n in ('upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r','WPN_root')}})
    if '--metrics-only' not in args:
        s.render.filepath=str(out/f'frame_{round(t*120):03d}.png');bpy.ops.render.render(write_still=True)
(out/'source_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SOURCE_AUDIT_COMPLETE',revision,flush=True)
