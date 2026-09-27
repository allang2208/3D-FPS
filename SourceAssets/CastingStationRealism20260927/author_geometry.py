"""Preserve the accepted anvil; replace the leaking staves and coarse water cap."""
import bpy, bmesh, json, math, sys
from pathlib import Path
from mathutils import Vector

HERE=Path(__file__).parent
OLD=HERE.parent/'CastingStation20260926/AnvilReferenceV3'
OUT=HERE/'Authored';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(OLD/'Authored/CastingStation_AnvilReference_Source.blend'))
bpy.context.preferences.filepaths.save_version=0
for ob in list(bpy.context.scene.objects):
    if ob.name.startswith(('Cooling barrel stave','Barrel bottom','Cooling water')):
        bpy.data.objects.remove(ob,do_unlink=True)

def co(p):return Vector((p[0]*.01,-p[1]*.01,p[2]*.01))
def make(name,verts,faces,slot):
    data=bpy.data.meshes.new(name);data.from_pydata([co(v) for v in verts],[],[tuple(reversed(f)) for f in faces]);data.update()
    ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob)
    mat=bpy.data.materials.get(slot) or bpy.data.materials.new(slot);data.materials.append(mat)
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    return ob

cx,cy=42.,-30.
profile=[(5,20),(12,21.7),(25,24),(39,23.5),(54,22)]
n=96;levels=len(profile);verts=[]
for inside in (False,True):
    for z,r in profile:
        for i in range(n):
            a=i*math.tau/n
            # Shallow engraved stave joint; all adjacent faces share vertices.
            groove=.045 if i%4==0 else 0
            radius=r-2.2 if inside else r-groove
            verts.append((cx+radius*math.cos(a),cy+radius*math.sin(a),z))
faces=[]
for side in range(2):
    off=side*levels*n
    for k in range(levels-1):
        for i in range(n):
            j=(i+1)%n;faces.append((off+k*n+i,off+k*n+j,off+(k+1)*n+j,off+(k+1)*n+i))
for i in range(n):
    j=(i+1)%n
    faces.extend([(i,j,levels*n+j,levels*n+i),
                  ((levels-1)*n+i,(levels-1)*n+j,(2*levels-1)*n+j,(2*levels-1)*n+i)])
wall=make('Cooling barrel sealed staves',verts,faces,'BarrelWood')
uv=wall.data.uv_layers.new(name='UprightOak50cm')
colors=wall.data.color_attributes.new(name='BarrelWetness',type='FLOAT_COLOR',domain='CORNER')
wall.data.color_attributes.active_color=colors
for face in wall.data.polygons:
    face.use_smooth=abs(face.normal.z)<.85
    for li in face.loop_indices:
        vi=wall.data.loops[li].vertex_index;x,y,z=verts[vi];i=vi%n
        a=i*math.tau/n
        if i==0 and any(wall.data.loops[l].vertex_index%n==n-1 for l in face.loop_indices):a=math.tau
        uv.data[li].uv=(a*22/50,(z-5)/70)
        wet=(.9 if vi>=levels*n else .25)*max(0,min(1,(48-z)/9))
        colors.data[li].color=(1,wet,0,1)
wall.data.set_sharp_from_angle(angle=math.radians(55))

# Bottom overlaps the inner wall below the water line; the vessel has a real interior floor.
bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=.182,depth=.022,location=co((cx,cy,6.1)))
bottom=bpy.context.object;bottom.name='Cooling barrel sealed bottom'
bottom.data.materials.append(bpy.data.materials['BarrelWood'])
uv=bottom.data.uv_layers.active or bottom.data.uv_layers.new(name='BottomOak')
for face in bottom.data.polygons:
    for li in face.loop_indices:
        v=bottom.data.vertices[bottom.data.loops[li].vertex_index].co;uv.data[li].uv=(v.x/.5,v.y/.5)

# A subdivided circular surface allows centimetre-scale displacement without a moving rim.
wv=[(cx,cy,46)];wf=[];radial=12
for ring in range(1,radial+1):
    r=21*ring/radial
    for i in range(n):a=i*math.tau/n;wv.append((cx+r*math.cos(a),cy+r*math.sin(a),46))
for i in range(n):wf.append((0,1+i,1+(i+1)%n))
for ring in range(radial-1):
    for i in range(n):
        j=(i+1)%n;a=1+ring*n;b=a+n;wf.append((a+i,b+i,b+j,a+j))
water=make('Cooling water rippled surface',wv,wf,'Water')
uv=water.data.uv_layers.new(name='BasinCoordinates')
for face in water.data.polygons:
    for li in face.loop_indices:
        x,y,z=wv[water.data.loops[li].vertex_index];uv.data[li].uv=((x-cx)/42+.5,(y-cy)/42+.5)

sys.path.insert(0,str(HERE))
from author_tool_rack import build as build_tool_rack
tool_rack=build_tool_rack()
manifest=json.loads((OLD/'Authored/manifest.json').read_text(encoding='utf8'))
manifest['revision']='CastingRealismV5_RackV7_Wind';manifest['assets']={}
manifest['sockets_ue_cm'].update(tool_rack['sockets'])
manifest['tool_rack']={key:value for key,value in tool_rack.items() if key!='groups'}
def export(name,objects,pivot,slot_order=None):
    copies=[]
    for src in objects:
        ob=src.copy();ob.data=src.data.copy();bpy.context.collection.objects.link(ob);copies.append(ob)
        # Joining differently named UV layers otherwise leaves UV0 blank on the barrel/water.
        # Every station surface uses UV0; carry each part's authored map into that same channel.
        source_uv=ob.data.uv_layers.active
        if source_uv:
            coordinates=[entry.uv.copy() for entry in source_uv.data]
            for layer in list(ob.data.uv_layers):ob.data.uv_layers.remove(layer)
            uv=ob.data.uv_layers.new(name='UVMap')
            for entry,coordinate in zip(uv.data,coordinates):entry.uv=coordinate
    bpy.ops.object.select_all(action='DESELECT')
    for ob in copies:ob.select_set(True)
    bpy.context.view_layer.objects.active=copies[0]
    if len(copies)>1:bpy.ops.object.join()
    ob=bpy.context.object;ob.name=name
    if slot_order:
        # The runtime body swap must keep water MIDs and every other material override.
        old_slots=[m.name for m in ob.data.materials]
        indices=[slot_order.index(old_slots[p.material_index]) for p in ob.data.polygons]
        ob.data.materials.clear()
        for slot in slot_order:ob.data.materials.append(bpy.data.materials[slot])
        for polygon,index in zip(ob.data.polygons,indices):polygon.material_index=index
    bpy.context.scene.cursor.location=co(pivot);bpy.ops.object.origin_set(type='ORIGIN_CURSOR');ob.location=(0,0,0)
    tri=ob.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    # Flat rims/caps inherited vertical UVs, collapsing their tangent basis on UE import.
    # Keep every valid authored island; project only collapsed triangles onto their own plane.
    uv_layer=ob.data.uv_layers.active
    repaired=0
    if uv_layer:
        for polygon in ob.data.polygons:
            loops=list(polygon.loop_indices)
            a,b,c=[uv_layer.data[li].uv.copy() for li in loops]
            if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))>1e-12:continue
            drop=max(range(3),key=lambda axis:abs(polygon.normal[axis]))
            axes=[axis for axis in range(3) if axis!=drop]
            for li in loops:
                p=ob.data.vertices[ob.data.loops[li].vertex_index].co
                uv_layer.data[li].uv=(p[axes[0]]*2,p[axes[1]]*2)
            repaired+=1
    path=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},apply_unit_scale=True,
      apply_scale_options='FBX_SCALE_NONE',axis_forward='-Y',axis_up='Z',use_mesh_modifiers=True,
      mesh_smooth_type='FACE',use_tspace=True,colors_type='LINEAR',add_leaf_bones=False,bake_anim=False)
    manifest['assets'][name]={'fbx':str(path),'pivot_ue_cm':pivot,'material_slots':[m.name for m in ob.data.materials],
                             'repaired_collapsed_uv_triangles':repaired}
    bpy.data.objects.remove(ob,do_unlink=True)
all_objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
station_slots=['Masonry','DarkSteel','PolishedSteel','Wood','Water','AnvilSteel','BarrelWood']
export('SM_CastingStation',all_objects,(0,0,0),station_slots)
hanging=[o for key,group in tool_rack['groups'].items() if key!='Mounts' for o in group]
export('SM_CastingStationBareRack',[o for o in all_objects if o not in hanging],(0,0,0),station_slots)
manifest['tool_rack']['swing_pivots_ue_cm']={}
for group,x in zip(('Tongs','Hammer','File','Poker'),tool_rack['hook_centers_cm']):
    pivot=(x,44,94.30)
    export('SM_Rack'+group,tool_rack['groups'][group],pivot)
    manifest['tool_rack']['swing_pivots_ue_cm'][group]=pivot
barrel=[o for o in all_objects if o.name.startswith(('Cooling barrel','Barrel iron hoop','Barrel handle'))]
export('SM_CoolingBarrel',barrel,(cx,cy,4))
export('SM_CoolingWater',[water],(cx,cy,46))
export('SM_BlacksmithTongs',tool_rack['groups']['Tongs'],(11,44.45,65))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'CastingStation_RealismV5.blend'))
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print('CASTING_REALISM_GEOMETRY_SAVED '+str(OUT),flush=True)
