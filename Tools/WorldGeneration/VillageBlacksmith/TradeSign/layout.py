"""Shared placements in the existing blacksmith's floor coordinates, in centimetres."""
from author_shop import pose,require

ROOT='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/TradeSign'
OLD_SIGN='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/DetailR6/Meshes/SM_SmithLoft_BlacksmithSign_R6'
OLD_CRATE='/Game/UndergroundTunnel/Meshes/Props/SM_WoodCrate01a'
SIGN=ROOT+'/SM_SmithTradeSign'
RACK=ROOT+'/SM_SmithTongStand'
PACKING=ROOT+'/SM_SmithWheelAndCases'

def placements(house):
    # The bracket's wall plate is at mesh origin. Resolve its outward vector
    # from the imported asymmetric arm before composing the house transform.
    bounds=require(SIGN).get_bounding_box()
    cx=(bounds.max.x+bounds.min.x)*.5
    cy=(bounds.max.y+bounds.min.y)*.5
    if abs(cy)>abs(cx):align=0 if cy<0 else 180
    else:align=90 if cx<0 else -90
    return [('Common',SIGN,pose(house,4,-401.5,321,align),'NoCollision'),
            ('Repaired',RACK,pose(house,-42,267,0,align-5),'BlockAll'),
            ('Repaired',PACKING,pose(house,282,-309,0,align-3),'BlockAll')]
