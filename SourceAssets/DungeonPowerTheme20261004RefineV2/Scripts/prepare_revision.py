"""Apply the requested station-scale revision to the authored base contract.

Run after prepare_design and layout_reuse, before author_scene. No UE mutation.
"""
import json, math
from pathlib import Path

R=Path(__file__).resolve().parents[1]
P=R/'Config/scene.json'
c=json.loads(P.read_text('utf8'))
base='/Game/Dungeons/PowerTheme20261004/RefineV2'
c.update(revision='power_theme_refine_v2_20261004',ue_base=base,
         sample_map='/Game/GameMaps/Design/L_PowerTheme20261004_Subject',
         name='失效供能中心 · 圆形总控扩建',prototype_ids=['GeneratorPrototype','StoragePrototype','ConsolePrototype'])
c['revision_reference']=dict(source='StationExpansion20260929/Config/room.json',
    source_version='station_expansion_20260929',main_hall_m=[48,33,11.7],
    equivalent_circle_diameter_m=2*math.sqrt(48*33/math.pi),chosen_clear_diameter_m=45,
    note='45m circle chosen from the final station main-hall area; full module including tunnels is not used as hall size.')
c['lighting_budget']=dict(max_total_lights=32,max_shadowed_lights=8,max_shadowed_per_section=3)
c['stairs']['circular_hall_width_cm']=200
for room in c['rooms']:
    for p in room.get('authored_parts',[]):
        p['mesh']=p['mesh'].replace('/Game/Dungeons/PowerTheme20261004/',base+'/')
r1,r2,r3=c['rooms']
# The precision console is a theme-only new prototype. The two nearest column
# webs are at x=-5.25 and 0; the envelope stops 1.04m from either column flange.
r2['reused_parts']=[p for p in r2['reused_parts'] if p['id']!='GeneratorDispatch']
for p in r2['reused_parts']:
    if p['id']=='DispatchChair':p['position_m']=[-2.60,8.93,2.4014]
r2['authored_parts'].append(dict(id='GeneratorDispatchRefined',mesh=base+'/Meshes/SM_Power_ControlConsole_Refined',position_m=[-2.60,10.04,2.4],yaw_deg=0,collision=True))
r2['console_clearance']=dict(position_m=[-2.60,10.04,2.4],max_width_m=2.76,max_depth_m=1.02,
    column_centres_x_m=[-5.25,0],column_half_width_m=.21,
    minimum_horizontal_column_clearance_m=1.01,rear_wall_inner_y_m=10.85,rear_console_y_m=10.55)

radius=22.5;height=11.7;deck=3.84;port=math.sqrt(radius*radius-1.75*1.75)
front=radius-6.2;back=math.sqrt((radius-.55)**2-8.0**2)
r3.update(name='03 圆形蓄能总控大厅',origin_m=[47+port,0,0],dimensions_m=[45,45,height],
    radius_m=radius,upper_deck_m=deck,upper_annulus_m=[radius-4.8,radius-.48],
    control_room=dict(x_bounds_m=[-8,8],y_bounds_m=[front,back],height_m=3.34),
    ports=[dict(id='Entry',position=[-port,0,0],normal=[-1,0,0],width=3,height=2.8),
           dict(id='Exit',position=[port,0,0],normal=[1,0,0],width=3,height=2.8)],
    design='参照车站最终48×33米主厅面积，45米直径圆形大厅、11.7米净高；3.84米完整环形二层、双200厘米径向楼梯；中央7.4米直径精细蓄能核心；北缘封闭主控制室、多台控制设备与设备架。')
r3['cells_m']=[]
y=-radius-.25
while y<radius+.25-1e-8:
    hi=min(radius+.25,y+1)
    near=0 if y<=0<=hi else min(abs(y),abs(hi))
    half=math.sqrt(max(0,(radius+.25)**2-near**2))
    r3['cells_m'].append(dict(min=[-half,y,-.34],max=[half,hi,height+.36]));y=hi
r3['walk_mask_m']=[dict(min=[-port+.5,-2.1,0],max=[-5,2.1,2.8]),
    dict(min=[5,-2.1,0],max=[port-.5,2.1,2.8]),
    dict(min=[-13,-10,0],max=[13,-5,2.8]),
    dict(min=[-7.7,front+.3,0],max=[7.7,back-.3,2.8])]
r3['encounter_anchors_m']=[[-12,0,0],[12,0,0],[0,-12,0],[-9,9,0],[9,9,0],[0,20,deck]]
r3['authored_parts']=[dict(id='FlywheelCoreRefined',mesh=base+'/Meshes/SM_Power_Accumulator',position_m=[0,0,.20],yaw_deg=0,collision=True)]
for i,x in enumerate((-4.8,0,4.8),1):
    r3['authored_parts'].append(dict(id='MainControlConsole%02d'%i,mesh=base+'/Meshes/SM_Power_ControlConsole_Refined',position_m=[x,back-.69,0],yaw_deg=0,collision=True))
assets={a['id']:a for a in c['existing_assets']}
r3['reused_parts']=[];r3['scene_containers']=[]

def add(id,name,p,yaw=0,**kw):
    row=dict(id=id,source_asset_id=name,mesh=assets[name]['mesh'],position_m=p,yaw_deg=yaw,collision=True,cast_shadow=True);row.update(kw)
    r3['reused_parts'].append(row);return row

for i,x in enumerate((-4.8,0,4.8),1):
    add('MainControlChair%02d'%i,'SM_Staff_Chair',[x,back-1.84,.0014],180)
for deg in (10,170,190,350):
    a=math.radians(deg);add('RingSwitchgear_%03d'%deg,'SM_Facility_PowerCabinet',[(radius-1.35)*math.cos(a),(radius-1.35)*math.sin(a),0],deg-90)
for side in (-1,1):
    add('ControlAuxCabinet_'+str(side),'SM_Facility_PowerCabinet',[side*7.29,front+1.25,0],-side*90)
add('ControlRecordsDesk','SM_Staff_Desk',[0,front+1.02,0],180)
add('ControlRecordsChair','SM_Staff_Chair',[0,front+1.99,.0014])

# Keep original working searchable assemblies; exact pivots and component
# pairing are taken from the already-authored base layout before replacing it.
original=json.loads((R/'References/ReuseBundle/HANDOFF.json').read_text())
orig={a['name']:a for a in original['assets']}
def turn(p,a):
    a=math.radians(a);return [p[0]*math.cos(a)-p[1]*math.sin(a),p[0]*math.sin(a)+p[1]*math.cos(a),p[2]]
for i,(x,y,yaw) in enumerate([(-6.65,front+3.10,0),(6.65,front+3.10,0)],3):
    id='PPE_%02d'%i;p=[x,y,0]
    add(id+'_Body','SM_Treatment_PPELocker_Body',p,yaw,container_id=id)
    h=turn(orig['SM_Treatment_PPELocker_Door']['pivot_blender_m'],yaw)
    add(id+'_Door','SM_Treatment_PPELocker_Door',[p[k]+h[k] for k in range(3)],yaw,container_id=id)
    r3['scene_containers'].append(dict(id=id,prototype='PPELocker',position_m=p,yaw_deg=yaw,caption='总控室防护用品柜',source_assembly='References/ReuseBundle/SourceAssets/IncineratorContainers20261003/Config/assemblies.json',rewards_deferred=True))
p=[-3.25,front+.64,0];yaw=180
add('Records_02_Carcass','SM_Treatment_RecordsCabinet_Carcass',p,yaw)
for i,z in enumerate((.11,.45,.79)):
    q=[p[0],p[1],z];id='Records_02_Drawer'+str(i+1)
    for name in ('Frame','Tray'):add(id+'_'+name,'SM_Treatment_RecordsDrawer_'+name,q,yaw,container_id=id)
    r3['scene_containers'].append(dict(id=id,prototype='RecordsDrawer',position_m=q,yaw_deg=yaw,caption='总控室检修记录 '+str(i+1),source_assembly='References/ReuseBundle/SourceAssets/IncineratorContainers20261003/Config/assemblies.json',rewards_deferred=True))

# Reuse unscaled 4.03m original chipped ceramic groups on chord backing panels.
# Each is rotated as a rigid unit, never bent/scaled around the circular room.
r3['tile_panel_angles_deg']=[15,40,140,165,190,215,240,265,290,315,340]
for i,deg in enumerate(r3['tile_panel_angles_deg']):
    a=math.radians(deg);n=(-math.cos(a),-math.sin(a));t=(math.sin(a),-math.cos(a))
    p=[radius*math.cos(a)+n[0]*(.31-.12021)-t[0]*2.015,
       radius*math.sin(a)+n[1]*(.31-.12021)-t[1]*2.015,0]
    add('OriginalCircularDado_%02d'%i,'SM_TileFracture_EntryEnd',p,deg+180,collision=False,cast_shadow=False)

def light(id,p,lm,rad,shadow=False,tint=(.74,.83,.86),role='path',ceiling=None):
    row=dict(id=id,position_m=p,lumens=lm,radius_cm=rad,cast_shadows=shadow,tint=list(tint),role=role,indirect=.7,max_draw_distance_cm=5400,fade_range_cm=700)
    if ceiling is not None:row['ceiling_m']=ceiling
    return row
r3['lights']=[light('CoreCrown',[0,0,10.35],3800,2100,True)]
for i in range(8):
    a=(i+.5)*math.tau/8
    r3['lights'].append(light('HallSector%02d'%i,[12.1*math.cos(a),12.1*math.sin(a),7.7],1800,1350,i in (0,4)))
for i in range(4):
    a=(i+.5)*math.tau/4
    r3['lights'].append(light('UpperRing%02d'%i,[19.8*math.cos(a),19.8*math.sin(a),7.0],950,1050))
for i,x in enumerate((-5,0,5)):
    r3['lights'].append(light('ControlRoom%02d'%i,[x,(front+back)/2,2.94],700,520,False,(.88,.90,.78),'control',3.34))
for l in r3['lights']:
    p=l['position_m'];add('Fixture_'+l['id'],'SM_Staff_LampFixture',[p[0],p[1],p[2]+.13],0,collision=False,cast_shadow=False,ceiling_m=l.get('ceiling_m',height))
c['connectors'][1]['origin_m']=[44,0,0]
for link in c['connectors']:
    link['dimensions_m']=[6,3.12,3.2]
    link['cells_m']=[dict(min=[-3,-1.91,-.3],max=[3,1.91,3.5])]
    link['door_overlap_fix']='60mm recessed corridor lining; 200mm end setback; noncoplanar stepped backing. Jamb inner faces exclusively own ±1.500m.'
# All reused visible English label faces are replaced per component within the
# new theme, including the moving door/tray components of native containers.
labels=base+'/Materials/M_Power_ContainerLabels'
affected={'SM_Treatment_PPELocker_Door','SM_Treatment_RecordsDrawer_Tray'}
overrides={}
for name in affected:
    overrides[name]=[labels if k=='RS_Labels' else v for k,v in orig[name]['materials'].items()]
for room in c['rooms']:
    for part in room['reused_parts']:
        if part['source_asset_id'] in affected:part['materials']=overrides[part['source_asset_id']]
    for item in room.get('scene_containers',[]):
        key='SM_Treatment_PPELocker_Door' if item['prototype']=='PPELocker' else 'SM_Treatment_RecordsDrawer_Tray'
        item['door_materials']=overrides[key]
c['required_material_roles']=['ContainerLabels','CabinetChinese','ServerChinese']
for room in c['rooms']:
    for part in room['reused_parts']:
        if part['source_asset_id']=='SM_Facility_PowerCabinet':part['materials']=[base+'/Materials/M_Power_CabinetChinese']
mp=R/'Config/materials.json';m=json.loads(mp.read_text('utf8'))
m['ContainerLabels']=dict(basecolor_linear=[.60,.57,.46],roughness=.70,metallic=0,uv_meters=1,new_authored=True,
    textures={'basecolor':'Authored/Textures/T_Power_ContainerLabels_BaseColor.png'})
m['CabinetChinese']=dict(basecolor_linear=[1,1,1],roughness=.7,metallic=0,uv_meters=1,new_authored=True,
    textures={'basecolor':'Authored/Textures/T_Power_CabinetSource_BaseColor.png',
              'normal':{'path':'Authored/Textures/T_Power_CabinetSource_NormalGL.png','normal_convention':'OpenGL'},
              'orm':'Authored/Textures/T_Power_CabinetSource_ORM.png',
              'labeloverlay':'Authored/Textures/T_Power_CabinetChinese_Overlay.png'},
    provenance='Original FacilityProp PBR copied unchanged; Chinese plate artwork is a separate alpha overlay. Shared UE material untouched.')
m['ServerChinese']=dict(basecolor_linear=[1,1,1],roughness=.7,metallic=0,uv_meters=1,new_authored=True,
    textures={'basecolor':'Authored/Textures/T_Power_ServerSource_BaseColor.png',
              'normal':{'path':'Authored/Textures/T_Power_ServerSource_NormalDX.png','normal_convention':'DirectX'},
              'orm':'Authored/Textures/T_Power_ServerSource_ORM.png',
              'labeloverlay':'Authored/Textures/T_Power_ServerChinese_Overlay.png'},
    provenance='Original DataArchive EquipmentV1 PBR copied unchanged; Chinese labels use separate alpha artwork. Shared mesh and UE material untouched.')
for name,rough,emission in [('WorkshopPrintCN',.86,0),('WorkshopScreenCN',.29,.3)]:
    m[name]=dict(basecolor_linear=[1,1,1],roughness=rough,metallic=0,uv_meters=1,new_authored=True,
        textures={'basecolor':'Authored/Textures/T_Power_WorkshopSource_BaseColor.png','labeloverlay':'Authored/Textures/T_Power_WorkshopChinese_Overlay.png'},
        provenance='Original Workshop PrintAtlas unchanged. Theme-only Chinese alpha artwork. Original shader roughness/emission preserved.')
    if emission:m[name].update(emissive_strength=emission,emissive_from_basecolor=True)
mp.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf8')
P.write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf8')
print('POWER_REVISION_CONFIG_AUTHORED',c['revision'],r3['origin_m'],sum(len(r['lights']) for r in c['rooms']+c['connectors']))
