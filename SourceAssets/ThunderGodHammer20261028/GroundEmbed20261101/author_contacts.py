"""Author ground contact anchors from the five current hammer-head meshes; no renders."""
import bpy
import json
import math
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
MODULES = OUT.parent / 'ModulesV1'
rows = []
for variant in ('factory', 'heavy_forged', 'flanged_breaker', 'light_drum', 'pointed_hammer'):
    name = 'SM_ThunderGodHammer_hammer_heads_' + variant
    source = MODULES / ('ThunderGodHammer_Modular_Editable.blend' if variant == 'factory' else 'ThunderGodHammer_SharedParts_Editable.blend')
    with bpy.data.libraries.load(str(source), link=False) as (available, loaded):
        loaded.objects = [name]
    obj = loaded.objects[0]
    # Mesh coordinates are relative to the head pivot, in metres. UE import
    # preserves X/Z and flips Y. Module placement adds Z=91.6 cm, then the
    # thrown assembly subtracts its 70 cm flight pivot. At pitch +135 degrees,
    # world Z = sin(pitch)*local X + cos(pitch)*local Z.
    points = [(v.co.x*100., -v.co.y*100., v.co.z*100.) for v in obj.data.vertices]
    a = math.radians(135.)
    heights = [math.sin(a)*p[0] + math.cos(a)*p[2] for p in points]
    lowest = min(heights)
    support = [p for p, h in zip(points, heights) if h <= lowest + .05]
    point = [sum(p[i] for p in support)/len(support) for i in range(3)]
    rows.append(dict(variant=variant, mesh=name, mesh_local_contact_cm=point,
                     source=str(source), pitch_degrees=135., support_tolerance_cm=.05))
    bpy.data.objects.remove(obj, do_unlink=True)

(OUT/'contacts.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
lines = ['#pragma once', '#include "CoreMinimal.h"', '',
         '// Authored from the current five hammer-head meshes, at GroundPitch=135.',
         '// Mesh-local centimetres; apply the installed module transform and CenterZ.',
         '// Regenerate with SourceAssets/ThunderGodHammer20261028/GroundEmbed20261101/author_contacts.py',
         'namespace ThunderHammerThrow {',
         'inline FVector GroundHeadContact(const FString& MeshPath)', '{']
for row in rows[1:]:
    p = row['mesh_local_contact_cm']
    lines.append('    if(MeshPath.EndsWith(TEXT(".' + row['mesh'] + '")))return FVector(' + ','.join(f'{v:.9f}' for v in p) + ');')
lines += ['    return FVector(' + ','.join(f'{v:.9f}' for v in rows[0]['mesh_local_contact_cm']) + ');', '}', '}', '']
(ROOT/'Source/FPSGAME/Production/ThunderHammerGroundContacts.h').write_text('\n'.join(lines), encoding='utf-8')
print(json.dumps(rows, indent=2), flush=True)
