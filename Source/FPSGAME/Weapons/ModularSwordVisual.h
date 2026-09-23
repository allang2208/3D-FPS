#pragma once
#include "CoreMinimal.h"
#include "GunsmithSystem.h"
class UStaticMeshComponent;

// Shared assembly contract for held, workbench, inventory and dropped swords.
namespace ColdSteelModularSword
{
    bool Supports(const FColdSteelItem& Item);
    FString ArmsMesh(const FColdSteelItem& Item);
    FString AnimationFolder(const FColdSteelItem& Item);
    void GatherVisualResources(const FColdSteelItem& Item,TArray<FSoftObjectPath>& Out,const FGunsmithParts* Draft=nullptr);
    FString Key(const FColdSteelItem& Item,const FGunsmithParts* Draft=nullptr,bool IncludeRune=true);
    bool Apply(UStaticMeshComponent* Blade,const FColdSteelItem& Item,const FGunsmithParts* Draft=nullptr,bool IncludeRune=true);
    void Clear(UStaticMeshComponent* Blade);
    TArray<UStaticMeshComponent*> Components(UStaticMeshComponent* Blade);
    FBox LocalBounds(UStaticMeshComponent* Blade);
    FTransform BoneMount(const FColdSteelItem& Item);
    FString Appearance(const FColdSteelItem& Item,const FString& Slot,const FString& Option);
    FVector BladePoint(const FColdSteelItem& Item,bool Tip);
}
