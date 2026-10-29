"""Review actual evaluated UE body/weapon geometry from the explicit pose audit."""
import bpy,numpy as np
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent/'FinalUppercutGeometry'
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=600;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT';scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.background_type='WORLD'
scene.world=bpy.data.worlds.new('Review');scene.world.color=(.035,.045,.065);scene.render.image_settings.file_format='PNG'
bpy.ops.mesh.primitive_plane_add(size=8,location=(0,0,-.025));bpy.context.object.color=(.11,.13,.16,1)
bpy.ops.object.camera_add();camera=bpy.context.object;scene.camera=camera;camera.data.type='ORTHO'
files=[p for p in OUT.glob('*.obj') if 'arm-overlap' in p.name or any(s in p.name for s in ('024','052','120'))]
for path in files:
    vertices=[];groups={};name=None
    for line in path.read_text().splitlines():
        if line.startswith('o '):name=line[2:];groups[name]=[]
        elif line.startswith('v '):vertices.append(list(map(float,line.split()[1:4])))
        elif line.startswith('f '):groups[name].append([int(x.split('/')[0])-1 for x in line.split()[1:]])
    v=np.array(vertices)*[.01,-.01,.01];objects=[]
    for i,(name,faces) in enumerate(groups.items()):
        if not faces:continue
        indices=np.unique(faces);mapping={int(x):j for j,x in enumerate(indices)}
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(v[indices].tolist(),[],[[mapping[x] for x in reversed(f)] for f in faces]);mesh.update()
        ob=bpy.data.objects.new(name,mesh);scene.collection.objects.link(ob);objects.append(ob)
        ob.color=(.24,.52,.78,1) if 'WeaponMesh' in name else (.91,.50,.17,1) if 'StaticMesh' in name else (.58,.67,.75,1)
        for poly in mesh.polygons:poly.use_smooth=True
    for view,eye in [('front',(1.5,-6,2.1)),('side',(-6,-.3,2.1))]:
        camera.location=eye;camera.rotation_euler=(Vector((0,0,1.0))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=2.45
        scene.render.filepath=str(OUT/(path.stem+'-'+view+'.png'));bpy.ops.render.render(write_still=True)
    for ob in objects:bpy.data.objects.remove(ob,do_unlink=True)
