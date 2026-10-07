#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "MonsterCoreStats.h"
#include "HangingBellM09.generated.h"
class UAnimSequence;
class USkeletalMesh;
class UPhysicsAsset;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UStaticMesh;
class USoundBase;
class USoundAttenuation;
class UStaticMeshComponent;
class UInstancedStaticMeshComponent;
class UAudioComponent;
class UNiagaraComponent;
class UMonsterCombatComponent;
class UMonsterCorpseRagdollComponent;
class AM09CeilingRoute;
UENUM(BlueprintType)
enum class EM09State : uint8 { Idle,Travel,Returning,SwingLeft,SwingRight,Resonance,Gaze,Claw,Stagger,Dying,Corpse };
/** Shared BT decisions, explicit ceiling graph locomotion, one authoritative attack clock. */
UCLASS(Blueprintable)
class FPSGAME_API AHangingBellM09 : public ACharacter
{
 GENERATED_BODY()
public:
 AHangingBellM09();
 virtual void OnConstruction(const FTransform& Transform) override;
 virtual void BeginPlay() override;
 virtual void EndPlay(const EEndPlayReason::Type Reason) override;
 virtual void Tick(float DeltaSeconds) override;
 virtual float TakeDamage(float Damage,const FDamageEvent& Event,AController* Instigator,AActor* Causer) override;
 virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
 virtual FVector GetPawnViewLocation() const override;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="M09") TObjectPtr<UMonsterCombatComponent> Combat;
 UPROPERTY(VisibleAnywhere,Category="M09") TObjectPtr<UMonsterCorpseRagdollComponent> Corpse;
 UPROPERTY(EditDefaultsOnly,Category="M09|Assets") TObjectPtr<USkeletalMesh> VisualMesh;
 UPROPERTY(EditDefaultsOnly,Category="M09|Assets") TMap<FName,TObjectPtr<UAnimSequence>> Clips;
 UPROPERTY(EditDefaultsOnly,Category="M09|Assets") TMap<FName,TObjectPtr<USoundBase>> Sounds;
 UPROPERTY(EditDefaultsOnly,Category="M09|Assets") TObjectPtr<UStaticMesh> WaveMesh;
 UPROPERTY(EditDefaultsOnly,Category="M09|Assets") TObjectPtr<UMaterialInterface> EnergyMaterial;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M09|Stats") float MaxHealth=1250.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M09|Stats") float PhysicalAttack=42.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M09|Stats") float MagicAttack=38.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M09|Stats") int32 PhysicalDefense=30;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M09|Stats") int32 MagicalDefense=38;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M09|Stats") int32 Level=8;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M09|Stats") EMonsterRank Rank=EMonsterRank::Elite;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M09|Stats") int32 ExperienceReward=420;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M09|AI") float AggroRadius=2200.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M09|AI") float LeashRadius=2200.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M09|Movement") float CeilingSpeed=55.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M09|Death") float CorpseSeconds=25.f;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Replicated,Category="M09") float Health=1250.f;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,ReplicatedUsing=OnRep_State,Category="M09") EM09State State=EM09State::Idle;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="M09") FVector Home=FVector::ZeroVector;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="M09") TObjectPtr<AM09CeilingRoute> Route;
 UPROPERTY(Replicated) FVector GripTargets[2];
 UPROPERTY(Replicated) FRotator GripRotations[2];
 UPROPERTY(Replicated) double StateStartedAt=0.;
 UPROPERTY(Replicated) FVector LockedAim;
 UPROPERTY(Replicated) uint8 StaggerReleaseSide=0;
 UPROPERTY(Replicated) float ReactionSeconds=0;
 float StateSeconds=0.f;
 bool Dead() const{return Health<=0||State==EM09State::Dying||State==EM09State::Corpse;}
 bool Busy() const{return Dead()||(State>=EM09State::SwingLeft);}
 bool CanAttack(APawn* Victim) const;
 bool StartAttack(APawn* Victim);
 void SetTarget(APawn* Victim){Target=Victim;}
 void SetLocomotion(bool Moving,bool Returning=false);
 void NavigateCeiling(FVector Destination,bool Returning);
 void StopCeiling();
 FVector CeilingCenter() const{return GetActorLocation()+FVector(0,0,143);}
 void InitializeHang(AM09CeilingRoute* InRoute);
 void InterruptAttack(float Seconds);
 void StartHitPresentation();
 void SetHitPresentationTime(float Elapsed,float Remaining);
 void FinishHitReaction();
 bool HasAttackSight(const APawn* Victim) const;
 float HandIKWeight(int32 Side) const;
 bool IsWeakpointHit(const FHitResult& Hit) const;
 UFUNCTION(BlueprintCallable,Category="M09|Authoring") static bool BuildHitSurfacePhysics(USkeletalMesh* InMesh,UPhysicsAsset* HitAsset);
 UFUNCTION(BlueprintCallable,Category="M09|Authoring") static bool BuildPhysics(USkeletalMesh* InMesh,UPhysicsAsset* Asset);
 UFUNCTION(BlueprintCallable,Category="M09|Authoring") static FString DescribePhysics(USkeletalMesh* InMesh);
 UFUNCTION(BlueprintCallable,Category="M09|Authoring") static void ConfigureReturnPortal(AActor* Portal);
 UFUNCTION(BlueprintCallable,Category="M09|Development") bool TriggerAttack(FName Attack);
private:
 UFUNCTION() void OnRep_State();
 void AlignVisual();
 void RefreshHitPhysics();
 void SetState(EM09State Next);
 void PresentState();
 UAnimSequence* Clip(FName Key) const;
 void Sample(float Time);
 void TickCeiling(float Dt);
 void TickGrips(float Dt,bool Moving);
 bool ResolveCeilingGrip(const FTransform& Frame,int32 Side,FVector& Position,FQuat& Rotation) const;
 void FollowCeilingHeight(float Dt);
 void UpdateCeilingAnimationRate();
 void TickAttack(float Previous);
 void UpdateFX();
 void EnterDeath();
 void Deal(APawn* Victim,float Damage,bool Magic,FVector HitPoint);
 void SweepContact(FVector From,FVector To,float Radius,float Damage);
 bool CanClawReach(const APawn* Victim) const;
 bool InClawRange(const APawn* Victim) const;
 bool CanGazeReach(const APawn* Victim) const;
 EM09State SelectAttack(APawn* Victim) const;
 void SweepClawContact(int32 Side,bool ResetPrevious);
 void ResonancePulse();
 void CaptureResonanceAim();
 bool HasResonanceSight(const APawn* Victim,FVector Origin) const;
 void GazePulse();
 void CreateGazeFX();
 void InitializeGazeFX();
 void ClearGazeFX();
 void UpdateGazeFX();
 void CaptureGazeAim();
 void QueryGazeBeam(FVector& From,FVector& End,FHitResult& Hit) const;
 FVector Eye() const;
 FName StateClip() const;
 USoundAttenuation* OneShotAttenuation(float Falloff) const;
 EM09State PresentedState=EM09State::Idle;
 UPROPERTY() TObjectPtr<UAudioComponent> Voice;
 UPROPERTY() TObjectPtr<UStaticMeshComponent> Beam;
 UPROPERTY() TObjectPtr<UStaticMeshComponent> Charge;
 UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> GazeIrises;
 UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> GazeFilaments;
 UPROPERTY() TArray<TObjectPtr<UNiagaraComponent>> GazeGatherSystems;
 UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> GazeBeamMID;
 UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> GazeIrisMID;
 UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> GazeFilamentMID;
 UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> GazeImpactMID;
 UPROPERTY(Replicated) FVector GazeDirection=FVector::ForwardVector;
 EM09State LastProductionAttack=EM09State::Idle;
 FVector GazeEyeLocalForward[5];
 UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Waves;
 TWeakObjectPtr<APawn> Target;
 TArray<FVector> Path;
 FVector LastDestination=FVector::ZeroVector,PreviousContact[2];
 FVector GripRest[2],GripStart,GripEnd;
 FQuat GripRotationStart,GripRotationEnd,GripRestRotation[2];
 TSet<TWeakObjectPtr<APawn>> HitVictims;
 float Cooldown[4]={0,2,3,0};
 float GlobalCooldown=0,PathAge=1,SupportAge=0;
 float GripClock=0,DesiredYaw=0,GripClearance[2]={28,28};
 bool bGripMoving=false,bWantsMove=false,bReturning=false,bInitialized=false,bGazeLocked=false,bRewarded=false;
 int32 GripSide=0,NextPulse=0,SwingCount=0;
 // All resonance pulses share one locked emission frame.
 UPROPERTY(EditDefaultsOnly,Category="M09|Assets") TObjectPtr<UMaterialInterface> ResonanceMaterial;
 UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> WaveMaterials;
 UPROPERTY(Replicated) FVector ResonanceOrigin=FVector::ZeroVector;
 UPROPERTY(Replicated) FVector ResonanceDirection=FVector::ForwardVector;
 // Append replicated cadence without moving the existing reflected members.
 UPROPERTY(Replicated) float CeilingAnimationRate=2.f;
 UPROPERTY(EditDefaultsOnly,Category="M09|Assets") TObjectPtr<UPhysicsAsset> HitSurfacePhysics;
 // Authoritative surface target is separate from the smoothly following body.
 float CeilingSurfaceHeight=0.f;
};
