from pathlib import Path
common=Path(__file__).parents[1]/'Repair02/render_arms.py'
exec(compile(common.read_text().split('current=load(')[0],str(common),'exec'))
scene.render.resolution_x=800;scene.render.resolution_y=650
for role,times in [('reload',(1.6,2.17,4.7)),('reload_empty',(1.6,5.36,5.78))]:
    after=np.load(root/(role+'_world.npz'))
    for time in times:
        i=round(time*120)
        worlds=np.asarray([after[n][i] for n in d['names']]);transforms=worlds@np.linalg.inv(bind)
        points=np.zeros_like(vertices)
        for bone,ids,coords in skin_groups:points[ids]+=coords@transforms[bone,:3,:].T
        hidden='New' if time<(3.2 if role=='reload' else 2.3) else 'Old'
        hideverts=np.unique(faces[np.array(['__'+hidden in materials[m] for m in sections])]);points[hideverts]=[0,0,-1000]
        mesh.vertices.foreach_set('co',points.astype(np.float32).ravel());mesh.update()
        scene.render.filepath=str(root/(f'candidate_{role}_{time:.2f}.png'));bpy.ops.render.render(write_still=True)
