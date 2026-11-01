#include "ThunderHammerThrow.h"
#include "ThunderHammerTuning.h"
#include "ThunderHammerZhenTing.h"
#include "ThunderHammerThrowLaunch.h"
#include "ThunderHammerCatchFrames.h"
#include "ProductionToolComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Skills/FPSMagicPreview.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Combat/RangedAttackQuery.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"

bool ThunderHammerThrow::Installed(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile)
{
    if(Item.Definition!=ThunderHammer::Definition||!Profile)return false;
    const auto* G=Profile->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    return G&&G->Installed(Item).FindRef(TEXT("head_mount"))==Seat;
}
FTransform ThunderHammerThrow::LaunchFrame(const APawn* Pawn)
{
    const auto* Character=Cast<AFPSGAMECharacter>(Pawn);
    const FTransform Aim=Character?Character->GetMeleeAimTransform():FTransform(Pawn->GetViewRotation(),Pawn->GetPawnViewLocation());
    return FTransform(Aim.GetRotation()*MeshRotation,Aim.TransformPosition(LaunchOffsetCM));
}
FTransform ThunderHammerThrow::CatchFrame(const APawn* Pawn,float Age)
{
    // Local presentation includes the exact current camera/arm pose. Authority
    // for remote pawns uses the same imported contact frames without loading arms.
    FTransform Presented;
    if(Pawn->IsLocallyControlled())
        if(const auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>();Tool&&Tool->GetThunderCatchFrame(Presented))return Presented;
    const float Frame=FMath::Clamp(Age/CatchFrameStepV4,0.f,float(UE_ARRAY_COUNT(CatchFramesV4)-1));
    const int32 A=FMath::FloorToInt(Frame),B=FMath::Min(A+1,int32(UE_ARRAY_COUNT(CatchFramesV4)-1));
    FTransform Local;Local.Blend(CatchFramesV4[A],CatchFramesV4[B],Frame-A);
    const auto* Character=Cast<AFPSGAMECharacter>(Pawn);
    const FTransform Aim=Character?Character->GetMeleeAimTransform():FTransform(Pawn->GetViewRotation(),Pawn->GetPawnViewLocation());
    return FTransform(Aim.GetRotation()*Local.GetRotation(),Aim.TransformPosition(Local.GetLocation()));
}
void ThunderHammerThrow::Launch(const APawn* Pawn,FVector& Position,FVector& Velocity,const FColdSteelItem* Item)
{
    const auto Frame=LaunchFrame(Pawn);Position=Frame.GetLocation();
    // Prevent a long overhead release from starting beyond nearby cover.
    const FVector Eye=Pawn->GetPawnViewLocation();FHitResult Wall;
    FCollisionQueryParams Q(SCENE_QUERY_STAT(ThunderThrowStart),false,Pawn);
    if(RangedAttackQuery::SweepSingle(Pawn->GetWorld(),Pawn,Wall,Eye,Position,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(Radius),Q))
        Position=Wall.Location;
    Velocity=FPSMagicPreview::LaunchVelocity(Position,FPSMagicPreview::AimPoint(Pawn,nullptr),Speed,Pawn->GetViewRotation().Vector());
    // Preserve lift and flight duration: at the same aim/floor height the
    // horizontal travel is exactly 1.5x, in both preview and authoritative flight.
    if(ThunderHammerZhenTing::Installed(Item)){Velocity.X*=1.5f;Velocity.Y*=1.5f;}
}
bool ThunderHammerThrow::Advance(const APawn* Pawn,const AActor* Ignore,FVector& Position,FVector& Velocity,FHitResult& Floor)
{
    const FVector Accel(0,0,-Gravity),End=Position+Velocity*Step+Accel*(.5f*Step*Step);
    FCollisionQueryParams Q(SCENE_QUERY_STAT(ThunderThrowFlight),false,Pawn);if(Ignore)Q.AddIgnoredActor(Ignore);
    FHitResult Hit;
    for(int32 I=0;I<16;++I)
    {
        if(!RangedAttackQuery::SweepSingle(Pawn->GetWorld(),Pawn,Hit,Position,End,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(Radius),Q))
        {Position=End;Velocity+=Accel*Step;return false;}
        auto* Actor=Hit.GetActor();
        if(Actor&&(Actor->IsA<APawn>()||Actor->FindComponentByClass<UMonsterCombatComponent>())){Q.AddIgnoredActor(Actor);continue;}
        Position=Hit.Location+Hit.ImpactNormal*1.f;
        if(Hit.ImpactNormal.Z>=.5f){Floor=Hit;return true;}
        // Walls/ceilings arrest the throw; the hammer then drops to the floor.
        Velocity=FVector(0,0,FMath::Min(0.,Velocity.Z))+Accel*Step;return false;
    }
    Velocity+=Accel*Step;return false;
}
