#include "MeleeGuardAssets.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "Serialization/JsonSerializer.h"

FString ColdSteelMeleeGuard::Selected(const FColdSteelItem& Item,const FGunsmithParts* Preview)
{
    if(Item.Definition!=TEXT("ue_frost_crystal_sword"))return {};
    FString Id;
    if(Preview)Id=Preview->FindRef(TEXT("guard"));
    else
    {
        TSharedPtr<FJsonObject> Data;const TSharedPtr<FJsonObject>* Parts=nullptr;
        if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)&&Data&&Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts))
            (*Parts)->TryGetStringField(TEXT("guard"),Id);
    }
    return Id==TEXT("bastion_guard")||Id==TEXT("riposte_guard")||Id==TEXT("light_guard")?Id:FString();
}

FString ColdSteelMeleeGuard::WorldMesh(const FColdSteelItem& Item,const FGunsmithParts* Preview)
{
    const FString Id=Selected(Item,Preview);
    return Id.IsEmpty()?ColdSteelInventory::Text(Item,TEXT("world_mesh")):
        TEXT("/Game/Weapons/FrostCrystalSword20260915/GuardsSmooth20260915/")+Id+TEXT("/SM_FrostCrystalSword_")+Id;
}

FString ColdSteelMeleeGuard::Viewmodel(const FColdSteelItem& Item)
{
    const FString Id=Selected(Item);
    return Id.IsEmpty()?ColdSteelInventory::Text(Item,TEXT("viewmodel_mesh")):
        TEXT("/Game/Weapons/FrostCrystalSword20260915/GuardsSmooth20260915/")+Id+TEXT("/SK_FrostCrystalSword_")+Id;
}
