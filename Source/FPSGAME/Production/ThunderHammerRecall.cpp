#include "ThunderHammerThrown.h"
#include "ThunderHammerThrow.h"
#include "ProductionToolStats.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/MagicOcclusion.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Weapons/FPSMeleeLightningComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/World.h"
#include "TimerManager.h"

namespace
{
constexpr float RecallSeconds=1.f;
constexpr float RecallDamageRangeCM=6000.f;
float Settle(float T){T=FMath::Clamp(T,0.f,1.f);return T*T*T*(T*(T*6.f-15.f)+10.f);}
FVector Bezier(const FVector& A,const FVector& B,const FVector& C,const FVector& D,float T)
{const float U=1.f-T;return A*(U*U*U)+B*(3.f*U*U*T)+C*(3.f*U*T*T)+D*(T*T*T);}
}
float AThunderHammerThrown::RecallAge() const {return FMath::Max(0.f,float(Clock()-RecallAt));}
float AThunderHammerThrown::CatchAge() const {return Phase==3?FMath::Max(0.f,float(Clock()-CaughtAt)):0.f;}

void AThunderHammerThrown::Recall()
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    if(!HasAuthority()||Phase!=1||!Pawn||!Profile)return;
    ColdSteelAuthority::FScope Scope(Profile);
    const auto Stats=ColdSteelTool::Evaluate(Weapon,Profile);
    RecallShot=ColdSteelSkills::Snapshot(Pawn,&Weapon);RecallShot.bMelee=true;
    RecallShot.DamagePanel=Stats.Damage;
    // One ordinary physical attack, never the launch's heavy multiplier,
    // lightning, magic panel, or ground-stun payload.
    RecallShot.DamagePanel.BaseMagic=RecallShot.DamagePanel.AddedMagic=0.;
    RecallShot.ToughnessDamageMultiplier=float(Stats.ToughnessDamage);
    RecallShot.CriticalChance=float(FMath::Clamp(double(RecallShot.CriticalChance)+Stats.CriticalChanceAdd,0.,100.));
    // A distant retrieval is transport only for this entire recall. Clearing
    // the damage panel also prevents hit procs and mastery from reactivating
    // when the hammer enters the 60 m radius near the end of its flight.
    if(FVector::DistSquared(Pawn->GetActorLocation(),GetActorLocation())>FMath::Square(RecallDamageRangeCM))
        RecallShot.DamagePanel={};
    RecallHits.Reset();RecallMasteryHits=0;
    Phase=2;RecallAt=Clock();RecallFrom=GetActorLocation();
    GetWorld()->GetTimerManager().ClearTimer(StaticFieldTimer);
    GetWorld()->GetTimerManager().ClearTimer(CoilTimer);
    SetActorEnableCollision(false);
    RecallGoal=ThunderHammerThrow::CatchFrame(Pawn).GetLocation();
    const FVector ToHand=RecallGoal-RecallFrom;const float Distance=float(ToHand.Size());
    RecallDuration=RecallSeconds;
    RecallControl=RecallFrom+FVector(0,0,FMath::Clamp(Distance*.08f,45.f,110.f))+
        ToHand.GetSafeNormal()*FMath::Min(160.f,Distance*.18f);
    RecallAxis=Pawn->GetViewRotation().RotateVector(FVector::RightVector);
    ForceNetUpdate();
}
void AThunderHammerThrown::AdvanceRecall(float Delta)
{
    auto* Pawn=Cast<APawn>(GetOwner());if(!Pawn)return;
    // Subdivide the swept path so a low frame rate cannot skip a victim or
    // replace a curved return with one long straight collision segment.
    const int32 Steps=FMath::Clamp(FMath::CeilToInt(Delta/ThunderHammerThrow::Step),1,16);
    const float H=Delta/Steps,Age=RecallAge();
    for(int32 I=0;I<Steps&&Phase==2;++I)
    {
        const float T=FMath::Clamp((Age-Delta+H*(I+1))/RecallDuration,0.f,1.f);
        const auto Hand=ThunderHammerThrow::CatchFrame(Pawn);const FVector End=Hand.GetLocation();
        RecallGoal=FMath::VInterpTo(RecallGoal,End,H,12.f+20.f*T);
        const FVector Goal=FMath::Lerp(RecallGoal,End,FMath::SmoothStep(.75f,1.f,T));
        // Approach from in front of the extended right palm, away from the face.
        const FVector Approach=Pawn->GetViewRotation().Vector()*FMath::Min(110.f,float(FVector::Distance(RecallFrom,End))*.22f);
        // Keep approach momentum into the palm. A quintic ease-out made the
        // hammer hover almost to a stop before the catch could absorb it.
        // Start smoothly, arrive with finite speed, then the authored arm
        // compression owns the stop. Rotation still finishes whole turns.
        const float Travel=T*T*(2.f-T);
        const FVector Next=Bezier(RecallFrom,RecallControl,Goal+Approach,Goal,Travel);
        const FVector From=GetActorLocation();
        // Sample the full trajectory by time, without a travel-speed ceiling
        // or a blocking sweep. Long range and walls cannot prolong the recall.
        // Goal converges to the live palm before T=1, including a moving owner.
        HitRecallSegment(From,Next);SetActorLocation(Next,false);
        if(T>=1.f)
        {
            // Phase 3 lasts only 100 ms. A replicated property can be coalesced
            // with destruction under packet loss; this ordered reliable receipt
            // reaches existing actor channels before their destruction message.
            Phase=3;CaughtAt=Clock();MulticastCaught(CaughtAt);ForceNetUpdate();
        }
    }
}
float AThunderHammerThrown::RecallSpinTurns() const
{
    const float T=FMath::Clamp(RecallAge()/RecallDuration,0.f,1.f);
    return float(FMath::Max(1,FMath::CeilToInt(RecallDuration*2.8f)))*Settle(T);
}
FQuat AThunderHammerThrown::RecallRotation() const
{
    const float T=FMath::Clamp(RecallAge()/RecallDuration,0.f,1.f),W=Settle(T);
    const auto* Pawn=Cast<APawn>(GetOwner());const FQuat Catch=ThunderHammerThrow::CatchFrame(Pawn).GetRotation();
    const FQuat Base=FQuat::Slerp(FRotator(135.f,FlightYaw,0).Quaternion(),Catch,W).GetNormalized();
    // Keep the head-led forward turn on recall, then complete whole turns
    // and slow down into the exact authored grip frame.
    return (FQuat(RecallAxis.GetSafeNormal(),2.f*PI*RecallSpinTurns())*Base).GetNormalized();
}
void AThunderHammerThrown::HitRecallSegment(const FVector& From,const FVector& To)
{
    if(!HasAuthority()||RecallShot.DamagePanel.Total()<=0.)return;
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());if(!Pawn)return;
    const FVector OwnerLocation=Pawn->GetActorLocation();
    if(FVector::DistSquared(OwnerLocation,From)>FMath::Square(RecallDamageRangeCM)||
        FVector::DistSquared(OwnerLocation,To)>FMath::Square(RecallDamageRangeCM))
    {RecallShot.DamagePanel={};return;}
    auto* Profile=ColdSteelAuthority::ForPawn(Pawn);if(!Profile)return;
    ColdSteelAuthority::FScope Scope(Profile);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ThunderHammerRecall),false,Pawn);Query.AddIgnoredActor(this);
    TArray<FHitResult> Hits;
    GetWorld()->SweepMultiByObjectType(Hits,From,To,FQuat::Identity,FCollisionObjectQueryParams::AllDynamicObjects,
        FCollisionShape::MakeSphere(ThunderHammerThrow::RecallHitRadius),Query);
    for(const auto& Hit:Hits)
        if(auto* A=Hit.GetActor();A&&(A->IsA<APawn>()||A->FindComponentByClass<UMonsterCombatComponent>()))Query.AddIgnoredActor(A);
    for(const auto& Hit:Hits)
    {
        auto* Target=Hit.GetActor();auto* Shape=Hit.GetComponent();
        auto* Combat=Target?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
        if(!Shape||!Combat||RecallHits.Contains(Target)||!UFPSMeleeLightningComponent::IsEnemy(Target,Pawn))continue;
        const FVector Origin=FMath::ClosestPointOnSegment(Shape->Bounds.Origin,From,To);
        FVector Point;if(Shape->GetClosestPointOnCollision(Origin,Point)<0.f)Point=Shape->Bounds.GetBox().GetClosestPointTo(Origin);
        FHitResult Cover;if(MagicOcclusion::TraceBlocker(GetWorld(),Origin,Point,Query,Cover))continue;
        RecallHits.Add(Target);
        const FVector Direction=(To-From).GetSafeNormal(UE_SMALL_NUMBER,(Point-Origin).GetSafeNormal());
        FHitResult Contact(Target,Shape,Point,-Direction);Contact.TraceStart=From;Contact.TraceEnd=To;
        auto Shot=RecallShot;const bool Eligible=ColdSteelSkills::IsMasteryTrainingTarget(Pawn,Target);
        Shot.ExtraMasteryExperience=Eligible&&RecallMasteryHits==1?Profile->MasteryDefinition(Shot.MasteryId).MultiHitExperience:0;
        FWeaponDamageResult Result;
        const float Damage=ColdSteelSkills::ApplyHit(Pawn,Contact,float(Shot.DamagePanel.Total()),Direction,Shot,&Result);
        if(Eligible&&(Damage>0.f||Result.bKilled))++RecallMasteryHits;
        if(Damage>0.f||Result.bKilled)Pawn->NotifyConfirmedWeaponHit(Target,Damage,&Result);
    }
}
