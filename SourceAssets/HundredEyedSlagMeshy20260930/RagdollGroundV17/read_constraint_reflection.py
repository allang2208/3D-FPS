"""Read the constraint serialization fields needed for asset authoring."""
import json
from pathlib import Path
import unreal as u

OUT = Path(__file__).resolve().parent
pa = u.load_asset('/Game/Monsters/HundredEyedSlag/RagdollGroundV16/PA_HundredEyedSlag_Ground_V16')
joint = u.load_object(None, pa.get_path_name() + ':PhysicsConstraintTemplate_0')
if not joint:
    raise RuntimeError('Constraint subobject is unavailable')
row = {'joint': joint.get_path_name(), 'fields': {}}
for name in ('default_instance', 'default_profile'):
    try:
        value = joint.get_editor_property(name)
        row['fields'][name] = str(value)
        if name == 'default_instance':
            for prop in ('profile_instance', 'constraint_bone1', 'constraint_bone2', 'pos1', 'pos2'):
                try:
                    row['fields'][prop] = str(value.get_editor_property(prop))
                except Exception as e:
                    row['fields'][prop] = str(e)
    except Exception as e:
        row['fields'][name] = str(e)
(OUT / 'constraint_serialization_fields.json').write_text(json.dumps(row, indent=2), encoding='utf-8')
print('SLAG_CONSTRAINT_SERIALIZATION_FIELDS_READ', flush=True)
