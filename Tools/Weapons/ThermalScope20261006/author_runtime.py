"""Fit the existing thermal master to measured, already used weapon interfaces."""
import bpy,bmesh,json,math,re
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).resolve().parents[3];S=P/'SourceAssets';O=S/'ThermalScopeRuntime20261007';E=O/'Exports';E.mkdir(parents=True,exist_ok=True)
source=S/'ThermalScope20261006';auth=json.loads((source/'authoring.json').read_text(encoding='utf-8'))
interfaces=json.loads((S/'HK416UniversalParts20260930/interfaces.json').read_text())
hk=json.loads((S/'HK416Reworked20260930/authoring.json').read_text())
original=Matrix(hk['root_matrix'])@Matrix(hk['source_to_weapon_root'])
hk_frame=(Matrix.Scale(4,4)@Matrix.Rotation(-math.pi/2,4,'Z')@Matrix.Translation((0,0,-.0294))@original.inverted()).inverted()
report={'source':str(source/'Model/ThermalScope_Editable.blend'),'runtime_tested':False,'models':{}}

def select(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
def fbx(part):
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(source/'Exports'/('SM_ThermalScope_'+part+'.fbx')))
    objects=[ob for ob in bpy.data.objects if ob not in before and ob.type=='MESH']
    for ob in objects:
        select(ob);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    return objects
def adapter(family):
    if family=='PitViper':
        file=S/'PitViper2011OpticPreviewFix20261002/Exports/SM_PitViper2011_eoth_holographic_Editable.blend'
        name='SM_PitViper2011_eoth_holographic'
    else:
        spec=interfaces[family];file=Path(spec['file']);name=next(iter(spec['meshes']))
    with bpy.data.libraries.load(str(file),link=False) as (src,dst):dst.objects=[name]
    ob=dst.objects[0];bpy.context.collection.objects.link(ob);ob.parent=None;ob.hide_set(False);ob.hide_render=False
    keep={i for i,m in enumerate(ob.data.materials) if any(k in m.name.lower() for k in ('adapter','attachmentfinish','interfacesteel'))}
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index not in keep],context='FACES')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(ob.data);bm.free()
    ob.data.materials.clear();ob.data.materials.append(bpy.data.materials['Thermal_Graphite'])
    for face in ob.data.polygons:face.material_index=0
    return ob,str(file)
def box(name,loc,size):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);ob=bpy.context.object;ob.name=name;ob.scale=size
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    ob.data.materials.append(bpy.data.materials['Thermal_Graphite'])
    bevel=ob.modifiers.new('Seat edge bevel','BEVEL');bevel.width=.00025;bevel.segments=3;bpy.ops.object.modifier_apply(modifier=bevel.name)
    return ob
def export(name,objects,frame,sockets):
    for ob in objects:
        ob.data.transform(frame);ob.data.update()
        # A consistent UV0 name retains the source texture coordinates on join.
        if ob.data.uv_layers:ob.data.uv_layers[0].name='SurfaceUV'
        else:
            uv=ob.data.uv_layers.new(name='SurfaceUV')
            for loop in ob.data.loops:
                v=ob.data.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(v.x*50,v.z*50)
    select(objects[0])
    for ob in objects:ob.select_set(True)
    if len(objects)>1:bpy.ops.object.join()
    ob=bpy.context.object;ob.name=name
    tri=ob.modifiers.new('Final export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    path=E/(name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(E/(name+'_Editable.blend')))
    def ue(p):return [p.x*100,-p.y*100,p.z*100]
    rotate=frame.to_quaternion();xf=rotate@Vector((1,0,0));zf=rotate@Vector((0,0,1))
    report['models'][name]={'fbx':str(path),'sockets':{k:ue(frame@Vector(v)) for k,v in sockets.items()},
        'socket_forward':[xf.x,-xf.y,xf.z],'socket_up':[zf.x,-zf.y,zf.z]}
    return ob

for family in ('Common','HK416','M16','M1911','G18','DW715','PitViper'):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
    parts=fbx('Body')+fbx('RailMount')+fbx('Display');selector=fbx('ZoomSelector')
    for m in list(bpy.data.materials):
        stem=re.sub(r'[._]\d{3}$','',m.name)
        if stem=='Thermal_Graphite' and not bpy.data.materials.get('Thermal_Graphite'):m.name='Thermal_Graphite'
    fit_source='Canonical Picatinny clamp; mount origin is the rail crown'
    lift=0.;extra=[]
    if family in ('M1911','G18','DW715','PitViper'):
        seat,fit_source=adapter(family);extra.append(seat)
        top=max(v.co.z for v in seat.data.vertices)
        # Keep the true gun-facing surface. A flat cap mates it to this optic's
        # clamp, independently of the old EOTH housing's contoured underside.
        lift=max(0.,top)+.00065
        extra.append(box('Thermal rail cap',(0,0,lift-.00045),(.048,.0212,.0011)))
    elif family=='M16':
        extra += [box('Carry handle rail',(0,0,-.003),(.17,.021,.006)),box('Carry handle saddle',(.012,0,-.0075),(.105,.013,.005)),box('Handle locking shoe',(.008,0,-.016),(.024,.018,.004))]
        fit_source='HK416UniversalParts20260930 measured M16 carry-handle saddle'
    for ob in parts:ob.data.transform(Matrix.Translation((0,0,lift)))
    sockets={k:Vector((p[0]/100,-p[1]/100,p[2]/100+lift)) for k,p in auth['models']['SM_ThermalScope_Body']['sockets_ue_cm'].items()}
    frame=hk_frame if family=='HK416' else Matrix.Identity(4)
    body=export('SM_Thermal_'+family,parts+extra,frame,sockets)
    report['models'][body.name]['interface_source']=fit_source
    # The selector remains at its own pivot; the socket carries host rotation.
    selector_scale=Matrix.Diagonal((*frame.to_scale(),1.))
    export('SM_ThermalSelector_'+family,selector,selector_scale,{})
    (O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('THERMAL_INTERFACE_AUTHORED '+family,flush=True)
