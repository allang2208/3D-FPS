from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];review=P/'Saved/Super90R7Review20261008'
code=(review/'check_surface.py').read_text();start=code.index('script=__file__');end=code.index('def cuts(')
render=O/'render_saved.py'
code=code[:start]+"exec(compile(Path(r'%s').read_text().split('items=[]')[0],r'%s','exec'))\n"%(render,render)+code[end:]
begin=code.index('for kind,f in ');end=code.index('\n    clip=',begin)
code=code[:begin]+"for kind,f in [('normal_7',f) for f in (74,78,82,86,90,96,100,104,108,112,114,116,118,122,126)]+[('normal_1',f) for f in (90,94,98,102)]:"+code[end:]
code=code.replace("if 'Bare' not in mat.name:gun.append(tri);continue","if 'Bare' not in mat.name:continue")
before='    def tree(tris):'
insert="""    for ob in groups['props']:
        ev=ob.evaluated_get(deps);me=ev.to_mesh();me.calc_loop_triangles();vs=[ev.matrix_world@v.co for v in me.vertices]
        for t in me.loop_triangles:gun.append([vs[i] for i in t.vertices])
        ev.to_mesh_clear()
"""
code=code.replace(before,insert+before).replace('surface_check.json','prop_contact.json')
exec(compile(code,__file__,'exec'),{'__file__':str(render),'Path':Path})
