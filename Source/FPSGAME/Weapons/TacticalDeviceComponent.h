#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "TacticalDeviceComponent.generated.h"

struct FFPSBodyLaserSample;

UCLASS()
class FPSGAME_API UTacticalDeviceComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UTacticalDeviceComponent();
    void Configure(const FString& Family,const FString& Variant,class USkeletalMeshComponent* Rifle,bool Enabled,bool OppositeSide=false);
    void ConfigureWorld(const FString& Variant,class USkeletalMeshComponent* Rifle,class UStaticMeshComponent* Device,
        bool bAuthoredAxis,uint8 RigIndex,uint8 PartIndex,uint32 Schema);
    bool DescribePart(const class UStaticMeshComponent* Part,FName& Variant,bool& bAuthoredAxis) const;
    bool ReadLaserSample(FFPSBodyLaserSample& Out) const;
    void SetPresentationHidden(bool Hidden);
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Function) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    FString Kind,AssetPath;
    bool bUseAuthoredEmitterAxis=false;
    bool bPresentationHidden=false;
    bool bWorldPresentation=false;
    /** Finite blend between the native barrel axis and the ready gun's aim point. */
    float LaserConvergeSeconds=0.08f;
    /** ADS 视为"已完成"的因子阈值；1.0 表示必须完全到位。 */
    float ADSSettleThreshold=1.0f;
    float LaserAimBlend=0.f;
    uint8 WorldRigIndex=0,WorldPartIndex=0;
    uint32 WorldSchema=0;
    bool bLaserSampleValid=false,bLaserSampleDot=false;
    double LaserSampleAt=-100.;
    FVector LaserSampleEnd=FVector::ZeroVector,LaserSampleNormal=FVector::UpVector;
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> Body;
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> Dot;
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> Beam;
    UPROPERTY(Transient) TObjectPtr<class USpotLightComponent> Light;
    UPROPERTY(Transient) TObjectPtr<class USkeletalMeshComponent> Host;
    void HideEffects();
    void InitializeEffects();
    /** 挂件或武器变化时丢弃上一件的对齐状态。 */
    void ResetLaserAim();
    UPROPERTY(Transient) TObjectPtr<class UMaterialInterface> BlessedDotMaterial;
    UPROPERTY(Transient) TObjectPtr<class UMaterialInterface> BlessedBeamMaterial;
    UPROPERTY(Transient) TObjectPtr<class UMaterialInterface> RedDotMaterial;
    UPROPERTY(Transient) TObjectPtr<class UMaterialInterface> RedBeamMaterial;
};
