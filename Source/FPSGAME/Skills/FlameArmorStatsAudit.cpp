#include "SkillNetworkAuditCommandlet.h"
#include "FPSFireMagicComponent.h"
#include "FPSFireballComponent.h"
#include "ColdSteelSkillRules.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/NurseZombie.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

int32 USkillNetworkAuditCommandlet::RunFlameArmorStatsAudit(const FString& Params)
{
    const FString Original=FCommandLine::Get(),Slot=TEXT("FlameArmorStatsAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("FlameArmorStatsAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("FlameArmorStatsAuditWorld"));
    auto* World=GI->GetWorld();auto* Host=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Host||!Host->IsAudit()||Host->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 2;
    int32 Failures=0;TArray<TSharedPtr<FJsonValue>> Rows,Levels;
    const auto Check=[&](bool OK,const FString& Name)
    {
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("case"),Name);R->SetBoolField(TEXT("passed"),OK);
        Rows.Add(MakeShared<FJsonValueObject>(R));Failures+=!OK;
        UE_LOG(LogTemp,Display,TEXT("FLAME_ARMOR_STATS %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),*Name);
    };
    auto Seed=Host->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();Seed.DungeonRun={};
    Seed.Hotbar.Init(TEXT(""),4);Seed.HotbarDefinitions.Init(TEXT(""),4);for(auto& B:Seed.QuickBindings)B={};
    for(auto& S:Seed.Skills){S.Value.Level=1;S.Value.Experience=0;}Seed.FlameArmorCooldown=Seed.FlameArmorCooldownDuration=0;
    auto* Shadow=Host->CreateShadowModel(Seed);auto* PC=World->SpawnActor<ASkillAuditRemoteController>();auto* PS=World->SpawnActor<AColdSteelPlayerState>();
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,500),FRotator::ZeroRotator);
    PS->SetOwner(PC);PC->SetPlayerState(PS);PC->Possess(Pawn);Pawn->SetPlayerState(PS);PS->ShadowModel=Shadow;
    Pawn->NetShadowProfile=Shadow;Shadow->CurrentPawn=Pawn;Shadow->Current.Mana=Shadow->Derived(TEXT("maxMp"));
    auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health->Health=Health->MaxHealth;
    auto* Fire=Pawn->FindComponentByClass<UFPSFireMagicComponent>();auto* Status=UCombatStatusFormula::GetOrAdd(Pawn);
    const auto Definition=Shadow->FlameArmorSkill;
    auto Previous=Shadow->FireMagicStats(TEXT("flameArmor"),1);
    for(int32 L=1;L<=Definition.MaxLevel;++L)
    {
        Shadow->Current.Skills.FindOrAdd(TEXT("flameArmor")).Level=L;
        const auto C=Shadow->FireMagicStats(TEXT("flameArmor"));const auto Preview=Shadow->FireMagicStats(TEXT("flameArmor"),L);
        Check(C.Damage>=Previous.Damage&&C.AuraDamage>=Previous.AuraDamage&&C.AuraRadius>=Previous.AuraRadius&&C.Duration>=Previous.Duration&&C.ManaCost>=Previous.ManaCost,
            FString::Printf(TEXT("level %d growth remains monotonic"),L));
        Check(C.Damage==Preview.Damage&&C.AuraDamage==Preview.AuraDamage&&C.Duration==Preview.Duration&&C.ManaCost==Shadow->SpellManaCost(TEXT("flameArmor"),L),
            FString::Printf(TEXT("level %d runtime and next-level preview share stats and mana"),L));
        auto R=MakeShared<FJsonObject>();R->SetNumberField(TEXT("level"),L);R->SetNumberField(TEXT("weapon_damage"),C.Damage);R->SetNumberField(TEXT("aura_damage"),C.AuraDamage);
        R->SetNumberField(TEXT("radius_cm"),C.AuraRadius);R->SetNumberField(TEXT("duration"),C.Duration);R->SetNumberField(TEXT("mana"),C.ManaCost);R->SetNumberField(TEXT("cooldown"),C.Cooldown);R->SetNumberField(TEXT("tick"),C.TickSeconds);
        Levels.Add(MakeShared<FJsonValueObject>(R));Previous=C;
    }
    const auto Low=Shadow->FireMagicStats(TEXT("flameArmor"),1),High=Shadow->FireMagicStats(TEXT("flameArmor"),20);
    Check(FMath::IsNearlyEqual(Low.AuraRadius,204.f)&&FMath::IsNearlyEqual(High.AuraRadius,375.f)&&Low.Duration==12&&High.Duration==30&&Low.ManaCost==40&&High.ManaCost==80&&Low.Cooldown==60&&High.Cooldown==60,
        TEXT("shipped config endpoints: radius 204-375cm duration 12-30s mana 40-80 cooldown 60s"));
    struct FField {const TCHAR* Name;float FFireMagicTuning::* Input;float FFireMagicCast::* Output;float Delta;bool Decreases=false;};
    const FField Fields[]={
        {TEXT("damageBase"),&FFireMagicTuning::DamageBase,&FFireMagicCast::Damage,10},
        {TEXT("damagePerLevel"),&FFireMagicTuning::DamagePerLevel,&FFireMagicCast::Damage,10},
        {TEXT("magicBase"),&FFireMagicTuning::MagicBase,&FFireMagicCast::Damage,10},
        {TEXT("magicPerLevel"),&FFireMagicTuning::MagicPerLevel,&FFireMagicCast::Damage,10},
        {TEXT("intelligenceBase"),&FFireMagicTuning::IntelligenceBase,&FFireMagicCast::Damage,10},
        {TEXT("intelligencePerLevel"),&FFireMagicTuning::IntelligencePerLevel,&FFireMagicCast::Damage,10},
        {TEXT("auraDamageBase"),&FFireMagicTuning::AuraDamageBase,&FFireMagicCast::AuraDamage,10},
        {TEXT("auraDamagePerLevel"),&FFireMagicTuning::AuraDamagePerLevel,&FFireMagicCast::AuraDamage,10},
        {TEXT("auraMagicBase"),&FFireMagicTuning::AuraMagicBase,&FFireMagicCast::AuraDamage,10},
        {TEXT("auraMagicPerLevel"),&FFireMagicTuning::AuraMagicPerLevel,&FFireMagicCast::AuraDamage,10},
        {TEXT("auraIntelligenceBase"),&FFireMagicTuning::AuraIntelligenceBase,&FFireMagicCast::AuraDamage,10},
        {TEXT("auraIntelligencePerLevel"),&FFireMagicTuning::AuraIntelligencePerLevel,&FFireMagicCast::AuraDamage,10},
        {TEXT("auraRadiusBase"),&FFireMagicTuning::AuraRadiusBase,&FFireMagicCast::AuraRadius,10},
        {TEXT("auraRadiusPerLevel"),&FFireMagicTuning::AuraRadiusPerLevel,&FFireMagicCast::AuraRadius,10},
        {TEXT("unitsToCM"),&FFireMagicTuning::UnitsToCM,&FFireMagicCast::AuraRadius,1},
        {TEXT("durationBase"),&FFireMagicTuning::DurationBase,&FFireMagicCast::Duration,1},
        {TEXT("durationGrowth"),&FFireMagicTuning::DurationGrowth,&FFireMagicCast::Duration,19},
        {TEXT("manaBase"),&FFireMagicTuning::ManaBase,&FFireMagicCast::ManaCost,10},
        {TEXT("manaGrowth"),&FFireMagicTuning::ManaGrowth,&FFireMagicCast::ManaCost,19},
        {TEXT("cooldown"),&FFireMagicTuning::Cooldown,&FFireMagicCast::Cooldown,10},
        {TEXT("cooldownReduction"),&FFireMagicTuning::CooldownReduction,&FFireMagicCast::Cooldown,5,true},
        {TEXT("tickSeconds"),&FFireMagicTuning::TickSeconds,&FFireMagicCast::TickSeconds,.05f}};
    for(const auto& F:Fields)
    {
        Shadow->FlameArmorSkill=Definition;Shadow->FlameArmorSkill.FireMagic.*(F.Input)+=F.Delta;
        const auto Changed=Shadow->FireMagicStats(TEXT("flameArmor"),20);
        Check(F.Decreases?Changed.*(F.Output)<High.*(F.Output):Changed.*(F.Output)>High.*(F.Output),FString(TEXT("tuning consumed: "))+F.Name);
    }
    Shadow->FlameArmorSkill=Definition;Shadow->Current.Skills.FindOrAdd(TEXT("flameArmor")).Level=1;
    Shadow->Current.FlameArmorCooldown=0;const float Before=Shadow->Snapshot().Mana;
    Status->SetStatusImmune(true);
    Check(!Shadow->BeginFireMagicCast(Low)&&Shadow->Snapshot().Mana==Before,TEXT("authority immune prepare rejects without cost"));
    Status->SetStatusImmune(false);Check(Shadow->BeginFireMagicCast(Low),TEXT("authority prepare succeeds without immunity"));
    PS->PendingCastSkill=TEXT("flameArmor");PS->PendingCastPawn=Pawn;PS->PendingIdentifiedCastId=41;PS->PendingCastPaidMana=Before-Shadow->Snapshot().Mana;PS->PendingFireMagicStats=Low;
    Status->SetStatusImmune(true);FColdSteelNetCastRequest Req;Req.SkillId=TEXT("flameArmor");Req.Phase=1;Req.CastId=41;PS->ExecuteCastRequest(Req);
    Check(Fire->ArmorTime==0&&PS->PendingCastSkill.IsNone()&&Shadow->Snapshot().Mana==Before&&Shadow->FireMagicCooldown(TEXT("flameArmor"))==0,
        TEXT("immunity gained during windup rejects release and refunds server reservation"));
    Fire->CommittedSkill=TEXT("flameArmor");Fire->CastSnapshot=Low;Fire->ReleaseAtContact();
    Check(Fire->ArmorTime==0&&Fire->CommittedSkill.IsNone(),TEXT("local release rechecks immunity"));Status->SetStatusImmune(false);
    const float FullMana=Host->Derived(TEXT("maxMp"));Host->Current.Mana=FullMana-10;Host->Current.FlameArmorCooldown=60;
    Fire->Hands()->RecordGesturePayment(10,0,true);Fire->CommittedSkill=TEXT("flameArmor");Fire->CancelPending();Fire->CancelPending();
    Check(Host->Snapshot().Mana==FullMana&&Host->FireMagicCooldown(TEXT("flameArmor"))==0,
        TEXT("menu/direct cancel refunds unreleased armor exactly once"));
    Shadow->FlameArmorSkill.FireMagic.bRequiresStaff=true;
    Check(!Shadow->BeginFireMagicCast(Shadow->FireMagicStats(TEXT("flameArmor"))),TEXT("requiresStaff configuration is enforced"));Shadow->FlameArmorSkill=Definition;

    Req.CastId=42;Fire->NetRelease(Pawn,Req,Shadow,Low);Shadow->Current.Skills.FindOrAdd(TEXT("flameArmor")).Level=20;
    Check(Fire->ArmorSnapshot.Damage==Low.Damage&&Fire->ArmorSnapshot.Duration==Low.Duration&&Fire->NetArmor.Cast.Damage==Low.Damage,
        TEXT("active cast keeps original stats after skill level changes"));
    Req.CastId=43;Fire->NetRelease(Pawn,Req,Shadow,Shadow->FireMagicStats(TEXT("flameArmor")));
    Check(Fire->NetArmor.Cast.Damage==High.Damage&&Fire->ArmorTime==High.Duration&&Host->FireMagicProgress(TEXT("flameArmor")).Level==1,
        TEXT("new guest cast uses guest level 20 instead of host level 1"));
    auto* Target=World->SpawnActor<ANurseZombie>(FVector(3000,0,500),FRotator::ZeroRotator);Target->Health=Target->MaxHealth=100000;
    Fire->ArmorSnapshot.CriticalChance=0;const float HP=Target->Health;Fire->OnWeaponHit(Target,Target->GetActorLocation());const float HighDamage=HP-Target->Health;
    Req.CastId=44;Fire->NetRelease(Pawn,Req,Shadow,Low);Fire->ArmorSnapshot.CriticalChance=0;Target->Health=100000;
    Fire->OnWeaponHit(Target,Target->GetActorLocation());const float LowDamage=100000-Target->Health;
    Check(HighDamage>LowDamage&&LowDamage>0,TEXT("higher-level weapon bonus increases actual target health loss"));Fire->EndArmor(false);

    const FVector Feet=Pawn->GetActorLocation()-FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-5);
    Target->SetActorLocation(Feet+FVector(300,0,Target->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()));Target->Health=100000;
    Req.CastId=45;Fire->NetRelease(Pawn,Req,Shadow,Low);Fire->ArmorSnapshot.CriticalChance=0;Fire->TickArmor(.5f);
    Check(Target->Health==100000,TEXT("level 1 aura cannot reach a target at three metres"));Fire->EndArmor(false);
    Req.CastId=46;Fire->NetRelease(Pawn,Req,Shadow,High);Fire->ArmorSnapshot.CriticalChance=0;Fire->TickArmor(.25f);
    Check(Target->Health==100000,TEXT("aura does not hit before configured half-second interval"));Fire->TickArmor(.25f);
    Check(Target->Health<100000,TEXT("level 20 aura reaches three metres on the configured tick"));Fire->EndArmor(false);
    Target->SetActorLocation(FVector(3000,0,500));

    const auto RewardCheck=[&](int32 FFireMagicTuning::* Field,const TCHAR* Name,FFireMagicRewards Reward)
    {
        Shadow->Current.Skills.FindOrAdd(TEXT("flameArmor"))={};Shadow->FlameArmorSkill=Definition;
        auto& T=Shadow->FlameArmorSkill.FireMagic;T.HitExperience=T.KillExperience=T.MultiHitExperience=T.MultiKillExperience=0;T.*Field=7;
        Shadow->FinishFireMagicCast(TEXT("flameArmor"),Reward);
        Check(Shadow->FireMagicProgress(TEXT("flameArmor")).Experience==7,FString(TEXT("training setting consumed: "))+Name);
    };
    FFireMagicRewards Reward;Reward.Hits=1;
    RewardCheck(&FFireMagicTuning::HitExperience,TEXT("hitExperience"),Reward);Reward.Kills=1;
    RewardCheck(&FFireMagicTuning::KillExperience,TEXT("killExperience"),Reward);Reward.Kills=0;Reward.bMultiHit=true;
    RewardCheck(&FFireMagicTuning::MultiHitExperience,TEXT("multiHitExperience"),Reward);Reward.bMultiHit=false;Reward.Kills=2;
    RewardCheck(&FFireMagicTuning::MultiKillExperience,TEXT("multiKillExperience"),Reward);
    Shadow->FlameArmorSkill=Definition;Shadow->FlameArmorSkill.ExperiencePerLevel=5;Shadow->Current.Skills.FindOrAdd(TEXT("flameArmor"))={};Reward={};Reward.Hits=5;
    Shadow->FinishFireMagicCast(TEXT("flameArmor"),Reward);
    Check(Shadow->FireMagicProgress(TEXT("flameArmor")).Level==2&&Shadow->FireMagicProgress(TEXT("flameArmor")).Experience==0,TEXT("experiencePerLevel controls actual training level-up"));
    Shadow->FlameArmorSkill=Definition;
    auto* LocalPC=World->SpawnActor<APlayerController>();LocalPC->SetAsLocalPlayerController();auto* LocalPawn=World->SpawnActor<AFPSGAMECharacter>();LocalPC->Possess(LocalPawn);
    Host->Current.FlameArmorCooldown=Host->Current.FlameArmorCooldownDuration=60;
    auto* Tuning=GI->GetSubsystem<UDevelopmentTuningSubsystem>();
    const bool Enabled=Tuning->SetEnabled(EDevelopmentTuningOption::NoAbilityCooldown,true,LocalPC);
    const bool Disabled=Tuning->SetEnabled(EDevelopmentTuningOption::NoAbilityCooldown,false,LocalPC);
    Check(Enabled&&Disabled&&Host->FireMagicCooldown(TEXT("flameArmor"))==0&&Host->FireMagicCooldownDuration(TEXT("flameArmor"))==0,
        TEXT("no-cooldown switch clears armor cooldown after switching back off"));
    auto Root=MakeShared<FJsonObject>();Root->SetNumberField(TEXT("checks"),Rows.Num());Root->SetNumberField(TEXT("failures"),Failures);Root->SetArrayField(TEXT("results"),Rows);Root->SetArrayField(TEXT("levels"),Levels);
    Root->SetNumberField(TEXT("magic_attack"),Low.MagicAttack);Root->SetNumberField(TEXT("intelligence"),Shadow->Attribute(TEXT("int")));Root->SetNumberField(TEXT("low_level_actual_hit"),LowDamage);Root->SetNumberField(TEXT("high_level_actual_hit"),HighDamage);
    FString Json;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));FString Path;
    if(!FParse::Value(*Params,TEXT("Output="),Path))Path=FPaths::ProjectSavedDir()/TEXT("FlameArmorStatsAudit20261017/stats.json");
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);FFileHelper::SaveStringToFile(Json,*Path);
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);return Failures?1:0;
}
