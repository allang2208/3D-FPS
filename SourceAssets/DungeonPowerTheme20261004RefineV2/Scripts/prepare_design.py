"""Author dimensional scene contract, new material identities and original sign atlas.
No user project mutation, no UE import and no test/render execution.
"""
import json, math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];C=ROOT/'Config';A=ROOT/'Authored';T=A/'Textures'
for p in (C,A,T):p.mkdir(parents=True,exist_ok=True)
def cell(a,b):return {'min':a,'max':b}
def port(s,x):return dict(id='Entry' if s<0 else 'Exit',position=[x,0,0],normal=[s,0,0],width=3.0,height=2.8)
def light(id,p,lm,r,shadow=False,tint=(.74,.83,.86),role='path'):
 return dict(id=id,position_m=p,lumens=lm,radius_cm=r,cast_shadows=shadow,tint=list(tint),role=role,indirect=.7,max_draw_distance_cm=3400,fade_range_cm=500)
rooms=[dict(id='SwitchgearGallery',name='01 配电检修廊',origin_m=[0,0,0],dimensions_m=[18,16,4.8],
 cells_m=[cell([-9.2,-8.2,-.3],[9.2,8.2,5.1]),cell([-3.2,8.2,-.3],[3.2,11.2,3.9])],
 ports=[port(-1,-9),port(1,9)],walk_mask_m=[cell([-8.5,-2.1,0],[8.5,2.1,2.6]),cell([-2.6,2.1,0],[2.6,10.4,2.6])],
 encounter_anchors_m=[[-5,0,0],[0,1.7,0],[5,0,0],[-4,-3.5,0],[4,3.4,0]],
 design='低顶贯通主道；两侧复用配电柜；北侧独立检修/值班凹室；地面电缆沟保留连续承托面。',
 lights=[light('Entry',[-7.4,0,3.7],450,470,False,(1,.81,.58)),light('AisleWest',[-4,0,4.0],950,760,True),light('AisleEast',[4,0,4.0],950,760),light('ServiceNook',[0,9.1,3.1],380,380,False,(1,.81,.59))],
 reused_parts=[],authored_parts=[]),
 dict(id='GeneratorHall',name='02 双机发电大厅',origin_m=[28,0,0],dimensions_m=[26,22,9.0],
 cells_m=[cell([-13.2,-11.2,-.3],[13.2,11.2,9.4])],ports=[port(-1,-13),port(1,13)],
 walk_mask_m=[cell([-12.6,-1.9,0],[12.6,1.9,2.8]),cell([-12.4,-9.7,0],[-6,-1.9,2.8]),cell([6,-9.7,0],[12.4,-1.9,2.8]),cell([-9.4,7.65,2.4],[9.4,10.25,4.7])],
 encounter_anchors_m=[[-8,0,0],[0,0,0],[8,0,0],[-8,-7.2,0],[7,-7.2,0],[0,8.9,2.4]],
 design='九米高浅拱屋面；双机沿主道两侧布置；北侧2.4米检修高台由双180厘米宽楼梯连接；主路两端门洞均平层。',
 lights=[light('West',[-8,0,5.8],1500,1100,True),light('East',[8,0,5.8],1500,1100),light('MachineA',[0,-4.3,6.6],1800,1200,True),light('MachineB',[0,4.3,6.6],1700,1200),light('Gallery',[0,9.2,5.1],780,840),light('WestStair',[-10.65,5,5.1],350,520,False,(1,.81,.58)),light('EastStair',[10.65,5,5.1],350,520,False,(1,.81,.58))],
 reused_parts=[],authored_parts=[dict(id='GeneratorA',mesh='/Game/Dungeons/PowerTheme20261004/Meshes/SM_Power_Generator',position_m=[0,-4.25,.28],yaw_deg=0,collision=True),dict(id='GeneratorB',mesh='/Game/Dungeons/PowerTheme20261004/Meshes/SM_Power_Generator',position_m=[0,4.25,.28],yaw_deg=180,collision=True)]),
 dict(id='AccumulatorControl',name='03 八角蓄能调控厅',origin_m=[58,0,0],dimensions_m=[22,22,7.2],
 cells_m=[cell([-11.2,-6.2,-.3],[11.2,6.2,7.6]),cell([-9.2,6.2,-.3],[9.2,8.2,7.6]),cell([-7.2,8.2,-.3],[7.2,11.2,7.6]),cell([-9.2,-8.2,-.3],[9.2,-6.2,7.6]),cell([-7.2,-11.2,-.3],[7.2,-8.2,7.6])],
 ports=[port(-1,-11),port(1,11)],walk_mask_m=[cell([-10.5,-2,0],[-3.2,2,2.8]),cell([3.2,-2,0],[10.5,2,2.8]),cell([-6,-6,0],[6,-3.2,2.8]),cell([-5.7,7.1,1.92],[5.7,9.7,4.1])],
 encounter_anchors_m=[[-7,0,0],[7,0,0],[-4,-4.5,0],[4,-4.5,0],[0,-7,0],[0,8.4,1.92]],
 design='真正八角房壳；实体蓄能飞轮核心形成环绕交火；北侧1.92米实心控制高台，双楼梯并可翻越栏杆；档案控制台与储物柜复用。',
 lights=[light('Core',[0,0,6.4],2100,1300,True),light('South',[0,-7.3,4.8],1100,900),light('West',[-7,0,4.8],850,820),light('East',[7,0,4.8],850,820),light('ControlGallery',[0,8.3,5.2],950,800,False,(.82,.86,.80)),light('CoreAccent',[0,-2.8,2.6],240,370,False,(1,.71,.39),'accent')],
 reused_parts=[],authored_parts=[dict(id='FlywheelCore',mesh='/Game/Dungeons/PowerTheme20261004/Meshes/SM_Power_Accumulator',position_m=[0,0,.18],yaw_deg=0,collision=True)])]
# Conservative one-metre strips cover the real chamfered octagon plus wall thickness.
bands=[]
y=-11.2
while y < 11.2-1e-7:
 hi=min(11.2,y+1.0);nearest=0 if y<=0<=hi else min(abs(y),abs(hi));half=min(11.2,17.4-nearest)
 bands.append(cell([-half,y,-.3],[half,hi,7.6]));y=hi
rooms[2]['cells_m']=bands
# Exact reusable-asset placements are completed only after local export metadata arrives.
connectors=[dict(id='Link01',origin_m=[12,0,0],dimensions_m=[6,3,3.2],cells_m=[cell([-3,-1.85,-.3],[3,1.85,3.5])],lights=[light('Service',[0,0,2.95],240,370,False,(1,.81,.58))]),dict(id='Link02',origin_m=[44,0,0],dimensions_m=[6,3,3.2],cells_m=[cell([-3,-1.85,-.3],[3,1.85,3.5])],lights=[light('Service',[0,0,2.95],240,370,False,(1,.81,.58))])]
scene=dict(id='FailedPowerCenter',name='失效供能中心 · 三连房',revision='power_theme_subject_r1_20261004',phase='subject_pending_user_review',ue_base='/Game/Dungeons/PowerTheme20261004',sample_map='/Game/GameMaps/Design/L_PowerTheme20261004_Subject',return_map='/Game/GameMaps/DayNight_Lighting',source_units='metres',unreal_coordinate_conversion='[100*x,-100*y,100*z]',rooms=rooms,connectors=connectors,player_start_m=[-7.5,0,1.02],player_yaw_deg=0,prototype_ids=['GeneratorPrototype','StoragePrototype'],sequence=[r['id'] for r in rooms],port_contract_cm=[300,280],stairs=dict(rise_cm=16,tread_cm=36,width_cm=180),rail_height_cm=108,tests_run=False,rendered=False,ue_imported=False,random_pool_registered=False,geometry_reuse_stage='awaiting_portable_local_asset_bundle',postprocess=dict(exposure_ev=.7,exposure_bias=-.05,indirect_intensity=.75,vignette=.25,bloom=.18),encounters_enabled=False,preview_port_caps=True,notes=['No altar menu, default map or MapsToCook changes.','No production room pool activation before user approval.','Encounter anchors are authoring data only, not spawned enemies.','Bounded stand-alone lighting; generator scheduler only on later accepted runtime integration.'])
(C/'scene.json').write_text(json.dumps(scene,ensure_ascii=False,indent=2),encoding='utf-8')
base='/Game/Dungeons/SeamMetal20260923/Materials/'
def material(color,rough,metal=0,existing=None,**kw):
 r=dict(basecolor_linear=color,roughness=rough,metallic=metal,uv_meters=1.0,**kw)
 if existing:r['existing_ue_path']=existing;r['required_existing']=True
 return r
mats={
 'Concrete':material([.29,.28,.25],.85,existing='/Game/Dungeons/WallUpgrade20260924/Materials/MI_WallConcrete',uv_meters_override=2),
 'Floor':material([.22,.23,.21],.82,existing='/Game/Dungeons/WallUpgrade20260924/Materials/MI_WallConcrete'),
 'Paint':material([.13,.17,.125],.53,.04,base+'MI_PaintedSteel'),
 'Steel':material([.24,.265,.27],.39,.92,base+'MI_BareSteel'),
 'Enamel':material([.17,.205,.145],.50,.03,base+'MI_PipeEnamel'),
 'Deck':material([.16,.18,.17],.53,.86,base+'MI_BridgeDeck'),
 'Yellow':material([.50,.31,.055],.56,.03,base+'MI_Room_YellowPaint'),
 'Rubber':material([.018,.021,.019],.88,existing='/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_Rubber'),
 'Copper':material([.50,.23,.105],.40,.9),
 'Ceramic':material([.72,.70,.58],.30,.02),
 'Red':material([.24,.035,.026],.68,.06),
 'Dark':material([.029,.035,.031],.80,.35),
 'Labels':material([.60,.57,.46],.70,.0,textures={'basecolor':'Authored/Textures/T_Power_Labels_BaseColor.png'}),
}
for role in ('Copper','Ceramic','Red','Dark','Labels'):mats[role]['new_authored']=True
(C/'materials.json').write_text(json.dumps(mats,ensure_ascii=False,indent=2),encoding='utf-8')
# Every rebuild writes the Chinese production atlas, never old English artwork.
import runpy
runpy.run_path(str(ROOT/'Scripts/prepare_chinese_signs.py'),run_name='__main__')
print('POWER_DESIGN_AUTHORED',len(rooms),'rooms',len(connectors),'connectors')
