#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FleshHandKnockdownComponent.generated.h"
class AFleshHandMonster;
class APawn;
class UAnimSequence;

UENUM(BlueprintType)
enum class EFleshHandKnockdownPhase : uint8 { None, Launch, Airborne, Landing, Downed, GettingUp, Corpse };

/** One swept character capsule and baked hand poses; no simulated finger bodies. */
UCLASS(ClassGroup=AI,meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFleshHandKnockdownComponent : public UActorComponent
{
 GENERATED_BODY()
public:
 UFleshHandKnockdownComponent();
 virtual void BeginPlay() override;
 virtual void TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Tick) override;
 bool Launch(APawn* Attacker,FVector Velocity,float DownSeconds,bool bForced=false);
 void Landed(const FHitResult& Hit);
 void ExtendControl(float Seconds);
 bool OnDeath();
 bool IsControlling() const {return !bCorpse&&OwnsPresentation();}
 bool OwnsPresentation() const {return Phase!=EFleshHandKnockdownPhase::None;}
 UPROPERTY(EditAnywhere,Category="Knockdown") bool bEnabled=true;
 UPROPERTY(EditAnywhere,Category="Knockdown",meta=(ClampMin="0.1",ClampMax="1.5")) float LaunchScale=.7f;
 UPROPERTY(EditAnywhere,Category="Knockdown",meta=(ClampMin="0",Units="s")) float GroundHoldSeconds=.65f;
 /** Baked maximum horizontal skin extent, including the side-supported get-up. */
 UPROPERTY(EditAnywhere,Category="Knockdown",meta=(ClampMin="1",Units="cm")) float FallCollisionRadius=140.f;
 UPROPERTY(EditDefaultsOnly,Category="Knockdown|Clips") TObjectPtr<UAnimSequence> LaunchPalmClip;
 UPROPERTY(EditDefaultsOnly,Category="Knockdown|Clips") TObjectPtr<UAnimSequence> LaunchBackClip;
 UPROPERTY(EditDefaultsOnly,Category="Knockdown|Clips") TObjectPtr<UAnimSequence> AirPalmClip;
 UPROPERTY(EditDefaultsOnly,Category="Knockdown|Clips") TObjectPtr<UAnimSequence> AirBackClip;
 UPROPERTY(EditDefaultsOnly,Category="Knockdown|Clips") TObjectPtr<UAnimSequence> LandPalmClip;
 UPROPERTY(EditDefaultsOnly,Category="Knockdown|Clips") TObjectPtr<UAnimSequence> LandBackClip;
 UPROPERTY(EditDefaultsOnly,Category="Knockdown|Clips") TObjectPtr<UAnimSequence> DownPalmClip;
 UPROPERTY(EditDefaultsOnly,Category="Knockdown|Clips") TObjectPtr<UAnimSequence> DownBackClip;
 UPROPERTY(EditDefaultsOnly,Category="Knockdown|Clips") TObjectPtr<UAnimSequence> GetUpPalmClip;
 UPROPERTY(EditDefaultsOnly,Category="Knockdown|Clips") TObjectPtr<UAnimSequence> GetUpBackClip;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Knockdown") EFleshHandKnockdownPhase Phase=EFleshHandKnockdownPhase::None;
private:
 AFleshHandMonster* Hand() const;
 void PlayPhase(EFleshHandKnockdownPhase Next,UAnimSequence* Clip,bool Loop=false);
 bool CapsuleFits(float Radius,float HalfHeight,const FVector& Center) const;
 void FinishRecovery();
 void FreezeCorpse();
 UPROPERTY(Transient) TObjectPtr<UAnimSequence> PlayingClip;
 float PhaseTime=0,BlendTime=0,DownHold=0,ProbeTime=0;
 float StandingRadius=0,StandingHalfHeight=0,AddedHalfHeight=0,StandingAirControl=0;
 double ControlUntil=0;
 FQuat StandingRotation=FQuat::Identity,GroundRotation=FQuat::Identity;
 ECollisionResponse StandingPawnResponse=ECR_Block;
 bool bPalmDown=true,bCorpse=false,bAutoOrient=true,bUpdateNavAgent=true;
};
