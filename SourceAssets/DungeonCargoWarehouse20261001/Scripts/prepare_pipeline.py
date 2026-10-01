"""Use the proven importer/exporter while limiting all writes to warehouse packages."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
old=PROJECT/'SourceAssets/DungeonFlueGasStation20261001'
s=(old/'Scripts/export_geometry.py').read_text('utf-8')
s=s.replace('FlueGas','CargoWarehouse').replace('AbandonedFlueGasStation_Source','AbandonedCargoWarehouse_Source')
start=s.index('no_collision=');end=s.index('for kind,g in G.items():')
s=s[:start]+"""no_collision={'Frames','RoofRibs','Hardware','RackHardware','RackBraces','Signs','SignSupports',
 'FloorMarkings','Nosing','HoistChain','HoistHook','CableTrays','LampHangers','Rollers'}
bevel_kinds={'Walls','Columns','Floors','Racks','RackDecks','RackGuards','Dock','DockEdge','RollerFrame','StairTreads','Hoist','HoistHook'}
"""+s[end:]
s=s.replace("kind not in {'Signs','FloorMarkings','Instruments','WetPipework','ControlHardware'}", "kind not in {'Signs','FloorMarkings','Hardware','RackHardware','RackBraces','SignSupports','HoistChain','HoistHook','Nosing','CableTrays','LampHangers','Rollers'}")
s=s.replace("    if globals().get('EXPORT_KINDS') and kind not in EXPORT_KINDS:continue\n",'')
s=s.replace("    fbx=OUT/(name+'.fbx')", "    if globals().get('EXPORT_KINDS') and kind not in EXPORT_KINDS:\n        for co in collision_objects:co.hide_render=True;co.hide_viewport=True\n        continue\n    fbx=OUT/(name+'.fbx')")
(ROOT/'Scripts/export_geometry.py').write_text(s,encoding='utf-8')
print('CARGO_WAREHOUSE_EXPORT_PIPELINE_WRITTEN')
