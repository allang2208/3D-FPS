# 全村制作脚本中的三店接入点

三店的独立保存脚本更新已有村庄子关卡。使用全村作者工程重建时，按下列原始代码段接回建筑、采光体积、工作区和道路预留。相邻房屋分支只作为定位上下文。

## Tools/WorldGeneration/AbandonedVillage/author_village.py

Lines 13–20

```python
sys.path.insert(0, str(root/'Tools/WorldGeneration/AbandonedVillage'))
sys.path.insert(0, str(root/'Tools/WorldGeneration/VillageBlacksmith'))
sys.path.insert(0, str(root/'Tools/WorldGeneration/VillageCarpenter'))
sys.path.insert(0, str(root/'Tools/WorldGeneration/VillageHerbalist'))
from author_shop import build_shop, furnish_home
from carpenter_shop import build_workshop, vision_room as carpenter_vision_room
from author_shop03 import build_herbalist, is_stateful_shell, set_herbalist_daylight
from layout_geometry import plot_geometry
```

Lines 74–79

```python
    if mesh.startswith('SM_H_RubblePile_'):
        # Preserve the deterministic draw order while reserving the working yard.
        for area in plan.get('service_clearings',[]):
            if area.get('owner')=='Carpenter04':
                lx,ly=rotate(x-area['center'][0],y-area['center'][1],-area['yaw'])
                if abs(lx)<area['half'][0]+.5 and abs(ly)<area['half'][1]+.5:return
```

Lines 83–118

```python
footprints=[]
house_scale=plan.get('house_scale',1.)
vision_rooms=[]
interior_receipt=[]
for house in plan['houses']:
    num,label,model,x,y,yaw=house
    pieces=kit[model]
    geometry=plot_geometry(house,pieces,plan)
    base=u.Transform(location=[x*100,y*100,4-geometry['floor']*house_scale],
                     rotation=u.Rotator(yaw=yaw),scale=[house_scale]*3)
    smith=num==plan.get('blacksmith',{}).get('house')
    carpenter=num==plan.get('carpenter',{}).get('house')
    tavern=num==plan.get('tavern',{}).get('house')
    herbalist=num==plan.get('herbalist',{}).get('house')
    if smith:
        interior_receipt.append(build_shop(house,pieces,base,geometry))
    elif carpenter:
        interior_receipt.append(build_workshop(house))
    elif tavern:
        interior_receipt.append(build_tavern(house,pieces,plan,geometry))
    elif herbalist:
        interior_receipt.append(build_herbalist(house,pieces,base))
    else:
        interior_receipt.append(furnish_home(house,pieces,geometry,house_scale,group))
    for p in ([] if smith or carpenter or tavern else pieces):
        # Leave the source doorways open. The fixed, closed meshes have no interactive hinge.
        if p['mesh'].endswith('.SM_Door_00A'):continue
        if herbalist and is_stateful_shell(p):continue
        pitch,angle,roll=p['rot']
        if 'SM_Window_Shutter_00A' in p['mesh']:
            angle+=55
        elif 'SM_Window_Shutter_01A' in p['mesh']:
            angle-=55
        piece=u.Transform(location=p['pos'],rotation=u.Rotator(pitch=pitch,yaw=angle,roll=roll),scale=p['scale'])
        group(p['mesh'],u.MathLibrary.compose_transforms(piece,base),p['materials'],p['profile'])
    vision_rooms.append((num,label,base,geometry,model))
```

Lines 310–328

```python
for num,label,transform,geometry,model in vision_rooms:
    room=actors.spawn_actor_from_class(u.BuildingDaylight,transform.translation,transform.rotation.rotator())
    if num==plan.get('tavern',{}).get('house'):
        set_tavern_vision(room, next(h for h in plan['houses'] if h[0]==num),geometry,plan)
        continue
    if num==plan.get('carpenter',{}).get('house'):
        carpenter_vision_room(room,next(h for h in plan['houses'] if h[0]==num))
        continue
    room.set_actor_label('Village_InteriorVision_'+num+'_'+label)
    room.set_actor_transform(transform,False,False)
    room.set_editor_property('room_minimum',u.Vector(*geometry['room_min']))
    room.set_editor_property('room_maximum',u.Vector(*geometry['room_max']))
    ruined='RuinedHouse' in model
    smith_loft=model=='SL_Blacksmith_LoftR3'
    room.set_editor_property('additional_dark_adaptation_stops',3.25 if smith_loft else (1.0 if ruined else 2.25))
    room.set_editor_property('exposure_compensation',.8 if smith_loft else (.2 if ruined else .6))
    room.set_editor_property('entrance_transition_cm',120.)
    if num==plan.get('herbalist',{}).get('house'):
        set_herbalist_daylight(room)
```

## Tools/WorldGeneration/AbandonedVillage/draw_plan.py

Lines 31–40

```python
houses=[]
house_shapes={}
for house in plan['houses']:
    num,name,model,x,y,angle=house
    parts=kit[model]
    geometry=plot_geometry(house,parts,plan)
    house_shapes[num]=geometry
    entry,step=geometry['entry'],geometry['step']
    roads.append(approach_path(house,geometry,plan,streets))
    houses.append((num,name,model,x,y,angle,entry))
```

Lines 54–63

```python
header.extend(['};','struct FBox { double X,Y,HalfX,HalfY,Cos,Sin; };','inline constexpr FBox Beds[] = {'])
for num,_,model,x0,y0,a,_ in houses:
    shape=house_shapes[num]
    header.append(row(shape['center'][0]*100,shape['center'][1]*100,shape['half'][0]*100,shape['half'][1]*100,
                      math.cos(math.radians(a)),math.sin(math.radians(a))))
for x0,y0,rx,ry in plan['meadows']+[plan['square']]:
    header.append(row(x0*100,y0*100,rx*100,ry*100,1,0))
for service in plan.get('service_clearings',[]):
    a=math.radians(service['yaw'])
    header.append(row(*[v*100 for v in service['center']],*[v*100 for v in service['half']],math.cos(a),math.sin(a)))
```
