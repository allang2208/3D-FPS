#include "ColdSteelSkillRules.h"
#include "../UI/ColdSteelStatusModel.h"
#include "FPSFireMagicComponent.h"
#include "../Combat/CoreCombatFormula.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../FPSGAMECharacter.h"
#include "Engine/GameInstance.h"
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
float UColdSteelStatusModel::DodgeStaminaCost() const
{ return StaminaTuning.DodgeCost*(1.f-DodgeEffect().DodgeCostReduction); }
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
    // 用户公式按「×技能等级」字面结算（1 级基础 30 伤 / 2.6 秒眩晕）；力量取当前总值。
    const auto& T=QuickCombatSkill.QuickCombat;
    const int32 L=FMath::Clamp(AtLevel<0?QuickCombatProgress().Level:AtLevel,1,QuickCombatSkill.MaxLevel);
    const float Strength=float(Attribute(TEXT("str")));
    const auto Mods=PreviewModifiers?*PreviewModifiers:ColdSteelMelee::EquippedModifiers(this);
    FQuickCombatCast C;
    C.DamageMultiplier=1.f+float(Mods.QuickCombatDamageAdd);
    C.Damage=(T.DamageBase+T.DamagePerLevel*L+Strength*(T.StrengthFactorBase+T.StrengthFactorPerLevel*L))*C.DamageMultiplier;
    C.StunSeconds=T.StunBase+T.StunPerLevel*L;
    C.KnockbackCM=T.KnockbackCM*float(Mods.QuickCombatKnockback);
    C.RangeCM=T.RangeCM;
    C.CooldownSeconds=T.Cooldown;
    return C;
}
bool UColdSteelStatusModel::TrainQuickCombat(int32 Amount)
{
    if(Amount<=0||QuickCombatProgress().Level>=QuickCombatSkill.MaxLevel)return false;
    SyncRuntime();auto P=Snapshot();ColdSteelSkills::AddExperience(P,QuickCombatSkill,Amount);return StageTraining(MoveTemp(P));
}
float UColdSteelStatusModel::QuickCombatCooldown() const
{ return HasNoAbilityCooldown() ? 0.f : Current.QuickCombatCooldown; }
bool UColdSteelStatusModel::CommitQuickCombatCast()
{
    // 动作实际开始时预留全额冷却；预留期间不走表，挥击结束才起跳（与火球/冰锥同合同）。
    if(Current.bQuickCombatReserved)return true;
    SyncRuntime();auto P=Snapshot();
    P.bQuickCombatReserved=true;
    P.QuickCombatCooldown=HasNoAbilityCooldown()?0.f:QuickCombatSkill.QuickCombat.Cooldown;
    P.QuickCombatCooldownDuration=P.QuickCombatCooldown;
    return CommitState(P);
}
void UColdSteelStatusModel::FinishQuickCombatCast()
{
    if(!Current.bQuickCombatReserved)return;
    // 冷却保留，只解除预留让走表开始；取消/死亡同样保留已提交的冷却。
    Current.bQuickCombatReserved=false;SyncRuntime();CommitState(Snapshot());
}
bool UColdSteelStatusModel::TriggerQuickCombat()
{
    // F/快捷栏统一入口：冷却中拒绝；**不限定武器类型**——按当前手里的武器选动作，
    // 三者共用同一套冷却/修炼/数值合同：
    //   剑类 → 符文剑配重锤；单持手枪 → 握把砸击；其余枪械 → 步枪枪托砸击。
    if(Current.bQuickCombatReserved || QuickCombatCooldown()>0)
    {
        UE_LOG(LogTemp,Log,TEXT("[QuickCombat] 冷却中（剩余 %.1f 秒），忽略触发"),QuickCombatCooldown());
        return false;
    }
    auto* Player=Cast<AFPSGAMECharacter>(UGameplayStatics::GetPlayerPawn(this,0));
    if(!Player)return false;
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
    AActor* Victim=Hit.GetActor(); const auto* Pawn=Cast<APawn>(Shooter);
    auto* Combat=Victim?Victim->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    FTrainingHit Training; Training.Victim=Victim;
    const FName Mastery=Shot.MasteryId.IsNone()?(Shot.bPistol?FName(TEXT("pistolMastery")):(Shot.bRifle?FName(TEXT("rifleMastery")):NAME_None)):Shot.MasteryId;
    const auto& Skill=MasteryDefinition(Mastery);
    Training.SkillId=Mastery;Training.ExtraExperience=Shot.ExtraMasteryExperience;Training.bMelee=Shot.bMelee;
    Training.bEligible=Combat && !Combat->IsDead() && !Victim->ActorHasTag(TEXT("Summoned")) && !Victim->ActorHasTag(TEXT("NoSkillTraining"));
    const bool Weakpoint=ColdSteelSkills::IsCriticalHit(Hit);
    Training.bCritical=Weakpoint||(Combat&&FMath::FRand()*100<CoreCombatFormula::CriticalChance(Shot.CriticalChance,CombatFormulaRuntime::MonsterCriticalResistance(Victim)));
    float Amount=Damage*(Shot.bRifle && Weakpoint?1+Shot.WeakpointPercent:1);
    if(Training.bCritical&&Shot.CriticalDamageBonus>0)Amount*=1+Shot.CriticalDamageBonus;
    TGuardValue<FTrainingHit*> HitScope(ActiveTrainingHit,&Training);
    CombatFormulaRuntime::WeaponHit WeaponHit;WeaponHit.Target=Victim;
    // Damage already contains this attack's heavy/combo/range multiplier. Apply
    // the same multiplier and shared critical roll to every panel component.
    WeaponHit.Incoming=Shot.DamagePanel.Total()>0?Shot.DamagePanel.Scaled(Amount/Shot.DamagePanel.Total()):FWeaponDamageParts{Amount,0,0,0};
    WeaponHit.PhysicalPenetration=Shot.ArmorPenetration;WeaponHit.MagicPenetration=Shot.MagicPenetration;
    TGuardValue<CombatFormulaRuntime::WeaponHit*> DamageScope(CombatFormulaRuntime::ActiveWeaponHit,&WeaponHit);
// 枪械默认不给怪物硬直：只有枪械目录显式声明 hit_stagger 的枪才关闭这道闸门。
    // 闸门关闭时受击端只记住攻击者，不动状态机、韧性时钟或受击表现。
    // 近战武器与手持枪械发动的近战打击（bMeleeStrike）不在闸门覆盖范围内：
    // 它们按原倍率进入受击端，否则削韧与硬直会被整段吞掉。
    bool bFirearmWithoutStagger=false;
    const FString WeaponDefinition=Shot.ItemDefinition.IsEmpty()?(Equipped()?Equipped()->Definition:FString()):Shot.ItemDefinition;
    if(!Shot.bMelee&&!Shot.bMeleeStrike&&!WeaponDefinition.IsEmpty())
        if(auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>())
            if(const auto* W=G->Weapon(WeaponDefinition))bFirearmWithoutStagger=!W->bHitStagger;
    auto ApplyDamage=[&](){ return UGameplayStatics::ApplyPointDamage(Victim,Amount,Direction,Hit,
        Pawn?Pawn->GetController():nullptr,Shooter,nullptr); };
    // 命中形式的唯一收口：所有武器命中都在这里标注，受击端据此折算削韧。
    const MonsterToughness::FScopedForm FormScope(Shot.AttackForm);
    auto ApplyToughness=[&](){return Combat?Combat->ApplyHitWithToughnessScale(Shot.ToughnessDamageMultiplier,ApplyDamage):ApplyDamage();};
    const float Applied=(Combat&&bFirearmWithoutStagger)?Combat->ApplyHitWithReactionScale(0.f,ApplyToughness):ApplyToughness();
    if(Result)
    {
        Result->BeforeDefense=WeaponHit.Incoming;Result->AfterDefense=WeaponHit.Mitigated;
        Result->Applied=WeaponHit.Mitigated.LimitedTo(Applied);Result->bResolved=WeaponHit.bResolved;Result->bCritical=Training.bCritical;
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
    const FColdSteelSkillDefinition* NoticeDefinitions[]={&RifleSkill,&PistolSkill,&CriticalStrikeSkill,&FireballSkill,&IceSpikeSkill,&LightningSkill,&HolyLightSkill,&MeteorSkill,&FlameArmorSkill,&DodgeSkill,&DexterousHandsSkill,&QuickCombatSkill,&MasteryDefinition(TEXT("swordMastery")),&MasteryDefinition(TEXT("machineGunMastery")),&MasteryDefinition(TEXT("shotgunMastery")),&MasteryDefinition(TEXT("bowMastery")),&MasteryDefinition(TEXT("heavyStrike")),&MasteryDefinition(TEXT("whirlwind")),&MasteryDefinition(TEXT("dashAttack"))};
    for(const auto* Definition:NoticeDefinitions)
    {
    const auto* Old=Before.Skills.Find(Definition->Id); const auto* New=After.Skills.Find(Definition->Id);
    if (Old && New && New->Level>Old->Level)
    {
        FColdSteelProgressNotice N; N.Title=FString::Printf(TEXT("%s升级   Lv.%d → %d"),*Definition->Name,Old->Level,New->Level);
        N.Detail=ColdSteelSkills::EffectSummary(ColdSteelSkills::Effect(*Definition,New->Level)); N.Icon=Definition->Icon;
        if(Definition->Id==TEXT("fireball"))N.Detail=FString::Printf(TEXT("火球威力提升 · 爆炸半径 %.2f 米"),FireballStats(New->Level).Radius/100);
        if(Definition->Id==TEXT("iceSpike"))N.Detail=FString::Printf(TEXT("冰锥威力提升 · 当前 %d 枚"),IceSpikeStats(New->Level).Count);
        if(FireMagic::IsSkill(Definition->Id))N.Detail=FString::Printf(TEXT("火系魔法提升 · 持续 %.0f 秒"),FireMagicStats(Definition->Id,New->Level).Duration);
        if(Definition->Id==TEXT("holyLight"))N.Detail=TEXT("圣光伤害与治疗提升");
        if(Definition->Id==TEXT("lightningStrike"))N.Detail=FString::Printf(TEXT("闪电威力提升 · 最多传导 %d 个目标"),LightningStats(New->Level).Count);
        if(Definition->Id==TEXT("dashAttack"))N.Detail=FString::Printf(TEXT("冲刺攻击 ×%.2f · 准备 %.2f 秒"),DashAttackStats(New->Level).DamageMultiplier,DashAttackStats(New->Level).ReadySeconds);
        if(Definition->Id==TEXT("whirlwind"))N.Detail=FString::Printf(TEXT("大旋风 ×%.1f · 力量 +%d"),WhirlwindStats(New->Level).DamageMultiplier,New->Level);
        if(Definition->Id==TEXT("quickCombat"))N.Detail=FString::Printf(TEXT("配重锤打击 %.0f · 眩晕 %.1f 秒"),QuickCombatStats(New->Level).Damage,QuickCombatStats(New->Level).StunSeconds);
        ProgressNotices.Add(MoveTemp(N));
    }
    }
}
bool UColdSteelStatusModel::PopProgressNotice(FColdSteelProgressNotice& Out)
{ if (ProgressNotices.IsEmpty()) return false; Out=MoveTemp(ProgressNotices[0]); ProgressNotices.RemoveAt(0); return true; }
