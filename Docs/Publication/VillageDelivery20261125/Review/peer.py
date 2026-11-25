import csv,json,os,time,traceback,unreal as u
from pathlib import Path
G=u.GameplayStatics
root=Path(os.environ['VILLAGE_AUDIT_EVIDENCE'])
role=os.environ['VILLAGE_AUDIT_ROLE']
folder=root/role
folder.mkdir(exist_ok=True,parents=True)
state=json.loads((folder/'progress.json').read_text())['phase'] if (folder/'progress.json').is_file() else 'start'
since=time.monotonic()
began=since
next_action=0.
def put(name,data):
    target=folder/(name+'.json');temp=target.with_suffix('.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8');temp.replace(target)
def move(new):
    global state,since
    state=new;since=time.monotonic()
    put('progress',dict(phase=state))
def cmd(w,text):
    u.SystemLibrary.execute_console_command(w,text,G.get_player_controller(w,0))
def actors(w,cls):
    return G.get_all_actors_of_class(w,cls)
def doors(w):
    result=[]
    tavern=next(iter(G.get_all_actors_with_tag(w,'VillageTavern.Site')),None)
    if not tavern:return []
    frame=tavern.get_actor_transform()
    for a in actors(w,u.ColdSteelDoor):
        pos=u.MathLibrary.inverse_transform_location(frame,a.get_actor_location())
        if not (-730<pos.x<660 and -440<pos.y<840 and 320<pos.z<690):continue
        if any(c.static_mesh and c.static_mesh.get_name().startswith('SM_InnRoomDoor') for c in a.get_components_by_class(u.StaticMeshComponent)):
            result.append(a)
    return sorted(result,key=lambda a:(round(a.get_actor_location().z),round(a.get_actor_location().x),round(a.get_actor_location().y)))
def seen(c):
    return c.is_visible() and not c.get_editor_property('hidden_in_game')
def snapshot(w,h,t,m):
    mx=m.get_components_by_class(u.StaticMeshComponent)
    west=t.get_components_by_class(u.StaticMeshComponent)
    ds=doors(w)
    return dict(mill=h.is_windmill_repaired(),inn=h.is_tavern_repaired(),
        mill_keeper=len(actors(w,u.VillageMillKeeper)),tavern_keeper=len(actors(w,u.VillageTavernKeeper)),
        doors=len(ds),open_doors=sum(a.is_door_open() for a in ds),
        mill_work_parts=sum(seen(c) for c in mx if c.component_has_tag('VillageWindmill.Restored')),
        grove=sum(seen(c) for c in mx if c.static_mesh and any(s in c.static_mesh.get_name() for s in ('Alder','Beech'))),
        lamps=sum(seen(c) for c in m.get_components_by_class(u.PointLightComponent) if c.component_has_tag('VillageWindmill.Restored')),
        runoff=sum(seen(c) for c in west if c.component_has_tag('VillageTavern.TroughRunoff')),
        runoff_collision=[str(c.get_collision_enabled()) for c in west if c.component_has_tag('VillageTavern.TroughRunoff')])
def tick(dt):
    global next_action,state
    try:
        now=time.monotonic()
        if state=='done':return False
        # The client can load an entry world before joining the real server.
        w=u.find_object(None,'/Game/GameMaps/L_ForestPathVillage.L_ForestPathVillage')
        if not w or 'L_ForestPathVillage' not in w.get_path_name():return True
        if now-began>620 or now-since>170 and state!='start':
            raise RuntimeError('timeout '+state)
        pc=G.get_player_controller(w,0)
        if not pc or not pc.get_controlled_pawn():return True
        h=next(iter(actors(w,u.TemperateHillsWorld)),None)
        if not h or not h.ready:return True
        m=next(iter(actors(w,u.HillsWindmill)),None)
        if not m:return True
        t=next(iter(G.get_all_actors_with_tag(w,'VillageTavern.Site')),None)
        if not t:return True
        if state=='start':
            if role=='host':
                cmd(w,'DisableAllScreenMessages')
            cmd(w,'fps.Test.VillageDelivery ground')
            move('arrival')
        if state=='arrival':
            if role=='host' and not (root/'client/initial.json').exists():return True
            a=snapshot(w,h,t,m)
            if role=='rejoin':
                if not (a['mill'] and a['inn'] and a['mill_keeper']==1 and a['tavern_keeper']==1 and a['doors']==5 and a['open_doors']==1):return True
                put('rejoined',a);cmd(w,'quit');state='done';return False
            if a['mill'] or a['inn']:raise ValueError('fresh fixture already repaired '+str(a))
            put('initial',a)
            if role=='host':
                cmd(w,'fps.Test.VillageDelivery repair')
            move('repair')
        if state=='repair':
            a=snapshot(w,h,t,m)
            put('last-state',a)
            if not (a['mill'] and a['inn'] and a['mill_keeper']==1 and a['tavern_keeper']==1 and a['doors']==5 and a['runoff']==1):return True
            put('repaired',a)
            if role=='host':
                if not (root/'client/repaired.json').exists():return True
                keeper=actors(w,u.VillageMillKeeper)[0]
                guest=next((c for c in actors(w,u.PlayerController) if not c.is_local_controller() and c.get_controlled_pawn()),None)
                if not guest:return True
                # Keep the remote player close enough for the actual conversation RPC.
                pawn=guest.get_controlled_pawn()
                offset=keeper.get_actor_forward_vector()*104
                u.SystemLibrary.execute_console_command(w,'t.MaxFPS 45')
                pawn.set_actor_location(keeper.get_actor_location()+offset,False,True)
                guest.set_control_rotation(u.MathLibrary.find_look_at_rotation(pawn.get_actor_location(),keeper.get_actor_location()))
                for d in doors(w):
                    d.open_door()
                    if d.is_door_open():break
                put('guest-position',dict(distance=pawn.get_distance_to(keeper),opened=sum(a.is_door_open() for a in doors(w))))
            move('door-talk')
        if state=='door-talk':
            if role=='client':
                if not (root/'host/guest-position.json').exists():return True
                if now>=next_action:
                    cmd(w,'fps.Test.VillageDelivery dialogue')
                    if not (folder/'client-dialogue.txt').exists():cmd(w,'fps.Test.VillageDelivery speak')
                    next_action=now+1.
                if not (folder/'client-dialogue.txt').exists() or not any(d.is_door_open() for d in doors(w)):return True
                put('accepted',snapshot(w,h,t,m));cmd(w,'quit');state='done';return False
            elif role=='host' and (root/'rejoin/rejoined.json').exists():
                put('finish',snapshot(w,h,t,m));cmd(w,'quit');state='done';return False
        return True
    except Exception:
        put('error',dict(phase=state,message=traceback.format_exc()));state='done'
        w=u.find_object(None,'/Game/GameMaps/L_ForestPathVillage.L_ForestPathVillage')
        if w:cmd(w,'quit')
        return False
handle=u.register_ticker_callback(tick,.45)
put('boot',dict(pid=os.getpid(),role=role))
