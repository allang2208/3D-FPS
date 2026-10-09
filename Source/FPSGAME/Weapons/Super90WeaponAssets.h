#pragma once
#include "CoreMinimal.h"

class USkeletalMeshComponent;

namespace Super90WeaponAssets
{
inline constexpr const TCHAR* Definition=TEXT("ue_super90");
inline constexpr const TCHAR* MeshPath=TEXT("/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7.SK_Super90_V7");
inline constexpr const TCHAR* LooseShellMaterial=TEXT("12gauge");
// The source rig parks its reload cartridge below the gun outside feed clips.
void SetLooseShellVisible(USkeletalMeshComponent* Mesh,bool bVisible);
inline constexpr int32 PelletCount=8;
inline constexpr float PelletConeDegrees=2.5f;
inline constexpr float SingleReload=99.f/60.f;
inline constexpr float FullReload=424.f/60.f;
inline constexpr float Insert=44.f/60.f;
inline constexpr float LoopStep=50.f/60.f;
inline constexpr float TailBegin=6.f;
inline constexpr float BoltRelease=6.25f;
inline FString AnimationPath(const TCHAR* Kind)
{
    return FString::Printf(TEXT("/Game/Weapons/Super90/Cransh20261006/Animations/A_Super90_%s.A_Super90_%s"),Kind,Kind);
}
inline float TailForCount(int32 Count){return Count>0?1.f+(Count-1)*LoopStep:0.f;}
inline FString SprintAnimationPath(const TCHAR* Kind)
{
    const FString Name=FString::Printf(TEXT("A_Super90_sprint_%s"),Kind);
    return TEXT("/Game/Weapons/Super90/TacticalSprint20261007/Animations/")+Name+TEXT(".")+Name;
}
}
