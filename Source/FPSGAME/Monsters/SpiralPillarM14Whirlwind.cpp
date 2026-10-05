#include "SpiralPillarM14.h"
#include "M14WhirlwindMotion.h"
#include "FleshHandMonster.h"
#include "FPSCombatHealthComponent.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/FPSIceWall.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

void ASpiralPillarM14::TickWhirlwindContact()
{
    using namespace M14WhirlwindMotion;
    // Only contact math substeps. Skin pose is published once on the ordinary
    // animation tick, preserving coherent previous-frame bone velocities.
    while(WhirlwindSample<=ContactSamples&&State==EM14State::Whirlwind&&!Dead())
    {
        const float To=ReadySeconds+float(WhirlwindSample)/ContactHz;
        if(To>StateSeconds+UE_SMALL_NUMBER)break;
        const float From=ReadySeconds+float(WhirlwindSample-1)/ContactHz;
        ++WhirlwindSample;
        WhirlwindContact(From,To);
    }
}

void ASpiralPillarM14::WhirlwindContact(float FromTime,float ToTime)
{
    using namespace M14WhirlwindMotion;
    const FVector Origin=GetNavAgentLocation()+FVector::UpVector*ContactHeight;
    const float Sense=bPositiveXIsRight?1.f:-1.f;
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_Pawn);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    Objects.AddObjectTypesToQuery(ECC_WorldStatic);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M14Whirlwind),false,this);
    TArray<FHitResult,TInlineAllocator<16>> Candidates;
    TArray<FHitResult> Hits;
    for(int32 Side=0;Side<2;++Side)
    {
        auto Radial=[&](float Time)
        {return FRotator(0,LockedYaw+Sense*(90.f+Yaw(Time))+180.f*Side,0).Vector();};
        const FVector Before=Radial(FromTime),After=Radial(ToTime);
        const FVector Tip=Origin+After*OuterRadius;
        GetWorld()->SweepMultiByObjectType(Hits,Origin+After*45.f,Tip,FQuat::Identity,
            Objects,FCollisionShape::MakeSphere(ContactRadius),Query);
        Candidates.Append(Hits);
        GetWorld()->SweepMultiByObjectType(Hits,Origin+Before*OuterRadius,Tip,FQuat::Identity,
            Objects,FCollisionShape::MakeSphere(ContactRadius),Query);
        Candidates.Append(Hits);
    }
    for(const FHitResult& Hit:Candidates)
    {
        if(State!=EM14State::Whirlwind||Dead())return;
        AActor* Victim=Hit.GetActor();APawn* Pawn=Cast<APawn>(Victim);
        const bool PlayerBody=Pawn&&Pawn->IsPlayerControlled()&&Hit.GetComponent()==Pawn->GetRootComponent();
        if(!IsValid(Victim)||(!PlayerBody&&!Victim->IsA<AFPSIceWall>())||WhirlwindVictims.Contains(Victim))continue;
        auto* Vitals=Victim->FindComponentByClass<UFPSCombatHealthComponent>();
        if(Vitals&&(Vitals->IsDead()||Vitals->IsInvulnerable()))continue;
        // Each target needs a clear radial contact line. A blocked lobe does
        // not damage a player behind scenery or behind a surviving ice wall.
        FVector Contact=Victim->GetActorLocation();Contact.Z=Origin.Z;
        FHitResult Block;
        if(GetWorld()->LineTraceSingleByChannel(Block,Origin,Contact,ECC_Visibility,Query)&&Block.GetActor()!=Victim)continue;
        WhirlwindVictims.Add(Victim);
        FVector Direction=(Victim->GetActorLocation()-GetActorLocation()).GetSafeNormal2D();
        if(Direction.IsNearlyZero())Direction=GetActorForwardVector();
        const float Before=Vitals?Vitals->Health:0.f;
        UGameplayStatics::ApplyPointDamage(Victim,PhysicalAttack*WhirlwindDamageMultiplier,
            Direction,Hit,GetController(),this,UEnemyMeleeDamage::StaticClass());
        // Guard/parry may synchronously interrupt or kill the attacking monster.
        // Invulnerability and a fully blocked hit must not produce displacement.
        if(State!=EM14State::Whirlwind||Dead())return;
        if(Vitals&&Vitals->Health<Before&&!Vitals->IsDead())
            if(auto* Character=Cast<ACharacter>(Victim))UFleshHandPushComponent::Apply(Character,Direction,WhirlwindKnockback);
    }
}
