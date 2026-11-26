#pragma once
#include "CoreMinimal.h"
#include "Engine/NetSerialization.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Pawn.h"
#include "ColdSteelPlayerProtocol.generated.h"

/** One small owner-only sample; natural food time does not require a full inventory mirror. */
USTRUCT()
struct FColdSteelFoodClockState
{
    GENERATED_BODY()
    UPROPERTY() FGuid Id;
    UPROPERTY() double Day=0.;
};

/**
 * 命中上报（客户端→服务端）的权威化口径：
 * 客户端只申报"我开枪了+几何上下文"（原点/命中点/骨骼/方向/武器声明/自报伤害），
 * 伤害构成（精通/暴击/穿透/弹药效果/面板拆项）一律由服务端按影子档案重算，
 * 自报伤害被钳制在服务端武器包络内。命中结论、目标与位置由服务端校验。
 */
USTRUCT()
struct FColdSteelNetHitReport
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<AActor> Target = nullptr;
    /** 客户端开火瞬间的相机/枪口原点——服务端用于位置容差与将来 rewind。 */
    UPROPERTY() FVector_NetQuantize AimOrigin;
    UPROPERTY() FVector_NetQuantize ImpactPoint;
    UPROPERTY() FVector_NetQuantizeNormal HitNormal;
    UPROPERTY() FName BoneName;
    UPROPERTY() FName HitComponent;
    UPROPERTY() FVector_NetQuantizeNormal Direction;
    UPROPERTY() FString ItemDefinition;
    UPROPERTY() FString ItemInstance;
    UPROPERTY() uint32 FireSequence=0;
    /** 客户端自报标量伤害：仅作参考，服务端按武器包络钳制。 */
    UPROPERTY() float ClaimedDamage = 0.f;
    /** 汇聚附魔消耗的弹数（0/1=无汇聚）；服务端按影子档案同参数复算倍率。 */
    UPROPERTY() uint8 ConvergenceRounds = 0;
    /** bit0 bMeleeStrike / bit1 bRifle / bit2 bPistol / bit3 bMelee / bit4 bRicochet / bit5 bInheritedCritical / bit6 bFiredRound / bit7 Azure Dragon active */
    UPROPERTY() uint8 Flags = 0;
    /** 攻击语义位（与 FColdSteelSkillShot::AttackMeta 同码）：0x0F=连段阶段，0x10=重击，0x20=旋风，0x40=裂斩波。 */
    UPROPERTY() uint8 AttackMeta = 0;
    UPROPERTY() uint8 MeleeDamagePhase = 0;
    /** 攻击语义上下文：弓=拉弦比 0-1。服务端据此把伤害完全重算为权威值。 */
    UPROPERTY() float DamageContext = 0.f;
    /** EMonsterAttackForm 的窄化传输；0 表示沿用服务端 Snapshot 推断值。 */
    UPROPERTY() uint8 AttackForm = 0;
    UPROPERTY() double ClientFireTime = 0.0;
    UPROPERTY() double HeavyReleaseTime = 0.0;
    /** Groups targets from one blade swing; carries no client-provided buff values. */
    UPROPERTY() uint32 GuardAttackSerial = 0;
    UPROPERTY() uint32 MasteryAttackSerial = 0;
    UPROPERTY() uint32 GenericMeleeSerial = 0;
    UPROPERTY() uint32 KukriAttackSerial = 0;
    UPROPERTY() uint32 QuickCombatSerial = 0;
    UPROPERTY() uint32 UppercutSerial = 0;
    UPROPERTY() uint32 WhirlwindSerial = 0;
    UPROPERTY() uint32 ShadowStepSerial = 0;
};

/**
 * 施法意图上报（客户端→服务端）：A 模式服务端化通道——
 * 客户端只报"放了哪个技能+相位+瞄准上下文"，消耗校验、orb 生成、弹道与伤害结算
 * 全部在服务端按影子档案执行，法术实体以复制 actor 回流到各端。
 * Phase: 0=凝聚 1=释放 2=未释放取消 3=弃置 4=龙息按 CastId 停止／取消。
 * 各字段按技能取用：AimPoint=瞄准/放置点（龙息为眼部瞄准空间的杖尖偏移）；AimNormal=放置朝向/坡面法线/弹道方向；
 * Variant=形态位（冰墙 0=高 1=低；圣光 bit0=自我施放）；Target=目标类法术锁定的 actor；
 * Charge=充能类技能的充量比（thunderLance）。
 */
USTRUCT()
struct FColdSteelNetCastRequest
{
    GENERATED_BODY()
    UPROPERTY() FName SkillId;
    UPROPERTY() TObjectPtr<APawn> SourcePawn=nullptr;
    UPROPERTY() uint32 Sequence=0;
    UPROPERTY() uint32 CastId=0; // Dragon/Storm prepare sequence; stable through release/cancellation.
    UPROPERTY() FString WeaponInstance; // Required by equipped-item casts.
    UPROPERTY() uint8 Phase = 0;
    UPROPERTY() FVector_NetQuantize AimPoint = FVector::ZeroVector;
    UPROPERTY() FVector_NetQuantizeNormal AimNormal = FVector::UpVector;
    UPROPERTY() FVector_NetQuantizeNormal AimAxis = FVector::ForwardVector; // 暴雪区椭圆长轴
    UPROPERTY() uint8 Variant = 0;
    UPROPERTY() TObjectPtr<AActor> Target = nullptr;
    UPROPERTY() float Charge = 0.f;
};

/** 服务端→客户端的命中回执（命中标记/击杀反馈）。 */
USTRUCT()
struct FColdSteelNetHitReceipt
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<AActor> Target = nullptr;
    UPROPERTY() float Applied = 0.f;
    UPROPERTY() float MagicApplied = 0.f;
    UPROPERTY() bool bCritical = false;
    UPROPERTY() bool bKilled = false;
    UPROPERTY() bool bRejected = false;
    UPROPERTY() bool bFirearm = false;
};

/** 全员可见的玩家公开信息（名牌/HUD/远端表现用的小字段，私有数据走 OwnerOnly）。 */
USTRUCT(BlueprintType)
struct FColdSteelPublicPlayerInfo
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) FString ActiveWeaponDefinition;
    UPROPERTY(BlueprintReadOnly) int32 Level = 1;
    UPROPERTY(BlueprintReadOnly) int32 Kills = 0;
};

