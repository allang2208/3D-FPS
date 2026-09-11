#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FPSBallisticsComponent.generated.h"
class UFPSWeaponFXComponent;
class USoundBase;
struct FFPSFlyingRound
{
    FVector Position,Direction;
    float Speed=0,Remaining=0,Damage=0;
    double Timestamp=0;
};
/** Straight swept projectiles, matching the source Godot zero-gravity fire path. */
UCLASS()
class FPSGAME_API UFPSBallisticsComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSBallisticsComponent();
    void Launch(FVector Start,FVector Direction,float SpeedCM,float RangeCM,float Damage,UFPSWeaponFXComponent* FX,USoundBase* Headshot);
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Fn) override;
    int32 ActiveCount()const{return Rounds.Num();}
    int32 ImpactCount=0;
    FVector LastLaunchStart=FVector::ZeroVector;
    FVector LastImpactPoint=FVector::ZeroVector;
private:
    TArray<FFPSFlyingRound> Rounds;
    UPROPERTY(Transient) TObjectPtr<UFPSWeaponFXComponent> WeaponFX;
    UPROPERTY(Transient) TObjectPtr<USoundBase> HeadshotSound;
};
