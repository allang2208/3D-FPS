import unreal as u

les = u.get_editor_subsystem(u.UnrealEditorSubsystem)
cur = les.get_editor_world() if les else None
if cur is not None:
    print('ABORT world-already-open %s' % cur.get_name())
    raise SystemExit(1)

u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/DayNight_Lighting')
world = les.get_editor_world()
if world is None:
    print('ABORT load-failed')
    raise SystemExit(1)
print('LOADED %s' % world.get_name())

BASE = u.Vector(0, 0, 50000)
TREE = u.load_object(None, '/Script/FPSGAME.ProductionFallingTree')
CLASSES = (u.DirectionalLight, u.SkyLight, u.SceneCapture2D, u.StaticMeshActor, TREE)


def count_near():
    n = 0
    for cls in CLASSES:
        for a in u.GameplayStatics.get_all_actors_of_class(world, cls):
            if (a.get_actor_location() - BASE).length() < 20000:
                n += 1
    return n


before = count_near()
print('BEFORE %d' % before)
for cls in CLASSES:
    for a in list(u.GameplayStatics.get_all_actors_of_class(world, cls)):
        if (a.get_actor_location() - BASE).length() < 20000:
            a.destroy_actor()
left = count_near()
print('LEFT %d' % left)
if left != 0:
    print('ABORT sweep-incomplete')
    raise SystemExit(1)
ok = u.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
print('SAVED %s' % bool(ok))

# 重载复核：文件里应当一个不剩
u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/DayNight_Lighting')
world = les.get_editor_world()
after = count_near()
print('VERIFY-RELOAD %d' % after)
print('RESULT %s' % ('CLEAN' if after == 0 else 'STILL-DIRTY'))
