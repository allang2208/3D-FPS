#include "HatchetGripAuditCommandlet.h"
#include "GunsmithSystem.h"
#include "GunsmithModificationTier.h"
#include "MeleeWeaponStats.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Combat/CoreCombatFormula.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/MonsterToughnessTypes.h"
#include "../Monsters/WolfMonster.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonSerializer.h"

int32 UHatchetGripAuditCommandlet::Main(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    const FString Slot=TEXT("SkillNetworkAudit_HatchetGrip_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("HatchetGripAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("HatchetGripAuditWorld"));
    FCommandLine::Set(*Original);
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();auto* G=GI->GetSubsystem<UGunsmithSystem>();
    ON_SCOPE_EXIT {GI->Shutdown();if(World){GEngine->DestroyWorldContext(World);World->DestroyWorld(false);}GI->RemoveFromRoot();};
    if(!World||!Model||!G||!Model->IsAudit())return 2;
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failures=0;
    const auto Check=[&](bool OK,const FString& Label,double Actual=0.,double Expected=0.)
    {
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("case"),Label);R->SetBoolField(TEXT("pass"),OK);
        R->SetNumberField(TEXT("actual"),Actual);R->SetNumberField(TEXT("expected"),Expected);Rows.Add(MakeShared<FJsonValueObject>(R));Failures+=!OK;
        UE_LOG(LogTemp,Display,TEXT("HATCHET_GRIP %s %s %.6f / %.6f"),OK?TEXT("PASS"):TEXT("FAIL"),*Label,Actual,Expected);
    };
    const auto Near=[&](double A,double B,const FString& Label){Check(FMath::IsNearlyEqual(A,B,.001),Label,A,B);};
    auto Seed=Model->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
    const auto Make=[&](const TCHAR* Definition,const TCHAR* Grip,int32 Cell)
    {
        auto I=Model->CreateItem(Definition);I.Place=1;I.Cell=Cell;
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),Data);
        auto Parts=MakeShared<FJsonObject>();if(Grip)Parts->SetStringField(TEXT("grip"),Grip);
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);I.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));return I;
    };
    const auto Equip=[&](FColdSteelItem Main,const FColdSteelItem* Off=nullptr,int32 ActiveSlot=6)
    {auto P=Seed;P.ActiveWeaponSlot=ActiveSlot;P.Items.Add(Main);if(Off)P.Items.Add(*Off);Model->AdoptNetMirror(P);};
    const auto Factory=Make(TEXT("ue_tactical_hatchet"),nullptr,6);
    const auto Breaker=Make(TEXT("ue_tactical_hatchet"),TEXT("hatchet_grip_agile"),6);
    const auto Long=Make(TEXT("ue_tactical_hatchet"),TEXT("hatchet_grip_long"),6);
    Equip(Factory);const auto Base=ColdSteelMelee::Evaluate(*Model->Equipped(),Model);
    const auto BaseQuick=Model->QuickCombatStats();const auto BaseWhirl=Model->WhirlwindStats();
    const auto BaseUpper=Model->SwordUppercutStaminaCost();const auto BaseCharge=Model->HeavyChargeStaminaPerSecond();
    Equip(Breaker);const auto Stats=ColdSteelMelee::Evaluate(*Model->Equipped(),Model);
    Near(Stats.Modifiers.PhysicalArmorPenetration,.25,TEXT("catalog penetration"));
    Near(Stats.Modifiers.ToughnessDamage,1.2,TEXT("catalog toughness"));
    Near(Stats.AttackSeconds,Base.AttackSeconds,TEXT("no speed bonus"));
    Near(Stats.Damage,Base.Damage,TEXT("no raw physical damage penalty or bonus"));
    Near(Stats.BaseReach,Base.BaseReach,TEXT("standard reach"));
    Near(Stats.AttackStamina,Base.AttackStamina*1.15,TEXT("ordinary attack cost"));
    Near(ColdSteelMelee::HeavyReleaseStamina(Model->Equipped(),Model),Base.AttackStamina*1.15,TEXT("heavy release cost"));
    Near(Model->HeavyChargeStaminaPerSecond(),BaseCharge*1.15,TEXT("heavy charge drain"));
    Near(Model->QuickCombatStats().ToughnessMultiplier,BaseQuick.ToughnessMultiplier*1.2,TEXT("quick combat toughness"));
    Near(Model->QuickCombatStats().StaminaCost,BaseQuick.StaminaCost*1.15,TEXT("quick combat cost"));
    Near(Model->WhirlwindStats().StaminaCost,BaseWhirl.StaminaCost*1.15,TEXT("whirlwind cost"));
    Near(Model->SwordUppercutStaminaCost(),BaseUpper*1.15,TEXT("uppercut cost"));
    Check(ColdSteelModification::Tier(Breaker.Definition,TEXT("grip"),TEXT("hatchet_grip_agile"))==EGunsmithModificationTier::Special,TEXT("breaker special tier"));
    Check(ColdSteelModification::Tier(Long.Definition,TEXT("grip"),TEXT("hatchet_grip_long"))==EGunsmithModificationTier::Special,TEXT("long special tier"));
    FGunsmithParts Foreign;Foreign.Add(TEXT("grip"),TEXT("hatchet_grip_agile"));
    Check(G->Normalize(TEXT("ue_kukri"),Foreign).FindRef(TEXT("grip"))!=TEXT("hatchet_grip_agile"),TEXT("axe exclusive option"));
    Equip(Long);const auto LongStats=ColdSteelMelee::Evaluate(*Model->Equipped(),Model);
    Near(LongStats.BaseReach,Base.BaseReach*1.25,TEXT("long reach retained"));
    Near(LongStats.Modifiers.PhysicalDamage,1.1,TEXT("long damage retained"));
    Near(LongStats.Modifiers.AttackSpeed,.95,TEXT("long speed retained"));
    Near(LongStats.Modifiers.Stamina,1.1,TEXT("long cost retained"));
    auto* Shooter=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<APlayerController>();
    if(!Shooter||!PC)return 2;
    PC->SetPlayer(NewObject<ULocalPlayer>(GEngine));PC->Possess(Shooter);Model->AttachPawn(Shooter);
    for(const TCHAR* MainDefinition:{TEXT("ue_m1911"),TEXT("ue_apprentice_staff")})for(int32 Active:{6,9})
    {
        const int32 OffSlot=Active==6?8:11;
        auto Main=Make(MainDefinition,nullptr,Active);auto Off=Make(TEXT("ue_tactical_hatchet"),TEXT("hatchet_grip_agile"),OffSlot);
        auto OffFactory=Make(TEXT("ue_tactical_hatchet"),nullptr,OffSlot);
        Equip(Main,&OffFactory,Active);const auto Before=Model->QuickCombatStats();
        Equip(Main,&Off,Active);const auto After=Model->QuickCombatStats();
        const FString Prefix=FString::Printf(TEXT("%s slot%d "),MainDefinition,Active);
        Near(After.ToughnessMultiplier,Before.ToughnessMultiplier*1.2,Prefix+TEXT("offhand quick toughness"));
        Near(After.StaminaCost,Before.StaminaCost*1.15,Prefix+TEXT("offhand quick cost"));
        const auto Shot=ColdSteelSkills::Snapshot(Shooter,Model->Equipped(OffSlot));
        Near(Shot.ArmorPenetration,.25,Prefix+TEXT("offhand penetration snapshot"));
        Near(ColdSteelSkills::Snapshot(Shooter,Model->Equipped()).ArmorPenetration,0.,Prefix+TEXT("main hand does not borrow penetration"));
    }
    FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Target=World->SpawnActor<AWolfMonster>(FVector(300,0,500),FRotator::ZeroRotator,Spawn);if(!Target)return 2;
    Target->MaxHealth=Target->Health=100000.f;
    auto* TargetCombat=Target->Combat.Get();if(!TargetCombat)return 2;
    TargetCombat->ToughnessThreshold=100000.f;TargetCombat->BladeResistance=0.f;TargetCombat->bAllowSubthresholdStagger=false;
    const double Defense=CombatFormulaRuntime::MonsterDefense(Target,false);
    Check(Defense>0.,TEXT("armored target fixture"),Defense,0.);
    for(int32 Mask=0;Mask<4;++Mask)
    {
        auto Main=Make(TEXT("ue_tactical_hatchet"),Mask&1?TEXT("hatchet_grip_agile"):nullptr,6);
        auto Off=Make(TEXT("ue_tactical_hatchet"),Mask&2?TEXT("hatchet_grip_agile"):nullptr,8);Equip(Main,&Off);
        auto Shot=ColdSteelSkills::Snapshot(Shooter,Model->Equipped());Shot.AttackMeta=0x16;
        ColdSteelSkills::CapturePairedDash(Shot,Shooter,Model);
        const FString Prefix=FString::Printf(TEXT("dual mask%d "),Mask);
        Near(Shot.ArmorPenetration,Mask&1?.25:0.,Prefix+TEXT("main penetration"));
        Near(Shot.PairedDashOffPenetration,Mask&2?.25:0.,Prefix+TEXT("off penetration"));
        Near(Shot.PairedDashMainPhysical.Total(),Shot.PairedDashOffPhysical.Total(),Prefix+TEXT("equal physical contributions"));
        const auto Dash=Model->DashAttackStats();
        Shot.ToughnessDamageMultiplier=Dash.ToughnessMultiplier;
        Near(Dash.ToughnessMultiplier,1.+.1*((Mask&1?1:0)+(Mask&2?1:0)),Prefix+TEXT("weighted toughness once"));
        // Editing the source loadout after capture must not alter the stored
        // contributions used by this explicit settlement fixture.
        if(Mask==2)Equip(Factory);
        Shot.CriticalChance=0;Shot.CriticalRoll=1;Shot.WeakpointPercent=0;
        FHitResult Hit(Target,Target->GetCapsuleComponent(),Target->GetActorLocation(),-FVector::ForwardVector);
        FWeaponDamageResult Result;
        Model->ApplySkillWeaponHit(Shooter,Hit,1000.f,FVector::ForwardVector,Shot,&Result);
        const double Expected=CoreCombatFormula::Defense(500.,Defense,false,Mask&1?.25:0.)+CoreCombatFormula::Defense(500.,Defense,false,Mask&2?.25:0.);
        Check(Result.bResolved,Prefix+TEXT("actual hit transaction resolved"));
        Near(Result.BeforeDefense.Total(),1000.,Prefix+TEXT("combined damage not duplicated"));
        Near(Result.AfterDefense.Total(),Expected,Prefix+TEXT("per-blade armor settlement"));
        // Dash poise is damage-derived: penetration changes its damage basis.
        Check(TargetCombat->LastToughnessDamage>0.f,Prefix+TEXT("nonzero actual toughness"));
        Near(TargetCombat->LastToughnessDamage,Expected*MonsterToughness::FormPower(Shot.AttackForm)*Dash.ToughnessMultiplier,Prefix+TEXT("actual weighted toughness"));
    }
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("checks"),Rows);Report->SetNumberField(TEXT("failures"),Failures);
    Report->SetNumberField(TEXT("count"),Rows.Num());Report->SetStringField(TEXT("isolated_profile"),Slot);
    Report->SetBoolField(TEXT("gameplay_started"),false);Report->SetBoolField(TEXT("real_network_transport_tested"),false);
    FString Out=FPaths::ProjectSavedDir()/TEXT("HatchetGripBalance20261103.json");FParse::Value(*Params,TEXT("Out="),Out);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));FFileHelper::SaveStringToFile(Json,*Out);
    UE_LOG(LogTemp,Display,TEXT("HATCHET_GRIP_AUDIT checks=%d failures=%d output=%s"),Rows.Num(),Failures,*Out);
    return Failures?1:0;
}
