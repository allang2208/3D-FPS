"""One-time author source migration; no tests or editor execution."""
from pathlib import Path
p=Path(__file__).with_name('author_rooms.py')
s=p.read_text(encoding='utf-8')
a=s.index('def tube(');b=s.index('def prism(',a)
s=s[:a]+'tube=detail.tube\nsmooth_pipe=detail.smooth_pipe\n'+s[b:]
a=s.index('    if breach:\n');b=s.index('    else:\n',a)
s=s[:a]+'    if breach:\n        detail.breach_wall(start,direction,normal,length,height,breach,mat)\n'+s[b:]
a=s.index('    # Individual ceramic tiles');b=s.index('    # Trim is segmented',a)
s=s[:a]+"    if tiles:SURFACES.wall(globals(),start,direction,normal,length,openings,breach,wall_depth)\n"+s[b:]
a=s.index("        for face,material in zip(mesh.polygons,g['m']):");b=s.index("        bpy.ops.object.select_all",a)
s=s[:a]+'''        for face,material,authored_uv,smooth in zip(mesh.polygons,g['m'],g['uv'],g['smooth']):
            face.material_index=names.index(material);axis=max(range(3),key=lambda i:abs(face.normal[i]));dims=[i for i in range(3) if i!=axis]
            face.use_smooth=smooth
            scale=.8 if material=='ServicePaint' else 1.28 if 'WallRelief' in material else 2
            for corner,li in enumerate(face.loop_indices):
                co=mesh.vertices[mesh.loops[li].vertex_index].co
                uv.data[li].uv=authored_uv[corner] if authored_uv is not None else (co[dims[0]]/scale,co[dims[1]]/scale)
                patches=max(0,math.sin(co.x*3.7+co.y*2.1+math.sin(co.z*5)))*max(0,math.sin(co.z*12+co.y*.7))
                age.data[li].color=(min(.8,.12+.5*patches+(.16 if ROOM['id']=='ShoredBreach' and material=='ServicePaint' else 0)),0,0,1)
'''+s[b:]
s=s.replace("bevel.width=.008;bevel.segments=2", "bevel.width=.0015 if kind=='Frames' else .005;bevel.segments=2")
s=s.replace("        for y in (y0+.25,y1-.25):\n            for i in range(21):box('Frames',(x0+.06+i*(x1-x0-.12)/20,y,.025),(.035,.5,.05),'BareSteel')", "        for y in (y0+.25,y1-.25):detail.grate(x0,x1,y)")
a=s.index('        for y,z,s in [');b=s.index("    for anchor in room['anchors']:",a)
s=s[:a]+'        detail.rubble()\n'+s[b:]
s+="\n(OUT/'corridor-surface-reuse.json').write_text(json.dumps(dict(source=str(SURFACES.source),placements=SURFACES.placements,method='approved final geometry and original UV/material transfer',tests_run=False),indent=2),encoding='utf-8')\n"
p.write_text(s,encoding='utf-8')
print('Room author source updated')
