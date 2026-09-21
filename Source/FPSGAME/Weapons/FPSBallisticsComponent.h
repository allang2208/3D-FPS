#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "FPSBallisticsComponent.generated.h"
class UFPSWeaponFXComponent;
class USoundBase;
struct FColdSteelItem;
struct FFPSFlyingRound
{
    FVector Position,Direction;
    float Speed=0,Remaining=0,Damage=0;
    float TraveledCM=0,EffectiveRangeCM=0;
    double Timestamp=0;
    // Stable per-round identity: the weapon FX keeps one tracer streak per Id and
    // refreshes it in place, instead of spawning a new one-frame segment each tick.
    int32 Id=INDEX_NONE;
    int32 Piercing=0,Poison=0;
    FColdSteelSkillShot Training;
    TArray<TWeakObjectPtr<AActor>> HitActors;
};
/** Straight swept projectiles, matching the source Godot zero-gravity fire path. */
UCLASS()
class FPSGAME_API UFPSBallisticsComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSBallisticsComponent();
    void Launch(FVector Start,FVector Direction,float SpeedCM,float RangeCM,float Damage,UFPSWeaponFXComponent* FX,USoundBase* Headshot,float EffectiveRangeCM=0,const FColdSteelItem* ShotItem=nullptr);
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Fn) override;
    int32 ActiveCount()const{return Rounds.Num();}
    int32 ImpactCount=0;
    FVector LastLaunchStart=FVector::ZeroVector;
    FVector LastImpactPoint=FVector::ZeroVector;
private:
    TArray<FFPSFlyingRound> Rounds;
    int32 NextRoundId=0;
    UPROPERTY(Transient) TObjectPtr<UFPSWeaponFXComponent> WeaponFX;
    UPROPERTY(Transient) TObjectPtr<USoundBase> HeadshotSound;
};
