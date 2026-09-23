"""Build the 100 x 100 m Roman marble plaza (v2) in the main hub map.

User-confirmed design (2026-09-22, second round):
  * plaza centre moved north to (1350, -975) -- exactly the midpoint of the fountain
    (y = -1550) and the pavilion (y = -400), so the pair is symmetric about the centre;
  * perimeter columns are the SQUARE-BASE `SM_RomanColumn_Detailed`, carrying
    `SM_Colonnade_Entablature` beams;
  * an inner precinct ring (low balustrade + Roman columns) encloses the pavilion and
    the fountain: rectangle, half 900 x 1200, centred on the plaza centre;
  * the whole pavilion is lifted so its base sits on the marble (it was coplanar with
    the new paving before);
  * gates are cut in both rings so the plaza is not a sealed box.

Layout numbers (cm):
  paving      : 6 x 13 of SM_MarbleFloorTiles, exactly 10000 x 10000, z 0..20
  colonnade   : half 4500, bay 500, square-base columns, 5 entablature beams per side
  balustrade  : half 4900, bay 200, 560-wide gate at each side midpoint
  precinct    : half 900 (x) x 1200 (y) around (1350,-975), low balustrade only
                (its 12 Roman columns were removed on 2026-09-23), gates on all four sides
  altar       : (1350, -2700) on the axis, outside the precinct
  fountain    : bounding box standing on the paving top (z = 20)

Idempotent: every generated actor carries `ColdSteel.MainPlaza.Generated` and is rebuilt
each run. Aborts rather than saving when another task's unsaved level edits are present.
Never starts PIE.

Run through Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript.
"""
import json
import traceback
from pathlib import Path

import unreal

HERE = Path(__file__).parent
MAP = '/Game/GameMaps/DayNight_Lighting'
PROPS = '/Game/Props/RomanColumn20260915'

MESH_PAVING = PROPS + '/SM_MarbleFloorTiles'
MESH_COLUMN_SQUARE = PROPS + '/SM_RomanColumn_Detailed'      # square-base perimeter column
MESH_COLUMN_ROUND = PROPS + '/SM_RomanColumn_Round_20'       # round column for the precinct
MESH_ENTABLATURE = PROPS + '/SM_Colonnade_Entablature'
MESH_BALUSTER = PROPS + '/SM_RomanBaluster_Small'
MESH_RAIL = PROPS + '/SM_RomanRail_200'

TAG = 'ColdSteel.MainPlaza'
TAG_GEN = TAG + '.Generated'
TAG_SUP = TAG + '.Superseded'
ALTAR_TAG = 'ColdSteel.ExpeditionAltar'
VOXEL_PREFIX = 'RomanFence_Voxel_40_'
SUPERSEDED_LABELS = ('MarbleFloor_Colonnade', 'StairWalk_Step_01')
FOUNTAIN_LABEL = 'RomanFountain1'
PAVILION_PREFIX = 'RomanPavilion2_'

# --- layout constants (cm) -------------------------------------------------
CX, CY = 1350.0, -975.0            # plaza centre = midpoint of fountain and pavilion
HALF = 5000.0                      # 100 m square
TOP = 20.0                         # paving top = base plane of every prop
PAVING_COLS, PAVING_ROWS = 6, 13
PAVING_MESH_W, PAVING_MESH_D = 1800.0, 800.0
PAVING_FORCED_LOD = 2              # UE forced model = LOD index + 1; target is LOD1.

COLONNADE_HALF = 4500.0
COLONNADE_BAY = 500.0
ENTAB_Z = 265.0                    # beam bottom; 15 cm down over the capitals
ENTAB_MESH_LEN = 1632.0
ENTAB_DEPTH = 76.0
ENTAB_PER_SIDE = 5

BALUSTRADE_HALF = 4900.0
BAY = 200.0                        # balustrade module (rail length)
RAIL_LIFT = 100.0
OUTER_GATE_HALF = 300.0            # -> 560 clear between the flanking balusters

PRECINCT_HALF_X = 900.0
PRECINCT_HALF_Y = 1200.0
PRECINCT_COL_BAY = 600.0
PRECINCT_GATE_HALF_X = 200.0       # -> 360 clear
PRECINCT_GATE_HALF_Y = 300.0       # -> 560 clear

ALTAR_X, ALTAR_Y = CX, -2700.0     # stays on the axis, outside the precinct

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
api = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def vec(v):
    return [round(v.x, 2), round(v.y, 2), round(v.z, 2)]


def tags_of(actor):
    return [str(t) for t in actor.tags]


def mesh_of(actor):
    if not isinstance(actor, unreal.StaticMeshActor):
        return None
    comp = actor.static_mesh_component
    return comp.static_mesh if comp else None


def bottom_z(actor):
    center, extent = actor.get_actor_bounds(False)
    return center.z - extent.z


def read_prop(obj, name):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return None


def set_visible(comp, flag):
    try:
        comp.set_editor_property('visible', flag)
    except Exception:
        pass


def set_shadow(comp, flag):
    for name in ('set_cast_shadow', 'set_cast_shadows'):
        fn = getattr(comp, name, None)
        if fn:
            fn(flag)
            return name
    comp.set_editor_property('cast_shadow', flag)
    return 'set_editor_property'


def set_forced_lod(comp, index):
    for name in ('set_forced_lod_model', 'set_forced_lod'):
        fn = getattr(comp, name, None)
        if fn:
            fn(index)
            return name
    comp.set_editor_property('forced_lod', index)
    return 'set_editor_property'


def main():
    world = editor.get_editor_world()
    if world is None:
        raise RuntimeError('The editor has no world loaded; nothing was built.')
    if editor.get_game_world() is not None:
        raise RuntimeError('PIE is active; nothing was built.')
    current = world.get_path_name().split('.')[0]
    # Follow place_hub_altar.py: if another map is active, refuse when anything is dirty (so no
    # other task's unsaved work is lost), otherwise open the main map here and switch back after.
    previous_map = current
    switched = False
    if current != MAP:
        dirty_elsewhere = [p.get_path_name()
                           for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
        if dirty_elsewhere:
            raise RuntimeError('Preserve unsaved level edits before switching maps: %s; '
                               'nothing was built.' % ', '.join(dirty_elsewhere))
        if not level.load_level(MAP):
            raise RuntimeError('Could not open %s; nothing was built.' % MAP)
        switched = True
        world = editor.get_editor_world()
        if world is None or world.get_path_name().split('.')[0] != MAP:
            raise RuntimeError('Switching to %s did not take effect; nothing was built.' % MAP)

    generated = [a for a in api.get_all_level_actors() if TAG_GEN in tags_of(a)]
    dirty = [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if dirty and not generated:
        raise RuntimeError('The main map has unsaved edits from another task (%s); '
                           'nothing was built and the map was not saved.' % ', '.join(dirty))

    meshes = {}
    for key, path in (('paving', MESH_PAVING), ('square', MESH_COLUMN_SQUARE),
                      ('round', MESH_COLUMN_ROUND), ('entab', MESH_ENTABLATURE),
                      ('baluster', MESH_BALUSTER), ('rail', MESH_RAIL)):
        mesh = unreal.load_asset(path)
        if mesh is None:
            raise RuntimeError('Missing plaza mesh: ' + path)
        meshes[key] = mesh

    receipt = dict(map=MAP, center_cm=[CX, CY], half_size_cm=HALF, paving_top_z=TOP,
                   registry_removed=[], superseded=[], moved=[], generated={},
                   layout=dict(
                       paving='%dx%d' % (PAVING_COLS, PAVING_ROWS),
                       perimeter_column='SM_RomanColumn_Detailed (square base)',
                       colonnade_half=COLONNADE_HALF, colonnade_bay=COLONNADE_BAY,
                       entablature='%d beams/side at z=%.0f' % (ENTAB_PER_SIDE, ENTAB_Z),
                       balustrade_half=BALUSTRADE_HALF, balustrade_bay=BAY,
                       outer_gates='4 midpoints, 560 clear',
                       precinct_half=[PRECINCT_HALF_X, PRECINCT_HALF_Y],
                       precinct_columns='SM_RomanColumn_Round_20 every %.0f' % PRECINCT_COL_BAY,
                       precinct_gates='4 (one per side)',
                       altar_axis=[ALTAR_X, ALTAR_Y]))

    def place(mesh, loc, label, folder, yaw=0.0, scale=None, extra_tags=(),
              cast_shadow=True, forced_lod=None):
        actor = api.spawn_actor_from_class(unreal.StaticMeshActor, loc,
                                          unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw))
        if actor is None:
            raise RuntimeError('Actor spawn failed at %s' % (vec(loc),))
        actor.modify()
        comp = actor.static_mesh_component
        comp.set_mobility(unreal.ComponentMobility.MOVABLE)
        comp.set_static_mesh(mesh)
        comp.set_collision_profile_name('BlockAll')
        comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        comp.set_editor_property('generate_overlap_events', False)
        # A flat floor casts no visible shadow but virtual shadow maps would still rasterise
        # every triangle of it; forcing LOD1 keeps the 16.7 m panels off LOD0 everywhere.
        if not cast_shadow:
            set_shadow(comp, False)
        if forced_lod is not None:
            try:
                if mesh.get_num_lods() >= forced_lod:
                    set_forced_lod(comp, forced_lod)
            except Exception:
                pass
        if scale is not None:
            actor.set_actor_scale3d(scale)
        actor.set_actor_label(label)
        actor.tags = list(dict.fromkeys(tags_of(actor) + [TAG, TAG_GEN] + list(extra_tags)))
        actor.set_folder_path(folder)
        comp.set_mobility(unreal.ComponentMobility.STATIC)
        actor.set_editor_property('is_spatially_loaded', False)
        return actor

    def place_run(axis, fixed, half, yaw, prefix, folder, tag, col_ts=(), skip_ts=(),
                  gate_half=None, skip_ends=False):
        """One straight balustrade run plus its columns.

        axis 'x': run along world X at world Y = fixed; 'y': along world Y at world X = fixed.
        `half`   : half length of the run, a whole number of BAY modules.
        `col_ts` : local offsets that carry a column.
        `skip_ts`: additional local offsets where no baluster is placed (e.g. corners whose
                   column belongs to the perpendicular run).
        `gate_half`: removes balusters and rails whose |t| is below it, cutting a gateway
                   centred on the run.
        `skip_ends`: leave out both end posts so the perpendicular runs own the shared corners.
        """
        bays = int(round(2.0 * half / BAY))
        posts = 0
        for k in range(bays + 1):
            if skip_ends and k in (0, bays):
                continue
            t = -half + k * BAY
            if gate_half is not None and abs(t) < gate_half:
                continue
            if any(abs(t - c) < 45.0 for c in tuple(col_ts) + tuple(skip_ts)):
                continue
            loc = (unreal.Vector(CX + t, fixed, TOP) if axis == 'x'
                   else unreal.Vector(fixed, CY + t, TOP))
            place(meshes['baluster'], loc, '%sPost_%02d' % (prefix, k), folder,
                  yaw=yaw, extra_tags=(tag,))
            posts += 1
        rails = 0
        for j in range(bays):
            t = -half + (j + 0.5) * BAY
            if gate_half is not None and abs(t) < gate_half:
                continue
            loc = (unreal.Vector(CX + t, fixed, TOP + RAIL_LIFT) if axis == 'x'
                   else unreal.Vector(fixed, CY + t, TOP + RAIL_LIFT))
            place(meshes['rail'], loc, '%sRail_%02d' % (prefix, j), folder,
                  yaw=yaw, extra_tags=(tag,))
            rails += 1
        for i, t in enumerate(col_ts):
            loc = (unreal.Vector(CX + t, fixed, TOP) if axis == 'x'
                   else unreal.Vector(fixed, CY + t, TOP))
            place(meshes['round'], loc, '%sCol_%02d' % (prefix, i), folder,
                  yaw=yaw, extra_tags=(tag,))
        return posts, rails, len(col_ts)

    counts = {}
    with unreal.ScopedEditorTransaction('Build 100x100 m main plaza v2'):
        # ---- 1. remove our own previous output -------------------------------
        for actor in generated:
            api.destroy_actor(actor)

        # ---- 2. remove the authorized leftover voxel fence -------------------
        for actor in api.get_all_level_actors():
            if not actor.get_actor_label().startswith(VOXEL_PREFIX):
                continue
            mesh = mesh_of(actor)
            receipt['registry_removed'].append(dict(
                label=actor.get_actor_label(), cls=actor.get_class().get_name(),
                loc=vec(actor.get_actor_location()),
                mesh=(mesh.get_path_name() if mesh else None),
                scale=vec(actor.get_actor_scale3d())))
            api.destroy_actor(actor)

        # ---- 3. hide (never delete) floor leftovers coplanar with the paving -
        for actor in api.get_all_level_actors():
            if actor.get_actor_label() not in SUPERSEDED_LABELS:
                continue
            comp = actor.static_mesh_component if isinstance(actor, unreal.StaticMeshActor) else None
            receipt['superseded'].append(dict(
                label=actor.get_actor_label(), loc=vec(actor.get_actor_location()),
                was_component_visible=(read_prop(comp, 'visible') if comp else None)))
            actor.modify()
            if comp:
                set_visible(comp, False)
                comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            actor.set_actor_hidden_in_game(True)
            actor.tags = list(dict.fromkeys(tags_of(actor) + [TAG, TAG_SUP]))
            actor.set_folder_path('Main Plaza/Superseded')

        # ---- 4. marble paving: exactly 10000 x 10000 -------------------------
        cell_w = 2.0 * HALF / PAVING_COLS
        cell_d = 2.0 * HALF / PAVING_ROWS
        scale = unreal.Vector(cell_w / PAVING_MESH_W, cell_d / PAVING_MESH_D, 1.0)
        for i in range(PAVING_COLS):
            for j in range(PAVING_ROWS):
                place(meshes['paving'],
                      unreal.Vector(CX - HALF + (i + 0.5) * cell_w,
                                    CY - HALF + (j + 0.5) * cell_d, 0.0),
                      'PlazaPaving_%02d_%02d' % (i, j), 'Main Plaza/Paving',
                      scale=scale, extra_tags=(TAG + '.Paving',),
                      cast_shadow=False, forced_lod=PAVING_FORCED_LOD)
        counts['paving'] = PAVING_COLS * PAVING_ROWS

        # ---- 5. perimeter colonnade: square-base columns ---------------------
        spans = int(round(2.0 * COLONNADE_HALF / COLONNADE_BAY))       # 18 bays
        colonnade = 0
        for k in range(spans + 1):
            if k * COLONNADE_BAY == COLONNADE_HALF:      # remove the column inside each gate
                continue
            t = -COLONNADE_HALF + k * COLONNADE_BAY
            for side, x, y in (('N', CX + t, CY + COLONNADE_HALF),
                               ('S', CX + t, CY - COLONNADE_HALF)):
                place(meshes['square'], unreal.Vector(x, y, TOP),
                      'PlazaColumn_%s_%02d' % (side, k), 'Main Plaza/Colonnade',
                      extra_tags=(TAG + '.Colonnade',))
                colonnade += 1
            if 0 < k < spans:                            # corners belong to the N/S rows
                for side, x, y in (('W', CX - COLONNADE_HALF, CY + t),
                                   ('E', CX + COLONNADE_HALF, CY + t)):
                    place(meshes['square'], unreal.Vector(x, y, TOP),
                          'PlazaColumn_%s_%02d' % (side, k), 'Main Plaza/Colonnade',
                          extra_tags=(TAG + '.Colonnade',))
                    colonnade += 1
        counts['colonnade'] = colonnade

        # ---- 6. entablature beams -------------------------------------------
        # 5 beams per side keeps a beam CENTRED over each gateway, so the beam is still
        # carried by the columns either side of the opening instead of ending in mid air.
        span_ns = 2.0 * COLONNADE_HALF                       # 9000
        span_we = span_ns - ENTAB_DEPTH                      # 8924, butts the N/S beams
        beams = 0
        for side in ('S', 'N', 'W', 'E'):
            along_x = side in ('S', 'N')
            length = span_ns if along_x else span_we
            piece = length / ENTAB_PER_SIDE
            sc = unreal.Vector(piece / ENTAB_MESH_LEN, 1.0, 1.0)
            yaw = 0.0 if along_x else 90.0
            fixed = CY + (COLONNADE_HALF if side == 'N' else -COLONNADE_HALF) if along_x \
                else CX + (COLONNADE_HALF if side == 'E' else -COLONNADE_HALF)
            for i in range(ENTAB_PER_SIDE):
                t = -length / 2.0 + (i + 0.5) * piece
                loc = (unreal.Vector(CX + t, fixed, ENTAB_Z) if along_x
                       else unreal.Vector(fixed, CY + t, ENTAB_Z))
                place(meshes['entab'], loc, 'PlazaEntablature_%s_%02d' % (side, i),
                      'Main Plaza/Colonnade', yaw=yaw, scale=sc,
                      extra_tags=(TAG + '.Colonnade', TAG + '.Entablature'))
                beams += 1
        counts['entablature'] = beams

        # ---- 7. outermost low-post balustrade, gated at each midpoint --------
        posts = rails = 0
        for side in ('S', 'N', 'W', 'E'):
            along_x = side in ('S', 'N')
            fixed = CY + (BALUSTRADE_HALF if side == 'N' else -BALUSTRADE_HALF) if along_x \
                else CX + (BALUSTRADE_HALF if side == 'E' else -BALUSTRADE_HALF)
            p, r, _ = place_run('x' if along_x else 'y', fixed, BALUSTRADE_HALF,
                                0.0 if along_x else 90.0, 'Plaza%s' % side,
                                'Main Plaza/Balustrade', TAG + '.Balustrade',
                                gate_half=OUTER_GATE_HALF, skip_ends=not along_x)
            posts += p
            rails += r
        counts['baluster_posts'] = posts
        counts['baluster_rails'] = rails

        # ---- 8. inner precinct: low balustrade only (user decision 2026-09-23) ----
        # No Roman columns here any more: the 12 columns were replaced by balustrade, so the
        # positions they occupied now carry balusters again. The corner posts belong to the
        # x-side runs, so the y-side runs skip their endpoints to avoid placing them twice.
        prec_posts = prec_rails = prec_cols = 0
        for side, fixed in (('PW', CX - PRECINCT_HALF_X), ('PE', CX + PRECINCT_HALF_X)):
            p, r, c = place_run('y', fixed, PRECINCT_HALF_Y, 90.0, 'Precinct%s' % side,
                                'Main Plaza/Precinct', TAG + '.Precinct',
                                gate_half=PRECINCT_GATE_HALF_X)
            prec_posts += p
            prec_rails += r
            prec_cols += c
        for side, fixed in (('PS', CY - PRECINCT_HALF_Y), ('PN', CY + PRECINCT_HALF_Y)):
            p, r, c = place_run('x', fixed, PRECINCT_HALF_X, 0.0, 'Precinct%s' % side,
                                'Main Plaza/Precinct', TAG + '.Precinct',
                                skip_ts=(-PRECINCT_HALF_X, PRECINCT_HALF_X),
                                gate_half=PRECINCT_GATE_HALF_Y)
            prec_posts += p
            prec_rails += r
            prec_cols += c
        counts['precinct_posts'] = prec_posts
        counts['precinct_rails'] = prec_rails
        counts['precinct_columns'] = prec_cols

        # ---- 9. lift the whole pavilion onto the marble ----------------------
        pavilion = [a for a in api.get_all_level_actors()
                    if a.get_actor_label().startswith(PAVILION_PREFIX)]
        if not pavilion:
            raise RuntimeError('The main-map pavilion (%s*) is missing.' % PAVILION_PREFIX)
        lowest = min(bottom_z(a) for a in pavilion)
        shift = TOP - lowest
        if abs(shift) > 0.01:
            for a in pavilion:
                a.modify()
                loc = a.get_actor_location()
                a.set_actor_location(unreal.Vector(loc.x, loc.y, loc.z + shift), False, False)
        receipt['pavilion'] = dict(actors=len(pavilion), shift_cm=round(shift, 2),
                                   min_z_before=round(lowest, 2))

        # ---- 10. re-align the altar onto the axis ----------------------------
        altars = [a for a in api.get_all_level_actors() if ALTAR_TAG in tags_of(a)]
        if len(altars) > 1:
            raise RuntimeError('Multiple tagged altars exist; left them untouched.')
        if altars:
            altar = altars[0]
            before = vec(altar.get_actor_location())
            altar.modify()
            yaw = altar.get_actor_rotation().yaw
            loc = altar.get_actor_location()
            altar.set_actor_location(unreal.Vector(ALTAR_X, ALTAR_Y, loc.z), False, False)
            loc = altar.get_actor_location()
            altar.set_actor_location(
                unreal.Vector(loc.x, loc.y, loc.z + (TOP - bottom_z(altar))), False, False)
            receipt['moved'].append(dict(label=altar.get_actor_label(), kind='altar',
                                         from_cm=before, to_cm=vec(altar.get_actor_location()),
                                         yaw=yaw))

        # ---- 11. stand the fountain on the paving ----------------------------
        fountain = next((a for a in api.get_all_level_actors()
                         if a.get_actor_label() == FOUNTAIN_LABEL), None)
        if fountain is None:
            raise RuntimeError('The main-map fountain %s is missing.' % FOUNTAIN_LABEL)
        before = vec(fountain.get_actor_location())
        fountain.modify()
        loc = fountain.get_actor_location()
        fountain.set_actor_location(
            unreal.Vector(loc.x, loc.y, loc.z + (TOP - bottom_z(fountain))), False, False)
        receipt['moved'].append(dict(label=fountain.get_actor_label(), kind='fountain',
                                     from_cm=before, to_cm=vec(fountain.get_actor_location())))

        # ---- 12. verify before saving ---------------------------------------
        got = dict(paving=0, colonnade=0, entablature=0, balustrade=0, precinct=0)
        for actor in api.get_all_level_actors():
            tags = tags_of(actor)
            if TAG_GEN not in tags:
                continue
            if TAG + '.Paving' in tags:
                got['paving'] += 1
            elif TAG + '.Entablature' in tags:
                got['entablature'] += 1
            elif TAG + '.Colonnade' in tags:
                got['colonnade'] += 1
            elif TAG + '.Balustrade' in tags:
                got['balustrade'] += 1
            elif TAG + '.Precinct' in tags:
                got['precinct'] += 1
        expect = dict(paving=counts['paving'], colonnade=counts['colonnade'],
                      entablature=counts['entablature'],
                      balustrade=counts['baluster_posts'] + counts['baluster_rails'],
                      precinct=prec_posts + prec_rails + prec_cols)
        receipt['generated'] = counts
        receipt['verified_counts'] = got
        receipt['expected_counts'] = expect
        if got != expect:
            raise RuntimeError('Plaza verification failed: got %s, expected %s' % (got, expect))

        # Keep regeneration on the same bounded instancing path as the performance integration.
        import importlib.util
        instance_path = HERE.parent / 'MainScenePerformance20260923' / 'plaza_instances.py'
        instance_spec = importlib.util.spec_from_file_location('plaza_instance_builder', instance_path)
        instance_module = importlib.util.module_from_spec(instance_spec)
        instance_spec.loader.exec_module(instance_module)
        receipt['instancing'] = instance_module.apply()

        if not level.save_current_level():
            raise RuntimeError('Main map save failed; the editor placement was left intact.')
        receipt['saved'] = True
        receipt['runtime_tested'] = False
        receipt['switched_from'] = previous_map if switched else None

    if switched:
        if not level.load_level(previous_map):
            unreal.log_warning('Plaza saved; the previous editor map could not be restored: %s'
                               % previous_map)
    return receipt


try:
    result = main()
    (HERE / 'plaza_build_receipt.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PLAZA_OK ' + json.dumps(result['verified_counts']))
    print('PLAZA_PAVILION shift=%s actors=%s' % (result['pavilion']['shift_cm'],
                                                  result['pavilion']['actors']))
    print('PLAZA_REMOVED %d HIDDEN %d MOVED %d SAVED %s'
          % (len(result['registry_removed']), len(result['superseded']),
             len(result['moved']), result['saved']))
except Exception:
    (HERE / 'plaza_build_error.txt').write_text(traceback.format_exc(), encoding='utf-8')
    print('PLAZA_FAILED')
    raise
