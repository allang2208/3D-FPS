#pragma once
#include "CoreMinimal.h"
#include "Super90ReleaseTiming.h"

class USkeletalMeshComponent;

namespace Super90WeaponAssets
{
inline constexpr const TCHAR* Definition=TEXT("ue_super90");
inline constexpr const TCHAR* MeshPath=TEXT("/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7.SK_Super90_V7");
inline constexpr const TCHAR* LooseShellMaterial=TEXT("12gauge");
// The source rig parks its reload cartridge below the gun outside feed clips.
void SetLooseShellVisible(USkeletalMeshComponent* Mesh,bool bVisible);
inline constexpr int32 PelletCount=8;
inline constexpr float PelletConeDegrees=3.0f; // 2026-10-19: 3.75 x 0.8; Saiga/M870/Super90 all share this cone.
inline constexpr float ADSPelletSpreadScale=.75f;
inline constexpr double MinimumAttackInterval=0.060;
inline constexpr float SingleReload=99.f/60.f;
// Cransh's native full reload reference; keep established shell-feed speed
// and speedloader stat conversion unchanged.
inline constexpr float FullReload=424.f/60.f;
inline constexpr float Insert=44.f/60.f;
inline constexpr float LoopStep=50.f/60.f;
inline constexpr float TailBegin=6.f;
// Ordinary empty and interrupted continuation both press the bolt release.
inline constexpr float CycleBoltReleaseCue=Super90ReleaseTiming::CycleClosed;
inline constexpr float CycleBoltReady=Super90ReleaseTiming::CycleClosed;
inline constexpr float NativeBoltReleaseCue=374.f/60.f;
inline constexpr float BoltRelease=374.f/60.f;
inline FString AnimationPath(const TCHAR* Kind)
{
    return FString::Printf(TEXT("/Game/Weapons/Super90/Cransh20261006/Animations/A_Super90_%s.A_Super90_%s"),Kind,Kind);
}
inline float TailForCount(int32 Count){return Count>0?1.f+(Count-1)*LoopStep:0.f;}
// Preserve the native return/bolt tail while repeating its final shell loop
// when a larger tube requires more than the authored seven feed contacts.
inline float FeedClipTime(float Time,float Tail,float Length)
{
    if(Time>=Tail)return FMath::Min(Length,TailBegin+Time-Tail);
    if(Time>=TailBegin)return TailBegin-LoopStep+FMath::Fmod(Time-TailBegin,LoopStep);
    return FMath::Min(Time,Length);
}
inline FString SprintAnimationPath(const TCHAR* Kind)
{
    const FString Name=FString::Printf(TEXT("A_Super90_sprint_%s"),Kind);
    return TEXT("/Game/Weapons/Super90/TacticalSprint20261007/Animations/")+Name+TEXT(".")+Name;
}
}
