import bpy,sys,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];scene=bpy.context.scene;cam=scene.camera
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['open','front','lock','handle','hinge','dungeon']
scene.cycles.samples=48;scene.render.resolution_x=1800;scene.render.resolution_y=1500
views={'hero':(1,(235,-300,205),(0,0,54),226),'open':(31,(245,-310,245),(0,0,72),250),'front':(1,(330,0,85),(0,0,53),175),'lock':(1,(260,-70,116),(47,0,54),71),'handle':(1,(95,-250,95),(0,-63,40),95),'hinge':(31,(-240,-180,160),(-45,0,85),180),'dungeon':(1,(235,-300,190),(0,0,54),226)}
for v in args:
    frame,loc,target,scale=views[v];scene.frame_set(frame);cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
    if v=='dungeon':
        bpy.data.lights['Key'].energy=650000;bpy.data.lights['Key'].color=(1,.57,.25)
        bpy.data.lights['Fill'].energy=500000;bpy.data.lights['Fill'].color=(.24,.45,1)
        bpy.data.lights['Rim'].energy=1600000;bpy.data.lights['Front'].energy=180000
        scene.world.node_tree.nodes['Background'].inputs[1].default_value=.1
    if v=='front':
        mat=bpy.data.materials.new('Clay_Check');mat.use_nodes=True;mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.42,.46,.5,1);mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.68;scene.view_layers[0].material_override=mat
    else:scene.view_layers[0].material_override=None
    scene.render.filepath=str(ROOT/'final_previews'/('01_Closed_Studio.png' if v=='hero' else '02_Open_Studio.png' if v=='open' else '03_Front_Clay.png' if v=='front' else '04_Lock_Detail.png' if v=='lock' else '05_Handle_Detail.png' if v=='handle' else '06_Hinge_Open.png' if v=='hinge' else '07_Dungeon_Light.png'))
    bpy.ops.render.render(write_still=True)
