"""Inspect the final compressed UE poses with the saved skinned surface."""
from pathlib import Path
import sys
source=Path(__file__).with_name('render_arms.py')
exec(compile(source.read_text(encoding='utf8').split('current=load(')[0],str(source),'exec'))
rig=load(root/'after_rig.pkl')
reverse='reverse' in sys.argv
if reverse:cam.location.x=-65;cam.rotation_euler=(Vector((0,-16,-14))-cam.location).to_track_quat('-Z','Y').to_euler()
for role,times in ([('reload',(2.17,))] if reverse else [('reload',(1.6,2.17,4.7,5.6)),('reload_empty',(1.6,3.8,5.8))]):
    current=load(root/('after_'+role+'.pkl'))
    for time in times:
        i=round(time*(len(current['frames'])-1)/current['duration'])
        row={n:mat(t) for n,t in zip(rig['names'],current['frames'][i])}
        g=mat(rig['bind'][rig['names'].index('WPN_root')])@np.linalg.inv(row['WPN_root'])
        worlds=np.asarray([g@row[n] for n in d['names']])
        transforms=worlds@np.linalg.inv(bind)
        points=np.zeros_like(vertices)
        for bone,ids,coords in skin_groups:points[ids]+=coords@transforms[bone,:3,:].T
        hidden='New' if time<(3.2 if role=='reload' else 2.3) else 'Old'
        hideverts=np.unique(faces[np.array(['__'+hidden in materials[m] for m in sections])])
        points[hideverts]=[0,0,-1000]
        mesh.vertices.foreach_set('co',points.astype(np.float32).ravel());mesh.update()
        scene.render.filepath=str(root/(f'saved_{role}_{time:.2f}'+('_reverse' if reverse else '')+'.png'));bpy.ops.render.render(write_still=True)
