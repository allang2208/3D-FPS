#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/GunsmithSystem.h"
#include "M4GunsmithWidget.h"
#include "ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"
#include "TimerManager.h"
#include "UnrealClient.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"

void AFPSGAMEPlayerController::RunM4GunsmithAudit()
{
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();auto* C=Cast<AFPSGAMECharacter>(GetPawn());
    if(!C||!P->IsAudit()||!P->ProfileSlot().Contains(TEXT("M4GunsmithAudit")))return;
    const FString Dir=FPaths::ProjectSavedDir()/TEXT("M4GunsmithAudit");IFileManager::Get().MakeDirectory(*Dir,true);
    auto Counts=MakeShared<FIntPoint>(0,0);
    auto Check=[Counts](bool Pass,const TCHAR* Name){Counts->X++;if(!Pass)Counts->Y++;UE_LOG(LogTemp,Display,TEXT("M4_GUNSMITH: %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Name);};
    const bool Load=FParse::Param(FCommandLine::Get(),TEXT("M4GunsmithLoadAudit"));
    auto State=P->Snapshot();
    if(!Load){State.Items.Reset();State.Hotbar.Init(TEXT(""),4);State.HotbarDefinitions.Init(TEXT(""),4);auto Gun=P->CreateItem(TEXT("ue_m4a1"));Gun.Place=1;Gun.Cell=9;Gun.Magazine=17;State.Items.Add(Gun);State.ActiveWeaponSlot=9;auto Ammo=P->CreateItem(TEXT("ammo_556"),40);Ammo.Cell=0;State.Items.Add(Ammo);Check(P->CommitState(State),TEXT("seed isolated secondary-slot M4"));}
    else Check(P->Equipped()&&G->Installed(*P->Equipped()).FindRef(TEXT("optic"))==TEXT("holographic")&&C->HasHolographicOptic(),TEXT("new process restores saved holographic M4"));
    auto Later=[this](float Time,TFunction<void()> Fn){FTimerHandle H;GetWorldTimerManager().SetTimer(H,[Fn](){Fn();},Time,false);};
    Later(3.f,[this,P,G,C,Check,Load,Dir](){
        Check(C->ValidateFoldingSights(Load),TEXT("initial sight heads match saved optic state"));
        Check(G->Weapon(TEXT("ue_m4a1"))&&!G->Weapon(TEXT("fps_akm"))&&!G->Weapon(TEXT("fps_hk416")),TEXT("native M4 catalog only; retired guns remain absent"));
        Check(OpenGunsmith(),TEXT("open actual equipped instance"));if(!GunsmithPanel)return;
        Check(!G->Select(TEXT("optic"),TEXT("invalid"))&&!G->Select(TEXT("stock"),TEXT("true")),TEXT("reject unsupported parts"));
        if(!Load){
            GunsmithPanel->Choose(true);
            Check(C->HasHolographicOptic()&&G->Installed(*P->Equipped()).IsEmpty(),TEXT("draft previews mesh without mutating inventory"));
            P->AuditFailNextSave=true;Check(!GunsmithPanel->ApplyDraft()&&G->Installed(*P->Equipped()).IsEmpty(),TEXT("failed save rolls back installed configuration"));
            Check(GunsmithPanel->ApplyDraft(),TEXT("apply through checked save transaction"));
        }
        Check(G->Installed(*P->Equipped()).FindRef(TEXT("optic"))==TEXT("holographic")&&P->Equipped()->Magazine==17,TEXT("installed optic and magazine preserved"));
        GunsmithPanel->SetAimPreview(true);
        FScreenshotRequest::RequestScreenshot(Dir/TEXT("m4-gunsmith-panel.png"),true,false);
    });
    Later(5.f,[this,C,Check,Dir](){float Error;Check(C->ValidateGunsmithSight(Error),TEXT("holographic reticle within two pixels of aim axis"));UE_LOG(LogTemp,Display,TEXT("M4_GUNSMITH: reticle_error_px=%.4f"),Error);
        float Roll,RailError;Check(C->MeasureHolographicOrientation(Roll,RailError),TEXT("read rendered optic orientation"));
        Check(C->ValidateFoldingSights(true),TEXT("both sight heads fold ninety degrees around fixed pivots"));
        UE_LOG(LogTemp,Display,TEXT("M4_GUNSMITH: ads_roll_deg=%.4f rail_error_deg=%.4f"),Roll,RailError);
        Check(FMath::Abs(Roll)<.2f,TEXT("ADS optic frame is level"));Check(RailError<.2f,TEXT("optic up axis matches weapon rail"));
        FScreenshotRequest::RequestScreenshot(Dir/TEXT("m4-holographic-ads.png"),true,false);});
    Later(6.f,[this,P,G,C,Check](){
        if(!GunsmithPanel)return;GunsmithPanel->Choose(false);Check(!C->HasHolographicOptic(),TEXT("remove preview hides mesh"));
        CloseGunsmith();Check(C->HasHolographicOptic()&&G->Installed(*P->Equipped()).FindRef(TEXT("optic"))==TEXT("holographic"),TEXT("close discards unapplied removal"));
        Check(!IsMoveInputIgnored()&&!IsLookInputIgnored()&&!bShowMouseCursor,TEXT("menu close restores gameplay input"));
        Check(OpenGunsmith(),TEXT("reopen"));if(!GunsmithPanel)return;GunsmithPanel->Choose(false);Check(GunsmithPanel->ApplyDraft()&&!C->HasHolographicOptic(),TEXT("apply removal restores iron sight"));CloseGunsmith();
        Check(P->ReloadProfile()&&!C->HasHolographicOptic()&&G->Installed(*P->Equipped()).IsEmpty(),TEXT("removal survives profile reload"));
        Check(OpenGunsmith(),TEXT("open to reinstall"));if(!GunsmithPanel)return;GunsmithPanel->Choose(true);Check(GunsmithPanel->ApplyDraft(),TEXT("reinstall and save"));CloseGunsmith();
        Check(P->ReloadProfile()&&C->HasHolographicOptic(),TEXT("saved holographic state rebinds visual"));
    });
    Later(7.f,[this,Dir](){FScreenshotRequest::RequestScreenshot(Dir/TEXT("m4-holographic-hip.png"),true,false);});
    Later(8.f,[P,C,Check](){Check(C->GetMagazineAmmo()==17&&P->AmmoCount()==40,TEXT("no ammo loss during repeated changes"));});
    Later(7.5f,[C,Check](){Check(C->ValidateFoldingSights(true),TEXT("cancel and profile reload restore folded heads"));});
    Later(10.2f,[C,Check](){Check(C->ValidateFoldingSights(true),TEXT("folded heads stay on receiver during reload"));});
    Later(14.f,[this](){if(OpenGunsmith()&&GunsmithPanel)GunsmithPanel->Choose(false);});
    Later(14.5f,[this,C,Check,Dir](){Check(C->ValidateFoldingSights(false),TEXT("removal unfolds both original sight heads"));if(GunsmithPanel)GunsmithPanel->SetAimPreview(true);});
    Later(14.6f,[P,Check](){Check(P->SaveNow(),TEXT("autosave succeeds during unapplied iron preview"));});
    Later(15.2f,[this,C,P,G,Check,Dir](){Check(!C->HasHolographicOptic()&&C->ValidateFoldingSights(false),TEXT("autosave does not overwrite upright iron preview"));Check(G->Installed(*P->Equipped()).FindRef(TEXT("optic"))==TEXT("holographic"),TEXT("preview remains transient after autosave"));FScreenshotRequest::RequestScreenshot(Dir/TEXT("m4-iron-restored.png"),true,false);});
    Later(15.6f,[this](){CloseGunsmith();});
    Later(16.5f,[C,Check](){Check(C->ValidateFoldingSights(true),TEXT("cancel removal restores folded state after switching weapons"));});
    Later(8.1f,[this](){InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::RightMouseButton,IE_Pressed,1));});
    Later(8.7f,[this,C,Check](){Check(C->IsAiming(),TEXT("gameplay aim input after menu close"));InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Pressed,1));});
    Later(8.8f,[this](){InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Released,0));});
    auto Shots=MakeShared<int32>(0);
    Later(9.f,[this,C,Check,Shots,Dir](){*Shots=17-C->GetMagazineAmmo();Check(*Shots>0&&*Shots<=2,TEXT("fire input consumes rounds"));Check(C->ValidateHolographicShot(),TEXT("shot ray follows visible reticle during recoil"));FScreenshotRequest::RequestScreenshot(Dir/TEXT("m4-holographic-fire.png"),true,false);InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::R,IE_Pressed,1));});
    Later(9.1f,[this,C,Check](){InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::R,IE_Released,0));Check(C->IsReloading()&&C->HasHolographicOptic(),TEXT("reload keeps optic attached"));});
    Later(10.f,[this,C,Check,Dir](){float Roll,RailError;Check(C->MeasureHolographicOrientation(Roll,RailError)&&RailError<.2f,TEXT("reload preserves rail alignment"));FScreenshotRequest::RequestScreenshot(Dir/TEXT("m4-holographic-reload.png"),true,false);});
    Later(13.f,[this,C,P,G,Check,Shots](){
        Check(!C->IsReloading()&&C->GetMagazineAmmo()==30&&P->AmmoCount()==27-*Shots,TEXT("reload completes with exact ammo conservation"));
        InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::RightMouseButton,IE_Released,0));
        auto S=P->Snapshot();const FString First=P->Equipped()->InstanceId;
        for(auto& I:S.Items){if(I.InstanceId==First)I.Magazine=17;if(I.Definition==TEXT("ammo_556"))I.Count=40;}
        if(!P->Equipped(6)){auto Other=P->CreateItem(TEXT("ue_m4a1"));Other.Place=1;Other.Cell=6;Other.Magazine=11;S.Items.Add(Other);}
        S.ActiveWeaponSlot=6;Check(P->CommitState(S)&&!C->HasHolographicOptic()&&G->Installed(*P->Equipped()).IsEmpty(),TEXT("second M4 does not inherit first instance optic"));
        S=P->Snapshot();S.ActiveWeaponSlot=9;Check(P->CommitState(S)&&C->HasHolographicOptic(),TEXT("switching back restores first instance optic"));
        Check(OpenGunsmith(),TEXT("open while secondary-slot weapon equips"));if(GunsmithPanel){GunsmithPanel->Choose(false);Check(!GunsmithPanel->ApplyDraft(),TEXT("active secondary-slot equip blocks modification"));CloseGunsmith();}
    });
    Later(17.f,[this,Counts,Dir](){UE_LOG(LogTemp,Display,TEXT("M4_GUNSMITH: COMPLETE checks=%d failures=%d"),Counts->X,Counts->Y);FFileHelper::SaveStringToFile(FString::Printf(TEXT("checks=%d failures=%d"),Counts->X,Counts->Y),*(Dir/TEXT("result.txt")));ConsoleCommand(TEXT("quit"));});
}
