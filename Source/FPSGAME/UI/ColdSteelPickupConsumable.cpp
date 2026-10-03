#include "ColdSteelPickup.h"
#include "../Items/PotionVisuals.h"
#include "../Weapons/MeleeRuneVisual.h"
#include "../Weapons/MeleeGuardAssets.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Weapons/Staff/StaffCatalog.h"
#include "../Weapons/Staff/StaffAssembly.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"

bool AColdSteelPickup::BuildConsumable(const FColdSteelItem& Item)
{
    const FString& Id=Item.Definition;
    if(ColdSteelStaff::IsStaff(Item))
    {
        return BuildStaff(Item);
    }
    if(ColdSteelInventory::Text(Item,TEXT("category"))==TEXT("equipment"))
    {
        const FString Path=ColdSteelInventory::Text(Item,TEXT("world_mesh"));
        if(auto* Asset=Path.IsEmpty()?nullptr:LoadObject<UStaticMesh>(nullptr,*Path))
        {
            const auto Bounds=Asset->GetBounds();
            Mesh->SetStaticMesh(Asset);Mesh->SetRelativeScale3D(FVector(1));Mesh->SetRelativeLocation(-Bounds.Origin);
            const FString MaterialPath=ColdSteelInventory::Text(Item,TEXT("world_material"));
            if(!MaterialPath.IsEmpty())if(auto* Material=LoadObject<UMaterialInterface>(nullptr,*MaterialPath))
                for(int32 Slot=0;Slot<Mesh->GetNumMaterials();++Slot)Mesh->SetMaterial(Slot,Material);
            Body->SetBoxExtent(Bounds.BoxExtent.ComponentMax(FVector(1.f)));
            return true;
        }
        return false;
    }
    if(ColdSteelInventory::IsMeleeWeapon(Item))
    {
        if(ColdSteelModularSword::Supports(Item))
        {
            Mesh->SetRelativeScale3D(FVector(1));
            if(!ColdSteelModularSword::Apply(Mesh,Item))return false;
            const FBox Bounds=ColdSteelModularSword::LocalBounds(Mesh);
            Mesh->SetRelativeLocation(-Bounds.GetCenter());Body->SetBoxExtent(Bounds.GetExtent().ComponentMax(FVector(1)));
            return true;
        }
        auto* Asset=LoadObject<UStaticMesh>(nullptr,*ColdSteelMeleeGuard::WorldMesh(Item));
        if(!Asset)return false;
        const auto Bounds=Asset->GetBounds();
        Mesh->SetStaticMesh(Asset);Mesh->SetRelativeScale3D(FVector(1));Mesh->SetRelativeLocation(-Bounds.Origin);
        ColdSteelMeleeRune::Apply(Mesh,ColdSteelMeleeRune::Selected(Item),Item.Definition);
        Body->SetBoxExtent(Bounds.BoxExtent.ComponentMax(FVector(1)));
        return true;
    }
    if(Id==TEXT("baguette_bread")||Id==TEXT("bread")||Id==TEXT("soda_can"))
    {
        auto* Asset=LoadObject<UStaticMesh>(nullptr,*ColdSteelInventory::Text(Item,TEXT("world_mesh")));
        if(!Asset)return false;
        const auto Bounds=Asset->GetBounds();
        Mesh->EmptyOverrideMaterials();Mesh->SetStaticMesh(Asset);
        Mesh->SetRelativeScale3D(FVector(1));Mesh->SetRelativeLocation(-Bounds.Origin);
        Body->SetBoxExtent(Bounds.BoxExtent.ComponentMax(FVector(1)));
        return true;
    }
    const bool bMaterial=Id==TEXT("enhancement_stone")||Id==TEXT("magic_dust");
    const bool bScroll=Id.StartsWith(TEXT("enchant_scroll_"));
    const bool bHealthPotion=Id==TEXT("hp_potion")||Id.StartsWith(TEXT("hp_potion_"));
    const bool bManaPotion=Id==TEXT("mp_potion")||Id.StartsWith(TEXT("mp_potion_"));
    const bool bWater=Id==TEXT("mineral_water");
    if(bHealthPotion||bManaPotion||bWater)
    {
        const int32 TierIndex=PotionVisuals::FindTier(Id);
        if(TierIndex==INDEX_NONE)return false;
        const auto& Visual=PotionVisuals::Tiers()[TierIndex];
        const FString& Closed=bWater&&ColdSteelInventory::Number(Item,TEXT("remainingUses"),2)==1&&!Visual.HalfClosed.IsEmpty()?Visual.HalfClosed:Visual.Closed;
        auto* Asset=LoadObject<UStaticMesh>(nullptr,*Closed);
        auto* LiquidMaterial=LoadObject<UMaterialInterface>(nullptr,*(Visual.LiquidMaterial.IsEmpty()?PotionVisuals::LiquidMaterial(bManaPotion):Visual.LiquidMaterial));
        if(!Asset||!LiquidMaterial)return false;
        const auto Bounds=Asset->GetBounds();
        const float Scale=Visual.HeightCm/FMath::Max(2.f*Bounds.BoxExtent.Z,.01f);
        Mesh->EmptyOverrideMaterials();Mesh->SetStaticMesh(Asset);
        const int32 LiquidSlot=Mesh->GetMaterialIndex(TEXT("Liquid"));
        if(LiquidSlot!=INDEX_NONE)Mesh->SetMaterial(LiquidSlot,LiquidMaterial);
        Mesh->SetRelativeScale3D(FVector(Scale));Mesh->SetRelativeLocation(-Bounds.Origin*Scale);
        Body->SetBoxExtent((Bounds.BoxExtent*Scale).ComponentMax(FVector(1.f)));
        return true;
    }
    if(!bMaterial&&!bScroll)return false;
    const FString Path=bScroll?TEXT("/Game/Items/MagicScroll/magic_scroll/SM_magic_scroll.SM_magic_scroll"):FString::Printf(TEXT("/Game/Items/EnhancementMaterials/%s/SM_%s.SM_%s"),*Id,*Id,*Id);
    auto* Asset=LoadObject<UStaticMesh>(nullptr,*Path);
    if(!Asset){UE_LOG(LogTemp,Error,TEXT("ConsumablePickup: missing %s"),*Path);return false;}
    const FBoxSphereBounds Bounds=Asset->GetBounds();
    const float Height=bScroll?24.f:Id==TEXT("enhancement_stone")?14.f:16.f;
    const float Scale=Height/FMath::Max(2.f*Bounds.BoxExtent.Z,.01f);
    Mesh->SetStaticMesh(Asset);Mesh->SetRelativeScale3D(FVector(Scale));Mesh->SetRelativeLocation(-Bounds.Origin*Scale);
    Body->SetBoxExtent((Bounds.BoxExtent*Scale).ComponentMax(FVector(1.f)));
    UE_LOG(LogTemp,Display,TEXT("ConsumablePickup: %s mesh=%s extent=%s"),*Id,*Path,*Body->GetUnscaledBoxExtent().ToString());
    return true;
}
