#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Engine/NetSerialization.h"
#include "WoodenTorchComponent.generated.h"

class UCameraComponent;
class UWoodenTorchArmsComponent;
class UColdSteelStatusModel;
class UStaticMeshComponent;
class UNiagaraComponent;
class UPointLightComponent;
struct FStreamableHandle;

UCLASS()
class FPSGAME_API UWoodenTorchComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UWoodenTorchComponent();
    void SurfaceContact(const FHitResult& Hit,uint32 OrdinarySwingSerial=0);
    bool PublishSurfaceContact(const FVector& Point,const FVector& Normal,float Reach);
    void EnemyContact(const FHitResult& Hit);
    static constexpr const TCHAR* MeshPath = TEXT("/Game/Weapons/WoodenTorch20261122/HearthWrapR7/SM_WrappedHearthTorch.SM_WrappedHearthTorch");
    void RefreshEquipment(const UColdSteelStatusModel& Profile,int32 ActiveMainSlot);
    void SetWorldProp(int32 Side, UStaticMeshComponent* Prop);
    const FString& LeftInstance() const { return Instances[1]; }
    bool HoldsRight() const { return !Instances[0].IsEmpty(); }
    USkeletalMeshComponent* HandForMotion(int32 Side) const;
    bool ShowsRight() const { return bPresented[0]; }
    bool HoldsLeft() const { return !Instances[1].IsEmpty(); }
    bool UsesRightClickAttack() const { return HoldsLeft() && !bPistolMain; }
    bool UsesQuickAttack() const { return QuickHand!=INDEX_NONE; }
    int32 QuickAttackHand() const { return QuickHand; }
    UStaticMeshComponent* ReadyPairedOffhand() const;
    bool ShowsLeft(const USceneComponent* Except) const;
    virtual void TickComponent(float Delta, ELevelTick Type, FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(Transient) TObjectPtr<UWoodenTorchArmsComponent> Arms[2];
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Props[2];
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> Flames[2];
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> FlameVolumes[2];
    UPROPERTY(Transient) TObjectPtr<UPointLightComponent> Lights[2];
    TWeakObjectPtr<UStaticMeshComponent> WorldProps[2];
    FString Instances[2];
    float RaiseAge[2]{};
    float GaitWeight[2]{};
    float SprintBlend = 0.f;
    bool bPresented[2]{};
    bool bFullFire[2]{true,true};
    bool bFlameInView[2]{};
    double NextViewAt[2]{};
    double NextShedAt[2]{};
    double NextWindSampleAt = 0.;
    FVector AmbientWind = FVector::ZeroVector;
    FVector AirLeanWorld = FVector::ZeroVector;
    FVector2D LastSlope[2]{FVector2D::ZeroVector, FVector2D::ZeroVector};
    struct FHandAirflow
    {
        TWeakObjectPtr<USceneComponent> Mount;
        FVector PreviousTip = FVector::ZeroVector;
        FVector DragWorld = FVector::ZeroVector;
    };
    FHandAirflow HandAir[2];
    bool bPistolMain = false;
    int32 QuickHand = INDEX_NONE;
    FString QuickMainInstance,QuickOffInstance;
    bool bLocalAssetsRequested = false;
    TSharedPtr<FStreamableHandle> Assets;
    void RequestAssets();
    void PrepareHand(int32 Side);
    void UpdateFlameWind(float DeltaSeconds);
    void SetFire(int32 Side, UStaticMeshComponent* Parent,bool bInHand=false);

    UFUNCTION(NetMulticast,Unreliable) void MulticastEmbers(FVector_NetQuantize10 Point,FVector_NetQuantizeNormal Normal,bool bOwnerPresented);
    UCameraComponent* LocalEmberCamera() const;
    void DrawEmbers(const FVector& Point,const FVector& Normal) const;
    double LastSurfaceReport=-1.;
};
