#pragma once
#include "CoreMinimal.h"
class APawn;
class AActor;
class UColdSteelStatusModel;
struct FColdSteelItem;
struct FHitResult;

namespace ThunderHammerThrow
{
    inline constexpr const TCHAR* Seat=TEXT("guan_lei_seat");
    inline constexpr float Release=.24f,Duration=.86f,RecallReadySeconds=.32f,CatchSeconds=.60f,CatchAttachSeconds=.10f;
    inline constexpr float RecallSpeed=2300.f,RecallHitRadius=34.f;
    inline constexpr float Speed=1700.f,Gravity=1400.f,Step=1.f/60.f,Radius=14.f;
    inline constexpr float CenterZ=70.f;
    // GroundPitch also defines the authored contact anchors in GroundContacts.
    inline constexpr float GroundPitch=135.f,GroundEmbedCM=4.f;
    inline constexpr const TCHAR* Charge=TEXT("/Game/Weapons/ThunderGodHammer20261028/ThunderThrowV1/A_ThunderHammer_ThrowCharge.A_ThunderHammer_ThrowCharge");
    inline constexpr const TCHAR* Throw=TEXT("/Game/Weapons/ThunderGodHammer20261028/ThunderThrowV1/A_ThunderHammer_ThrowRelease.A_ThunderHammer_ThrowRelease");
    inline constexpr const TCHAR* RecallReady=TEXT("/Game/Weapons/ThunderGodHammer20261028/RecallCatchV2/A_ThunderHammer_RecallReady_V2.A_ThunderHammer_RecallReady_V2");
    inline constexpr const TCHAR* Catch=TEXT("/Game/Weapons/ThunderGodHammer20261028/RecallCatchV2/A_ThunderHammer_Catch_V2.A_ThunderHammer_Catch_V2");
    bool Installed(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile);
    FTransform LaunchFrame(const APawn* Pawn);
    FTransform CatchFrame(const APawn* Pawn,float CatchAge=0.f);
    void Launch(const APawn* Pawn,FVector& Position,FVector& Velocity,const FColdSteelItem* Item);
    // Shared fixed-step trajectory for the real projectile and the magic-style preview.
    bool Advance(const APawn* Pawn,const AActor* Ignore,FVector& Position,FVector& Velocity,FHitResult& Floor);
}
