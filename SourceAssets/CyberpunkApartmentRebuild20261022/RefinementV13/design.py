from pathlib import Path
import runpy
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[2]
BASE='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV13'
MAP='/Game/GameMaps/L_CyberpunkApartment';OWNER='CyberpunkApartment.RefinementV13'
OLD12='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV12'
OLD7='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV7'
SUB='/Game/SubstrateMaterials/Textures/'
TV=dict(center=(21.011,-4.08,2.899),width=6.1744,height=3.978,depth=.09)
ROOMS=[
 ('Office',(0.225,-10.125,0),(7.2,-.225,5.53125),False),
 ('Living',(7.425,-10.125,0),(21.15,-.225,5.53125),False),
 ('Bed2',(21.375,-10.125,0),(29.775,-.225,5.53125),False),
 ('Bed3',(21.375,-20.4,0),(29.775,-10.35,5.53125),False),
 ('Kitchen',(9.,-20.4,0),(16.2,-12.825,5.53125),False),
 ('Foyer',(16.425,-20.4,0),(21.15,-12.825,5.53125),True),
 ('Corridor',(.225,-12.60,0),(21.15,-10.35,5.53125),True),
 ('Laundry',(.225,-15.15,0),(5.1,-12.825,5.53125),False),
 ('Service',(5.325,-15.15,0),(8.775,-12.825,5.53125),True),
 ('Gym',(-5.05,-22.9125,0),(5.1,-15.25,5.53125),False),
 ('Bath',(5.325,-22.9125,0),(8.775,-15.375,5.53125),False),
 ('Balcony',(7.2,.02,0),(21.5,5.4,5.6),False),
 ('Landing',(16.05,-24.9,0),(21.15,-20.625,5.53125),True),
]
DOOR_ROOMS={'Entry':(5,12),'Master':(0,6),'Bed2':(1,2),'Bed3':(5,3),'Bath1':(8,10),'Bath2':(7,9),'Balcony':(1,11)}
OPEN_PORTALS=[(1,6,(15.18,-10.2375,1.9)),(6,7,(3.09,-12.7125,1.9)),(6,8,(7.56,-12.7125,1.9)),(6,4,(12.375,-12.7125,1.9)),(6,5,(18.6,-12.7125,1.9))]
LIGHT_ROOM={'Master':0,'Living':1,'Bed2':2,'Bed3':3,'Kitchen':4,'Foyer':5,'Corridor':6,'Laundry':7,'Service':8,'Bath2':9,'Balcony':11,'Landing':12}
LIGHTS=runpy.run_path(str(ROOT.parent/'RefinementV12/design.py'))['LIGHTS']
REUSE={'Graphite':OLD12+'/Materials/M_AP12_Graphite','Steel':OLD12+'/Materials/M_AP12_Steel',
       'Acoustic':OLD7+'/Materials/M_AP7_Leather','Rubber':OLD7+'/Materials/M_AP7_Plastic'}
DEVICES=[
 dict(key='TV',station='AP_Living_TV',label='海湾资讯屏',world=(20.94,-6.82,.76),yaw=-90.,radius=1500.,workout=False),
 dict(key='Office',station='AP_Office_Workstation',label='办公室终端',offset=(.78,.24,.86),radius=500.,workout=False),
 dict(key='Bed2',station='AP_Bed2_Desk',label='卧室终端 01',offset=(.59,.24,.86),radius=450.,workout=False),
 dict(key='Bed3',station='AP_Bed3_Desk',label='卧室终端 02',offset=(.59,.24,.86),radius=450.,workout=False),
 dict(key='Treadmill',station='AP_Gym_Treadmill',label='跑步机',offset=(.278,-.373,1.19),scale=.55,radius=270.,workout=True),
 dict(key='Rower',station='AP_Gym_Rower',label='划船机',offset=(0,-.033,.59),scale=.65,radius=260.,workout=True),
]
