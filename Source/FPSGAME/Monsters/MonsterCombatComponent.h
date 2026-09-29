#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "../Combat/MonsterToughnessTypes.h"
#include "MonsterCombatComponent.generated.h"
class UAnimSequence;
class APawn;
class UCombatStatusFormula;
/** Shared execution gate. Decisions belong to the AI tree, damage clocks to each monster. */
UCLASS(ClassGroup=AI, meta=(BlueprintSpawnableComponent))
class FPSGAME_API UMonsterCombatComponent : public UActorComponent
{
 GENERATED_BODY()
public:
 UMonsterCombatComponent();
 virtual void BeginPlay() override;
 virtual void TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Tick) override;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Reaction") TObjectPtr<UAnimSequence> HitClip;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Reaction") float StaggerDuration=.55f;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Reaction") int32 HitReactions=0;
 /** Explicit skill/parry stun only; toughness stagger and knockdown are separate. */
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Reaction") bool bStunned=false;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Reaction|Stun") TObjectPtr<UAnimSequence> DizzyClip;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Reaction|Stun",meta=(ClampMin="0.25",ClampMax="2")) float DizzyPlayRate=1.f;
 bool IsPlayingStunSway() const { return bPlayingSway; }
 float StunSecondsRemaining() const;
 bool IsImmobileReaction() const;

 // ── 韧性系统 ──────────────────────────────────────────────────────────
 // 命中先按「形式 × 对应抗性」折算成韧性伤害并累积；只有累积达到阈值才破韧造成硬直。
 // 未达阈值的命中不打断动作、不进入硬直、不播放受击表现（只累积韧性）。
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Toughness",meta=(ClampMin="0",ToolTip="韧性上限：累积的韧性伤害达到该值即破韧。0 = 每次命中都破韧。")) float ToughnessThreshold=60.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Toughness",meta=(Units="s",ClampMin="0",ToolTip="破韧硬直时长：韧性被打满后怪物失去控制的时间。")) float ToughnessBreakSeconds=1.2f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Toughness",meta=(ClampMin="0",ClampMax="0.9",ToolTip="锐器抗性：按比例减免刃口切割与突刺（剑刃、斧刃、冰锥）造成的韧性伤害。")) float BladeResistance=0.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Toughness",meta=(ClampMin="0",ClampMax="0.9",ToolTip="钝器抗性：按比例减免锤击、配重与枪托砸击造成的韧性伤害。")) float BluntResistance=0.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Toughness",meta=(ClampMin="0",ClampMax="0.9",ToolTip="冲击抗性：按比例减免爆炸、坍塌、撞击以及未标注形式伤害造成的韧性伤害。")) float ImpactResistance=0.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Toughness",meta=(Units="s",ClampMin="0",ToolTip="脱战恢复：连续该秒数没有受击后清空累积韧性。")) float ToughnessRecoverySeconds=2.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Toughness",meta=(ToolTip="开=未达阈值的命中仍播放 StaggerDuration 短硬直（旧的每击打断手感）；关=完全按阈值闸门。")) bool bAllowSubthresholdStagger=false;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Toughness",meta=(ToolTip="当前累积的韧性伤害。")) float Toughness=0;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Toughness",meta=(ToolTip="最近一次命中实际造成的韧性伤害。")) float LastToughnessDamage=0;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Toughness",meta=(ToolTip="最近一次命中的形式。")) EMonsterAttackForm LastAttackForm=EMonsterAttackForm::Impact;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Toughness",meta=(ToolTip="累计破韧次数。")) int32 Breaks=0;

 bool IsDead() const;
 bool GetVitals(float& Health,float& MaxHealth,FText& Name) const;
 bool IsBusy() const;
 bool IsControlled() const;
 bool IsKnockedDown() const;
 bool CanAttack(APawn* Target) const;
 bool TryAttack(APawn* Target);
 void SetLocomotion(bool Moving,bool Returning=false);
 void SetTarget(APawn* Target);
 float AggroRange() const;
 float LeashRange() const;
 float StopRange() const;
 FVector Home() const;
 void ReachedHome();
 /** 该命中形式对应的韧性抗性（0..0.9）。 */
 float ToughnessResistance(EMonsterAttackForm Form) const;
 /** 这次伤害在指定形式下会折算出的韧性伤害（只算不改状态），供调参与自检使用。 */
 float ToughnessDamageFor(float Damage,EMonsterAttackForm Form) const;
 /** 韧性进度 0..1。 */
 float ToughnessPercent() const { return ToughnessThreshold>0.f?FMath::Clamp(Toughness/ToughnessThreshold,0.f,1.f):1.f; }
 /** 受击入口：Form 由攻击端标注，决定按哪条抗性折算削韧。 */
 void ReceiveHit(float Damage,APawn* Attacker,EMonsterAttackForm Form=EMonsterAttackForm::Impact);
 // The multiplier is scoped to this target's synchronous hit receipt, never to poison or parries.
 float ApplyHitWithReactionScale(float Multiplier,TFunctionRef<float()> ApplyDamage);
 float ApplyHitWithToughnessScale(float Multiplier,TFunctionRef<float()> ApplyDamage);
 void ReceiveParry(APawn* Defender,float Seconds,float KnockbackCM);
 void ReceiveMeleeKnockback(APawn* Attacker,float DistanceCM);
 UFUNCTION(BlueprintCallable,Category="Monster|Knockdown")
 bool ReceiveKnockdown(APawn* Attacker,FVector LaunchVelocity,float DownSeconds=.7f);
 /** 技能硬控：打断当前攻击进入眩晕反应，并沿受击方向推退。无招架表现标记。 */
 void ReceiveStun(APawn* Attacker,float Seconds,float KnockbackCM);
 bool IsParryReaction() const { return bParryReaction; }
 const FVector& GetParryDirection() const { return ParryPushDirection; }
 void BeginReaction(float Duration);
 void FinishReaction();
 UFUNCTION(BlueprintCallable,Category="MonsterAI|Editor") static bool AuthorHitClip(UAnimSequence* Clip,bool bHandBrain);
private:
 float IncomingHitReactionMultiplier=1.f;
 float IncomingToughnessDamageMultiplier=1.f;
 float SinceHit=100.f,ReactionTime=0,ReactionDuration=0;
 void UpdateReactionPresentation();
 void LoadHumanoidStun();
 bool BeginHumanoidStun(float Duration);
 bool UpdateHumanoidStun(float Elapsed,float Remaining);
 void PlayHumanoidStunClip(UAnimSequence* Clip,float BlendSeconds);
 void ClearHumanoidStun();
 bool bSwayArmed=false,bPlayingSway=false,bLeavingSway=false;
 float SwayEntrySeconds=.14f,SwayTime=0.f,SwayBlendTime=0.f;
 TWeakObjectPtr<UCombatStatusFormula> SwayStatus;
 bool bParryReaction=false;
 void TickParryPush(float Delta);
 bool MoveParryPush(float Distance);
 FVector ParryPushDirection=FVector::ZeroVector;
 float ParryPushDistance=0.f,ParryPushAge=0.f;
 void TickMeleePush(float Delta);
 bool MoveMeleePush(float Distance);
 FVector MeleePushDirection=FVector::ZeroVector;
 float MeleePushDistance=0.f,MeleePushAge=0.f;
 // Uses world game time; no extra timer or Tick. Physical reactions cannot extend it.
 double ExplicitStunUntil=0.0;
 void RegisterExplicitStun(float Seconds);
};
