#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "HandBrainFearComponent.generated.h"
class AController;
class UCameraComponent;
class UMaterialInstanceDynamic;
class UAudioComponent;
UCLASS(ClassGroup=(Combat),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UHandBrainFearComponent : public UActorComponent
{
 GENERATED_BODY()
public:
 UHandBrainFearComponent();
 void Apply(AActor* Source);
 virtual void TickComponent(float Dt,ELevelTick TickType,FActorComponentTickFunction* Tick) override;
 virtual void EndPlay(const EEndPlayReason::Type Reason) override;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Fear") int32 Stacks=0;
 float GetRemainingSeconds() const;
 /** 净化通道（旧 SUPPORT_CLEANSE_TYPES 含 fear）：有层数才结算释放。 */
 void Cleanse(){if(Stacks>0)Release();}
private:
    friend class UFPSStatusReplicationComponent;
 void Release();
 void UpdatePsychicFeedback(float Dt);
 void StopPsychicFeedback();
 TWeakObjectPtr<UCameraComponent> PsychicCamera;
 TWeakObjectPtr<AActor> PsychicFeedbackSource;
 UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> PsychicView;
 UPROPERTY(Transient) TObjectPtr<UAudioComponent> PsychicEarVoice;
 float PsychicFeedbackAge=0.f;
 TWeakObjectPtr<AActor> Threat;
 TWeakObjectPtr<AController> LockedController;
 TArray<double> Expirations;
 float RestoreSpeed=0;
};
