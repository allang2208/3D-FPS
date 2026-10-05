"""Export current nonhumanoid production meshes for continuous corpse authoring."""
from pathlib import Path
import json
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/MonsterSoftCorpse20261005')
DEST = '/Game/Monsters/SoftCorpseV1'
E = u.EditorAssetLibrary
TARGETS = {
    'PoisonMaggot': '/Game/Monsters/PoisonMaggot/BP_PoisonMaggot',
    'HandBrain': '/Game/Monsters/HandBrain/BP_HandBrain',
    'FleshHand': '/Game/Monsters/FleshHand/BP_FleshHand',
    'FleshHandMinion': '/Game/Monsters/FleshHand/BP_FleshHandMinion',
    'Wolf': '/Game/Monsters/Wolf/BP_WolfMonster',
    'ZombieDog': '/Game/Monsters/ZombieDog/V1/BP_ZombieDog',
    'InfectedDog': '/Game/Monsters/InfectedDog/BP_InfectedDog',
    'LurkerM08': '/Game/Monsters/LurkerM08/BP_LurkerM08',
    'HangingBellM09': '/Script/FPSGAME.HangingBellM09',
    'M10Mawcrawler': '/Game/Monsters/M10Mawcrawler/BP_M10Mawcrawler',
    'VortexCofferM25': '/Game/Monsters/VortexCofferM25/BP_VortexCofferM25',
}


def prop(obj, name):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return None


def save(asset):
    if not asset or not E.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ' + str(asset))


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    groups = {}
    for key, path in TARGETS.items():
        cls = u.load_class(None, path) if path.startswith('/Script/') else E.load_blueprint_class(path)
        if not cls:
            raise RuntimeError('Missing class ' + path)
        cdo = u.get_default_object(cls)
        animation_set = prop(cdo, 'animation_set')
        mesh = prop(cdo, 'visual_mesh') or (prop(animation_set, 'reference_mesh') if animation_set else None)
        if not mesh:
            mesh = cdo.get_component_by_class(u.SkeletalMeshComponent).get_skeletal_mesh_asset()
        if not mesh:
            raise RuntimeError('Missing live mesh ' + key)
        source_path = mesh.get_path_name()
        if source_path in groups:
            groups[source_path]['characters'].append(key)
            continue
        out = ROOT/key
        out.mkdir(parents=True, exist_ok=True)
        corpse_path = DEST+'/'+key+'/SK_'+key+'_SoftCorpse'
        corpse = u.load_asset(corpse_path) or E.duplicate_asset(source_path, corpse_path)
        # Never modify the living mesh's geometry. Remove only HandBrain's two
        # overlapping attack representations, hidden in its existing Death clip.
        omit = ['arm_mount', 'fan_mount'] if key == 'HandBrain' else []
        data = u.load_asset(DEST+'/'+key+'/DA_'+key+'_SoftCorpse')
        already_bound = data and data.get_editor_property('corpse_mesh') == corpse
        if already_bound:
            # Resuming this production batch must use the original export, not
            # reinterpret the appended soft bones as the source animation rig.
            if not (out/'surface.bin').exists():
                raise RuntimeError('Missing original export; author a new revision for '+key)
        else:
            if not u.M14SoftBodyData.export_surface(corpse, str(out/'surface.bin'), omit):
                raise RuntimeError('Surface export failed ' + key)
            save(corpse)
        groups[source_path] = dict(key=key, characters=[key], source=source_path,
            corpse=corpse_path, skeleton=mesh.skeleton.get_path_name(),
            omitted_attack_branches=omit, tested=False)
        print('SOFT_CORPSE_SOURCE ' + key, flush=True)
    (ROOT/'sources.json').write_text(json.dumps(list(groups.values()), indent=2)+'\n', encoding='utf8')


main()
