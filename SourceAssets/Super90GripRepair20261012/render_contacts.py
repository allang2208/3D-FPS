"""Targeted offline views of the saved production contact geometry."""
import bpy,json,sys,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;sys.path.insert(0,str(O))
from grip_math import load,matrix,pose,skinned
mode=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'before'
only_mount='--mount' in sys.argv
data=load('SK_Super90_V7');profiles=load('profiles_'+('before' if mode=='donor' else mode));poses=load('poses')
C=np.diag([.01,-.01,.01,1]);mount=Matrix(((0,-1,0,0),(1,0,0,.16),(0,0,1,-.8015),(0,0,0,1)))
R=O/'Views';R.mkdir(exist_ok=True)
def obj(name,vs,fs,color):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vs,[],fs);mesh.update()
    ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
    mat=bpy.data.materials.new(name);mat.diffuse_color=(*color,1);mesh.materials.append(mat)
    for f in mesh.polygons:f.use_smooth=True
    return ob
faces=np.array(data['faces']);left=np.array([sum(v for n,v in w.items() if n.endswith('_l'))>.5 for w in data['weights']])
gun=np.array([sum(v for n,v in w.items() if n.startswith('WPN_'))>.5 for w in data['weights']])
for key in ('vertical','tactical_vertical','canted','prism','angled'):
    family='vertical' if key=='tactical_vertical' else key;profile=profiles[family]
    layer=next(c for c in profile['clips'] if c['base'].split('/')[-1].startswith('A_Super90_idle.'))
    row=poses[layer['base']]['samples'][0];world,_=pose(data,row,layer)
    normalize=matrix(data['rest']['WPN_root'])@world['WPN_root'].inverted()
    world={n:normalize@m for n,m in world.items()};v=skinned(data,world)*np.array([.01,-.01,.01])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if not only_mount:
        if mode=='donor':
            donor=load('SK_M4_FoldingSights_HK416');dw,_=pose(donor,load('M4_donors')[family]);dn=matrix(donor['rest']['WPN_root'])@dw['WPN_root'].inverted();dw={n:dn@m for n,m in dw.items()}
            dv=skinned(donor,dw)*np.array([.01,-.01,.01])
            auth=json.loads((O.parent/'ASH12UniversalAttachments20260919/authoring_inputs.json').read_text())
            models=json.loads((O.parent/'Super90Foregrips20261007/models.json').read_text())
            m=np.array(mount@Matrix.Translation((0,0,models['parts'][key]['body_lift']))@Matrix(auth['donors'][family]['mount']).inverted())
            dv=dv@m[:3,:3].T+m[:3,3];dt=np.array(donor['faces']);mask=np.array([sum(w for n,w in weights.items() if n.endswith('_l'))>.5 for weights in donor['weights']])
            obj('Accepted donor',dv.tolist(),dt[np.all(mask[dt],axis=1)].tolist(),(.62,.40,.28))
        else:obj('Current V7 left arm',v.tolist(),faces[np.all(left[faces],axis=1)].tolist(),(.62,.40,.28))
    obj('Super90 native gun',v.tolist(),faces[np.all(gun[faces],axis=1)].tolist(),(.13,.15,.17))
    if mode=='after':
        with bpy.data.libraries.load(str(O/'Exports'/('SM_Super90_'+key+'_Editable.blend')),link=False) as (a,b):b.objects=['SM_Super90_'+key]
        grip=b.objects[0];bpy.context.collection.objects.link(grip);grip.matrix_world=mount
        grip.data.materials.clear();mat=bpy.data.materials.new('grip');mat.diffuse_color=(.25,.32,.38,1);grip.data.materials.append(mat)
        for f in grip.data.polygons:f.material_index=0
    else:
        g=load('SM_Super90_'+key);gv=np.array(g['vertices'])*np.array([.01,-.01,.01]);m=np.array(mount)
        gv=gv@m[:3,:3].T+m[:3,3];obj('grip',gv.tolist(),g['faces'],(.25,.32,.38))
    scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=750;scene.render.resolution_y=650;scene.render.resolution_percentage=100
    sh=scene.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.show_specular_highlight=True;sh.background_type='WORLD'
    scene.world=bpy.data.worlds.new('BG');scene.world.color=(.06,.06,.06);scene.view_settings.view_transform='Standard'
    center=Vector((0,.16,-.84));cam=bpy.data.objects.new('contact',bpy.data.cameras.new('contact'));bpy.context.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.225
    if only_mount:center.z=-.806;cam.data.ortho_scale=.155
    for label,offset in [('palm',(.25,-.16,-.10)),('back',(-.23,-.14,-.09))]:
        cam.location=center+Vector(offset);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(R/(mode+'_'+key+'_'+label+('_mount' if only_mount else '')+'.png'));bpy.ops.render.render(write_still=True)
    print('GRIP_VIEW '+mode+' '+key,flush=True)
