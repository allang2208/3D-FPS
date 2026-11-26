"""Read the actual PIE pawn, including native private fields through UE reflection."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
OUT=ROOT/'SourceAssets/IceArmor20261017/RuntimeVisibilityV4';OUT.mkdir(parents=True,exist_ok=True)
def props(obj,names):return json.loads(u.ToolsetLibrary.get_object_properties(obj,names))
def path(obj):return obj.get_path_name() if obj else None
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
p=u.GameplayStatics.get_player_character(w,0) if w else None
data={'world':path(w),'pawn':path(p)}
if p:
    ice=p.get_component_by_class(u.FPSIceArmorComponent)
    u.SystemLibrary.execute_console_command(w,'obj dump '+ice.get_path_name())
    data['ice_property_list']=u.ToolsetLibrary.list_struct_properties(ice.get_class())
    data['ice']=props(ice,['State','ShellMeshes','LensMesh','ArmorMaterial','LensMaterial','ArmorMID','LensMID','BodyShells','Lens','Mist'])
    data['components']=[]
    for c in p.get_components_by_class(u.SceneComponent):
        if isinstance(c,u.CameraComponent) or isinstance(c,u.MeshComponent):
            row={'path':path(c),'class':c.get_class().get_name(),'props':props(c,['bVisible','bHiddenInGame','RelativeLocation','RelativeRotation','RelativeScale3D','AttachParent'])}
            if isinstance(c,u.MeshComponent):
                row['materials']=[path(c.get_material(i)) for i in range(c.get_num_materials())]
                row['render']=props(c,['bOnlyOwnerSee','bOwnerNoSee','bRenderInMainPass','FirstPersonPrimitiveType','StaticMesh','SkeletalMeshAsset','LeaderPoseComponent'])
            data['components'].append(row)
(OUT/'runtime-initial.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('ICE_RUNTIME_INITIAL '+json.dumps(data,ensure_ascii=False),flush=True)
