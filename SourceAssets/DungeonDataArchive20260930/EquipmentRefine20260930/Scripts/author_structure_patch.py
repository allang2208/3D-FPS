"""Export only the four revised architecture groups, keeping existing packages intact."""
from pathlib import Path
TASK=Path(__file__).resolve().parents[1];HALL=TASK.parent
p=HALL/'Scripts/author_archive.py';source=p.read_text(encoding='utf-8')
# Run the actual hall author up to its export stage with its own path/context.
source=source[:source.index("EXPORT_BLEND_NAME=")]
scope={'__file__':str(p),'__name__':'__main__'};exec(compile(source,str(p),'exec'),scope)
scope['G']={k:v for k,v in scope['G'].items() if k in ('Railings','EquipmentBases','BayFrames','BayPanels')}
scope['OUT']=TASK/'Structure';scope['EXPORT_SUFFIX']='_V2';scope['EXPORT_BLEND_NAME']='Archive_RailsAndWallBays_V2.blend'
p=HALL/'Scripts/export_geometry.py';exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),scope)
