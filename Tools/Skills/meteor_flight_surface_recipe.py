"""Surface-rooted meteor flame and speed-adaptive swept wake; no impact edits."""
import math
from pathlib import Path
import unreal as u
from build_fireball_assets import API, LIB, ref, assignments, put, setdata
from build_fireball_flames import FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import expression, user_parameter
from build_fireball_slow_burn import smooth
from meteor_renderer_bindings import bind_impact_attributes

ROOT=Path(__file__).resolve().parents[2]
VEC4='/Script/CoreUObject.Vector4f'
A,N='Particles.Age','Particles.NormalizedAge'
SEED='frac(float(Particles.UniqueID)*.61803398875+.173)'
VAR='frac(float(Particles.UniqueID)*.41421356237+.317)'
ANGLE='(float(Particles.UniqueID)*2.39996323+.4)'
E=u.EditorAssetLibrary

def sample_surface():
    """Ray-sample the actual closed rock. Read geometry only; never save it."""
    path='/Game/Skills/FireMagic20260921/MeteorClosedVolumeV1/SM_MeteorClosedRock'
    model=u.ModelingService
    result=model.load_mesh_from_static_mesh(path,0)
    if not result.get_editor_property('success'):raise RuntimeError('Cannot read meteor rock geometry')
    handle=result.get_editor_property('handle')
    try:
        mesh=model.get_dynamic_mesh(handle)
        query=u.GeometryScript_MeshQueries
        info=model.get_mesh_info(handle)
        lo,hi=info.get_editor_property('bounds_min'),info.get_editor_property('bounds_max')
        diameter=max(hi.x-lo.x,hi.y-lo.y,hi.z-lo.z)
        vertices={}
        for index in range(query.get_num_vertex_i_ds(mesh)):
            p,valid=query.get_vertex_position(mesh,index)
            if valid:vertices[index]=(p.x,p.y,p.z)
        triangles=[]
        sub=lambda a,b:tuple(a[i]-b[i] for i in range(3))
        dot=lambda a,b:sum(a[i]*b[i] for i in range(3))
        cross=lambda a,b:(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
        for index in range(query.get_num_triangle_i_ds(mesh)):
            t,valid=query.get_triangle_indices(mesh,index)
            if valid:
                a,b,c=vertices[t.x],vertices[t.y],vertices[t.z]
                e1,e2=sub(b,a),sub(c,a)
                triangles.append((a,e1,e2))
        points=[]
        for index in range(48):
            z=1-2*(index+.5)/48
            radius=math.sqrt(1-z*z)
            angle=index*2.39996323
            direction=(radius*math.cos(angle),radius*math.sin(angle),z)
            nearest=None
            for p0,e1,e2 in triangles:
                p=cross(direction,e2);det=dot(e1,p)
                if abs(det)<1e-9:continue
                start=tuple(-v for v in p0)
                bary_u=dot(start,p)/det
                if bary_u<0 or bary_u>1:continue
                q=cross(start,e1);bary_v=dot(direction,q)/det
                if bary_v<0 or bary_u+bary_v>1:continue
                distance=dot(e2,q)/det
                if distance<=0 or (nearest and distance>=nearest[0]):continue
                normal=cross(e1,e2)
                length=math.sqrt(dot(normal,normal))
                normal=tuple(v/length for v in normal)
                if dot(normal,direction)<0:normal=tuple(-v for v in normal)
                nearest=(distance,normal)
            if nearest is None:raise RuntimeError('Cannot place flame root on rock surface')
            distance,normal=nearest
            # 1.2 source cm above the mesh; actor multiplies by BodyScale later.
            point=[(direction[i]*distance+normal[i]*1.2)*80/diameter for i in range(3)]
            points.append(dict(position=point,normal=list(normal)))
        return dict(mesh=path,source_diameter_cm=diameter,normalized_diameter_cm=80,points=points)
    finally:model.release_mesh(handle)

def selection(points,key):
    def vector(point):return 'float3('+','.join(f'{v:.6f}' for v in point[key])+')'
    result=vector(points[-1])
    for index in reversed(range(len(points)-1)):
        result=f'({SEED}<{(index+1)/len(points):.8f}?{vector(points[index])}:{result})'
    return result

def rotate(value):
    terms=[]
    for axis,component,default in [('X','x','1,0,0'),('Y','y','0,1,0'),('Z','z','0,0,1')]:
        basis=f'User.RockAxis{axis}'
        terms.append(f'(dot({basis},{basis})>.5?{basis}:float3({default}))*({value}).{component}')
    return '('+'+'.join(terms)+')'

def sample_module(system,emitter,tag,values):
    key='Meteor.FlightSurface.'+emitter+'.'+tag
    module=E.get_metadata_tag(system,key)
    if not module:
        entries=[]
        for name,(typ,_) in values.items():
            entry=u.NiagaraExt_SetParameterEntry()
            entry.import_text('(Variable=(Name="'+name+'",Type=(ClassStructOrEnum="'+typ+'",UnderlyingType=2)))')
            entries.append(entry)
        module=str(API.call_method('AddSetParametersModule',(ref(system,emitter,'ParticleSpawnScript'),entries)).get_editor_property('module_name'))
        E.set_metadata_tag(system,key,module)
    for name,(_,code) in values.items():
        expression(system,emitter,'ParticleSpawnScript',module,name,code)

def apply(mantle,tail,fire,smoke,profile):
    if not E.get_metadata_tag(mantle,'Meteor.FlightSurface.Axes'):
        for axis in ['X','Y','Z']:user_parameter(mantle,'RockAxis'+axis,VEC3)
        E.set_metadata_tag(mantle,'Meteor.FlightSurface.Axes','1')
    anchor=rotate('Particles.MeteorSurfaceAnchor')
    normal=rotate('Particles.MeteorSurfaceNormal')
    for name,rate,life,size,alpha,lift in [
        ('V6AttachedHeat',48,f'.28+.12*{VAR}','float2(35,44)',.55,'0'),
        ('V6LiftedTongues',18,f'.24+.10*{VAR}','float2(25,64)',.43,f'7*{N}*{N}'),
    ]:
        expression(mantle,name,'EmitterUpdateScript','SpawnRate','SpawnRate',f'{rate}*saturate(User.Fade)')
        appearance={
            'Particles.SpriteSize':(VEC2,f'{size}*(.87+.20*{VAR})*(1-.12*{N})'),
            'Particles.Color':(COLOR,f'float4(1,1,1,{alpha}*User.Fade*{smooth(0,.06,N)}*(1-{smooth(.64,1,N)}))'),
            'Particles.DynamicMaterialParameter':(VEC4,f'float4(frac({VAR}+{A}*.62),{SEED},.70-.22*{N},0)'),
        }
        rooted={
            'Particles.Position':(POSITION,f'{anchor}-User.FlightDirection*({lift})'),
            'Particles.SpriteAlignment':(VEC3,f'normalize(-User.FlightDirection+{normal}*.28+float3(0,0,.001))'),
        }
        assignments(mantle,name,'ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,life),**appearance})
        sample_module(mantle,name,'Samples',{
            'Particles.MeteorSurfaceAnchor':(VEC3,selection(profile['points'],'position')),
            'Particles.MeteorSurfaceNormal':(VEC3,selection(profile['points'],'normal')),
        })
        sample_module(mantle,name,'Root',rooted)
        assignments(mantle,name,'ParticleUpdateScript',{'Particles.Velocity':(VEC3,'float3(0,0,0)'),**appearance,**rooted})
        setdata('SetRendererData',u.NiagaraExt_RendererData,ref(mantle,name,renderer=0),
                {'PivotInUVSpace':{'X':.5,'Y':.88},'Alignment':'CustomAlignment'})
    mantle.set_editor_property('fixed_bounds',u.Box(min=u.Vector(-90,-90,-90),max=u.Vector(90,90,155)))
    scale='max(User.VisualScale,1.0)'
    for name,rate,life,size,alpha,offset,smoking in [
        ('V6HotWake',f'clamp(User.FlightSpeed/({scale}*14),40,96)',f'.34+.08*{SEED}','float2(54,106)',.43,f'1.5+3.5*{SEED}',False),
        ('V6TornWake',f'clamp(User.FlightSpeed/({scale}*60),10,20)',f'.26+.09*{VAR}','float2(31,83)',.29,f'7+5*{SEED}',False),
        ('V6CoolingWake','8',f'.52+.18*{SEED}','float2(57,90)',.20,f'3+6*{SEED}',True),
    ]:
        expression(tail,name,'EmitterUpdateScript','SpawnRate','SpawnRate',f'({rate})*saturate(User.Fade)')
        spread=f'float3(cos({ANGLE}),sin({ANGLE}),0)*({offset})'
        fade=(f'{smooth(0,.18,N)}*(1-{smooth(.40,1,N)})' if smoking else
              f'{smooth(0,.015,N)}*(1-{smooth(.42,1,N)})')
        appearance={
            'Particles.SpriteSize':(VEC2,f'{size}*{scale}*(.90+.14*{VAR})*'+(f'(.85+.42*{N})' if smoking else f'(1-.25*{N})')),
            'Particles.SpriteAlignment':(VEC3,'normalize(-User.FlightDirection+float3(0,0,.001))'),
            'Particles.Color':(COLOR,f'float4('+('.20,.18,.16,' if smoking else '1,1,1,')+f'{alpha}*{fade})'),
            'Particles.DynamicMaterialParameter':(VEC4,f'float4(frac({VAR}+{A}*.62),{SEED},'+('0' if smoking else f'.90*pow(1-{N},.85)')+',0)'),
        }
        spawn={
            'Particles.Lifetime':(FLOAT,life),
            'Particles.Position':(POSITION,f'lerp(User.PreviousPosition,User.CurrentPosition,{SEED})+{spread}*{scale}'),
            'Particles.Velocity':(VEC3,f'-User.FlightDirection*(8+min(User.FlightSpeed*.004,16))+{spread}*.35'),**appearance,
        }
        force=f'float3(sin(Particles.Position.z*.016+{VAR}*6)*10,cos(Particles.Position.z*.014+{SEED}*6)*10,12)'
        update={
            'Particles.Position':(POSITION,'Particles.Position+Particles.Velocity*Engine.DeltaTime'),
            'Particles.Velocity':(VEC3,f'(Particles.Velocity+{force}*Engine.DeltaTime)*exp(-1.6*Engine.DeltaTime)'),**appearance,
        }
        assignments(tail,name,'ParticleSpawnScript',spawn)
        assignments(tail,name,'ParticleUpdateScript',update)
        setdata('SetRendererData',u.NiagaraExt_RendererData,ref(tail,name,renderer=0),
                {'PivotInUVSpace':{'X':.5,'Y':.5 if smoking else .82}})
    # NE_Core's inherited bindings must explicitly read these computed values.
    bind_impact_attributes(mantle)
    bind_impact_attributes(tail)
    for material in [fire,smoke]:
        for node in LIB.get_material_expressions(material):
            if isinstance(node,u.MaterialExpressionCustom):
                tag=node.get_editor_property('description')
                if tag=='MeteorV6.Sample':
                    node.set_editor_property('code',(ROOT/'Tools/Skills/meteor_flight_surface_sample.hlsl').read_text(encoding='utf8'))
                elif tag=='MeteorV6.Thermal':
                    node.set_editor_property('code', '''float heat=saturate(Fields.g*.72+sqrt(saturate(Fields.r))*.28);
float3 warm=lerp(float3(.8,.035,.001),float3(1,.23,.012),smoothstep(.12,.60,heat));
float3 fire=lerp(warm,float3(1,.62,.12),smoothstep(.58,.98,heat));
return fire*(1.2+3.2*heat*heat)*max(0,Dynamic.z)*Tint;''')
            elif isinstance(node,u.MaterialExpressionDepthFade) and material==fire:
                node.set_editor_property('fade_distance_default',2.5)
    E.set_metadata_tag(mantle,'Meteor.FlightSurface','48 mesh-sampled roots; rotating rock axes; bounded tongue lift')
    E.set_metadata_tag(tail,'Meteor.FlightSurface','Speed-adaptive swept births; compact core, torn edges, cooling smoke')
