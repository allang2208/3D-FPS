#include "WarhammerModificationAuditCommandlet.h"
#include "ProductionToolComponent.h"
#include "WarhammerCombat.h"
#include "WarhammerShockwave.h"
#include "ThunderHammerTuning.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"

namespace
{
void FormulaParts(FColdSteelItem& Item,const FGunsmithParts& Parts)
{
    TSharedPtr<FJsonObject> Data;
    FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
    auto Mods=MakeShared<FJsonObject>();
    for(const auto& Part:Parts)Mods->SetStringField(Part.Key,Part.Value);
    Data->SetObjectField(TEXT("gunsmith_parts"),Mods);
    // Old inventory instances must not override character skill progression.
    Data->SetNumberField(TEXT("heavy_damage_multiplier"),99.);
    Data->SetNumberField(TEXT("heavy_charge_seconds"),99.);
    Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
}
}

int32 UWarhammerModificationAuditCommandlet::AuditHeavyFormula(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    const FString Slot=TEXT("HammerModsAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("WarhammerModificationAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("HammerHeavyFormulaWorld"));
    auto* World=GI->GetWorld();auto* Host=GI->GetSubsystem<UColdSteelStatusModel>();auto* G=GI->GetSubsystem<UGunsmithSystem>();
    if(!World||!Host||!G||!Host->IsAudit()||Host->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 2;
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failures=0;
    const auto Check=[&](bool Passed,const FString& Label,double Actual=0.,double Expected=0.)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("check"),Label);Row->SetBoolField(TEXT("pass"),Passed);
        Row->SetNumberField(TEXT("actual"),Actual);Row->SetNumberField(TEXT("expected"),Expected);
        Rows.Add(MakeShared<FJsonValueObject>(Row));Failures+=!Passed;
        if(!Passed)UE_LOG(LogTemp,Error,TEXT("HAMMER_HEAVY FAIL %s actual=%.6f expected=%.6f"),*Label,Actual,Expected);
    };
    const auto Equal=[&](double Actual,double Expected,const FString& Label)
    {Check(FMath::IsNearlyEqual(Actual,Expected,.001),Label,Actual,Expected);};
    const auto Panel=[&](const FWeaponDamageParts& Actual,const FWeaponDamageParts& Expected,const FString& Label)
    {
        Equal(Actual.BasePhysical,Expected.BasePhysical,Label+TEXT(" base physical"));
        Equal(Actual.BaseMagic,Expected.BaseMagic,Label+TEXT(" base magic"));
        Equal(Actual.AddedPhysical,Expected.AddedPhysical,Label+TEXT(" added physical"));
        Equal(Actual.AddedMagic,Expected.AddedMagic,Label+TEXT(" added magic"));
    };
    auto Seed=Host->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
    Seed.Stamina=100;Seed.bSprintExhausted=false;Seed.Skills.FindOrAdd(TEXT("heavyStrike")).Level=1;
    Host->AdoptNetMirror(Seed);
    auto* Guest=Host->CreateShadowModel(Seed);
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<AWarhammerAuditRemoteController>();
    auto* PS=World->SpawnActor<AColdSteelPlayerState>();PC->PlayerState=PS;PC->Possess(Pawn);PS->ShadowModel=Guest;Guest->AttachPawn(Pawn);
    auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>();Tool->Character=Pawn;Tool->Kind=TEXT("warhammer");
    if(auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>())Health->Health=Health->MaxHealth;
    Check(ColdSteelAuthority::ForPawn(Pawn)==Guest,TEXT("authority resolves attacker's shadow profile"));
    const auto& Definition=Host->MasteryDefinition(TEXT("heavyStrike"));
    Equal(Definition.HeavyMultiplierBase,2.5,TEXT("catalog level 1 heavy multiplier"));
    Equal(Definition.HeavyMultiplierPerLevel,.1,TEXT("catalog heavy multiplier growth"));
    Equal(Definition.MaxLevel,20,TEXT("catalog maximum heavy level"));
    uint32 Request=0;int32 RelevantParts=0;bool SawFlat=false,SawMartial=false;
    for(const TCHAR* Id:{TEXT("ue_steel_warhammer"),TEXT("ue_runebound_warhammer"),ThunderHammer::Definition})
    {
        auto Hammer=Host->CreateItem(Id);Hammer.Place=1;Hammer.Cell=6;FormulaParts(Hammer,{});
        const auto* Catalog=G->ModifiableWeapon(Id);Check(Catalog!=nullptr,FString(Id)+TEXT(" catalog exists"));
        if(!Catalog)continue;
        for(int32 Level=0;Level<=20;++Level)
        {
            Seed.Items={Hammer};Seed.Skills.FindOrAdd(TEXT("heavyStrike")).Level=Level;Guest->AdoptNetMirror(Seed);
            const double Expected=2.5+FMath::Max(0,Level-1)*.1;
            const double Charge=2.-FMath::Max(0,Level-1)*.05;
            const FString Label=FString::Printf(TEXT("%s L%d"),Id,Level);
            const auto Stats=ColdSteelTool::Evaluate(Hammer,Guest);
            Equal(Stats.HeavyDamageMultiplier,Expected,Label+TEXT(" final multiplier ignores legacy item value"));
            Equal(Stats.HeavyChargeSeconds,Charge,Label+TEXT(" charge uses skill growth"));
            Tool->ApplyToolStats(Guest->ActiveProductionTool(),ColdSteelAuthority::ForPawn(Pawn));
            Equal(Tool->BluntHeavyMultiplier,Expected,Label+TEXT(" component uses guest multiplier"));
            Equal(Tool->BluntChargeSeconds,Charge,Label+TEXT(" component charge agrees with preview"));
            if(Level==1||Level==10||Level==20)
            {
                Tool->CancelUse();Tool->BluntServerReadyAt=0.;Guest->AdoptNetMirror(Seed);
                Tool->ServerBeginBluntCharge_Implementation(++Request);
                Check(Tool->bBluntServerCharging,Label+TEXT(" authority accepted charge"));
                Tool->BluntServerChargeStartedAt=World->GetTimeSeconds()-Charge-.05;
                Tool->ServerBeginBluntAttack_Implementation(Request,true,false);
                Check(Guest->Stamina()<Seed.Stamina,Label+TEXT(" authority accepted release"));
                Panel(Tool->AxeStrike.DamagePanel,Stats.Damage.Scaled(Expected),Label+TEXT(" authoritative heavy snapshot"));
                Tool->CancelUse();Tool->BluntServerReadyAt=0.;
            }
        }
        // Real registered parts, including flat heavy bonuses and martial damage.
        // Both the UI draft and equipped authority must consume the same result.
        Seed.Skills.FindOrAdd(TEXT("heavyStrike")).Level=10;
        const auto InspectParts=[&](const FGunsmithParts& Parts,const FString& Label)
        {
            auto Modified=Hammer;FormulaParts(Modified,Parts);Seed.Items={Modified};Guest->AdoptNetMirror(Seed);
            const auto M=G->Calculate(Id,Parts).Melee;
            const double Expected=(3.4*M.HeavyDamage+M.HeavyDamageAdd)*M.MartialDamage;
            const auto Equipped=ColdSteelTool::Evaluate(Modified,Guest);
            const auto Draft=ColdSteelTool::Evaluate(Hammer,Guest,&Parts);
            Equal(Equipped.HeavyDamageMultiplier,Expected,Label+TEXT(" equipped final multiplier"));
            Equal(Draft.HeavyDamageMultiplier,Expected,Label+TEXT(" draft final multiplier"));
            Equal(Equipped.HeavyChargeSeconds,FMath::Max(.2,1.55/(1.+Equipped.HeavyChargeSpeedBonus)),Label+TEXT(" equipped charge"));
            Equal(Draft.HeavyChargeSeconds,Equipped.HeavyChargeSeconds,Label+TEXT(" draft charge"));
            Tool->ApplyToolStats(Guest->ActiveProductionTool(),Guest);
            Equal(Tool->BluntHeavyMultiplier,Expected,Label+TEXT(" component final multiplier"));
            if(FString(Id)==ThunderHammer::Definition)
            {
                const double Native=FMath::Max(0.,Guest->Derived(TEXT("matk")))*(1.+Guest->SetEffect(TEXT("magicDamage")))*M.MagicDamage*M.AllAttackDamage;
                Equal(ThunderHammer::LightningMagic(Modified,Guest),Native,Label+TEXT(" native thunder has no extra heavy factor"));
            }
        };
        FGunsmithParts Combined;
        for(const auto& Column:Catalog->Options)for(const auto& Option:Column.Value)
        {
            const auto& M=Option.Melee;
            if(M.HeavyDamage==1.&&M.HeavyDamageAdd==0.&&M.MartialDamage==1.&&M.HeavyChargeSpeedBonus==0.
                &&M.MagicDamage==1.&&M.AllAttackDamage==1.&&Option.Id!=TEXT("guan_lei_seat")&&Option.Id!=TEXT("ji_lei_seat"))continue;
            FGunsmithParts Parts;Parts.Add(Column.Key,Option.Id);
            if(G->Normalize(Id,Parts).FindRef(Column.Key)!=Option.Id)continue;
            SawFlat|=M.HeavyDamageAdd!=0.;SawMartial|=M.MartialDamage!=1.;++RelevantParts;
            InspectParts(Parts,FString(Id)+TEXT(" ")+Option.Id);
            Combined.Add(Column.Key,Option.Id);
        }
        InspectParts(Combined,FString(Id)+TEXT(" combined parts"));
    }
    Check(RelevantParts>0,TEXT("registered heavy and magic modifiers exercised"),RelevantParts,1);
    // The current hammer catalog has no flat-heavy/martial option. Exercise
    // their ordering through an in-memory fixture, never by editing game data.
    auto* FixturePart=const_cast<FGunsmithOption*>(G->Option(ThunderHammer::Definition,TEXT("head_mount"),TEXT("guan_lei_seat")));
    Check(FixturePart!=nullptr,TEXT("isolated modifier fixture available"));
    if(FixturePart)
    {
        const auto OriginalModifiers=FixturePart->Melee;
        FixturePart->Melee.HeavyDamage=1.2;FixturePart->Melee.HeavyDamageAdd=.45;FixturePart->Melee.MartialDamage=1.15;
        FGunsmithParts Parts{{TEXT("head_mount"),TEXT("guan_lei_seat")}};
        auto Hammer=Host->CreateItem(ThunderHammer::Definition);Hammer.Place=1;Hammer.Cell=6;FormulaParts(Hammer,Parts);
        Seed.Items={Hammer};Seed.Skills.FindOrAdd(TEXT("heavyStrike")).Level=10;Guest->AdoptNetMirror(Seed);
        const auto Stats=ColdSteelTool::Evaluate(Hammer,Guest);
        constexpr double Expected=5.2095; // (3.4 * 1.2 + 0.45) * 1.15
        Equal(Stats.HeavyDamageMultiplier,Expected,TEXT("synthetic multiply then flat then martial"));
        Equal(ColdSteelTool::Evaluate(Hammer,Guest,&Parts).HeavyDamageMultiplier,Expected,TEXT("synthetic UI draft agrees"));
        Tool->CancelUse();Tool->BluntServerReadyAt=0.;
        Tool->ServerBeginBluntCharge_Implementation(++Request);
        Tool->BluntServerChargeStartedAt=World->GetTimeSeconds()-Stats.HeavyChargeSeconds-.05;
        Tool->ServerBeginBluntAttack_Implementation(Request,true,false);
        Check(Tool->bThunderThrowSeat&&Guest->Stamina()<Seed.Stamina,TEXT("GuanLei authority accepts modified heavy release"));
        Panel(Tool->AxeStrike.DamagePanel,Stats.Damage.Scaled(Expected),TEXT("GuanLei authoritative mixed modifier snapshot"));
        Tool->CancelUse();Tool->BluntServerReadyAt=0.;FixturePart->Melee=OriginalModifiers;
    }
    Equal(Host->MasteryProgress(TEXT("heavyStrike")).Level,1,TEXT("guest levels never change host progress"));
    const FWeaponDamageParts Base{100.,0.,20.,40.};
    Panel(WarhammerCombat::Damage(Base,Guest,false,false,4.4f,0),Base,TEXT("ordinary attack ignores heavy multiplier"));
    Panel(WarhammerCombat::Damage(Base,Guest,false,false,4.4f,2),{125.,0.,25.,50.},TEXT("combo finisher keeps 1.25 multiplier"));
    const double Sprint=FMath::FloorToDouble(Base.Total()*Guest->DashAttackStats().DamageMultiplier);
    Equal(WarhammerCombat::Damage(Base,Guest,true,true,99.f,2).Total(),Sprint,TEXT("sprint ignores heavy multiplier"));
    FColdSteelSkillShot Shot;Shot.DamagePanel=WarhammerCombat::Damage(Base,Guest,false,true,3.4f,0);
    // No owner, opponents, BeginPlay, world tick, asset mutation or gameplay.
    auto* Wave=World->SpawnActor<AWarhammerShockwave>();
    Wave->Setup(Shot,300,1.5f,200.f);
    Panel(Wave->DamageWithElectricMultiplier(1.f),{340.,0.,68.,336.},TEXT("native slam and thrown landing add lightning once"));
    Panel(Wave->DamageWithElectricMultiplier(1.15f),{340.,0.,68.,366.},TEXT("electrified boosts only native lightning"));
    Wave->Setup(Shot,300,1.5f,200.f,true);
    Panel(Wave->DamageWithElectricMultiplier(1.f),{0.,340.,0.,404.},TEXT("JiLei preserves heavy total and converts to magic once"));
    Panel(Wave->DamageWithElectricMultiplier(1.15f),{0.,391.,0.,464.6},TEXT("JiLei whole lightning benefits from electrified"));
    Wave->Setup(Shot,300,2.f);
    Panel(Wave->DamageWithElectricMultiplier(1.15f),Shot.DamagePanel,TEXT("non-thunder hammer ignores electric vulnerability"));
    Wave->Destroy();Tool->CancelUse();Pawn->Destroy();PC->Destroy();PS->Destroy();
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("checks"),Rows);
    Report->SetNumberField(TEXT("failures"),Failures);Report->SetNumberField(TEXT("count"),Rows.Num());
    Report->SetNumberField(TEXT("registered_parts_checked"),RelevantParts);
    Report->SetBoolField(TEXT("catalog_has_flat_heavy_part"),SawFlat);Report->SetBoolField(TEXT("catalog_has_martial_damage_part"),SawMartial);
    Report->SetBoolField(TEXT("synthetic_modifier_fixture_used"),FixturePart!=nullptr);
    Report->SetStringField(TEXT("isolated_profile"),Slot);Report->SetBoolField(TEXT("user_profile_modified"),false);
    Report->SetBoolField(TEXT("gameplay_started"),false);Report->SetBoolField(TEXT("real_network_transport_tested"),false);
    FString Out=FPaths::ProjectSavedDir()/TEXT("WarhammerHeavyFormula.json");FParse::Value(*Params,TEXT("Out="),Out);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    const bool Saved=FFileHelper::SaveStringToFile(Json,*Out);
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    UE_LOG(LogTemp,Display,TEXT("HAMMER_HEAVY_DONE checks=%d failures=%d parts=%d"),Rows.Num(),Failures,RelevantParts);
    return Failures||!Saved?1:0;
}
