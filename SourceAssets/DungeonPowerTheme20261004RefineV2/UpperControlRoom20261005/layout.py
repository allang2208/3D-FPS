"""Persistent authored layout for the elevated glazed control room (metres)."""
import json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent
BASE='/Game/Dungeons/PowerTheme20261004/UpperControlRoom20261005'

def apply(scene):
    room=next(r for r in scene['rooms'] if r['id']=='AccumulatorControl')
    z=room['upper_deck_m']
    room['control_room']=dict(x_bounds_m=[-8,8],y_bounds_m=[13.3,20],height_m=3.4,
        floor_m=z,balcony_front_m=11.1,platform_half_width_m=10,
        door_center_y_m=17.3,door_clear_width_m=2.3,
        design='Upper open-plan glazed control room with two side entrances and a continuous front balcony')
    room['stairs_angles_deg']=[35,145]
    room['stairs_width_m']=2.4
    moved=[]
    def move(p,position,yaw=0):
        p['position_m']=position;p['yaw_deg']=yaw;moved.append(p['id'])
    for p in room['authored_parts']:
        if p['id'].startswith('MainControlConsole'):
            i=int(p['id'][-2:])-1;move(p,[-4.9+4.9*i,14.75,z],180)
    for p in room['reused_parts']:
        name=p['id']
        if name.startswith('MainControlChair'):
            i=int(name[-2:])-1;move(p,[-4.9+4.9*i,16,z+.0014])
        elif name.startswith('ControlAuxCabinet'):
            side=-1 if name.endswith('_-1') else 1;move(p,[side*7.5,14.95,z],-side*90)
        elif name.startswith(('PPE_03_','PPE_04_')):
            x=-6.8 if name.startswith('PPE_03_') else 6.8
            move(p,[x+(.307 if name.endswith('_Door') else 0),19.58-(.233 if name.endswith('_Door') else 0),z+(.09 if name.endswith('_Door') else 0)],180)
        elif name.startswith('Records_02_'):
            height=0 if name.endswith('Carcass') else [.11,.45,.79][int(name.split('Drawer')[1][0])-1]
            move(p,[-4.4,19.5,z+height],0)
        elif name.startswith('Fixture_ControlRoom'):
            i=int(name[-2:]);move(p,[-5+5*i,16.8,z+3.13]);p['ceiling_m']=z+3.4
        elif name in ('ControlRecordsDesk','ControlRecordsElectronics'):
            target=[-1.2,19.23,z];anchor=p['source_anchor_blender_m']
            move(p,[target[i]-anchor[i] for i in range(3)]);p['target_anchor_m']=target
        elif name.startswith('ControlServerRack'):
            target=[2.2+1.2*(int(name[-2:])-1),19.25,z]
            move(p,target);p['target_anchor_m']=target[:]
    lights=[]
    containers=room.get('scene_containers',[])+[p for p in scene.get('scene_containers',[]) if p.get('room_id')==room['id']]
    for p in containers:
        name=p['id']
        if name in ('PPE_03','PPE_04'):
            p['position_m']=[-6.8 if name=='PPE_03' else 6.8,19.58,z];p['yaw_deg']=180
        elif name.startswith('Records_02_Drawer'):
            p['position_m']=[-4.4,19.5,z+[.11,.45,.79][int(name[-1])-1]];p['yaw_deg']=0
    for p in room['lights']:
        if p['id'].startswith('ControlRoom'):
            i=int(p['id'][-2:]);p['position_m']=[-5+5*i,16.8,z+3]
            p['ceiling_m']=z+3.4;lights.append(p['id'])
    room['upper_control_revision']='UpperControlRoom20261005'
    return dict(room=room['id'],moved_parts=moved,moved_lights=lights)

def interaction_specs(scene):
    room=next(r for r in scene['rooms'] if r['id']=='AccumulatorControl');z=room['upper_deck_m']
    glass=[];doors=[]
    def pane(name,pos,yaw,kind,w):
        glass.append(dict(id=name,position_m=pos,yaw_deg=yaw,kind=kind,width_m=w,height_m=2.00))
    for i,x in enumerate((-6,-2,2,6)):
        pane('UpperControlFrontGlass%02d'%i,[x,13.3,z+1.96],90,'Front',3.92)
    for side in (-1,1):
        pane('UpperControlSideGlass'+str(side),[side*8,14.715,z+1.96],0,'Side',2.735)
        for leaf,y in enumerate((16.7375,17.8625)):
            doors.append(dict(id='UpperControlDoor%s_%s'%(side,leaf),position_m=[side*8,y,z+.015],
                yaw_deg=0,positive_hinge=leaf==0,open_angle_degrees=85,
                leaf_mesh='/Game/Dungeons/StationWorkshop20261003/RefineV2/Meshes/SM_SW_PersonnelLeaf'))
    return dict(glass=glass,doors=doors)

def main():
    p=SOURCE/'Config/scene.json';scene=json.loads(p.read_text('utf8'))
    before=ROOT/'scene-before.json'
    if not before.exists():before.write_text(json.dumps(scene,ensure_ascii=False,indent=2),encoding='utf8')
    changes=apply(scene);p.write_text(json.dumps(scene,ensure_ascii=False,indent=2),encoding='utf8')
    (ROOT/'layout.json').write_text(json.dumps(dict(**changes,interactions=interaction_specs(scene)),indent=2),encoding='utf8')
    print('POWER_UPPER_CONTROL_LAYOUT_WRITTEN')
if __name__=='__main__':main()
