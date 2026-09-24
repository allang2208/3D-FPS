"""Boss-only compact material slots, real arrises and contact wear; shared rooms are untouched."""
import math
import bpy
from service_routing import pipe_age

def export(H):
    widths=dict(Columns=.006,MachineBases=.018,PumpWest=.003,PumpEast=.003,Receiver=.002,
        GalleryFrames=.0015,RoofTrusses=.0015,GalleryRails=.001,WallServices=.002,
        Floors=.005,Ceilings=.005,Shell=.005,Frames=.0015,StairWest=.001,StairEast=.001)
    replacement={'ServicePaint':'BossMachinePaint','PaintedSteel':'BossStructuralSteel','BridgeDeck':'BossGrating'}
    for kind,g in H['GROUPS'].items():
        labels=[('BossPipeCoat' if m=='PipeEnamel' else 'BossPipeHardware' if kind=='Services' and m in ('ServiceHardware','BareSteel','PipeCutSteel') else replacement.get(m,m)) for m in g['m']]
        names=list(dict.fromkeys(labels));name='SM_RS_'+H['ROOM']['id']+'_'+kind
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(g['v'],[],g['f']);mesh.update()
        obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
        for n in names:mesh.materials.append(H['MATS'][n])
        uv=mesh.uv_layers.new(name='UVMap');age=mesh.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER')
        pipe_cache={}
        for face,material,authored,smooth in zip(mesh.polygons,labels,g['uv'],g['smooth']):
            face.material_index=names.index(material);face.use_smooth=smooth
            axis=max(range(3),key=lambda i:abs(face.normal[i]));dims=[i for i in range(3) if i!=axis]
            scale=.8 if material=='BossMachinePaint' else .64 if material=='FractureConcrete' else .075 if material=='V2_CeramicFractureCore' else 1.28 if 'WallRelief' in material else 2
            for corner,li in enumerate(face.loop_indices):
                co=mesh.vertices[mesh.loops[li].vertex_index].co
                uv.data[li].uv=authored[corner] if authored is not None else (co[dims[0]]/scale,co[dims[1]]/scale)
                grime=.04
                if kind in ('PumpWest','PumpEast'):
                    center_y=10.7 if kind=='PumpWest' else 14.3
                    grime+=.40*math.exp(-abs(co.z-.76)*4)+.24*math.exp(-abs(co.y-(center_y+.52))*12)
                else:grime+=.30*math.exp(-max(0,co.z)*3)
                grime*=.7+.3*math.sin(co.x*8.2+co.y*3.1)**2
                wet=0
                if material in ('BossFloor','BossWetConcrete'):
                    wall=min(15-abs(co.x),co.y,26-co.y)
                    grime=.32*math.exp(-max(0,wall)*2)
                    for m in H['ROOM']['machines']:
                        x,y,_=m['at'];dist=max(abs(co.x-x)-2.3,abs(co.y-y)-2.5,0)
                        grime=max(grime,.40*math.exp(-dist*2.4))
                    grime*=.60+.4*math.sin(co.x*2.8+co.y*4.1)**2
                if material=='BossWetConcrete':
                    # Outer ring vertices are written first for each disconnected patch.
                    # Distance to the authored irregular boundary gives a 20% feather.
                    for m in H['ROOM']['machines']:
                        x,y,_=m['at']
                        for index,(dx,dy,sx,sy) in enumerate(((1.9,.55,1.2,1.7),(-1.15,2.3,1.0,.8))):
                            xx=(co.x-x-dx)/sx;yy=(co.y-y-dy)/sy;a=math.atan2(yy,xx)
                            radius=1+.14*math.sin(5*a+index)+.10*math.cos(9*a+x)
                            wet=max(wet,max(0,min(1,(1-math.hypot(xx,yy)/radius)/.2)))
                corrosion=0
                if material in ('BossPipeCoat','BossPipeHardware'):
                    vi=mesh.loops[li].vertex_index
                    if vi not in pipe_cache:pipe_cache[vi]=pipe_age(co,H['PIPE_RUNS'])
                    grime,corrosion=pipe_cache[vi]
                    if material=='BossPipeHardware':corrosion=max(corrosion,.42)
                age.data[li].color=(min(.75,grime),corrosion,wet,1)
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
        if kind in widths:
            bevel=obj.modifiers.new('Manufactured edge radii','BEVEL');bevel.width=widths[kind];bevel.segments=2
            bevel.limit_method='ANGLE';bevel.angle_limit=.6;bevel.harden_normals=True
            bpy.ops.object.modifier_apply(modifier=bevel.name)
            # Keep cap/side boundaries sharp while preserving cylindrical smooth sides.
            normal=obj.modifiers.new('Weighted machined faces','WEIGHTED_NORMAL');normal.keep_sharp=True;normal.weight=30
            bpy.ops.object.modifier_apply(modifier=normal.name)
        tri=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
        path=H['OUT']/(name+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
            bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
        H['RECORDS'].append(dict(name=name,room=H['ROOM']['id'],kind=kind,fbx=str(path),origin_m=H['ROOM']['origin_m'],
            materials={'RS_'+n:H['MAPPING'][n] for n in names},collision=kind not in ('Fixtures','CableRoutes','CableTrays','Drainage','FloorDetails')))
        obj.location=H['ROOM']['origin_m']
