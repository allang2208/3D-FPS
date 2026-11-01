#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "ThunderHammerThrown.generated.h"
class UStaticMeshComponent;
class USceneComponent;
class UAudioComponent;
class USoundBase;
struct FStreamableHandle;

/** A weapon instance in flight, on the floor, or returning. Never an inventory duplicate. */
UCLASS()
class FPSGAME_API AThunderHammerThrown : public AActor
{
    GENERATED_BODY()
public:
    AThunderHammerThrown();
    void Launch(const FColdSteelItem& Item,const FColdSteelSkillShot& Shot,float Magic);
    void Recall();
    void ReturnToStorage();
    bool IsStillEquipped(const FColdSteelProfile& Profile) const;
    bool IsGrounded() const {return Phase==1;}
    bool IsReturning() const {return Phase==2;}
    bool IsCatching() const {return Phase==3;}
    float RecallAge() const;
    float CatchAge() const;
    const FString& Instance() const {return Weapon.InstanceId;}
    virtual void Tick(float Delta) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
private:
    friend class UWarhammerNetworkAuditCommandlet;
    friend class UThunderHammerRecallAuditCommandlet;
    friend class UWarhammerModificationAuditCommandlet;
    friend class AThunderHammerWireController;
    friend class AThunderHammerWireGameMode;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Visual;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Mesh;
    UPROPERTY(ReplicatedUsing=PrepareVisual) FColdSteelItem Weapon;
    UPROPERTY(Replicated) uint8 Phase=0;
    UPROPERTY(Replicated) double StartedAt=0.;
    UPROPERTY(Replicated) double RecallAt=0.;
    UPROPERTY(Replicated) double CaughtAt=0.;
    UPROPERTY(Replicated) float RecallDuration=.5f;
    UPROPERTY(Replicated) FVector RecallFrom=FVector::ZeroVector;
    UPROPERTY(Replicated) FVector RecallAxis=FVector::RightVector;
    UPROPERTY(Replicated) FQuat InitialRotation=FQuat::Identity;
    UPROPERTY(Replicated) float FlightYaw=0.f;
    FColdSteelSkillShot DamageShot;
    FColdSteelSkillShot RecallShot;
    TSet<TWeakObjectPtr<AActor>> RecallHits;
    int32 RecallMasteryHits=0;
    FVector RecallControl=FVector::ZeroVector,RecallGoal=FVector::ZeroVector;
    FVector Velocity=FVector::ZeroVector;
    float MagicDamage=0.f,Accumulator=0.f,OwnerCheck=0.f;
    FTimerHandle StaticFieldTimer;
    void PulseStaticField();
    FTimerHandle CoilTimer;
    void PulseCoil();
    TSharedPtr<FStreamableHandle> Assets;
    TSharedPtr<FStreamableHandle> AudioAssets;
    UFUNCTION() void PrepareVisual();
    UFUNCTION(NetMulticast,Reliable) void MulticastRetireFromEquipment();
    UFUNCTION(NetMulticast,Reliable) void MulticastCaught(double ContactTime);
    void BuildVisual();
    void BuildRecallAudio();
    void Land(const FHitResult& Hit);
    void AdvanceRecall(float Delta);
    void HitRecallSegment(const FVector& From,const FVector& To);
    FQuat RecallRotation() const;
    float RecallSpinTurns() const;
    double Clock() const;
    UPROPERTY(Transient) TObjectPtr<USoundBase> RecallMetalSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> RecallAirSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> RecallCatchSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> RecallThrowWhooshSound;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> RecallMetalAudio;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> RecallAirAudio;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> RecallThrowWhooshAudio;
    bool bRecallCatchAudioPlayed=false;
    void TickRecallAudio();
    void StopRecallAudio(float FadeSeconds);
    void PlayRecallCatchAudio();
};
