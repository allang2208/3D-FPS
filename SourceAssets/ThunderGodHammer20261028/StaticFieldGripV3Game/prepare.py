"""Prepare a version-isolated structured game mesh from the retained V2 design."""
from pathlib import Path
import shutil

P = Path(__file__).resolve().parent
V2 = P.parent / 'StaticFieldGripV2'
(P / 'Textures').mkdir(exist_ok=True)
(P / 'Export').mkdir(exist_ok=True)
shutil.copy2(V2 / 'surface.py', P / 'surface.py')
for image in (V2 / 'Textures').glob('T_*.png'):
    shutil.copy2(image, P / 'Textures' / image.name)

s = (V2 / 'author.py').read_text(encoding='utf-8')
s = s.replace('V2 production model:', 'V3 structured game retopology:')
# Reuse exact native interface objects, including custom corner normals.
s = s.replace("exec(compile(prelude,str(P/'native_interface_prelude.py'),'exec'))", """
prelude = prelude.split("native_band('01_NativeUpperMatingLand'")[0]
exec(compile(prelude,str(P/'native_interface_prelude.py'),'exec'))
bpy.data.objects.remove(factory, do_unlink=True)
with bpy.data.libraries.load(str(P.parent/'StaticFieldGripV2/StaticField_Design.blend'), link=False) as (src,dst):
    dst.objects = ['01_NativeUpperMatingLand','02_NativeLowerMatingLand']
for ob in dst.objects:
    bpy.context.collection.objects.link(ob)
    for i, mat in enumerate(ob.data.materials):
        ob.data.materials[i] = dark if mat and 'Recess' in mat.name else native
    parts.append(ob)
# Fine stitches are baked into the leather; no runtime thread material section.
rows[:] = [r for r in rows if r['slot'] != 'M_StaticField_WaxedThread']
""")
s = s.replace('angles=np.linspace(0,TAU,513);zs=np.linspace(z0,z1,897)',
              'angles=np.linspace(0,TAU,129);zs=np.linspace(z0,z1,257)')
start = s.index('# Genuine two-ply saddle thread.')
end = s.index('# Dense, individually chamfered forged collar', start)
s = s[:start] + '# Two-ply thread retained in V2 baking source only.\n' + s[end:]
replacements = {
    '2401': '401', '1601': '321',
    'np.linspace(.348,.401,145)': 'np.linspace(.348,.401,33)',
    'steel,384)': 'steel,128)', 'silver,384)': 'silver,128)', 'dark,384)': 'dark,128)',
    'N=256;K=30': 'N=96;K=8',
    'TAU,641)': 'TAU,161)', 'TAU,1001)': 'TAU,241)',
    '.00540,30)': '.00540,4)', '.00650,8)': '.00650,3)',
    '.000095,12)': '.000095,8)', '.000145,12)': '.000145,8)',
    '.000018,6)': '.000018,4)', '.00011,10)': '.00011,6)',
    '.000115,12)': '.000115,8)', '.00012,12)': '.00012,8)',
    '.000016,6)': '.000016,4)', '.000055,10)': '.000055,6)',
}
for before, after in replacements.items():
    s = s.replace(before, after)
# Keep cap UVs and exact native normals; weld only generated seam duplicates.
marker = "source=bpy.data.collections.new('StaticField_EditableParts')"
s = s.replace(marker, """
for ob in parts:
    if ob.name.startswith(('01_', '02_')):
        continue
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-8)
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=1e-10)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(ob.data); bm.free(); ob.data.update()
""" + marker)
s = s.replace('STATIC_FIELD_V2_AUTHORED', 'STATIC_FIELD_V3_RETOPOLOGIZED')
(P / 'author.py').write_text(s, encoding='utf-8')

# A closed tube must reuse its first ring, not create coincident end caps.
helper = '''
def tube(name, points, mat, width, depth=None, N=8):
    depth = depth or width
    closed = (Vector(points[0])-Vector(points[-1])).length < 1e-8
    points = points[:-1] if closed else points
    vs=[]; fs=[]; uv=[]; length=0.
    count=len(points)
    for i, point in enumerate(points):
        p=Vector(point)
        prev=(i-1)%count if closed else max(0,i-1)
        nex=(i+1)%count if closed else min(count-1,i+1)
        t=(Vector(points[nex])-Vector(points[prev])).normalized()
        n=Vector((p.x-CX,p.y-CY,0)).normalized()
        n=(n-t*n.dot(t)).normalized(); b=t.cross(n).normalized()
        if i: length+=(p-Vector(points[i-1])).length
        for j in range(N):
            a=TAU*j/N
            vs.append(tuple(p+n*(depth*math.cos(a))+b*(width*math.sin(a))))
            uv.append((j/N*.001/.065,length/.065))
    for i in range(count if closed else count-1):
        ni=(i+1)%count
        for j in range(N):
            nj=(j+1)%N
            fs.append((i*N+j,i*N+nj,ni*N+nj,ni*N+j))
    if not closed:
        fs.extend([tuple(reversed(range(N))),tuple((count-1)*N+j for j in range(N))])
    return mesh(name,vs,fs,mat,uv)
'''
s = s.replace('R=surf.R;z0,z1=surf.Z0,surf.Z1', helper+'\nR=surf.R;z0,z1=surf.Z0,surf.Z1')
(P / 'author.py').write_text(s, encoding='utf-8')
print('V3 author and inherited PBR sources prepared')
