#pragma once
#include "ColdSteelInventoryTypes.h"
#include "../Characters/FPSPlayerBodyTypes.h"

// An authored display mesh can retain the wearable proportions while a pickup
// uses a flattened resting pose. Existing rigid attachments keep their source.
inline FSoftObjectPath ColdSteelEquipmentIconMesh(const FColdSteelItem& Item)
{
    const FString Path=ColdSteelInventory::Text(Item,TEXT("ue_equipment_icon_mesh"));
    return Path.IsEmpty()?FPSBodyEquipment::StaticOutfitMesh(Item.Definition):FSoftObjectPath(Path);
}
