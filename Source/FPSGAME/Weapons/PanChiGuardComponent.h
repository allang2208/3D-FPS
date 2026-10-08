#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Engine/NetSerialization.h"
#include "GunsmithSystem.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "PanChiGuardComponent.generated.h"

class UColdSteelStatusModel;
class UDynamicMeshComponent;
class UStaticMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class USoundBase;
struct FStreamableHandle;
struct FHitResult;
struct FColdSteelSkillShot;

/** Equipped-only Pan Chi guard. Charges and releases are settled by the server. */
UCLASS()
class FPSGAME_API UPanChiGuardComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UPanChiGuardComponent();
    void Configure(const UColdSteelStatusModel* InProfile);
    void ConfirmGuard(bool bPerfect);
    void SetGuardIntent(bool bRaised);
    float ResolveRemoteGuard(float Damage,const UDamageType* Type,AController* Instigator,AActor* Causer);
    static void StampBladeAttack(AActor* Owner,FColdSteelSkillShot& Shot);
    bool CanEmpowerUppercut() const;
    float UppercutToughnessMultiplier(const FColdSteelSkillShot& Shot) const;
    void ReleaseUppercutDragon(const FTransform& Aim,float HeavyDamage,const FColdSteelSkillShot& Shot,USoundBase* HitSound);
    int32 Charges() const;
    float Remaining() const;
    float CooldownRemaining() const;
    float Duration() const {return Modifiers.PanChiSeconds;}
    float CooldownDuration() const {return Modifiers.PanChiCooldown;}
    bool IsActive() const;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
protected:
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    double Clock() const;
    bool IsUppercutHit(const FColdSteelSkillShot& Shot) const;
    void ClearCharges();
    void Publish();
    void TickDragonFlight(float Delta);
    void ApplyReleasePull(const FVector& Center);
    void RequestVisuals();
    void RefreshGuardVisual();
    void TickReleaseVisual();
    void BuildSpiritMeshes();
    void BuildLaunchCircle();
    void TickLaunchCircle(float Age);
    UFUNCTION() void OnRep_Charges();
    UFUNCTION(Server,Reliable) void ServerSetGuardIntent(bool bRaised);
    UFUNCTION(Server,Reliable) void ServerReleaseDragon(uint32 Serial,const FString& SourceInstance,FRotator AimRotation);
    UFUNCTION(NetMulticast,Reliable) void MulticastRelease(FVector_NetQuantize Origin,FRotator Rotation,double At,uint8 SpentCharges,float RangeCM,float SpeedCM);
    UFUNCTION(NetMulticast,Reliable) void MulticastStopDragon(double ReleasedAt,float TravelCM,double StoppedAt);
    TWeakObjectPtr<const UColdSteelStatusModel> Profile;
    FString EquippedInstance,EquippedData;
    FMeleeModifiers Modifiers;
    uint32 AttackSerial=0,ConsumedAttackSerial=0;
    float ConsumedToughness=1.f;
    bool bRemoteGuard=false,bVisualsRequested=false;
    double RemoteGuardStarted=0.,ReleaseAt=-100.;
    FVector ReleaseOrigin=FVector::ZeroVector;
    FRotator ReleaseRotation=FRotator::ZeroRotator;
    TSharedPtr<FStreamableHandle> VisualLoad;
    TWeakObjectPtr<UStaticMeshComponent> GuardMesh;
    UPROPERTY(ReplicatedUsing=OnRep_Charges) int32 StoredCharges=0;
    UPROPERTY(ReplicatedUsing=OnRep_Charges) double ChargesEnd=0.;
    UPROPERTY(ReplicatedUsing=OnRep_Charges) double ReadyAt=0.;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> GuardMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> GuardMID;
    // One bounded flight per holder; authority owns damage and stop distance.
    float ReleaseVisualSeconds=1.f;
    uint8 ReleaseCharges=1;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> SpiritMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> MoteMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> SpiritMID;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> MoteMID;
    UPROPERTY(Transient) TObjectPtr<UDynamicMeshComponent> SpiritMesh;
    UPROPERTY(Transient) TObjectPtr<UDynamicMeshComponent> MoteMesh;
    float FlightRangeCM=1200.f,FlightSpeedCM=1800.f,FlightTravelCM=0.f;
    float FlightDamage=0.f,FlightPullCM=300.f;
    double FlightStoppedAt=-1.;
    bool bFlightActive=false;
    FColdSteelSkillShot FlightShot;
    TSet<TWeakObjectPtr<AActor>> FlightHitActors;
    UPROPERTY(Transient) TObjectPtr<USoundBase> FlightHitSound;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> CircleMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> CircleMID;
    UPROPERTY(Transient) TObjectPtr<UDynamicMeshComponent> CircleMesh;
    double CircleBuiltAt=-100.;
};
