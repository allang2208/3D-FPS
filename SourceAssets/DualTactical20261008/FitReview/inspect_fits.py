"""Requested 66-case offline fit inspection, using freshly exported UE assets."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;P=O.parents[2];inputs=json.loads((O/'current-assets.json').read_text())['families']
auth=json.loads((P/'SourceAssets/BlessedLaser20261006/Model/authoring.json').read_text())
pivots=json.loads((O.parent/'authoring.json').read_text())['opposite_pivots_cm']
S=Matrix.Diagonal((1,-1,1,1));cm=Matrix.Diagonal((100,100,100,1));metres=cm.inverted()
out=O/'Before';out.mkdir(exist_ok=True);cache=O/'Cache';cache.mkdir(exist_ok=True)
report={};mode=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'all'
def matrix(v):return Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:]))
def basis(f,z):
    f=f.normalized();z=(z-f*z.dot(f)).normalized();return Matrix((f,z.cross(f),z)).transposed().to_4x4()
def mount(family,bones,side):
    root=bones['WPN_root']
    if family=='ASH12':
        rear=bones['WPN_RearSight'];r=basis(bones['WPN_FrontSight'].translation-rear.translation,rear.to_quaternion()@Vector((0,0,1)))
        t=r@Matrix.Rotation(0 if side else math.pi,4,'X');t.translation=rear.translation+r.to_3x3()@Vector((29.5,3.19 if side else -3.19,-8.25));return t
    if family=='Super90':
        t=basis(Vector((0,-1,0)),Vector((0,0,1)))@Matrix.Rotation(math.pi if side else 0,4,'X');t.translation=Vector((-2.48 if side else 2.48,-16,-77.075));return t
    base=Matrix.Identity(4) if family=='HK416' else root@metres
    if not side:return base
    pivot=Vector(pivots[family]);rot=Matrix.Rotation(math.pi,4,'Y');rot.translation=pivot-rot.to_3x3()@pivot
    return base@rot
def newmesh(name,v,f,material):
    data=bpy.data.meshes.new(name);data.from_pydata(v,[],f);data.update();ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob);data.materials.append(material);return ob
def material(name,color):
    mat=bpy.data.materials.new(name);mat.diffuse_color=(*color,1);return mat
def render(path,center,scale):
    scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=720;scene.render.resolution_y=520;scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new('Inspection background');scene.world.color=(.035,.035,.035)
    sh=scene.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.show_specular_highlight=True;sh.background_type='WORLD'
    scene.view_settings.view_transform='Standard';camera=bpy.data.objects.new('Mount closeup',bpy.data.cameras.new('Mount closeup'));bpy.context.collection.objects.link(camera);scene.camera=camera
    camera.location=center+Vector((-.11,-.24,.082));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=scale
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
for family,row in inputs.items():
    if mode!='all' and family not in mode.split(','):continue
    bones={n:matrix(v) for n,v in row['host']['bones'].items()}
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=row['host']['fbx'])
    hv=[];hf=[]
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH':continue
        groups={g.index for g in ob.vertex_groups if g.name.startswith('WPN_')};ids={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if g.group in groups)>.5}
        faces=[p for p in ob.data.polygons if all(i in ids for i in p.vertices)];used=sorted({i for p in faces for i in p.vertices});remap={i:len(hv)+j for j,i in enumerate(used)}
        hv.extend([list(ob.matrix_world@ob.data.vertices[i].co) for i in used]);hf.extend([[remap[i] for i in p.vertices] for p in faces])
    (cache/(family+'-host.json')).write_text(json.dumps(dict(vertices=hv,faces=hf),separators=(',',':')))
    for kind,entry in row['devices'].items():
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=entry['fbx'])
        verts=[];faces=[];mats=[];face_mats=[]
        for ob in bpy.context.scene.objects:
            if ob.type!='MESH':continue
            first=len(verts);mi=len(mats);mats.extend([m.name for m in ob.data.materials]);verts.extend([ob.matrix_world@v.co for v in ob.data.vertices]);faces.extend([[first+i for i in p.vertices] for p in ob.data.polygons]);face_mats.extend([mi+p.material_index for p in ob.data.polygons])
        source=auth['ASH12' if family=='Super90' else family];f=Vector(source['forward_blender']);up=Vector(source['up_blender']);frame=Matrix((f,up.cross(f),up));origin=S.to_3x3()@Vector(entry['sockets']['Emitter'])/100
        canonical=frame.to_4x4()@Matrix.Translation(-origin);dv=[canonical@v for v in verts]
        (cache/(family+'-'+kind+'.json')).write_text(json.dumps(dict(vertices=[list(v) for v in dv],faces=faces,face_materials=face_mats,materials=mats,canonical=list(map(list,canonical))),separators=(',',':')))
        for side in (0,1):
            key=family+'-'+kind+'-'+str(side+1);bpy.ops.wm.read_factory_settings(use_empty=True)
            transform=canonical@S@metres@mount(family,bones,side).inverted()@cm@S
            host=[transform@Vector(v) for v in hv]
            (cache/(key+'-host.json')).write_text(json.dumps(dict(vertices=[list(v) for v in host],faces=hf,host_to_canonical=list(map(list,transform))),separators=(',',':')))
            tree=BVHTree.FromPolygons(host,hf);parttree=BVHTree.FromPolygons(dv,faces)
            bounds={}
            for i,name in enumerate(mats):
                ids={j for face,mat in zip(faces,face_mats) if mat==i for j in face}
                if ids:bounds[name]=[[min(dv[j][a] for j in ids)*1000 for a in range(3)],[max(dv[j][a] for j in ids)*1000 for a in range(3)]]
            contact=[]
            for x in (-.07,-.06,-.05,-.04,-.03,-.02):
                for y in (-.008,-.004,0,.004,.008):
                    h=tree.ray_cast(Vector((x,y,.015)),Vector((0,0,1)),.15)[0]
                    t=parttree.ray_cast(Vector((x,y,.18)),Vector((0,0,-1)),.165)[0]
                    if h is not None and t is not None:contact.append([x*1000,y*1000,(h.z-t.z)*1000,h.z*1000,t.z*1000])
            report[key]={'material_bounds_mm':bounds,'axis_gap_probes_mm':contact}
            gun=material('Actual host',(.23,.31,.38));body=material('Retained device body',(.12,.13,.14));clamp=material('Mount interfaces',(.65,.35,.10))
            newmesh('Current host geometry',host,hf,gun);part=newmesh('Current device geometry',dv,faces,body);part.data.materials.append(clamp)
            for poly,mi in zip(part.data.polygons,face_mats):
                name=mats[mi].lower();poly.material_index=1 if any(w in name for w in ('collar','mount','gripmetal','seat','graphite')) else 0
            center=Vector((-.045,0,.025));render(out/(key+'.png'),center,.16 if family!='M16' else .23)
            print('TACTICAL_FIT_CASE '+key,flush=True)
            (out/'measurements.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
