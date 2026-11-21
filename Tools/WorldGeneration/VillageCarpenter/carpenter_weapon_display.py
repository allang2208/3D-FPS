"""Freestanding bowyer's rack along the west street bay of plot 04 (centimetres)."""
import json
from pathlib import Path

import unreal as u
from author_shop import pose, require


PLANK = '/Game/UnrealNormandy/StaticMeshes/SM_HW_Plank_'
FINISH = '/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_Carpenter'
LEATHER = '/Game/Building/ArcaneWorkbenchV6_20261107/Materials/M_EW_Leather_dark_worn_binding'
LINEN = '/Game/Weapons/DarkBow20260925/ModularV13/M_Bow_GripLinen'
ROUND = '/Engine/BasicShapes/Cylinder'
BOWS = '/Game/Weapons/DarkBow20260925/BodyVariantsV14/SM_Bow_Body_'
STATIC_DISPLAY = 'VillageCarpenter.DisplayStatic'


def add_weapon_display(house, add):
    # Turn the complete rack to face the central aisle. Both ends fit between
    # the street pier and the foot of the west stair without narrowing its treads.
    frame = pose(house, -9, -397, yaw=180)
    data = Path(__file__).resolve().parents[3] / 'Content/ColdSteelData'
    def catalogue(name):
        return json.loads((data / (name + '.json')).read_text(encoding='utf-8-sig'))
    bow = catalogue('bows')['bow_dark']
    staff = catalogue('staffs')['ue_apprentice_staff']
    staff_columns = {c['key']: c for c in catalogue('staff-gunsmith')['columns']}
    def option(key, part_id):
        return next(p['mesh'] for p in staff_columns[key]['options'] if p['id'] == part_id)

    placements = {'Common': 0, 'Ruined': 0, 'Repaired': 0}
    weapon_parts = set()
    def mount(state, path, t, material=None, profile='NoCollision', single=False):
        placements[state] += 1
        if path.startswith('/Game/Weapons/'):
            weapon_parts.add(path)
        add(state, path, u.MathLibrary.compose_transforms(t, frame),
            (material,) if material else (), profile=profile, extra=(STATIC_DISPLAY,) if single else ())

    pieces = {}
    for suffix in ('00A', '01A'):
        path = PLANK + suffix
        bounds = require(path).get_bounding_box()
        pieces[suffix] = (path, (bounds.min + bounds.max)*.5, bounds.max-bounds.min)

    def plank(state, a, b, thickness, height, finish='Sawn', rough=False, profile='NoCollision'):
        a,b = u.Vector(*a),u.Vector(*b)
        direction = b-a
        path, middle, span = pieces['01A' if rough else '00A']
        t = u.Transform(location=(a+b)*.5, rotation=u.MathLibrary.make_rot_from_x(direction),
                        scale=(direction.length()/span.x,thickness/span.y,height/span.z))
        mount(state,path,u.MathLibrary.compose_transforms(u.Transform(location=-middle),t),FINISH+finish,profile)

    def pin(state, a, b, radius, material, single=False):
        a,b = u.Vector(*a),u.Vector(*b)
        axis = b-a
        t = u.Transform(location=(a+b)*.5,rotation=u.MathLibrary.make_rot_from_z(axis),
                        scale=(radius/50,radius/50,axis.length()/100))
        mount(state,ROUND,t,material,single=single)

    # Independent shoes are bedded into the three worn floorboards in this bay.
    for y, floor in ((-313,-1.44),(-142,-.30),(-40,-2.58)):
        plank('Common',(336,y,floor+3),(378,y,floor+3),11,6,profile='BlockAll')
        plank('Common',(368,y,floor+4),(368,y,187),9,7,profile='BlockAll')
        plank('Common',(340,y,floor+6),(366,y,30),5.5,6,rough=True)
        for z in (23,108):
            pin('Common',(362.9,y,z),(372.4,y,z),1.05,FINISH+'Cut')
    plank('Common',(368,-321,25),(368,-33,25),8,10,rough=True)
    plank('Common',(369,-316,43),(369,-139,96),4.5,6.5,rough=True)
    plank('Common',(361,-321,109),(361,-34,109),7,14,profile='BlockAll')
    plank('Repaired',(361,-321,169),(361,-140,169),7,14,profile='BlockAll')
    plank('Ruined',(361,-322,169),(362,-232,166),7,11,'Rot',True)
    for y,z in ((-313,109),(-142,109),(-40,109),(-313,169)):
        pin('Common',(356.9,y,z),(365.5,y,z),1.15,FINISH+'Iron')
    pin('Repaired',(356.9,-142,169),(365.5,-142,169),1.15,FINISH+'Iron')

    # The shelves follow the two lengths of stock: short fletching supplies on
    # the left, two full-height vertical staff sockets on the right.
    plank('Common',(352,-318,36),(352,-143,36),26,4.5,profile='BlockAll')
    for y in (-313,-149):
        plank('Common',(337,y,32),(367,y,32),7,5)
        plank('Common',(341,y,30),(366,y,18),4.3,4.5)
    plank('Repaired',(353,-139,17),(353,-34,17),27,5.2,profile='BlockAll')
    for y in (-137,-42):
        plank('Repaired',(338,y,11),(370,y,11),7,7)
    # A rim keeps a shaft's ferrule seated without modelling solid wood through it.
    for x in (340.4,362.8):
        plank('Repaired',(x,-137,22),(x,-38,22),3.2,5.2)
    for y in (-131,-78,-42):
        plank('Repaired',(341,y,22),(362,y,22),3,5.2)

    # Native static risers retain the protected nock and wrap interfaces of the
    # animated hunter bow. Rotate the entire assembly together, at catalog scale.
    bow_center_y = -228.
    bow_rotation = u.MathLibrary.make_rot_from_xz(u.Vector(0,0,1),u.Vector(0,1,0))
    def nock(key):
        return u.Vector(*map(float,bow[key].split(',')))

    for body,height,undersides in (('Swift',173.,(-3.19,-2.92)),('Heavy',115.,(-6.16,-6.68))):
        t = u.Transform(location=(348.,bow_center_y,height),rotation=bow_rotation)
        for path in (BOWS+body,bow['bow_part_grip_mesh'],bow['bow_part_arrow_rest_mesh']):
            mount('Repaired',path,t,single=True)
        # String uses the same local-space nocking points and thickness as the weapon.
        anchors = [u.MathLibrary.transform_location(t,nock(k)) for k in
                   ('nock_lower_cm','brace_nock_cm','nock_upper_cm')]
        for p,q in zip(anchors,anchors[1:]):
            pin('Repaired',(p.x,p.y,p.z),(q.x,q.y,q.z),bow['bow_part_string_radius_cm'],
                bow['bow_part_string_material'],single=True)
        # Heights come from the lower surfaces of the actual limb mesh in the two
        # z=+/-28 cm sections. The padded pegs carry the wood, clear of the string.
        for offset,underside in zip((-28,28),undersides):
            y = bow_center_y+offset
            z = height+underside-1.55
            pin('Repaired',(336.8,y,z),(363.6,y,z),1.19,FINISH+'Cut')
            pin('Repaired',(343.6,y,z),(352.4,y,z),1.55,LEATHER,single=True)
            pin('Repaired',(337.6,y,z),(337.6,y,z+4.7),1.12,FINISH+'Brass')

    # One catalogued, complete apprentice staff and a second fitted from the
    # native body/grip/head/crown set. Those components share their authored pivot.
    for y,paths,orientation in (
            (-102,(staff['world_mesh'],),4),
            (-57,(staff['staff_body_mesh'],option('grip_lining','pine_grip'),
                  option('head_crystal','jade_spirit_crystal'),option('crown','wreath_crown')),-26)):
        base_bounds = require(paths[0]).get_bounding_box()
        t = u.Transform(location=(351.5,y,19.6-base_bounds.min.z),rotation=u.Rotator(yaw=orientation))
        for path in paths:
            mount('Repaired',path,t,single=True)
        for side in (-1,1):
            yy = y+side*4.1
            pin('Repaired',(347.3,yy,109),(362.7,yy,109),1.2,FINISH+'Brass')
            pin('Repaired',(349.3,yy,109),(355.2,yy,109),1.42,LEATHER,single=True)

    # A lipped tray, two arrow saddles and three of the project's 76 cm arrows.
    for x in (341,363):
        plank('Repaired',(x,-314,40),(x,-207,40),2.5,4.2)
    for y in (-292,-239):
        plank('Repaired',(342,y,40),(363,y,40),3.5,3.7)
    for x,cy,turn in ((346,-265,90),(352,-267,89),(358,-263,91)):
        mount('Repaired',bow['bow_part_arrow_mesh'],u.Transform(
            location=(x,cy,42.1),rotation=u.Rotator(yaw=turn)),single=True)
    # Hand-wound linen bobbin, end-grain flanges and a spindle end on the shelf.
    for y,radius,half_length in ((-185,3.75,3.9),(-164,2.6,2.5)):
        z=43.55
        pin('Repaired',(351,y-4.3,z),(351,y+4.3,z),1.9,FINISH+'Sawn')
        pin('Repaired',(351,y-half_length,z),(351,y+half_length,z),radius,LINEN,single=True)
        for face in (y-4.5,y+3.9):
            pin('Repaired',(351,face,z),(351,face+.65,z),5.3,FINISH+'Cut')
        pin('Repaired',(351,y-5.4,z),(351,y+5.4,z),1.1,FINISH+'Sawn')

    # The one intact rail and a surviving pair of pegs explain this fixture when
    # the market stock is absent. The slipped top rail lies across the empty shelf.
    for y in (-256,-200):
        pin('Ruined',(343,y,108),(363.2,y,108),1.25,FINISH+'Cut')
    plank('Ruined',(349,-279,41),(354,-188,41),7,4.7,'Rot',True)
    plank('Ruined',(350,-239,45),(354,-194,45),3.1,3.4,'Cut',True)
    return {'bay': 'west street bay', 'placements': placements, 'weapon_parts': sorted(weapon_parts)}
