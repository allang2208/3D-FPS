"""Independent HK416-derived common attachments, preserving original UV0/PBR.

Canonical meshes use metres, +X forward / +Z up. HK416 keeps its component
reference frame. Interface variants retain the measured host-side saddles.
"""
import bpy,bmesh,json,math,re,importlib.util
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent;H=S/'HK416Reworked20260930';X=O/'Exports';X.mkdir(exist_ok=True)
a=json.loads((H/'authoring.json').read_text());original=Matrix(a['root_matrix'])@Matrix(a['source_to_weapon_root']);inverse=original.inverted()
interfaces=json.loads((O/'interfaces.json').read_text());records={}
spec=importlib.util.spec_from_file_location('eoth_reticle_geometry',O/'reticle_geometry.py');reticle_geometry=importlib.util.module_from_spec(spec);spec.loader.exec_module(reticle_geometry)
bpy.context.preferences.filepaths.save_version=0

def select(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob

def adapter(family):
    source=interfaces[family];name=next(iter(source['meshes']))
    with bpy.data.libraries.load(source['file'],link=False) as (src,dst):dst.objects=[name]
    ob=dst.objects[0];bpy.context.collection.objects.link(ob);ob.parent=None;ob.hide_set(False)
    keep={i for i,m in enumerate(ob.data.materials) if 'AdapterSteel' in m.name or 'G18_AttachmentFinish' in m.name}
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index not in keep],context='FACES')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(ob.data);bm.free()
    return ob

def physical_uv(ob):
    while len(ob.data.uv_layers)<4:ob.data.uv_layers.new(name='UV'+str(len(ob.data.uv_layers)))
    for uv in ob.data.uv_layers:
        for f in ob.data.polygons:
            axes=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(f.normal[k]))]
            for li in f.loop_indices:
                p=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]/.1+.5,p[axes[1]]/.1+.5)

def box(name,loc,size):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);ob=bpy.context.object;ob.name=name;ob.scale=size
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    ob.data.materials.append(bpy.data.materials.get('Universal_InterfaceSteel') or bpy.data.materials.new('Universal_InterfaceSteel'))
    bevel=ob.modifiers.new('Machined edges','BEVEL');bevel.width=.00025;bevel.segments=3;bpy.ops.object.modifier_apply(modifier=bevel.name);physical_uv(ob)
    return ob

def collar(back):
    # A closed annular section with an open central bore. Rear threads overlap
    # the barrel; the front shoulder joins the original can's inlet.
    n=96;profile=[(back,.0084),(back+.002,.0084),(-.001,.012),(.003,.012),(.006,.010),(.006,.0065),(back,.0065)]
    verts=[(x,r*math.cos(i*2*math.pi/n),r*math.sin(i*2*math.pi/n)) for x,r in profile for i in range(n)]
    faces=[(j*n+i,j*n+(i+1)%n,((j+1)%len(profile))*n+(i+1)%n,((j+1)%len(profile))*n+i) for j in range(len(profile)) for i in range(n)]
    me=bpy.data.meshes.new('OpenBoreInterface');me.from_pydata(verts,[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new('OpenBoreInterface',me);bpy.context.collection.objects.link(ob)
    me.materials.append(bpy.data.materials.get('Universal_InterfaceSteel') or bpy.data.materials.new('Universal_InterfaceSteel'));physical_uv(ob)
    return ob

for kind,families in [('eoth_holographic',['Common','HK416','M16','M1911','G18','DW715']),('multi_caliber_suppressor',['Common','Pistol','HK416'])]:
    source='holographic' if kind=='eoth_holographic' else 'suppressor'
    for family in families:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        with bpy.data.libraries.load(str(H/f'Exports/Attachments/SM_HK416_{source}_Editable.blend'),link=False) as (src,dst):dst.objects=['SM_HK416_'+source]
        bpy.context.scene.collection.objects.link(dst.objects[0])
        bpy.context.preferences.filepaths.save_version=0
        ob=bpy.data.objects['SM_HK416_'+source]
        for other in list(bpy.context.scene.objects):
            if other!=ob:bpy.data.objects.remove(other,do_unlink=True)
        ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.hide_set(False);ob.hide_render=False
        extra=[];frame=Matrix.Identity(4)
        if family!='HK416':
            if source=='holographic':
                pistol=family in ('M1911','G18','DW715');scale=.65 if pistol else 1.
                seat=.028423 if pistol else .0294;lift=.0018 if family=='G18' else -.0002 if pistol else 0.
                frame=Matrix.Translation((0,0,lift))@Matrix.Scale(4*scale,4)@Matrix.Rotation(-math.pi/2,4,'Z')@Matrix.Translation((0,0,-seat))@inverse
                if pistol:extra.append(adapter(family))
                elif family=='M16':
                    extra.extend([box('Carry handle rail',(0,0,-.003),(.17,.021,.006)),box('Carry handle saddle',(.012,0,-.0075),(.105,.013,.005)),box('Handle locking shoe',(.008,0,-.016),(.024,.018,.004))])
                    for x in [-.060,-.032,-.004,.024,.052]:extra.append(box('Rail lug',(x,0,-.0008),(.009,.023,.0016)))
            else:
                frame=Matrix.Scale(4,4)@Matrix.Rotation(-math.pi/2,4,'Z')@Matrix.Translation((0,-.08077891171,-.01987559302))@inverse
                extra.append(collar(-.0122 if family=='Pistol' else -.002))
            ob.data.transform(frame);ob.data.update()
        # Join by channel identity, not donor-specific layer names. The original
        # maps use UV0; host coatings may read UV2/UV3 for physical surface detail.
        for part in [ob]+extra:
            coords=[[tuple(p.uv) for p in layer.data] for layer in part.data.uv_layers]
            for layer in list(part.data.uv_layers):part.data.uv_layers.remove(layer)
            for i in range(4):
                layer=part.data.uv_layers.new(name='UV'+str(i));values=coords[i] if i<len(coords) else coords[0] if coords else []
                for j,p in enumerate(values):layer.data[j].uv=p
        select(ob)
        for part in extra:part.select_set(True)
        if extra:bpy.ops.object.join()
        ob.name=f'SM_{family}_{kind}';sockets={}
        for label,p in a['static'][source]['sockets_source_m'].items():
            point=frame@original@Vector(p);sockets[label]=list(point)
            child=bpy.data.objects.new('SOCKET_'+label,None);bpy.context.collection.objects.link(child);child.parent=ob;child.location=point;child.select_set(True)
        if source=='holographic':
            sockets['AimCenter']=sockets['SightRear']
            reticle_geometry.replace_reticle(ob,sockets)
        file=X/(ob.name+'.fbx')
        for layer in ob.data.uv_layers:layer.active_render=False
        ob.data.uv_layers.active_index=0;ob.data.uv_layers[0].active_render=True
        bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
        bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(X/(ob.name+'_Editable.blend')))
        records[family+'/'+kind]={'fbx':str(file),'name':ob.name,'kind':kind,'family':family,'sockets_blender_m':sockets,'source':str(H/f'Exports/Attachments/SM_HK416_{source}_Editable.blend'),'materials':[m.name for m in ob.data.materials],'interface':interfaces.get(family,{}).get('file','original HK416 reference frame' if family=='HK416' else 'canonical Picatinny or open-bore interface'),'runtime_tested':False}
        (O/'authoring.json').write_text(json.dumps(records,indent=2));print('COMMON_PART_AUTHORED',ob.name,flush=True)
