#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "ColdSteelEnchantmentCombat.generated.h"

struct FColdSteelShotEffects {int32 Piercing=0,Poison=0;};
struct FColdSteelItem;
// 在命名空间外前置声明：命名空间内的 `class X` 会新建 ColdSteelCombat::X 并遮蔽真实类型。
class UColdSteelEnhancementSystem;
struct FWeaponHandling;
/** 涡轮增压（附魔）：持续开火时攻击间隔由 StartMultiplier 线性过渡到 PeakMultiplier。 */
struct FColdSteelTurboRamp
{
    bool Enabled=false;
    double StartMultiplier=1.,PeakMultiplier=1.,Seconds=0.;
};
/** 汇聚（附魔）：一次射击打空弹匣，单发按消耗发数与 DamageScale 聚合结算。 */
struct FColdSteelConvergence
{
    bool Enabled=false;
    double DamageScale=0.;
};
namespace ColdSteelCombat
{
    struct FBigBlind
    {
        bool Enabled=false;
        float CriticalBonusPerStack=0.f,Seconds=0.f;
        int32 MaxStacks=0;
    };
    FPSGAME_API FBigBlind BigBlind(const UColdSteelEnhancementSystem* Enhancement,const FColdSteelItem* Item);
    struct FComposure
    {
        bool Enabled=false;
        float StabilityPerStack=0.f,RecoilReductionPerStack=0.f,Seconds=0.f;
        int32 MaxStacks=0;
    };
    FPSGAME_API FComposure Calm(const UColdSteelEnhancementSystem* Enhancement,const FColdSteelItem* Item);
    /** Temporary player buff on composed firearm stats; never write it into equipment. */
    FPSGAME_API FWeaponHandling ComposureHandling(AActor* Shooter,const FWeaponHandling& Base);
    FPSGAME_API float ComposureRecoilMultiplier(AActor* Shooter);
    FPSGAME_API FColdSteelShotEffects Snapshot(AActor* Shooter,const FColdSteelItem* Item=nullptr);
    FPSGAME_API void OnHit(AActor* Target,AActor* Shooter,int32 Poison);
    // 三个数值同属一次附魔，缺一项即视为未附魔，避免半套数据改动射速。
    FPSGAME_API FColdSteelTurboRamp TurboRamp(const UColdSteelEnhancementSystem* Enhancement,const FColdSteelItem* Item);
    // 持续开火 HeldSeconds 后的攻击间隔倍率；未附魔恒为 1。
    FPSGAME_API double TurboIntervalMultiplier(const FColdSteelTurboRamp& Ramp,double HeldSeconds);
    // 开关与倍率同属一次附魔，缺一项即视为未附魔。
    FPSGAME_API FColdSteelConvergence Convergence(const UColdSteelEnhancementSystem* Enhancement,const FColdSteelItem* Item);
    // 本发聚合倍率：消耗 Rounds 发时，单发伤害 = 单发基础伤害 × Rounds × DamageScale。
    FPSGAME_API double ConvergenceShotScale(const FColdSteelConvergence& Convergence,int32 Rounds);
}
/** Target-owned poison; one damage per stack per second, one stack fades every five seconds; no dependence on later weapon swaps. */
UCLASS()
class FPSGAME_API UColdSteelPoisonComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    void AddStacks(AActor* Source,int32 Amount);
    int32 GetStacks()const{return Stacks;}
    void Pulse();
protected:
    virtual void EndPlay(const EEndPlayReason::Type)override;
private:
    int32 Stacks=0,TicksLeft=0;
    TWeakObjectPtr<AActor> Shooter;
    TWeakObjectPtr<AController> Instigator;
    FTimerHandle Timer;
};
