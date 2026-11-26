#include "KukriRuneWireAudit.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/Kukri/KukriBerserkerComponent.h"
#include "../Weapons/Kukri/KukriFrostRavenComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "HAL/PlatformMisc.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"

namespace KukriRuneWire
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("KukriRuneWireAudit"));}
const TCHAR* Cases[]={TEXT("mixed_equipment_idle"),TEXT("both_runes_active"),TEXT("weapon_switch_clears"),
    TEXT("switch_back_stays_idle"),TEXT("second_activation"),TEXT("death_clears")};
FColdSteelProfile Seed(UColdSteelStatusModel* Model,const FString& Prefix)
{
    auto P=Model->Snapshot();P.Items.Reset();P.ActiveWeaponSlot=6;P.ActiveProductionTool.Reset();P.DungeonRun={};
    P.Stamina=150;P.bSprintExhausted=false;
    for(int32 Side=0;Side<2;++Side)
    {
        auto I=Model->CreateItem(TEXT("ue_kukri"));I.Place=1;I.Cell=Side?8:6;I.InstanceId=Prefix+(Side?TEXT("_raven"):TEXT("_wolf"));
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),Data);
        if(!Data)Data=MakeShared<FJsonObject>();
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("blade_2"),Side?TEXT("frost_raven_rune"):TEXT("berserker_rune"));
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);I.Data.Reset();
        FJsonSerializer::Serialize(Data,TJsonWriterFactory<>::Create(&I.Data));P.Items.Add(I);
    }
    return P;
}
void Prepare(AFPSGAMECharacter* Pawn,UColdSteelStatusModel* Model,int32 Phase)
{
    Pawn->SetActorLocation(FVector(0,Pawn->HasAuthority()&&Pawn->IsLocallyControlled()?1000:0,500));
    Pawn->GetCharacterMovement()->StopMovementImmediately();Pawn->GetCharacterMovement()->SetComponentTickEnabled(false);
    Pawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Pawn->SetActorTickEnabled(false);
    auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    auto P=Model->Snapshot();P.ActiveWeaponSlot=Phase==2?9:6;Model->AdoptNetMirror(P);Model->AttachPawn(Pawn);
    // AttachPawn applies the profile's health. Inject the death transition after
    // equipment setup so the fixture does not immediately restore that health.
    if(Pawn->HasAuthority())Health->Health=Phase==5?0.f:Health->MaxHealth;
    Pawn->FindComponentByClass<UKukriBerserkerComponent>()->Configure(Model);
    Pawn->FindComponentByClass<UKukriFrostRavenComponent>()->Configure(Model);
    Pawn->ForceNetUpdate();
}
void Activate(AFPSGAMECharacter* Pawn,UColdSteelStatusModel* Model,int32 Cycle)
{
    auto* Wolf=Pawn->FindComponentByClass<UKukriBerserkerComponent>();
    auto* Raven=Pawn->FindComponentByClass<UKukriFrostRavenComponent>();
    auto Shot=ColdSteelSkills::Snapshot(Pawn,Model->Equipped());Shot.bMelee=true;Shot.bRicochet=false;
    for(uint32 I=1;I<=12;++I){Shot.MasteryAttackSerial=Cycle*100+I;Wolf->ConfirmHit(Shot,10.f);}
    Shot.ItemInstance=Model->Equipped(8)->InstanceId;
    for(uint32 I=1;I<=8;++I){Shot.MasteryAttackSerial=Cycle*100+20+I;Raven->ConfirmHit(Shot,Pawn,10.f);}
}
template<class T> T State(const UObject* Object)
{
    const auto* Field=Object?FindFProperty<FStructProperty>(Object->GetClass(),TEXT("State")):nullptr;
    return Field?*Field->ContainerPtrToValuePtr<T>(Object):T{};
}
bool HasObject(const UObject* Object,const TCHAR* Name)
{
    const auto* Field=Object?FindFProperty<FObjectPropertyBase>(Object->GetClass(),Name):nullptr;
    return Field&&Field->GetObjectPropertyValue_InContainer(Object);
}
bool Check(AFPSGAMECharacter* Pawn,int32 Phase,const FString& Prefix,FString& Details)
{
    if(!Pawn){Details=TEXT("pawn missing");return false;}
    const auto* Wolf=Pawn->FindComponentByClass<UKukriBerserkerComponent>();
    const auto* Raven=Pawn->FindComponentByClass<UKukriFrostRavenComponent>();
    const auto W=State<FKukriBerserkerState>(Wolf);const auto R=State<FKukriFrostRavenState>(Raven);
    const bool Active=Phase==1||Phase==4,Equipped=Phase!=2&&Phase!=5;
    const bool IDs=Equipped?(W.Instances==TArray<FString>{Prefix+TEXT("_wolf")}&&R.Instances==TArray<FString>{Prefix+TEXT("_raven")}):W.Instances.IsEmpty()&&R.Instances.IsEmpty();
    const bool Timing=Wolf&&Raven&&(Wolf->Remaining()>0.f)==Active&&(Raven->Remaining()>0.f)==Active;
    const bool Charge=W.Charge==(Active?12:0)&&R.Charge==(Active?8:0);
    // No rendering assertion in a NullRHI run. This verifies owner/observer routing.
    const bool Presentation=(!Equipped||(HasObject(Wolf,TEXT("ActiveVFX"))&&HasObject(Raven,TEXT("ActiveVFX"))))&&
        (Pawn->IsLocallyControlled()||(!HasObject(Wolf,TEXT("Hud"))&&!HasObject(Raven,TEXT("Hud"))));
    Details=FString::Printf(TEXT("ids=%d charge=%d/%d remaining=%.2f/%.2f owner=%d presentation=%d revisions=%u/%u"),
        IDs,W.Charge,R.Charge,Wolf?Wolf->Remaining():-1.f,Raven?Raven->Remaining():-1.f,Pawn->IsLocallyControlled(),Presentation,W.EquipmentRevision,R.EquipmentRevision);
    return IDs&&Timing&&Charge&&Presentation;
}
}
void AKukriRuneWireController::ClientCase_Implementation(int32 Phase,AFPSGAMECharacter* Subject)
{
    if(!KukriRuneWire::Enabled()||HasAuthority()||Phase==Current||Phase<0||Phase>=UE_ARRAY_COUNT(KukriRuneWire::Cases))return;
    auto* Controlled=Cast<AFPSGAMECharacter>(GetPawn());auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Controlled||!Model||!Model->IsAudit()||!Subject)return;
    if(Current<0)Model->AdoptNetMirror(KukriRuneWire::Seed(Model,TEXT("guest")));
    Host=Subject;Current=Phase;Started=GetWorld()->GetRealTimeSeconds();LastSent=-10;
    KukriRuneWire::Prepare(Controlled,Model,Phase);
}
void AKukriRuneWireController::Tick(float Delta)
{
    Super::Tick(Delta);if(!KukriRuneWire::Enabled()||HasAuthority()||!IsLocalController())return;
    const double Now=GetWorld()->GetRealTimeSeconds();if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(Current<0||Now-Started<.5||Now-LastSent<.5)return;
    FString OwnerDetails,Observer;const bool A=KukriRuneWire::Check(Cast<AFPSGAMECharacter>(GetPawn()),Current,TEXT("guest"),OwnerDetails);
    const bool B=KukriRuneWire::Check(Host,Current,TEXT("host"),Observer);
    if((A&&B)||Now-Started>10.){LastSent=Now;ServerResult(Current,A&&B,OwnerDetails+TEXT(" | observer: ")+Observer);}
}
void AKukriRuneWireController::ServerResult_Implementation(int32 Phase,bool ClientPassed,const FString& Details)
{
    if(!KukriRuneWire::Enabled()||Phase!=Finished||Phase<0||Phase>=UE_ARRAY_COUNT(KukriRuneWire::Cases))return;
    FString Observer;const bool Remote=KukriRuneWire::Check(Cast<AFPSGAMECharacter>(GetPawn()),Phase,TEXT("guest"),Observer);
    auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),KukriRuneWire::Cases[Phase]);
    Row->SetBoolField(TEXT("passed"),ClientPassed&&Remote);Row->SetStringField(TEXT("client"),Details);Row->SetStringField(TEXT("host_observer"),Observer);
    Rows.Add(MakeShared<FJsonValueObject>(Row));Passed&=ClientPassed&&Remote;++Finished;
    UE_LOG(LogTemp,Display,TEXT("KUKRI_WIRE_CASE %d pass=%d %s | host: %s"),Phase,ClientPassed&&Remote,*Details,*Observer);
}
void AKukriRuneWireController::ClientFinish_Implementation()
{if(KukriRuneWire::Enabled())ExitAt=GetWorld()->GetRealTimeSeconds()+.5;}
AKukriRuneWireGameMode::AKukriRuneWireGameMode()
{PlayerControllerClass=AKukriRuneWireController::StaticClass();PlayerStateClass=AKukriRuneWirePlayerState::StaticClass();DefaultPawnClass=AFPSGAMECharacter::StaticClass();PrimaryActorTick.bCanEverTick=true;}
void AKukriRuneWireGameMode::PostLogin(APlayerController* Player)
{Super::PostLogin(Player);if(KukriRuneWire::Enabled()&&!Player->IsLocalController()){Guest=Cast<AKukriRuneWireController>(Player);Joined=GetWorld()->GetRealTimeSeconds();}}
void AKukriRuneWireGameMode::Tick(float Delta)
{
    Super::Tick(Delta);if(!KukriRuneWire::Enabled())return;const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(!Host)for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(It->IsValid()&&It->Get()->IsLocalController())Host=Cast<AFPSGAMECharacter>(It->Get()->GetPawn());
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Host||!Model||!Model->IsAudit())return;
    if(!Seeded){Model->AdoptNetMirror(KukriRuneWire::Seed(Model,TEXT("host")));KukriRuneWire::Prepare(Host,Model,0);Seeded=true;UE_LOG(LogTemp,Display,TEXT("KUKRI_WIRE_HOST_READY"));}
    if(!Guest)return;
    if(Guest->Finished>=UE_ARRAY_COUNT(KukriRuneWire::Cases)||Now-Joined>150.)
    {
        auto Result=MakeShared<FJsonObject>();Result->SetBoolField(TEXT("passed"),Guest->Passed&&Guest->Finished==UE_ARRAY_COUNT(KukriRuneWire::Cases));
        Result->SetArrayField(TEXT("cases"),Guest->Rows);Result->SetBoolField(TEXT("rendered"),false);
        Result->SetStringField(TEXT("scope"),TEXT("UDP production rune replication with isolated profiles; not attack RPC or inventory upload"));
        FString Json,Path;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Json));
        if(FParse::Value(FCommandLine::Get(),TEXT("KukriRuneWireOutput="),Path))FFileHelper::SaveStringToFile(Json,*Path);
        UE_LOG(LogTemp,Display,TEXT("KUKRI_WIRE_FINISHED %s"),*Json);Guest->ClientFinish();ExitAt=Now+2.;return;
    }
    auto* Pawn=Cast<AFPSGAMECharacter>(Guest->GetPawn());auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();if(!Pawn||!PS)return;
    if(!GuestModel)
    {
        GuestModel=Model->CreateShadowModel(KukriRuneWire::Seed(Model,TEXT("guest")));
        if(!GuestModel){UE_LOG(LogTemp,Error,TEXT("KUKRI_WIRE_SEED_REJECTED %s"),*Model->ResultMessage());Guest->Passed=false;Guest->Finished=UE_ARRAY_COUNT(KukriRuneWire::Cases);return;}
        PS->ShadowModel=GuestModel;Pawn->NetShadowProfile=GuestModel;
    }
    if(Prepared!=Guest->Finished)
    {
        Prepared=Guest->Finished;KukriRuneWire::Prepare(Host,Model,Prepared);KukriRuneWire::Prepare(Pawn,GuestModel,Prepared);
        if(Prepared==1||Prepared==4){KukriRuneWire::Activate(Host,Model,Prepared);KukriRuneWire::Activate(Pawn,GuestModel,Prepared);}
        LastSetup=-10;
    }
    if(Now-LastSetup>1.){LastSetup=Now;Guest->ClientCase(Prepared,Host);}
}
