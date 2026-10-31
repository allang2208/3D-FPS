"""Scoped saved-mesh intersections and diagnostic views requested by the user."""
import bpy,json,sys,math,csv
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent
phase=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'before'
D=R/'Audit'/phase
data=json.loads((D/'components.json').read_text('utf8'))
bpy.ops.wm.read_factory_settings(use_empty=True)
objects=[];trees={};records=[];source={};mats={}

def color(role):
    r=role.lower()
    if any(s in r for s in ['warm','copper','ochre','brass']):return (.38,.18,.07,1)
    if any(s in r for s in ['linen','paper']):return (.60,.63,.60,1)
    if any(s in r for s in ['fabric','weave','rug','carpet']):return (.10,.18,.22,1)
    if any(s in r for s in ['steel','metal']):return (.32,.39,.43,1)
    if any(s in r for s in ['oak','walnut','wood']):return (.18,.12,.075,1)
    if any(s in r for s in ['cyan','cool','screen','control','ui']):return (.03,.45,.56,1)
    if 'wall' in r or 'ceiling' in r:return (.35,.38,.40,1)
    return (.12,.14,.16,1)

for idx,row in enumerate(data['components']):
    raw=source.setdefault(row['key'],json.loads((D/(row['key']+'.json')).read_text('utf8')))
    t=row['transform'];axes=t['axes'];o=t['origin']
    vs=[]
    for v in raw['vertices']:
        p=[(o[i]+sum(v[j]*axes[j][i] for j in range(3)))/100 for i in range(3)]
        vs.append((p[0],-p[1],p[2]))
    fs=[];ids=[]
    for i,f in enumerate(raw['triangles']):
        if min(f)<0:continue
        ps=[vs[j] for j in f]
        if max(p[0] for p in ps)<21.15 or min(p[0] for p in ps)>30.0 or max(p[1] for p in ps)<-.1 or min(p[1] for p in ps)>10.35:continue
        fs.append(tuple(reversed(f)));ids.append(raw['materials'][i])
    if not fs:continue
    mesh=bpy.data.meshes.new(row['actor']+'_'+row['component']);mesh.from_pydata(vs,[],fs);mesh.update()
    ob=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(ob);ob['source_index']=idx
    for role in row['slots']:
        if role not in mats:
            m=bpy.data.materials.new(role);m.diffuse_color=color(role);mats[role]=m
        mesh.materials.append(mats[role])
    for poly,mi in zip(mesh.polygons,ids):poly.material_index=max(0,min(mi,len(row['slots'])-1))
    ob.hide_render=row['hidden'] or 'Ceiling' in row['actor']
    objects.append((idx,ob,row))
    if not row['hidden']:trees[idx]=BVHTree.FromPolygons(vs,fs,all_triangles=True,epsilon=0.)
    records.append(dict(index=idx,actor=row['actor'],component=row['component'],mesh=row['mesh'],triangles=len(fs),hidden=row['hidden'],bounds_cm=row['bounds_cm']))

def intersect_bounds(a,b):
    lo=[max(a[0][i],b[0][i]) for i in range(3)];hi=[min(a[1][i],b[1][i]) for i in range(3)]
    return lo,hi,[hi[i]-lo[i] for i in range(3)]

def interior(actor):
    return actor.startswith(('BP_','AP_Bed2_','AP7_Bed2_','AP_Container_Bed2_')) or actor in {'AP13_Control_Bed2','AP_Planter3','AP_Foliage3'}

# These four connections were traced to the retained source construction:
# V4 author.py planter soil; V3 refinement_v3_parts.py chassis/glass;
# V7 author_details.py motherboard connections and glass fastening screws.
installed_interfaces={
    frozenset(('AP_Planter3','AP_Foliage3')):'Plant stems enter the planter soil surface; planted root interface.',
    frozenset(('AP_Bed2_Desk_PC','AP_Bed2_Desk_PCGlass')):'Glass panel seats inside the chassis upper retaining edge.',
    frozenset(('AP_Bed2_Desk_PC','AP7_Bed2_PCDetail')):'Motherboard connectors and circuit details meet their mounting board.',
    frozenset(('AP_Bed2_Desk_PCGlass','AP7_Bed2_PCDetail')):'Four glass mounting screws pass through the glazing at fastening points.',
}
pairs=[];installation_contacts=[]
for p,(i,a,ra) in enumerate(objects):
    if i not in trees:continue
    for j,b,rb in objects[p+1:]:
        if j not in trees:continue
        if ra['actor']==rb['actor']:continue
        if not (interior(ra['actor']) or interior(rb['actor'])):continue
        lo,hi,depth=intersect_bounds(ra['bounds_cm'],rb['bounds_cm'])
        if min(depth)<=.005:continue
        hit=trees[i].overlap(trees[j])
        if not hit:continue
        affected=set(v for f,_ in hit for v in a.data.polygons[f].vertices)
        ps=[a.data.vertices[v].co for v in affected]
        pair=dict(a=ra['actor']+'/'+ra['component'],b=rb['actor']+'/'+rb['component'],triangle_pairs=len(hit),
                  broadphase_overlap_cm=depth,intersection_bounds_m=[[min(p[q] for p in ps) for q in range(3)],[max(p[q] for p in ps) for q in range(3)]])
        pair['b_face_centers_m']=[list(b.data.polygons[f].center) for f in sorted({fb for _,fb in hit})[:24]]
        reason=installed_interfaces.get(frozenset((ra['actor'],rb['actor'])))
        if reason:
            pair['classification']=reason;installation_contacts.append(pair)
        else:pairs.append(pair)
        print('INSTALLATION_CONTACT' if reason else 'CONTACT',pair['a'],pair['b'],len(hit),flush=True)

(D/'intersections.json').write_text(json.dumps(dict(phase=phase,components=len(records),pairs=pairs,installation_contacts=installation_contacts,method='SourceModel LOD0 triangle-surface intersections; explicitly documented planted/fastened interfaces retained'),indent=2),encoding='utf8')
with (D/'component-matrix.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=['index','actor','component','mesh','triangles','hidden','bounds_cm']);writer.writeheader();writer.writerows(records)

scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO';scene.display.shading.studiolight_rotate_z=.3
scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
scene.display.shading.cavity_type='BOTH';scene.display.shading.show_specular_highlight=True
scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('DiagnosticWorld');scene.world.color=(.12,.12,.12)
scene.render.resolution_x=1400;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard'
camdata=bpy.data.cameras.new('Diagnostic');cam=bpy.data.objects.new('Diagnostic',camdata);bpy.context.collection.objects.link(cam);scene.camera=cam
camdata.type='ORTHO';camdata.clip_start=.01;camdata.clip_end=100
views=[('desk',(26.6,3.1,2.25),(24.9,1.20,.95),2.8),('desk_side',(23.2,2.2,1.25),(24.9,1.18,.83),2.5),
       ('bed',(23.3,5.3,3.2),(25.7,8.70,1.0),5.7),('bedside',(24.3,8.6,1.45),(23.52,9.63,.65),1.25),
       ('basket',(28.0,7.9,1.12),(28.7,8.8,.30),1.10),('bench',(26.6,2.2,1.18),(27.2,.78,.35),2.2),
       ('shelf',(23.4,4.9,2.35),(21.65,3.9,1.8),2.4),('top',(25.5,5.1,15.),(25.5,5.1,0.),15.2)]
for name,eye,target,size in views:
    cam.location=eye;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();camdata.ortho_scale=size
    # Exterior/global architectural meshes remain in the intersection inventory.
    # Hide only foreground enclosing faces for diagnostic cutaway views.
    for idx,ob,row in objects:
        ob.hide_render=row['hidden'] or any(s in row['actor'] for s in ('Ceiling','Wall_','Facade','WindowGlass','WindowFrames','WindowDrapes','CurtainTracks','Lighting_','AP12_Fixture'))
        if name=='top':ob.hide_render=row['hidden'] or not (interior(row['actor']) or row['actor'] in {'AP_Floor_Bed2','Door_Bed2'})
    scene.render.filepath=str(D/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(D/'SavedGeometry_Diagnostic.blend'))
print('BEDROOM_GEOMETRY_AUDIT_FINISHED',phase,len(records),len(pairs),flush=True)
