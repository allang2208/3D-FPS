#include "ShotgunWireAudit.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/PistolAmmoHelpers.h"
#include "PistolDualWieldComponent.h"
#include "GunsmithSystem.h"
#include "FPSBallisticsComponent.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "Engine/NetDriver.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

namespace ShotgunWire {void Save(const TArray<TSharedPtr<FJsonValue>>&,bool,const TCHAR*);}
namespace PistolAmmoWire
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("PistolAmmoWire"));}
struct FCase {FString Definition;int32 Side=0;bool Switch=false,Cancel=false,Partial=false,Loader=false,Pair=false,Staff=false,Empty=false;};
const TArray<FCase>& Cases()
{
    static const TArray<FCase> List=[]
    {
        TArray<FCase> R;
        for(const TCHAR* Def:{TEXT("ue_m1911"),TEXT("ue_g18"),TEXT("ue_pit_viper2011"),TEXT("ue_dan_wesson715"),TEXT("ue_rsh12")})
            for(int32 Side=0;Side<2;++Side)
            {
                FCase C;C.Definition=Def;C.Side=Side;R.Add(C);
                // Only these two pistol calibers currently offer alternate
                // enabled rounds in the production catalog.
                if(C.Definition==TEXT("ue_m1911")||C.Definition==TEXT("ue_dan_wesson715")){C.Switch=true;R.Add(C);C.Switch=false;}
                C.Empty=true;R.Add(C);
            }
        for(const TCHAR* Def:{TEXT("ue_dan_wesson715"),TEXT("ue_rsh12")})for(int32 Side=0;Side<2;++Side)
        {FCase C;C.Definition=Def;C.Side=Side;C.Partial=true;R.Add(C);C.Partial=false;C.Loader=true;R.Add(C);}
        FCase C;C.Definition=TEXT("ue_m1911");C.Cancel=true;R.Add(C);C.Side=1;R.Add(C);
        C={};C.Definition=TEXT("ue_g18");C.Pair=true;R.Add(C);
        C={};C.Definition=TEXT("ue_pit_viper2011");C.Side=1;C.Staff=true;R.Add(C);
        return R;
    }();return List;
}
FString Name(const FCase& C)
{return C.Definition+FString::Printf(TEXT("/%s/%s"),C.Pair?TEXT("mixed-dual"):C.Staff?TEXT("staff-left"):C.Side?TEXT("left"):TEXT("right"),C.Switch?TEXT("switch-ammo"):C.Empty?TEXT("empty-reload"):C.Partial?TEXT("partial-cancel-close"):C.Loader?TEXT("speedloader"):C.Cancel?TEXT("cancel-before-contact"):TEXT("reload-then-fire"));}
FColdSteelProfile Seed(UColdSteelStatusModel* Model,const FString& Id,const FCase& C)
{
    auto S=Model->Snapshot();S.Items.Reset();S.ActiveWeaponSlot=6;S.ActiveProductionTool.Reset();S.DungeonRun={};S.AmmoPouch.Reset();
    for(const auto& Type:Model->AmmoCatalog())if(Type.Enabled)S.AmmoPouch.Add(Type.Id,C.Pair?5:100);
    auto Gun=Model->CreateItem(C.Definition);Gun.InstanceId=Id;Gun.Place=1;Gun.Cell=C.Side?8:6;Gun.Magazine=C.Empty?0:2;Gun.VirtualMagazineAmmo=0;
    if(C.Loader)
    {
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Gun.Data),Data);
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("reload_device"),C.Definition==TEXT("ue_rsh12")?TEXT("rsh12_speedloader_5"):TEXT("dw715_speedloader"));
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Gun.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Gun.Data));
    }
    PistolAmmo::SetCases(Gun,C.Definition==TEXT("ue_rsh12")?5:6);S.Items.Add(Gun);
    if(C.Pair){auto Other=Model->CreateItem(TEXT("ue_pit_viper2011"));Other.InstanceId=Id+TEXT("_L");Other.Place=1;Other.Cell=8;Other.Magazine=2;S.Items.Add(Other);}
    if(C.Staff){auto Staff=Model->CreateItem(TEXT("ue_apprentice_staff"));Staff.Place=1;Staff.Cell=6;S.Items.Add(Staff);}
    return S;
}
FString Alternate(UColdSteelStatusModel* Model,const FColdSteelItem& Gun)
{for(const auto& Type:Model->AmmoCatalog())if(Type.Enabled&&Type.Group==Model->AmmoGroupFor(Gun)&&Type.Id!=Model->AmmoDefinitionFor(Gun))return Type.Id;return {};}
void Pin(AFPSGAMECharacter* AuditPawn)
{
    AuditPawn->SetActorTickEnabled(false);AuditPawn->GetCharacterMovement()->SetComponentTickEnabled(false);
    AuditPawn->GetCharacterMovement()->DisableMovement();AuditPawn->GetCharacterMovement()->StopMovementImmediately();
    AuditPawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);AuditPawn->SetActorLocation(FVector(0,0,500));

}
void Network(UWorld* World)
{
#if DO_ENABLE_NET_TEST
    if(auto* Driver=World->GetNetDriver()){FPacketSimulationSettings S;S.PktLag=60;S.PktLoss=5;Driver->SetPacketSimulationSettings(S);}
#endif
}
}

void AShotgunWireAuditController::SetupPistolAmmo(int32 Phase,const FString& Id,AFPSGAMECharacter* Host)
{
    if(HasAuthority()||Current==Phase)return;
    auto* AuditPawn=Cast<AFPSGAMECharacter>(GetPawn());auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* PS=GetPlayerState<AColdSteelPlayerState>();if(!AuditPawn||!Model||!Model->IsAudit()||!PS)return;
    if(Current<0)PistolAmmoWire::Network(GetWorld());
    AuditPawn->InterruptActionsForPriority(true);PS->PistolPendingReloads.Reset();PS->PistolCancelPending.Reset();PS->PistolPredictedShots.Reset();
    PS->PistolAppliedPouchDelta.Reset();PS->PistolAppliedAmmoRevision=0;PS->bPistolAmmoInitialized=false;
    Model->Current=PistolAmmoWire::Seed(Model,Id,PistolAmmoWire::Cases()[Phase]);Model->CurrentPawn=AuditPawn;AuditPawn->ApplyColdSteelProfile(Model);
    PistolAmmoWire::Pin(AuditPawn);AuditPawn->ShotsFired=10000+Phase*100;Current=Phase;Weapon=Id;Started=GetWorld()->GetRealTimeSeconds();
    AmmoStage=AmmoFired=0;AmmoCancelled=bReported=false;AmmoNextShot=0.;ObserverSubject=Host;
    UE_LOG(LogTemp,Display,TEXT("PISTOL_AMMO_WIRE_SETUP %d %s"),Phase,*PistolAmmoWire::Name(PistolAmmoWire::Cases()[Phase]));
}

bool AShotgunWireAuditController::TickPistolAmmo(float Delta)
{
    if(!PistolAmmoWire::Enabled())return false;Super::Tick(Delta);
    if(HasAuthority()||!IsLocalController())return true;
    const double Now=GetWorld()->GetRealTimeSeconds();if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return true;}
    if(Current<0||bReported)return true;
    auto* AuditPawn=Cast<AFPSGAMECharacter>(GetPawn());auto* PS=GetPlayerState<AColdSteelPlayerState>();
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!AuditPawn||!PS||!Model)return true;
    PS->TickPistolRecovery();const auto& C=PistolAmmoWire::Cases()[Current];
    // Run the production executors with real world time. The movement/camera
    // fixture is pinned, but no reload frame or loaded round is manufactured.
    AuditPawn->UpdateWeaponState(Delta);
    if(AuditPawn->DualPistols->IsActive())AuditPawn->DualPistols->Advance(Delta);
    else AuditPawn->ServicePendingReloadCycle();
    AuditPawn->UpdateActionPose(Delta);
    const auto* Gun=Model->FindItem(Weapon);if(!Gun)return true;
    // Left-hand reloads can begin from the equip queue during Advance.
    // Observe that start even while IsWeaponBusy() is already true; otherwise
    // the test waits until completion before ever sending its cancel input.
    if(AmmoStage==0&&PS->IsPistolReloadPending(Weapon))AmmoStage=1;
    if(AmmoStage==0&&PS->IsPistolServerReady(Weapon)&&!AuditPawn->IsWeaponBusy())
    {
        if(C.Switch)AuditPawn->StartAmmoSwitch(Weapon,PistolAmmoWire::Alternate(Model,*Gun));else AuditPawn->ReloadPressed();
        if(PS->IsPistolReloadPending(Weapon))AmmoStage=1;
    }
    if(AmmoStage==1)
    {
        if(!AmmoCancelled&&((C.Cancel&&Now-Started>.2)||(C.Partial&&Gun->Magazine==3&&AuditPawn->IsReloading())))
        {
            UE_LOG(LogTemp,Display,TEXT("PISTOL_AMMO_CANCEL_INPUT phase=%d dual=%d reloading=%d rounds=%d serial=%u"),Current,AuditPawn->DualPistols->IsActive(),AuditPawn->IsReloading(),Gun->Magazine,PS->PistolPendingReloads.FindRef(Weapon));
            if(AuditPawn->DualPistols->IsActive())AuditPawn->DualPistols->InterruptReloads();else AuditPawn->InterruptReload();AmmoCancelled=true;
        }
        if(!AuditPawn->IsReloading()&&!PS->IsPistolReloadPending(Weapon)&&(!C.Pair||!PS->IsPistolReloadPending(Weapon+TEXT("_L"))))
        {AmmoStage=2;AmmoNextShot=Now+.1;}
    }
    const int32 ShotsWanted=C.Cancel||C.Partial||C.Pair?0:3;
    if(AmmoStage==2&&AmmoFired<ShotsWanted&&Now>=AmmoNextShot)
    {
        const auto Before=AuditPawn->ShotsFired;
        if(AuditPawn->DualPistols->IsActive())
        {AuditPawn->DualPistols->Trigger(C.Side,true);AuditPawn->DualPistols->Advance(0.f);AuditPawn->DualPistols->Trigger(C.Side,false);}
        else AuditPawn->FireShot();
        if(AuditPawn->ShotsFired>Before){++AmmoFired;AmmoNextShot=Now+.2;}
    }
    const bool FinishedCase=AmmoStage==2&&AmmoFired==ShotsWanted&&PS->PistolPredictedShots.IsEmpty();
    if(!FinishedCase&&Now-Started<45.)return true;
    auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),PistolAmmoWire::Name(C));
    Row->SetBoolField(TEXT("executor_completed"),FinishedCase);Row->SetNumberField(TEXT("shots"),AmmoFired);
    Row->SetBoolField(TEXT("cancel_input_sent"),AmmoCancelled);
    Row->SetNumberField(TEXT("owner_rounds"),Gun->Magazine);Row->SetNumberField(TEXT("owner_cases"),PistolAmmo::Cases(*Gun));
    Row->SetStringField(TEXT("owner_ammo"),Model->AmmoDefinitionFor(*Gun));Row->SetBoolField(TEXT("owner_cycle"),WeaponReloadStages::NeedsCycle(*Gun));
    Row->SetNumberField(TEXT("owner_pouch"),Model->PouchCount(Model->AmmoDefinitionFor(*Gun)));
    if(C.Pair)Row->SetNumberField(TEXT("owner_left_rounds"),Model->FindItem(Weapon+TEXT("_L"))->Magazine);
    Results.Add(MakeShared<FJsonValueObject>(Row));bReported=true;
    FString Json;FJsonSerializer::Serialize(Row,TJsonWriterFactory<>::Create(&Json));ServerPistolAmmoResult(Current,Json);
    ShotgunWire::Save(Results,true,TEXT("client-observations"));return true;
}

void AShotgunWireAuditController::ServerPistolAmmoResult_Implementation(int32 Phase,const FString& Report)
{
    if(!PistolAmmoWire::Enabled()||Phase!=Expected||Finished!=Phase)return;
    auto* PS=GetPlayerState<AColdSteelPlayerState>();if(!PS||!PS->ShadowModel)return;
    const auto& C=PistolAmmoWire::Cases()[Phase];TSharedPtr<FJsonObject> Row;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Report),Row)||!Row)return;
    auto* Model=PS->ShadowModel.Get();const auto* Gun=Model->Equipped(C.Side?8:6);if(!Gun)return;
    const auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();const int32 Capacity=G->CalculateItem(*Gun,G->Installed(*Gun)).Capacity;
    bool Passed=Row->GetBoolField(TEXT("executor_completed"));
    const auto Check=[&](const TCHAR* Key,bool OK){Row->SetBoolField(Key,OK);Passed&=OK;};
    const int32 ExpectedRounds=C.Cancel?2:C.Partial?3:Capacity-3;
    Check(TEXT("owner_authority_magazine_match"),Row->GetNumberField(TEXT("owner_rounds"))==Gun->Magazine);
    Check(TEXT("owner_authority_ammo_match"),Row->GetStringField(TEXT("owner_ammo"))==Model->AmmoDefinitionFor(*Gun));
    Check(TEXT("owner_authority_pouch_match"),Row->GetNumberField(TEXT("owner_pouch"))==Model->PouchCount(Model->AmmoDefinitionFor(*Gun)));
    Check(TEXT("mechanism_closed"),!WeaponReloadStages::NeedsCycle(*Gun)&&!Row->GetBoolField(TEXT("owner_cycle")));
    if(C.Pair)
    {const auto* Left=Model->Equipped(8);Check(TEXT("shared_five_rounds"),Left&&Gun->Magazine+Left->Magazine==9&&Model->PouchCount(Model->AmmoDefinitionFor(*Gun))==0&&Row->GetNumberField(TEXT("owner_left_rounds"))==Left->Magazine);}
    else Check(TEXT("expected_final_rounds"),Gun->Magazine==ExpectedRounds);
    if(!C.Pair)
    {
        const int32 Spent=C.Cancel?0:C.Partial?1:C.Loader||C.Switch||C.Empty?Capacity:Capacity-2;
        Check(TEXT("actual_reserve_debit"),Model->PouchCount(Model->AmmoDefinitionFor(*Gun))==100-Spent);
    }
    if(!C.Cancel&&!C.Partial&&!C.Pair)
    {
        Check(TEXT("three_real_shots_registered"),PS->RegisteredPistolShots.Num()==3);
        bool Ammo=true;for(const auto& Pair:PS->RegisteredPistolShots)Ammo&=Pair.Value.Item.LoadedAmmoType==Model->AmmoDefinitionFor(*Gun);
        Check(TEXT("shot_frozen_ammo_is_current"),Ammo);
    }
    Row->SetBoolField(TEXT("passed"),Passed);Row->SetNumberField(TEXT("phase"),Phase);Results.Add(MakeShared<FJsonValueObject>(Row));
    bAllPassed&=Passed;++Finished;UE_LOG(LogTemp,Display,TEXT("PISTOL_AMMO_WIRE_CASE %d passed=%d %s"),Phase,Passed,*PistolAmmoWire::Name(C));
}

bool AShotgunWireAuditGameMode::TickPistolAmmo(float Delta)
{
    if(!PistolAmmoWire::Enabled())return false;Super::Tick(Delta);const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return true;}
    if(!Guest)return true;auto* AuditPawn=Cast<AFPSGAMECharacter>(Guest->GetPawn());auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!AuditPawn||!PS||!Model||!Model->IsAudit())return true;
    if(Guest->Finished>=PistolAmmoWire::Cases().Num())
    {ShotgunWire::Save(Guest->Results,Guest->bAllPassed,TEXT("listen-host-authority"));Guest->ClientFinish(Guest->bAllPassed);ExitAt=Now+3.;return true;}
    if(Prepared!=Guest->Finished)
    {
        if(Prepared==INDEX_NONE)PistolAmmoWire::Network(GetWorld());
        Prepared=Guest->Finished;Guest->Expected=Prepared;Weapon=FGuid::NewGuid().ToString();
        const auto Seed=PistolAmmoWire::Seed(Model,Weapon,PistolAmmoWire::Cases()[Prepared]);
        PS->StopPistolAuthority();PS->ServerGunLedgers.Reset();PS->RegisteredPistolShots.Reset();PS->PistolPouchDelta.Reset();PS->PistolPouchHistory.Reset();PS->PistolAmmoRevision=0;
        if(!PS->ShadowModel)PS->ShadowModel=Model->CreateShadowModel(Seed);else PS->ShadowModel->AdoptNetMirror(Seed);
        PS->ShadowModel->CurrentPawn=AuditPawn;AuditPawn->NetShadowProfile=PS->ShadowModel;AuditPawn->ApplyColdSteelProfile(PS->ShadowModel);
        PistolAmmoWire::Pin(AuditPawn);LastSetup=-10;
    }
    PS->TickPistolAuthority();
    if(Now-LastSetup>1.){LastSetup=Now;Guest->ClientSetup(Prepared,Weapon,AuditPawn);PS->SendPistolAmmo();}
    return true;
}
