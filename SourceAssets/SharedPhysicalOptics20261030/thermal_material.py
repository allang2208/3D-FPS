"""Install the terrain inputs used by the physical lens thermal pass."""
from pathlib import Path
import unreal as u


def configure(material):
    edit=u.MaterialEditingLibrary
    image=edit.get_material_property_input_node(material,u.MaterialProperty.MP_EMISSIVE_COLOR)
    if not isinstance(image,u.MaterialExpressionCustom):
        raise RuntimeError('Missing thermal post-process shader on '+material.get_path_name())
    pins=list(image.get_editor_property('inputs'))
    names={str(pin.get_editor_property('input_name')) for pin in pins}
    missing=[(name,scene_id) for name,scene_id in (('TerrainBase',u.SceneTextureId.PPI_BASE_COLOR),
             ('TerrainNormal',u.SceneTextureId.PPI_WORLD_NORMAL)) if name not in names]
    for name,_ in missing:
        pin=u.CustomInput()
        pin.set_editor_property('input_name',name)
        pins.append(pin)
    if missing:
        image.set_editor_property('inputs',pins)
    for name,scene_id in missing:
        node=edit.create_material_expression(material,u.MaterialExpressionSceneTexture)
        node.set_editor_properties(dict(scene_texture_id=scene_id,filtered=False))
        if not edit.connect_material_expressions(node,'Color',image,name):
            raise RuntimeError('Could not connect '+name)
    image.set_editor_property('code',Path(__file__).with_name('thermal_scene.hlsl').read_text('utf8'))
    image.set_editor_property('desc','Thermal screen: cold surface relief, white-hot creatures and amber fire')
