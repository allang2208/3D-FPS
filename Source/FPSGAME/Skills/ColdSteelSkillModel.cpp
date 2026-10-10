#include "ColdSteelSkillRules.h"
#include "../Weapons/ZhenmoRuneComponent.h"
#include "MeleeToughnessTuning.h"
#include "SwordUppercutTuning.h"
#include "../UI/ColdSteelStatusModel.h"
#include "FPSFireMagicComponent.h"
#include "../Combat/CoreCombatFormula.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/BoundCongregate.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Monsters/MonsterIdleBreathingMeshComponent.h"
#include "../Monsters/PoisonMaggotProjectile.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/FPSMeleeLightningComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/TangDaoGuardComponent.h"
#include "../Weapons/PanChiGuardComponent.h"
#include "../Weapons/RuneSwordRisingDragon.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "../Weapons/Unarmed/FPSUnarmedIdleComponent.h"
#include "../FPSGAMECharacter.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"

FColdSteelSkillProgress UColdSteelStatusModel::RifleProgress() const
{ const auto* P=Current.Skills.Find(RifleSkill.Id); return P?*P:FColdSteelSkillProgress(); }
FColdSteelSkillProgress UColdSteelStatusModel::CriticalStrikeProgress() const
{ const auto* P=Current.Skills.Find(CriticalStrikeSkill.Id);return P?*P:FColdSteelSkillProgress(); }
FColdSteelSkillEffect UColdSteelStatusModel::CriticalStrikeEffect(int32 AtLevel) const
{ return ColdSteelSkills::Effect(CriticalStrikeSkill,AtLevel<0?CriticalStrikeProgress().Level:AtLevel); }
FColdSteelSkillProgress UColdSteelStatusModel::PistolProgress() const
{ const auto* P=Current.Skills.Find(PistolSkill.Id);return P?*P:FColdSteelSkillProgress(); }
FColdSteelSkillEffect UColdSteelStatusModel::PistolEffect(int32 AtLevel) const
{ return ColdSteelSkills::Effect(PistolSkill,AtLevel<0?PistolProgress().Level:AtLevel); }
float UColdSteelStatusModel::PistolWeaponDamage(const FColdSteelItem& Item,float WeaponDamage) const
{
    if(!ColdSteelSkills::IsPistol(&Item))return WeaponDamage;
    const auto E=PistolEffect();return FMath::RoundToFloat(WeaponDamage*(1+E.DamagePercent)+E.FlatDamage);
}
float UColdSteelStatusModel::PistolMovementMultiplier() const
{ return ColdSteelSkills::IsPistol(Equipped())&&!ActiveProductionTool()?1.f+PistolEffect().MoveSpeed:1.f; }
float UColdSteelStatusModel::MachineGunMovementMultiplier() const
{
    const auto* I=Equipped();
    if(!I||ActiveProductionTool())return 1.f;
    // 机枪归类沿用武器专精的唯一入口（weaponType=machineGun），
    // 这样目录里新增机枪不需要再维护第二份清单。
    if(WeaponMastery(I)!=TEXT("machineGunMastery"))return 1.f;
    const float Multiplier=MasteryEffect(TEXT("machineGunMastery")).MovementMultiplier;
    return Multiplier>0.f?Multiplier:1.f;
}
FColdSteelSkillProgress UColdSteelStatusModel::DodgeProgress() const
{ const auto* P=Current.Skills.Find(DodgeSkill.Id);return P?*P:FColdSteelSkillProgress(); }
FColdSteelSkillProgress UColdSteelStatusModel::DexterousHandsProgress() const
{ const auto* P=Current.Skills.Find(DexterousHandsSkill.Id);return P?*P:FColdSteelSkillProgress(); }
FColdSteelSkillEffect UColdSteelStatusModel::DexterousHandsEffect(int32 AtLevel) const
{ return ColdSteelSkills::Effect(DexterousHandsSkill,AtLevel<0?DexterousHandsProgress().Level:AtLevel); }
float UColdSteelStatusModel::ReloadSpeedMultiplier() const
{ return 1.f+DexterousHandsEffect().ReloadSpeed; }
FColdSteelSkillEffect UColdSteelStatusModel::DodgeEffect(int32 AtLevel) const
{ return ColdSteelSkills::Effect(DodgeSkill,AtLevel<0?DodgeProgress().Level:AtLevel); }
float UColdSteelStatusModel::DodgeStaminaCost(int32 AtLevel) const
{
    const auto* Guard=CurrentPawn.IsValid()?CurrentPawn->FindComponentByClass<UTangDaoGuardComponent>():nullptr;
    return StaminaTuning.DodgeCost*(1.f-DodgeEffect(AtLevel).DodgeCostReduction)*(Guard?Guard->DodgeStaminaMultiplier():1.f);
}
bool UColdSteelStatusModel::TrainDodge(int32 Amount)
{
    if(Amount<=0||DodgeProgress().Level>=DodgeSkill.MaxLevel)return false;
    // 进度型修炼与命中修炼同口径：实时档案立即更新，写盘交给定时自动存档。
    SyncRuntime();auto P=Snapshot();ColdSteelSkills::AddExperience(P,DodgeSkill,Amount);return StageTraining(MoveTemp(P));
}
bool UColdSteelStatusModel::TrainDexterousHands(int32 Amount)
{
    if(Amount<=0||DexterousHandsProgress().Level>=DexterousHandsSkill.MaxLevel)return false;
    SyncRuntime();auto P=Snapshot();ColdSteelSkills::AddExperience(P,DexterousHandsSkill,Amount);return StageTraining(MoveTemp(P));
}
FColdSteelSkillProgress UColdSteelStatusModel::QuickCombatProgress() const
{ const auto* P=Current.Skills.Find(QuickCombatSkill.Id);return P?*P:FColdSteelSkillProgress(); }
FQuickCombatCast UColdSteelStatusModel::QuickCombatStats(int32 AtLevel,const FMeleeModifiers* PreviewModifiers) const
{
    // 原公式各项同乘 0.2；力量与武器倍率仍来自当前结算入口。
    const auto& T=QuickCombatSkill.QuickCombat;
    const int32 L=FMath::Clamp(AtLevel<0?QuickCombatProgress().Level:AtLevel,1,QuickCombatSkill.MaxLevel);
    const float Strength=float(Attribute(TEXT("str")));
    const auto Mods=PreviewModifiers?*PreviewModifiers:ColdSteelMelee::EquippedModifiers(this);
    FQuickCombatCast C;
    C.DamageMultiplier=float((1.+Mods.QuickCombatDamageAdd)*Mods.AllAttackDamage);
    C.Damage=(T.DamageBase+T.DamagePerLevel*L+Strength*(T.StrengthFactorBase+T.StrengthFactorPerLevel*L))*C.DamageMultiplier;
    C.KnockbackCM=T.KnockbackCM*float(Mods.QuickCombatKnockback*Mods.AllAttackKnockback);
    C.ToughnessMultiplier=float(Mods.QuickCombatToughnessMultiplier());
    C.BleedChance=FMath::Clamp(float(Mods.QuickCombatBleedChance),0.f,1.f);
    C.bAreaHit=Mods.bQuickCombatAOE;
    C.RangeCM=T.RangeCM;
    C.StaminaCost=QuickCombatStaminaCost(L,&Mods);
    return C;
}
float UColdSteelStatusModel::QuickCombatStaminaCost(int32 AtLevel,const FMeleeModifiers* PreviewModifiers) const
{
    const auto& T=QuickCombatSkill.QuickCombat;
    const int32 L=FMath::Clamp(AtLevel<0?QuickCombatProgress().Level:AtLevel,1,QuickCombatSkill.MaxLevel);
    const auto Mods=PreviewModifiers?*PreviewModifiers:ColdSteelMelee::EquippedModifiers(this);
    const float Reduction=FMath::Clamp(T.StaminaReductionPerLevel*(L-1),0.f,1.f);
    return T.StaminaCost*(1.f-Reduction)*float(Mods.Stamina*ColdSteelMelee::TemporaryModifiers(this).Stamina);
}
bool UColdSteelStatusModel::TrainQuickCombat(int32 Amount)
{
    if(Amount<=0||QuickCombatProgress().Level>=QuickCombatSkill.MaxLevel)return false;
    SyncRuntime();auto P=Snapshot();ColdSteelSkills::AddExperience(P,QuickCombatSkill,Amount);return StageTraining(MoveTemp(P));
}
float UColdSteelStatusModel::QuickCombatCooldown() const
{ return Current.bQuickCombatReserved?Current.QuickCombatCooldown:0.f; }
bool UColdSteelStatusModel::CommitQuickCombatCast(float ActionDuration)
{
    if(Current.bQuickCombatReserved)return false;
    if(bPersistenceBlocked||(GetWorld()&&GetWorld()->GetNetMode()==NM_Client))return false;
    if(!SpendStamina(QuickCombatStaminaCost()))return false;
    Current.bQuickCombatReserved=true;
    UpdateQuickCombatAction(ActionDuration,ActionDuration);
    // Like other stamina actions, keep this high-frequency clock in memory;
    // training/autosave owns persistence instead of writing twice per swing.
    return true;
}
void UColdSteelStatusModel::UpdateQuickCombatAction(float Remaining,float Duration)
{
    if(!Current.bQuickCombatReserved)return;
    Current.QuickCombatCooldownDuration=FMath::Max(0.f,Duration);
    Current.QuickCombatCooldown=FMath::Clamp(Remaining,0.f,Current.QuickCombatCooldownDuration);
}
void UColdSteelStatusModel::FinishQuickCombatCast()
{
    Current.bQuickCombatReserved=false;
    Current.QuickCombatCooldown=Current.QuickCombatCooldownDuration=0.f;
}
bool UColdSteelStatusModel::TriggerQuickCombat()
{
    // F/快捷栏统一入口：完整动作期间拒绝再次施放，结束后没有额外冷却。
    // 各类武器共用体力、修炼和数值合同：
    //   剑类 → 符文剑配重锤；单持手枪 → 握把砸击；其余枪械 → 步枪枪托砸击。
    if(Current.bQuickCombatReserved)
    {
        UE_LOG(LogTemp,Log,TEXT("[QuickCombat] 动作尚未结束（剩余 %.2f 秒），忽略触发"),QuickCombatCooldown());
        return false;
    }
    auto* Player=Cast<AFPSGAMECharacter>(UGameplayStatics::GetPlayerPawn(this,0));
    if(!Player)return false;
    if(UBoundCongregateCaptureComponent::IsCaptured(Player))
        if(auto* Hands=Player->FindComponentByClass<UFPSUnarmedIdleComponent>();Hands&&Hands->IsEquipped())return Hands->BeginPunch();
    if(auto* Staff=Player->FindComponentByClass<UStaffWeaponComponent>();Staff&&Staff->IsEquipped())return Staff->BeginQuickCombat();
    if(auto* Bow=Player->FindComponentByClass<UBowWeaponComponent>();Bow && Bow->IsEquipped())return Bow->BeginQuickCombat();
    if(auto* Sword=Player->FindComponentByClass<URuneSwordComponent>())
        if(Sword->IsEquipped())return Sword->BeginQuickCombatStrike();
    if(Player->QuickCombatPistol)
        return Player->IsPistolWeapon()?Player->TriggerPistolQuickCombat():Player->TriggerRifleStockMelee();
    UE_LOG(LogTemp,Log,TEXT("[QuickCombat] 角色没有快速进战动作组件，无法触发"));
    return false;
}
FColdSteelSkillEffect UColdSteelStatusModel::RifleEffect(int32 AtLevel) const
{ return ColdSteelSkills::Effect(RifleSkill,AtLevel<0?RifleProgress().Level:AtLevel); }
float UColdSteelStatusModel::RifleWeaponDamage(const FColdSteelItem& Item,float WeaponDamage) const
{
    if (!ColdSteelSkills::IsRifle(&Item)) return WeaponDamage;
    const auto E=RifleEffect(); return FMath::RoundToFloat(WeaponDamage*(1+E.DamagePercent)+E.FlatDamage);
}
float UColdSteelStatusModel::ApplySkillWeaponHit(AActor* Shooter,const FHitResult& Hit,float Damage,const FVector& Direction,const FColdSteelSkillShot& Shot,FWeaponDamageResult* Result)
{
    if(auto* Bound=Cast<ABoundCongregate>(Hit.GetActor());Bound&&Bound->IsTentaclePart(Hit))
    {
        // The exposed restraint is its own 300 HP organ, with no torso armor,
        // body stagger, kill reward or duplicated on-hit status transaction.
        const bool Firearm=!Shot.bMelee&&!Shot.bMeleeStrike&&(Shot.bRifle||Shot.bPistol||Shot.BulletSpeedCM>0.f||
            Shot.MasteryId==TEXT("shotgunMastery")||Shot.MasteryId==TEXT("machineGunMastery"));
        const float Applied=Firearm&&Bound->IsTentacleHit(Hit)?Bound->ApplyTentacleShot(Damage):0.f;
        if(Result)
        {
            *Result={};Result->bResolved=true;
            Result->BeforeDefense=Shot.DamagePanel.Total()>0?Shot.DamagePanel.Scaled(Damage/Shot.DamagePanel.Total()):FWeaponDamageParts{Damage,0,0,0};
            Result->AfterDefense=Result->BeforeDefense;Result->Applied=Result->BeforeDefense.LimitedTo(Applied);
        }
        return Applied;
    }
    AActor* Victim=Hit.GetActor(); const auto* Pawn=Cast<APawn>(Shooter);
    auto* Combat=Victim?Victim->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    const bool bAliveBefore=Combat&&!Combat->IsDead();
    FTrainingHit Training; Training.Victim=Victim;
    const FName Mastery=Shot.MasteryId.IsNone()?(Shot.bPistol?FName(TEXT("pistolMastery")):(Shot.bRifle?FName(TEXT("rifleMastery")):NAME_None)):Shot.MasteryId;
    const auto& Skill=MasteryDefinition(Mastery);
    Training.SkillId=Mastery;Training.ExtraExperience=Shot.ExtraMasteryExperience;Training.bMelee=Shot.bMelee;
    Training.bEligible=Combat && !Combat->IsDead() && !Victim->ActorHasTag(TEXT("Summoned")) && !Victim->ActorHasTag(TEXT("NoSkillTraining"));
    const bool Weakpoint=!Shot.bRicochet&&ColdSteelSkills::IsCriticalHit(Hit);
    Training.bCritical=Shot.bRicochet?Shot.bInheritedCritical:
        (Weakpoint||(Combat&&FMath::FRand()*100<CoreCombatFormula::CriticalChance(Shot.CriticalChance,CombatFormulaRuntime::MonsterCriticalResistance(Victim))));
    float Amount=Damage*(Shot.bRifle && Weakpoint?1+Shot.WeakpointPercent:1);
    auto* TangGuard=Shooter?Shooter->FindComponentByClass<UTangDaoGuardComponent>():nullptr;
    const bool bGuardContact=TangGuard&&bAliveBefore&&Damage>0.f&&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter);
    float GuardToughnessBonus=0.f;
    auto* PanChi=Shooter?Shooter->FindComponentByClass<UPanChiGuardComponent>():nullptr;
    const bool bPanChiContact=bAliveBefore&&Damage>0.f&&PanChi&&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter);
    const float PanChiToughness=bPanChiContact?PanChi->UppercutToughnessMultiplier(Shot):1.f;
    if(bGuardContact)Amount*=TangGuard->ConsumeDragon(Shot,GuardToughnessBonus);
    float WagerBonus=0.f;
    // 普通暴击与要害暴击共用这一次判定；继承伤害的次生命中不重复叠层。
    if(Shooter&&Shooter->HasAuthority()&&Training.bCritical&&!Shot.bRicochet&&Damage>0.f
        &&Shot.ComposureStabilityPerStack>0.f&&Shot.ComposureRecoilReductionPerStack>0.f
        &&Shot.ComposureSeconds>0.f&&Shot.ComposureMaxStacks>0
        &&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter))
        UCombatStatusFormula::GetOrAdd(Shooter)->AddComposure(Shot.ComposureStabilityPerStack,
            Shot.ComposureRecoilReductionPerStack,Shot.ComposureSeconds,Shot.ComposureMaxStacks);
    // 命中新增的一层也参与本次暴击。仅实际附魔手枪的敌人命中触发；
    // 暴击消耗先于伤害回调，避免同一组层数被递归/附带伤害再次使用。
    if(Shooter&&Shooter->HasAuthority()&&Shot.bPistol&&!Shot.bRicochet&&Damage>0.f
        &&Shot.WagerCriticalBonusPerStack>0.f&&Shot.WagerSeconds>0.f&&Shot.WagerMaxStacks>0
        &&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter))
    {
        auto* Status=UCombatStatusFormula::GetOrAdd(Shooter);
        Status->AddWager(Shot.WagerCriticalBonusPerStack,Shot.WagerSeconds,Shot.WagerMaxStacks);
        if(Training.bCritical){WagerBonus=Status->WagerCriticalBonus();Status->ConsumeWager();}
    }
    if(!Shot.bRicochet&&Training.bCritical&&(Shot.CriticalDamageBonus+WagerBonus)>0)Amount*=1+Shot.CriticalDamageBonus+WagerBonus;
    TGuardValue<FTrainingHit*> HitScope(ActiveTrainingHit,&Training);
    CombatFormulaRuntime::WeaponHit WeaponHit;WeaponHit.Target=Victim;WeaponHit.bMelee=Shot.bMelee||Shot.bMeleeStrike;
    // Damage already contains this attack's heavy/combo/range multiplier. Apply
    // the same multiplier and shared critical roll to every panel component.
    WeaponHit.Incoming=Shot.DamagePanel.Total()>0?Shot.DamagePanel.Scaled(Amount/Shot.DamagePanel.Total()):FWeaponDamageParts{Amount,0,0,0};
    // Azure Dragon doubles physical channels only. Existing magic additions keep
    // their own value; multiplying the scalar would incorrectly double them too.
    const bool bAzureDragon=Shot.bMelee&&!Shot.bRicochet&&Shot.AzureDragonPhysicalMultiplier>1.f;
    if(bAzureDragon)
    {
        WeaponHit.Incoming.BasePhysical*=Shot.AzureDragonPhysicalMultiplier;
        WeaponHit.Incoming.AddedPhysical*=Shot.AzureDragonPhysicalMultiplier;
        Amount=WeaponHit.Incoming.Total();
    }
    WeaponHit.PhysicalPenetration=Shot.ArmorPenetration;WeaponHit.MagicPenetration=Shot.MagicPenetration;
    TGuardValue<CombatFormulaRuntime::WeaponHit*> DamageScope(CombatFormulaRuntime::ActiveWeaponHit,&WeaponHit);
    // 普通怪沿用 hit_stagger 枪械闸门；精英以上枪弹削韧，破韧期可造成短硬直。
    // 闸门关闭时受击端只记住攻击者，不动状态机、韧性时钟或硬直动作。
    // 枪弹局部回弹单独叠到原姿态，不经过这道控制状态闸门。
    // 近战武器与手持枪械发动的近战打击（bMeleeStrike）不在闸门覆盖范围内：
    // 它们按原倍率进入受击端，否则削韧与硬直会被整段吞掉。
    bool bFirearmWithoutStagger=false;
    bool bFirearmContact=false;
    const FString WeaponDefinition=Shot.ItemDefinition.IsEmpty()?(Equipped()?Equipped()->Definition:FString()):Shot.ItemDefinition;
    if(!Shot.bMelee&&!Shot.bMeleeStrike&&!WeaponDefinition.IsEmpty())
        if(auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>())
            if(const auto* W=G->Weapon(WeaponDefinition))
            {
                bFirearmWithoutStagger=!W->bHitStagger;
                bFirearmContact=!G->IsMelee(WeaponDefinition)&&!G->IsTool(WeaponDefinition)
                    &&!G->IsStaff(WeaponDefinition)&&!G->IsBow(WeaponDefinition);
            }
    auto ApplyDamage=[&](){ return UGameplayStatics::ApplyPointDamage(Victim,Amount,Direction,Hit,
        Pawn?Pawn->GetController():nullptr,Shooter,nullptr); };
    // 命中形式的唯一收口：所有武器命中都在这里标注，受击端据此折算削韧。
    const MonsterToughness::FScopedForm FormScope(Shot.AttackForm);
    const float FixedToughness=Shot.bMelee&&!Shot.bRicochet?MeleeToughness::FixedBaseFor(Shot.AttackMeta):-1.f;
    auto ApplyToughness=[&](){return Combat?Combat->ApplyHitWithToughnessScale(Shot.ToughnessDamageMultiplier*PanChiToughness,ApplyDamage,FixedToughness,GuardToughnessBonus):ApplyDamage();};
    float Applied=(Combat&&bFirearmWithoutStagger&&!Combat->UsesToughnessBar())?Combat->ApplyHitWithReactionScale(0.f,ApplyToughness):ApplyToughness();
    FWeaponDamageParts AppliedParts=WeaponHit.Mitigated.LimitedTo(Applied);
    // A real second damage transaction, with its own magic defense and remaining
    // HP. Share the original training/kill scope, but never recurse through
    // ApplyHit (which would duplicate crit rolls, affixes, charge and training).
    if(bAzureDragon&&bAliveBefore&&Shot.AzureDragonMagicDamage>0.f&&IsValid(Victim)
        &&!Victim->IsActorBeingDestroyed()&&!Combat->IsDead())
    {
        CombatFormulaRuntime::WeaponHit MagicHit;
        MagicHit.Target=Victim;MagicHit.bMelee=true;
        MagicHit.Incoming.AddedMagic=Shot.AzureDragonMagicDamage;
        MagicHit.MagicPenetration=Shot.MagicPenetration;
        TGuardValue<CombatFormulaRuntime::WeaponHit*> MagicScope(CombatFormulaRuntime::ActiveWeaponHit,&MagicHit);
        auto ApplyMagic=[&](){return UGameplayStatics::ApplyPointDamage(Victim,Shot.AzureDragonMagicDamage,
            Direction,Hit,Pawn?Pawn->GetController():nullptr,Shooter,nullptr);};
        // The second receipt is bonus damage, not a second blade impact/reaction.
        const float MagicApplied=Combat->ApplyHitWithReactionScale(0.f,[&]()
        {return Combat->ApplyHitWithToughnessScale(0.f,ApplyMagic,0.f);});
        WeaponHit.Incoming.AddedMagic+=MagicHit.Incoming.AddedMagic;
        WeaponHit.Mitigated.AddedMagic+=MagicHit.Mitigated.AddedMagic;
        AppliedParts.AddedMagic+=MagicHit.Mitigated.LimitedTo(MagicApplied).AddedMagic;
        WeaponHit.bResolved=WeaponHit.bResolved&&MagicHit.bResolved;
        Applied+=MagicApplied;
    }
    const bool bDirectKill=bAliveBefore&&Applied>0.f&&(!IsValid(Victim)||Victim->IsActorBeingDestroyed()||Combat->IsDead());
    if(bGuardContact)TangGuard->ConfirmBladeHit(Shot);
    if(bAliveBefore&&Applied>0.f&&Training.bCritical&&!Shot.bRicochet&&Shot.bMelee
        &&!Shot.ZhenmoSourceInstance.IsEmpty()&&Shooter&&Shooter->HasAuthority()
        &&Victim&&!Victim->ActorHasTag(TEXT("Friendly"))&&!Victim->ActorHasTag(TEXT("Companion")))
        if(auto* Rune=Shooter->FindComponentByClass<UZhenmoRuneComponent>())Rune->ConfirmCritical(Shot.ZhenmoSourceInstance);
    // Normal stage 3 keeps its own damage formula; the launch now obeys poise.
    // Settle here for both standalone and authoritative remote hits.
    if(bAliveBefore&&Amount>0.f&&IsValid(Victim)&&!Victim->IsActorBeingDestroyed()
        &&Victim->HasAuthority()&&!Combat->IsDead()&&Shot.bMelee&&!Shot.bRicochet
        &&Shot.AttackMeta==3&&Shot.bRisingDragonFinisher&&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter))
    {
        FVector Away=(Victim->GetActorLocation()-Shooter->GetActorLocation()).GetSafeNormal2D();
        if(Away.IsNearlyZero())Away=Direction.GetSafeNormal2D();
        Combat->ReceiveForcedLaunch(Cast<APawn>(Shooter),Away*RuneSwordRisingDragon::LaunchForwardCM+
            FVector(0,0,RuneSwordRisingDragon::LaunchUpCM),RuneSwordRisingDragon::ControlSeconds);
    }
    // 凝碧星核由权威命中入口施加，单机与远端命中共用；重复命中刷新。
    if(bAliveBefore&&Applied>0.f&&IsValid(Victim)&&!Victim->IsActorBeingDestroyed()
        &&Victim->HasAuthority()&&!Combat->IsDead()&&Shot.bMelee&&!Shot.bRicochet
        &&(Shot.AttackMeta&0x80)&&Shot.QuickCombatRuneVulnerabilitySeconds>0.f
        &&Shot.QuickCombatRuneVulnerability>0.f&&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter))
        UCombatStatusFormula::GetOrAdd(Victim)->AddRuneMagicVulnerability(Shot.QuickCombatRuneVulnerability,Shot.QuickCombatRuneVulnerabilitySeconds);
    // 虎啸在快速近战命中结算后施加；期间所有攻击按目标易削韧状态结算。
    if(bAliveBefore&&Amount>0.f&&IsValid(Victim)&&!Victim->IsActorBeingDestroyed()
        &&Victim->HasAuthority()&&!Combat->IsDead()&&Shot.bMelee&&!Shot.bRicochet
        &&(Shot.AttackMeta&0x80)&&Shot.QuickCombatTigerRoarSeconds>0.f
        &&Shot.QuickCombatTigerRoarToughnessBonus>0.f&&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter))
        UCombatStatusFormula::GetOrAdd(Victim)->AddTigerRoar(Shot.QuickCombatTigerRoarToughnessBonus,Shot.QuickCombatTigerRoarSeconds);
    // 破锋燕翎配重：本次命中结算后施加物理易伤，重复命中刷新。
    if(bAliveBefore&&Amount>0.f&&IsValid(Victim)&&!Victim->IsActorBeingDestroyed()
        &&Victim->HasAuthority()&&!Combat->IsDead()&&Shot.bMelee&&!Shot.bRicochet
        &&(Shot.AttackMeta&0x80)&&Shot.QuickCombatPhysicalVulnerabilitySeconds>0.f
        &&Shot.QuickCombatPhysicalVulnerabilityBonus>0.f&&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter))
        UCombatStatusFormula::GetOrAdd(Victim)->AddPhysicalVulnerability(Shot.QuickCombatPhysicalVulnerabilityBonus,Shot.QuickCombatPhysicalVulnerabilitySeconds);
    // Armor can absorb damage and still leave a visible contact. Lethal hits
    // yield entirely to the existing death/ragdoll presentation.
    if(bFirearmContact&&bAliveBefore&&Amount>0.f&&IsValid(Victim)&&!Victim->IsActorBeingDestroyed()
        &&Victim->HasAuthority()&&!Combat->IsDead())
        if(const auto* Character=Cast<ACharacter>(Victim))
            if(auto* Mesh=Cast<UMonsterIdleBreathingMeshComponent>(Character->GetMesh()))
                Mesh->AddGunHitFeedback(Hit,Direction,FMath::Max(Applied,1.f));
    // One contact, one captured ammo effect. Armor reducing the direct damage
    // to zero does not cancel a hit; status immunity still rejects the effect.
    if(Combat&&Victim->HasAuthority()&&!Combat->IsDead())
    {
        if(Shot.AmmoBleedStacks>0)
            UCombatStatusFormula::GetOrAdd(Victim)->AddBleeding(Shooter,Shot.AmmoBleedStacks);
        if(Shot.AmmoPoisonStacks>0)
        {
            auto* Poison=Victim->FindComponentByClass<UMaggotPoisonComponent>();
            if(!Poison){Poison=NewObject<UMaggotPoisonComponent>(Victim);Victim->AddInstanceComponent(Poison);Poison->RegisterComponent();}
            for(int32 Stack=0;Stack<Shot.AmmoPoisonStacks;++Stack)Poison->AddStack(Shooter);
        }
    }
    if(Result)
    {
        Result->BeforeDefense=WeaponHit.Incoming;Result->AfterDefense=WeaponHit.Mitigated;
        Result->Applied=AppliedParts;Result->bResolved=WeaponHit.bResolved;Result->bCritical=Training.bCritical;
        Result->bKilled=bDirectKill;
    }
    // Lethal rewards are committed together with the monster's AwardKill transaction.
    if (Applied>0 && Training.bEligible && !Training.bKillAttempted)
    {
        SyncRuntime();auto P=Snapshot();bool Trained=false;
        auto Train=[&](const FColdSteelSkillDefinition& D,int32 Experience){
            const auto* Progress=P.Skills.Find(D.Id);
            if(Progress&&Progress->Level<D.MaxLevel&&Experience>0){ColdSteelSkills::AddExperience(P,D,Experience);Trained=true;}
        };
        if(!Training.SkillId.IsNone())Train(Skill,Skill.HitExperience+Training.ExtraExperience+(Training.bCritical?Skill.CriticalExperience:0));
        if(Training.bCritical)Train(CriticalStrikeSkill,CriticalStrikeSkill.CriticalHitExperience);
        if(Training.bMelee)Train(DexterousHandsSkill,DexterousHandsSkill.MeleeHitExperience);
        // Hit experience is high-frequency: stage it in the live profile and let
        // the coalesced save own the disk transaction instead of saving per hit.
        if(Trained)StageTraining(MoveTemp(P));
    }
    if(Applied>0&&Combat&&!Combat->IsDead())
        if(auto* Armor=Shooter->FindComponentByClass<UFPSFireMagicComponent>())Armor->OnWeaponHit(Victim,Hit.ImpactPoint);
    return Applied;
}
void UColdSteelStatusModel::QueueProgressNotices(const FColdSteelProfile& Before,const FColdSteelProfile& After)
{
    if (After.Level>Before.Level)
    {
        FColdSteelProgressNotice N; N.Title=FString::Printf(TEXT("角色升级   Lv.%d → %d"),Before.Level,After.Level);
        N.Detail=FString::Printf(TEXT("获得 %d 点属性点 · 打开角色状态进行分配"),After.Points-Before.Points);
        ProgressNotices.Add(MoveTemp(N));
    }
    const FColdSteelSkillDefinition* NoticeDefinitions[]={&StormDomainSkill,&ThunderLanceSkill,&RifleSkill,&PistolSkill,&CriticalStrikeSkill,&FireballSkill,&IceSpikeSkill,&IceWallSkill,&LightningSkill,&HolyLightSkill,&MeteorSkill,&FlameArmorSkill,&DodgeSkill,&DexterousHandsSkill,&QuickCombatSkill,&MasteryDefinition(TEXT("swordMastery")),&MasteryDefinition(TEXT("machineGunMastery")),&MasteryDefinition(TEXT("shotgunMastery")),&MasteryDefinition(TEXT("bowMastery")),&MasteryDefinition(TEXT("heavyStrike")),&MasteryDefinition(TEXT("swordUppercut")),&MasteryDefinition(TEXT("whirlwind")),&MasteryDefinition(TEXT("dashAttack"))};
    for(const auto* Definition:NoticeDefinitions)
    {
    const auto* Old=Before.Skills.Find(Definition->Id); const auto* New=After.Skills.Find(Definition->Id);
    if (Old && New && New->Level>Old->Level)
    {
        FColdSteelProgressNotice N; N.Title=FString::Printf(TEXT("%s升级   Lv.%d → %d"),*Definition->Name,Old->Level,New->Level);
        N.Detail=ColdSteelSkills::EffectSummary(ColdSteelSkills::Effect(*Definition,New->Level)); N.Icon=Definition->Icon;
        if(Definition->Id==TEXT("swordUppercut")){const auto E=ColdSteelSkills::Effect(*Definition,New->Level);N.Detail=FString::Printf(TEXT("上挑 ×%.2f · 力量 +%d · 距离 ×%.3f"),SwordUppercut::HeavyDamageScale*E.HeavyMultiplier,E.Strength,E.UppercutReachMultiplier);}
        if(Definition->Id==TEXT("fireball"))N.Detail=FString::Printf(TEXT("火球威力提升 · 爆炸半径 %.2f 米"),FireballStats(New->Level).Radius/100);
        if(Definition->Id==TEXT("iceSpike"))N.Detail=FString::Printf(TEXT("冰锥威力提升 · 当前 %d 枚"),IceSpikeStats(New->Level).Count);
        if(Definition->Id==TEXT("iceWall"))N.Detail=FString::Printf(TEXT("冰墙成长 · %d 段 · %.1f 秒"),IceWallStats(New->Level).Count,IceWallStats(New->Level).Duration);
        if(FireMagic::IsSkill(Definition->Id))N.Detail=FString::Printf(TEXT("火系魔法提升 · 持续 %.0f 秒"),FireMagicStats(Definition->Id,New->Level).Duration);
        if(Definition->Id==TEXT("holyLight"))N.Detail=TEXT("圣光伤害与治疗提升");
        if(ElectricMagic::IsSkill(Definition->Id))N.Detail=TEXT("电系魔法威力提升");
        if(Definition->Id==TEXT("lightningStrike"))N.Detail=FString::Printf(TEXT("闪电威力提升 · 最多传导 %d 个目标"),LightningStats(New->Level).Count);
        if(Definition->Id==TEXT("dashAttack"))N.Detail=FString::Printf(TEXT("冲刺攻击 ×%.2f · 准备 %.2f 秒"),DashAttackStats(New->Level).DamageMultiplier,DashAttackStats(New->Level).ReadySeconds);
        if(Definition->Id==TEXT("whirlwind"))N.Detail=FString::Printf(TEXT("大旋风 ×%.1f · 力量 +%d"),WhirlwindStats(New->Level).DamageMultiplier,New->Level);
        if(Definition->Id==TEXT("quickCombat")){const auto C=QuickCombatStats(New->Level);N.Detail=FString::Printf(TEXT("快速打击 %.0f · 体力 %.2f"),C.Damage,C.StaminaCost);}
        ProgressNotices.Add(MoveTemp(N));
    }
    }
}
bool UColdSteelStatusModel::PopProgressNotice(FColdSteelProgressNotice& Out)
{ if (ProgressNotices.IsEmpty()) return false; Out=MoveTemp(ProgressNotices[0]); ProgressNotices.RemoveAt(0); return true; }
