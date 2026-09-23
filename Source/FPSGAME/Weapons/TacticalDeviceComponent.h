#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "TacticalDeviceComponent.generated.h"

UCLASS()
class FPSGAME_API UTacticalDeviceComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UTacticalDeviceComponent();
    void Configure(const FString& Family,const FString& Variant,class USkeletalMeshComponent* Rifle,bool Enabled);
    void SetPresentationHidden(bool Hidden);
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Function) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    FString Kind,AssetPath;
    bool bPresentationHidden=false;
    /**
     * 开镜对齐的时间窗（秒）。开镜过渡期间光束保持沿枪管，等 ADS 完全到位
     * （WeaponADSFactor >= ADSSettleThreshold）后才在这么长的时间内迅速转到准星。
     * 过渡期就提前扳光束会让激光在抬枪过程中乱扫，所以改用"到位后快速对齐"。
     */
    float LaserConvergeSeconds=0.08f;
    /** ADS 视为"已完成"的因子阈值；1.0 表示必须完全到位。 */
    float ADSSettleThreshold=1.0f;
    /** 上一帧 ADS 是否已到位（用于检测进入到位状态的那一刻）。 */
    bool bLaserSettled=false;
    /** 已到位并开始对齐至今的秒数；对齐按这个时间解析求值，与帧率无关。 */
    float LaserSettleElapsed=0.f;
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> Body;
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> Dot;
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> Beam;
    UPROPERTY(Transient) TObjectPtr<class USpotLightComponent> Light;
    UPROPERTY(Transient) TObjectPtr<class USkeletalMeshComponent> Host;
    void HideEffects();
    /** 挂件或武器变化时丢弃上一件的对齐状态。 */
    void ResetLaserAim();
};
