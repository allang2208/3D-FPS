"""Author the reusable central botanical display assembly and its printed nameplate."""
from pathlib import Path
import json, math, random
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent;PARENT=ROOT.parent;PROJECT=PARENT.parents[1]
BASE='/Game/Dungeons/FacilityTransit20261007/BotanicalDisplay'
for d in ('Authored/Textures','Receipts'): (ROOT/d).mkdir(parents=True,exist_ok=True)
fits=json.loads((PROJECT/'SourceAssets/DungeonEcology20261004/Sources/StockV4/root-fits.json').read_text('utf8'))
roles=json.loads((PARENT/'RefineV2/materials.json').read_text('utf8'))
keep=('Steel','Graphite','Gasket','EC','Stone','Brass','Glow','Soil')
roles={k:roles[k] for k in keep}
roles['Labels']=dict(existing_ue_path=BASE+'/Materials/M_BotanicalDisplay_Label',basecolor_linear=[.05,.09,.065],roughness=.65,metallic=.12,uv_meters=1)
(ROOT/'materials.json').write_text(json.dumps(roles,indent=2),encoding='utf8')
im=Image.new('RGB',(2048,512),(20,36,29));d=ImageDraw.Draw(im)
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
d.rounded_rectangle((16,16,2031,495),radius=12,outline=(155,145,104),width=4)
d.rectangle((48,52,59,460),fill=(183,162,106))
d.text((100,62),'植物生态展柜',font=font(106),fill=(229,229,211))
d.text((108,197),'BOTANICAL CONSERVATORY  /  LIVING COLLECTION',font=font(41),fill=(177,191,167))
d.line((110,279,1925,279),fill=(100,117,90),width=3)
d.text((108,318),'乔木 · 林下植物 · 循环灌溉',font=font(51),fill=(211,219,198))
d.text((108,398),'设施植物收藏  01       请勿敲击玻璃',font=font(34),fill=(167,184,157))
im.save(ROOT/'Authored/Textures/T_BotanicalDisplay_Label.png')
(ROOT/'atlas.json').write_text(json.dumps(dict(size=[2048,512],rects={'exhibit':[0,0,2048,512]})),encoding='utf8')

def soil_z(x,y):
    return .605+.058*math.exp(-((x-.55)**2+(y+.5)**2)/2.4)+.022*math.sin(2.3*x+1.4*y)*max(0,1-math.hypot(x,y)/3.08)

def plant(mesh,root_pos,height,yaw,id):
    fit=fits[mesh];s=height/fit['height_m'];r=fit['root_blender_m'];co=math.cos(math.radians(yaw));si=math.sin(math.radians(yaw))
    return dict(id=id,mesh=mesh,position_m=[root_pos[0]-(co*r[0]-si*r[1])*s,root_pos[1]-(si*r[0]+co*r[1])*s,root_pos[2]-r[2]*s-.014],scale=[s]*3,yaw_deg=yaw,root_position_m=root_pos,height_m=height,collision=False,cast_shadow=True)

tree_path='/Game/RuralAustralia/StaticMeshes/Vegetation/Tree_M_03/SM_Tree_M_03'
t=fits[tree_path];s=4.8/t['height_m'];cx=(t['min_m'][0]+t['max_m'][0])/2;cy=(t['min_m'][1]+t['max_m'][1])/2
# Centre the complete stock crown envelope, keeping the measured basal anchor in the soil.
root=[(t['root_blender_m'][0]-cx)*s,(t['root_blender_m'][1]-cy)*s,0]
root[2]=soil_z(*root[:2]);tree=plant(tree_path,root,4.8,0,'CanopyTree');tree['collision']=True
tree['indoor_tree_materials']=True
plants=[tree];rng=random.Random(71007)
prefix='/Game/PN_tropicalGroundPlants/Meshes/tropicalPlant_'
# Broad leaves inside, fine ground foliage outside; each full source envelope fits the glass.
for ring,(radius,count,kinds,heights) in enumerate(((1.30,9,('01_01','01_02','02_01'),(.72,1.10)),(2.12,15,('03_01','04_01','04_02','05_02'),(.30,.58)))):
    for i in range(count):
        angle=math.tau*(i+.18*ring)/count+rng.uniform(-.065,.065);r=radius+rng.uniform(-.10,.10);x,y=r*math.cos(angle),r*math.sin(angle)
        mesh=prefix+kinds[i%len(kinds)];fit=fits[mesh];anchor=fit['root_blender_m']
        bound=max(math.hypot(xx-anchor[0],yy-anchor[1]) for xx in (fit['min_m'][0],fit['max_m'][0]) for yy in (fit['min_m'][1],fit['max_m'][1]))
        h=min(rng.uniform(*heights),(3.03-r)*fit['height_m']/max(bound,.01))
        plants.append(plant(mesh,[x,y,soil_z(x,y)],h,rng.uniform(0,360),'Understory_%02d_%02d'%(ring,i)))

radius=3.3;ap=radius*math.cos(math.pi/12);width=2*radius*math.sin(math.pi/12)-.048;height=5.66
glass=[dict(id='DisplayGlass_%02d'%i,position_m=[ap*math.cos(math.tau*i/12),ap*math.sin(math.tau*i/12),3.52],yaw_deg=30*i,width_m=width,height_m=height,
            pane=BASE+'/Meshes/SM_FT_Botanical_DisplayPaneV5',fracture=BASE+'/Meshes/SM_FT_Botanical_DisplayFractureV5') for i in range(12)]
cfg=dict(revision='20261007-botanical-display-v1',base=BASE,owner='FacilityTransit.BotanicalDisplay',position_m=[0,0,0],base_diameter_m=7.0,glass_radius_m=radius,height_m=6.52,glass=glass,plants=plants,
         lights=[dict(id='Botanical_Canopy_A',position_m=[1.82,0,6.12],intensity=280,radius=4.4,cast_shadows=False,type='point',role='Local'),dict(id='Botanical_Canopy_B',position_m=[-1.82,0,6.12],intensity=280,radius=4.4,cast_shadows=False,type='point',role='Local')],
         replaces_actor_labels=['FacilityTransit_SM_FT_Hall_FloorGuidance'],maps=['/Game/GameMaps/Design/L_FacilityTransit_Subject','/Game/GameMaps/Design/L_FacilityTransit_Alternate_Subject'],
         asset_provenance='Reuse project-owned RuralAustralia Tree_M_03, PN_tropicalGroundPlants, Ecology soil and indoor tree material instances. Original fabricated display case.',tests_run=False,rendered=False)
(ROOT/'assembly.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
print('BOTANICAL_DISPLAY_PREPARED',len(plants),'reused botanical placements')
