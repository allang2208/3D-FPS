"""Offline contact inspection requested by the user; no editor/game launch."""
import bpy,json,sys
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).resolve().parents[3];O=P/'SourceAssets/BlessedLaser20261006/Model';R=O/'MountRepair'
mode=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'Before'
base=P/'trash/weapon-accessories-20261006/SourceAssets/BlessedLaser20261006/Model/MountRepair/Before' if mode=='Before' else O
auth=json.loads((base/'authoring.json').read_text());dest=R/('Views'+mode);dest.mkdir(exist_ok=True)
for family,e in auth.items():
    bpy.ops.wm.open_mainfile(filepath=str(base/'Fitted'/('BlessedLaser_'+family+'.blend')))
    f=Vector(e['forward_blender']);up=Vector(e['up_blender']);frame=Matrix((f,up.cross(f),up));origin=Vector(e['emitter_blender_m']);s=e['scale']
    for ob in list(bpy.context.scene.objects):
        if ob.type!='MESH':bpy.data.objects.remove(ob,do_unlink=True);continue
        ob.data.transform(frame.to_4x4()@Matrix.Translation(-origin)@ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
        for m in ob.data.materials:
            if not m.name.startswith('Blessed'):m.diffuse_color=(.08,.095,.115,1)
    geo=json.loads((R/'Hosts'/(family+'-geometry.json')).read_text())
    data=bpy.data.meshes.new('Actual firearm');data.from_pydata([frame@(Vector(v)-origin) for v in geo['vertices']],[],geo['faces']);data.update()
    host=bpy.data.objects.new('Actual firearm',data);bpy.context.collection.objects.link(host)
    mat=bpy.data.materials.new('Host inspection clay');mat.diffuse_color=(.24,.29,.34,1);data.materials.append(mat)
    scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=640;scene.render.resolution_y=440;scene.render.resolution_percentage=100
    if not scene.world:scene.world=bpy.data.worlds.new('Contact inspection background')
    scene.world.color=(.025,.025,.025)
    shading=scene.display.shading;shading.light='STUDIO';shading.studiolight_rotate_z=.4;shading.color_type='MATERIAL';shading.show_shadows=True;shading.show_cavity=True;shading.cavity_type='BOTH';shading.show_specular_highlight=True;shading.background_type='WORLD'
    scene.view_settings.view_transform='Standard'
    camera=bpy.data.objects.new('Contact camera',bpy.data.cameras.new('Contact camera'));bpy.context.collection.objects.link(camera);scene.camera=camera
    center=Vector((-.042*s,0,.025*s));camera.location=center+Vector((.11,-.29,.085));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=.16*s
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(dest/(family+'.png'));bpy.ops.render.render(write_still=True)
    print('CONTACT_VIEW',mode,family,flush=True)
