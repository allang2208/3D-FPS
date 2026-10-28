#include "KukriNetworkAuditCommandlet.h"
#include "ColdSteelPlayerState.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/Kukri/KukriFrostRavenComponent.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/WolfMonster.h"
#include "Engine/World.h"
#include "Net/UnrealNetwork.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"

void UKukriNetworkAuditCommandlet::CheckRunes(AColdSteelPlayerState* PS,AFPSGAMECharacter* Pawn,TFunctionRef<void(bool,const TCHAR*)> Check)
{
    auto* Model=PS->ShadowModel.Get();
    auto* Rune=Pawn->FindComponentByClass<UKukriFrostRavenComponent>();
    auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    Check(Rune!=nullptr,TEXT("frost rune default subobject exists"));if(!Rune)return;
    Health->Health=Health->MaxHealth;
    auto Seed=Model->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
    const auto Item=[&](int32 Cell,const FString& RuneId)
    {
        auto Value=Model->CreateItem(TEXT("ue_kukri"));Value.Place=1;Value.Cell=Cell;
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Value.Data),Data);
        if(!Data)Data=MakeShared<FJsonObject>();
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("blade_2"),RuneId);
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);
        Value.Data.Reset();FJsonSerializer::Serialize(Data,TJsonWriterFactory<>::Create(&Value.Data));return Value;
    };
    const auto Main=Item(6,TEXT("frost_raven_rune")),Off=Item(8,TEXT("frost_raven_rune"));
    Seed.Items={Main,Off};Model->AdoptNetMirror(Seed);Rune->Configure(Model);
    FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Victim=Pawn->GetWorld()->SpawnActor<AWolfMonster>(FVector(0,0,1500),FRotator::ZeroRotator,Spawn);
    auto* Other=Pawn->GetWorld()->SpawnActor<AWolfMonster>(FVector(500,0,1500),FRotator::ZeroRotator,Spawn);
    auto* Status=UCombatStatusFormula::GetOrAdd(Victim);
    auto Shot=ColdSteelSkills::Snapshot(Pawn,Model->Equipped());Shot.bMelee=true;Shot.bRicochet=false;
    Check(Rune->State.Instances.Num()==2,TEXT("two frost knives share one component state"));
    const float WithRune=Shot.CriticalChance;
    auto Plain=Main;Plain.Data=TEXT("{}");auto PlainSeed=Seed;PlainSeed.Items={Plain};
    Model->AdoptNetMirror(PlainSeed);const auto PlainShot=ColdSteelSkills::Snapshot(Pawn,Model->Equipped());
    Check(FMath::IsNearlyEqual(WithRune-PlainShot.CriticalChance,20.f),TEXT("passive adds twenty percentage points to this knife"));
    Model->AdoptNetMirror(Seed);Rune->Configure(Model);
    for(uint32 I=1;I<=7;++I)
    {
        Shot.MasteryAttackSerial=I;Rune->ConfirmHit(Shot,Victim,10.f);Rune->ConfirmHit(Shot,Other,10.f);
    }
    Check(Rune->State.Charge==7&&Rune->Remaining()==0.f,TEXT("seven area actions charge seven times"));
    Shot.MasteryAttackSerial=8;Rune->ConfirmHit(Shot,Victim,10.f);
    const double ActivationEnd=Rune->State.EndsAt;
    Check(Rune->Remaining()>15.9f&&Status->ChillCount()==0,TEXT("eighth action activates sixteen seconds without chilling"));
    Check(FMath::IsNearlyEqual(Rune->ToughnessMultiplier(Shot,Model),1.f),TEXT("later contacts of activating action are not boosted"));
    Shot.MasteryAttackSerial=9;
    Check(FMath::IsNearlyEqual(Rune->ToughnessMultiplier(Shot,Model),1.35f),TEXT("next action receives toughness plus thirty five percent"));
    Rune->ConfirmHit(Shot,Victim,10.f);Shot.ItemInstance=Off.InstanceId;Rune->ConfirmHit(Shot,Victim,10.f);
    Check(Status->ChillCount()==4&&FMath::IsNearlyEqual(Status->ChillMovementMultiplier(),.8f),TEXT("dual contact applies four chill stacks and twenty percent slow"));
    Rune->ConfirmHit(Shot,Other,10.f);
    Check(UCombatStatusFormula::GetOrAdd(Other)->ChillCount()==4,TEXT("same area action chills a second victim independently"));
    for(uint32 I=10;I<=13;++I){Shot.MasteryAttackSerial=I;Rune->ConfirmHit(Shot,Victim,10.f);}
    Check(Status->ChillCount()==10&&FMath::IsNearlyEqual(Status->FrozenRemaining(),4.f),TEXT("twenty chill consumes ten stacks and freezes four seconds"));
    Shot.MasteryAttackSerial=14;Rune->ConfirmHit(Shot,Victim,10.f);
    Check(Status->ChillCount()==10&&Rune->State.EndsAt==ActivationEnd&&Rune->State.Charge==8,
        TEXT("frozen target rejects chill and active hits do not extend or precharge"));
    auto Away=Seed;Away.ActiveWeaponSlot=9;Model->AdoptNetMirror(Away);Rune->Configure(Model);
    Check(Rune->Remaining()==0.f&&Rune->State.Charge==0,TEXT("switching away clears the activation"));
    Model->AdoptNetMirror(Seed);Rune->Configure(Model);
    Check(Rune->Remaining()==0.f&&Rune->State.Charge==0,TEXT("switching back cannot resume an old activation"));
    const auto MixedMain=Item(6,TEXT("berserker_rune"));auto Mixed=Seed;Mixed.Items={MixedMain,Off};
    Model->AdoptNetMirror(Mixed);Rune->Configure(Model);
    Shot.ItemInstance=MixedMain.InstanceId;Shot.MasteryAttackSerial=100;Rune->ConfirmHit(Shot,Other,10.f);
    Check(Rune->State.Charge==0,TEXT("mixed rune main knife cannot charge frost"));
    Shot.ItemInstance=Off.InstanceId;Rune->ConfirmHit(Shot,Other,10.f);
    Check(Rune->State.Charge==1,TEXT("mixed rune offhand charges frost independently"));
    Health->Health=0.f;Rune->Configure(Model);
    Check(Rune->State.Charge==0&&Rune->State.Instances.IsEmpty(),TEXT("death clears charge and equipment state"));
    Health->Health=Health->MaxHealth;

    Rune->GetClass()->SetUpRuntimeReplicationData();
    TArray<FLifetimeProperty> Props;Rune->GetLifetimeReplicatedProps(Props);
    const auto* StateField=FindFProperty<FProperty>(Rune->GetClass(),TEXT("State"));
    Check(StateField&&Props.ContainsByPredicate([&](const auto& P){return P.RepIndex==StateField->RepIndex&&P.Condition==COND_None;}),
        TEXT("frost activation replication includes observers"));

    FColdSteelNetHitReport Report;Report.ItemDefinition=TEXT("ue_kukri");
    PS->KukriAttack.Serial=900;Report.AttackMeta=0;
    const uint32 Normal=PS->ResolveKukriRuneAttackSerial(Report,10001);
    Report.MasteryAttackSerial=123456;
    Check(Normal==PS->ResolveKukriRuneAttackSerial(Report,10002),TEXT("both normal blades reuse accepted action identity"));
    Report.AttackMeta=0x20;PS->WhirlwindActiveSequence=900;
    const uint32 Area=PS->ResolveKukriRuneAttackSerial(Report,10003);
    Report.MasteryAttackSerial=987654;
    Check(Area!=Normal&&Area==PS->ResolveKukriRuneAttackSerial(Report,10004),TEXT("changing client mastery id cannot multiply area rune charge"));
    ++PS->WhirlwindActiveSequence;
    Check(Area!=PS->ResolveKukriRuneAttackSerial(Report,10005),TEXT("new accepted area cast receives a new rune identity"));
    Report.AttackMeta=0x80;PS->QuickCombatServerSequence=900;
    const uint32 Quick=PS->ResolveKukriRuneAttackSerial(Report,10006);
    Check(Quick!=Normal&&Quick==PS->ResolveKukriRuneAttackSerial(Report,10007),TEXT("quick combat uses its own accepted action identity"));
    Report.AttackMeta=0x14;PS->UppercutActiveSequence=900;
    const uint32 Upper=PS->ResolveKukriRuneAttackSerial(Report,10008);
    Check(Upper!=Quick&&Upper==PS->ResolveKukriRuneAttackSerial(Report,10009),TEXT("uppercut uses its own accepted action identity"));
    PS->UppercutActiveSequence=0;
    Check(PS->ResolveKukriRuneAttackSerial(Report,10010)==0,TEXT("missing accepted action cannot supply a rune identity"));
}
