#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameFramework/DamageType.h"
#include "CombatStatusFormula.generated.h"

UCLASS()
class FPSGAME_API UCombatDirectDamage : public UDamageType { GENERATED_BODY() };

/** Status-driven magic damage (mine gas, revive-agnostic DoTs); consumes the magic-defense chain. */
UCLASS()
class FPSGAME_API UStatusMagicDamage : public UDamageType { GENERATED_BODY() };

/** Target-owned temporary reductions; seconds in UE, milliseconds in gamedev. */
UCLASS(ClassGroup=(Combat),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UCombatStatusFormula : public UActorComponent
{
    GENERATED_BODY()
public:
    UCombatStatusFormula();
    UFUNCTION(BlueprintCallable) static UCombatStatusFormula* GetOrAdd(AActor* Target);
    UFUNCTION(BlueprintCallable) void AddCorrosion(int32 Stacks=1,float Seconds=5,float ReductionPerStack=.05f);
    UFUNCTION(BlueprintCallable) void AddMagicResistanceShred(float Ratio,float Seconds);
    UFUNCTION(BlueprintCallable) void AddHolyWard(float Multiplier,float Seconds);
    UFUNCTION(BlueprintCallable) void AddMagicVulnerability(int32 Stacks=1);
    void AddRuneMagicVulnerability(float Ratio,float Seconds);
    void GrantRiposteGuard(float Seconds,float AttackSpeed,float Stamina);
    float RiposteAttackSpeed()const{return RiposteTime>0?RiposteSpeed:1;}
    float RiposteStaminaMultiplier()const{return RiposteTime>0?RiposteStamina:1;}
    UFUNCTION(BlueprintCallable) void AddBleeding(AActor* Source,int32 Stacks=1);
    UFUNCTION(BlueprintCallable) void AddBurn(AActor* Source,float MagicAttack,int32 Stacks=1,float Seconds=3,float DamageMultiplier=.5f,float TickSeconds=.5f);
    UFUNCTION(BlueprintCallable) void SetStatusImmune(bool Immune);
    bool IsImmune()const{return bImmune||ImmuneTime>0;}
    /** 状态免疫（计时版）：免疫一切增减益状态；到期自动解除。旧 applyStatusImmune。 */
    UFUNCTION(BlueprintCallable) void AddStatusImmune(float Seconds);
    // Returns true once at the overload threshold. The spell owns the resulting chain.
    bool AddElectrified(int32 Stacks,float Seconds,int32 OverloadThreshold,float BonusPerStack);
    float ElectricMultiplier()const{return ElectrifiedTime>0?1+ElectrifiedStacks*ElectrifiedBonus:1.f;}

    // ===== gamedev 状态机制迁移（旧 DamageableEntity.apply* 家族） =====
    /** 眩晕：移速/闪避/动作封锁 + 状态栏卡片；玩家额外走破防输入锁。旧 applyStun。 */
    UFUNCTION(BlueprintCallable) void AddStun(float Seconds);
    /** 束缚：移速/闪避封锁，施法与攻击不受影响。旧 applyBind。 */
    UFUNCTION(BlueprintCallable) void AddBind(float Seconds);
    /** 减速（默认 -50% 移速）。旧 'slow' 状态。 */
    UFUNCTION(BlueprintCallable) void AddSlow(float Seconds,float Percent=.5f);
    /** 致残：机制同 -50% 减速，显示借用 slow 类型（🦴 致残）。旧 applyCripple。 */
    UFUNCTION(BlueprintCallable) void AddCripple(float Seconds);
    /** 封蜡减速：只刷新时间与数值不叠层，封顶 90%。旧 applyWaxSealSlow。 */
    UFUNCTION(BlueprintCallable) void AddWaxSeal(float Seconds,float Percent=.2f);
    /** 命中动能（P4040 等）：独立乘区、只刷新；与通用加速互不干扰。旧 applyWeaponHaste。 */
    UFUNCTION(BlueprintCallable) void AddWeaponHaste(float Seconds,float Percent=.10f);
    /** 石化：定格动作 + 魔法/电系承伤 ×MagicTakenMul。旧 applyPetrify。 */
    UFUNCTION(BlueprintCallable) void AddPetrify(float Seconds,float MagicTakenMul=1.5f);
    /** 标记（铁匠铺能力）：受所有伤害 ×(1+Value)，重复取更高 value。旧 addStatusEffect('marked')。 */
    UFUNCTION(BlueprintCallable) void AddMarked(float Seconds,float Value=.15f);
    /** 激励：移速 ×SpeedMul、攻击 ×AtkMul；已存在只刷新时长。旧 applyInspire。 */
    UFUNCTION(BlueprintCallable) void AddInspire(float Seconds,float SpeedMul=1.33f,float AtkMul=1.5f);
    /** 骆驼惊吓（受击者侧来源减伤）：自身输出 ×(1-Reduction)。旧 applyCamelFright。 */
    UFUNCTION(BlueprintCallable) void AddCamelFright(float Seconds,float Reduction=.1f);
    /** 矿毒：由毒区每帧刷新，离开后按 linger（默认3s）残留；每秒 maxHp×0.5% 魔法伤害。 */
    UFUNCTION(BlueprintCallable) void AddMinePoison(float RefreshSeconds,float LingerSeconds=3.f);
    /** 无人机易伤：按来源标记，最强快照生效；玩家侧攻击享受承伤/暴击加成。旧 applyDroneVulnerability。 */
    UFUNCTION(BlueprintCallable) void AddDroneMark(FName SourceId,float DamageBonusPercent,float CritBonusPercent,float Seconds,AActor* MarkOwner=nullptr);
    UFUNCTION(BlueprintCallable) void RemoveDroneMark(FName SourceId,bool bImmediate=true);
    /** 仅当攻击者是受益阵营（玩家/友军/召唤物）时返回 >1 的加成。 */
    float DroneDamageMultiplier(const AActor* Attacker)const;
    /** 受益攻击者对被标记目标的暴击率加成（百分点）。 */
    float DroneCritBonusPercent(const AActor* Attacker)const;
    bool IsStunned()const{return StunTime>0;}
    bool IsFrozen()const{return FrozenTime>0;}
    bool IsPetrified()const{return PetrifyTime>0;}
    bool IsMinePoisoned()const{return MineTime>0;}
    /** 眩晕/束缚/冻结/石化封锁闪避与位移（施法攻击不受此闸影响）。 */
    bool BlocksMovement()const{return FrozenTime>0||StunTime>0||BindTime>0||PetrifyTime>0;}
    void AddChill(int32 Stacks,float Seconds,float SlowPerStack);
    void AddHaste(int32 Stacks,float Seconds);
    void AddChainSpell();
    void ConsumeChainSpell();
    int32 ChainSpellStacks()const{return ChainTime>0?ChainStacks:0;}
    float MovementMultiplier()const;
    float FrozenRemaining()const{return FrozenTime;}
    float CorrosionMultiplier()const{return FMath::Max(0.f,1-CorrosionStacks*CorrosionReduction);}
    float MagicShred()const{return ShredTime>0?Shred:0;}
    float FinalMultiplier()const{return WardTime>0?Ward:1;}
    /** 标记承伤乘区（所有伤害类型）。 */
    float MarkedMultiplier()const{return MarkedTime>0?1+MarkedValue:1;}
    /** 石化承伤乘区（魔法/电系）。 */
    float PetrifiedMagicMultiplier()const{return PetrifyTime>0?PetrifyMul:1;}
    /** 骆驼惊吓：本实体作为攻击方的输出折减。 */
    float OutgoingDamageMultiplier()const;
    /** 激励在战斗面板结算处消费的物理/魔法攻乘区。 */
    float InspireAttackMultiplier()const{return InspireTime>0?InspireAtk:1;}
    float MagicVulnerabilityMultiplier()const{return (1+VulnerabilityStacks*.05f)*(1+(RuneVulnerabilityTime>0?RuneVulnerability:0));}
    /** 击杀触发：grant Marble/ginseng 类 1 秒治疗窗口的显示钩子（数据面在 StatusModel）。 */
    UFUNCTION(BlueprintCallable) void ShowProcTile(FName Type,float Seconds);
    /** 复活/重生清理：清空所有瞬时状态与卡片（旧 _reviveInplace 的状态清算）。 */
    UFUNCTION(BlueprintCallable) void PurgeTransient();
    /** 旧 SUPPORT_CLEANSE_TYPES 净化：按白名单顺序最多清除 Count 条负面状态（含毒/恐惧组件；感电连层数硬清）。 */
    UFUNCTION(BlueprintCallable) int32 CleanseDebuffs(int32 Count);
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Fn)override;
private:
    void InterruptOwnerActions(float Seconds);
    bool bImmune=false;
    int32 ElectrifiedStacks=0;
    float ElectrifiedTime=0,ElectrifiedBonus=.03f;
    int32 ChillStacks=0,HasteStacks=0,ChainStacks=0;
    float ChillTime=0,ChillSlow=.05f,FrozenTime=0,HasteTime=0,ChainTime=0;
    int32 CorrosionStacks=0;
    float CorrosionTime=0,CorrosionDuration=5,CorrosionReduction=.05f;
    float ShredTime=0,Shred=0,WardTime=0,Ward=1;
    int32 VulnerabilityStacks=0,BleedStacks=0;
    float VulnerabilityTime=0,BleedTime=0,BleedTick=0,BurnTick=0,BurnInterval=.5f;
    float RuneVulnerability=0,RuneVulnerabilityTime=0;
    float RiposteTime=0,RiposteSpeed=1,RiposteStamina=1;
    TWeakObjectPtr<AActor> BleedSource;
    struct FBurn {TWeakObjectPtr<AActor> Source;float Damage=0,Remaining=0;};
    TArray<FBurn> Burns;
    // gamedev 迁移字段（单位秒）：
    float StunTime=0,BindTime=0,SlowTime=0,SlowPct=0,WaxTime=0,WaxPct=0;
    float WeaponHasteTime=0,WeaponHasteMul=1;
    float PetrifyTime=0,PetrifyMul=1.5f;
    float MarkedTime=0,MarkedValue=.15f;
    float InspireTime=0,InspireSpeed=1,InspireAtk=1;
    float CamelTime=0,CamelReduction=0;
    float ImmuneTime=0;
    float MineTime=0,MineLinger=3,MineTick=0;
    struct FDroneMark {FName SourceId;float DamagePercent=0,CritPercent=0,Remaining=0;TWeakObjectPtr<AActor> Owner;};
    TMap<FName,FDroneMark> Drones;
};
