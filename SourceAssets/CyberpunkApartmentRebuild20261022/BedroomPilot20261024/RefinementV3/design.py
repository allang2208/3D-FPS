from pathlib import Path
import runpy,copy
R=Path(__file__).resolve().parent;PROJECT=R.parents[3]
base=runpy.run_path(str(R.parent/'design.py'))
SURFACES=copy.deepcopy(base['SURFACES']);SUB=base['SUB'];SOURCE_MAP=base['SOURCE_MAP'];MAP=base['MAP']
BASE='/Game/Props/CyberpunkBedroomPilot20261024/RefinementV3'
OWNER='Cyberpunk.BedroomPilot.RefinementV3'
for role,period,strength in [('Graphite',.16,.48),('EdgeSteel',.22,.45),('Copper',.22,.38),('Walnut',.65,.75),('CharcoalWeave',.13,1.),('FogLinen',.16,.9),('OchreCloth',.13,.95),('Rug',.20,1.05),('Rubber',.12,.55)]:
    SURFACES[role].update(period=period,strength=strength)
# The library tile contains hundreds of yarn repeats. A 13 cm tile reduced the
# yarn below a pixel at ordinary bedside distance; use physically legible yarns.
for role,period in [('CharcoalWeave',.55),('FogLinen',.32),('OchreCloth',.45),('Rug',.55)]:SURFACES[role]['period']=period
SURFACES['CharcoalWeave']['base']='02_Upholstery/Textiles/T_TextilePlain_BC'
SURFACES['FogLinen']['base']='02_Upholstery/Textiles/T_TextileStriped_BC'
SURFACES['OchreCloth']['base']='02_Upholstery/Textiles/T_TextilePlain_BC'
for role,family,color,rough,period in [('Ceramic','Ceramic',(.32,.36,.31),(.25,.43),.12),('Paper','Paper',(.65,.61,.49),(.70,.88),.10),('PageEdges','Pages',(.64,.60,.49),(.74,.91),.10),('Soil','Soil',(.045,.027,.014),(.84,.97),.15),('Leaf','Leaf',(.10,.22,.055),(.32,.57),1.)]:
    SURFACES[role]=dict(color=color,limits=rough,metal=0,period=period,strength=.75 if role!='Leaf' else .55,generated=family)
for role,color in [('BookNavy',(.028,.055,.075)),('BookOchre',(.24,.115,.045)),('BookSage',(.12,.16,.105))]:
    SURFACES[role]=dict(color=color,normal='02_Upholstery/T_Leather_00_SmallGrain_N',rough='02_Upholstery/T_Leather_00_SmallGrain_R',period=.14,strength=.65,limits=(.48,.68),metal=0)
SURFACES['Stem']=dict(color=(.045,.09,.026),normal='08_WoodVeneer/T_WoodVeneer_Oak_N',rough='08_WoodVeneer/T_WoodVeneer_Oak_R',period=.04,strength=.35,limits=(.5,.72),metal=0)
BRIEF=dict(base['BRIEF'],revision='V3 close-range geometry, closed lamps and calibrated PBR',geometry_checks_requested=True)
