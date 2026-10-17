#pragma once
#include "CoreMinimal.h"
#include "Super90ReleaseTiming.h"
#include "Super90LoaderPushTiming.h"
#include "M870WeaponAssets.h"

// M870 uses the same physical loader (one gunsmith id) and the R27 source
// timeline frame for frame: same rig, idle gun placement, contacts and push
// clock (SourceAssets/M870Speedloader20261016/author_clips.py). Only the empty
// tail differs: regrip the pump, then the M870 standalone pump cycle.
namespace M870LoaderTiming
{
inline constexpr float CycleStart=144.f/60.f;
inline constexpr float PullCue=CycleStart+.12f;
inline constexpr float ReleaseCue=CycleStart+M870WeaponAssets::PumpPush;
inline constexpr float Eject=CycleStart+M870WeaponAssets::PumpEject;
inline constexpr float Closed=CycleStart+M870WeaponAssets::PumpClosed;
inline constexpr float End=208.f/60.f;
inline constexpr const TCHAR* Guide=TEXT("/Game/Weapons/M870/Speedloader20261016/SM_M870_LoaderGuide.SM_M870_LoaderGuide");
}

namespace Super90SpeedloaderAssets
{
inline constexpr const TCHAR* Id=TEXT("super90_tube_loader");
inline constexpr const TCHAR* Guide=TEXT("/Game/Weapons/Super90/Speedloader20261007/SM_Super90_LoaderGuide.SM_Super90_LoaderGuide");
inline constexpr const TCHAR* Props=TEXT("/Game/Weapons/Super90/Speedloader20261007/SK_Super90_LoaderProps.SK_Super90_LoaderProps");
inline constexpr int32 Capacity=7;
// Native 60 Hz source clock; gameplay rate includes the installed loader modifier.
// R16: the complete R15 drive is compressed 36 -> 24 frames, with a quicker
// initial hand release. Contacts use the same mapping as pose and grip tracks.
inline constexpr float Contacts[]={90.f/60.f,93.397242f/60.f,96.529458f/60.f,
    99.468221f/60.f,102.596790f/60.f,106.f/60.f,110.f/60.f};
inline constexpr float Insert=Contacts[0];
inline constexpr float Dock=87.012105f/60.f;
inline constexpr float NormalReference=144.f/60.f;
inline constexpr float EmptyReference=Super90ReleaseTiming::End;
// Stats and playback rate share the full paced duration, including the push extension.
inline constexpr float NormalPacedReference=NormalReference+Super90LoaderPushTiming::ExtraDuration;
inline constexpr float EmptyPacedReference=EmptyReference+Super90LoaderPushTiming::ExtraDuration;
inline constexpr float PropsVisibleBegin=74.f/60.f;
inline float FirstContact(int32 Count){return Contacts[Capacity-FMath::Clamp(Count,1,Capacity)];}
inline float LastContact(int32 Count){return Contacts[Capacity-1];}
// StartContact is captured at action start so a cancel cannot shift the shell
// clock after reducing the target count. The source path itself stays intact.
inline float FeedContact(float StartContact,int32 Index)
{
    int32 First=0;
    while(First<Capacity-1&&Contacts[First]<StartContact-.0001f)++First;
    return Contacts[FMath::Clamp(First+Index,0,Capacity-1)];
}
inline float PropsVisibleEnd(int32 Count){return Super90ReleaseTiming::Withdrawal;}
// SUPER90: Cransh button press after withdrawal, or standalone interrupted
// continuation. M870: the pump closes in its appended or standalone cycle.
inline float Release(int32 Count,bool M870=false)
{
    if(M870)return Count>0?M870LoaderTiming::Closed:M870WeaponAssets::PumpClosed;
    return Count>0?Super90ReleaseTiming::Closed:Super90ReleaseTiming::CycleClosed;
}
inline const TCHAR* GuideFor(bool M870){return M870?M870LoaderTiming::Guide:Guide;}
inline float EmptyPacedReferenceFor(bool M870)
{
    return M870?M870LoaderTiming::End+Super90LoaderPushTiming::ExtraDuration:EmptyPacedReference;
}
inline FString Animation(int32 Count,bool Empty,bool M870=false)
{
    if(M870&&Count==0)return M870WeaponAssets::AnimationPath(TEXT("cycle"));
    const FString Name=Count==0?TEXT("A_Super90_loader_cycle"):
        FString::Printf(TEXT("A_%s_loader_%s_%d"),M870?TEXT("M870"):TEXT("Super90"),Empty?TEXT("empty"):TEXT("normal"),Count);
    return (M870?TEXT("/Game/Weapons/M870/Speedloader20261016/Animations/"):TEXT("/Game/Weapons/Super90/Speedloader20261007/Animations/"))
        +Name+TEXT(".")+Name;
}
}
