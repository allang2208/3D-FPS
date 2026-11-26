"""Local geometry diagnosis of the requested crouch defect; no game launch."""
import sys,json
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME');sys.path.insert(0,str(P/'Tools/RangerCrouchFit'));import fit
R=fit.R;inputs=fit.read(R/'inputs.json');frame=inputs['clips'][globals().get('CLIP','Crouch.Idle')]['samples'][globals().get('SAMPLE',0)]['bones'];prefix=globals().get('OUTPUT_PREFIX','diagnostic_crouch')
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=20;scene.cycles.use_denoising=True;scene.render.resolution_x=1300;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Diagnostic world');scene.world.color=(.22,.22,.22);scene.view_settings.view_transform='AgX'
def material(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*color,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.75;return m
cloth=material('Diagnostic green cloth',(.08,.19,.035));leather=material('Diagnostic brown trousers',(.23,.105,.043));lining=material('Inner lining',(.025,.025,.018))
candidate_root=Path(globals().get('CANDIDATE_ROOT',R));use_pose_clearance=globals().get('USE_POSE_CLEARANCE',True)
candidate_pants=fit.read(candidate_root/'Authored/ue_leather_pants/LeatherPants.json') if (candidate_root/'Authored/ue_leather_pants/LeatherPants.json').exists() else fit.canonical(fit.read(P/'SourceAssets/TrouserFit20261018/Jason_LeatherPants.json'))
sources=[('Before',fit.read(inputs['sources']['Jason']['file']),fit.canonical(fit.read(P/'SourceAssets/TrouserFit20261018/Jason_LeatherPants.json')),-.50),('Candidate',fit.read(candidate_root/'Authored/ue_field_sweater/Jason.json'),candidate_pants,.50)]
for label,shirt,pants,dx in sources:
    for kind,d,mat in [('Shirt',shirt,cloth),('Trousers',pants,leather)]:
        tr=fit.transforms(d,frame);p=fit.skinned(np.array(d['positions']),d['weights'],tr)
        if label=='Candidate' and kind=='Shirt' and use_pose_clearance:
            import pose_clearance
            p=pose_clearance.offset(d,p,tr)
        p[:,0]-=frame['pelvis']['p'][0];p[:,1]-=frame['pelvis']['p'][1]
        p=np.c_[p[:,0]*.01+dx,-p[:,1]*.01,p[:,2]*.01];mesh=bpy.data.meshes.new(label+kind);mesh.from_pydata(p.tolist(),[],d['triangles']);mesh.update();ob=bpy.data.objects.new(mesh.name,mesh);scene.collection.objects.link(ob);mesh.materials.append(mat);mesh.materials.append(lining)
        for poly in mesh.polygons:poly.use_smooth=True;poly.material_index=int(kind=='Shirt' and d['triangle_materials'][poly.index]==2)
for loc,power,size in [((0,-2,2),350,2),((0,2,1.4),250,1.7),((-2,0,1),180,1.5)]:
    data=bpy.data.lights.new('Diagnostic softbox','AREA');data.energy=power;data.size=size;ob=bpy.data.objects.new(data.name,data);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,.65))-ob.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('Diagnostic camera');camdata.type='ORTHO';camdata.ortho_scale=1.65;cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam);scene.camera=cam;cam.location=(.7,-3,.95);cam.rotation_euler=(Vector((0,0,.65))-cam.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(candidate_root/(prefix+'_front.png'));bpy.ops.render.render(write_still=True)
cam.location=(-.3,3,.85);cam.rotation_euler=(Vector((0,0,.65))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(candidate_root/(prefix+'_back.png'));bpy.ops.render.render(write_still=True)
