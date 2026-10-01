"""Controlled before/after attachment material inspection, identical mesh/UV/light."""
import bpy,json,ast,sys
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;S=O.parent/'HK416Reworked20260930'
auth=json.loads((S/'authoring.json').read_text());ri=Matrix(auth['root_matrix']).inverted()
tree=ast.parse((O.parent/'G18IconsFinal20260930/author_icons.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='scene'],type_ignores=[]),'material comparison studio','exec'))
for state in ('before','after'):
    bpy.ops.wm.read_factory_settings(use_empty=True);objects=[]
    for part in ('vertical','flashlight'):
        file=O/'Before'/('SM_HK416_'+part+'_Editable.blend') if state=='before' else Path(auth['static'][part]['fbx']).with_name('SM_HK416_'+part+'_Editable.blend')
        with bpy.data.libraries.load(str(file),link=False) as (_,dst):dst.objects=['SM_HK416_'+part]
        ob=dst.objects[0];bpy.context.scene.collection.objects.link(ob);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.data.transform(ri);ob.hide_render=False;ob.hide_set(False);objects.append(ob)
    s,_=scene(objects,(1,0,0),False);s.render.resolution_x=1280;s.render.resolution_y=900;s.cycles.samples=32
    s.render.film_transparent=False;s.view_settings.exposure=0
    s.render.filepath=str(O/('materials_'+state+'.png'));bpy.ops.render.render(write_still=True)
