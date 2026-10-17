#pragma once
#include "CoreMinimal.h"

class USkeletalMeshComponent;
namespace M870OpticAssets
{
inline bool Supports(const FString& Variant)
{
    return Variant==TEXT("holographic") || Variant==TEXT("eoth_holographic") ||
        Variant==TEXT("panoramic_red_dot") || Variant==TEXT("prism_scope_2x") ||
        Variant==TEXT("lpvo_1_6x") || Variant==TEXT("thermal_scope");
}
inline FString MeshPath(const FString& Variant)
{ return TEXT("/Game/Weapons/M870/Optics20261016/Meshes/SM_M870_")+Variant; }
inline FString SeatPath(const FString& Variant)
{ return MeshPath(TEXT("OpticSeat_")+Variant); }
FTransform RailMount(const USkeletalMeshComponent* Host);
FTransform OpticMount(const USkeletalMeshComponent* Host,const FString& Variant);
}
