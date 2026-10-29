"""Inspect the occluded recovery hand from the outer side and rear."""
from pathlib import Path
OUT=Path(__file__).resolve().parent
setup=(OUT/'render_gif_preview.py').read_text().split("for label in ('jason','kaitlin'):")[0]
exec(compile(setup,str(OUT/'render_gif_preview.py'),'exec'))
knife.hide_render=True
for label in ('jason','kaitlin'):
    data=np.load(OUT/(label+'-gif-preview.npz'))
    k=46
    mesh=bpy.data.meshes.new(label)
    mesh.from_pydata((data['vertices'][k]*mirror*.01).tolist(),[],data['triangles'][:,::-1].tolist())
    mesh.update()
    obj=bpy.data.objects.new(label,mesh);scene.collection.objects.link(obj);obj.color=(.59,.68,.75,1)
    for poly in mesh.polygons:poly.use_smooth=True
    center=Vector(data['hands'][k,1]*mirror*.01)
    for name,offset in [('side',(3.,0.,.3)),('rear',(1.5,2.,1.))]:
        camera.location=center+Vector(offset)
        camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
        camera.data.ortho_scale=.75
        scene.render.filepath=str(OUT/f'{label}-recovery-left-{name}.png')
        bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(obj,do_unlink=True)
