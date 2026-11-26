#include "ShotgunAttachmentAuditCommandlet.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/PistolAmmoHelpers.h"
#include "../Skills/SkillNetworkAuditCommandlet.h"
#include "../UI/ColdSteelStatusModel.h"
#include "GunsmithSystem.h"
#include "PistolDualWieldComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

int32 UShotgunAttachmentAuditCommandlet::RunPistolAmmoAudit(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    FCommandLine::Set(*(FString(FCommandLine::Get())+TEXT(" -ShotgunAttachmentAudit -PistolPresentationWire -ColdSteelProfile=PistolAmmoAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits)));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("PistolAmmoAudit"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();auto* G=GI->GetSubsystem<UGunsmithSystem>();
    if(!World||!Model||!G||!Model->IsAudit())return 2;
    auto Seed=Model->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();Seed.DungeonRun={};
    auto* PC=World->SpawnActor<ASkillAuditRemoteController>();auto* PS=World->SpawnActor<AColdSteelPlayerState>();
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,1000,500),FRotator::ZeroRotator);
    PS->SetOwner(PC);PC->SetPlayerState(PS);PC->Possess(Pawn);Pawn->SetPlayerState(PS);
    auto* Shadow=Model->CreateShadowModel(Seed);PS->ShadowModel=Shadow;Pawn->NetShadowProfile=Shadow;Shadow->CurrentPawn=Pawn;
    Pawn->DispatchBeginPlay();Pawn->SetActorTickEnabled(false);
    int32 Failures=0;TArray<TSharedPtr<FJsonValue>> Rows,Skipped;uint32 Control=0,Shot=0;
    const auto Check=[&](bool Pass,const FString& Name)
    {auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),Pass);Rows.Add(MakeShared<FJsonValueObject>(Row));Failures+=!Pass;UE_LOG(LogTemp,Display,TEXT("PISTOL_AMMO_AUDIT %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),*Name);};
    const auto Configure=[&](TArray<FColdSteelItem> Items,int32 Reserve)
    {
        PS->StopPistolAuthority();PS->ServerGunLedgers.Reset();PS->RegisteredPistolShots.Reset();
        PS->PistolPouchDelta.Reset();PS->PistolPouchHistory.Reset();PS->PistolAmmoRevision=0;PS->IncomingPistolAmmoRevision=0;
        auto P=Seed;P.Items=MoveTemp(Items);P.AmmoPouch.Reset();
        for(const auto& Type:Model->AmmoCatalog())if(Type.Enabled)P.AmmoPouch.Add(Type.Id,Reserve);
        Shadow->AdoptNetMirror(P);Pawn->ApplyColdSteelProfile(Shadow);
    };
    const auto Complete=[&](const FString& Id)
    {if(auto* R=PS->PistolReloads.Find(Id);R&&R->Active){R->Started=World->GetTimeSeconds()-R->Duration-.02;PS->TickPistolAuthority();}};
    const TCHAR* Definitions[]={TEXT("ue_m1911"),TEXT("ue_g18"),TEXT("ue_pit_viper2011"),TEXT("ue_dan_wesson715"),TEXT("ue_rsh12")};
    for(const auto* Definition:Definitions)for(const int32 Cell:{6,8})
    {
        auto Gun=Model->CreateItem(Definition);Gun.Place=1;Gun.Cell=Cell;Gun.Magazine=2;Gun.VirtualMagazineAmmo=0;
        PistolAmmo::SetCases(Gun,PistolAmmo::Revolver(Gun)?(Gun.Definition==TEXT("ue_rsh12")?5:6):2);
        Configure({Gun},100);const int32 Capacity=G->CalculateItem(Gun,G->Installed(Gun)).Capacity;
        const FString Prefix=Gun.Definition+(Cell==6?TEXT("/right/"):TEXT("/left/"));
        const auto Before=Shadow->Snapshot();const FString Ammo=Shadow->AmmoDefinitionFor(Gun);
        PS->ServerPistolReload_Implementation(++Control,Gun.InstanceId,TEXT(""),6,Pawn);
        Check(PS->PistolReloads.FindRef(Gun.InstanceId).Active,Prefix+TEXT("tactical reload accepted"));
        Complete(Gun.InstanceId);
        Check(Shadow->FindItem(Gun.InstanceId)->Magazine==Capacity&&Shadow->PouchCount(Ammo)==100-(Capacity-2),Prefix+TEXT("actual insertion and reserve debit"));
        for(int32 N=0;N<3;++N)PS->ServerRememberPistolShot_Implementation(++Shot,Gun.InstanceId,6,1,Pawn);
        Check(Shadow->FindItem(Gun.InstanceId)->Magazine==Capacity-3&&PS->RegisteredPistolShots.Contains(Shot),Prefix+TEXT("third shot after tactical reload is accepted"));
        const int32 Count=Shadow->FindItem(Gun.InstanceId)->Magazine;
        PS->ServerRememberPistolShot_Implementation(Shot,Gun.InstanceId,6,1,Pawn);
        Check(Shadow->FindItem(Gun.InstanceId)->Magazine==Count,Prefix+TEXT("duplicate shot is not charged twice"));
        auto OldUpload=Before;PS->IncomingPistolAmmoRevision=0;PS->IncomingPistolIntent=0;
        Check(PS->RebasePistolUpload(OldUpload,Shadow->Snapshot(),false)&&OldUpload.Items[0].Magazine==Count&&OldUpload.AmmoPouch.FindRef(Ammo)==Shadow->PouchCount(Ammo),Prefix+TEXT("old upload cannot restore fired rounds or reserves"));
        FString Other;
        for(const auto& Type:Model->AmmoCatalog())if(Type.Enabled&&Type.Group==Model->AmmoGroupFor(Gun)&&Type.Id!=Ammo){Other=Type.Id;break;}
        if(Other.IsEmpty())Skipped.Add(MakeShared<FJsonValueString>(Prefix+TEXT("catalog has only one enabled ammo type")));
        if(!Other.IsEmpty())
        {
            PS->ServerPistolReload_Implementation(++Control,Gun.InstanceId,Other,6,Pawn);Complete(Gun.InstanceId);
            PS->ServerRememberPistolShot_Implementation(++Shot,Gun.InstanceId,6,1,Pawn);
            const auto* Fired=PS->RegisteredPistolShots.Find(Shot);
            Check(Fired&&Fired->Item.LoadedAmmoType==Other,Prefix+TEXT("first shot freezes confirmed new ammo"));
        }
        Configure({Gun},100);
        PS->ServerPistolReload_Implementation(++Control,Gun.InstanceId,TEXT(""),6,Pawn);
        auto& R=PS->PistolReloads.FindChecked(Gun.InstanceId);
        const uint32 ReloadSerial=R.Serial;
        PS->ServerPistolCancel_Implementation(++Control,Gun.InstanceId,ReloadSerial,Pawn);
        Check(Shadow->FindItem(Gun.InstanceId)->Magazine==2&&Shadow->PouchCount(Ammo)==100&&!R.Active,Prefix+TEXT("cancel before contact consumes nothing"));
        if(PistolAmmo::Revolver(Gun))
        {
            PS->ServerPistolReload_Implementation(++Control,Gun.InstanceId,TEXT(""),6,Pawn);
            auto& Partial=PS->PistolReloads.FindChecked(Gun.InstanceId);
            if(Partial.Seats.Num()>0)
            {
                Partial.Started=World->GetTimeSeconds()-Partial.Seats[0]-.01;PS->TickPistolAuthority();
                PS->ServerPistolCancel_Implementation(++Control,Gun.InstanceId,Partial.Serial,Pawn);
                Check(Shadow->FindItem(Gun.InstanceId)->Magazine==3&&WeaponReloadStages::NeedsCycle(*Shadow->FindItem(Gun.InstanceId)),Prefix+TEXT("one inserted round survives cancellation with open cylinder"));
                PS->ServerPistolReload_Implementation(++Control,Gun.InstanceId,TEXT(""),6,Pawn);Complete(Gun.InstanceId);
                Check(Shadow->FindItem(Gun.InstanceId)->Magazine==3&&!WeaponReloadStages::NeedsCycle(*Shadow->FindItem(Gun.InstanceId))&&Shadow->PouchCount(Ammo)==99,Prefix+TEXT("cycle-only recovery grants no new round"));
                if(!Other.IsEmpty())
                {
                    PS->ServerPistolReload_Implementation(++Control,Gun.InstanceId,Other,6,Pawn);
                    auto& Switching=PS->PistolReloads.FindChecked(Gun.InstanceId);
                    Check(Switching.Active&&!Switching.Seats.IsEmpty(),Prefix+TEXT("partial ammo switch accepted"));
                    if(!Switching.Seats.IsEmpty())
                    {
                        Switching.Started=World->GetTimeSeconds()-Switching.Seats[0]-.01;PS->TickPistolAuthority();
                        PS->ServerPistolCancel_Implementation(++Control,Gun.InstanceId,Switching.Serial,Pawn);
                    }
                    const auto* Switched=Shadow->FindItem(Gun.InstanceId);
                    Check(Switched->Magazine==1&&PistolAmmo::Cases(*Switched)==1&&Switched->LoadedAmmoType==Other,
                        Prefix+TEXT("interrupted ammo switch retains only the newly inserted cartridge"));
                }
            }
        }
        Gun.Magazine=0;PistolAmmo::SetCases(Gun,0);Configure({Gun},0);
        PS->ServerRememberPistolShot_Implementation(++Shot,Gun.InstanceId,6,1,Pawn);
        Check(!PS->RegisteredPistolShots.Contains(Shot)&&Shadow->FindItem(Gun.InstanceId)->Magazine==0,Prefix+TEXT("empty pistol never gains a timed capacity refill"));
    }
    auto Right=Model->CreateItem(TEXT("ue_m1911")),Left=Right;Right.Place=Left.Place=1;Right.Cell=6;Left.Cell=8;
    Left.InstanceId=TEXT("pistol-ammo-audit-left");Right.Magazine=Left.Magazine=2;Configure({Right,Left},5);
    PS->ServerPistolReload_Implementation(++Control,Right.InstanceId,TEXT(""),6,Pawn);
    PS->ServerPistolReload_Implementation(++Control,Left.InstanceId,TEXT(""),6,Pawn);
    for(auto& Pair:PS->PistolReloads)Pair.Value.Started=World->GetTimeSeconds()-Pair.Value.Duration-.02;
    PS->TickPistolAuthority();
    Check(Shadow->FindItem(Right.InstanceId)->Magazine+Shadow->FindItem(Left.InstanceId)->Magazine==9&&Shadow->PouchCount(Shadow->AmmoDefinitionFor(Right))==0,TEXT("two hands share five real reserve rounds without duplication"));
    Configure({Left},100);
    PS->ServerPistolReload_Implementation(++Control,Left.InstanceId,TEXT(""),6,Pawn);
    const uint32 OldReload=PS->PistolReloads.FindChecked(Left.InstanceId).Serial;
    Shadow->Current.ActiveWeaponSlot=9;PS->TickPistolAuthority();
    Check(!PS->PistolReloads.FindChecked(Left.InstanceId).Active&&Shadow->FindItem(Left.InstanceId)->Magazine==2,
        TEXT("switching to the other empty weapon group cancels left reload without adding ammo"));
    PS->ServerPistolReload_Implementation(++Control,Left.InstanceId,TEXT(""),9,Pawn);
    Check(!PS->PistolReloads.FindChecked(Left.InstanceId).Active,
        TEXT("offhand in the inactive group cannot reload in an empty group"));
    PS->ServerPistolReload_Implementation(++Control,Left.InstanceId,TEXT(""),6,Pawn);
    PS->ServerPistolCancel_Implementation(++Control,Left.InstanceId,OldReload,Pawn);
    Check(PS->PistolReloads.FindChecked(Left.InstanceId).Active,
        TEXT("old cancel serial cannot stop a newer reload on the same pistol"));
    auto Late=Shadow->Snapshot();Late.ActiveWeaponSlot=9;PS->IncomingPistolIntent=0;
    Check(PS->RebasePistolUpload(Late,Shadow->Snapshot(),false)&&Late.ActiveWeaponSlot==6,
        TEXT("profile captured before a reload intent cannot restore the stale weapon group"));
    const uint32 AcceptedControl=PS->PistolProcessedControl;
    auto* OtherPawn=World->SpawnActor<ACharacter>();
    PS->ServerPistolCancel_Implementation(++Control,Left.InstanceId,PS->PistolReloads.FindChecked(Left.InstanceId).Serial,OtherPawn);
    Check(PS->PistolProcessedControl==AcceptedControl&&PS->PistolReloads.FindChecked(Left.InstanceId).Active,
        TEXT("request from a different pawn cannot alter a live reload"));
    OtherPawn->Destroy();
    auto Root=MakeShared<FJsonObject>();Root->SetNumberField(TEXT("failures"),Failures);Root->SetBoolField(TEXT("passed"),Failures==0);
    Root->SetStringField(TEXT("scope"),TEXT("isolated production authority handlers, not UDP transport"));Root->SetArrayField(TEXT("checks"),Rows);
    Root->SetArrayField(TEXT("not_applicable"),Skipped);
    FString Output,Json;FParse::Value(*Params,TEXT("Output="),Output);FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));
    if(!Output.IsEmpty())FFileHelper::SaveStringToFile(Json,*Output);
    Model->CurrentPawn.Reset();Shadow->CurrentPawn.Reset();
    for(TActorIterator<AActor> It(World);It;++It)if(It->HasActorBegunPlay())
    {
        It->RouteEndPlay(EEndPlayReason::Quit);
        TInlineComponentArray<UActorComponent*> Components;It->GetComponents(Components);
        for(auto* Component:Components)if(Component->HasBegunPlay())Component->EndPlay(EEndPlayReason::Quit);
    }
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failures?1:0;
}
