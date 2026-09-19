import bpy,sys
from pathlib import Path
P=Path(__file__).parent;family=sys.argv[sys.argv.index('--')+1]
bpy.ops.wm.open_mainfile(filepath=str(P/family/'PhantomRearGrip_ReceiverFit_Editable.blend'))
m=bpy.data.materials.new('Clay');m.use_nodes=True
next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(.08,.18,.24,1)
grip=bpy.data.objects['SM_PhantomRearGrip']
for ob in bpy.context.scene.objects:
    if ob.type=='MESH':ob.hide_render=not(ob==grip or ob.name.startswith('Receiver_'))
for slot in grip.material_slots:slot.material=m
bpy.context.scene.render.filepath=str(P/(family+'_mount.png'));bpy.ops.render.render(write_still=True)
