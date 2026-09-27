#pragma once
#include "CoreMinimal.h"

class AActor;
class FJsonObject;
class USkeletalMeshComponent;
class UStaticMeshComponent;
struct FGunsmithWeapon;

namespace PistolGripSurface
{
    inline constexpr const TCHAR* WetMaterialsPath = TEXT("/Game/Weapons/PistolGripSurface20260927/DA_PistolGripSurfaceWetMaterials");
    bool IsPart(const FString& Part);
    bool Supports(const FGunsmithWeapon* Weapon);
    FString MeshPath(const FGunsmithWeapon* Weapon);
    FString MaterialPath(const FString& Part);
    void MergeOptions(const TSharedPtr<FJsonObject>& Catalog, const TSharedPtr<FJsonObject>& Weapon,
        TArray<FString>& Allowed);
    UStaticMeshComponent* Configure(AActor* Owner, USkeletalMeshComponent* Host,
        UStaticMeshComponent* Existing, const FGunsmithWeapon* Weapon, const FString& Part, bool bEnabled);
}
