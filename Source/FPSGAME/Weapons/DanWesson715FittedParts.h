#pragma once
#include "CoreMinimal.h"

class AActor;
class USkeletalMeshComponent;
class UStaticMeshComponent;

namespace DanWesson715FittedParts
{
    inline constexpr const TCHAR* RubberGrip = TEXT("dw715_rubber_grip");
    inline constexpr const TCHAR* TargetGrip = TEXT("dw715_target_wood_grip");
    inline constexpr const TCHAR* CompactGrip = TEXT("dw715_compact_grip");
    inline constexpr const TCHAR* Brake = TEXT("dw715_muzzle_brake");
    inline constexpr const TCHAR* CompactCompensator = TEXT("dw715_compact_compensator");
    inline constexpr const TCHAR* TargetMuzzleWeight = TEXT("dw715_target_muzzle_weight");
    inline constexpr const TCHAR* WetMaterials = TEXT("/Game/Weapons/DanWesson715/GripBrake20260927/DA_DW715_GripBrakeWetMaterials");
    inline constexpr const TCHAR* CompactWetMaterials = TEXT("/Game/Weapons/DanWesson715/CompactScope20260927/DA_DW715_CompactScopeWetMaterials");
    inline bool IsGrip(const FString& Part) { return Part == RubberGrip || Part == TargetGrip || Part == CompactGrip; }
    inline bool IsMuzzle(const FString& Part) { return Part == Brake || Part == CompactCompensator || Part == TargetMuzzleWeight; }
    inline bool Supports(const FString& Part) { return IsGrip(Part) || IsMuzzle(Part); }
    inline FString MeshPath(const FString& Part)
    {
        if (Part == CompactGrip) return TEXT("/Game/Weapons/DanWesson715/CompactScope20260927/Meshes/SM_dw715_compact_grip");
        if (Part == CompactCompensator) return TEXT("/Game/Weapons/DanWesson715/MuzzleModels20260927/Meshes/SM_dw715_compact_compensator");
        if (Part == TargetMuzzleWeight) return TEXT("/Game/Weapons/DanWesson715/MuzzleModels20260927/Meshes/SM_dw715_target_muzzle_weight");
        return TEXT("/Game/Weapons/DanWesson715/GripBrake20260927/Meshes/SM_") + Part;
    }
    inline FVector MuzzleTip(const FString& Part)
    {
        // Authored muzzle exit in mesh-local centimetres; shared by both hands and FX.
        if (Part == CompactCompensator) return FVector(1.95f, 0.f, 0.f);
        if (Part == TargetMuzzleWeight) return FVector(1.17f, 0.f, 0.f);
        return Part == Brake ? FVector(3.4f, 0.f, 0.f) : FVector::ZeroVector;
    }
    // Same section operation is used by the right hand and the independent left-hand rig.
    void ShowFactoryGrip(USkeletalMeshComponent* Host, bool bVisible);
    UStaticMeshComponent* Configure(AActor* Owner, USkeletalMeshComponent* Host,
        UStaticMeshComponent* Existing, const FString& Part, bool bEnabled, bool bMuzzle);
}
