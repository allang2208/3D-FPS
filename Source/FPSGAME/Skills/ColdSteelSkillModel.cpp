#include "../Weapons/Kukri/KukriRelentlessComponent.h"
#include "../Weapons/PojunGrip.h"
#include "../Weapons/Kukri/KukriDecisiveComponent.h"
#include "ColdSteelSkillRules.h"
#include "../Weapons/Kukri/HatchetCharmComponent.h"
#include "../Weapons/Kukri/KukriPairedHeavyHit.h"
#include "../Weapons/Kukri/KukriBerserkerComponent.h"
#include "../Weapons/Kukri/KukriFrostRavenComponent.h"
#include "../Weapons/AncientSealSeat.h"
#include "../Combat/AncientBreakingSealComponent.h"
#include "LightningHasteSpeed.h"
#include "../Monsters/RootCrownRigPreview.h"
#include "../Weapons/ZhenmoRuneComponent.h"
#include "../Weapons/TimeSandEchoComponent.h"
#include "../Weapons/DealerEnchantmentComponent.h"
#include "MeleeToughnessTuning.h"
#include "SwordUppercutTuning.h"
#include "../Weapons/HighlandBreakSweep.h"
#include "../UI/ColdSteelStatusModel.h"
#include "FPSFireMagicComponent.h"
#include "../Combat/CoreCombatFormula.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/WildlifeAnimal.h"
#include "../Monsters/WolfMonster.h"
#include "../Monsters/BoundCongregate.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Monsters/MonsterIdleBreathingMeshComponent.h"
#include "../Monsters/PoisonMaggotProjectile.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/FPSMeleeLightningComponent.h"
#include "../Production/ThunderHammerRunes.h"
#include "../Production/ThunderHammerPommel.h"
#include "../Production/ProductionToolStats.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/EagleTalonGuardComponent.h"
#include "../Weapons/RavenQuillChargeComponent.h"
#include "../Props/FPSPracticeTarget.h"
#include "../Weapons/TangDaoGuardComponent.h"
#include "../Weapons/PanChiGuardComponent.h"
#include "../Weapons/RuneSwordRisingDragon.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "../Weapons/WoodenTorchItem.h"
#include "../Weapons/WoodenTorchItem.h"
#include "../Weapons/Staff/StaffCatalog.h"
#include "../Weapons/Unarmed/FPSUnarmedIdleComponent.h"
#include "../Weapons/PistolDualWieldComponent.h"
#include "../Weapons/Spellbook/SpellbookComponent.h"
#include "../Weapons/Kukri/KukriWeaponComponent.h"
#include "../Weapons/Kukri/OffhandKukriComponent.h"
#include "../Production/ProductionToolComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"

FColdSteelSkillProgress UColdSteelStatusModel::RifleProgress() const
{ return MasteryProgress(RifleSkill.Id); }
FColdSteelSkillProgress UColdSteelStatusModel::CriticalStrikeProgress() const
{ return MasteryProgress(CriticalStrikeSkill.Id); }
FColdSteelSkillEffect UColdSteelStatusModel::CriticalStrikeEffect(int32 AtLevel) const
{
    auto E=ColdSteelSkills::Effect(CriticalStrikeSkill,AtLevel<0?CriticalStrikeProgress().Level:AtLevel);
    // Equipment crit-damage lives in bonusStats (weapons keep their own top-level
    // critDamageBonus and are added in the weapon shot path). Set-level crit damage
    // is a separate five-piece effect.
    E.CriticalDamageBonus+=float(EquipmentBonus(TEXT("critDamageBonus"))+SetEffect(TEXT("critDamage")));
    return E;
}
FColdSteelSkillProgress UColdSteelStatusModel::PistolProgress() const
{ return MasteryProgress(PistolSkill.Id); }
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
{ return MasteryProgress(DodgeSkill.Id); }
FColdSteelSkillProgress UColdSteelStatusModel::DexterousHandsProgress() const
{ return MasteryProgress(DexterousHandsSkill.Id); }
FColdSteelSkillEffect UColdSteelStatusModel::DexterousHandsEffect(int32 AtLevel) const
{ return ColdSteelSkills::Effect(DexterousHandsSkill,AtLevel<0?DexterousHandsProgress().Level:AtLevel); }
float UColdSteelStatusModel::ReloadSpeedMultiplier() const
{ return (1.f+DexterousHandsEffect().ReloadSpeed)*LightningHaste::ActionSpeed(RuntimePawn()); }
FColdSteelSkillEffect UColdSteelStatusModel::DodgeEffect(int32 AtLevel) const
{ return ColdSteelSkills::Effect(DodgeSkill,AtLevel<0?DodgeProgress().Level:AtLevel); }
float UColdSteelStatusModel::DodgeStaminaCost(int32 AtLevel) const
{
    const auto* Guard=CurrentPawn.IsValid()?CurrentPawn->FindComponentByClass<UTangDaoGuardComponent>():nullptr;
    const auto* Charms=CurrentPawn.IsValid()?CurrentPawn->HatchetCharms.Get():nullptr;
    return (Charms&&Charms->StepReady()?.76f:1.f)*StaminaTuning.DodgeCost*(1.f-DodgeEffect(AtLevel).DodgeCostReduction)*(Guard?Guard->DodgeStaminaMultiplier():1.f)*ActionStaminaMultiplier();
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
{ return Current.Skills.FindRef(QuickCombatSkill.Id); }
FQuickCombatCast UColdSteelStatusModel::QuickCombatStats(int32 AtLevel,const FMeleeModifiers* PreviewModifiers,const FColdSteelItem* PreviewWeapon,
    const FGunsmithParts* PreviewParts) const
{
    // The conical seat substitutes current weapon physical damage for strength
    // in the same skill formula; level growth and action bonuses remain shared.
    const auto& T=QuickCombatSkill.QuickCombat;
    const int32 L=FMath::Clamp(AtLevel<0?QuickCombatProgress().Level:AtLevel,1,QuickCombatSkill.MaxLevel);
    const float Strength=float(Attribute(TEXT("str")));
    const auto Mods=PreviewModifiers?*PreviewModifiers:ColdSteelMelee::QuickCombatModifiers(this);
    FQuickCombatCast C;
    C.DamageMultiplier=float((1.+Mods.QuickCombatDamageAdd)*Mods.AllAttackDamage*Mods.MartialDamage);
    // (Main hand empty: the lone off-hand kukri / hatchet strikes, ActiveKukriWeapon.)
    const auto* QuickItem=PreviewWeapon?PreviewWeapon:ActiveProductionTool()?ActiveProductionTool():ActiveKukriWeapon();
    float DamageInput=Strength;
    if(const auto* Grip=PojunGrip::Modifiers(QuickItem,this,PreviewParts))
    {
        // Quick combat starts with skill damage, then splits it by the weapon panel.
        // Recover the pre-grip physical fraction so the magic share keeps its value.
        const auto Panel=ColdSteelTool::Evaluate(*QuickItem,this,PreviewParts,&Mods).Damage;
        const double Physical=Panel.BasePhysical+Panel.AddedPhysical;
        const double Before=Physical/Grip->PhysicalDamage+Panel.BaseMagic+Panel.AddedMagic;
        C.DamageMultiplier*=float(Before>0.?Panel.Total()/Before:Grip->PhysicalDamage);
    }
    if(Mods.bQuickCombatUsesWeaponDamage&&QuickItem&&PojunGrip::UsesHammerMotion(*QuickItem))
    {
        auto WeaponMods=Mods;
        // All-attack damage is applied once, outside the complete quick formula.
        WeaponMods.AllAttackDamage=1.;
        const auto Weapon=ColdSteelTool::Evaluate(*QuickItem,this,nullptr,&WeaponMods);
        DamageInput=float(Weapon.Damage.BasePhysical+Weapon.Damage.AddedPhysical);
    }
    C.Damage=(T.DamageBase+T.DamagePerLevel*L+DamageInput*(T.StrengthFactorBase+T.StrengthFactorPerLevel*L))*C.DamageMultiplier;
    if(QuickItem&&(ColdSteelInventory::IsDualPistol(*QuickItem)||ColdSteelInventory::UsesStaffMelee(*QuickItem)))QuickItem=ColdSteelMelee::PairedOneHandedWeapon(QuickItem,this);
    C.Damage*=UKukriBerserkerComponent::DamageMultiplier(QuickItem,this);
    const auto* Bow=PreviewWeapon?PreviewWeapon:ActiveBow();
    if(Bow&&Bow->Definition==TEXT("bow_frontier_compound"))
    {
        const auto* Aurora=ColdSteelBow::AuroraRiser(this,Bow);
        const auto* Active=ColdSteelBow::AuroraRiser(this,ActiveBow());
        const bool Selected=PreviewParts?PreviewParts->FindRef(TEXT("riser"))==TEXT("frontier_aurora"):Aurora!=nullptr;
        if(Selected)
        {
            const auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
            const auto* Part=Aurora?Aurora:(G?G->Option(Bow->Definition,TEXT("riser"),TEXT("frontier_aurora")):nullptr);
            if(Part)C.Damage*=(1.+SetEffect(TEXT("magicDamage")))*Part->Bow.MagicDamage/(Active?Active->Bow.MagicDamage:1.);
        }
    }
    C.KnockbackCM=T.KnockbackCM*float(Mods.QuickCombatKnockback*Mods.AllAttackKnockback);
    C.ToughnessMultiplier=float(Mods.QuickCombatToughnessMultiplier());
    C.BleedChance=FMath::Clamp(float(Mods.QuickCombatBleedChance),0.f,1.f);
    C.bAreaHit=Mods.bQuickCombatAOE;
    C.RangeCM=T.RangeCM*Mods.MartialRange*Mods.QuickCombatRange;
    C.StaminaCost=QuickCombatStaminaCost(L,&Mods,PreviewWeapon,PreviewParts);
    return C;
}
float UColdSteelStatusModel::QuickCombatStaminaCost(int32 AtLevel,const FMeleeModifiers* PreviewModifiers,const FColdSteelItem* PreviewWeapon,const FGunsmithParts* PreviewParts) const
{
    if(UEagleTalonGuardComponent::Ready(this))return 0.f;
    const auto& T=QuickCombatSkill.QuickCombat;
    const int32 L=FMath::Clamp(AtLevel<0?QuickCombatProgress().Level:AtLevel,1,QuickCombatSkill.MaxLevel);
    const auto Mods=PreviewModifiers?*PreviewModifiers:ColdSteelMelee::QuickCombatModifiers(this);
    const float Reduction=FMath::Clamp(T.StaminaReductionPerLevel*(L-1),0.f,1.f);
    const auto* Riser=ColdSteelBow::EclipseRiser(this, PreviewWeapon ? PreviewWeapon : ActiveBow(), PreviewParts);
    return T.StaminaCost*(1.f-Reduction)*float(Mods.Stamina*ColdSteelMelee::TemporaryModifiers(this).Stamina)
        *ActionStaminaMultiplier()*float(Riser ? Riser->Bow.Stamina : 1.);
}
bool UColdSteelStatusModel::TrainQuickCombat(int32 Amount)
{
    if(Amount<=0||QuickCombatProgress().Level>=QuickCombatSkill.MaxLevel)return false;
    SyncRuntime();auto P=Snapshot();ColdSteelSkills::AddExperience(P,QuickCombatSkill,Amount);return StageTraining(MoveTemp(P));
}
float UColdSteelStatusModel::QuickCombatCooldown() const
{ return Current.bQuickCombatReserved?Current.QuickCombatCooldown:0.f; }
bool UColdSteelStatusModel::SpendQuickCombatResources(float StaminaCost,float& ManaPaid)
{
    ManaPaid=0.f;
    const bool Aurora=ColdSteelBow::AuroraRiser(this,ActiveBow())!=nullptr;
    const float Due=Aurora&&!HasInfiniteMana()?AdjustedManaCost(StaminaCost):0.f;
    if(!CanSpendMana(Due)){Message=TEXT("魔法不足");return false;}
    if(!SpendStamina(StaminaCost))return false;
    Current.Mana-=Due;
    ManaPaid=Due;
    return true;
}
bool UColdSteelStatusModel::CommitQuickCombatCast(float ActionDuration)
{
    if(Current.bQuickCombatReserved)return false;
    if(!IsSkillLearned(TEXT("quickCombat"))){Message=TEXT("尚未习得快速进战");return false;}
    if(bPersistenceBlocked&&!bNetShadowProfile)return false;
    auto* PS=CurrentPawn.IsValid()?CurrentPawn->GetPlayerState<AColdSteelPlayerState>():nullptr;
    if(GetWorld()&&GetWorld()->GetNetMode()==NM_Client&&!PS)return false;
    const float Cost=QuickCombatStaminaCost();
    float ManaPaid=0.f;
    if(!SpendQuickCombatResources(Cost,ManaPaid))return false;
    Current.bQuickCombatReserved=true;
    UpdateQuickCombatAction(ActionDuration,ActionDuration);
    if(GetWorld()&&GetWorld()->GetNetMode()==NM_Client)PS->RequestQuickCombat(ActionDuration,Cost,ManaPaid);
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
    if(Current.bQuickCombatReserved&&GetWorld()&&GetWorld()->GetNetMode()==NM_Client&&CurrentPawn.IsValid())
        if(auto* PS=CurrentPawn->GetPlayerState<AColdSteelPlayerState>())PS->FinishQuickCombat();
    Current.bQuickCombatReserved=false;
    Current.QuickCombatCooldown=Current.QuickCombatCooldownDuration=0.f;
}
bool UColdSteelStatusModel::TriggerQuickCombat()
{
    // F/快捷栏统一入口：完整动作期间拒绝再次施放，结束后没有额外冷却。
    // 各类武器共用体力、修炼和数值合同：
    //   剑类 → 符文剑配重锤；单持手枪 → 握把砸击；其余枪械 → 步枪枪托砸击。
    if(!IsSkillLearned(TEXT("quickCombat"))){Message=TEXT("尚未习得快速进战　按 P 打开技能树");return false;}
    if(Current.bQuickCombatReserved)
    {
        UE_LOG(LogTemp,Log,TEXT("[QuickCombat] 动作尚未结束（剩余 %.2f 秒），忽略触发"),QuickCombatCooldown());
        return false;
    }
    auto* Player=Cast<AFPSGAMECharacter>(UGameplayStatics::GetPlayerPawn(this,0));
    if(!Player)return false;
    if(UBoundCongregateCaptureComponent::IsCaptured(Player))
        if(auto* Hands=Player->FindComponentByClass<UFPSUnarmedIdleComponent>();Hands&&Hands->IsEquipped())return Hands->BeginPunch();
    if(!ActiveProductionTool()&&ColdSteelInventory::QuickTorch(Equipped(),Equipped(ActiveOffhandSlot())))
    {
        auto* Staff=Player->FindComponentByClass<UStaffWeaponComponent>();
        return Staff&&Staff->BeginQuickCombat();
    }
    if(auto* Book=Player->FindComponentByClass<USpellbookComponent>();Book&&Book->IsEquipped())return Book->BeginQuickCombat();
    if(auto* Staff=Player->FindComponentByClass<UStaffWeaponComponent>();Staff&&Staff->HasMeleeMoveset())return Staff->BeginQuickCombat();
    if(auto* Bow=Player->FindComponentByClass<UBowWeaponComponent>();Bow && Bow->IsEquipped())return Bow->BeginQuickCombat();
    if(const auto* Item=ActiveProductionTool();Item&&PojunGrip::UsesHammerMotion(*Item))
    {
        auto* Tool=Player->FindComponentByClass<UProductionToolComponent>();
        return Tool&&Tool->BeginQuickCombat();
    }
    if(auto* Sword=Player->FindComponentByClass<URuneSwordComponent>())
        if(Sword->IsEquipped())return Sword->BeginQuickCombatStrike();
    // 尼泊尔弯刀 → 刀把砸击（KukriQuickCombat.cpp）。
    if(auto* Kukri=Player->FindComponentByClass<UKukriWeaponComponent>();Kukri&&Kukri->IsEquipped())return Kukri->BeginQuickCombat();
    // 手枪＋副手弯刀固定出刀。按装备身份分派，ADS／冲刺／占手动作的可中断性由刀处理；
    // 刀暂不可用时也不能回退到手枪砸击（F 与快捷栏共用此入口）。
    if(auto* Offhand=Player->FindComponentByClass<UOffhandKukriComponent>();Offhand&&Offhand->IsEquipped())return Offhand->BeginQuickCombat();
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
float UColdSteelStatusModel::ApplySkillWeaponHit(AActor* Shooter,const FHitResult& Hit,float Damage,const FVector& Direction,const FColdSteelSkillShot& Shot,FWeaponDamageResult* Result,FKukriPairedHeavyHit* PairedHeavy)
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
    const bool GaleEnemy=Shot.GalePaymentKey && bAliveBefore && Shooter && Shooter->HasAuthority() &&
        !Shot.bRicochet && UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter);
    FTrainingHit Training; Training.Victim=Victim;
    const FName Mastery=Shot.MasteryId.IsNone()?(Shot.bPistol?FName(TEXT("pistolMastery")):(Shot.bRifle?FName(TEXT("rifleMastery")):NAME_None)):Shot.MasteryId;
    const auto& Skill=MasteryDefinition(Mastery);
    Training.SkillId=Mastery;Training.ExtraExperience=Shot.ExtraMasteryExperience;Training.bMelee=Shot.bMelee;
    const bool bBowEnemy=Mastery==TEXT("bowMastery") && UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter);
    // Both bow skills must share the same live enemy gate. Friendly/companion
    // contacts previously trained bow mastery while correctly rejecting Hands.
    Training.bEligible=Combat && !Combat->IsDead() && !Victim->ActorHasTag(TEXT("Summoned")) && !Victim->ActorHasTag(TEXT("NoSkillTraining"))
        && (Mastery!=TEXT("bowMastery") || bBowEnemy)
        && (!ColdSteelSkills::IsMeleeMastery(Mastery)||ColdSteelSkills::IsMasteryTrainingTarget(Shooter,Victim));
    Training.bPerfectBowHit=Shot.bPerfectBowRelease && bBowEnemy && !Shot.bRicochet
        && Shooter && Shooter->HasAuthority();
    Training.bHeartPiercingArrow=Shot.bHeartPiercingArrow && bBowEnemy && !Shot.bRicochet
        && Shooter && Shooter->HasAuthority();
    struct FPreparedBlade
    {
        CombatFormulaRuntime::WeaponHit Weapon;
        FVector2D Pendant=FVector2D(1,1);
        float Amount=0.f,GuardBonus=0.f,PanChi=1.f;
        bool Critical=false;
    };
    const auto PrepareBlade=[&](const FHitResult& Hit,float Damage,const FColdSteelSkillShot& Shot)
    {
        FPreparedBlade Prepared;
        const bool Weakpoint=!Shot.bRicochet&&ColdSteelSkills::IsCriticalHit(Hit);
        // 枪械在开火时预掷一次（霰弹多弹丸、穿透多目标共用），近战/快捷进战仍按接触点各掷。
        const float CriticalRoll=Shot.CriticalRoll>=0.f?Shot.CriticalRoll:FMath::FRand();
        const auto* TargetStatus=Victim?Victim->FindComponentByClass<UCombatStatusFormula>():nullptr;
        float CriticalChance=Shot.CriticalChance+(Shot.bEagleTalonStrike?30.f:0.f)+(TargetStatus?TargetStatus->CriticalVulnerabilityBonusPercent():0.f);
        if(Shot.AttackMeta==ShadowStep::AttackMetaStage2&&Shot.bMelee&&!Shot.bRicochet&&Victim&&Shooter)
        {
            const bool bBroken=Combat&&Combat->IsToughnessBroken();
            const FVector VictimFwd=Victim->GetActorForwardVector().GetSafeNormal2D();
            const FVector FromAttacker=(Victim->GetActorLocation()-Shooter->GetActorLocation()).GetSafeNormal2D();
            const bool bBackstab=!VictimFwd.IsNearlyZero()&&!FromAttacker.IsNearlyZero()&&FVector::DotProduct(VictimFwd,FromAttacker)>.25f;
            if(bBroken||bBackstab)CriticalChance+=MasteryDefinition(ShadowStep::SkillId).ShadowStep.FollowupBackstabCritBonus;
        }
        bool GuardOtherTarget=false;
        if(Damage>0.f&&Shot.bMelee&&!Shot.bRicochet&&Shot.ItemDefinition==TEXT("ue_forged_steel_greatsword")
            &&Shooter&&Shooter->HasAuthority())
        {
            auto* Raven=Shooter->FindComponentByClass<URavenQuillChargeComponent>();
            const bool RavenActive=Raven&&Raven->Matches(Shot);
            if(RavenActive||Shot.bEagleTalonStrike)
            {
                if(IsValid(Victim)&&Victim->CanBeDamaged())
                {
                    const auto* Animal=Cast<AColdSteelAnimal>(Victim);
                    GuardOtherTarget=Victim->IsA<AFPSPracticeTarget>()||(Animal&&!Animal->IsDead()
                        &&!Victim->ActorHasTag(TEXT("Friendly"))&&!Victim->ActorHasTag(TEXT("Companion")));
                }
                if(RavenActive&&(GuardOtherTarget||UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter)))
                    CriticalChance+=Raven->ContactBonus(Shot);
            }
        }
        Prepared.Critical=Shot.bRicochet?Shot.bInheritedCritical:
            (Weakpoint||((Combat||GuardOtherTarget)&&CriticalRoll*100.f<CoreCombatFormula::CriticalChance(CriticalChance,CombatFormulaRuntime::MonsterCriticalResistance(Victim))));
        // 要害加成按数值生效：步枪精通与枪械自带（M1911「要害特化」）共用同一乘区，
        // 未声明要害加成的武器 WeakpointPercent 为 0，行为与旧版按 bRifle 判定完全一致。
        float Amount=Damage*(Weakpoint&&Shot.WeakpointPercent>0?1+Shot.WeakpointPercent:1);
        const FVector2D PendantBonus=UKukriDecisiveComponent::Multipliers(Shot,this);
        Amount*=PendantBonus.X;
        auto* TangGuard=Shooter?Shooter->FindComponentByClass<UTangDaoGuardComponent>():nullptr;
        const bool bGuardContact=TangGuard&&bAliveBefore&&Damage>0.f&&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter);
        float GuardToughnessBonus=0.f;
        auto* PanChi=Shooter?Shooter->FindComponentByClass<UPanChiGuardComponent>():nullptr;
        const bool bPanChiContact=bAliveBefore&&Damage>0.f&&PanChi&&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter);
        const float PanChiToughness=bPanChiContact?PanChi->UppercutToughnessMultiplier(Shot):1.f;
        if(bGuardContact)Amount*=TangGuard->ConsumeDragon(Shot,GuardToughnessBonus);
        float WagerBonus=0.f;
        // 普通暴击与要害暴击共用这一次判定；继承伤害的次生命中不重复叠层。
        if(Shooter&&Shooter->HasAuthority()&&Prepared.Critical&&!Shot.bRicochet&&Damage>0.f
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
            if(Prepared.Critical){WagerBonus=Status->WagerCriticalBonus();Status->ConsumeWager();}
        }
        // 武器暴击在防御前乘、法术暴击（CoreCombatFormula::CriticalDamage）在防御后乘：
        // 两者都是乘性、可交换，只在逐段取整上差 ≤1 点，因此不搬动这条链（会牵动削韧/回血口径）。
        if(!Shot.bRicochet&&Prepared.Critical&&(Shot.CriticalDamageBonus+WagerBonus)>0)Amount*=1+Shot.CriticalDamageBonus+WagerBonus;
        // The fifth valid enemy contact adds its card before scaling the entire damage panel.
        if(Shooter&&Shooter->HasAuthority()&&bAliveBefore&&Damage>0.f&&!Shot.bRicochet&&Shot.Dealer.Enabled
            &&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter))
            if(auto* Dealer=Shooter->FindComponentByClass<UDealerEnchantmentComponent>())
                Amount*=Dealer->Hit(Shot.DealerSourceInstance,Shot.Dealer,Prepared.Critical);
        auto& WeaponHit=Prepared.Weapon;WeaponHit.Target=Victim;WeaponHit.bMelee=Shot.bMelee||Shot.bMeleeStrike;
        // Damage already contains this attack's heavy/combo/range multiplier. Apply
        // the same multiplier and shared critical roll to every panel component.
        auto Panel=Shot.DamagePanel;
        const bool PairedDash=Shot.bMelee&&!Shot.bRicochet&&Shot.AttackMeta==0x16&&Shot.PairedDashOffPhysical.Total()>0.;
        if(PairedDash){Panel=Shot.PairedDashMainPhysical;Panel+=Shot.PairedDashOffPhysical;}
        WeaponHit.Incoming=Panel.Total()>0?Panel.Scaled(Amount/Panel.Total()):FWeaponDamageParts{Amount,0,0,0};
        if(!Shot.bRicochet&&(Shot.AttackMeta==0x10||Shot.AttackMeta==0x15))
        {
            WeaponHit.Incoming.BasePhysical*=Shot.OathPhysicalMultiplier;
            WeaponHit.Incoming.AddedPhysical*=Shot.OathPhysicalMultiplier;
        }
        const bool bNormalOrHeavy=(Shot.AttackMeta>=1&&Shot.AttackMeta<=3)||Shot.AttackMeta==0x10;
        if(Shot.bFishtailPommel&&bNormalOrHeavy&&Shot.bMelee&&!Shot.bRicochet&&Shot.AttackForm==EMonsterAttackForm::Blade
            &&bAliveBefore&&Combat->IsToughnessBroken()&&Combat->ToughnessPhaseSecondsRemaining()>0.f
            &&Shooter&&Shooter->HasAuthority()&&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter))
        {
            WeaponHit.Incoming.BasePhysical*=1.25;
            WeaponHit.Incoming.AddedPhysical*=1.25;
        }
        Amount=WeaponHit.Incoming.Total();
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
        if(PairedDash)
        {
            // Resolve defense per blade instead of lending the main hand's penetration
            // to the entire combined hit or averaging a nonlinear defense formula.
            const double Scale=Amount/Panel.Total();
            WeaponHit.Contributions.Add({Shot.PairedDashMainPhysical.Scaled(Scale),{},Shot.ArmorPenetration,0.});
            WeaponHit.Contributions.Add({Shot.PairedDashOffPhysical.Scaled(Scale),{},Shot.PairedDashOffPenetration,0.});
        }
        Prepared.Amount=Amount;Prepared.Pendant=PendantBonus;Prepared.GuardBonus=GuardToughnessBonus;Prepared.PanChi=PanChiToughness;
        return Prepared;
    };
    auto* Charms=Shooter?Shooter->FindComponentByClass<UHatchetCharmComponent>():nullptr;
    const bool CharmContact=Charms&&Shooter->HasAuthority()&&bAliveBefore&&Shot.bMelee&&!Shot.bRicochet
        &&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter);
    if(CharmContact)Charms->Configure(this);
    const bool FirstWedge=CharmContact&&Damage>0.f&&Charms->CanWedge(Shot,Victim);
    const bool SecondWedge=CharmContact&&PairedHeavy&&PairedHeavy->Second.Damage>0.f&&Charms->CanWedge(PairedHeavy->Second.Shot,Victim);
    const bool CouldBreak=CharmContact&&Combat->UsesToughnessBar()&&!Combat->IsToughnessBroken();
    auto First=PrepareBlade(Hit,Damage,Shot);
    FPreparedBlade Second;
    if(PairedHeavy)Second=PrepareBlade(PairedHeavy->Second.Hit,PairedHeavy->Second.Damage,PairedHeavy->Second.Shot);
    Training.bCritical=First.Critical||(PairedHeavy&&Second.Critical);
    TGuardValue<FTrainingHit*> HitScope(ActiveTrainingHit,&Training);
    auto WeaponHit=MoveTemp(First.Weapon);
    float Amount=First.Amount;
    const FVector2D PendantBonus=First.Pendant;
    float GuardToughnessBonus=First.GuardBonus;
    const float PanChiToughness=First.PanChi;
    auto* TangGuard=Shooter?Shooter->FindComponentByClass<UTangDaoGuardComponent>():nullptr;
    const bool bGuardContact=TangGuard&&bAliveBefore&&Damage>0.f&&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter);
    const bool bAzureDragon=Shot.bMelee&&!Shot.bRicochet&&Shot.AzureDragonPhysicalMultiplier>1.f;
    if(PairedHeavy)
    {
        WeaponHit.Contributions.Add({WeaponHit.Incoming,{},WeaponHit.PhysicalPenetration,WeaponHit.MagicPenetration});
        WeaponHit.Contributions.Add({Second.Weapon.Incoming,{},Second.Weapon.PhysicalPenetration,Second.Weapon.MagicPenetration});
        WeaponHit.Incoming+=Second.Weapon.Incoming;Amount=WeaponHit.Incoming.Total();
        PairedHeavy->Critical[0]=First.Critical;PairedHeavy->Critical[1]=Second.Critical;
    }
    TGuardValue<CombatFormulaRuntime::WeaponHit*> DamageScope(CombatFormulaRuntime::ActiveWeaponHit,&WeaponHit);
    // 普通怪沿用 hit_stagger 枪械闸门；精英以上默认不再削韧，只有目录声明
    // "toughness_damage": true 的枪才会累积韧性，破韧期枪弹可造成短硬直。
    // 闸门关闭时受击端只记住攻击者，不动状态机、韧性时钟或硬直动作。
    // 枪弹局部回弹单独叠到原姿态，不经过这道控制状态闸门。
    // 近战武器与手持枪械发动的近战打击（bMeleeStrike）不在闸门覆盖范围内：
    // 它们按原倍率进入受击端，否则削韧与硬直会被整段吞掉。
    bool bFirearmWithoutStagger=false;
    bool bFirearmToughness=false;
    bool bFirearmToughnessRangeLimited=false;
    bool bFirearmContact=false;
    const FString WeaponDefinition=Shot.ItemDefinition.IsEmpty()?(Equipped()?Equipped()->Definition:FString()):Shot.ItemDefinition;
    if(!Shot.bMelee&&!Shot.bMeleeStrike&&!WeaponDefinition.IsEmpty())
        if(auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>())
            if(const auto* W=G->Weapon(WeaponDefinition))
            {
                bFirearmWithoutStagger=!W->bHitStagger;
                // 2026-10-19 用户规则：枪械默认不造成韧性伤害，只有目录声明
                // "toughness_damage": true 的枪（SVD／SVCh／左轮 715／RSH-12）才削韧。
                bFirearmToughness=W->bToughnessDamage;
                // 霰弹枪（2026-10-19 用户规则）：只在有效射程内削韧，超出射程的命中不削韧。
                // 射程与距离都在下面按命中结果现算，不在开火快照里固化。
                bFirearmToughnessRangeLimited=W->bToughnessRangeLimited;
                bFirearmContact=!G->IsMelee(WeaponDefinition)&&!G->IsTool(WeaponDefinition)
                    &&!G->IsStaff(WeaponDefinition)&&!G->IsBow(WeaponDefinition);
            }
    auto* Animal = Cast<AColdSteelAnimal>(Victim);
    auto ApplyDamage=[&](){ return UGameplayStatics::ApplyPointDamage(Victim,Amount,Direction,Hit,
        Pawn?Pawn->GetController():nullptr,Shooter,Animal && bFirearmContact ? UWildlifeGunDamage::StaticClass() : nullptr); };
    // 命中形式的唯一收口：所有武器命中都在这里标注，受击端据此折算削韧。
    const bool bExecutionerContact=Shot.bExecutionerBlade&&Shot.bMelee&&!Shot.bRicochet
        &&Shot.AttackForm==EMonsterAttackForm::Blade&&(Shot.AttackMeta&(0x40|0x80))==0;
    const MonsterToughness::FScopedForm FormScope(bExecutionerContact?EMonsterAttackForm::Blunt:Shot.AttackForm);
    float FixedToughness=Shot.bMelee&&!Shot.bRicochet?MeleeToughness::FixedBaseFor(Shot.AttackMeta):-1.f;
    // 目录未声明削韧的枪械整段关闭韧性通道（精英以上的韧性条同样按 0 倍率结算），
    // 受击端不累积韧性、不刷新削韧时钟，也不会被枪弹打破韧；生命伤害照常。
    // 目录声明 toughness_range_limited 的霰弹枪只保留有效射程内的那一部分命中。
    // 射程取射手当前武器的有效射程（含弹种倍率），距离取命中结果自带的射线起点到命中点：
    // 枪械命中端统一把它写成枪口／发射点（弹道写 LaunchOrigin，枪口顶住的即时命中写 Muzzle，
    // 服务端重建的远端命中写上报的 AimOrigin），因此与伤害衰减同一口径，且权威端可自行复算。
    bool bBeyondToughnessRange=false;
    if(bFirearmToughnessRangeLimited)
    {
        const auto* RangeOwner=Cast<AFPSGAMECharacter>(Shooter);
        const float EffectiveRangeCM=RangeOwner?RangeOwner->GetEffectiveWeaponRangeCM():0.f;
        bBeyondToughnessRange=EffectiveRangeCM<=0.f
            ||FVector::Dist(Hit.TraceStart,Hit.ImpactPoint)>EffectiveRangeCM;
    }
    const bool bToughnessBlocked=bFirearmContact&&(!bFirearmToughness||bBeyondToughnessRange);
    // Damage-derived toughness already contains the pendant damage multiplier;
    // cancel it before applying the independent toughness multiplier.
    const float PendantToughness=PendantBonus.Y/(FixedToughness>=0.f?1.f:PendantBonus.X);
    float ToughnessScale=bToughnessBlocked?0.f:Shot.ToughnessDamageMultiplier*PanChiToughness*UKukriFrostRavenComponent::ToughnessMultiplier(Shot,this)*PendantToughness*(FirstWedge?1.3f:1.f);
    if(PairedHeavy)
    {
        const auto& Other=PairedHeavy->Second.Shot;
        const float OtherScale=Other.ToughnessDamageMultiplier*Second.PanChi*UKukriFrostRavenComponent::ToughnessMultiplier(Other,this)*Second.Pendant.Y*(SecondWedge?1.3f:1.f);
        // Fixed heavy poise is summed per actual blade, independently of HP damage.
        GuardToughnessBonus=GuardToughnessBonus*ToughnessScale+Second.GuardBonus*OtherScale;
        FixedToughness=FixedToughness*ToughnessScale+MeleeToughness::FixedBaseFor(Other.AttackMeta)*OtherScale;
        ToughnessScale=1.f;
    }
    auto ApplyToughness=[&](){return Combat?Combat->ApplyHitWithToughnessScale(ToughnessScale,ApplyDamage,FixedToughness,GuardToughnessBonus):ApplyDamage();};
    float Applied=(Combat&&bFirearmWithoutStagger&&!Combat->UsesToughnessBar())?Combat->ApplyHitWithReactionScale(0.f,ApplyToughness):ApplyToughness();
    FWeaponDamageParts AppliedParts=WeaponHit.Mitigated.LimitedTo(Applied);
    if(PairedHeavy)
    {
        const double Total=WeaponHit.bResolved?WeaponHit.Mitigated.Total():WeaponHit.Incoming.Total();
        for(int32 I=0;I<2;++I)
        {
            const auto& Part=WeaponHit.Contributions[I];
            const double Share=WeaponHit.bResolved?Part.Mitigated.Total():Part.Incoming.Total();
            PairedHeavy->Applied[I]=Total>0.?Applied*Share/Total:0.f;
        }
    }
    if(CharmContact&&Applied>0.f)
    {
        const bool Broke=CouldBreak&&IsValid(Victim)&&Combat->IsToughnessBroken();
        if(!PairedHeavy||PairedHeavy->Applied[0]>0.f)Charms->Confirm(Shot,Victim,FirstWedge,Broke,this);
        if(PairedHeavy&&PairedHeavy->Applied[1]>0.f)Charms->Confirm(PairedHeavy->Second.Shot,Victim,SecondWedge,Broke,this);
    }
    // Native slam, thrown landing, JiLei and overload retain the attacking
    // hammer's snapshot. A physical-only kill must not grant the electric buff.
    if(bAliveBefore&&Shot.HammerElectricDamage>0.f)
        ThunderHammerPommel::ConfirmElectricDamage(Shooter,Shot.HammerLightning,
            float(AppliedParts.BaseMagic+AppliedParts.AddedMagic));
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
    if(bDirectKill && GaleEnemy)
        if(auto* Sword=Shooter->FindComponentByClass<URuneSwordComponent>())
            Sword->ConfirmGaleKill(Shot.GalePaymentKey,Shot.ItemInstance);
    if(Shot.FirearmCriticalStunSeconds>0.f&&First.Critical&&!Shot.bRicochet&&bAliveBefore&&Applied>0.f&&!bDirectKill
        &&Shooter&&Shooter->HasAuthority()&&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter))
    {
        Combat->ReceiveStun(Cast<APawn>(Shooter),Shot.FirearmCriticalStunSeconds,0.f);
        Combat->ShowZhimingCritical(Hit.ImpactPoint+Hit.ImpactNormal,Shot.FirearmCriticalStunSeconds);
    }
    // Charge each participating blade once, after resolving the contact against
    // the old armor. Both hands use their own authoritative equipment snapshot.
    const int32 ScytheContacts=int32(Shot.bGhostScytheContact&&First.Amount>0.f)
        +int32(PairedHeavy&&PairedHeavy->Second.Shot.bGhostScytheContact&&Second.Amount>0.f)
        +int32(Shot.AttackMeta==0x16&&Shot.bPairedDashOffGhostScythe&&Shot.PairedDashOffPhysical.Total()>0.);
    if(ScytheContacts&&Shot.bMelee&&!Shot.bRicochet&&Shooter&&Shooter->HasAuthority()
        &&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter))
        UCombatStatusFormula::GetOrAdd(Victim)->AddArmorCorrosion(ScytheContacts);
    if(bAliveBefore&&Applied>0.f&&IsValid(Victim)&&!Victim->IsActorBeingDestroyed()&&!Combat->IsDead()
        &&(Shot.bHammerRuneContact||Shot.HammerNativeStacks>0))
        ThunderHammerRunes::OnHit(Shooter,Victim,Shot);
    if(bGuardContact)TangGuard->ConfirmBladeHit(Shot);
    if(bAliveBefore&&Applied>0.f&&First.Critical&&(Shot.bBlackthornCriticalWeakness||Shot.bWhitehartCriticalVulnerability)
        &&Shot.bMelee&&!Shot.bRicochet&&Shot.ItemDefinition==TEXT("ue_highland_claymore")
        &&Shooter&&Shooter->HasAuthority()&&IsValid(Victim)&&!Victim->IsActorBeingDestroyed()
        &&!Combat->IsDead()&&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter))
    {
        // Apply after this hit's critical roll and damage; new layers benefit subsequent attacks.
        auto* Status=UCombatStatusFormula::GetOrAdd(Victim);
        if(Shot.bBlackthornCriticalWeakness)Status->AddWeakness();
        if(Shot.bWhitehartCriticalVulnerability)Status->AddCriticalVulnerability();
    }
    if(bAliveBefore&&Applied>0.f&&First.Critical&&!Shot.bRicochet&&Shot.bMelee
        &&!Shot.ZhenmoSourceInstance.IsEmpty()&&Shooter&&Shooter->HasAuthority()
        &&Victim&&!Victim->ActorHasTag(TEXT("Friendly"))&&!Victim->ActorHasTag(TEXT("Companion")))
        if(auto* Rune=Shooter->FindComponentByClass<UZhenmoRuneComponent>())Rune->ConfirmCritical(Shot.ZhenmoSourceInstance);
    if(PairedHeavy&&bAliveBefore&&PairedHeavy->Applied[1]>0.f&&Second.Critical
        &&!PairedHeavy->Second.Shot.ZhenmoSourceInstance.IsEmpty()&&Shooter&&Shooter->HasAuthority()
        &&Victim&&!Victim->ActorHasTag(TEXT("Friendly"))&&!Victim->ActorHasTag(TEXT("Companion")))
        if(auto* Rune=Shooter->FindComponentByClass<UZhenmoRuneComponent>())Rune->ConfirmCritical(PairedHeavy->Second.Shot.ZhenmoSourceInstance);
    // Settle uppercut after damage/poise so a break caused by this hit qualifies.
    // Both weapon families and remote authority use this single launch receipt.
    const bool bUppercutLaunch=Shot.AttackMeta==SwordUppercut::AttackMeta;
    const bool bFinisherLaunch=Shot.AttackMeta==3&&Shot.bRisingDragonFinisher;
    const bool bSweepLaunch=Shot.AttackMeta==HighlandBreakSweep::AttackMeta&&WeaponDefinition==TEXT("ue_highland_claymore")&&Applied>0.f;
    if(bAliveBefore&&Amount>0.f&&IsValid(Victim)&&!Victim->IsActorBeingDestroyed()
        &&Victim->HasAuthority()&&!Combat->IsDead()&&Shot.bMelee&&!Shot.bRicochet
        &&(bUppercutLaunch||bFinisherLaunch||bSweepLaunch)&&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter))
    {
        FVector Away=(Victim->GetActorLocation()-Shooter->GetActorLocation()).GetSafeNormal2D();
        if(Away.IsNearlyZero())Away=Direction.GetSafeNormal2D();
        const float Forward=bUppercutLaunch?SwordUppercut::LaunchForwardCM:RuneSwordRisingDragon::LaunchForwardCM;
        const float Up=bUppercutLaunch?SwordUppercut::LaunchUpCM:RuneSwordRisingDragon::LaunchUpCM;
        const float Hold=bUppercutLaunch?SwordUppercut::ControlSeconds:RuneSwordRisingDragon::ControlSeconds;
        // The monster gate admits unarmoured normals and currently broken bars.
        if(bSweepLaunch)
            Combat->ReceiveForcedLaunch(Cast<APawn>(Shooter),Away*HighlandBreakSweep::LaunchOutCMPerSecond+
                FVector::UpVector*HighlandBreakSweep::LaunchUpCMPerSecond,HighlandBreakSweep::LaunchControlSeconds);
        else
            Combat->ReceiveForcedLaunch(Cast<APawn>(Shooter),Away*Forward+FVector(0,0,Up),Hold);
    }
    // Shared conduction rune: settle once after each valid authoritative hammer
    // contact, including the heavy/sprint wave that carries the same snapshot.
    if(bAliveBefore&&Applied>0.f&&IsValid(Victim)&&!Victim->IsActorBeingDestroyed()
        &&Victim->HasAuthority()&&!Combat->IsDead()&&Shot.bMelee&&!Shot.bRicochet
        &&Shot.BluntRuneVulnerability>0.f&&Shot.BluntRuneVulnerabilitySeconds>0.f
        &&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter))
        UCombatStatusFormula::GetOrAdd(Victim)->AddRuneMagicVulnerability(Shot.BluntRuneVulnerability,Shot.BluntRuneVulnerabilitySeconds);
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
    // Apply the target seal after this contact's damage and poise settlement.
    // The server's weapon snapshot fixes the seat identity for remote quick hits.
    if(bAliveBefore&&Applied>0.f&&IsValid(Victim)&&!Victim->IsActorBeingDestroyed()
        &&Victim->HasAuthority()&&!Combat->IsDead()&&Shot.bMelee&&!Shot.bRicochet
        &&(Shot.AttackMeta&0x80)&&Shot.bQuickCombatBreakingSeal
        &&AncientSealSeat::Supports(Shot.ItemDefinition)&&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter))
        if(auto* Status=UCombatStatusFormula::GetOrAdd(Victim);Status&&!Status->IsImmune())
            UAncientBreakingSealComponent::Apply(Victim,Shooter,Hit.ImpactPoint,AncientSealSeat::Seconds);
    // Armor can absorb damage and still leave a visible contact. Lethal hits
    // yield entirely to the existing death/ragdoll presentation.
    if(!Animal&&bFirearmContact&&bAliveBefore&&Amount>0.f&&IsValid(Victim)&&!Victim->IsActorBeingDestroyed()
        &&Victim->HasAuthority()&&!Combat->IsDead())
        if(auto* Crown=Cast<ARootCrownRigPreview>(Victim))
            Crown->PresentGunContact(Hit,Direction,FMath::Max(Applied,1.f));
        else if(auto* Wolf=Cast<AWolfMonster>(Victim); Wolf && Wolf->IsWildlifeWolf())
            Wolf->MulticastWildlifeGunHit(Hit.BoneName,Hit.ImpactPoint,Direction,FMath::Max(Applied,1.f));
        else if(const auto* Character=Cast<ACharacter>(Victim))
            if(auto* Mesh=Cast<UMonsterIdleBreathingMeshComponent>(Character->GetMesh()))
                Mesh->AddGunHitFeedback(Hit,Direction,FMath::Max(Applied,1.f));
    // The attack's existing target deduplication owns contact frequency. Keep
    // bleed in this authoritative settlement so offhand and skill hits agree;
    // status ticks and secondary damage never enter this melee contact branch.
    if(bAliveBefore&&Amount>0.f&&IsValid(Victim)&&!Victim->IsActorBeingDestroyed()
        &&Victim->HasAuthority()&&!Combat->IsDead()&&Shot.bMelee&&!Shot.bRicochet
        &&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter))
    {
        int32 BleedStacks=Shot.MeleeHitBleedStacks+(PairedHeavy?PairedHeavy->Second.Shot.MeleeHitBleedStacks:0);
        // The kukri dash settles both blades as one damage contact. Its snapshot
        // describes the main hand, so include the participating offhand here.
        // Ordinary contacts carry separate snapshots; paired heavy was added above.
        if(Shot.AttackMeta==0x16)
            if(const auto* Main=Equipped();Main&&ColdSteelInventory::UsesKukriMoveset(*Main)&&Main->InstanceId==Shot.ItemInstance)
                if(const auto* Off=ColdSteelMelee::PairedOneHandedWeapon(Main,this))
                    BleedStacks+=ColdSteelMelee::ItemModifiers(Off,this).MeleeHitBleedStacks;
        // The forged sword's opening applies bleed through blade contact only.
        const bool bForgedBladeContact=Shot.ItemDefinition!=TEXT("ue_forged_steel_greatsword")||
            (Shot.AttackForm==EMonsterAttackForm::Blade&&(Shot.AttackMeta&(0x40|0x80))==0);
        if(BleedStacks>0&&bForgedBladeContact)UCombatStatusFormula::GetOrAdd(Victim)->AddBleedingHit(Shooter,BleedStacks,Hit);
        // Read the phase after this contact's toughness damage, including a break just caused by this swing.
        if(bExecutionerContact&&(Combat->IsToughnessBroken()||FMath::FRand()<.5f))
            UCombatStatusFormula::GetOrAdd(Victim)->AddStun(1.f);
    }
    // One contact, one captured ammo effect. Armor reducing the direct damage
    // to zero does not cancel a hit; status immunity still rejects the effect.
    if(Combat&&Victim->HasAuthority()&&!Combat->IsDead())
    {
        if(Shot.AmmoBleedStacks>0)
            UCombatStatusFormula::GetOrAdd(Victim)->AddBleedingHit(Shooter,Shot.AmmoBleedStacks,Hit);
        if(Shot.AmmoPoisonStacks>0)
        {
            auto* Poison=Victim->FindComponentByClass<UMaggotPoisonComponent>();
            if(!Poison){Poison=NewObject<UMaggotPoisonComponent>(Victim);Victim->AddInstanceComponent(Poison);Poison->RegisterComponent();}
            for(int32 Stack=0;Stack<Shot.AmmoPoisonStacks;++Stack)Poison->AddStack(Shooter);
        }
    }
    if(bAliveBefore&&Applied>0.f&&Shot.TimeSandEchoRatio>0.f&&Shooter&&Shooter->HasAuthority()
        &&Shot.ItemDefinition==TEXT("ue_rune_sword")&&Shot.bMelee&&!Shot.bRicochet
        &&Shot.AttackForm==EMonsterAttackForm::Blade&&!(Shot.AttackMeta&0xC0)
        &&UFPSMeleeLightningComponent::IsEnemy(Victim,Shooter))
        if(auto* Echo=Shooter->FindComponentByClass<UTimeSandEchoComponent>())
            Echo->Queue(this,Hit,Shot,AppliedParts,Training.bCritical);
    if(Result)
    {
        Result->BeforeDefense=WeaponHit.Incoming;Result->AfterDefense=WeaponHit.Mitigated;
        Result->Applied=WeaponHit.bResolved?AppliedParts:FWeaponDamageParts::FromChannels(Applied,WeaponHit.Incoming.MagicPortion(Applied));
        Result->bResolved=WeaponHit.bResolved;Result->bCritical=Training.bCritical;
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
        if(!Training.SkillId.IsNone())
        {
            const int32 HitXP=Skill.HitExperience+Training.ExtraExperience+(Training.bCritical?Skill.CriticalExperience:0);
            Train(Skill,HitXP);
            if(ColdSteelSkills::IsTwoHandedSubMastery(Training.SkillId))Train(MasteryDefinition(TEXT("twoHandedMastery")),HitXP);
        }
        if(Training.bCritical)Train(CriticalStrikeSkill,CriticalStrikeSkill.CriticalHitExperience);
        if(Training.bMelee)Train(DexterousHandsSkill,DexterousHandsSkill.MeleeHitExperience);
        if(Training.bPerfectBowHit)Train(DexterousHandsSkill,DexterousHandsSkill.PerfectBowHitExperience);
        if(Training.bHeartPiercingArrow)
        {
            const auto& Piercing=MasteryDefinition(TEXT("heartPiercingArrow"));
            Train(Piercing,Piercing.HitExperience);
        }
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
        FColdSteelProgressNotice N; N.Title=FString::Printf(TEXT("角色升级   Lv.%d → %d"),Before.Level,After.Level);N.bUpgrade=true;
        N.Detail=FString::Printf(TEXT("获得 %d 点属性点 · 打开角色状态进行分配"),After.Points-Before.Points);
        ProgressNotices.Add(MoveTemp(N));
    }
    const FColdSteelSkillDefinition* NoticeDefinitions[]={&StormDomainSkill,&ThunderLanceSkill,&RifleSkill,&PistolSkill,&CriticalStrikeSkill,&FireballSkill,&IceSpikeSkill,&IceWallSkill,&BlizzardSkill,&LightningSkill,&HolyLightSkill,&MeteorSkill,&FlameArmorSkill,&IceArmorSkill,&LightningHasteSkill,&DragonBreathSkill,&DodgeSkill,&DexterousHandsSkill,&QuickCombatSkill,&MasteryDefinition(TEXT("twoHandedMastery")),&MasteryDefinition(TEXT("oneHandedMastery")),&MasteryDefinition(TEXT("swordMastery")),&MasteryDefinition(TEXT("bluntMastery")),&MasteryDefinition(TEXT("machineGunMastery")),&MasteryDefinition(TEXT("shotgunMastery")),&MasteryDefinition(TEXT("bowMastery")),&MasteryDefinition(TEXT("heartPiercingArrow")),&MasteryDefinition(TEXT("magicArrowRain")),&MasteryDefinition(TEXT("elementalArrow")),&MasteryDefinition(TEXT("illuminationArrow")),&MasteryDefinition(TEXT("heavyStrike")),&MasteryDefinition(TEXT("swordUppercut")),&MasteryDefinition(TEXT("chainSlash")),&MasteryDefinition(TEXT("leapStrike")),&MasteryDefinition(TEXT("shadowStepSlash")),&MasteryDefinition(TEXT("whirlwind")),&MasteryDefinition(TEXT("dashAttack"))};
    for(const auto* Definition:NoticeDefinitions)
    {
    const auto* Old=Before.Skills.Find(Definition->Id); const auto* New=After.Skills.Find(Definition->Id);
    if (Old && New && New->Level>Old->Level)
    {
        FColdSteelProgressNotice N; N.Title=FString::Printf(TEXT("%s升级   Lv.%d → %d"),*Definition->Name,Old->Level,New->Level);N.bUpgrade=true;
        N.Detail=ColdSteelSkills::EffectSummary(ColdSteelSkills::Effect(*Definition,New->Level)); N.Icon=Definition->Icon;
        if(Definition->Id==TEXT("illuminationArrow"))
        {
            const auto C=IlluminationArrowStats(New->Level);
            N.Detail=FString::Printf(TEXT("范围 %.1f m · 标记 %.1f s · 承伤 +%.1f%% · 冷却 %.1f s"),C.Radius/100.f,C.Duration,C.DamageBonus*100.f,C.Cooldown);
        }
        else if(Definition->Id==TEXT("elementalArrow"))
        {
            const auto& T=Definition->ElementalArrow;
            N.Detail=FString::Printf(TEXT("火焰 ×%.2f · 寒冰 ×%.2f · 闪电 ×%.2f"),
                ElementalArrow::DamageMultiplier(T,EArrowElement::Fire,New->Level),
                ElementalArrow::DamageMultiplier(T,EArrowElement::Ice,New->Level),
                ElementalArrow::DamageMultiplier(T,EArrowElement::Lightning,New->Level));
        }
        if(Definition->Id==TEXT("heartPiercingArrow"))
        {
            const auto C=HeartPiercingArrow::Evaluate(Definition->HeartPiercingArrow,New->Level);
            N.Detail=FString::Printf(TEXT("满拉伤害 ×%.2f · 目标穿透 +%d · 箭速 ×%.0f"),C.DamageMultiplier,C.TargetPenetration,C.SpeedMultiplier);
        }
        if(ColdSteelSkills::IsMeleeMastery(Definition->Id))
        {
            const auto E=ColdSteelSkills::Effect(*Definition,New->Level);
            const float Speed=(1.f/FMath::Max(.05f,1.f-E.CooldownReduction)-1.f)*100;
            if(Definition->Id==TEXT("oneHandedMastery"))
                N.Detail=FString::Printf(TEXT("单手伤害 +%.1f%% · 暴击率 +%.2f%% · 普攻速度 +%.1f%%"),E.DamagePercent*100,E.CriticalChance,Speed);
            else if(Definition->Id==TEXT("twoHandedMastery"))
                N.Detail=FString::Printf(TEXT("双手伤害 +%.1f%% · 普攻速度 +%.1f%%"),E.DamagePercent*100,Speed);
            else if(Definition->Id==TEXT("bluntMastery"))
                N.Detail=FString::Printf(TEXT("双手钝器伤害 +%.2f%% · 普攻速度 +%.1f%%"),E.DamagePercent*100,Speed);
            else
                N.Detail=FString::Printf(TEXT("%s固定伤害 +%.0f · 普攻速度 +%.1f%%"),*Definition->Name,E.FlatDamage,Speed);
        }
        if(Definition->Id==TEXT("swordUppercut")){const auto E=ColdSteelSkills::Effect(*Definition,New->Level);N.Detail=FString::Printf(TEXT("上挑 ×%.2f · 力量 +%d · 距离 ×%.3f"),SwordUppercut::HeavyDamageScale*E.HeavyMultiplier,E.Strength,E.UppercutReachMultiplier);}
        if(Definition->Id==TEXT("fireball"))N.Detail=FString::Printf(TEXT("火球威力提升 · 爆炸半径 %.2f 米"),FireballStats(New->Level).Radius/100);
        if(Definition->Id==TEXT("iceSpike"))N.Detail=FString::Printf(TEXT("冰锥威力提升 · 当前 %d 枚"),IceSpikeStats(New->Level).Count);
        if(Definition->Id==TEXT("lightningHaste")){const auto C=LightningHasteStats(New->Level);N.Detail=FString::Printf(TEXT("移速 +%.1f%% · 动作 +%.1f%% · 持续 %.1f 秒"),C.MoveBonus*100,C.ActionBonus*100,C.Duration);}
        if(Definition->Id==TEXT("iceArmor")){const auto C=IceArmorStats(New->Level);N.Detail=FString::Printf(TEXT("物防 +%.0f · 魔防 +%.0f · 持续 %.0f 秒"),C.PhysicalDefense,C.MagicDefense,C.Duration);}
        if(Definition->Id==TEXT("iceWall"))N.Detail=FString::Printf(TEXT("冰墙成长 · %d 段 · %.1f 秒"),IceWallStats(New->Level).Count,IceWallStats(New->Level).Duration);
        if(Definition->Id==TEXT("blizzard")){const auto C=BlizzardStats(New->Level);N.Detail=FString::Printf(TEXT("暴风雪成长 · 范围 %.2f × %.2f 米 · 持续 %.0f 秒"),C.RadiusX*.02f,C.RadiusY*.02f,C.Duration);}
        if(FireMagic::IsSkill(Definition->Id))N.Detail=FString::Printf(TEXT("火系魔法提升 · 持续 %.0f 秒"),FireMagicStats(Definition->Id,New->Level).Duration);
        if(Definition->Id==TEXT("dragonBreath")){const auto C=FireMagicStats(Definition->Id,New->Level);N.Detail=FString::Printf(TEXT("龙息成长 · 半径 %.2f 米 · 每跳 %.0f 伤害"),C.Radius/100,C.Damage);}
        if(Definition->Id==TEXT("holyLight"))N.Detail=TEXT("圣光伤害与治疗提升");
        if(ElectricMagic::IsSkill(Definition->Id))N.Detail=TEXT("电系魔法威力提升");
        if(Definition->Id==TEXT("lightningStrike"))N.Detail=FString::Printf(TEXT("闪电威力提升 · 最多传导 %d 个目标"),LightningStats(New->Level).Count);
        if(Definition->Id==TEXT("dashAttack"))N.Detail=FString::Printf(TEXT("冲刺攻击 ×%.2f · 准备 %.2f 秒"),DashAttackStats(New->Level).DamageMultiplier,DashAttackStats(New->Level).ReadySeconds);
        if(Definition->Id==TEXT("chainSlash")){const auto C=ChainSlashStats(New->Level);N.Detail=FString::Printf(TEXT("每段 %.1f%% · 冷却 %.1f s · 体力 %.1f"),C.DamageMultiplier*100.f,C.CooldownSeconds,C.StaminaCost);}
        if(Definition->Id==TEXT("leapStrike")){const auto C=LeapStrikeStats(New->Level);N.Detail=FString::Printf(TEXT("伤害 %.1f%% · 半径 %.1f m · 跳距 %.1f m"),C.DamageMultiplier*100.f,C.RadiusCM/100.f,C.ReachCM/100.f);}
        if(Definition->Id==TEXT("shadowStepSlash")){const auto C=ShadowStepStats(New->Level);N.Detail=FString::Printf(TEXT("一段 %.0f%% / 二段 %.0f%% · 突进 %.1f m · 冷却 %.1f s"),C.Stage1DamageMultiplier*100.f,C.Stage2DamageMultiplier*100.f,C.DashDistanceCM/100.f,C.CooldownSeconds);}
        if(Definition->Id==TEXT("whirlwind"))N.Detail=FString::Printf(TEXT("大旋风 ×%.1f · 力量 +%d"),WhirlwindStats(New->Level).DamageMultiplier,New->Level);
        if(Definition->Id==TEXT("quickCombat")){const auto C=QuickCombatStats(New->Level);N.Detail=FString::Printf(TEXT("快速打击 %.0f · 体力 %.2f"),C.Damage,C.StaminaCost);}
        ProgressNotices.Add(MoveTemp(N));
    }
    }
    QueueSkillTreeNotices(Before,After);
}
bool UColdSteelStatusModel::PopProgressNotice(FColdSteelProgressNotice& Out)
{ if (ProgressNotices.IsEmpty()) return false; Out=MoveTemp(ProgressNotices[0]); ProgressNotices.RemoveAt(0); return true; }
