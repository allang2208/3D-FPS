"""Local geometry views for the requested grip/twisted-index investigation."""
import sys,json
from pathlib import Path
O=Path(__file__).parent
sys.path.insert(0,str(O.parent/'RSH12InspectGrip20261004'))
from grip_scene import *
O=Path(__file__).parent
rig,D,profile,meta=load()
profile=json.loads((O/'Single/profile.json').read_text())
steel=json.loads((O.parent/'MetalGauntlet20260927/SteelGauntletV1/Authored/DW715.json').read_text())
S=np.diag([1.,-1.,1.,1.]);positions=np.c_[np.array(steel['positions']),np.ones(len(steel['positions']))]
groups=[]
for n in {n for w in steel['weights'] for n in w}:
    ids=np.array([i for i,w in enumerate(steel['weights']) if n in w]);ww=np.array([steel['weights'][i][n] for i in ids])
    b=steel['bones'][n];m=np.eye(4);m[:3,:3]=np.array(b['axes']).T;m[:3,3]=b['position']
    groups.append((n,ids,ww,positions[ids]@(S@np.linalg.inv(m)).T))
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1000;scene.render.resolution_y=850;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.world=bpy.data.worlds.new('ContactReview');scene.world.color=(.09,.11,.14);scene.display.shading.background_type='WORLD'
for kind in ('idle','inspect'):
    sample=min(D['clips'][kind]['samples'],key=lambda s:abs(s['time']-(1.2 if kind=='inspect' else 0)))
    p=pose(rig,D,profile,kind,sample);set_pose(rig,p);canon=canonical_pose(p,meta)
    for ob in list(bpy.data.objects):
        if ob.name.startswith('Review_'):bpy.data.objects.remove(ob,do_unlink=True)
    deps=bpy.context.evaluated_depsgraph_get()
    for ob in list(bpy.data.objects):
        if ob.type!='MESH':continue
        ev=ob.evaluated_get(deps);em=bpy.data.meshes.new_from_object(ev)
        verts=[v.co[:] for v in em.vertices];faces=[tuple(poly.vertices) for poly in em.polygons if poly.material_index not in (1,2)]
        mesh=bpy.data.meshes.new('Review_Gun');mesh.from_pydata(verts,[],faces)
        shown=bpy.data.objects.new('Review_Gun',mesh);bpy.context.collection.objects.link(shown)
        shown.matrix_world=canon@rig.matrix_world.inverted()@ob.matrix_world;ob.hide_render=True
        mat=bpy.data.materials.new('Gun');mat.diffuse_color=(.12,.15,.18,1);mesh.materials.append(mat)
    out=np.zeros((len(positions),3))
    for n,ids,ww,bound in groups:out[ids]+=(bound@np.array(canon@p[n]).T)[:,:3]*ww[:,None]
    mesh=bpy.data.meshes.new('Review_Glove');mesh.from_pydata(out.tolist(),[],steel['triangles'])
    ob=bpy.data.objects.new('Review_Glove',mesh);bpy.context.collection.objects.link(ob)
    for color in ((.36,.37,.39,1),(.58,.62,.66,1)):
        mat=bpy.data.materials.new('Glove');mat.diffuse_color=color;mesh.materials.append(mat)
    for poly,index in zip(mesh.polygons,steel['triangle_materials']):poly.material_index=index;poly.use_smooth=True
    target=Vector((0,.15,-.028))
    for name,offset in [('right',(.26,.10,.07)),('left',(-.26,.10,.07))]:
        cd=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',cd);bpy.context.collection.objects.link(cam)
        cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
        cd.type='ORTHO';cd.ortho_scale=.20;cd.clip_start=.001;scene.camera=cam
        scene.render.filepath=str(O/f'{kind}_{name}.png');bpy.ops.render.render(write_still=True)
