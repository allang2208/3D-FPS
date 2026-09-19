#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "QuickCombatPistolMotion.h"
#include "QuickCombatRifleMotion.h"
#include "FPSQuickCombatComponent.generated.h"
class AFPSGAMECharacter;
class UColdSteelStatusModel;
class USoundBase;

UENUM(BlueprintType)
enum class EQuickCombatBashPhase : uint8 { None, Release, Cock, Smash, Follow, Recover };

// 枪械版「快速进战」：手枪 = 单持松左手、握把底前砸；步枪 = 双手持枪的枪托/枪身前段砸击。
// 只负责动作时钟、接触结算与技能提交；武装仲裁在角色侧
// （TriggerPistolQuickCombat / TriggerRifleStockMelee）。
// 单一绝对时钟 ActionAge 驱动阶段/镜头/接触点，全部由 clip 长度换算，不逐段累计。
// 两种武器的动作本体都在作者源 clip 里（手枪 DW715、步枪 M4 六个握把配置），
// 本组件不参与姿态——只给出命中探针来源、结算时机与镜头语言。
enum class EQuickCombatStyle : uint8 { Pistol, Rifle };

UCLASS(ClassGroup=(Skills),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSQuickCombatComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSQuickCombatComponent();
    /** 动作入口：武装仲裁通过后由角色调用；提交冷却与使用修炼。 */
    bool BeginAction();
    void Cancel();
    UFUNCTION(BlueprintPure,Category="Skills|QuickCombat") bool IsOccupyingLeftHand() const { return Phase!=EQuickCombatBashPhase::None; }
    UFUNCTION(BlueprintPure,Category="Skills|QuickCombat") EQuickCombatBashPhase GetPhase() const { return Phase; }
    /** 当前阶段内进度 0..1（回握交还动画用）。 */
    UFUNCTION(BlueprintPure,Category="Skills|QuickCombat") float PhaseFraction() const;
    /** 动作绝对时间（秒）：姿态层按它采样关键帧表。 */
    UFUNCTION(BlueprintPure,Category="Skills|QuickCombat") float GetActionAge() const { return ActionAge; }
    /** 姿态层权重：跟随段之前为 1，回握段收到 0 交还动画。 */
    UFUNCTION(BlueprintPure,Category="Skills|QuickCombat") float LayerWeight() const;
    /** 按实际 clip 长度推导接触/阶段时间（作者源改节奏不会与结算脱节）。 */
    void ConfigureForClipLength(float Length);
    /** 切换为步枪枪托砸击，并按实际 clip 长度推导时间轴。 */
    void ConfigureForRifle(float Length);
    EQuickCombatStyle GetStyle() const { return Style; }
    /** 镜头语言（配重锤 GetCameraMotion 同款合同）：相机空间位置 cm 与旋转度。 */
    void GetCameraMotion(FVector& Location,FRotator& Rotation) const;
    uint32 GetActionSerial() const { return Serial; }
protected:
    virtual void BeginPlay() override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    EQuickCombatStyle Style=EQuickCombatStyle::Pistol;
    EQuickCombatBashPhase Phase=EQuickCombatBashPhase::None;
    float ActionAge=0.f;
    // 运行时时间轴（由 clip 长度换算）
    float ReleaseEnd=0.f, CockEnd=0.f, ContactTime=0.f, FollowEnd=0.f, AttackEnd=0.f;
    float ClipLength=0.f;
    float ImpactAge=1.f;   // 1=无冲量；命中置 0，Tick 内衰减
    float ImpactStrength=0.f;
    uint32 Serial=0;
    bool bContactDone=false,bKillPending=false;
    UPROPERTY(Transient) TObjectPtr<USoundBase> ImpactSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> SwingSound;
    void ContactHit();
    void FinishAction();
    EQuickCombatBashPhase PhaseForAge(float Age) const;
    UColdSteelStatusModel* Model() const;
};
