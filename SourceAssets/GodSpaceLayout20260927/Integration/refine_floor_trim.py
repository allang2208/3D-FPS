"""Local Blender repair of the accepted floor strips, in UE FBX mirror-Y space.

Called both by the scoped repair and the future accepted-layout exporter.
No scene render or changes to the approved carpet material.
"""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix

ROOT=Path(__file__).parent
OUT=ROOT/'FloorTrim'
WIDTH=.075
BAR_WIDTH=.018
MAIN_BARS=[-40,-32,-24,-16.5,4.4,14.5,40.5]
CROSS_BARS=[-34,-24,-12,12,24,34]

def top_height(y):
    def smooth(a,b,t):
        t=max(0,min(1,(t-a)/(b-a)));return t*t*(3-2*t)
    return .2355+.0215*smooth(4.9,5.4,y)*(1-smooth(10.6,11.1,y))+.0015

def create_continuous_trim():
    # One connected solid: side rails, corner returns and transverse strips
    # share the same vertices. No butted floating boxes or overlapping caps.
    xs={-36.5,-36.5+WIDTH,-4.7,-4.7+WIDTH,4.7-WIDTH,4.7,36.5-WIDTH,36.5}
    ys={-44,-44+WIDTH,44-WIDTH,44,5.4,5.4+WIDTH,10.6-WIDTH,10.6}
    for x in CROSS_BARS:xs.update([x-BAR_WIDTH/2,x+BAR_WIDTH/2])
    for y in MAIN_BARS:ys.update([y-BAR_WIDTH/2,y+BAR_WIDTH/2])
    for start in [4.9,10.6]:ys.update(round(start+i*.1,5) for i in range(6))
    xs=sorted(xs);ys=sorted(ys)
    def active(x,y):
        main=abs(x)<4.7 and abs(y)<44
        cross=abs(x)<36.5 and 5.4<y<10.6
        if not (main or cross):return False
        inner=(abs(x)<4.7-WIDTH and abs(y)<44-WIDTH) or (abs(x)<36.5-WIDTH and 5.4+WIDTH<y<10.6-WIDTH)
        return not inner or (main and any(abs(y-v)<BAR_WIDTH/2+.000001 for v in MAIN_BARS)) or (cross and any(abs(x-v)<BAR_WIDTH/2+.000001 for v in CROSS_BARS))
    cells={(i,j) for i in range(len(xs)-1) for j in range(len(ys)-1) if active((xs[i]+xs[i+1])/2,(ys[j]+ys[j+1])/2)}
    vertices=[];faces=[];index={}
    def vid(i,j,upper):
        k=(i,j,upper)
        if k not in index:
            index[k]=len(vertices);vertices.append((xs[i],ys[j],top_height(ys[j]) if upper else .22))
        return index[k]
    for i,j in sorted(cells):
        corners=[(i,j),(i+1,j),(i+1,j+1),(i,j+1)]
        a=[vid(x,y,False) for x,y in corners];b=[vid(x,y,True) for x,y in corners]
        faces.extend([tuple(b),tuple(reversed(a))])
        for k,near in enumerate([(i,j-1),(i+1,j),(i,j+1),(i-1,j)]):
            if near not in cells:
                q=(k+1)%4;faces.append((a[k],a[q],b[q],b[k]))
    me=bpy.data.meshes.new('Continuous floor trim');me.from_pydata(vertices,[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.dissolve_limit(bm,angle_limit=.0001,use_dissolve_boundaries=False,verts=list(bm.verts),edges=list(bm.edges))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    nonmanifold=sum(not e.is_manifold for e in bm.edges)
    if nonmanifold:raise RuntimeError('New rail union has open edges: '+str(nonmanifold))
    bm.to_mesh(me);bm.free()
    obj=bpy.data.objects.new('Floor satin brass continuous frame',me);bpy.context.collection.objects.link(obj)
    mat=bpy.data.materials.get('Floor satin brass') or bpy.data.materials.new('Floor satin brass')
    mat.diffuse_color=(.52,.38,.20,1);me.materials.append(mat)
    bevel=obj.modifiers.new('1.5 mm softened exposed edges','BEVEL');bevel.width=.0015;bevel.segments=2;bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(35)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    bm=bmesh.new();bm.from_mesh(obj.data)
    after_open=sum(not e.is_manifold for e in bm.edges)
    if after_open:raise RuntimeError('Beveled trim has nonmanifold edges: '+str(after_open))
    pending=set(bm.verts);components=0
    while pending:
        stack=[pending.pop()];components+=1
        while stack:
            v=stack.pop()
            for edge in v.link_edges:
                other=edge.other_vert(v)
                if other in pending:pending.remove(other);stack.append(other)
    bm.free()
    if components!=1:raise RuntimeError('Floor strip connections are disconnected: '+str(components))
    # Explicit hard planar normals keep broad metal caps flat; chamfers provide
    # real edge highlights without a full-surface smoothing artefact.
    for p in obj.data.polygons:p.use_smooth=False
    uv=obj.data.uv_layers.new(name='SurfaceUV')
    for p in obj.data.polygons:
        axis=max(range(3),key=lambda k:abs(p.normal[k]));axes=[k for k in range(3) if k!=axis]
        for li in p.loop_indices:
            co=obj.data.vertices[obj.data.loops[li].vertex_index].co
            uv.data[li].uv=(co[axes[0]]*2,co[axes[1]]*2)
    obj.data.transform(Matrix.Diagonal((1,-1,1,1)))
    for p in obj.data.polygons:p.flip()
    return obj,{'rail_width_cm':7.5,'bar_width_cm':1.8,'protrusion_mm':1.5,'bevel_mm':1.5,
        'main_bar_y_m':MAIN_BARS,'cross_bar_x_m':CROSS_BARS,'corner_method':'Single welded rectilinear union with softened edges',
        'height_transition_cm':2.15,'transition_length_cm':50,'new_trim_open_edges_before_bevel':nonmanifold}

def refine_structure(obj):
    me=obj.data
    if any(m and m.name=='Floor satin brass' for m in me.materials):raise RuntimeError('Trim revision already present; preserve edited assembly')
    parent=list(range(len(me.vertices)))
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for edge in me.edges:
        a,b=map(find,edge.vertices);parent[b]=a
    groups={}
    for v in me.vertices:groups.setdefault(find(v.index),[]).append(v.index)
    remove=set();records=[]
    for ids in groups.values():
        lo=[min(me.vertices[i].co[k] for i in ids) for k in range(3)]
        hi=[max(me.vertices[i].co[k] for i in ids) for k in range(3)]
        sx,sy,sz=[hi[k]-lo[k] for k in range(3)]
        old_bar=abs(sx-9)<.002 and abs(sy-.035)<.002 and abs(sz-.012)<.002 and abs(lo[2]-.244)<.002
        side=abs(sx-.12)<.002 and abs(sy-88)<.002 and abs(lo[2]-.225)<.002
        crossing=abs(sx-73)<.002 and abs(sy-.10)<.002 and abs(lo[2]-.255)<.002
        if old_bar or side or crossing:
            remove.update(ids);records.append({'type':'crossbar' if old_bar else 'rail','min':lo,'max':hi})
    if sum(r['type']=='crossbar' for r in records)!=43 or sum(r['type']=='rail' for r in records)!=4:
        raise RuntimeError('Source trim differs from inspected 43 bars / 4 rails; no geometry changed')
    before=sum(len(p.vertices)-2 for p in me.polygons)
    def carpet_vertices(data):
        ids={vi for p in data.polygons if data.materials[p.material_index] and 'inlay' in data.materials[p.material_index].name.lower() for vi in p.vertices}
        return sorted(tuple(round(float(v),6) for v in data.vertices[i].co) for i in ids)
    accepted_carpet=carpet_vertices(me)
    bm=bmesh.new();bm.from_mesh(me);bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[bm.verts[i] for i in sorted(remove)],context='VERTS')
    bm.to_mesh(me);bm.free()
    trim,details=create_continuous_trim()
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);trim.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.object.join()
    if accepted_carpet!=carpet_vertices(obj.data):raise RuntimeError('Preserve approved carpet geometry')
    details.update(removed=records,triangles_before=before,triangles_after=sum(len(p.vertices)-2 for p in obj.data.polygons),
        carpet_geometry_changed=False,existing_materials_preserved=True,additional_material_slots=1,
        old_bar_to_side_rail_gap_cm=28,old_rail_to_carpet_gap_cm=8,visible_trim_rise_mm=1.5,
        new_trim_after_bevel={'nonmanifold_edges':0,'connected_components':1},carpet_vertex_positions_unchanged=True)
    return details

def author():
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'Structure_Before.blend'))
    obj=bpy.data.objects['SM_GodSpaceStructure']
    for other in list(bpy.context.scene.objects):
        if other!=obj:bpy.data.objects.remove(other,do_unlink=True)
    # Restore stable imported slot names. Material identity stays unchanged in UE.
    inputs=json.loads((OUT/'inputs.json').read_text(encoding='utf8'))
    for material,row in zip(obj.data.materials,inputs['slots']):material.name=row['imported']
    details=refine_structure(obj)
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Structure_TrimV2.blend'))
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    path=OUT/'SM_GodSpaceStructure_TrimV2.fbx'
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',add_leaf_bones=False)
    details.update(file=str(path),materials=[m.name for m in obj.data.materials],rendered=False)
    (OUT/'geometry-repair.json').write_text(json.dumps(details,indent=2),encoding='utf8')
    print('FLOOR_TRIM_AUTHORED '+json.dumps({k:v for k,v in details.items() if k!='removed'}))

if __name__=='__main__':author()
