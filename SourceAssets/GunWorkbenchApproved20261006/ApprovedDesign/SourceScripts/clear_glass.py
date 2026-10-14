import bpy,pathlib
R=pathlib.Path(__file__).resolve().parents[1]
m=bpy.data.materials['Smoked safety glazing'];b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(.90,.96,.97,1);b.inputs['Transmission Weight'].default_value=1;b.inputs['Roughness'].default_value=.022
for l in list(m.node_tree.links):
 if l.to_node==b and l.to_socket==b.inputs['Normal']:m.node_tree.links.remove(l)
o=bpy.data.objects.get('Press nameplate');o.location.x-=.028;o.location.y=.4*0+(-.079);o.data.size=.019
# The press was offset in X in this scene; preserve that offset above.
o=bpy.data.objects.get('Press designation');o.location.x-=.025;o.location.y=-.079
bpy.ops.wm.save_as_mainfile(filepath=str(R/'output/Machines_Design_Working.blend'));s=bpy.context.scene;s.render.filepath=str(R/'output/Machines_Design_Preview.png');bpy.ops.render.render(write_still=True)
