"""Opt-in isolated hills check. Reads real spawned components and captures two views."""
import json
import math
import time
import traceback
from pathlib import Path
import unreal as u

if '-ChapelSupportCheck' not in u.SystemLibrary.get_command_line():
    raise RuntimeError('Isolated check flag required')
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelShrineForecourt20261116/WallStoneR3/Check')
OUT.mkdir(parents=True,exist_ok=True)
started=time.monotonic();handle=None;stage=0;next_at=0.;last_log=0.
report={'checks':{},'runtime':True,'captures':[]}
xyz=lambda v:[v.x,v.y,v.z]
def check(name,ok,detail=None):report['checks'][name]={'pass':bool(ok),'detail':detail}
def snapshot(c):
    o,e,_=u.SystemLibrary.get_component_bounds(c)
    mesh=c.get_editor_property('static_mesh') if isinstance(c,u.StaticMeshComponent) else None
    return {'name':c.get_name(),'class':c.get_class().get_name(),'location':xyz(c.get_world_location()),
            'origin':xyz(o),'extent':xyz(e),'receives_decals':c.get_editor_property('receives_decals'),
            'mesh':mesh.get_path_name() if mesh else None,
            'materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]}
def trace(world,x,y,high,low,ignore,complex=True):
    result=u.SystemLibrary.line_trace_single(world,u.Vector(x,y,high),u.Vector(x,y,low),u.TraceTypeQuery.TRACE_TYPE_QUERY1,complex,ignore,u.DrawDebugTrace.NONE,True)
    if result is None:return {'hit':False}
    hit=next((item for item in result if isinstance(item,u.HitResult)),None) if isinstance(result,tuple) else result
    if hit is None:return {'hit':False}
    # NativeBreakFunc is exposed on the struct, not GameplayStatics, in Python.
    data=hit.to_tuple()
    return {'hit':bool(data[0]),'point':xyz(data[5]),'normal':xyz(data[7]),
            'actor':data[9].get_name() if data[9] else None,'component':data[10].get_name() if data[10] else None}
def capture(world,name):
    path=OUT/(name+'.png')
    u.SystemLibrary.execute_console_command(world,'HighResShot 1280x720 filename="'+str(path).replace('\\','/')+'"')
    report['captures'].append(str(path))
def finish(world,error=None):
    if error:report['error']=error
    report['elapsed_seconds']=time.monotonic()-started
    report['passed']=not error and all(v['pass'] for v in report['checks'].values())
    (OUT/'runtime.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    u.log('CHAPEL_SUPPORT_RUNTIME_CHECK '+json.dumps({'passed':report['passed'],'checks':len(report['checks']),'error':error}))
    if handle:u.unregister_slate_post_tick_callback(handle)
    u.SystemLibrary.execute_console_command(world,'quit')
def tick(dt):
    global stage,next_at,last_log,shrine,pedestal,statue,pawn,pc,center,direction,ground_z
    world=u.get_default_object(u.UnrealEditorSubsystem).get_game_world()
    if not world:return
    elapsed=time.monotonic()-started
    try:
        if elapsed>600:finish(world,'Timed out waiting for the actual hills scene');return
        if elapsed<next_at:return
        if stage==0:
            hills=u.GameplayStatics.get_all_actors_of_class(world,u.TemperateHillsWorld)
            shrines=u.GameplayStatics.get_all_actors_of_class(world,u.ChapelShrine)
            pc=u.GameplayStatics.get_player_controller(world,0);pawn=u.GameplayStatics.get_player_pawn(world,0)
            if not hills or not hills[0].get_editor_property('ready') or not shrines or not pawn or pc.is_move_input_ignored():
                if elapsed-last_log>=15:u.log('CHAPEL_SUPPORT_WAIT %.1f'%elapsed);last_log=elapsed
                return
            shrine=shrines[0];components=shrine.get_components_by_class(u.StaticMeshComponent)
            pedestal=next((c for c in components if c.get_name()=='RockPedestal'),None)
            statue=next((c for c in components if c.get_name()=='Statue'),None)
            if not pedestal or not statue or not statue.static_mesh:return
            center=shrine.get_actor_location();ground_z=center.z-100.
            direction=pawn.get_actor_location()-center;direction.z=0.;direction=direction.normal()
            pawn.set_actor_location(center+direction*330.+u.Vector(0,0,6),False,True)
            pc.set_control_rotation(u.MathLibrary.find_look_at_rotation(center+direction*330.+u.Vector(0,0,65),center+u.Vector(0,0,-35)))
            report['seed']=hills[0].get_editor_property('seed');report['world']=world.get_path_name()
            stage=1;next_at=elapsed+15.;return
        if stage==1:
            ps,ss=snapshot(pedestal),snapshot(statue);report['pedestal']=ps;report['statue']=ss
            top=ps['origin'][2]+ps['extent'][2];bottom=ps['origin'][2]-ps['extent'][2]
            statue_min=ss['origin'][2]-ss['extent'][2]
            report['installed_statue_seat_depth_cm']=top-statue_min
            check('statue_contact',-1.1<=statue_min-top<=.1,{'bounds_gap_cm':statue_min-top})
            catalog=json.loads(Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/shrines.json').read_text(encoding='utf-8'))['statues']
            chosen=next(r for r in catalog if r['mesh']==ss['mesh'])
            original=json.loads(Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelShrineForecourt20261116/SupportFixR2/Check/saved-assets-before-seat-adjustment.json').read_text(encoding='utf-8'))
            measured=next(r for r in original['statues'] if r['id']==chosen['id'])
            actual_gap=measured['actual_contact_gap_cm']-report['installed_statue_seat_depth_cm']
            check('actual_statue_geometry_contact',-1.1<=actual_gap<=.1,{'id':chosen['id'],'actual_gap_cm':actual_gap})
            check('both_shrine_parts_reject_decals',not ps['receives_decals'] and not ss['receives_decals'])
            check('runtime_pedestal_material',all(m and 'M_ChapelShrinePedestalStone' in m for m in ps['materials']))
            report['ground_traces']=[];report['support_traces']=[]
            scale=pedestal.get_world_scale();radius=220.*scale.x
            for i in range(9):
                a=math.tau*(i-1)/8.;r=0. if i==0 else radius*.95
                t=trace(world,center.x+math.cos(a)*r,center.y+math.sin(a)*r,ground_z+90.,ground_z-150.,[shrine,pawn])
                report['ground_traces'].append(t)
            check('bed_contact_all_around',all(t['hit'] and .5<t['point'][2]-bottom<8. for t in report['ground_traces']),{'burial_cm':[t['point'][2]-bottom if t['hit'] else None for t in report['ground_traces']]})
            for i in range(8):
                a=math.tau*i/8.;r=radius*.76
                for complex in (False,True):
                    t=trace(world,center.x+math.cos(a)*r,center.y+math.sin(a)*r,ground_z+85.,ground_z-50.,[pawn],complex)
                    t['complex']=complex;report['support_traces'].append(t)
            check('solid_top_collision',all(t['hit'] and t['component']=='RockPedestal' and abs(t['point'][2]-top)<.2 for t in report['support_traces']))
            camera=pawn.get_editor_property('first_person_camera')
            primitives=[c for c in camera.get_children_components(True) if isinstance(c,u.PrimitiveComponent)]
            report['first_person']=[snapshot(c) for c in primitives]
            check('first_person_rejects_decals',len(primitives)>0 and all(not c.get_editor_property('receives_decals') for c in primitives),{'components':len(primitives)})
            ground_names=('M_ChapelShrinePedestalStone','M_ChapelYardCap','M_ChapelEarth','M_TemperateGround')
            check('first_person_has_no_ground_material_assignment',not any(any(name in m for name in ground_names) for c in report['first_person'] for m in c['materials'] if m))
            tools=[c for c in pawn.get_components_by_class(u.PrimitiveComponent) if c.get_name()=='ProductionToolMesh']
            check('production_tool_rejects_decals',len(tools)==1 and not tools[0].get_editor_property('receives_decals'))
            report['nearby_decals']=[]
            for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
                for c in actor.get_components_by_class(u.DecalComponent):
                    if (c.get_world_location()-center).length()<5000:
                        report['nearby_decals'].append({'actor':actor.get_name(),'component':c.get_name(),'location':xyz(c.get_world_location()),'size':xyz(c.get_editor_property('decal_size'))})
            capture(world,'runtime-first-person');stage=2;next_at=elapsed+5.;return
        if stage==2:
            pawn.crouch()
            pawn.set_actor_location(center+direction*280.+u.Vector(0,0,6),False,True)
            eye=center+direction*280.+u.Vector(0,0,10.)
            pc.set_control_rotation(u.MathLibrary.find_look_at_rotation(eye,center+u.Vector(0,0,-75.)))
            stage=3;next_at=elapsed+15.;return
        if stage==3:
            capture(world,'runtime-support-contact');stage=4;next_at=elapsed+4.;return
        if stage==4:finish(world)
    except Exception:finish(world,traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
u.log('CHAPEL_SUPPORT_RUNTIME_CHECK registered')
