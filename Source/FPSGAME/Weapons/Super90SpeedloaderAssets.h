#pragma once
#include "CoreMinimal.h"
#include "Super90ReleaseTiming.h"
#include "Super90LoaderPushTiming.h"

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
// Cransh button press after withdrawal, or standalone interrupted continuation.
inline float Release(int32 Count){return Count>0?Super90ReleaseTiming::Closed:Super90ReleaseTiming::CycleClosed;}
inline FString Animation(int32 Count,bool Empty)
{
    const FString Name=Count==0?TEXT("A_Super90_loader_cycle"):
        FString::Printf(TEXT("A_Super90_loader_%s_%d"),Empty?TEXT("empty"):TEXT("normal"),Count);
    return TEXT("/Game/Weapons/Super90/Speedloader20261007/Animations/")+Name+TEXT(".")+Name;
}
}
