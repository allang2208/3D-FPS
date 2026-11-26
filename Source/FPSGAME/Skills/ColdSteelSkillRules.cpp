#include "ColdSteelSkillRules.h"
#include "../Combat/CombatChill.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

FColdSteelSkillDefinition ColdSteelSkills::LoadDefinition(FName Id)
{
    FColdSteelSkillDefinition D;D.Id=Id;
    if(Id==TEXT("illuminationArrow"))
    {
        D.Name=TEXT("照明箭");D.Icon=TEXT("Skills/illumination_arrow_cold_steel.png");D.MaxLevel=20;
        D.ExperiencePerLevel=300;D.KillExperience=12;D.HitExperience=0;D.CriticalExperience=0;
        D.Description=TEXT("弓限定主动技能。搭箭后正常拉弓射击，伤害按普通箭计算；沿途扫描标记敌人，直击标记时间翻倍并留下持续照明。红色轮廓高亮、破除螳螂隐身并加深承伤，兼容节拍与穿心箭。");
    }
    if(Id==TEXT("elementalArrow"))
    {
        D.Name=TEXT("元素箭");D.Icon=TEXT("Skills/elemental_arrow_fire.png");D.MaxLevel=20;
        D.ExperiencePerLevel=300;D.HitExperience=4;D.KillExperience=10;D.MultiHitExperience=6;
        D.Description=TEXT("弓限定主动技能，独立修炼至20级。短按搭箭，长按切换火焰／寒冰／闪电；左键拉弓、松手射击，兼容完美节拍与穿心箭。元素箭等级提升原魔法的伤害调用倍率，原魔法等级和当前属性继续影响伤害。持续拉弓消耗体力与魔法；射出蓝耗按元素箭倍率提高，冷却与对应魔法共用。");
    }
    if(Id==TEXT("magicArrowRain"))
    {
        D.Name=TEXT("魔法箭雨");D.Icon=TEXT("Skills/magic_arrow_rain_cold_steel.png");
        D.Description=TEXT("弓限定主动魔法，以敏捷为主、智力为辅。激活后搭上绿色附魔箭，长按左键拉弓并以镜头选择地面范围；满蓄后松手，引导箭在上方空爆并降下一次密集箭雨。保持拉弓持续耗体耗蓝，耗尽收弓，不会自动射出。");
        D.ExperiencePerLevel=300;D.HitExperience=4;D.KillExperience=10;D.MultiHitExperience=6;
    }
    if(Id==TEXT("heartPiercingArrow"))
    {
        D.Name=TEXT("穿心箭");D.Icon=TEXT("Skills/heart_piercing_arrow_cold_steel.png");
        D.Description=TEXT("弓限定被动战技。连续拉弓超过 3 秒且满拉后，红色脉冲提示穿心箭就绪，松手射出高伤害、双倍箭速并可贯穿多个目标的箭矢。拉弓持续耗体，耗尽收弓，不自动射箭。");
        D.ExperiencePerLevel=300;D.HitExperience=4;D.KillExperience=10;D.CriticalExperience=0;
    }
    if(ElectricMagic::IsSkill(Id))
    {
        const bool bLance=Id==TEXT("thunderLance");
        if(!bLance)D.ElectricMagic.bRequiresStaff=true;
        D.Name=bLance?TEXT("贯穿雷枪"):TEXT("雷暴领域");
        D.Icon=bLance?TEXT("Skills/thunder_lance_cold_steel.png"):TEXT("Skills/storm_domain_cold_steel.png");
        D.Description=bLance?TEXT("长按绑定键充能，松键发射贯穿雷枪；未满充在收拢准星内散射，100%充能合并为点并保持待释放。"):TEXT("雷云跟随玩家，每0.9秒自动落雷、传导并叠加感电。");
        if(bLance){auto& T=D.ElectricMagic;T.DamageBase=110;T.DamagePerLevel=14;T.MagicBase=1.8f;T.MagicPerLevel=.26f;T.IntelligenceBase=2;T.IntelligencePerLevel=.30f;T.ManaBase=120;T.ManaGrowth=35;T.Cooldown=32;T.CooldownReduction=4;T.RangeBase=900;T.RangePerLevel=15;T.ElectrifyStacks=2;T.ElectrifySeconds=5;T.StunSeconds=0;T.HitExperience=2;T.KillExperience=10;T.MultiHitExperience=8;T.MultiKillExperience=10;}
    }
    if(Id==TEXT("blizzard")){D.Name=TEXT("暴风雪");D.Description=TEXT("需要装备法杖才能施放的高级寒冰魔法，在准星地面召唤持续伤害与寒冷的暴风雪区域。");D.Icon=TEXT("Skills/blizzard_cold_steel.png");}
    if(Id==TEXT("staffLight"))
    {D.Name=TEXT("水晶照明");D.Description=TEXT("学徒长杖的特殊功能：按 G 切换水晶照明，无冷却、无消耗。抬杖动作只播放一次，照明持续至再次按 G 或卸下法杖。");D.Icon=TEXT("Skills/staff_light_cold_steel.png");return D;}
    if(Id==TEXT("dodge")){D.Name=TEXT("闪避");D.Description=TEXT("短按左 Shift 后松开，朝输入方向快速闪避；无输入时沿朝向。动作期间无敌。");D.Icon=TEXT("Skills/dodge_cold_steel.png");}
    if(Id==TEXT("dexterousHands")){D.Name=TEXT("巧手");D.Description=TEXT("提高敏捷、换弹与拉弓速度。换弹、近战及完美节拍箭命中敌人可修炼，被动效果常驻。");D.Icon=TEXT("Skills/dexterous_hands.png");D.BowDrawSpeedPerLevel=.0125f;D.PerfectBowHitExperience=4;D.PerfectBowKillExperience=6;}
    if(Id==TEXT("pistolMastery")){D.Name=TEXT("手枪精通");D.Description=TEXT("精通手枪的快速射击，在移动中也能精准命中。");D.Icon=TEXT("Skills/pistol_mastery_cold_steel.png");}
    if(Id==TEXT("criticalStrike")){D.Name=TEXT("暴击");D.Description=TEXT("精通暴击之道，每次暴击都能造成更致命的打击。");D.Icon=TEXT("Skills/critical_strike_cold_steel.png");}
    if(Id==TEXT("fireball")){D.Name=TEXT("火球");D.Description=TEXT("按绑定键凝聚火球，再次按键朝准星发射。直击要害必定暴击，普通直击与爆炸波及目标各自随机判定暴击。");D.Icon=TEXT("Skills/fireball_ember_red.png");D.KillExperience=24;}
    if(Id==TEXT("quickCombat")){D.Name=TEXT("快速进战");D.Description=TEXT("按 F 以当前武器快速打击前方单个目标，造成少量伤害并击退，不附加眩晕。完整动作结束即可再次使用；技能成长降低体力消耗。快捷栏倒计时显示本次武器动作的剩余时间。");D.Icon=TEXT("Skills/quick_combat_placeholder.png");}
    if(Id==TEXT("runeBlades")){D.Name=TEXT("环绕飞剑");D.Description=TEXT("持符文长剑时按 G 唤出 4 把环绕身体的蓝色能量剑，最长驻留 30 秒；期间每按一次 G 随机发射一把朝向准星，命中造成（武器攻击＋魔法攻击）×1.2 的魔法伤害。全部发射或超时后进入 15 秒冷却。普通飞剑击杀减少魔法冷却 0.5 秒；装配金色符文后每枚有效命中减少魔法冷却 1 秒，击杀不重复结算。不影响武技及飞剑自身冷却。");D.Icon=TEXT("Skills/rune_orb_blades_cold_steel.png");}
    FString Json; TSharedPtr<FJsonObject> Root;
    if (!FFileHelper::LoadFileToString(Json, *(FPaths::ProjectContentDir()/TEXT("ColdSteelData/skills.json"))) ||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root) return D;
    const TSharedPtr<FJsonObject>* Entry = nullptr;
    if (!Root->TryGetObjectField(Id.ToString(), Entry)) return D;
    const auto& O = *Entry;
    O->TryGetStringField(TEXT("name"), D.Name); O->TryGetStringField(TEXT("description"), D.Description);
    O->TryGetStringField(TEXT("icon"), D.Icon); O->TryGetStringField(TEXT("upgradeSound"), D.UpgradeSound);
    auto Num = [&](const TCHAR* Key, double Default) { double Value=Default; O->TryGetNumberField(Key,Value); return FMath::IsFinite(Value)?Value:Default; };
    if(Id==TEXT("leapStrike"))
    {
        auto& T=D.LeapStrike;
        T.DamageBase=Num(TEXT("damageMultiplierBase"),T.DamageBase);T.DamageMax=Num(TEXT("damageMultiplierMax"),T.DamageMax);
        T.CooldownBase=Num(TEXT("cooldownBase"),T.CooldownBase);T.CooldownMin=Num(TEXT("cooldownMin"),T.CooldownMin);
        T.StaminaBase=Num(TEXT("staminaBase"),T.StaminaBase);T.StaminaMax=Num(TEXT("staminaMax"),T.StaminaMax);
        T.RadiusBaseCM=Num(TEXT("radiusBaseCM"),T.RadiusBaseCM);T.RadiusMaxCM=Num(TEXT("radiusMaxCM"),T.RadiusMaxCM);
        T.ReachBaseCM=Num(TEXT("reachBaseCM"),T.ReachBaseCM);T.ReachMaxCM=Num(TEXT("reachMaxCM"),T.ReachMaxCM);
        T.MultiKillExperience=Num(TEXT("multiKillExperience"),T.MultiKillExperience);
    }
    if(Id==TEXT("chainSlash"))
    {
        auto& T=D.ChainSlash;
        T.DamageBase=Num(TEXT("damageMultiplierBase"),T.DamageBase);T.DamageMax=Num(TEXT("damageMultiplierMax"),T.DamageMax);
        T.CooldownBase=Num(TEXT("cooldownBase"),T.CooldownBase);T.CooldownMin=Num(TEXT("cooldownMin"),T.CooldownMin);
        T.StaminaBase=Num(TEXT("staminaBase"),T.StaminaBase);T.StaminaMax=Num(TEXT("staminaMax"),T.StaminaMax);
        T.MultiKillExperience=Num(TEXT("multiKillExperience"),T.MultiKillExperience);
    }
    if(Id==TEXT("shadowStepSlash"))
    {
        auto& T=D.ShadowStep;
        T.Stage1DamageBase=Num(TEXT("stage1DamageBase"),T.Stage1DamageBase);T.Stage1DamageMax=Num(TEXT("stage1DamageMax"),T.Stage1DamageMax);
        T.Stage2DamageBase=Num(TEXT("stage2DamageBase"),T.Stage2DamageBase);T.Stage2DamageMax=Num(TEXT("stage2DamageMax"),T.Stage2DamageMax);
        T.DualPerHandRatio=FMath::Clamp(float(Num(TEXT("dualPerHandRatio"),T.DualPerHandRatio)),.1f,1.f);
        T.FollowupBackstabCritBonus=FMath::Clamp(float(Num(TEXT("followupBackstabCritBonus"),T.FollowupBackstabCritBonus)),0.f,100.f);
        T.FollowupWindowSeconds=FMath::Clamp(float(Num(TEXT("followupWindowSeconds"),T.FollowupWindowSeconds)),.1f,2.f);
        T.DashDistanceBaseCM=FMath::Clamp(float(Num(TEXT("dashDistanceBaseCM"),T.DashDistanceBaseCM)),100.f,1500.f);
        T.DashDistanceMaxCM=FMath::Clamp(float(Num(TEXT("dashDistanceMaxCM"),T.DashDistanceMaxCM)),T.DashDistanceBaseCM,1500.f);
        T.CooldownBase=Num(TEXT("cooldownBase"),T.CooldownBase);T.CooldownMin=Num(TEXT("cooldownMin"),T.CooldownMin);
        T.StaminaBase=Num(TEXT("staminaBase"),T.StaminaBase);T.StaminaMax=Num(TEXT("staminaMax"),T.StaminaMax);
        T.ToughnessStage1=Num(TEXT("toughnessStage1"),T.ToughnessStage1);T.ToughnessStage2=Num(TEXT("toughnessStage2"),T.ToughnessStage2);
        T.MultiKillExperience=Num(TEXT("multiKillExperience"),T.MultiKillExperience);
    }
    if(Id==TEXT("illuminationArrow"))
    {
        auto& T=D.IlluminationArrow;
        T.RadiusBase=Num(TEXT("radiusBaseCM"),T.RadiusBase);T.RadiusMax=Num(TEXT("radiusMaxCM"),T.RadiusMax);
        T.DurationBase=Num(TEXT("durationBase"),T.DurationBase);T.DurationMax=Num(TEXT("durationMax"),T.DurationMax);
        T.BonusBase=Num(TEXT("damageBonusBase"),T.BonusBase);T.BonusMax=Num(TEXT("damageBonusMax"),T.BonusMax);
        T.CooldownBase=Num(TEXT("cooldownBase"),T.CooldownBase);T.CooldownMin=Num(TEXT("cooldownMin"),T.CooldownMin);
        T.ManaCost=Num(TEXT("manaCost"),T.ManaCost);T.ThreeKillExperience=Num(TEXT("threeKillExperience"),T.ThreeKillExperience);
        T.FiveKillExperience=Num(TEXT("fiveKillExperience"),T.FiveKillExperience);T.SevenKillExperience=Num(TEXT("sevenKillExperience"),T.SevenKillExperience);
    }
    if(Id==TEXT("elementalArrow"))
    {
        auto& T=D.ElementalArrow;
        T.FireDamageMultiplier=FMath::Clamp(float(Num(TEXT("fireDamageMultiplier"),T.FireDamageMultiplier)),0.f,20.f);
        T.IceDamageMultiplier=FMath::Clamp(float(Num(TEXT("iceDamageMultiplier"),T.IceDamageMultiplier)),0.f,20.f);
        T.LightningDamageMultiplier=FMath::Clamp(float(Num(TEXT("lightningDamageMultiplier"),T.LightningDamageMultiplier)),0.f,20.f);
        T.FireGrowth=FMath::Clamp(float(Num(TEXT("fireGrowth"),T.FireGrowth)),0.f,2.f);
        T.FireLateGrowth=FMath::Clamp(float(Num(TEXT("fireLateGrowth"),T.FireLateGrowth)),0.f,2.f);
        T.ControlGrowth=FMath::Clamp(float(Num(TEXT("controlGrowth"),T.ControlGrowth)),0.f,2.f);
        T.ControlLateGrowth=FMath::Clamp(float(Num(TEXT("controlLateGrowth"),T.ControlLateGrowth)),0.f,2.f);
        T.GrowthChangeLevel=FMath::Clamp(int32(Num(TEXT("growthChangeLevel"),T.GrowthChangeLevel)),2,D.MaxLevel);
        T.ManaCostMultiplier=FMath::Clamp(float(Num(TEXT("manaCostMultiplier"),T.ManaCostMultiplier)),0.f,20.f);
        T.ManaPerSecond=FMath::Clamp(float(Num(TEXT("manaPerSecond"),T.ManaPerSecond)),0.f,100.f);
        T.RadiusMultiplier=Num(TEXT("radiusMultiplier"),2);
        T.ChillSeconds=Num(TEXT("chillSeconds"),5);T.ChillSlow=CombatChill::SlowPerStack;T.StunSeconds=Num(TEXT("stunSeconds"),1.5);
    }
    if(Id==TEXT("heartPiercingArrow"))
    {
        auto& T=D.HeartPiercingArrow;
        T.ChargeSeconds=FMath::Max(.1f,float(Num(TEXT("chargeSeconds"),3)));
        T.DamageBase=Num(TEXT("damageMultiplierBase"),2.5);
        T.EarlyGrowth=Num(TEXT("damageGrowthEarly"),.1);T.LateGrowth=Num(TEXT("damageGrowthLate"),.15);
        T.GrowthChangeLevel=FMath::Clamp(int32(Num(TEXT("growthChangeLevel"),8)),1,20);
        T.SecondPenetrationLevel=FMath::Clamp(int32(Num(TEXT("secondPenetrationLevel"),8)),1,20);
        T.ThirdPenetrationLevel=FMath::Clamp(int32(Num(TEXT("thirdPenetrationLevel"),16)),T.SecondPenetrationLevel,20);
        T.SpeedMultiplier=FMath::Max(1.f,float(Num(TEXT("arrowSpeedMultiplier"),2)));
    }
    if(Id==TEXT("magicArrowRain"))
    {
        auto& T=D.MagicArrowRain;
        T.ChargeSeconds=Num(TEXT("chargeSeconds"),1.2);T.Radius=Num(TEXT("radiusCM"),400);T.Range=Num(TEXT("rangeCM"),4000);
        T.BurstHeight=Num(TEXT("burstHeightCM"),600);T.MinimumHeight=Num(TEXT("minimumHeightCM"),220);
        T.ManaCost=Num(TEXT("manaCost"),20);T.ManaPerSecond=Num(TEXT("manaPerSecond"),3);T.Cooldown=Num(TEXT("cooldownSeconds"),16);
        T.SeedSpeed=Num(TEXT("seedSpeedCM"),3500);T.ArrowCount=FMath::Clamp(int32(Num(TEXT("arrowCount"),28)),24,32);
        T.DamageBase=Num(TEXT("damageBase"),T.DamageBase);T.DamagePerLevel=Num(TEXT("damagePerLevel"),T.DamagePerLevel);
        T.DexterityBase=Num(TEXT("dexterityBase"),T.DexterityBase);T.DexterityPerLevel=Num(TEXT("dexterityPerLevel"),T.DexterityPerLevel);
        T.IntelligenceBase=Num(TEXT("intelligenceBase"),T.IntelligenceBase);T.IntelligencePerLevel=Num(TEXT("intelligencePerLevel"),T.IntelligencePerLevel);
    }
    if(Id==TEXT("swordUppercut"))
    {
        D.UppercutStaminaCost=FMath::Max(0.f,float(Num(TEXT("staminaCost"),25)));
        D.UppercutCooldownSeconds=FMath::Clamp(float(Num(TEXT("cooldownSeconds"),8)),0.f,300.f);
        D.UppercutRangeMultiplier=FMath::Max(.01f,float(Num(TEXT("rangeMultiplier"),1.25)));
        D.UppercutReachGrowthPerLevel=FMath::Max(0.f,float(Num(TEXT("reachGrowthPerLevel"),.01)));
    }
    D.HeavyMultiplierBase=Num(TEXT("heavyMultiplierBase"),2.5);D.HeavyMultiplierPerLevel=Num(TEXT("heavyMultiplierPerLevel"),.1);
    D.HeavyChargeBase=Num(TEXT("heavyChargeBase"),2);D.HeavyChargeReductionPerLevel=Num(TEXT("heavyChargeReductionPerLevel"),.05);
    D.HeavyChargeStaminaPerSecond=FMath::Max(0.f,float(Num(TEXT("heavyChargeStaminaPerSecond"),2)));
    D.HeavyHit2Experience=Num(TEXT("heavyHit2Experience"),5);D.HeavyKill2Experience=Num(TEXT("heavyKill2Experience"),12);
    D.HeavyHit5Experience=Num(TEXT("heavyHit5Experience"),25);D.HeavyKill5Experience=Num(TEXT("heavyKill5Experience"),60);
    D.StrengthPerLevel=Num(TEXT("strengthPerLevel"),0);D.ConstitutionPerLevel=Num(TEXT("constitutionPerLevel"),0);
    D.HitExperience=Num(TEXT("hitExperience"),0);D.MultiHitExperience=Num(TEXT("multiHitExperience"),0);
    D.CooldownReductionPerLevel=Num(TEXT("cooldownReductionPerLevel"),0);
    D.CriticalChancePerLevel=FMath::Clamp(float(Num(TEXT("criticalChancePerLevel"),0)),0.f,20.f);
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
    D.BowDrawSpeedPerLevel=FMath::Clamp(float(Num(TEXT("bowDrawSpeedPerLevel"),D.BowDrawSpeedPerLevel)),0.f,1.f);
    D.ReloadExperience=FMath::Clamp(int32(Num(TEXT("reloadExperience"),5)),0,10000);
    D.MeleeHitExperience=FMath::Clamp(int32(Num(TEXT("meleeHitExperience"),0)),0,10000);
    D.MeleeKillExperience=FMath::Clamp(int32(Num(TEXT("meleeKillExperience"),0)),0,10000);
    D.PerfectBowHitExperience=FMath::Clamp(int32(Num(TEXT("perfectBowHitExperience"),D.PerfectBowHitExperience)),0,10000);
    D.PerfectBowKillExperience=FMath::Clamp(int32(Num(TEXT("perfectBowKillExperience"),D.PerfectBowKillExperience)),0,10000);
    D.MoveSpeedPerLevel=FMath::Clamp(float(Num(TEXT("moveSpeedPerLevel"),.01)),0.f,1.f);
    // 持械移速固定档：0 = 不配置（保持 1 倍倍率），否则钳制在 0-1.5，避免写错系数毁掉移动。
    D.MovementMultiplier=FMath::Clamp(float(Num(TEXT("movementMultiplier"),0)),0.f,1.5f);
    D.CriticalDamageBase=FMath::Clamp(float(Num(TEXT("criticalDamageBase"),.50)),0.f,5.f);
    D.CriticalDamagePerLevel=FMath::Clamp(float(Num(TEXT("criticalDamagePerLevel"),.05)),0.f,1.f);
    D.LuckPerLevel=FMath::Clamp(int32(Num(TEXT("luckPerLevel"),1)),0,100);
    D.CriticalHitExperience=FMath::Clamp(int32(Num(TEXT("criticalHitExperience"),1)),0,10000);
    D.CriticalKillExperience=FMath::Clamp(int32(Num(TEXT("criticalKillExperience"),10)),0,10000);
    if(ElectricMagic::IsSkill(Id))
    {
        auto& T=D.ElectricMagic;
        T.DamageBase=Num(TEXT("damageBase"),T.DamageBase);T.DamagePerLevel=Num(TEXT("damagePerLevel"),T.DamagePerLevel);
        T.MagicBase=Num(TEXT("magicBase"),T.MagicBase);T.MagicPerLevel=Num(TEXT("magicPerLevel"),T.MagicPerLevel);
        T.IntelligenceBase=Num(TEXT("intelligenceBase"),T.IntelligenceBase);T.IntelligencePerLevel=Num(TEXT("intelligencePerLevel"),T.IntelligencePerLevel);
        T.ManaBase=Num(TEXT("manaBase"),T.ManaBase);T.ManaGrowth=Num(TEXT("manaGrowth"),T.ManaGrowth);
        T.Cooldown=Num(TEXT("cooldown"),T.Cooldown);T.CooldownReduction=Num(TEXT("cooldownReduction"),T.CooldownReduction);
        T.Duration=Num(TEXT("duration"),T.Duration);T.DurationGrowth=Num(TEXT("durationGrowth"),T.DurationGrowth);
        T.RadiusBase=Num(TEXT("radiusBase"),T.RadiusBase);T.RadiusPerLevel=Num(TEXT("radiusPerLevel"),T.RadiusPerLevel);
        T.RangeBase=Num(TEXT("rangeBase"),T.RangeBase);T.RangePerLevel=Num(TEXT("rangePerLevel"),T.RangePerLevel);T.UnitsToCM=Num(TEXT("unitsToCM"),T.UnitsToCM);
        T.StrikeSeconds=FMath::Max(.1f,float(Num(TEXT("strikeSeconds"),T.StrikeSeconds)));T.ChainRange=Num(TEXT("chainRange"),T.ChainRange);T.ChainDecay=Num(TEXT("chainDecay"),T.ChainDecay);
        T.ChainExtraBase=Num(TEXT("chainExtraBase"),T.ChainExtraBase);T.ChainLevelStep=FMath::Max(1,int32(Num(TEXT("chainLevelStep"),T.ChainLevelStep)));
        T.StunSeconds=Num(TEXT("stunSeconds"),T.StunSeconds);T.ElectrifyStacks=Num(TEXT("electrifyStacks"),T.ElectrifyStacks);T.ElectrifySeconds=Num(TEXT("electrifySeconds"),T.ElectrifySeconds);
        T.MinCharge=Num(TEXT("minCharge"),T.MinCharge);T.MaxCharge=Num(TEXT("maxCharge"),T.MaxCharge);T.ChargeBonus=Num(TEXT("chargeBonus"),T.ChargeBonus);T.StackDamage=Num(TEXT("stackDamage"),T.StackDamage);
        T.HalfWidth=Num(TEXT("halfWidth"),T.HalfWidth);T.KnockbackBase=Num(TEXT("knockbackBase"),T.KnockbackBase);T.KnockbackGrowth=Num(TEXT("knockbackGrowth"),T.KnockbackGrowth);T.EndRadius=Num(TEXT("endRadius"),T.EndRadius);
        T.BeamHold=FMath::Clamp(float(Num(TEXT("beamHold"),T.BeamHold)),.05f,4.f);T.BeamFade=FMath::Clamp(float(Num(TEXT("beamFade"),T.BeamFade)),.05f,2.f);
        O->TryGetBoolField(TEXT("requiresStaff"),T.bRequiresStaff);
        T.HitExperience=Num(TEXT("hitExperience"),T.HitExperience);T.KillExperience=Num(TEXT("killExperience"),T.KillExperience);T.MultiHitExperience=Num(TEXT("multiHitExperience"),T.MultiHitExperience);T.MultiKillExperience=Num(TEXT("multiKillExperience"),T.MultiKillExperience);
    }
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
    if(Id==TEXT("blizzard"))
    {
        auto& F=D.Blizzard;
        O->TryGetBoolField(TEXT("requiresStaff"),F.bRequiresStaff);
        F.DamageBase=Num(TEXT("damageBase"),5);F.DamagePerLevel=Num(TEXT("damagePerLevel"),2);
        F.MagicBase=Num(TEXT("magicBase"),.12);F.MagicPerLevel=Num(TEXT("magicPerLevel"),.02);
        F.IntelligenceBase=Num(TEXT("intelligenceBase"),.12);F.IntelligencePerLevel=Num(TEXT("intelligencePerLevel"),.02);
        F.RadiusXBase=Num(TEXT("radiusXBase"),200);F.RadiusXPerLevel=Num(TEXT("radiusXPerLevel"),8);
        F.RadiusYBase=Num(TEXT("radiusYBase"),124);F.RadiusYPerLevel=Num(TEXT("radiusYPerLevel"),5);
        F.ManaCost=Num(TEXT("manaCost"),150);F.Cooldown=Num(TEXT("cooldown"),40);F.CooldownReduction=Num(TEXT("cooldownReduction"),5);
        F.Duration=Num(TEXT("duration"),5);F.DurationGrowth=Num(TEXT("durationGrowth"),5);
        F.Range=Num(TEXT("maxRange"),650);F.UnitsToCM=Num(TEXT("unitsToCM"),1.5);
        F.TickSeconds=FMath::Max(.1f,float(Num(TEXT("tickSeconds"),.5)));
        F.ChillStacks=Num(TEXT("chillStacks"),1);F.ChillSeconds=Num(TEXT("chillSeconds"),2.5);F.ChillSlow=CombatChill::SlowPerStack;
        F.HitExperience=Num(TEXT("hitExperience"),1);F.KillExperience=Num(TEXT("killExperience"),6);
        F.MultiHitExperience=Num(TEXT("multiHitExperience"),5);F.MultiKillExperience=Num(TEXT("multiKillExperience"),10);
    }
    if(Id==TEXT("iceWall"))
    {
        auto& F=D.IceWall;
        O->TryGetBoolField(TEXT("requiresStaff"),F.bRequiresStaff);
        F.DamageBase=Num(TEXT("damageBase"),10);F.DamagePerLevel=Num(TEXT("damagePerLevel"),10);
        F.IntelligenceBase=Num(TEXT("intelligenceBase"),1);F.IntelligencePerLevel=Num(TEXT("intelligencePerLevel"),.25);
        F.WisdomBase=Num(TEXT("wisdomBase"),1);F.WisdomPerLevel=Num(TEXT("wisdomPerLevel"),.25);
        F.CountBase=FMath::Clamp(int32(Num(TEXT("countBase"),5)),1,43);F.CountPerLevel=FMath::Clamp(int32(Num(TEXT("countPerLevel"),2)),0,2);
        F.ManaCost=Num(TEXT("manaCost"),100);F.Cooldown=Num(TEXT("cooldown"),30);
        F.Range=Num(TEXT("maxRange"),500);F.UnitsToCM=Num(TEXT("unitsToCM"),1.5);
        F.Duration=Num(TEXT("duration"),10);F.DurationPerLevel=Num(TEXT("durationPerLevel"),.5);
        F.SegmentSpacing=Num(TEXT("segmentSpacing"),28);F.Thickness=Num(TEXT("thicknessCM"),62);
        F.HighHeight=Num(TEXT("highHeightCM"),260);F.LowHeight=Num(TEXT("lowHeightCM"),100);
        F.HoverDuration=Num(TEXT("hoverDuration"),30);
        F.RiseSeconds=FMath::Max(.05f,float(Num(TEXT("riseSeconds"),.08)));
        F.RiseHeight=FMath::Max(0.f,float(Num(TEXT("riseHeightCM"),160)));
        F.DropSeconds=FMath::Max(.05f,float(Num(TEXT("dropSeconds"),.06)));
        F.DropHeight=FMath::Max(0.f,float(Num(TEXT("dropHeightCM"),360)));
        F.MaxHealth=FMath::Max(1.f,float(Num(TEXT("maxHealth"),300)));
        F.MaxHealthPerLevel=FMath::Max(0.f,float(Num(TEXT("maxHealthPerLevel"),50)));
        F.Knockback=Num(TEXT("hitKnockback"),50);F.PushDistanceMultiplier=Num(TEXT("pushDistanceMultiplier"),2);
        F.ChillRadius=Num(TEXT("chillRadius"),100);F.ChillInterval=FMath::Max(.1f,float(Num(TEXT("chillInterval"),1)));
        F.ChillStacks=Num(TEXT("chillStacks"),1);F.ChillDuration=Num(TEXT("chillDuration"),2.5);F.ChillSlow=CombatChill::SlowPerStack;
        F.HitExperience=Num(TEXT("hitExperience"),3);F.KillExperience=Num(TEXT("killExperience"),10);F.MultiHitExperience=Num(TEXT("multiHitExperience"),10);
    }
    if(Id==TEXT("lightningHaste"))
    {
        auto& T=D.LightningHaste;
        T.MoveBase=Num(TEXT("moveSpeedBase"),T.MoveBase);T.MovePerLevel=Num(TEXT("moveSpeedPerLevel"),T.MovePerLevel);
        T.ActionBase=Num(TEXT("actionSpeedBase"),T.ActionBase);T.ActionPerLevel=Num(TEXT("actionSpeedPerLevel"),T.ActionPerLevel);
        T.DurationBase=Num(TEXT("durationBase"),T.DurationBase);T.DurationPerLevel=Num(TEXT("durationPerLevel"),T.DurationPerLevel);
        T.ManaBase=Num(TEXT("manaBase"),T.ManaBase);T.ManaPerLevel=Num(TEXT("manaPerLevel"),T.ManaPerLevel);T.Cooldown=Num(TEXT("cooldown"),T.Cooldown);
        T.CastExperience=Num(TEXT("castExperience"),T.CastExperience);T.KillExperience=Num(TEXT("killExperience"),T.KillExperience);
        T.Kill6Bonus=Num(TEXT("kill6Bonus"),T.Kill6Bonus);T.Kill11Bonus=Num(TEXT("kill11Bonus"),T.Kill11Bonus);
    }
    if(Id==TEXT("iceArmor"))
    {
        auto& T=D.IceArmor;
        T.PhysicalBase=Num(TEXT("physicalDefenseBase"),T.PhysicalBase);
        T.PhysicalPerLevel=Num(TEXT("physicalDefensePerLevel"),T.PhysicalPerLevel);
        T.PhysicalMagic=Num(TEXT("physicalDefenseMagicFactor"),T.PhysicalMagic);
        T.MagicBase=Num(TEXT("magicDefenseBase"),T.MagicBase);
        T.MagicPerLevel=Num(TEXT("magicDefensePerLevel"),T.MagicPerLevel);
        T.MagicMagic=Num(TEXT("magicDefenseMagicFactor"),T.MagicMagic);
        T.DurationBase=Num(TEXT("durationBase"),T.DurationBase);
        T.DurationGrowth=Num(TEXT("durationGrowth"),T.DurationGrowth);
        T.ManaBase=Num(TEXT("manaBase"),T.ManaBase);
        T.ManaPerLevel=Num(TEXT("manaPerLevel"),T.ManaPerLevel);
        T.Cooldown=Num(TEXT("cooldown"),T.Cooldown);
        T.CooldownReduction=Num(TEXT("cooldownReduction"),T.CooldownReduction);
        T.RadiusBase=Num(TEXT("radiusBaseCM"),T.RadiusBase);
        T.RadiusGrowth=Num(TEXT("radiusGrowthCM"),T.RadiusGrowth);
        T.PulseSeconds=Num(TEXT("pulseSeconds"),T.PulseSeconds);
        T.ChillSeconds=Num(TEXT("chillSeconds"),T.ChillSeconds);
        T.ChillGrowth=Num(TEXT("chillDurationGrowth"),T.ChillGrowth);
        T.SlowPerStack=CombatChill::SlowPerStack;
        T.TrainingSourceInterval=Num(TEXT("trainingSourceInterval"),T.TrainingSourceInterval);
        T.CastExperience=Num(TEXT("castExperience"),T.CastExperience);
        T.MeleeExperience=Num(TEXT("meleeHitExperience"),T.MeleeExperience);
        T.RangedExperience=Num(TEXT("rangedHitExperience"),T.RangedExperience);
        T.ExperienceCap=Num(TEXT("experienceCapPerCast"),T.ExperienceCap);
        T.PulseSeconds=FMath::Max(.1f,T.PulseSeconds);T.DurationBase=FMath::Max(.1f,T.DurationBase);T.TrainingSourceInterval=FMath::Max(.1f,T.TrainingSourceInterval);
    }
    if(FireMagic::IsSkill(Id))
    {
        auto& F=D.FireMagic;
        F.RadiusMaximum=Num(TEXT("radiusMaximumCM"),1500);
        F.ArcDegrees=Num(TEXT("arcDegrees"),90);
        F.DamageBase=Num(TEXT("damageBase"),F.DamageBase);F.DamagePerLevel=Num(TEXT("damagePerLevel"),F.DamagePerLevel);
        F.MagicBase=Num(TEXT("magicBase"),F.MagicBase);F.MagicPerLevel=Num(TEXT("magicPerLevel"),F.MagicPerLevel);
        F.IntelligenceBase=Num(TEXT("intelligenceBase"),F.IntelligenceBase);F.IntelligencePerLevel=Num(TEXT("intelligencePerLevel"),F.IntelligencePerLevel);
        F.AuraDamageBase=Num(TEXT("auraDamageBase"),F.AuraDamageBase);F.AuraDamagePerLevel=Num(TEXT("auraDamagePerLevel"),F.AuraDamagePerLevel);
        F.AuraMagicBase=Num(TEXT("auraMagicBase"),F.AuraMagicBase);F.AuraMagicPerLevel=Num(TEXT("auraMagicPerLevel"),F.AuraMagicPerLevel);
        F.AuraIntelligenceBase=Num(TEXT("auraIntelligenceBase"),F.AuraIntelligenceBase);F.AuraIntelligencePerLevel=Num(TEXT("auraIntelligencePerLevel"),F.AuraIntelligencePerLevel);
        F.RadiusBase=Num(TEXT("radiusBase"),F.RadiusBase);F.RadiusPerLevel=Num(TEXT("radiusPerLevel"),F.RadiusPerLevel);
        F.AuraRadiusBase=Num(TEXT("auraRadiusBase"),F.AuraRadiusBase);F.AuraRadiusPerLevel=Num(TEXT("auraRadiusPerLevel"),F.AuraRadiusPerLevel);
        F.UnitsToCM=Num(TEXT("unitsToCM"),F.UnitsToCM);F.ManaBase=Num(TEXT("manaBase"),F.ManaBase);F.ManaGrowth=Num(TEXT("manaGrowth"),F.ManaGrowth);
        F.Cooldown=Num(TEXT("cooldown"),F.Cooldown);F.CooldownReduction=Num(TEXT("cooldownReduction"),F.CooldownReduction);
        F.DurationBase=Num(TEXT("durationBase"),F.DurationBase);F.DurationGrowth=Num(TEXT("durationGrowth"),F.DurationGrowth);
        F.Range=Num(TEXT("maxRange"),F.Range);F.FallSeconds=Num(TEXT("fallSeconds"),F.FallSeconds);
        F.TickSeconds=FMath::Max(.05f,float(Num(TEXT("tickSeconds"),F.TickSeconds)));F.StunSeconds=Num(TEXT("stunSeconds"),F.StunSeconds);
        F.BurnStacks=Num(TEXT("burnStacks"),F.BurnStacks);F.BurnSeconds=Num(TEXT("burnSeconds"),F.BurnSeconds);F.BurnMultiplier=Num(TEXT("burnMultiplier"),F.BurnMultiplier);
        F.AuraBurnStacks=Num(TEXT("auraBurnStacks"),F.AuraBurnStacks);F.AuraBurnSeconds=Num(TEXT("auraBurnSeconds"),F.AuraBurnSeconds);F.AuraBurnMultiplier=Num(TEXT("auraBurnMultiplier"),F.AuraBurnMultiplier);
        F.HitExperience=Num(TEXT("hitExperience"),F.HitExperience);F.KillExperience=Num(TEXT("killExperience"),F.KillExperience);
        F.MultiHitExperience=Num(TEXT("multiHitExperience"),F.MultiHitExperience);F.MultiKillExperience=Num(TEXT("multiKillExperience"),F.MultiKillExperience);
        O->TryGetBoolField(TEXT("requiresStaff"),F.bRequiresStaff);
    }
    if(Id==TEXT("holyLight"))
    {
        auto& F=D.HolyLight;
        F.AmountBase=Num(TEXT("amountBase"),5);F.AmountPerLevel=Num(TEXT("amountPerLevel"),5);
        F.MagicBase=Num(TEXT("magicBase"),.25);F.MagicPerLevel=Num(TEXT("magicPerLevel"),.25);
        F.IntelligenceBase=Num(TEXT("intelligenceBase"),1);F.IntelligencePerLevel=Num(TEXT("intelligencePerLevel"),.5);
        F.WisdomBase=Num(TEXT("wisdomBase"),1);F.WisdomPerLevel=Num(TEXT("wisdomPerLevel"),.5);
        F.ManaCost=Num(TEXT("manaCost"),30);F.Cooldown=Num(TEXT("cooldown"),10);
        F.CooldownLevelStep=FMath::Max(1,int32(Num(TEXT("cooldownLevelStep"),5)));F.CooldownStepReduction=Num(TEXT("cooldownStepReduction"),1);
        F.Range=Num(TEXT("range"),600);F.AimRadius=Num(TEXT("aimRadius"),200);F.UnitsToCM=Num(TEXT("unitsToCM"),1.5);
        F.ZombieMultiplier=Num(TEXT("zombieMultiplier"),2);F.Duration=Num(TEXT("duration"),2);F.Fade=Num(TEXT("fade"),.4);
        F.TopWidth=Num(TEXT("topWidth"),60);F.BottomWidth=Num(TEXT("bottomWidth"),110);F.Height=Num(TEXT("height"),1400);F.DissolveRatio=Num(TEXT("dissolveRatio"),.28);
        F.HitExperience=Num(TEXT("hitExperience"),5);F.KillExperience=Num(TEXT("killExperience"),10);
    }
    if(Id==TEXT("lightningStrike"))
    {
        auto& F=D.Lightning;
        F.DamageBase=Num(TEXT("damageBase"),20);F.DamagePerLevel=Num(TEXT("damagePerLevel"),10);
        F.MagicBase=Num(TEXT("magicBase"),1.15);F.MagicPerLevel=Num(TEXT("magicPerLevel"),.25);
        F.IntelligenceBase=Num(TEXT("intelligenceBase"),1);F.IntelligencePerLevel=Num(TEXT("intelligencePerLevel"),.25);
        F.ManaCost=Num(TEXT("manaCost"),30);F.Cooldown=Num(TEXT("cooldown"),12);
        F.AimRadius=Num(TEXT("aimRadius"),200);F.Range=Num(TEXT("maxRange"),600);F.ChainRange=Num(TEXT("chainRange"),200);F.UnitsToCM=Num(TEXT("unitsToCM"),1.5);
        F.CountBase=Num(TEXT("countBase"),1);F.CountLevelStep=FMath::Max(1,int32(Num(TEXT("countLevelStep"),5)));F.ChainDecay=Num(TEXT("chainDecay"),.1);
        F.StunBase=Num(TEXT("stunBase"),.75);F.StunPerLevel=Num(TEXT("stunPerLevel"),.02);
        F.Duration=Num(TEXT("duration"),.5);F.Fade=Num(TEXT("fade"),.25);F.Segments=Num(TEXT("segments"),10);F.Jitter=Num(TEXT("jitter"),.09);
        F.ElectrifyStacks=Num(TEXT("electrifyStacks"),1);F.ElectrifyDuration=Num(TEXT("electrifyDuration"),4);F.ElectricBonusPerStack=Num(TEXT("electricBonusPerStack"),.03);
        F.OverloadStacks=Num(TEXT("overloadStacks"),5);F.OverloadStun=Num(TEXT("overloadStun"),1.2);F.OverloadRange=Num(TEXT("overloadRange"),150);
        F.OverloadBase=Num(TEXT("overloadBase"),20);F.OverloadMagic=Num(TEXT("overloadMagic"),1.2);F.OverloadIntelligence=Num(TEXT("overloadIntelligence"),1.2);
        F.HitExperience=Num(TEXT("hitExperience"),4);F.KillExperience=Num(TEXT("killExperience"),10);
        F.MultiHitExperience=Num(TEXT("multiHitExperience"),10);F.MultiKillExperience=Num(TEXT("multiKillExperience"),10);
    }
    if(Id==TEXT("dashAttack"))
    {
        auto& T=D.DashAttack;
        T.DamageBase=Num(TEXT("damageMultiplierBase"),1.75);T.DamagePerLevel=Num(TEXT("damageMultiplierPerLevel"),.05);
        T.ReadySeconds=Num(TEXT("readySeconds"),1);T.ReadyReductionPerLevel=Num(TEXT("readyReductionPerLevel"),.03);
        T.StaminaCost=Num(TEXT("staminaCost"),20);T.Distance=Num(TEXT("distanceCM"),100);
        T.UnitsToCM=Num(TEXT("unitsToCM"),1.5);
        T.RangeBase=Num(TEXT("rangeBonusBase"),6);T.RangePerLevel=Num(TEXT("rangeBonusPerLevel"),6);T.RangeFlat=Num(TEXT("rangeBonusFlat"),55);
        T.KnockbackBonus=Num(TEXT("knockbackBonus"),188);T.KnockbackPerLevel=Num(TEXT("knockbackPerLevel"),6);
        T.ArcDegrees=Num(TEXT("arcDegrees"),60);
    }
    if(Id==TEXT("whirlwind"))
    {
        auto& W=D.Whirlwind;
        W.DamageBase=Num(TEXT("damageMultiplierBase"),1.5);W.DamagePerLevel=Num(TEXT("damageMultiplierPerLevel"),.1);
        W.CooldownBase=Num(TEXT("cooldownBase"),10);W.CooldownReduction=Num(TEXT("cooldownReduction"),.2);
        W.StaminaBase=Num(TEXT("staminaBase"),20);W.StaminaPerLevel=Num(TEXT("staminaPerLevel"),1);
        W.RadiusBase=Num(TEXT("radiusBase"),120);W.RadiusPerLevel=Num(TEXT("radiusPerLevel"),5);
        W.MeleeRadiusBonus=Num(TEXT("meleeRadiusBonus"),80);W.UnitsToCM=Num(TEXT("unitsToCM"),1.5);
        W.Knockback=Num(TEXT("knockback"),250);W.StunSeconds=Num(TEXT("stunSeconds"),2.5);
        W.ReadySeconds=Num(TEXT("readySeconds"),.5);W.SpinSeconds=Num(TEXT("spinSeconds"),W.SpinSeconds);
        W.RecoverSeconds=Num(TEXT("recoverSeconds"),.52);W.TurnDegrees=Num(TEXT("turnDegrees"),720);
        W.HitStopSeconds=Num(TEXT("hitStopSeconds"),.045);W.HitStopBudget=Num(TEXT("hitStopBudget"),.135);
        W.MotionBlur=Num(TEXT("motionBlur"),.65);
    }
    if(Id==TEXT("quickCombat"))
    {
        auto& Q=D.QuickCombat;
        Q.DamageBase=Num(TEXT("damageBase"),5);Q.DamagePerLevel=Num(TEXT("damagePerLevel"),1);
        Q.StrengthFactorBase=Num(TEXT("strengthFactorBase"),1);Q.StrengthFactorPerLevel=Num(TEXT("strengthFactorPerLevel"),.02);
        Q.KnockbackCM=FMath::Clamp(float(Num(TEXT("knockbackCM"),50)),0.f,1000.f);
        Q.RangeCM=FMath::Clamp(float(Num(TEXT("rangeCM"),200)),50.f,1000.f);
        Q.StaminaCost=FMath::Max(0.f,float(Num(TEXT("staminaCost"),15)));
        Q.StaminaReductionPerLevel=FMath::Clamp(float(Num(TEXT("staminaReductionPerLevel"),.02)),0.f,1.f);
    }
    return D;
}
