"""Per-side closed bearing repairs; retain approved device bodies and finishes."""
import bpy,bmesh,json,math,re,sys
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;P=O.parents[2];C=O/'Cache';X=O/'Repaired';X.mkdir(exist_ok=True)
assets=json.loads((O/'current-assets.json').read_text())['families'];auth=json.loads((P/'SourceAssets/BlessedLaser20261006/Model/authoring.json').read_text())
manifest=json.loads((X/'manifest.json').read_text()) if (X/'manifest.json').exists() else {}
selected=sys.argv[sys.argv.index('--')+1].split(',') if '--' in sys.argv else [f for f in assets if f!='HK416']
if 'HK416' in selected:raise RuntimeError('HK416 must use ../HK416NativeRailCorrection/author_native.py; never regenerate generic bearings for its native rail assemblies')
bpy.context.preferences.filepaths.save_version=0
def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[-1]
def tree(ob):return BVHTree.FromPolygons([v.co for v in ob.data.vertices],[list(p.vertices) for p in ob.data.polygons])
def clean(s):return re.sub(r'[._]\d{3}$','',s)
def create(name,verts,faces,mat):
    m=bpy.data.meshes.new(name);m.from_pydata(verts,[],faces);m.update();ob=bpy.data.objects.new(name,m);bpy.context.collection.objects.link(ob);m.materials.append(mat)
    bm=bmesh.new();bm.from_mesh(m);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(m);bm.free();return ob
def ray(t,x,y,z=-.06):return t.ray_cast(Vector((x,y,z)),Vector((0,0,1)),.4)[0]
def top(t,x,y):return t.ray_cast(Vector((x,y,.20)),Vector((0,0,-1)),.3)[0]
def uv(ob,layers):
    for name in layers:
        layer=ob.data.uv_layers.new(name=name)
        for face in ob.data.polygons:
            axis=max(range(3),key=lambda a:abs(face.normal[a]));axes=[a for a in range(3) if a!=axis]
            for li in face.loop_indices:
                v=ob.data.vertices[ob.data.loops[li].vertex_index].co;layer.data[li].uv=(v[axes[0]]/.025,v[axes[1]]/.025)
def material_path(entry,name):
    return next((m['path'] for m in entry['materials'] if clean(m['slot'])==clean(name) or clean(m['path'].split('/')[-1].split('.')[0])==clean(name)),None)
for family in selected:
    row=assets[family]
    for kind,entry in row['devices'].items():
        old=json.loads((C/(family+'-'+kind+'.json')).read_text());canonical=Matrix(old['canonical']);desired=canonical.copy()
        # HK416's native flashlight was beneath the weapon; both tactical slots
        # now use the actual lateral rails, like its laser, retaining the native lamp.
        if family=='HK416' and kind=='flashlight':
            e=Vector(auth[family]['emitter_blender_m']);f=Vector(auth[family]['forward_blender']).normalized();up=Vector(auth[family]['up_blender']);e+=f*.0376
            desired=Matrix((f,up.cross(f),up)).to_4x4()@Matrix.Translation(-e)
            native_up=Vector((0,0,1));native_right=native_up.cross(f)
            actual_emitter=Vector(entry['sockets']['Emitter']);actual_emitter.y*=-1;actual_emitter/=100
            canonical=Matrix((f,native_right,native_up)).to_4x4()@Matrix.Translation(-actual_emitter)
        for side in (1,2):
            key=f'{family}-{kind}-{side}';bpy.ops.wm.read_factory_settings(use_empty=True)
            if kind=='blessed_laser':
                src=P/'SourceAssets/BlessedLaser20261006/Model/BlessedLaser_GameMaster.blend'
                with bpy.data.libraries.load(str(src),link=False) as (a,b):b.objects=['SM_BlessedLaser_Master']
                body=b.objects[0];bpy.context.collection.objects.link(body);body.data.transform(Matrix.Scale(auth['ASH12' if family=='Super90' else family]['scale'],4));body.matrix_world=Matrix.Identity(4)
                bindings={m.name:material_path(entry,m.name) for m in body.data.materials}
            else:
                bpy.ops.import_scene.fbx(filepath=entry['fbx'],use_custom_normals=True)
                obs=[ob for ob in bpy.context.scene.objects if ob.type=='MESH']
                for ob in obs:
                    transform=canonical@ob.matrix_world;ob.parent=None;ob.data.transform(transform);ob.matrix_world=Matrix.Identity(4)
                select(obs)
                if len(obs)>1:bpy.ops.object.join()
                body=bpy.context.object;bindings={m.name:material_path(entry,m.name) for m in body.data.materials}
                if family!='HK416':
                    body_slot=next(m for m in entry['materials'] if m['slot'] in ('M_Tactical_'+kind,'M_ASH12_'+kind+'_Body',f'A762_{kind}_0',f'SVD_{kind}_0',f'PKM14_{kind}_0',f'LMG20122_{kind}_1'))
                    body_mat=body_slot['path'].split('/')[-1].split('.')[0]
                    bm=bmesh.new();bm.from_mesh(body.data)
                    bmesh.ops.delete(bm,geom=[f for f in bm.faces if clean(body.data.materials[f.material_index].name)!=clean(body_mat)],context='FACES')
                    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(body.data);bm.free()
                    # Earlier ASH exports included abandoned M4 collar islands
                    # under the body material. Remove only those separate high blocks.
                    if family in ('ASH12','Super90'):
                        bm=bmesh.new();bm.from_mesh(body.data);seen=set();remove=[]
                        for v in bm.verts:
                            if v in seen:continue
                            group=[];queue=[v];seen.add(v)
                            while queue:
                                a=queue.pop();group.append(a)
                                for edge in a.link_edges:
                                    q=edge.other_vert(a)
                                    if q not in seen:seen.add(q);queue.append(q)
                            if min(v.co.z for v in group)>.010 and max(v.co.z for v in group)>.027:remove.extend(group)
                        bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(body.data);bm.free()
            body.name='Retained approved body'
            for ob in list(bpy.context.scene.objects):
                if ob!=body:bpy.data.objects.remove(ob,do_unlink=True)
            h=json.loads((C/(key+'-host.json')).read_text());host_vertices=[Vector(v) for v in h['vertices']]
            if desired!=Matrix(old['canonical']):
                update=desired@Matrix(old['canonical']).inverted();host_vertices=[update@v for v in host_vertices]
            hosttree=BVHTree.FromPolygons(host_vertices,h['faces']);fitverts=list(host_vertices);fitfaces=[list(f) for f in h['faces']];retained=[]
            if family=='M16':
                # Keep the native near-side saddle. A closed half-collar per side
                # avoids crossing two complete, asymmetric wraparound assemblies.
                band_entry=row['devices']['laser'];bpy.ops.import_scene.fbx(filepath=band_entry['fbx'],use_custom_normals=True)
                bands=[ob for ob in bpy.context.scene.objects if ob.type=='MESH' and ob!=body]
                band_c=Matrix(json.loads((C/'M16-laser.json').read_text())['canonical'])
                old_origin=Vector(band_entry['sockets']['Emitter']);old_origin.y*=-1;old_origin/=100
                band_c=desired # same native frame, expressed around this device's aperture
                for ob in bands:
                    ob.data.transform(band_c@ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4)
                    wanted=band_entry['materials'][0]['path'].split('/')[-1].split('.')[0]
                    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if clean(ob.data.materials[f.material_index].name)!=clean(wanted)],context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(ob.data);bm.free()
                    laser_frame=Matrix(json.loads((C/'M16-laser.json').read_text())['canonical'])
                    cut_z=(desired@laser_frame.inverted()@Vector((0,0,.07553))).z-.002
                    bm=bmesh.new();bm.from_mesh(ob.data)
                    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=Vector((0,0,cut_z)),plane_no=Vector((0,0,1)),clear_outer=True,clear_inner=False)
                    boundary=[edge for edge in bm.edges if edge.is_boundary and all(abs(v.co.z-cut_z)<.00001 for v in edge.verts)]
                    if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
                    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
                    if not ob.data.polygons:bpy.data.objects.remove(ob,do_unlink=True);continue
                    retained.append(ob);offset=len(fitverts);fitverts.extend([v.co.copy() for v in ob.data.vertices]);fitfaces.extend([[offset+i for i in p.vertices] for p in ob.data.polygons])
                    for mat in ob.data.materials:bindings[mat.name]=material_path(band_entry,mat.name)
            if family=='HK416' and kind=='laser':
                # Preserve the native remote switch and cable, but seat the
                # switch outside this side's surface rather than inside it.
                bm=bmesh.new();bm.from_mesh(body.data);seen=set();switch=[];cable=[]
                for v in bm.verts:
                    if v in seen:continue
                    seen.add(v);queue=[v];group=[]
                    while queue:
                        a=queue.pop();group.append(a)
                        for edge in a.link_edges:
                            q=edge.other_vert(a)
                            if q not in seen:seen.add(q);queue.append(q)
                    if max(v.co.z for v in group)>.040:
                        (switch if min(v.co.z for v in group)>.040 else cable).extend(group)
                correction=0.
                for v in switch:
                    hit=ray(hosttree,v.co.x,v.co.y,-.15)
                    if hit is not None:correction=max(correction,v.co.z-hit.z+.0004)
                if correction:
                    anchor=min(v.co.z for v in switch)
                    for v in switch:v.co.z-=correction
                    for v in cable:v.co.z-=correction*max(0.,min(1.,v.co.z/anchor))
                bm.to_mesh(body.data);bm.free()
            target=BVHTree.FromPolygons(fitverts,fitfaces)
            s=auth['ASH12' if family=='Super90' else family]['scale']
            if kind=='blessed_laser':bounds=(-.055*s,-.035*s,-.0065*s,.0065*s)
            elif kind=='laser':bounds=(-.060,-.028,-.0065,.0065)
            else:bounds=(-.078,-.046,-.0065,.0065)
            if family=='HK416' and kind=='laser':bounds=(-.065,-.038,-.006,-.001)
            x0,x1,y0,y1=bounds;source_tree=tree(body)
            # Use solid rail crowns / fore-end walls. Prefer close, broad surfaces,
            # and span openings instead of growing spikes into their far walls.
            candidates=[]
            for dx in (-.008,-.004,0,.004,.008):
                for dy in (-.012,-.008,-.004,0,.004,.008,.012):
                    hits=[ray(target,x+dx,y+dy,.010) for x in (x0,(x0+x1)*.5,x1) for y in (y0,(y0+y1)*.5,y1)]
                    z=sorted(p.z for p in hits if p is not None)
                    if len(z)<9:continue
                    score=(z[-1]-z[0])*1.4+z[4]+abs(dx)*.25+abs(dy)*.4
                    candidates.append((score,dx,dy,z))
            if not candidates:raise RuntimeError('No solid attachment footprint '+key)
            _,dx,dy,heights=min(candidates)
            floor=heights[0];ceiling=floor+.003
            # A small clearance protects the existing device body from the host;
            # actual contact is supplied by the new closed bearing only.
            required=0.;samples=0
            for v in body.data.vertices:
                p=v.co
                if family=='HK416' and kind=='laser' and p.x<-.095:continue
                if family!='HK416' and p.z<0:continue
                hit=ray(hosttree,p.x,p.y)
                if hit is not None:required=max(required,p.z-hit.z+.00025);samples+=1
            for x in (x0,(x0+x1)*.5,x1):
                for y in (y0,(y0+y1)*.5,y1):
                    p=top(source_tree,x,y)
                    if p is not None:required=max(required,p.z-floor+.0015)
            if required>.035:raise RuntimeError('Unexpected large displacement '+key+' '+str(required))
            shift=Vector((0,0,-required));body.data.transform(Matrix.Translation(shift));source_tree=tree(body)
            nx=24;ny=12;lower=[];upper=[];bearing=[];bridged=0
            for ix in range(nx+1):
                for iy in range(ny+1):
                    x=x0+(x1-x0)*ix/nx;y=y0+(y1-y0)*iy/ny;p=top(source_tree,x,y)
                    if p is None:raise RuntimeError('Device key footprint misses body '+key)
                    h=ray(target,x+dx,y+dy,.010)
                    if h is None:z=floor;bridged+=1
                    else:
                        z=min(h.z,ceiling)
                        if h.z<=ceiling:bearing.append([x+dx,y+dy,h.z])
                        else:bridged+=1
                    lower.append((x,y,p.z-.00012));upper.append((x+dx,y+dy,z+.00008))
            n=len(lower);verts=lower+upper;faces=[]
            for ix in range(nx):
                for iy in range(ny):
                    a=ix*(ny+1)+iy;b=a+1;c=b+ny+1;d=a+ny+1;faces.extend([(a,b,c,d),(d+n,c+n,b+n,a+n)])
            rim=list(range(ny+1))+[ix*(ny+1)+ny for ix in range(1,nx+1)]+[nx*(ny+1)+iy for iy in range(ny-1,-1,-1)]+[ix*(ny+1) for ix in range(nx-1,0,-1)]
            faces.extend((a,a+n,b+n,b) for a,b in zip(rim,rim[1:]+rim[:1]))
            mat=bpy.data.materials.new('Tactical_Fitted_Bearing')
            mount_material=next((m['path'] for m in entry['materials'] if any(t in m['slot'].lower() for t in ('interface','collar','gripmetal','graphite','seat'))),entry['materials'][0]['path'])
            bindings[mat.name]=mount_material;pad=create('Closed host matched bearing',verts,faces,mat);uv(pad,[v.name for v in body.data.uv_layers] or ['UVMap'])
            select([*retained,pad,body]);bpy.ops.object.join();body.name=f'SM_{kind}_{side}'
            tri=body.modifiers.new('Explicit contact triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
            # Keep a canonical editable assembly, then export in the exact frame
            # used by the existing native mount (including its scale cancellation).
            bpy.ops.wm.save_as_mainfile(filepath=str(X/(key+'.blend')))
            body.data.transform(desired.inverted());sockets={}
            for label,raw in entry['sockets'].items():
                p=Vector(raw);p.y*=-1;p/=100;p=canonical@p+shift;p=desired.inverted()@p
                sockets[label]=[p.x*100,-p.y*100,p.z*100]
                ob=bpy.data.objects.new('SOCKET_'+label,None);bpy.context.collection.objects.link(ob);ob.parent=body;ob.location=p;ob.select_set(True)
            path=X/(key+'.fbx');bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
            paths={m.name:bindings.get(m.name) for m in body.data.materials}
            used={p.material_index for p in body.data.polygons}
            if any(not paths[body.data.materials[i].name] for i in used):raise RuntimeError('Material provenance missing '+key)
            manifest[key]={'family':family,'kind':kind,'side':side,'fbx':str(path),'materials':paths,'sockets':sockets,'source':entry['path'],'body_outward_mm':required*1000,'bearing_contact_samples':len(bearing),'bridged_opening_samples':bridged,'bearing_overlap_mm':.08,'body_overlap_mm':.12,'bearing_points':bearing,'footprint':bounds,'top_offset_mm':[dx*1000,dy*1000],'canonical':list(map(list,desired)),'native_bands_retained':bool(retained)}
            (X/'manifest.json').write_text(json.dumps(manifest,separators=(',',':')),encoding='utf-8')
            print('TACTICAL_REPAIRED',key,'body_shift_mm',round(required*1000,3),'bearing_samples',len(bearing),flush=True)
