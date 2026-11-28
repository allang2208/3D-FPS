#include "ColdSteelSkillRules.h"
#include "../Weapons/Bow/EclipseBowMark.h"
#include "../Weapons/PojunGrip.h"
#include "../Weapons/Kukri/KukriWeaponComponent.h"
#include "../Weapons/Kukri/KukriRelentlessComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/Kukri/KukriPairedHeavyHit.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Production/ThunderHammerRunes.h"
#include "../Production/ThunderHammerTuning.h"
#include "../Weapons/Kukri/KukriBerserkerComponent.h"
#include "../Weapons/Kukri/KukriEnchantment.h"
#include "../Weapons/Kukri/KukriFrostRavenComponent.h"
#include "../Weapons/AncientSealSeat.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "FPSLightningHasteComponent.h"
#include "IlluminationMarkComponent.h"
#include "../Monsters/RootCrownRigPreview.h"
#include "../Monsters/HeQueMonster.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Production/ProductionToolStats.h"
#include "../Production/ProductionToolComponent.h"
#include "../Production/RuneboundHammerTuning.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/FPSBallisticsComponent.h"
#include "../Weapons/FPSMeleeLightningComponent.h"
#include "../Weapons/WoodenTorchComponent.h"
#include "../Weapons/WoodenTorchItem.h"
#include "../Weapons/ColdSteelEnchantmentCombat.h"
#include "../Weapons/SniperSuppressorAssets.h"
#include "../Monsters/MonsterDamageAlert.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/HandBrainMonster.h"
#include "../Monsters/M10Mawcrawler.h"
#include "../Monsters/M66IncineratorMonster.h"
#include "../Monsters/HangingBellM09.h"
#include "../Monsters/VortexCofferM25.h"
#include "../Monsters/SpiralPillarM14.h"
#include "../Monsters/BoundCongregate.h"
#include "../Monsters/HumanoidHitVolumeData.h"
#include "../Props/FPSPracticeTarget.h"
#include "Engine/GameInstance.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"

namespace
{
// Keep the same shadow-profile-first lookup at each combat entry point.
UColdSteelStatusModel* SkillCombatModel(AActor* Shooter)
{
    if(Shooter&&Shooter->ActorHasTag(TEXT("VillageDefense")))return nullptr;
    UColdSteelStatusModel* Model=nullptr;
    if(const auto* Character=Cast<AFPSGAMECharacter>(Shooter))Model=Character->GetNetShadowProfile();
    if(!Model&&Shooter&&Shooter->GetGameInstance())Model=Shooter->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    return Model;
}
}

bool ColdSteelSkills::IsRifle(const FColdSteelItem* I)
{ if(!I)return false;const FString Type=ColdSteelInventory::Text(*I,TEXT("weaponType"));return Type==TEXT("rifle")||Type==TEXT("sniper"); }
bool ColdSteelSkills::IsPistol(const FColdSteelItem* I)
{ return I && ColdSteelInventory::Text(*I,TEXT("weaponType"))==TEXT("pistol"); }
bool ColdSteelSkills::IsCriticalHit(const FHitResult& Hit)
{
    if(const auto* HeQue=Cast<AHeQueMonster>(Hit.GetActor()))return HeQue->IsWeakpointHit(Hit);
    if(const auto* Crown=Cast<ARootCrownRigPreview>(Hit.GetActor()))return Crown->IsWeakpointHit(Hit);
    if(const auto* M14=Cast<ASpiralPillarM14>(Hit.GetActor()))return M14->IsWeakpointHit(Hit);
    if(const auto* M25=Cast<AVortexCofferM25>(Hit.GetActor()))return M25->IsWeakpointHit(Hit);
    if(const auto* M09=Cast<AHangingBellM09>(Hit.GetActor()))return M09->IsWeakpointHit(Hit);
    if(const auto* M10=Cast<AM10Mawcrawler>(Hit.GetActor()))return M10->IsWeakpointHit(Hit);
    if(const auto* M66=Cast<AM66IncineratorMonster>(Hit.GetActor()))return M66->IsWeakpointHit(Hit);
    // 手脑怪要害自定义：只有释放吼叫（Howl）期间命中张开的口部才算弱点；其余时间头部
    // （cranium）一律不触发要害必暴。随机暴击是角色属性驱动（见 Snapshot 的 crit chance），
    // 不经此处，所以近战/枪械仍可按概率对其暴击，符合"平时无固定弱点、可被随机暴击"的口径。
    if(const auto* Brain=Cast<AHandBrainMonster>(Hit.GetActor()))return Brain->IsWeakpointHit(Hit);
    // 训练靶：命中点落在靶心正面区域即要害（靶心无骨骼，按网格本地坐标判定）。
    if(const auto* Target=Cast<AFPSPracticeTarget>(Hit.GetActor()))return Target->IsBullseyeHit(Hit);
    bool bFittedHead = false;
    if (UHumanoidHitVolumeData::ResolveCriticalHit(Hit, bFittedHead)) return bFittedHead;
    const FString Bone=Hit.BoneName.ToString();return Bone.Contains(TEXT("head"),ESearchCase::IgnoreCase)||Bone.Equals(TEXT("cranium"),ESearchCase::IgnoreCase);
}

FColdSteelSkillShot ColdSteelSkills::StaffQuickStrike(const UColdSteelStatusModel& Profile,const FColdSteelItem* Torch)
{
    FColdSteelSkillShot Shot;
    Shot.CriticalChance=Profile.Derived(TEXT("crit"));
    Shot.CriticalDamageBonus=Profile.CriticalStrikeEffect().CriticalDamageBonus;
    if(Torch){Shot.ItemDefinition=Torch->Definition;Shot.ItemInstance=Torch->InstanceId;}
    return Shot;
}

FColdSteelSkillShot ColdSteelSkills::Snapshot(AActor* Shooter,const FColdSteelItem* Item,bool bFiredRound)
{
    FColdSteelSkillShot Shot;
    if(const FColdSteelItem* Source=Item?Item:nullptr){Shot.ItemDefinition=Source->Definition;Shot.ItemInstance=Source->InstanceId;}
    // 联机：服务端上远端玩家的数值来源是影子档案，不是 GameInstance 单例（单例是主机的档）。
    UColdSteelStatusModel* M=SkillCombatModel(Shooter);
    if (M)
    { Shot.bRifle=IsRifle(Item?Item:M->Equipped());Shot.bPistol=IsPistol(Item?Item:M->Equipped()); Shot.WeakpointPercent=Shot.bRifle?M->RifleEffect().WeakpointPercent:0;
      // 枪械自带的要害伤害加成（物品定义 innate_weakpoint_percent，M1911 = 120%）：
      // 与步枪精通同一个要害乘区，非步枪武器靠这一项获得要害收益。
      if(const auto* I=Item?Item:M->Equipped())Shot.WeakpointPercent+=float(ColdSteelInventory::Number(*I,TEXT("innate_weakpoint_percent")));
      Shot.CriticalDamageBonus=M->CriticalStrikeEffect().CriticalDamageBonus; }
    if(M)
    {
        Shot.CriticalChance=M->Derived(TEXT("crit"));Shot.MasteryId=M->WeaponMastery(Item?Item:M->Equipped());
        if(IsMeleeMastery(Shot.MasteryId)){static uint32 NextMasteryAttack=0;if(++NextMasteryAttack==0)++NextMasteryAttack;Shot.MasteryAttackSerial=NextMasteryAttack;}
        if(const auto* I=Item?Item:M->Equipped())if(auto* E=Shooter->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {
            Shot.CriticalChance+=100*E->Effect(*I,TEXT("critRate"));
            Shot.ArmorPenetration=E->CraftEffect(*I,TEXT("armorPenetrationPercent"))+E->Effect(*I,TEXT("armorPenetrationPercent"));
            // 武器自带护甲穿透（物品定义 innate_armor_penetration，Pit Viper 2011 = 25%）：
            // 与改造/附魔/弹种穿透同一路相加，最终在步枪兵分支里 clamp 到 [0,1]。
            Shot.ArmorPenetration+=float(ColdSteelInventory::Number(*I,TEXT("innate_armor_penetration")));
            Shot.MagicPenetration=E->CraftEffect(*I,TEXT("magicPenetrationPercent"))+E->Effect(*I,TEXT("magicPenetrationPercent"));
        }
        if(const auto* I=Item?Item:M->Equipped())
        {
            if(bFiredRound)
            {
                Shot.Dealer=ColdSteelCombat::Dealer(Shooter->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>(),I);
                if(Shot.Dealer.Enabled)Shot.DealerSourceInstance=I->InstanceId;
                Shot.ArmorPenetration=FMath::Clamp(Shot.ArmorPenetration+M->AmmoArmorPenetration(*I),0.f,1.f);
                if(const auto* Ammo=M->AmmoType(M->AmmoDefinitionFor(*I)))
                {Shot.AmmoPoisonStacks=Ammo->PoisonStacks;Shot.AmmoBleedStacks=Ammo->BleedStacks;}
            }
            if(Shot.ItemDefinition.IsEmpty())Shot.ItemDefinition=I->Definition;
            if(Shot.ItemInstance.IsEmpty())Shot.ItemInstance=I->InstanceId;
            if(I->Definition==ThunderHammer::Definition)
            {
                Shot.HammerLightning=M->LightningStats();ThunderHammerRunes::Configure(Shot.HammerLightning,I);
                Shot.bHammerRuneContact=Shot.HammerLightning.RuneElectrifyChance>0.f;
            }
            const auto Wager=ColdSteelCombat::BigBlind(Shooter->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>(),I);
            if(Wager.Enabled)
            {Shot.WagerCriticalBonusPerStack=Wager.CriticalBonusPerStack;Shot.WagerSeconds=Wager.Seconds;Shot.WagerMaxStacks=Wager.MaxStacks;}
            const auto Calm=ColdSteelCombat::Calm(Shooter->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>(),I);
            if(Calm.Enabled)
            {
                Shot.ComposureStabilityPerStack=Calm.StabilityPerStack;
                Shot.ComposureRecoilReductionPerStack=Calm.RecoilReductionPerStack;
                Shot.ComposureSeconds=Calm.Seconds;Shot.ComposureMaxStacks=Calm.MaxStacks;
            }
            Shot.bMelee=ColdSteelInventory::IsMeleeWeapon(*I);
            // 武器自带的暴击伤害加成（items 定义 critDamageBonus）与暴击技能倍率相加后，
            // 在 ColdSteelSkillModel 里只乘一次（要害或随机暴击同一击不叠加）。
            Shot.CriticalDamageBonus+=FMath::Max(0.,ColdSteelInventory::Number(*I,TEXT("critDamageBonus")));
            if(ColdSteelInventory::IsBow(*I))
                if(const auto* Gunsmith=Shooter->GetGameInstance()->GetSubsystem<UGunsmithSystem>())
                    Shot.CriticalDamageBonus+=Gunsmith->Calculate(I->Definition,Gunsmith->Installed(*I)).Bow.CriticalDamageBonus;
            // 近战默认按锐器折算削韧（配重锤等钝击动作由攻击端覆盖）；其余按冲击。
            Shot.AttackForm=ColdSteelInventory::IsTwoHandedBlunt(*I)?EMonsterAttackForm::Blunt:
                Shot.bMelee?EMonsterAttackForm::Blade:EMonsterAttackForm::Impact;
            if(Shot.bMelee)
            {
                const auto Melee=ColdSteelMelee::Evaluate(*I,M);
                Shot.DamagePanel=Melee.DamageParts;
                if(I->Definition==TEXT("ue_forged_steel_greatsword"))
                    if(const auto* Gunsmith=Shooter->GetGameInstance()->GetSubsystem<UGunsmithSystem>())
                    {
                        const auto Parts=Gunsmith->Installed(*I);
                        Shot.bExecutionerBlade=Parts.FindRef(TEXT("blade_1"))==TEXT("executioner_blade");
                        const FString Pommel=Parts.FindRef(TEXT("pommel"));
                        Shot.bRingChainPommel=Pommel==TEXT("ring_chain_pommel");
                        Shot.bFishtailPommel=Pommel==TEXT("fishtail_pommel");
                    }
                if(I->Definition==TEXT("ue_tactical_hatchet"))
                    if(const auto* Gunsmith=Shooter->GetGameInstance()->GetSubsystem<UGunsmithSystem>())
                    {
                        const auto Parts=Gunsmith->Installed(*I);
                        Shot.bGhostScytheContact=Parts.FindRef(TEXT("blade_1"))==TEXT("hatchet_ghost_scythe");
                        const auto Charm=Parts.FindRef(TEXT("lanyard"));
                        Shot.bEmberWedge=Charm==TEXT("hatchet_lanyard_ember_wedge");
                        Shot.bRavenWhistle=Charm==TEXT("hatchet_lanyard_raven_whistle");
                    }
                if(I->Definition==TEXT("ue_highland_claymore"))
                    if(const auto* Gunsmith=Shooter->GetGameInstance()->GetSubsystem<UGunsmithSystem>())
                    {
                        const FString Material=Gunsmith->Installed(*I).FindRef(TEXT("blade_material"));
                        Shot.bBlackthornCriticalWeakness=Material==TEXT("blackthorn_steel");
                        Shot.bWhitehartCriticalVulnerability=Material==TEXT("whitehart_mithril");
                    }
                if(I->Definition==TEXT("ue_frost_crystal_sword"))
                {
                    Shot.HitHealthReturnRatio=float(Melee.Modifiers.HitHealthReturnRatio);
                    Shot.HitManaReturnRatio=float(Melee.Modifiers.HitManaReturnRatio);
                }
                if(I->Definition==TEXT("ue_rune_sword"))
                {
                    Shot.TimeSandEchoRatio=float(Melee.Modifiers.TimeSandEchoRatio);
                    Shot.TimeSandEchoDelay=float(Melee.Modifiers.TimeSandEchoDelay);
                    Shot.TimeSandCooldownReward=.5f+float(Melee.Modifiers.CooldownReduceSecondsPerHit);
                }
                // Captured from this attack's item on both client and authority;
                // never exported to the character's global spell critical stats.
                Shot.CriticalChance+=float(Melee.Modifiers.MeleeCriticalChanceAdd);
                Shot.CriticalDamageBonus+=float(Melee.Modifiers.MeleeCriticalDamageBonus);
                // Two-handed passive crit is already included by Derived(crit).
                // One-handed parts belong to this attack's blade, never the other hand.
                if(ColdSteelInventory::IsOneHandedMelee(*I)||KukriEnchantment::Supports(*I))
                    Shot.CriticalChance+=float(Melee.Modifiers.CriticalChanceAdd);
                if(Melee.Modifiers.ZhenmoSeconds>0.)Shot.ZhenmoSourceInstance=I->InstanceId;
                Shot.ArmorPenetration=FMath::Clamp(Shot.ArmorPenetration+float(Melee.Modifiers.PhysicalArmorPenetration),0.f,1.f);
                Shot.ToughnessDamageMultiplier=Melee.Modifiers.ToughnessDamage;
                Shot.MeleeHitBleedStacks=Melee.Modifiers.MeleeHitBleedStacks;
                Shot.QuickCombatTigerRoarToughnessBonus=Melee.Modifiers.QuickCombatTigerRoarToughnessBonus;
                Shot.QuickCombatTigerRoarSeconds=Melee.Modifiers.QuickCombatTigerRoarSeconds;
                Shot.QuickCombatPhysicalVulnerabilityBonus=Melee.Modifiers.QuickCombatPhysicalVulnerabilityBonus;
                Shot.QuickCombatPhysicalVulnerabilitySeconds=Melee.Modifiers.QuickCombatPhysicalVulnerabilitySeconds;
                Shot.QuickCombatRuneVulnerability=Melee.Modifiers.QuickCombatRuneVulnerability;
                Shot.QuickCombatRuneVulnerabilitySeconds=Melee.Modifiers.QuickCombatRuneVulnerabilitySeconds;
                if(PojunGrip::UsesHammerMotion(*I))
                {
                    Shot.bQuickCombatBreakingSeal=AncientSealSeat::Installed(*I);
                    const auto Blunt=ColdSteelTool::Evaluate(*I,M);
                    Shot.DamagePanel=Blunt.Damage;
                    Shot.ToughnessDamageMultiplier=float(Blunt.ToughnessDamage);
                    Shot.BluntRuneVulnerability=float(Melee.Modifiers.RuneVulnerability);
                    Shot.BluntRuneVulnerabilitySeconds=float(Melee.Modifiers.RuneVulnerabilitySeconds);
                }
                if(const auto* E=Shooter->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();E&&!bFiredRound)
                {
                    if(E->Effect(*I,TEXT("electrifiedMelee"))>0.)
                    {
                        Shot.ElectrifiedRadiusCM=E->Effect(*I,TEXT("electrifiedRadiusM"))*100.;
                        Shot.ElectrifiedMinLevel=int32(E->Effect(*I,TEXT("electrifiedMinLevel")));
                    }
                    const float Speed=E->Effect(*I,TEXT("berserkSpeedPerStack"));
                    const float Period=E->Effect(*I,TEXT("berserkDecaySeconds"));
                    const int32 Limit=int32(E->Effect(*I,TEXT("berserkMaxStacks")));
                    if(E->Effect(*I,TEXT("berserkMelee"))>0.&&Speed>0.f&&Period>0.f&&Limit>0)
                    {Shot.BerserkSourceInstance=I->InstanceId;Shot.BerserkSpeedPerStack=Speed;Shot.BerserkDecaySeconds=Period;Shot.BerserkMaxStacks=Limit;}
                }
            }
            else if(ColdSteelInventory::IsBow(*I))
                Shot.DamagePanel=ColdSteelWeaponStats::DamageParts(*I,M,ColdSteelInventory::Number(*I,TEXT("full_damage"),69));
            else if(ColdSteelInventory::IsStaff(*I))
                Shot.DamagePanel=ColdSteelWeaponStats::DamageParts(*I,M,ColdSteelInventory::Number(*I,TEXT("melee_damage"),3));
            else if(const auto* G=Shooter->GetGameInstance()->GetSubsystem<UGunsmithSystem>();G&&G->Weapon(I->Definition))
            {
                const auto Installed=G->Installed(*I);
                const auto Stats=G->Calculate(I->Definition,Installed);
                if(bFiredRound)
                {
                    Shot.CriticalDamageBonus+=float(Stats.FirearmCriticalDamageBonus);
                    Shot.FirearmCriticalStunSeconds=float(Stats.CriticalStunSeconds);
                }
                Shot.bSilentLethalShot=bFiredRound&&SniperSuppressorAssets::Supports(I->Definition)
                    &&Installed.FindRef(TEXT("muzzle"))==SniperSuppressorAssets::Part;
                Shot.DamagePanel=ColdSteelWeaponStats::DamageParts(*I,M,Stats.Damage);
                if(bFiredRound&&!G->IsMelee(I->Definition)&&!G->IsTool(I->Definition)&&!G->IsStaff(I->Definition)&&!G->IsBow(I->Definition))
                    if(const auto* E=Shooter->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
                    {
                        const double Radius=E->Effect(*I,TEXT("shatterRadiusM"));
                        const double Scale=E->Effect(*I,TEXT("shatterDamageScale"));
                        if(E->Effect(*I,TEXT("shatterBullet"))>0.&&Radius>0.&&Scale>0.)
                        {Shot.ShatterRadiusCM=Radius*100.;Shot.ShatterDamageScale=Scale;Shot.BulletSpeedCM=Stats.Speed*100.;}
                    }
            }
        }
    }
    if(Shot.bMelee&&Shot.ItemDefinition==TEXT("ue_kukri"))
        if(auto* Pendant=Shooter->FindComponentByClass<UKukriRelentlessComponent>())Pendant->CaptureAttack(Shot.MasteryAttackSerial,M);
    return Shot;
}
ColdSteelSkills::FColdSteelNetHitForward& ColdSteelSkills::NetHitForward()
{
    static FColdSteelNetHitForward Instance=nullptr;
    return Instance;
}
void ColdSteelSkills::AwardKillByOwner(UGameInstance* GameInstance,AController* Instigator,AActor* Victim,int64 ExperienceReward)
{
    const auto* Killer=Cast<AFPSGAMECharacter>(Instigator?Instigator->GetPawn():nullptr);
    if(!GameInstance||!Victim||!Victim->HasAuthority()||!Killer||!Killer->IsPlayerControlled())return;
    if(auto* Model=ColdSteelAuthority::ForPawn(Killer))Model->AwardKill(Victim,ExperienceReward);
}
void ColdSteelSkills::NotifyKillByOwner(UGameInstance* GameInstance,AController* Instigator,AActor* Victim)
{
    if(!GameInstance||!Victim||!Victim->HasAuthority())return;
    FEclipseBowImpact::OnDeath(Victim);
    const auto* Killer=Cast<AFPSGAMECharacter>(Instigator?Instigator->GetPawn():nullptr);
    if(!Killer||Killer==Victim)return;
    UColdSteelStatusModel* Model=ColdSteelAuthority::ForPawn(Killer);
    if(Model)Model->ApplyKillStaminaRecovery(Victim);
    if(auto* Haste=Killer->FindComponentByClass<UFPSLightningHasteComponent>())Haste->ObserveKill(Victim);
    if(auto* Mark=Victim->FindComponentByClass<UIlluminationMarkComponent>())Mark->ObserveKill(Killer);
}
void ColdSteelSkills::GrantBerserkOnWeaponHit(AActor* Shooter,const FColdSteelSkillShot& Shot)
{
    if(!Shooter||!Shooter->HasAuthority()||!Shot.bMelee||Shot.BerserkSourceInstance.IsEmpty()
        ||Shot.BerserkSpeedPerStack<=0.f||Shot.BerserkDecaySeconds<=0.f||Shot.BerserkMaxStacks<=0)return;
    UColdSteelStatusModel* Model=SkillCombatModel(Shooter);
    const auto* Held=Model?Model->ActiveProductionTool():nullptr;
    if(!Held&&Model)Held=Model->ActiveKukriWeapon();   // (the lone off-hand blade too)
    if(!Held||Held->InstanceId!=Shot.BerserkSourceInstance)return;
    if(auto* Status=UCombatStatusFormula::GetOrAdd(Shooter))
        Status->AddBerserk(Shot.BerserkSpeedPerStack,Shot.BerserkDecaySeconds,Shot.BerserkMaxStacks);
}
float ColdSteelSkills::ApplyHit(AActor* Shooter,const FHitResult& Hit,float Damage,const FVector& Direction,const FColdSteelSkillShot& Shot,FWeaponDamageResult* Result,FKukriPairedHeavyHit* PairedHeavy)
{
    if(PairedHeavy&&Shooter&&!Shooter->HasAuthority())
    {AColdSteelPlayerState::ForwardPairedHeavyHit(Shooter,Hit,Damage,Direction,Shot,*PairedHeavy);return 0.f;}
    // M3 联机：客户端命不本地结算，转发权威服务器（枪械/近战/法术共用此汇入点）。
    if(Shooter&&!Shooter->HasAuthority()&&NetHitForward()&&NetHitForward()(Shooter,Hit,Damage,Direction,Shot))return 0.f;
    if(Result)*Result={};
    // Same scope used by BowArrow: defer this victim's group alarm until the
    // actual damage/death result. A surviving victim still broadcasts normally.
    // Leave an existing outer bow scope intact when this shot has no modifier.
    TOptional<MonsterDamageAlert::FScopedSilentShot> SilentShot;
    if(Shot.bSilentLethalShot&&!Shot.bRicochet)SilentShot.Emplace(Hit.GetActor());
    // 联机：服务端结算远端玩家命中时用影子档案（GetNetShadowProfile），主机/单机回退单例。
    UColdSteelStatusModel* M=SkillCombatModel(Shooter);
    if (M)
    {
        // Detached restraint health is not a full monster contact. This also
        // keeps delayed/invalid part reports out of torso damage and procs.
        if(ABoundCongregate::IsTentaclePart(Hit))
            return M->ApplySkillWeaponHit(Shooter,Hit,Damage,Direction,Shot,Result);
        // Capture eligibility before the original victim dies. This common fired-shot
        // path covers flying, hitscan, blocked-muzzle and either dual-wield hand.
        const bool bShatter=Shooter->HasAuthority()&&!Shot.bRicochet&&Shot.ShatterRadiusCM>0.f
            &&UFPSBallisticsComponent::IsShatterEnemy(Hit.GetActor(),Shooter);
        FWeaponDamageResult Receipt;
        bool bTorchContact=Shooter->HasAuthority()&&Shot.bMeleeStrike&&!Shot.bRicochet&&
            Shot.ItemDefinition==ColdSteelInventory::WoodenTorchDefinition&&
            (Shot.AttackMeta==0||Shot.AttackMeta==0x80)&&UFPSMeleeLightningComponent::IsEnemy(Hit.GetActor(),Shooter);
        if(bTorchContact&&Shot.AttackMeta==0x80)
        {
            const auto* Off=M->Equipped(M->ActiveOffhandSlot());
            const auto* StrikingTorch=ColdSteelInventory::QuickTorch(M->Equipped(),Off);
            bTorchContact=StrikingTorch&&StrikingTorch->InstanceId==Shot.ItemInstance;
        }
        const bool bRingChain=Shot.bRingChainPommel&&Shot.bMelee&&!Shot.bRicochet
            &&Shot.AttackMeta>=1&&Shot.AttackMeta<=3&&Shot.AttackForm==EMonsterAttackForm::Blade
            &&Shooter->HasAuthority()&&UFPSMeleeLightningComponent::IsEnemy(Hit.GetActor(),Shooter);
        const bool bElectrified=Shot.bMelee&&Shot.ElectrifiedRadiusCM>0.f&&Shot.ElectrifiedMinLevel>0
            &&Shooter->HasAuthority()&&UFPSMeleeLightningComponent::IsEnemy(Hit.GetActor(),Shooter);
        const bool bBerserk=Shot.bMelee&&Shot.BerserkMaxStacks>0&&Damage>0.f
            &&Shooter->HasAuthority()&&UFPSMeleeLightningComponent::IsEnemy(Hit.GetActor(),Shooter);
        const bool bRunebound=Shot.bMelee&&Shot.AttackForm==EMonsterAttackForm::Blunt&&
            Shot.ItemDefinition==RuneboundHammer::Definition&&Shooter->HasAuthority()&&
            UFPSMeleeLightningComponent::IsEnemy(Hit.GetActor(),Shooter);
        const bool bWolf=Shot.ItemDefinition==TEXT("ue_kukri")&&Shot.bMelee&&!Shot.bRicochet&&Shooter->HasAuthority()
            &&UFPSMeleeLightningComponent::IsEnemy(Hit.GetActor(),Shooter);
        const bool bPairedEnemy=PairedHeavy&&Shooter->HasAuthority()&&UFPSMeleeLightningComponent::IsEnemy(Hit.GetActor(),Shooter);
        const bool bCrystal=Shot.ItemDefinition==TEXT("ue_frost_crystal_sword")&&Shot.bMelee&&!Shot.bRicochet
            &&(Shot.HitHealthReturnRatio>0.f||Shot.HitManaReturnRatio>0.f)&&Shooter->HasAuthority()
            &&UFPSMeleeLightningComponent::IsEnemy(Hit.GetActor(),Shooter);
        float CrystalHealth=0.f,CrystalMaxHealth=0.f;FText CrystalName;
        if(bCrystal)if(const auto* Combat=Hit.GetActor()->FindComponentByClass<UMonsterCombatComponent>())
            Combat->GetVitals(CrystalHealth,CrystalMaxHealth,CrystalName);
        float WolfHealth=0.f,WolfMaxHealth=0.f;FText WolfName;
        if(bWolf)if(const auto* Combat=Hit.GetActor()->FindComponentByClass<UMonsterCombatComponent>())Combat->GetVitals(WolfHealth,WolfMaxHealth,WolfName);
        TSharedPtr<FEclipseBowShot> BowBash;
        if (Shot.bMeleeStrike && (Shot.AttackMeta & 0x80) && Shot.ItemDefinition == TEXT("bow_frontier_compound"))
            BowBash = FEclipseBowShot::Capture(Cast<APawn>(Shooter));
        FEclipseBowImpact BashImpact(BowBash.Get(), Hit.GetActor());
        const float Applied=M->ApplySkillWeaponHit(Shooter,Hit,Damage,Direction,Shot,Result?Result:&Receipt,PairedHeavy);
        BashImpact.Confirm(Applied);
        if(bTorchContact)
        {
            if(auto* Torch=Shooter->FindComponentByClass<UWoodenTorchComponent>())Torch->EnemyContact(Hit);
            if(Applied>0.f&&!(Result?Result->bKilled:Receipt.bKilled)&&FMath::FRand()<.25f)
                if(auto* Status=UCombatStatusFormula::GetOrAdd(Hit.GetActor()))
                    Status->AddBurn(Shooter,M->Derived(TEXT("matk")),1,5.f);
        }
        if(bRingChain&&Applied>0.f)
            if(auto* Sword=Shooter->FindComponentByClass<URuneSwordComponent>())
                Sword->ConfirmRingChainHit(Shot.ItemInstance,Shot.GenericMeleeSerial?Shot.GenericMeleeSerial:Shot.GuardAttackSerial);
        if(Shot.bMeleeStrike&&Shooter->GetNetMode()==NM_ListenServer&&(Applied>0.f||(Result?Result->bKilled:Receipt.bKilled)))
            if(const auto* Local=Cast<APawn>(Shooter);Local&&Local->IsLocallyControlled())
                UKukriWeaponComponent::PublishBladeHit(Shooter,Hit,Shot);
        if(Applied>0.f && Shooter->HasAuthority() && Shot.AttackMeta==0x10 && Shot.MeleeDamagePhase==0
            && Shot.ItemDefinition==TEXT("ue_tactical_hatchet") && !Shot.bRicochet)
            if(auto* Kukri=Shooter->FindComponentByClass<UKukriWeaponComponent>())
            {
                if(!PairedHeavy||PairedHeavy->Applied[0]>0.f)Kukri->ConfirmFalconHook(Shot,Hit);
                if(PairedHeavy&&PairedHeavy->Applied[1]>0.f)
                    Kukri->ConfirmFalconHook(PairedHeavy->Second.Shot,PairedHeavy->Second.Hit);
            }
        // Every actual enemy contact contributes; overkill cannot restore resources.
        if(bCrystal&&CrystalHealth>0.f&&Applied>0.f)
        {
            float Remaining=0.f;
            if(IsValid(Hit.GetActor()))
                if(const auto* Combat=Hit.GetActor()->FindComponentByClass<UMonsterCombatComponent>())
                    Combat->GetVitals(Remaining,CrystalMaxHealth,CrystalName);
            const float Effective=FMath::Min(Applied,FMath::Clamp(CrystalHealth-Remaining,0.f,CrystalHealth));
            M->RestoreMagicCrystalResources(Shooter,Effective*Shot.HitHealthReturnRatio,Effective*Shot.HitManaReturnRatio);
        }
        if(bWolf&&WolfHealth>0.f&&Applied>0.f)
        {
            const auto ConfirmBlade=[&](const FColdSteelSkillShot& Blade,float Share)
            {
                const float Effective=Share*FMath::Min(Applied,WolfHealth)/Applied;
                if(auto* Rune=Shooter->FindComponentByClass<UKukriBerserkerComponent>())Rune->ConfirmHit(Blade,Effective);
                if(auto* Rune=Shooter->FindComponentByClass<UKukriFrostRavenComponent>())Rune->ConfirmHit(Blade,Hit.GetActor(),Effective);
                if(auto* Pendant=Shooter->FindComponentByClass<UKukriRelentlessComponent>())Pendant->ConfirmHit(Blade,Effective);
            };
            ConfirmBlade(Shot,PairedHeavy?PairedHeavy->Applied[0]:Applied);
            if(PairedHeavy)ConfirmBlade(PairedHeavy->Second.Shot,PairedHeavy->Applied[1]);
        }
        if(bRunebound&&(Applied>0.f||(Result?Result->bKilled:Receipt.bKilled)))
            if(auto* Tool=Shooter->FindComponentByClass<UProductionToolComponent>())Tool->RecordRuneboundHit(Shot,Hit);
        if(bBerserk)GrantBerserkOnWeaponHit(Shooter,Shot);
        if(bPairedEnemy&&PairedHeavy->Second.Shot.BerserkMaxStacks>0&&PairedHeavy->Second.Damage>0.f)
            GrantBerserkOnWeaponHit(Shooter,PairedHeavy->Second.Shot);
        if(bElectrified&&Damage>0.f)
            if(auto* Lightning=Shooter->FindComponentByClass<UFPSMeleeLightningComponent>())
            {
                // One roll for a nonlethal melee contact. A direct melee kill
                // bypasses the roll; later lightning kill fan-out never rolls.
                const bool bMeleeKill=Result?Result->bKilled:Receipt.bKilled;
                if(bMeleeKill||FMath::FRand()<.25f)
                    Lightning->QueueDischarge(Hit,Shot.ElectrifiedRadiusCM,Shot.ElectrifiedMinLevel,Shot.HammerLightning);
            }
        if(bPairedEnemy&&PairedHeavy->Second.Damage>0.f)
        {
            const auto& Other=PairedHeavy->Second.Shot;
            if(Other.ElectrifiedRadiusCM>0.f&&Other.ElectrifiedMinLevel>0)
                if(auto* Lightning=Shooter->FindComponentByClass<UFPSMeleeLightningComponent>())
                    if((Result?Result->bKilled:Receipt.bKilled)||FMath::FRand()<.25f)
                        Lightning->QueueDischarge(PairedHeavy->Second.Hit,Other.ElectrifiedRadiusCM,Other.ElectrifiedMinLevel,Other.HammerLightning);
        }
        if(bShatter)
            if(auto* Ballistics=Shot.BulletSource.IsValid()?Shot.BulletSource.Get():Shooter->FindComponentByClass<UFPSBallisticsComponent>())
                Ballistics->QueueShatter(Hit,Shot,Result?*Result:Receipt);
        return Applied;
    }
    const auto* Pawn=Cast<APawn>(Shooter);
    return UGameplayStatics::ApplyPointDamage(Hit.GetActor(),Damage,Direction,Hit,Pawn?Pawn->GetController():nullptr,Shooter,nullptr);
}

bool ColdSteelSkills::IsMasteryTrainingTarget(AActor* Shooter,AActor* Target)
{
    const auto* Combat=Target?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    return Combat&&!Combat->IsDead()&&!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining"))
        &&UFPSMeleeLightningComponent::IsEnemy(Target,Shooter);
}
