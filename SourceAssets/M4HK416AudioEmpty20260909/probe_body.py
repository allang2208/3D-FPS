import bpy,json
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4ReloadFinger20260909/M4_Reload_FingerCurl.blend')
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['M4_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update()
o=bpy.data.objects['M4_M4 Body_Export'];mesh=o.data
links=[[] for v in mesh.vertices]
for e in mesh.edges:
    x,y=e.vertices;links[x].append(y);links[y].append(x)
seen=set();parts=[];root=r.data.bones['WPN_root'].matrix_local.inverted()
for i in range(len(links)):
    if i in seen:continue
    stack=[i];seen.add(i);ids=[]
    while stack:
        v=stack.pop();ids.append(v)
        for n in links[v]:
            if n not in seen:seen.add(n);stack.append(n)
    ps=[root@mesh.vertices[j].co for j in ids]
    parts.append({'id':len(parts),'vertices':ids,'count':len(ids),'bounds':[[min(p[k] for p in ps),max(p[k] for p in ps)] for k in range(3)]})
(OUT/'body_parts.json').write_text(json.dumps(parts))
for o in s.objects:
    if o.type=='MESH':o.hide_render=o.parent!=r
    if o.type=='LIGHT':o.hide_render=True
d=bpy.data.cameras.new('Side');c=bpy.data.objects.new('Side',d);s.collection.objects.link(c);s.camera=c
target=r.pose.bones['WPN_root'].matrix@Vector((0,-.035,.005));c.location=target+Vector((-.65,-.13,.09));c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=.48
for p in [(-.4,-.3,1),(.5,.5,1)]:
    d=bpy.data.lights.new('SideLight','AREA');d.energy=100;d.size=2;l=bpy.data.objects.new('SideLight',d);s.collection.objects.link(l);l.location=p;l.rotation_euler=(target-l.location).to_track_quat('-Z','Y').to_euler()
s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1100;s.render.resolution_y=800;s.render.resolution_percentage=100
bpy.data.objects['SK_Manny_Arms_Export'].hide_render=True
s.render.filepath=str(OUT/'m4_receiver_left.png');bpy.ops.render.render(write_still=True)
print('PARTS',[(p['id'],p['count'],p['bounds']) for p in parts if p['count']>20])
