#include "ColdSteelPickup.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"

bool AColdSteelPickup::BuildConsumable(const FColdSteelItem& Item)
{
    const FString& Id=Item.Definition;
    const bool bMaterial=Id==TEXT("enhancement_stone")||Id==TEXT("magic_dust");
    const bool bScroll=Id==TEXT("enchant_scroll_heavy")||Id==TEXT("enchant_scroll_sharp")||Id==TEXT("enchant_scroll_skeleton")||Id==TEXT("enchant_scroll_tarantula");
    if(!bMaterial&&!bScroll&&Id!=TEXT("hp_potion")&&Id!=TEXT("mp_potion")&&Id!=TEXT("ammo_556")&&Id!=TEXT("ammo_762"))return false;
    const FString Path=bScroll?TEXT("/Game/Items/MagicScroll/magic_scroll/SM_magic_scroll.SM_magic_scroll"):FString::Printf(TEXT("/Game/Items/%s/%s/SM_%s.SM_%s"),bMaterial?TEXT("EnhancementMaterials"):TEXT("Consumables"),*Id,*Id,*Id);
    auto* Asset=LoadObject<UStaticMesh>(nullptr,*Path);
    if(!Asset){UE_LOG(LogTemp,Error,TEXT("ConsumablePickup: missing %s"),*Path);return false;}
    const FBoxSphereBounds Bounds=Asset->GetBounds();
    const float Height=bScroll?24.f:Id==TEXT("enhancement_stone")?14.f:Id==TEXT("magic_dust")?16.f:Id==TEXT("hp_potion")?18.f:Id==TEXT("mp_potion")?18.5f:Id==TEXT("ammo_556")?12.f:13.f;
    const float Scale=Height/FMath::Max(2.f*Bounds.BoxExtent.Z,.01f);
    Mesh->SetStaticMesh(Asset);Mesh->SetRelativeScale3D(FVector(Scale));Mesh->SetRelativeLocation(-Bounds.Origin*Scale);
    Body->SetBoxExtent((Bounds.BoxExtent*Scale).ComponentMax(FVector(1.f)));
    UE_LOG(LogTemp,Display,TEXT("ConsumablePickup: %s mesh=%s extent=%s"),*Id,*Path,*Body->GetUnscaledBoxExtent().ToString());
    return true;
}
