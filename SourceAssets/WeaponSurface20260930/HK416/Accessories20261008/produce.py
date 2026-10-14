"""HK416-only accessory finish recipe; factory geometry/materials are excluded."""
import json,hashlib
from pathlib import Path
O=Path(__file__).parent;C=json.loads((O/'Input/current.json').read_text())
R={'version':'HK416-AccessoryFinish-20261008','root':'/Game/Weapons/HK416/AccessoryFinish20261008',
   'targets':{},'bindings':{},'retained':{},'reference':{},'geometry_changed':False,'tested':False}
for path,row in C['meshes'].items():
    if row['skeletal']:
        R['reference'][path]=row['slots'];continue
    selected=[];kept=[]
    for s in row['slots']:
        source=s['material'];m=C['materials'][source];params=m['parameters'];p=params['scalar'];slot=s['slot'];name=slot.lower()
        scalars={};vectors={};mode='';normal=None
        if slot=='HK416_Original_Rail_Clamp':
            kept.append({**s,'reason':'original HK416 clamp'});continue
        if 'R01_Roughness' in p:
            mode='existing_authored'
            # Keep the finer RG01 normal/roughness treatment already applied to
            # rear grips. Use no higher noise amplitude than their current one.
            scalars={'R01_Grain':min(p['R01_Grain'],.007),'R01_Variation':min(p['R01_Variation'],.002),
                     'R01_SourceRoughnessWeight':min(p['R01_SourceRoughnessWeight'],.20),
                     'R01_PolymerSourceWeight':min(p['R01_PolymerSourceWeight'],.18),
                     'R02_SourceColorContrast':.50,'WeaponWetness':0.}
            vectors={'R01_ToneScale':[.52,.55,.59],'R01_PolymerTint':[.022,.023,.025]}
        elif name.startswith('stock_') and '/LegendaryStock20261006/' in source:
            mode='stock'
            profiles={'Stock_Graphite':([.024,.026,.029],0.,.42,.55),
                      'Stock_Polymer':([.022,.023,.025],0.,.51,.75),
                      'Stock_Steel':([.034,.035,.037],1.,.35,.65),
                      'Stock_Rubber':([.017,.018,.019],0.,.67,.85)}
            if slot not in profiles:
                kept.append({**s,'reason':'intentional champagne/red decoration'});continue
            color,metal,rough,normal=profiles[slot]
            scalars={'Metallic':metal,'RoughnessScale':rough/.9,'AccessoryWetRoughness':max(.12,rough*.76),
                     'AccessoryNormalDetail':normal,'WeaponWetness':0.}
            vectors={'SurfaceTint':color}
        elif name.startswith('thermal_'):
            mode='thermal';base=slot.rsplit('_',1)[0] if slot.rsplit('_',1)[-1].isdigit() else slot
            profiles={'Thermal_Graphite':([.030,.032,.034],1.,.39),
                      'Thermal_Copper':(None,1.,.32),'Thermal_Titanium':(None,1.,.32),
                      'Thermal_LegendRed':(None,0.,.43),'Thermal_Marking':(None,0.,.52),
                      'Thermal_Rubber':(None,0.,.65)}
            if base not in profiles:
                kept.append({**s,'reason':'optical/display function'});continue
            color,metal,rough=profiles[base]
            scalars={'Metallic':metal,'DryRoughness':rough,'AccessoryWetRoughness':max(.12,rough*.76),
                     'AccessoryGrain':.007 if base=='Thermal_Graphite' else 0.,'WeaponWetness':0.}
            if color:vectors={'SurfaceTint':color}
        elif slot in ('Blessed_Graphite','Blessed_Gold','Blessed_Black'):
            mode='blessed';profiles={'Blessed_Graphite':([.030,.032,.034],1.,.39),
                                    'Blessed_Gold':([.68,.43,.14],1.,.29),
                                    'Blessed_Black':([.009,.011,.014],0.,.53)}
            color,metal,rough=profiles[slot];vectors={'SurfaceTint':color}
            scalars={'Metallic':metal,'DryRoughness':rough,'WeaponWetness':0.}
        else:
            kept.append({**s,'reason':'preserve optical, markings, rubber or recess material'});continue
        key=source+'|'+mode;suffix=hashlib.sha1(key.encode()).hexdigest()[:10]
        R['targets'][key]={'source':source,'mode':mode,'base':m['base'],'scalars':scalars,'vectors':vectors,
                           'asset':R['root']+'/Materials/MI_HK416_A08_'+mode+'_'+suffix}
        selected.append({**s,'key':key})
    if selected:R['bindings'][path]=selected
    if kept:R['retained'][path]=kept
(O/'recipe.json').write_text(json.dumps(R,indent=2))
print('HK416_ACCESSORY_RECIPE',len(R['targets']),'materials',len(R['bindings']),'meshes')
