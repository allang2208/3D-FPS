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
    FString Key(const FColdSteelItem& Item,const FGunsmithParts* Draft=nullptr,bool IncludeRune=true);
    bool Apply(UStaticMeshComponent* Blade,const FColdSteelItem& Item,const FGunsmithParts* Draft=nullptr,bool IncludeRune=true);
    void Clear(UStaticMeshComponent* Blade);
    TArray<UStaticMeshComponent*> Components(UStaticMeshComponent* Blade);
    FBox LocalBounds(UStaticMeshComponent* Blade);
    FTransform BoneMount();
    FVector BladePoint(const FColdSteelItem& Item,bool Tip);
}
