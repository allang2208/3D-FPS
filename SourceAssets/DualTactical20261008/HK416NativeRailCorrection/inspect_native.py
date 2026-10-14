import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;P=O.parents[2];X=O/'Review';X.mkdir(exist_ok=True)
a=json.loads((P/'SourceAssets/HK416Reworked20260930/authoring.json').read_text())
W=Matrix(a['root_matrix'])@Matrix(a['source_to_weapon_root']);G=Matrix.Diagonal((4,4,4,1))@W.inverted()
sources=json.loads((O/'sources.json').read_text());S=Matrix.Diagonal((1,-1,1,1))
def load(name,frame=Matrix.Identity(4),host=False):
    before=set(bpy.context.scene.objects);bpy.ops.import_scene.fbx(filepath=sources[name]['fbx']);obs=[o for o in bpy.context.scene.objects if o not in before and o.type=='MESH']
    for ob in obs:
        if host:
            groups={g.index for g in ob.vertex_groups if g.name.startswith('WPN_')};ids={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if g.group in groups)>.5}
            bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in ids],context='VERTS');bm.to_mesh(ob.data);bm.free()
        t=G@frame@ob.matrix_world;ob.parent=None;ob.modifiers.clear();ob.data.transform(t);ob.matrix_world=Matrix.Identity(4)
        mat=bpy.data.materials.new(name);mat.diffuse_color=(.22,.29,.34,1) if host else (.56,.48,.29,1)
        ob.data.materials.clear();ob.data.materials.append(mat)
        for p in ob.data.polygons:p.material_index=0
    for ob in list(bpy.context.scene.objects):
        if ob.type not in ('MESH','CAMERA'):bpy.data.objects.remove(ob,do_unlink=True)
    return obs
def render(name,side=1,angle=0):
    s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=1100;s.render.resolution_y=700;s.render.resolution_percentage=100
    s.world=bpy.data.worlds.new('Review');s.world.color=(.035,.035,.035);s.view_settings.view_transform='Standard'
    sh=s.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.background_type='WORLD'
    cam=bpy.data.objects.new('ReviewCamera',bpy.data.cameras.new('ReviewCamera'));bpy.context.collection.objects.link(cam);s.camera=cam
    center=Vector((0,.205,.077));cam.location=center+Vector((.65*side,-.02,.14 if angle==0 else -.14));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.35
    s.render.filepath=str(X/(name+'.png'));bpy.ops.render.render(write_still=True)
if __name__=='__main__':
    for kind in ('laser','flashlight','blessed_laser'):
        bpy.ops.wm.read_factory_settings(use_empty=True);load('host',host=True);load(kind);render('native-'+kind)
    bpy.ops.wm.read_factory_settings(use_empty=True);load('host',host=True);load('laser-1');render('rejected-laser-1')
    pivot=Vector((.05025823,0,-.00547877));roll=Matrix.Rotation(math.pi,4,'Y');roll.translation=pivot-roll.to_3x3()@pivot;runtime=S@roll@S
    print('OLD_PIVOT_GUN_METRES',list(G@pivot),'EXPECTED_RAIL_CENTER_Z',(.016998438+.022568376)*2)
    (O/'frames.json').write_text(json.dumps({'asset_to_gun':list(map(list,G)),'runtime_opposite_blender':list(map(list,runtime))},indent=2))
