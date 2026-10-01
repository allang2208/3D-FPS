"""Move the two G18 devices forward and conform their existing saddles to the new rail seat."""
import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O=Path(__file__).parent;S=O.parent/'G18Integration20260929';X=O/'Exports';X.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
DELTA=Vector((0,-.025,0));record={};icons={}
bpy.ops.wm.open_mainfile(filepath=str(S/'Single/G18_single_Editable.blend'))
rig=bpy.data.objects['SK_G18_Manny'];inv=rig.data.bones['WPN_root'].matrix_local.inverted()
gun=bpy.data.objects['G18_G18']
rail=BVHTree.FromPolygons([inv@v.co for v in gun.data.vertices],[list(p.vertices) for p in gun.data.polygons])

def select(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob

for kind in ('laser','flashlight'):
    source=S/f'Attachments/SM_G18_{kind}_Editable.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source));ob=bpy.data.objects['SM_G18_'+kind];mesh=ob.data
    world=ob.matrix_world.copy();local=world.inverted();points=[world@v.co for v in mesh.vertices]
    collar_slots={i for i,m in enumerate(mesh.materials) if 'Collar' in m.name}
    collar_faces=[p for p in mesh.polygons if p.material_index in collar_slots]
    collar_vertices={i for p in collar_faces for i in p.vertices}
    collar=BVHTree.FromPolygons(points,[list(p.vertices) for p in collar_faces],epsilon=1e-8)
    bounds=[(min(points[i][axis] for i in collar_vertices),max(points[i][axis] for i in collar_vertices)) for axis in (0,1)]
    # Keep the accepted body's split normals and UVs; the saddle alone changes shape.
    normals=[n.vector.copy() for n in mesh.corner_normals]
    changes=[]
    for v,old in zip(mesh.vertices,points):
        new=old+DELTA
        if v.index in collar_vertices:
            # Sample inside the 0.2 mm rounded perimeter, where both surfaces exist.
            x=max(bounds[0][0]+.0003,min(bounds[0][1]-.0003,old.x))
            y=max(bounds[1][0]+.0003,min(bounds[1][1]-.0003,old.y))
            top=collar.ray_cast(Vector((x,y,.08)),Vector((0,0,-1)))[0]
            contact=rail.ray_cast(Vector((new.x,new.y,-.08)),Vector((0,0,1)))[0]
            if top is None or contact is None:
                raise RuntimeError('Cannot construct G18 rail contact at '+str(tuple(new))+' top='+str(top)+' rail='+str(contact))
            # Deform the upper 1 mm of the saddle and its bevel only. Housing
            # contact lies below this band and retains the exact original fit.
            weight=max(0.,min(1.,1.+(old.z-top.z)/.001))
            # Bottom stays against the translated housing; top follows G18, including rail grooves.
            dz=(contact.z+.00015-top.z)*weight;new.z+=dz;changes.append(dz)
        v.co=local@new
    for p in collar_faces:
        for li in p.loop_indices:normals[li]=Vector((0,0,0))
    mesh.update();mesh.normals_split_custom_set(normals)
    # Reproject only the saddle's coating UV at the existing physical tile size.
    if len(mesh.uv_layers)>1:
        uv=mesh.uv_layers[1]
        for p in collar_faces:
            axes=[i for i in range(3) if i!=max(range(3),key=lambda a:abs(p.normal[a]))]
            for li in p.loop_indices:
                v=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]]/.1+.5,v[axes[1]]/.1+.5)
    for socket in ob.children:
        if socket.type=='EMPTY':
            transform=socket.matrix_world.copy();transform.translation+=DELTA;socket.matrix_world=transform
    bpy.context.view_layer.update()
    sockets={c.name:list(c.matrix_world.translation) for c in ob.children if c.type=='EMPTY'}
    mesh.calc_loop_triangles()
    icons[kind]={'vertices':[list(ob.matrix_world@v.co) for v in mesh.vertices],'triangles':[list(t.vertices) for t in mesh.loop_triangles]}
    select(ob)
    for c in ob.children:
        if c.type=='EMPTY':c.select_set(True)
    file=X/f'SM_G18_{kind}.fbx'
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(X/f'SM_G18_{kind}_Editable.blend'))
    record[kind]={'fbx':str(file),'source':str(source),'body_translation_m':list(DELTA),'forward_shift_mm':25,'guard_front_y_m':-.06311700493,'device_rear_y_m':-.079,'longitudinal_guard_gap_mm':15.88299507,'saddle_contact':'existing closed saddle reshaped between unchanged housing seat and sampled G18 rail underside','saddle_z_change_mm':[min(changes)*1000,max(changes)*1000],'contact_embed_mm':.15,'sockets_blender_m':sockets,'slots':[m.name for m in mesh.materials]}
    print('G18_TACTICAL_AUTHORED '+kind,flush=True)
(O/'authoring.json').write_text(json.dumps(record,indent=2))
(O/'icon_geometry.json').write_text(json.dumps(icons,separators=(',',':')))
