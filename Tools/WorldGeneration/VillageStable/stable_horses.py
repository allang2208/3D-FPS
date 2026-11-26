"""Clean up legacy static stall horses; runtime daily market horses are now spawned dynamically
across the 4 stalls and open paddock by UStableMarketShowcaseSubsystem with summon fade-in/out."""
import unreal as ue
from stable_actors import ASSEMBLY

TAG = 'VillageStable.Horses'


def remove_legacy_static_horses(actors):
    removed = []
    for actor in list(actors.get_all_level_actors()):
        tags = set(map(str, actor.tags))
        lbl = actor.get_actor_label()
        if TAG in tags or lbl.startswith('Village_Stable_Horse_Stall'):
            removed.append(lbl)
            actors.destroy_actor(actor)
    return removed


def install_horses(actors, upgrade_placed=False):
    removed = remove_legacy_static_horses(actors)
    return dict(
        scope='horses_dynamic_showcase',
        removed_legacy_static_horses=removed,
        horses=[],
        note='Daily market horses are dynamically placed in stalls & paddock by UStableMarketShowcaseSubsystem.',
    )
