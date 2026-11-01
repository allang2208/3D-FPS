import bpy
from pathlib import Path
exec(compile((Path(__file__).parent/'diagnose.py').read_text().split("\nif __name__=='__main__':")[0],'diagnose','exec'))
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=1066;s.render.resolution_y=600;s.render.resolution_percentage=100
s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.background_type='WORLD';s.world=bpy.data.worlds.new('Background');s.world.color=(.12,.14,.17)
bpy.ops.object.camera_add();cam=bpy.context.object;cam.rotation_euler=(math.pi/2,0,0);cam.data.sensor_fit='VERTICAL';cam.data.sensor_height=24;cam.data.lens=24/(2*math.tan(math.radians(37.5)));cam.data.clip_start=.01;s.camera=cam
def draw(X,file):
 cp=np.c_[X,np.ones(len(X))]@C.T;p=cp[:,[1,0,2]]*.01
 me=bpy.data.meshes.new('ActualKaitlinSkin');me.from_pydata(p,[],F);me.update();ob=bpy.data.objects.new('ActualKaitlinSkin',me);s.collection.objects.link(ob);ob.color=(.52,.30,.18,1)
 for face in me.polygons:face.use_smooth=True
 s.render.filepath=str(file);bpy.ops.render.render(write_still=True);bpy.data.objects.remove(ob,do_unlink=True)
if __name__=='__main__':
 for role in ('idle','sprint_loop'):
  e=entry('skeleton_base',role);row,_=compose(e,e['duration']*.5);draw(skin(row),O/('before_'+role+'.png'))
