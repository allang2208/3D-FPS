"""Neutral close views of UE-skinned surfaces including joint correctives."""
import bpy,json,numpy as np,sys
from pathlib import Path
from mathutils import Vector,Quaternion
r=Path(__file__).resolve().parent;label=sys.argv[-1] if '--' in sys.argv else 'after';out=r/('native_'+label+'_views');out.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=900;scene.render.resolution_y=700;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.world=bpy.data.worlds.new('Review');scene.world.color=(.075,.075,.075)
def mat(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);return m
skin=mat('Skin',(.58,.34,.22));metal=mat('Gun',(.14,.19,.23))
def matrix(v):
    m=np.array(Quaternion((v[6],*v[3:6])).to_matrix().to_4x4());m[:3,:3]*=np.array(v[7:10]);m[:3,3]=v[:3];return m
def mesh(name,v,f,material):
    ids,indices=np.unique(f,return_inverse=True);m=bpy.data.meshes.new(name);m.from_pydata(v[ids].tolist(),[],indices.reshape(-1,3).tolist());m.materials.append(material)
    for p in m.polygons:p.use_smooth=name=='Skin'
    ob=bpy.data.objects.new(name,m);scene.collection.objects.link(ob)
for family in ('base','vertical','angled','canted','prism'):
    folder=r/('native_'+label)/('box_normal_'+family);data=json.loads((folder/'review.json').read_text());meta=json.loads((folder/'geometry.json').read_text());dominant=np.fromfile(folder/'dominant.bin',np.uint32)
    for stage,at in [('hold',data['duration']),('travel',1.13)]:
        row=data['frames'][-1] if stage=='hold' else min(data['frames'],key=lambda x:abs(x['source']-at))
        stem=folder/Path(row['file']).stem;v=np.fromfile(stem.with_suffix('.vertices'),np.float32).reshape(-1,3);f=np.fromfile(stem.with_suffix('.indices'),np.uint32).reshape(-1,3);slots=np.fromfile(stem.with_suffix('.materials'),np.uint32)
        xf=matrix(row['component']);mirror=np.array([1,-1,1])
        def points(v):return (v@xf[:3,:3].T+xf[:3,3])*mirror
        for ob in list(scene.objects):bpy.data.objects.remove(ob,do_unlink=True)
        visible=np.isin(slots,row['visible_materials']);sk=np.isin(slots,[i for i,n in enumerate(meta['slots']) if n.startswith('Skin_')]);left=np.array([n.endswith('_l') for n in meta['bones']])[dominant]
        mesh('Skin',points(v),f[visible&sk&left[f].any(1)],skin);mesh('Gun',points(v),f[visible&~sk],metal)
        for part in folder.glob(stem.name+'_*.vertices'):
            mesh(part.stem,points(np.fromfile(part,np.float32).reshape(-1,3)),np.fromfile(part.with_suffix('.indices'),np.uint32).reshape(-1,3),metal)
        palm=points(v[dominant==meta['bones'].index('hand_l')]).mean(0)
        target=palm+np.array([-5.,1.,-3.]);camera=bpy.data.cameras.new('Camera');co=bpy.data.objects.new('Camera',camera);scene.collection.objects.link(co)
        co.location=target+np.array([16.,60.,24.]);co.rotation_euler=(Vector(target)-co.location).to_track_quat('-Z','Y').to_euler();camera.type='ORTHO';camera.ortho_scale=37.;camera.clip_start=.1;scene.camera=co
        scene.render.filepath=str(out/(family+'_'+stage+'.png'));bpy.ops.render.render(write_still=True)
