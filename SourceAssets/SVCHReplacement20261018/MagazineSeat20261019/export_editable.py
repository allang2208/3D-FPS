"""Editable V9 + weapon action source; no preview render or game launch."""
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2]
source=P/'SourceAssets/SVCHRefinement20261018/R9ReloadGrip/export_editable.py'
code=source.read_text().replace('profile_reload_grip.json','profile_magazine_seat.json').replace('SVCH_R9_','SVCH_MagazineSeat_')
code=code.replace("O.parent / 'R8Surface/SVCH_R8Surface.blend'","O.parent / 'RealSights20261019/SVCH_RealFoldingSights_Editable.blend'")
code=code.replace('world.append(world[parent] @ local[j] if parent >= 0 else local[j])', '''if parent < 0:
                world.append(local[j])
            else:
                pp,pq,ps=world[parent].decompose()
                lp,lq,ls=local[j].decompose()
                world.append(Matrix.LocRotScale(world[parent] @ lp,pq @ lq,Vector(tuple(a*b for a,b in zip(ps,ls)))))''')
code=code.replace('scene.frame_set(220)','scene.frame_set(325)')
code=code.replace("if role == 'reload':","if role == 'reload_empty':")

code=code.replace("scene = bpy.context.scene", """scene = bpy.context.scene
cal=json.loads((O/'seat_calibration.json').read_text())
magfix=Matrix(cal['correction_bind_component_cm'])
boltshift=Vector(json.loads((O.parent/'SightsR2/bolt_fit_recipe.json').read_text())['delta_component_cm'])
for ob in scene.objects:
    if ob.type!='MESH':continue
    for vertex in ob.data.vertices:
        groups=[ob.vertex_groups[g.group].name for g in vertex.groups if g.weight>.999]
        if 'WPN_SOCKET_Magazine' in groups:
            world=ob.matrix_world @ vertex.co
            vertex.co=ob.matrix_world.inverted() @ CI @ magfix @ C @ world
        elif 'WPN_bolt' in groups:
            vertex.co+=ob.matrix_world.inverted().to_3x3() @ (CI.to_3x3() @ boltshift)
""")
exec(compile(code,str(source),'exec'),globals())
