"""Resources used by village fixtures with the apprentice staff's illumination."""
import unreal as u

FOLDER = '/Game/WorldGeneration/TemperateHills/ShopLighting/'
WICK = FOLDER+'MI_StaffLampWick'
TORCH_CARD = FOLDER+'M_StaffTorchCard'
HEARTH_FIRE = FOLDER+'NS_StaffHearthFire'
TORCH_FIRE = FOLDER+'NS_StaffTorchFire'
EMBER = FOLDER+'M_StaffHearthEmber'


def configure(light):
    u.VillageInteriorLighting.configure(light, 1.)


def apply_embers(component):
    for slot in range(component.get_num_materials()):
        material = component.get_material(slot)
        if material and material.get_name() == 'M_TavernHearthEmber':
            ember = u.EditorAssetLibrary.load_asset(EMBER)
            if not ember:
                raise RuntimeError('Missing '+EMBER)
            component.set_material(slot,ember)

