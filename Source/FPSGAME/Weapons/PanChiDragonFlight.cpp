#include "PanChiGuardComponent.h"
#include "SwordWaveTuning.h"
#include "PanChiUppercutTuning.h"
#include "MeleeWeaponStats.h"
#include "FPSMeleeLightningComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/SwordUppercutTuning.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

void UPanChiGuardComponent::ReleaseUppercutDragon(const FTransform& Aim,float HeavyDamage,const FColdSteelSkillShot& Shot,USoundBase* HitSound)
{
    if(!IsActive()||Shot.AttackMeta!=SwordUppercut::AttackMeta||Shot.GuardSourceInstance!=EquippedInstance||Shot.GuardAttackSerial==0)return;
    if(!GetOwner()->HasAuthority())
    {
        if(Charges()>0&&CooldownRemaining()<=0.f)ServerReleaseDragon(Shot.GuardAttackSerial,Shot.GuardSourceInstance,Aim.Rotator());
        return;
    }
    if(!IsUppercutHit(Shot)||HeavyDamage<=0.f||!CanEmpowerUppercut()||Shot.GuardAttackSerial==ConsumedAttackSerial)return;
    const FRotator Facing(0.f,Aim.Rotator().Yaw,0.f);
    const FVector Forward=Facing.Vector(),Body=GetOwner()->GetActorLocation();
    FVector GroundProbe=Body+Forward*PanChiUppercut::ForwardCM;
    FHitResult Wall,Ground;
    if(PanChiUppercut::TraceSurface(GetWorld(),GetOwner(),Body,GroundProbe,Wall))
        GroundProbe=Wall.ImpactPoint-Forward*20.f;
    if(!PanChiUppercut::TraceSurface(GetWorld(),GetOwner(),GroundProbe+FVector(0,0,60),GroundProbe-FVector(0,0,450),Ground)
        ||Ground.ImpactNormal.Z<.6f)return;
    const FVector Origin=Ground.ImpactPoint+FVector(0,0,PanChiUppercut::LaunchLiftCM);
    const uint8 Spent=uint8(FMath::Clamp(Charges(),1,3));
    ConsumedToughness=UppercutToughnessMultiplier(Shot);ConsumedAttackSerial=Shot.GuardAttackSerial;
    const auto* E=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();
    const auto Flight=SwordWaveTuning::RiftFlight(E,Profile->Equipped());
    // A separate all-magic receipt equal to the full-heavy damage snapshot before
    // target defense. Do not multiply this scalar again by the sword panel.
    FlightDamage=HeavyDamage*Modifiers.PanChiMagicDamageScale;FlightPullCM=Modifiers.PanChiPullCM;FlightHitSound=HitSound;
    FlightShot={};FlightShot.ItemDefinition=Shot.ItemDefinition;FlightShot.MasteryId=Shot.MasteryId;
    FlightShot.bMelee=true;FlightShot.AttackMeta=0x50;FlightShot.AttackForm=EMonsterAttackForm::Impact;
    FlightShot.DamagePanel.BaseMagic=FlightDamage;FlightShot.MagicPenetration=Shot.MagicPenetration;
    FlightShot.CriticalChance=Shot.CriticalChance;FlightShot.CriticalDamageBonus=Shot.CriticalDamageBonus;
    FlightShot.ToughnessDamageMultiplier=0.f;
    // A fresh snapshot intentionally carries no guard/rune/affix trigger keys.
    // Rift retains its independent heavy-attack trigger and hit ledger.
    FlightHitActors.Reset();StoredCharges=0;ChargesEnd=0.;ReadyAt=Clock()+Modifiers.PanChiCooldown;
    // Spread the full ascent over the visual lifetime: no early arrival and
    // frozen dragon at the top. Rift keeps its own independent flight speed.
    const float RiseSpeed=Flight.RangeCM/PanChiUppercut::DragonSeconds;
    MulticastRelease(Origin,FRotator(90.f,Facing.Yaw,0.f),Clock(),Spent,Flight.RangeCM,RiseSpeed);
    ApplyReleasePull(Ground.ImpactPoint);
    Publish();
}

void UPanChiGuardComponent::ApplyReleasePull(const FVector& Center)
{
    auto* Player=Cast<APawn>(GetOwner());
    const float Radius=Modifiers.PanChiRadiusCM;
    if(!Player||!Player->HasAuthority()||Radius<=0.f||FlightPullCM<=0.f)return;
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_Pawn);
    Objects.AddObjectTypesToQuery(ECC_PhysicsBody);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(PanChiFormationPull),false,Player);
    TArray<FOverlapResult> Overlaps;
    GetWorld()->OverlapMultiByObjectType(Overlaps,Center,FQuat::Identity,Objects,FCollisionShape::MakeSphere(Radius),Query);
    TSet<TWeakObjectPtr<AActor>> Seen;
    for(const FOverlapResult& Overlap:Overlaps)
    {
        AActor* Target=Overlap.GetActor();
        if(Seen.Contains(Target)||!UFPSMeleeLightningComponent::IsEnemy(Target,Player))continue;
        Seen.Add(Target);
        if(FVector::DistSquared(Target->GetActorLocation(),Center)>FMath::Square(Radius))continue;
        FHitResult Wall;
        if(PanChiUppercut::TraceSurface(GetWorld(),Player,Center+FVector(0,0,60),Target->GetActorLocation(),Wall))continue;
        // Release-time crowd control has no damage receipt or per-flight hit dependency.
        Target->FindComponentByClass<UMonsterCombatComponent>()->ReceiveFormationPull(Player,Center,FlightPullCM);
    }
}

void UPanChiGuardComponent::ServerReleaseDragon_Implementation(uint32 Serial,const FString& SourceInstance,FRotator AimRotation)
{
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Player||Player->IsLocallyControlled()||!IsActive()||SourceInstance!=EquippedInstance||Serial==0||AimRotation.ContainsNaN())return;
    const auto* Item=Profile->Equipped();if(!Item)return;
    const auto Melee=ColdSteelMelee::Evaluate(*Item,Profile.Get());
    auto Shot=ColdSteelSkills::Snapshot(Player,Item);
    Shot.AttackMeta=SwordUppercut::AttackMeta;Shot.GuardAttackSerial=Serial;Shot.GuardSourceInstance=SourceInstance;
    const float Damage=Melee.Damage*Melee.Modifiers.HeavyMultiplier(Profile->MasteryEffect(TEXT("heavyStrike")).HeavyMultiplier);
    // The client sends action identity and aim only; origin, damage, range,
    // charges and cooldown all come from the authoritative pawn/profile.
    ReleaseUppercutDragon(FTransform(AimRotation,Player->GetPawnViewLocation()),Damage,Shot,nullptr);
}

void UPanChiGuardComponent::MulticastRelease_Implementation(FVector_NetQuantize Origin,FRotator Rotation,double At,uint8 SpentCharges,float RangeCM,float SpeedCM)
{
    ReleaseOrigin=Origin;ReleaseRotation=Rotation;ReleaseAt=At;ReleaseCharges=SpentCharges;
    FlightRangeCM=RangeCM;FlightSpeedCM=SpeedCM;FlightTravelCM=0.f;FlightStoppedAt=-1.;bFlightActive=true;
    // Ascent and visuals share one clock from the post-stride ground release.
    ReleaseVisualSeconds=PanChiUppercut::DragonSeconds;
    SetComponentTickEnabled(true);SetComponentTickInterval(0.f);
    if(GetNetMode()!=NM_DedicatedServer){RequestVisuals();BuildSpiritMeshes();TickReleaseVisual();}
}

void UPanChiGuardComponent::MulticastStopDragon_Implementation(double ReleasedAt,float TravelCM,double StoppedAt)
{
    if(ReleasedAt!=ReleaseAt)return;
    FlightTravelCM=TravelCM;FlightStoppedAt=StoppedAt;bFlightActive=false;
    // Scene collisions stop travel; the launch effect retains its bounded fade.
}

void UPanChiGuardComponent::TickDragonFlight(float Delta)
{
    if(!bFlightActive)return;
    if(!GetOwner()->HasAuthority())
    {
        FlightTravelCM=FMath::Clamp(float(Clock()-ReleaseAt)*FlightSpeedCM,0.f,FlightRangeCM);
        return;
    }
    // Use elapsed release time, not a component delta that may still include
    // the former 40 ms idle interval on the first flight tick.
    const float Desired=FMath::Min(FlightRangeCM,float(FMath::Max(0.,Clock()-ReleaseAt))*FlightSpeedCM);
    const float Distance=FMath::Max(0.f,Desired-FlightTravelCM);
    if(Distance<=0.f)return;
    const FVector Direction=ReleaseRotation.Vector();
    const FVector Start=ReleaseOrigin+Direction*FlightTravelCM,End=Start+Direction*Distance;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(PanChiDragonFlight),false,GetOwner());
    float WallTime=1.f;bool bWall=false;
    TArray<FHitResult> Contacts;
    // Scale the cross-section with the wider dragon. An enemy body must not
    // hide the nearest wall or later enemies from this frame's complete sweep.
    for(;;)
    {
        TArray<FHitResult> Hits;bool bPastBody=false;
        GetWorld()->SweepMultiByChannel(Hits,Start,End,ReleaseRotation.Quaternion(),ECC_Visibility,
            FCollisionShape::MakeBox(FVector(6.f,88.f*PanChiUppercut::DragonWidthScale,36.f*PanChiUppercut::DragonWidthScale)),Query);
        for(const FHitResult& Hit:Hits)
        {
            AActor* Target=Hit.GetActor();
            const bool bBody=Target&&(Target->IsA<APawn>()||Target->FindComponentByClass<UMonsterCombatComponent>());
            if(bBody)
            {
                Query.AddIgnoredActor(Target);bPastBody|=Hit.bBlockingHit;
                if(UFPSMeleeLightningComponent::IsEnemy(Target,GetOwner())&&!FlightHitActors.Contains(Target))Contacts.Add(Hit);
            }
            else if(Hit.bBlockingHit){bWall=true;WallTime=FMath::Min(WallTime,Hit.Time);}
        }
        if(!bPastBody)break;
    }
    Contacts.Sort([](const FHitResult& A,const FHitResult& B){return A.Time<B.Time;});
    for(const FHitResult& Hit:Contacts)
    {
        AActor* Target=Hit.GetActor();
        if((bWall&&Hit.Time>=WallTime)||FlightHitActors.Contains(Target)||!UFPSMeleeLightningComponent::IsEnemy(Target,GetOwner()))continue;
        FlightHitActors.Add(Target);
        FWeaponDamageResult Receipt;
        const float Applied=ColdSteelSkills::ApplyHit(GetOwner(),Hit,FlightDamage,Direction,FlightShot,&Receipt);
        if(Applied<=0.f)continue;
        if(FlightHitSound)UGameplayStatics::PlaySoundAtLocation(this,FlightHitSound,Hit.ImpactPoint,.85f,.9f);
        if(auto* Player=Cast<AFPSGAMECharacter>(GetOwner()))Player->NotifyConfirmedWeaponHit(Target,Applied,&Receipt);
    }
    FlightTravelCM+=Distance*WallTime;
    if(bWall||FlightTravelCM>=FlightRangeCM-UE_KINDA_SMALL_NUMBER)
        MulticastStopDragon(ReleaseAt,FlightTravelCM,Clock());
}
