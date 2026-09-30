"""Seat existing shared attachments on measured 201 interfaces; retain UV0."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=json.loads((O/'sources.json').read_text());B=json.loads((O/'geometry_source_bounds.json').read_text())
E=O/'Exports';E.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
grips=['vertical','tactical_vertical','canted','prism','angled']
stocks=['skeleton','core_stock','qr_performance','tactical_telescopic']
surface=json.loads((O.parent/'Refine12/201_surface.json').read_text())
r=S['201']['bones']['WPN_root'];q=r['q'];root=Matrix.LocRotScale(Vector(r['p']),Quaternion((q[3],*q[:3])),Vector(r['s']))
inv=root.inverted();reflect=Matrix.Diagonal((1,-1,1,1))
verts=[reflect@inv@Vector(v) for v in surface['vertices']]
def points(name):
    i=surface['materials'].index(name)
    ids={v for tri,mat in zip(surface['triangles'],surface['material_ids']) if mat==i for v in tri}
    return [verts[j] for j in ids]
def center(v):return Vector([(min(p[i] for p in v)+max(p[i] for p in v))*.5 for i in range(3)])
rear=points('M_LMG201_FactoryRearGrip');hi=max(v.z for v in rear);lo=min(v.z for v in rear)
rear_top=center([v for v in rear if v.z>hi-.005]);rear_top.z=hi-.0005
rear_bottom=center([v for v in rear if v.z<lo+.015])
handguard=points('M_LMG201_Handguard');seat=[v for v in handguard if -.36<v.y<-.30 and abs(v.x)<.016]
rail_z=min(v.z for v in seat)+.0007
grip_delta=Vector((.00083815,.025937,rail_z-.031700287))
out={'meshes':{},'grip_transform_blender':[list(x) for x in Matrix.Translation(grip_delta)],'interfaces':{'underbarrel_top':[.0008,-.335,rail_z],'stock_face':[.0008,.078,.035],'rear_grip_top':list(rear_top),'rear_grip_bottom':list(rear_bottom)}}
def cube(name,p,size,mat):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.name=name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
    b=o.modifiers.new('SeatEdges','BEVEL');b.width=.00065;b.segments=3;bpy.ops.object.modifier_apply(modifier=b.name)
    n=o.modifiers.new('SeatNormals','WEIGHTED_NORMAL');n.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=n.name)
    o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4);return o
for key,info in S['meshes'].items():
    if key=='pso1_4x':continue  # Retired 201 option; skip historical source snapshots.
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=info['file'])
    obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];bindings={}
    for o in obs:
        o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4)
        # UE's combined FBX names materials by interface object, not slot name.
        mapping={m['path'].split('.')[-1]:m for m in info['materials']}
        remove=set()
        for i,m in enumerate(o.data.materials):
            original=mapping[m.name]
            if original['slot']=='PKM14_Interface':remove.add(i)
            else:
                old=m.name;m.name='LMG20122_'+key+'_'+str(i);bindings[m.name]=original
        bm=bmesh.new();bm.from_mesh(o.data)
        bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index in remove],context='FACES')
        bm.to_mesh(o.data);bm.free()
    xf=Matrix.Identity(4)
    if key in grips:xf=Matrix.Translation(grip_delta)
    elif key in stocks:xf=Matrix.Translation(Vector((.000838,.015864,-.0279)))
    elif key.endswith('reargrip'):
        pv=[]
        for ob in obs:
            used={i for p in ob.data.polygons for i in p.vertices}
            pv.extend(ob.data.vertices[i].co.copy() for i in used)
        zmax=max(v.z for v in pv);zmin=min(v.z for v in pv)
        top=center([v for v in pv if v.z>zmax-.003]);top.z=zmax
        low=center([v for v in pv if v.z<zmin+.014])
        rotation=(low-top).rotation_difference(rear_bottom-rear_top).to_matrix().to_4x4()
        xf=Matrix.Translation(rear_top)@rotation@Matrix.Translation(-top)
    elif key in ['laser','flashlight']:xf=Matrix.Translation((.018,.075,-.024))
    for o in obs:o.data.transform(xf)
    mat=bpy.data.materials.new('LMG20122_Interface');mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.02,.024,.03,1);bs.inputs['Metallic'].default_value=.78;bs.inputs['Roughness'].default_value=.35
    bindings[mat.name]={'path':'201_INTERFACE','slot':'Interface'}
    if key in grips:
        obs.append(cube('201_UnderRailSeat',(.0008,-.335,rail_z-.0016),(.026,.085,.0032),mat))
    elif key in stocks:obs.append(cube('201_StockSeat',(.0008,.078,.035),(.039,.013,.064),mat))
    elif key.endswith('reargrip'):obs.append(cube('201_GripCollar',rear_top-Vector((0,0,.0015)),(.029,.038,.003),mat))
    elif key in ['laser','flashlight']:obs.append(cube('201_SideClamp',(.036,-.4009,.0359),(.014,.069,.025),mat))
    for o in obs:
        # Only new seats get new UVs; donor channels/normals remain intact.
        if len(o.data.uv_layers)==0:
            uv=o.data.uv_layers.new(name='SeatUV')
            for poly in o.data.polygons:
                axis=max(range(3),key=lambda i:abs(poly.normal[i]));ax=[i for i in range(3) if i!=axis]
                for l in poly.loop_indices:
                    v=o.data.vertices[o.data.loops[l].vertex_index].co;uv.data[l].uv=(v[ax[0]]/.05,v[ax[1]]/.05)
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:o.select_set(True)
    bpy.context.view_layer.objects.active=obs[0]
    name='SM_LMG201_'+key
    bpy.ops.export_scene.fbx(filepath=str(E/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(O/(name+'.blend')))
    # UE centimetres: preserve each socket's orientation and physical scale.
    ue=reflect@xf@reflect;sockets={}
    for n,v in info['sockets'].items():
        p=ue@Vector([a*.01 for a in v['p']]);sockets[n]=dict(v,p=[a*100 for a in p])
    out['meshes'][key]={'name':name,'file':str(E/(name+'.fbx')),'materials':bindings,'sockets':sockets,'transform_blender':[list(r) for r in xf],'source':info['asset']}
    (O/'geometry.json').write_text(json.dumps(out,indent=2))
    print('LMG20122_GEOMETRY',key,flush=True)
