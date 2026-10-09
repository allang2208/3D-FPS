"""Restore the boot-compatible skin binding and the closed-boot visibility mask."""
from pathlib import Path
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/rebuild_arms_v05.py').read_text(encoding='utf-8')
prefix=src.split("for o in list(scene.objects):\n    if o.type=='MESH' and not o.name.startswith('Security_Boot'):unbind(o)")[0]
prefix=prefix.replace("ROOT=BASE/'V05'","ROOT=BASE/'V10'").replace("BASE/'V04/Authoring/FacelessSecurity_V04.blend'","BASE/'V09/Authoring/FacelessSecurity_V09.blend'")
exec(compile(prefix,'boot_skin_helpers','exec'))
rows=read_weights(display);source=[fit(ws)@v.co for ws,v in zip(rows,display.data.vertices)];changed=0
for i,(v,p) in enumerate(zip(display.data.vertices,source)):
    if p.z>=.25:continue
    side='l' if p.x>=0 else 'r';calf=.65*ease(.105,.235,p.z)
    ws=norm({'foot_'+side:1-calf,'calf_'+side:calf})
    v.co=fit(ws).inverted()@p;rows[i]=ws;changed+=1
put_weights(display,rows)
# This is a visibility copy, not the complete anatomy. Closed leather boots
# fully cover the toes and instep. Keep the ankle overlap at the boot opening.
bm=bmesh.new();bm.from_mesh(display.data);bm.verts.ensure_lookup_table();remove=[]
for f in bm.faces:
    c=sum((source[v.index] for v in f.verts),Vector())/len(f.verts)
    if c.z<.205:remove.append(f)
removed_faces=len(remove)
bmesh.ops.delete(bm,geom=remove,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bm.to_mesh(display.data);bm.free();display.data.update()
body.hide_set(True);body.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessSecurity_V10.blend'))
report={'revision':'V10 boot skin','source':'V09','visible_foot_vertices_rebound':changed,'covered_skin_faces_removed':removed_faces,
 'complete_body':'Preserved V09 anatomy, positions, weights and topology in full',
 'binding':'Display ankle uses the same foot/calf field as the boot; covered toes and instep excluded from the render mesh',
 'unchanged':'V09 uniform, hands, forearms, trousers, boots and materials','game_tested':False,'rendered':False}
(ROOT/'boot_skin_recipe.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('SECURITY_V10_BOOT_SKIN '+json.dumps(report),flush=True)
export=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/export_delivery.py').read_text(encoding='utf-8').replace('V01','V10')
exec(compile(export,'export_security_v10','exec'))
