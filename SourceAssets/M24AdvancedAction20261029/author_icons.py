"""Produce actual-part grayscale catalog icons, not gameplay preview renders."""
import bpy,bmesh,json,runpy,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).resolve().parent
G=runpy.run_path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
spec=json.loads((O/'authoring.json').read_text())
frame=(O.parent/'M24Modular20261027/author_icons.py').read_text(encoding='utf-8')
frame=frame[frame.index('    def mat(name'):];frame='\n'.join(x[4:] if x.startswith('    ') else x for x in frame.splitlines())
for key in ('m24_advanced_action','false'):
    bpy.ops.wm.open_mainfile(filepath=str(O/'M24_AdvancedAction_Editable.blend'),use_scripts=False)
    if key=='false':
        ob=bpy.data.objects['M24_base'];ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear()
        wanted={tuple(round(p[k],3) for k in range(3)) for p in json.loads((O/'factory_vertices.json').read_text())}
        bm=bmesh.new();bm.from_mesh(ob.data)
        bmesh.ops.delete(bm,geom=[v for v in bm.verts if (round(v.co.x*100,3),round(-v.co.y*100,3),round(v.co.z*100,3)) not in wanted],context='VERTS')
        bm.to_mesh(ob.data);bm.free();keep=[ob]
    else:keep=[bpy.data.objects[n] for k in spec['models'].values() for n in k['objects']]
    for ob in list(bpy.data.objects):
        if ob not in keep:bpy.data.objects.remove(ob,do_unlink=True)
    for ob in keep:
        ob.hide_set(False);ob.hide_render=False
        ob.data.transform(ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
    pts=[v.co for ob in keep for v in ob.data.vertices]
    lo=Vector([min(v[k] for v in pts) for k in range(3)]);hi=Vector([max(v[k] for v in pts) for k in range(3)])
    for ob in keep:
        ob.data.transform(Matrix.Scale(1.28/max(hi.y-lo.y,hi.z-lo.z),4)@Matrix.Translation(-(lo+hi)*.5));ob.location.x=-.17
    G['apply_grayscale'](keep);s=bpy.context.scene
    exec(compile(frame,'Shared M24 metal-framed icon production','exec'))
