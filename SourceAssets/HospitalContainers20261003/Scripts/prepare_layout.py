"""Author wall bays, table placements, bedside rules, and undistorted labels."""
import copy
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
BASE='/Game/Dungeons/HospitalContainers20261003'
for folder in ('Config','Receipts','Backup'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
manifest=json.loads((ROOT/'Authored/manifest.json').read_text('utf8'))
prototypes=manifest['prototypes']
staff=json.loads((PROJECT/'SourceAssets/DungeonStaffLiving20261002/Production20261002/Config/modules.json').read_text('utf8'))


def spec(key,position,yaw,identity):
    value=copy.deepcopy(prototypes[key]);value.pop('dimensions_m',None)
    value.update(type='scene_container',container_id='Hospital.'+identity,position=position,yaw=yaw,
                 body=BASE+'/Meshes/'+value['body'],door=BASE+'/Meshes/'+value['door'])
    return value


def slot(identity,key,position,yaw,jitter=0):
    variants=[]
    for offset in ((-jitter,0,jitter) if jitter else (0,)):
        at=list(position)
        # Parallel to the wall only. Facing and distance from wall stay fixed.
        at[1 if yaw in (90,-90) else 0]+=offset
        variants.append(dict(containers=[spec(key,at,yaw,identity)]))
    return dict(id='Hospital.'+identity,variants=variants)


cart_slots=[slot('Ward.Cart.'+identity,'MedicalCart',p,yaw,10)
    for identity,p,yaw in [('N01',[-1800,-1190,4.4],180),('N02',[950,-1190,4.4],180),
                         ('N03',[2750,-1190,4.4],180),('S01',[-2800,1190,4.4],0),('S02',[760,1190,4.4],0)]]
# Include the maximum drawer extension in the reservation for every possible bay.
cart_reserves=[]
for item in cart_slots:
    c=item['variants'][1]['containers'][0];x,y,z=c['position']
    cart_reserves.append(dict(min=[x-47,y-(40 if c['yaw']==180 else 72),z-.2],
                              max=[x+47,y+(72 if c['yaw']==180 else 40),z+112]))

groups={
 'Drainage':[
    dict(id='Hospital.Drainage.ToolBays',pick_count=[2,2],slots=[
        slot('Drainage.Tools.Entry','ToolBox',[-535,-340,.3],90,12),
        slot('Drainage.Tools.Service','ToolBox',[-510,-1880,.3],90,12)])],
 'AbandonedIsolationWard':[
    dict(id='Hospital.Ward.MedicalCarts',pick_count=[5,5],slots=cart_slots),
    dict(id='Hospital.Ward.Emergency',pick_count=[1,1],slots=[
        slot('Ward.Emergency.West','FirstAid',[-2800,-419,132],180),
        slot('Ward.Emergency.East','FirstAid',[2830,-419,132],180)])],
 'AbandonedAnatomyTheatre':[
    dict(id='Hospital.Theatre.Cart',pick_count=[1,1],slots=[
        slot('Theatre.Cart','MedicalCart',[330,1155,.3],0,8)]),
    dict(id='Hospital.Theatre.Instruments',pick_count=[1,2],slots=[
        slot('Theatre.Instruments.A','InstrumentBox',[590,1045,93],0),
        slot('Theatre.Instruments.B','InstrumentBox',[590,1150,93],0)]),
    dict(id='Hospital.Theatre.Specimens',pick_count=[1,1],slots=[
        slot('Theatre.Specimens','SpecimenCase',[680,1150,.3],0)])]}

# The raised gallery's floor is +216 cm. Furniture faces inward along the arc,
# leaving both the rear of the last seating tier and every stair route clear.
gallery_slots=[]
for identity,key,angle in [('West','MedicalCart',38),('NorthWest','PatientBox',65),
                           ('NorthEast','ToolBox',116),('East','SpecimenCase',146)]:
    variants=[]
    for delta in (-1.5,0,1.5):
        a=math.radians(angle+delta)
        variants.append(dict(containers=[spec(key,[1330*math.cos(a),200-1330*math.sin(a),216.3],
            -angle-delta-90,'Theatre.Gallery.'+identity)]))
    gallery_slots.append(dict(id='Hospital.Theatre.Gallery.'+identity,variants=variants))
groups['AbandonedAnatomyTheatre'].append(dict(id='Hospital.Theatre.Gallery',pick_count=[2,3],slots=gallery_slots))
patient=prototypes['PatientBox']
bedside=dict(body=BASE+'/Meshes/'+patient['body'],door=BASE+'/Meshes/'+patient['door'],
             hinge=patient['hinge'],opened_roll=patient['opened_roll'],caption=patient['caption'],
             container_id_prefix='Hospital.Bedside',min_count=2,max_count=3,bed_gap=24)
layout=dict(revision=2,groups=groups,ward_cart_reservations=cart_reserves,bedside=bedside,
            outline=staff['container_outline'],preview_seed=20261003,
            count_ranges=dict(Drainage=[2,2],AbandonedIsolationWard=[8,9],AbandonedAnatomyTheatre=[5,7]),
            bedside_count_policy='2-3 desired; occupied or blocked bedside slots are skipped',
            rewards_deferred=True,tests_run=False,rendered=False)
(ROOT/'Config/layout.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2),encoding='utf8')

image=Image.new('RGB',(800,2400),(222,226,217));draw=ImageDraw.Draw(image)
large=ImageFont.truetype('C:/Windows/Fonts/simsun.ttc',62)
small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',25)
title=[('医疗耗材','MEDICAL SUPPLIES'),('个人物品','PATIENT BELONGINGS'),('急救用品','FIRST AID'),
       ('消毒器械','STERILE INSTRUMENTS'),('标本转运','SPECIMEN TRANSPORT'),('检修工具','MAINTENANCE TOOLS')]
for row,(cn,en) in enumerate(title):
    top=row*400;draw.rectangle((20,top+20,779,top+379),outline=(57,75,71),width=5)
    draw.rectangle((22,top+22,777,top+73),fill=(57,75,71))
    draw.text((60,top+115),cn,font=large,fill=(38,49,47))
    draw.text((62,top+222),en,font=small,fill=(60,72,68))
    draw.line((60,top+283,740,top+283),fill=(96,107,97),width=3)
    draw.text((62,top+310),'HOSPITAL / '+str(row+1).zfill(2)+'   |   HANDLE WITH CARE',font=small,fill=(65,76,70))
image.save(ROOT/'Authored/T_Hospital_Labels.png')
print('HOSPITAL_LAYOUT_AND_LABELS_AUTHORED',flush=True)
