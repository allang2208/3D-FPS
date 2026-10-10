#include "BoundCongregate.h"
#include "BoundCongregateMeleeTiming.h"
#include "FPSCombatHealthComponent.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/IceWallCombat.h"
#include "../Skills/FPSIceWall.h"
#include "../Weapons/FPSImpactFXSubsystem.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/AudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"

bool ABoundCongregate::CanBite(APawn* Victim) const
{
    if(!BiteClip||!IsValid(Victim)||Clock()<NextBite)return false;
    const FVector D=Victim->GetActorLocation()-GetActorLocation();
    return D.Size2D()<=BiteTriggerRange&&FMath::Abs(D.Z)<180.f&&
        FMath::Abs(FMath::FindDeltaAngleDegrees(GetActorRotation().Yaw,D.Rotation().Yaw))<=35.f&&
        (HasSight(Victim)||IceWallCombat::BlockingWall(this,Victim,BiteTriggerRange));
}

bool ABoundCongregate::CanFlurry(APawn* Victim) const
{
    if(!FlurryClip||!IsValid(Victim)||Clock()<NextFlurry)return false;
    const FVector D=Victim->GetActorLocation()-GetActorLocation();
    return D.Size2D()<=FlurryRange&&FMath::Abs(D.Z)<170.f&&
        FMath::Abs(FMath::FindDeltaAngleDegrees(GetActorRotation().Yaw,D.Rotation().Yaw))<=45.f&&
        (HasSight(Victim)||IceWallCombat::BlockingWall(this,Victim,FlurryRange));
}

void ABoundCongregate::TickMelee(float Dt)
{
    using namespace BoundCongregateMeleeTiming;
    const float T=float(StateElapsed());
    const bool Flurry=NetState.State==EBoundCongregateState::Flurry;
    Sample(T);
    if(Flurry)
        while(NextFlurrySound<HitCount&&T>=Contacts[NextFlurrySound])
        {
            const int32 Beat=NextFlurrySound++;
            // Clients replay the same ground contact for local pooled effects;
            // authority settles damage through NextFlurryHit below.
            if(!HasAuthority()&&T-Contacts[Beat]<.2f)FlurryContact(Beat,T);
            if(GetNetMode()!=NM_DedicatedServer&&FlurrySound&&T-Contacts[Beat]<.2f)
            {ActionVoice->SetSound(FlurrySound);ActionVoice->SetVolumeMultiplier(Beat==HitCount-1?1.f:.65f);ActionVoice->Play();}
        }
    if(!HasAuthority())return;
    APawn* Victim=Target.Get();
    const auto* VictimHealth=Victim?Victim->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!IsValid(Victim)||(VictimHealth&&VictimHealth->IsDead()))
    {bContactConsumed=true;NextAttack=Clock()+.35f;SetState(EBoundCongregateState::Idle);return;}
    // Aim only while visibly loading; the committed strokes can be sidestepped.
    const float TurnUntil=Flurry?TurnEnd:BiteWindupEnd;
    if(T<TurnUntil)
        AttackYaw=FMath::FixedTurn(AttackYaw,(Victim->GetActorLocation()-GetActorLocation()).Rotation().Yaw,110.f*Dt);
    SetActorRotation(FRotator(0,AttackYaw,0));
    if(Flurry)
    {
        while(NextFlurryHit<HitCount&&T>=Contacts[NextFlurryHit])
        {
            const int32 Beat=NextFlurryHit++;
            // Do not dump several old hits on the player after a long hitch.
            if(T-Contacts[Beat]>.2f)continue;
            FlurryContact(Beat,T);
            // A player parry/death callback may synchronously cancel the attack.
            if(NetState.State!=EBoundCongregateState::Flurry)return;
        }
    }
    else if(!bContactConsumed&&T>=BiteContactSeconds-.02f)
    {
        // V28 closes at .56 s, holds full extension until .65 s, then tears
        // back. Follow that short closing/hold interval instead of spending
        // the entire bite on one range query at .56 s.
        const float Close=BiteContactSeconds+.09f;
        if(T<=Close||(T-Dt<=Close&&T-Close<=.2f))
        {
            Sample(FMath::Min(T,Close));GetMesh()->TickAnimation(0,false);GetMesh()->RefreshBoneTransforms();Contact();
            if(NetState.State!=EBoundCongregateState::Bite)return;
            Sample(T);
        }
        if(T>=Close)bContactConsumed=true;
    }
    const UAnimSequence* Clip=Flurry?FlurryClip.Get():BiteClip.Get();
    if(T>=(Clip?Clip->GetPlayLength():Flurry?Duration:BiteDuration))
    {NextAttack=Clock()+.22f;SetState(EBoundCongregateState::Idle);}
}

void ABoundCongregate::FlurryContact(int32 Beat,float PlaybackTime)
{
    using namespace BoundCongregateMeleeTiming;
    const bool Finisher=Beat==HitCount-1;
    const float Damage=Finisher?FlurryFinisherDamage:FlurryDamage;
    const float Radius=FMath::Max(1.f,FlurryPalmRadius)+(Finisher?FinisherRadiusBonus:0.f);
    const FName Bones[]={TEXT("leg_L1_foot"),TEXT("leg_R1_foot"),TEXT("leg_L2_foot"),TEXT("leg_R2_foot")};
    Sample(Contacts[Beat]);GetMesh()->TickAnimation(0,false);GetMesh()->RefreshBoneTransforms();
    FVector Palms[4];
    for(int32 Limb=0;Limb<4;++Limb)
        if(LimbMasks[Beat]&(1u<<Limb))Palms[Limb]=GetMesh()->GetSocketLocation(Bones[Limb])+GetActorForwardVector()*10.f;
    const FVector Body=GetMesh()->GetSocketLocation(TEXT("maw"));
    Sample(PlaybackTime);
    FCollisionQueryParams Q(SCENE_QUERY_STAT(CongregateGroundSlap),false,this);
    FCollisionObjectQueryParams FloorObjects;FloorObjects.AddObjectTypesToQuery(ECC_WorldStatic);FloorObjects.AddObjectTypesToQuery(ECC_WorldDynamic);
    // The union of two final palm circles remains one damage beat per player.
    TSet<APawn*> Damaged;
    TSet<AFPSIceWall*> DamagedWalls;
    auto StrikeCover=[&](const FHitResult& Block)
    {
        if(!HasAuthority())return;
        if(auto* Wall=Cast<AFPSIceWall>(Block.GetActor());Wall&&Wall->IsSolid()&&!DamagedWalls.Contains(Wall))
        {
            DamagedWalls.Add(Wall);
            UGameplayStatics::ApplyPointDamage(Wall,Damage,GetActorForwardVector(),Block,GetController(),this,UEnemyMeleeDamage::StaticClass());
        }
    };
    UCameraComponent* Camera=nullptr;
    UFPSImpactFXSubsystem* FX=nullptr;
    if(GetNetMode()!=NM_DedicatedServer)
    {
        FX=GetWorld()->GetSubsystem<UFPSImpactFXSubsystem>();
        if(const APawn* Viewer=UGameplayStatics::GetPlayerPawn(this,0))Camera=Viewer->FindComponentByClass<UCameraComponent>();
    }
    for(int32 Limb=0;Limb<4;++Limb)
    {
        if(!(LimbMasks[Beat]&(1u<<Limb)))continue;
        FHitResult Ground;
        // Only an actual nearby walkable surface can produce a ground slam.
        if(!GetWorld()->LineTraceSingleByObjectType(Ground,Palms[Limb]+FVector(0,0,20),Palms[Limb]-FVector(0,0,70),FloorObjects,Q)||
            !GetCharacterMovement()->IsWalkable(Ground)||!Ground.GetComponent()||
            Ground.GetComponent()->GetCollisionResponseToChannel(ECC_Pawn)!=ECR_Block)continue;
        const FVector Origin=Ground.ImpactPoint;
        FHitResult Cover;
        if(GetWorld()->LineTraceSingleByObjectType(Cover,Body,Origin+FVector(0,0,12),FloorObjects,Q))
        {StrikeCover(Cover);continue;}
        if(FX)FX->SpawnPounceLanding(Ground,GetActorForwardVector(),Radius,360.f,Camera,this,false);
        if(!HasAuthority())continue;
        TArray<FOverlapResult> Overlaps;
        GetWorld()->OverlapMultiByObjectType(Overlaps,Origin+FVector(0,0,GroundDamageHeight*.5f),FQuat::Identity,
            FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeBox(FVector(Radius,Radius,GroundDamageHeight*.5f+20.f)),Q);
        for(const auto& Overlap:Overlaps)
        {
            auto* Victim=Cast<APawn>(Overlap.GetActor());
            if(!IsValid(Victim)||!Victim->IsPlayerControlled()||Damaged.Contains(Victim))continue;
            const auto* VictimHealth=Victim->FindComponentByClass<UFPSCombatHealthComponent>();
            if(VictimHealth&&VictimHealth->IsDead())continue;
            float R=0,H=0;Victim->GetSimpleCollisionCylinder(R,H);
            const FVector Center=Victim->GetActorLocation();
            const float FeetZ=Center.Z-H;
            if(FVector::DistSquared2D(Origin,Center)>FMath::Square(Radius+R)||
                FeetZ-Origin.Z>GroundDamageHeight||FeetZ-Origin.Z< -25.f)continue;
            FCollisionQueryParams Sight=Q;Sight.AddIgnoredActor(Victim);
            const FVector Contact(Center.X,Center.Y,FeetZ+FMath::Min(H,45.f));
            FHitResult Block;
            if(GetWorld()->LineTraceSingleByChannel(Block,Origin+FVector(0,0,15),Contact,ECC_Visibility,Sight))
            {StrikeCover(Block);continue;}
            const FVector Direction=(Contact-Origin).GetSafeNormal();
            FHitResult Hit;Hit.Location=Hit.ImpactPoint=Contact-Direction*R;Hit.ImpactNormal=-Direction;
            Damaged.Add(Victim);
            UGameplayStatics::ApplyPointDamage(Victim,Damage,Direction,Hit,GetController(),this,UEnemyMeleeDamage::StaticClass());
            if(NetState.State!=EBoundCongregateState::Flurry)return;
        }
    }
}
