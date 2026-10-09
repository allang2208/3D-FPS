#pragma once
#include "CoreMinimal.h"
class USkeletalMeshComponent;
namespace Super90OpticAssets
{
inline bool Supports(const FString& V){return V==TEXT("holographic")||V==TEXT("eoth_holographic")||V==TEXT("panoramic_red_dot")||V==TEXT("prism_scope_2x")||V==TEXT("lpvo_1_6x");}
inline FString MeshPath(const FString& V){return TEXT("/Game/Weapons/Super90/Optics20261007/Meshes/SM_Super90_")+V;}
FTransform RailMount(const USkeletalMeshComponent* Host);
FTransform OpticMount(const USkeletalMeshComponent* Host,const FString& Variant);
void FactorySights(USkeletalMeshComponent* Host,bool Visible);
}
