#include "ColdSteelSkillRules.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Engine/GameInstance.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"

FColdSteelSkillDefinition ColdSteelSkills::LoadDefinition(FName Id)
{
    FColdSteelSkillDefinition D;D.Id=Id;
    if(Id==TEXT("dodge")){D.Name=TEXT("闪避");D.Description=TEXT("短按左 Shift 后松开，朝输入方向快速闪避；无输入时沿朝向。动作期间无敌。");D.Icon=TEXT("Skills/dodge_cold_steel.png");}
    if(Id==TEXT("dexterousHands")){D.Name=TEXT("巧手");D.Description=TEXT("灵巧的双手带来更高敏捷与更快换弹。完成换弹即可修炼，被动效果常驻。");D.Icon=TEXT("Skills/dexterous_hands.png");}
    if(Id==TEXT("pistolMastery")){D.Name=TEXT("手枪精通");D.Description=TEXT("精通手枪的快速射击，在移动中也能精准命中。");D.Icon=TEXT("Skills/pistol_mastery_cold_steel.png");}
    if(Id==TEXT("criticalStrike")){D.Name=TEXT("暴击");D.Description=TEXT("精通暴击之道，每次暴击都能造成更致命的打击。");D.Icon=TEXT("Skills/critical_strike_cold_steel.png");}
    if(Id==TEXT("fireball")){D.Name=TEXT("火球");D.Description=TEXT("按绑定键凝聚火球，再次按键朝准星发射。直击要害必定暴击，普通直击与爆炸波及目标各自随机判定暴击。");D.Icon=TEXT("Skills/fireball_ember_red.png");D.KillExperience=24;}
    if(Id==TEXT("quickCombat")){D.Name=TEXT("快速进战");D.Description=TEXT("按 F 快速进入战斗姿态。占位技能：正式效果与成长待定义。");D.Icon=TEXT("Skills/quick_combat_placeholder.png");}
    FString Json; TSharedPtr<FJsonObject> Root;
    if (!FFileHelper::LoadFileToString(Json, *(FPaths::ProjectContentDir()/TEXT("ColdSteelData/skills.json"))) ||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root) return D;
    const TSharedPtr<FJsonObject>* Entry = nullptr;
    if (!Root->TryGetObjectField(Id.ToString(), Entry)) return D;
    const auto& O = *Entry;
    O->TryGetStringField(TEXT("name"), D.Name); O->TryGetStringField(TEXT("description"), D.Description);
    O->TryGetStringField(TEXT("icon"), D.Icon); O->TryGetStringField(TEXT("upgradeSound"), D.UpgradeSound);
    auto Num = [&](const TCHAR* Key, double Default) { double Value=Default; O->TryGetNumberField(Key,Value); return FMath::IsFinite(Value)?Value:Default; };
    D.HeavyMultiplierBase=Num(TEXT("heavyMultiplierBase"),2.5);D.HeavyMultiplierPerLevel=Num(TEXT("heavyMultiplierPerLevel"),.1);
    D.HeavyChargeBase=Num(TEXT("heavyChargeBase"),2);D.HeavyChargeReductionPerLevel=Num(TEXT("heavyChargeReductionPerLevel"),.05);
    D.HeavyHit2Experience=Num(TEXT("heavyHit2Experience"),5);D.HeavyKill2Experience=Num(TEXT("heavyKill2Experience"),12);
    D.HeavyHit5Experience=Num(TEXT("heavyHit5Experience"),25);D.HeavyKill5Experience=Num(TEXT("heavyKill5Experience"),60);
    D.StrengthPerLevel=Num(TEXT("strengthPerLevel"),0);D.ConstitutionPerLevel=Num(TEXT("constitutionPerLevel"),0);
    D.HitExperience=Num(TEXT("hitExperience"),0);D.MultiHitExperience=Num(TEXT("multiHitExperience"),0);
    D.CooldownReductionPerLevel=Num(TEXT("cooldownReductionPerLevel"),0);D.SpreadDelayPerLevel=Num(TEXT("spreadDelayPerLevel"),0);D.KnockbackPerLevel=Num(TEXT("knockbackPerLevel"),0);
    // Version 1's save contract fixes the level cap; tuning accepts positive, bounded coefficients.
    D.ExperiencePerLevel = FMath::Clamp(int32(Num(TEXT("experiencePerLevel"),100)),1,100000);
    D.KillExperience = FMath::Clamp(int32(Num(TEXT("killExperience"),D.KillExperience)),0,10000);
    D.CriticalExperience = FMath::Clamp(int32(Num(TEXT("criticalExperience"),5)),0,10000);
    D.DamagePercentPerLevel = FMath::Clamp(Num(TEXT("damagePercentPerLevel"),.01),0.,1.);
    D.FlatDamagePerLevel = FMath::Clamp(Num(TEXT("flatDamagePerLevel"),1),0.,100.);
    D.WeakpointPerLevel = FMath::Clamp(Num(TEXT("weakpointPercentPerLevel"),.01),0.,1.);
    D.WisdomPerLevel = FMath::Clamp(int32(Num(TEXT("wisdomPerLevel"),1)),0,100);
    D.DodgeDistanceCMPerLevel=FMath::Clamp(float(Num(TEXT("distanceCMPerLevel"),10)),0.f,100.f);
    D.DodgeCostReductionPerLevel=FMath::Clamp(float(Num(TEXT("costReductionPerLevel"),.015)),0.f,.045f);
    D.UseExperience=FMath::Clamp(int32(Num(TEXT("useExperience"),1)),0,10000);
    D.MeleeDodgeExperience=FMath::Clamp(int32(Num(TEXT("meleeDodgeExperience"),5)),0,10000);
    D.RangedDodgeExperience=FMath::Clamp(int32(Num(TEXT("rangedDodgeExperience"),10)),0,10000);
    D.DexterityPerLevel=FMath::Clamp(int32(Num(TEXT("dexterityPerLevel"),1)),0,100);
    D.ReloadSpeedPerLevel=FMath::Clamp(float(Num(TEXT("reloadSpeedPerLevel"),.01)),0.f,1.f);
    D.ReloadExperience=FMath::Clamp(int32(Num(TEXT("reloadExperience"),5)),0,10000);
    D.MoveSpeedPerLevel=FMath::Clamp(float(Num(TEXT("moveSpeedPerLevel"),.01)),0.f,1.f);
    D.CriticalDamageBase=FMath::Clamp(float(Num(TEXT("criticalDamageBase"),.50)),0.f,5.f);
    D.CriticalDamagePerLevel=FMath::Clamp(float(Num(TEXT("criticalDamagePerLevel"),.05)),0.f,1.f);
    D.LuckPerLevel=FMath::Clamp(int32(Num(TEXT("luckPerLevel"),1)),0,100);
    D.CriticalHitExperience=FMath::Clamp(int32(Num(TEXT("criticalHitExperience"),1)),0,10000);
    D.CriticalKillExperience=FMath::Clamp(int32(Num(TEXT("criticalKillExperience"),10)),0,10000);
    if(Id==TEXT("fireball"))
    {
        auto& F=D.Fireball;
        F.MagicBase=FMath::Clamp(float(Num(TEXT("magicBase"),8.5)),0.0f,100.0f);
        F.MagicPerLevel=FMath::Clamp(float(Num(TEXT("magicPerLevel"),0.5)),0.0f,100.0f);
        F.UnitsToCM=FMath::Clamp(float(Num(TEXT("unitsToCM"),1.5)),0.1f,10.0f);
        F.RadiusBase=FMath::Clamp(float(Num(TEXT("radiusBase"),80)),1.0f,1000.0f);
        F.RadiusPerLevel=FMath::Clamp(float(Num(TEXT("radiusPerLevel"),5)),0.0f,100.0f);
        F.RadiusScale=FMath::Clamp(float(Num(TEXT("radiusScale"),1.65)),0.1f,10.0f);
        F.Speed=FMath::Clamp(float(Num(TEXT("flySpeed"),1600)),100.0f,10000.0f);
        F.Range=FMath::Clamp(float(Num(TEXT("maxRange"),1200)),100.0f,10000.0f);
        F.Gravity=FMath::Clamp(float(Num(TEXT("gravity"),400)),0.0f,5000.0f);
        F.ManaCost=FMath::Clamp(float(Num(TEXT("manaCost"),50)),0.0f,10000.0f);
        F.ManaCostPerLevel=FMath::Clamp(float(Num(TEXT("manaCostPerLevel"),2)),0.0f,1000.0f);
        F.Cooldown=FMath::Clamp(float(Num(TEXT("cooldown"),12)),0.1f,300.0f);
        F.MinimumCooldown=FMath::Clamp(float(Num(TEXT("minimumCooldown"),8)),0.1f,F.Cooldown);
        F.HoverDuration=FMath::Clamp(float(Num(TEXT("hoverDuration"),30)),1.0f,120.0f);
        F.HitExperience=FMath::Clamp(int32(Num(TEXT("hitExperience"),8)),0,10000);
        F.MultiHitExperience=FMath::Clamp(int32(Num(TEXT("multiHitExperience"),20)),0,10000);
        F.MultiKillExperience=FMath::Clamp(int32(Num(TEXT("multiKillExperience"),20)),0,10000);
    }
    if(Id==TEXT("iceSpike"))
    {
        auto& F=D.IceSpike;
        // Same shape as the fireball: magic attack only, no independent intelligence term.
        F.DamageBase=Num(TEXT("damageBase"),21);F.DamagePerLevel=Num(TEXT("damagePerLevel"),3.5);
        F.MagicBase=Num(TEXT("magicBase"),1.4);F.MagicPerLevel=Num(TEXT("magicPerLevel"),.2917);
        F.CountBase=Num(TEXT("countBase"),2);F.CountLevelStep=FMath::Max(1,int32(Num(TEXT("countLevelStep"),5)));
        F.Cooldown=Num(TEXT("cooldown"),12);F.MinimumCooldown=Num(TEXT("minimumCooldown"),8);
        F.ManaCost=Num(TEXT("manaCost"),30);F.ManaCostPerLevel=Num(TEXT("manaCostPerLevel"),2);
        F.HoverDuration=Num(TEXT("hoverDuration"),30);F.Speed=Num(TEXT("flySpeed"),1600);
        F.Range=Num(TEXT("maxRange"),800);F.UnitsToCM=Num(TEXT("unitsToCM"),1.5);
        F.Gravity=FMath::Clamp(float(Num(TEXT("gravity"),400)),0.f,5000.f);
        F.HitExperience=Num(TEXT("hitExperience"),4);F.KillExperience=Num(TEXT("killExperience"),12);
        F.MultiHitExperience=Num(TEXT("multiHitExperience"),10);F.MultiKillExperience=Num(TEXT("multiKillExperience"),10);
    }
    if(Id==TEXT("quickCombat"))
    {
        auto& Q=D.QuickCombat;
        Q.DamageBase=Num(TEXT("damageBase"),25);Q.DamagePerLevel=Num(TEXT("damagePerLevel"),5);
        Q.StrengthFactorBase=Num(TEXT("strengthFactorBase"),5);Q.StrengthFactorPerLevel=Num(TEXT("strengthFactorPerLevel"),.1);
        Q.KnockbackCM=FMath::Clamp(float(Num(TEXT("knockbackCM"),100)),0.f,1000.f);
        Q.RangeCM=FMath::Clamp(float(Num(TEXT("rangeCM"),200)),50.f,1000.f);
        Q.StunBase=Num(TEXT("stunBase"),2.5);Q.StunPerLevel=Num(TEXT("stunPerLevel"),.1);
        Q.Cooldown=FMath::Clamp(float(Num(TEXT("cooldown"),12)),0.f,300.f);
    }
    return D;
}
bool ColdSteelSkills::Migrate(FColdSteelProfile& P)
{
    if (P.SkillProgressVersion >= 11) return false;
    if (P.SkillProgressVersion < 8)
    {
        P.Skills.FindOrAdd(TEXT("rifleMastery"));P.Skills.FindOrAdd(TEXT("dodge"));P.Skills.FindOrAdd(TEXT("dexterousHands"));P.Skills.FindOrAdd(TEXT("pistolMastery"));P.Skills.FindOrAdd(TEXT("criticalStrike"));P.Skills.FindOrAdd(TEXT("fireball"));for(FName Id:{FName(TEXT("swordMastery")),FName(TEXT("machineGunMastery")),FName(TEXT("shotgunMastery")),FName(TEXT("bowMastery"))})P.Skills.FindOrAdd(Id);P.Skills.FindOrAdd(TEXT("heavyStrike"));
    }
    if(P.SkillProgressVersion<9)
    {
    P.FireballCooldownDuration=0.f;
    if (P.FireballCooldown>0.f)
    {
        // Legacy saves have no cast-time level/equipment snapshot. Estimate once
        // from the saved level, preserving the actual remaining cooldown exactly.
        const auto Definition=LoadDefinition(TEXT("fireball"));
        const auto* Progress=P.Skills.Find(TEXT("fireball"));
        const int32 L=FMath::Clamp(Progress?Progress->Level:1,1,Definition.MaxLevel);
        const float Growth=float(L-1)/FMath::Max(1,Definition.MaxLevel-1);
        const float Estimated=FMath::Lerp(Definition.Fireball.Cooldown,Definition.Fireball.MinimumCooldown,Growth);
        P.FireballCooldownDuration=FMath::Max(P.FireballCooldown,Estimated);
    }
    }
    P.Skills.FindOrAdd(TEXT("iceSpike"));
    // Version 11 adds quickCombat; the early return above means only <11 reaches here.
    P.Skills.FindOrAdd(TEXT("quickCombat"));
    P.SkillProgressVersion=11;
    return true;
}
bool ColdSteelSkills::Validate(const FColdSteelProfile& P, FString& Reason)
{
    if (P.SkillProgressVersion<0 || P.SkillProgressVersion>11 || P.Skills.Num()>128) { Reason=TEXT("技能存档版本或数量无效"); return false; }
    if (P.SkillProgressVersion>=1 && !P.Skills.Contains(TEXT("rifleMastery"))) { Reason=TEXT("技能进度缺失"); return false; }
    if (P.SkillProgressVersion>=2 && !P.Skills.Contains(TEXT("dodge"))) { Reason=TEXT("闪避进度缺失"); return false; }
    if (P.SkillProgressVersion>=3 && !P.Skills.Contains(TEXT("dexterousHands"))) { Reason=TEXT("巧手进度缺失"); return false; }
    if (P.SkillProgressVersion>=4 && !P.Skills.Contains(TEXT("pistolMastery"))) { Reason=TEXT("手枪精通进度缺失"); return false; }
    if (P.SkillProgressVersion>=5 && !P.Skills.Contains(TEXT("criticalStrike"))) { Reason=TEXT("暴击进度缺失"); return false; }
    if (P.SkillProgressVersion>=6 && (!P.Skills.Contains(TEXT("fireball")) || !FMath::IsFinite(P.FireballCooldown) || P.FireballCooldown<0 || P.FireballCooldown>300)) { Reason=TEXT("火球进度或冷却无效"); return false; }
    if(P.SkillProgressVersion>=8&&!P.Skills.Contains(TEXT("heavyStrike"))){Reason=TEXT("重击进度缺失");return false;}
    if(P.SkillProgressVersion>=9&&(!FMath::IsFinite(P.FireballCooldownDuration)||P.FireballCooldownDuration<P.FireballCooldown||P.FireballCooldownDuration>300)){Reason=TEXT("火球冷却总时长无效");return false;}
    if(P.SkillProgressVersion>=10&&(!P.Skills.Contains(TEXT("iceSpike"))||!FMath::IsFinite(P.IceSpikeCooldown)||P.IceSpikeCooldown<0||!FMath::IsFinite(P.IceSpikeCooldownDuration)||P.IceSpikeCooldownDuration<P.IceSpikeCooldown||P.IceSpikeCooldownDuration>300)){Reason=TEXT("冰锥进度或冷却无效");return false;}
    if(P.SkillProgressVersion>=11&&!P.Skills.Contains(TEXT("quickCombat"))){Reason=TEXT("快速进战进度缺失");return false;}
    if(P.SkillProgressVersion>=11&&(!FMath::IsFinite(P.QuickCombatCooldown)||P.QuickCombatCooldown<0||!FMath::IsFinite(P.QuickCombatCooldownDuration)||P.QuickCombatCooldownDuration<P.QuickCombatCooldown||P.QuickCombatCooldownDuration>300)){Reason=TEXT("快速进战冷却无效");return false;}
    for (const auto& Pair:P.Skills)
        if (Pair.Key.IsNone() || Pair.Value.Level<1 || Pair.Value.Level>20 || Pair.Value.Experience<0 || Pair.Value.Experience>2000000 || (Pair.Value.Level==20 && Pair.Value.Experience!=0))
        { Reason=TEXT("技能等级或修炼值无效"); return false; }
    return true;
}
bool ColdSteelSkills::IsRifle(const FColdSteelItem* I)
{ return I && ColdSteelInventory::Text(*I,TEXT("weaponType"))==TEXT("rifle"); }
bool ColdSteelSkills::IsPistol(const FColdSteelItem* I)
{ return I && ColdSteelInventory::Text(*I,TEXT("weaponType"))==TEXT("pistol"); }
bool ColdSteelSkills::IsCriticalHit(const FHitResult& Hit)
{ const FString Bone=Hit.BoneName.ToString();return Bone.Contains(TEXT("head"),ESearchCase::IgnoreCase)||Bone.Equals(TEXT("cranium"),ESearchCase::IgnoreCase); }
FColdSteelSkillEffect ColdSteelSkills::Effect(const FColdSteelSkillDefinition& D, int32 Level)
{
    const int32 L=FMath::Clamp(Level,0,D.MaxLevel);
    if(D.Id==TEXT("heavyStrike")){FColdSteelSkillEffect E;E.Strength=L*D.StrengthPerLevel;E.HeavyMultiplier=D.HeavyMultiplierBase+FMath::Max(0,L-1)*D.HeavyMultiplierPerLevel;E.HeavyChargeSeconds=FMath::Max(.1f,D.HeavyChargeBase-FMath::Max(0,L-1)*D.HeavyChargeReductionPerLevel);return E;}
    if(D.Id==TEXT("swordMastery")||D.Id==TEXT("machineGunMastery")||D.Id==TEXT("shotgunMastery")||D.Id==TEXT("bowMastery"))
    {FColdSteelSkillEffect E;E.Strength=L*D.StrengthPerLevel;E.Constitution=L*D.ConstitutionPerLevel;E.Dexterity=L*D.DexterityPerLevel;E.DamagePercent=L*D.DamagePercentPerLevel;E.FlatDamage=L*D.FlatDamagePerLevel;E.CooldownReduction=L*D.CooldownReductionPerLevel;E.SpreadDelay=L*D.SpreadDelayPerLevel;E.Knockback=L*D.KnockbackPerLevel;return E;}
    if(D.Id==TEXT("criticalStrike")){FColdSteelSkillEffect E;E.CriticalDamageBonus=L>0?D.CriticalDamageBase+L*D.CriticalDamagePerLevel:0.f;E.Luck=L*D.LuckPerLevel;return E;}
    if(D.Id==TEXT("dodge")){FColdSteelSkillEffect E;E.DodgeDistanceCM=L*D.DodgeDistanceCMPerLevel;E.DodgeCostReduction=L*D.DodgeCostReductionPerLevel;return E;}
    // 占位技能：正式效果定义前保持零收益，避免落入步枪精通的通用档。
    if(D.Id==TEXT("quickCombat")){FColdSteelSkillEffect E;return E;}
    if(D.Id==TEXT("dexterousHands")){FColdSteelSkillEffect E;E.Dexterity=L*D.DexterityPerLevel;E.ReloadSpeed=L*D.ReloadSpeedPerLevel;return E;}
    if(D.Id==TEXT("pistolMastery")){FColdSteelSkillEffect E;E.Dexterity=L*D.DexterityPerLevel;E.DamagePercent=L*D.DamagePercentPerLevel;E.FlatDamage=L*D.FlatDamagePerLevel;E.MoveSpeed=L*D.MoveSpeedPerLevel;return E;}
    FColdSteelSkillEffect E; E.DamagePercent=L*D.DamagePercentPerLevel; E.FlatDamage=L*D.FlatDamagePerLevel;
    E.WeakpointPercent=L*D.WeakpointPerLevel; E.Wisdom=L*D.WisdomPerLevel; return E;
}
int32 ColdSteelSkills::ExperienceRequired(const FColdSteelSkillDefinition& D, int32 L)
{ return L>=D.MaxLevel?0:FMath::Max(1,L)*D.ExperiencePerLevel; }
void ColdSteelSkills::AddExperience(FColdSteelProfile& P, const FColdSteelSkillDefinition& D, int32 Amount)
{
    auto* Progress=P.Skills.Find(D.Id);
    if (!Progress || Amount<=0 || Progress->Level>=D.MaxLevel) return;
    Progress->Experience+=Amount;
    while (Progress->Level<D.MaxLevel)
    {
        const int32 Need=ExperienceRequired(D,Progress->Level); if (Progress->Experience<Need) break;
        Progress->Experience-=Need; ++Progress->Level;
    }
    if (Progress->Level==D.MaxLevel) Progress->Experience=0;
}
FString ColdSteelSkills::EffectSummary(const FColdSteelSkillEffect& E)
{ if(E.HeavyMultiplier>0)return FString::Printf(TEXT("重击 ×%.1f · 蓄力 %.2f 秒 · 力量 +%d"),E.HeavyMultiplier,E.HeavyChargeSeconds,E.Strength);
if(E.CriticalDamageBonus>0||E.Luck>0)return FString::Printf(TEXT("暴击伤害 +%.0f%%   ·   幸运 +%d"),E.CriticalDamageBonus*100,E.Luck);
if(E.DodgeDistanceCM>0||E.DodgeCostReduction>0)return FString::Printf(TEXT("闪避距离 +%.1f 米   ·   体力消耗 −%.1f%%"),E.DodgeDistanceCM/100,E.DodgeCostReduction*100);
if(E.MoveSpeed>0)return FString::Printf(TEXT("手枪伤害 +%.0f%% / +%.0f   ·   敏捷 +%d   ·   持枪移速 +%.0f%%"),E.DamagePercent*100,E.FlatDamage,E.Dexterity,E.MoveSpeed*100);
if(E.CooldownReduction>0||E.Strength>0||E.Constitution>0)return FString::Printf(TEXT("伤害 +%.0f%% / +%.0f · 属性 +%d · 间隔 −%.0f%%"),E.DamagePercent*100,E.FlatDamage,E.Strength+E.Constitution+E.Dexterity,E.CooldownReduction*100);
if(E.Dexterity>0||E.ReloadSpeed>0)return FString::Printf(TEXT("敏捷 +%d   ·   换弹速度 +%.0f%%"),E.Dexterity,E.ReloadSpeed*100);
return FString::Printf(TEXT("步枪伤害 +%.0f%% / +%.0f   ·   精神 +%d   ·   要害伤害 +%.0f%%"),E.DamagePercent*100,E.FlatDamage,E.Wisdom,E.WeakpointPercent*100); }
FColdSteelSkillShot ColdSteelSkills::Snapshot(AActor* Shooter,const FColdSteelItem* Item)
{
    FColdSteelSkillShot Shot;
    if(const FColdSteelItem* Source=Item?Item:nullptr)Shot.ItemDefinition=Source->Definition;
    if (Shooter && Shooter->GetGameInstance()) if (auto* M=Shooter->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
    { Shot.bRifle=IsRifle(Item?Item:M->Equipped());Shot.bPistol=IsPistol(Item?Item:M->Equipped()); Shot.WeakpointPercent=Shot.bRifle?M->RifleEffect().WeakpointPercent:0;Shot.CriticalDamageBonus=M->CriticalStrikeEffect().CriticalDamageBonus; }
    if(Shooter&&Shooter->GetGameInstance())if(auto* M=Shooter->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
    {
        Shot.CriticalChance=M->Derived(TEXT("crit"));Shot.MasteryId=M->WeaponMastery(Item?Item:M->Equipped());
        if(const auto* I=Item?Item:M->Equipped())if(auto* E=Shooter->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {
            Shot.CriticalChance+=100*E->Effect(*I,TEXT("critRate"));
            Shot.ArmorPenetration=E->CraftEffect(*I,TEXT("armorPenetrationPercent"))+E->Effect(*I,TEXT("armorPenetrationPercent"));
            Shot.MagicPenetration=E->CraftEffect(*I,TEXT("magicPenetrationPercent"))+E->Effect(*I,TEXT("magicPenetrationPercent"));
        }
        if(const auto* I=Item?Item:M->Equipped())
        {
            if(Shot.ItemDefinition.IsEmpty())Shot.ItemDefinition=I->Definition;
            if(ColdSteelInventory::IsMeleeWeapon(*I))Shot.DamagePanel=ColdSteelMelee::Evaluate(*I,M).DamageParts;
            else if(const auto* G=Shooter->GetGameInstance()->GetSubsystem<UGunsmithSystem>();G&&G->Weapon(I->Definition))
                Shot.DamagePanel=ColdSteelWeaponStats::DamageParts(*I,M,G->Calculate(I->Definition,G->Installed(*I)).Damage);
        }
    }
    return Shot;
}
float ColdSteelSkills::ApplyHit(AActor* Shooter,const FHitResult& Hit,float Damage,const FVector& Direction,const FColdSteelSkillShot& Shot,FWeaponDamageResult* Result)
{
    if(Result)*Result={};
    if (Shooter && Shooter->GetGameInstance()) if (auto* M=Shooter->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        return M->ApplySkillWeaponHit(Shooter,Hit,Damage,Direction,Shot,Result);
    const auto* Pawn=Cast<APawn>(Shooter);
    return UGameplayStatics::ApplyPointDamage(Hit.GetActor(),Damage,Direction,Hit,Pawn?Pawn->GetController():nullptr,Shooter,nullptr);
}
