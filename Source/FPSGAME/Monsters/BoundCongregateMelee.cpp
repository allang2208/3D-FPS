#include "BoundCongregate.h"
#include "BoundCongregateMeleeTiming.h"
#include "FPSCombatHealthComponent.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/IceWallCombat.h"
#include "Animation/AnimSequence.h"
#include "Components/AudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
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
            if(GetNetMode()!=NM_DedicatedServer&&FlurrySound&&T-Contacts[Beat]<.2f)
            {ActionVoice->SetSound(FlurrySound);ActionVoice->SetVolumeMultiplier(Beat==HitCount-1?1.f:.65f);ActionVoice->Play();}
        }
    if(!HasAuthority())return;
    APawn* Victim=Target.Get();
    const auto* VictimHealth=Victim?Victim->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!IsValid(Victim)||(VictimHealth&&VictimHealth->IsDead()))
    {bContactConsumed=true;NextAttack=Clock()+.35f;SetState(EBoundCongregateState::Idle);return;}
    // Aim only while visibly loading; the committed strokes can be sidestepped.
    const float TurnUntil=Flurry?TurnEnd:BiteTurnEnd;
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
    else if(!bContactConsumed&&T>=BiteContactSeconds)
    {
        bContactConsumed=true;
        if(T-BiteContactSeconds<=.2f)
        {
            Sample(BiteContactSeconds);GetMesh()->TickAnimation(0,false);GetMesh()->RefreshBoneTransforms();Contact();
            if(NetState.State!=EBoundCongregateState::Bite)return;
            Sample(T);
        }
    }
    const UAnimSequence* Clip=Flurry?FlurryClip.Get():BiteClip.Get();
    if(T>=(Clip?Clip->GetPlayLength():Flurry?Duration:BiteDuration))
    {NextAttack=Clock()+.22f;SetState(EBoundCongregateState::Idle);}
}

void ABoundCongregate::FlurryContact(int32 Beat,float PlaybackTime)
{
    using namespace BoundCongregateMeleeTiming;
    APawn* Victim=Target.Get();if(!IsValid(Victim))return;
    const bool Finisher=Beat==HitCount-1;
    const float Damage=Finisher?FlurryFinisherDamage:FlurryDamage;
    // Three exact clip samples cover the fast curved stroke with two sweeps.
    // The final double slap is one beat and can damage the same victim only once.
    const FName Bones[]={TEXT("leg_L1_foot"),TEXT("leg_R1_foot")};
    FVector Points[2][3];
    for(int32 Step=0;Step<3;++Step)
    {
        // Only sweep the committed release, never the preceding load arc.
        Sample(FMath::Lerp(StrikeStarts[Beat],Contacts[Beat],Step*.5f));
        GetMesh()->TickAnimation(0,false);GetMesh()->RefreshBoneTransforms();
        // The foot joint is at the wrist/ankle. Centre the sphere over the
        // palm/sole, halfway along the original approximately 20 cm end bone.
        for(int32 Side=0;Side<2;++Side)Points[Side][Step]=GetMesh()->GetSocketLocation(Bones[Side])+GetActorForwardVector()*10.f;
    }
    Sample(PlaybackTime);
    if(IceWallCombat::ApplyMelee(this,Victim,FlurryRange,Damage))return;
    float R=0,H=0;Victim->GetSimpleCollisionCylinder(R,H);
    const FVector Center=Victim->GetActorLocation(),Axis(0,0,FMath::Max(0.f,H-R));
    FCollisionQueryParams Q(SCENE_QUERY_STAT(CongregatePalmContact),false,this);Q.AddIgnoredActor(Victim);
    const float Radius=FlurryPalmRadius+(Finisher?8.f:0.f);
    for(int32 Side=0;Side<2;++Side)
    {
        if(!Finisher&&Side!=Beat%2)continue;
        for(int32 Segment=0;Segment<2;++Segment)
        {
            FVector OnStroke,OnVictim;
            FMath::SegmentDistToSegmentSafe(Points[Side][Segment],Points[Side][Segment+1],Center-Axis,Center+Axis,OnStroke,OnVictim);
            if(FVector::DistSquared(OnStroke,OnVictim)>FMath::Square(Radius+R))continue;
            FHitResult Block;
            // Both the body-to-hand and hand-to-victim lines must be open.
            // Prevent an authored limb arc reaching through a wall or pillar.
            if(GetWorld()->LineTraceSingleByChannel(Block,GetMesh()->GetSocketLocation(TEXT("maw")),OnStroke,ECC_Visibility,Q)||
               GetWorld()->LineTraceSingleByChannel(Block,OnStroke,OnVictim,ECC_Visibility,Q))continue;
            const FVector Direction=(OnVictim-OnStroke).GetSafeNormal();
            FHitResult Hit;Hit.Location=Hit.ImpactPoint=OnVictim-Direction*R;Hit.ImpactNormal=-Direction;
            UGameplayStatics::ApplyPointDamage(Victim,Damage,Direction,Hit,GetController(),this,UEnemyMeleeDamage::StaticClass());
            return;
        }
    }
}
