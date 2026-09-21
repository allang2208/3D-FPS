#include "ColdSteelPickup.h"
#include "../Weapons/MeleeRuneVisual.h"
#include "../Weapons/MeleeGuardAssets.h"
#include "../Weapons/ModularSwordVisual.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"

bool AColdSteelPickup::BuildConsumable(const FColdSteelItem& Item)
{
    const FString& Id=Item.Definition;
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
        ColdSteelMeleeRune::Apply(Mesh,ColdSteelMeleeRune::Selected(Item));
        Body->SetBoxExtent(Bounds.BoxExtent.ComponentMax(FVector(1)));
        return true;
    }
    const bool bMaterial=Id==TEXT("enhancement_stone")||Id==TEXT("magic_dust");
    const bool bScroll=Id==TEXT("enchant_scroll_heavy")||Id==TEXT("enchant_scroll_sharp")||Id==TEXT("enchant_scroll_skeleton")||Id==TEXT("enchant_scroll_tarantula");
    if(!bMaterial&&!bScroll&&Id!=TEXT("hp_potion")&&Id!=TEXT("mp_potion"))return false;
    const FString Path=bScroll?TEXT("/Game/Items/MagicScroll/magic_scroll/SM_magic_scroll.SM_magic_scroll"):FString::Printf(TEXT("/Game/Items/%s/%s/SM_%s.SM_%s"),bMaterial?TEXT("EnhancementMaterials"):TEXT("Consumables"),*Id,*Id,*Id);
    auto* Asset=LoadObject<UStaticMesh>(nullptr,*Path);
    if(!Asset){UE_LOG(LogTemp,Error,TEXT("ConsumablePickup: missing %s"),*Path);return false;}
    const FBoxSphereBounds Bounds=Asset->GetBounds();
    const float Height=bScroll?24.f:Id==TEXT("enhancement_stone")?14.f:Id==TEXT("magic_dust")?16.f:Id==TEXT("hp_potion")?18.f:18.5f;
    const float Scale=Height/FMath::Max(2.f*Bounds.BoxExtent.Z,.01f);
    Mesh->SetStaticMesh(Asset);Mesh->SetRelativeScale3D(FVector(Scale));Mesh->SetRelativeLocation(-Bounds.Origin*Scale);
    Body->SetBoxExtent((Bounds.BoxExtent*Scale).ComponentMax(FVector(1.f)));
    UE_LOG(LogTemp,Display,TEXT("ConsumablePickup: %s mesh=%s extent=%s"),*Id,*Path,*Body->GetUnscaledBoxExtent().ToString());
    return true;
}
