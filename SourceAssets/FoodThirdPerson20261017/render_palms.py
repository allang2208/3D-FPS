"""Palm-side views of the saved large-lamb skin, where thumb folds were not visible in front views."""
from pathlib import Path
import sys
O=Path(__file__).parent
sys.argv=['review','--','source']
exec((O/'review_geometry.py').read_text().split('report=[]')[0])
row=data['cases'][0]
for time in [.55,2.75,4.65,5.3]:
    s=min(row['samples'],key=lambda a:abs(a['time']-time));out=deform(s['world']);bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh('Jason actual skin',out.tolist(),skin['triangles'],(.52,.39,.30))
    frame=mat(s['world'][ix['hand_l']])@mat(s['prop_local']);geo=foods[row['food']]
    meat=mesh('Lamb',[list(frame@Vector(v)) for v in geo['vertices']],geo['faces'],(.3,.15,.06))
    scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1000;scene.render.resolution_y=750;scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new('world');scene.world.color=(.07,.07,.07);scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_cavity=True;scene.view_settings.view_transform='Standard'
    camera=bpy.data.objects.new('camera',bpy.data.cameras.new('camera'));scene.collection.objects.link(camera);scene.camera=camera;camera.data.type='ORTHO';camera.data.ortho_scale=42
    center=(Vector(s['world'][ix['hand_l']][:3])+Vector(s['world'][ix['hand_r']][:3]))*.5
    for label,offset in [('palms',(0,-85,55)),('above',(0,5,120))]:
        camera.location=center+Vector(offset);camera.rotation_euler=(-Vector(offset)).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(O/f'source_lamb_{time:.2f}_{label}.png');bpy.ops.render.render(write_still=True)
