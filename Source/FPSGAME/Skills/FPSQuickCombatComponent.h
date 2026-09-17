#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "QuickCombatPistolMotion.h"
#include "FPSQuickCombatComponent.generated.h"
class AFPSGAMECharacter;
class UColdSteelStatusModel;
class USoundBase;

UENUM(BlueprintType)
enum class EQuickCombatBashPhase : uint8 { None, Release, Cock, Smash, Recover };

// 手枪版「快速进战」：单持时松开左手，右手持枪以握把前砸。
// 只负责动作时钟、接触结算与技能提交；武装仲裁在角色侧（TriggerPistolQuickCombat）。
UCLASS(ClassGroup=(Skills),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSQuickCombatComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSQuickCombatComponent();
    /** 姿态层入口：武装仲裁通过后由角色调用；提交冷却与使用修炼。 */
    bool BeginAction();
    void Cancel();
    UFUNCTION(BlueprintPure,Category="Skills|QuickCombat") bool IsOccupyingLeftHand() const { return Phase!=EQuickCombatBashPhase::None; }
    UFUNCTION(BlueprintPure,Category="Skills|QuickCombat") EQuickCombatBashPhase GetPhase() const { return Phase; }
    /** 当前阶段内进度 0..1，供姿态层采样。 */
    UFUNCTION(BlueprintPure,Category="Skills|QuickCombat") float PhaseFraction() const;
    uint32 GetActionSerial() const { return Serial; }
protected:
    virtual void BeginPlay() override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    EQuickCombatBashPhase Phase=EQuickCombatBashPhase::None;
    float PhaseAge=0.f;
    uint32 Serial=0;
    bool bContactDone=false,bKillPending=false;
    UPROPERTY(Transient) TObjectPtr<USoundBase> ImpactSound;
    void AdvancePhase(float Delta);
    void ContactHit();
    void FinishAction();
    UColdSteelStatusModel* Model() const;
};
