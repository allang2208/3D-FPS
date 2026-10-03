"""Publish only the selected authored food motion families."""
import json
import copy
import math
import runpy
from pathlib import Path

food_motion = runpy.run_path(str(Path(__file__).with_name('natural_food_motion.py')))['food_motion']

def runtime_family(definition, profile):
    """Express the authored contact in the existing center-anchored prop frame.

    Moving both the grip track and palm relation by the same rigid offset keeps
    the actual grasp intact. The runtime's bounds-center assignment therefore
    needs no native change; each food still retains its own physical contact.
    """
    family = copy.deepcopy(profile)
    family.update(food_motion(definition))
    height = 6.0 if definition == 'bread' else 15.0
    contact = family.pop('grip_in_object')
    delta = [-contact[0], -contact[1], height-contact[2]]
    palm_delta = [delta[0], -delta[2], delta[1]]
    family['grip_in_palm'] = [round(a+b,4) for a,b in zip(family['grip_in_palm'],palm_delta)]
    family['grip_height'] = height
    family['authored_contact_in_object'] = contact
    for key in family['keys']:
        pitch, yaw, roll = key['rotation']
        p,y,r = map(math.radians,(-pitch,yaw,-roll))
        x,v,z = delta
        v,z = math.cos(r)*v-math.sin(r)*z, math.sin(r)*v+math.cos(r)*z
        x,z = math.cos(p)*x+math.sin(p)*z, -math.sin(p)*x+math.cos(p)*z
        x,v = math.cos(y)*x-math.sin(y)*v, math.sin(y)*x+math.cos(y)*v
        key['grip'] = [round(a+b,5) for a,b in zip(key['grip'],(x,v,z))]
    return family

def publish(definitions=('bread','baguette_bread')):
    source = Path(__file__).resolve().parent/'grip_profiles.json'
    path = Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/potion_use_motion.json')
    profiles = json.loads(source.read_text(encoding='utf-8'))
    motion = json.loads(path.read_text(encoding='utf-8-sig'))
    for definition in definitions:
        profiles[definition].update(food_motion(definition))
        motion[definition] = runtime_family(definition,profiles[definition])
    source.write_text(json.dumps(profiles,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    path.write_text(json.dumps(motion,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    catalog_path = path.with_name('items.json')
    catalog = json.loads(catalog_path.read_text(encoding='utf-8-sig'))
    for definition in definitions:
        catalog[definition]['useDuration'] = profiles[definition]['times']['duration']
    catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('FOOD_MOTION_SAVED', ','.join(definitions))

if __name__ == '__main__': publish()
