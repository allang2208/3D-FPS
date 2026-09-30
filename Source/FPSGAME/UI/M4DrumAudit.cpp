#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/GunsmithSystem.h"
#include "ColdSteelStatusModel.h"
#include "M4GunsmithWidget.h"
#include "Engine/GameInstance.h"
#include "TimerManager.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "UnrealClient.h"

void AFPSGAMEPlayerController::RunM4DrumAudit()
{
 auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();auto* C=Cast<AFPSGAMECharacter>(GetPawn());
 if(!C||!P->IsAudit()||!P->ProfileSlot().Contains(TEXT("M4DrumAudit")))return;
 const FString Dir=FPaths::ProjectSavedDir()/TEXT("M4DrumAudit");IFileManager::Get().MakeDirectory(*Dir,true);
 auto Counts=MakeShared<FIntPoint>(0,0);auto Check=[Counts](bool Pass,const TCHAR* Name){++Counts->X;if(!Pass)++Counts->Y;UE_LOG(LogTemp,Display,TEXT("M4_DRUM: %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Name);};
 auto Later=[this](float T,TFunction<void()> F){FTimerHandle H;GetWorldTimerManager().SetTimer(H,[F](){F();},T,false);};
 auto Ammo=[P](FColdSteelProfile& S,int32 Count){S.Items.RemoveAll([](const auto& I){return I.Place==0;});int32 Cell=0;while(Count>0){auto A=P->CreateItem(TEXT("ammo_556"));A.Count=FMath::Min<int64>(Count,A.StackMax);Count-=A.Count;A.Cell=Cell++;S.Items.Add(A);}};
 // Drum contract: +30 rounds over the factory magazine (60 total, 2026-09-17)
 // plus the shared M4DrumReloadTiming scales. Read it from the catalog so
 // retuning gunsmith.json keeps this audit valid instead of pinning the
 // superseded Godot snapshot (50 rounds, x1.75 only, ADS 0.24/1.15).
 const auto Drum=G->Calculate(TEXT("ue_m4a1"),{{TEXT("magazine"),TEXT("large_drum")}});
 const int32 DrumCapacity=Drum.Capacity,FactoryCapacity=30,DrumOverflow=DrumCapacity-FactoryCapacity;
 const double DrumNormalReload=Drum.Reload,DrumEmptyReload=Drum.EmptyReload;
 const bool Load=FParse::Param(FCommandLine::Get(),TEXT("M4DrumLoadAudit"));
 if(Load)Check(C->HasGunsmithDrum()&&C->GetMagazineCapacity()==DrumCapacity&&C->GetMagazineAmmo()==17&&G->Installed(*P->Equipped()).FindRef(TEXT("magazine"))==TEXT("large_drum"),TEXT("new process restores installed drum, capacity and rounds"));
 else {auto S=P->Snapshot();S.Items.Reset();S.Hotbar.Init(TEXT(""),4);S.HotbarDefinitions.Init(TEXT(""),4);auto I=P->CreateItem(TEXT("ue_m4a1"));I.Place=1;I.Cell=9;I.Magazine=17;S.Items.Add(I);S.ActiveWeaponSlot=9;Ammo(S,140);Check(P->CommitState(S),TEXT("seed isolated profile"));}
 Later(3.f,[this,P,G,C,Check,Load](){
  Check(OpenGunsmith(),TEXT("open actual M4 gunsmith"));if(!GunsmithPanel)return;
  GunsmithPanel->ChooseDrum(true);GunsmithPanel->Choose(true);
  Check(C->HasGunsmithDrum()&&C->ValidateDrumAttachment(),TEXT("draft attaches drum and removes entire original magazine"));
  G->Undo();GunsmithPanel->ChooseDrum(G->Draft().FindRef(TEXT("magazine"))==TEXT("large_drum"));GunsmithPanel->Choose(G->Draft().FindRef(TEXT("optic"))==TEXT("holographic"));
  Check(G->Pending()==0&&C->HasGunsmithDrum()==Load&&C->GetMagazineAmmo()==17,TEXT("undo restores installed appearance without changing rounds"));
  GunsmithPanel->ChooseDrum(true);GunsmithPanel->Choose(true);
  if(!Load){Check(C->GetMagazineCapacity()==30&&C->GetMagazineAmmo()==17,TEXT("visual preview does not mutate live ammo or capacity"));P->AuditFailNextSave=true;Check(!GunsmithPanel->ApplyDraft()&&C->GetMagazineCapacity()==30,TEXT("failed save preserves installed capacity"));}
  if(Load)Check(G->Pending()==0&&!GunsmithPanel->ApplyDraft()&&C->GetMagazineAmmo()==17,TEXT("restored configuration needs no duplicate application"));
  else Check(GunsmithPanel->ApplyDraft(),TEXT("apply drum through saved instance transaction"));
  const auto S=G->Calculate(TEXT("ue_m4a1"),G->Installed(*P->Equipped()));
  Check(C->GetMagazineCapacity()==S.Capacity&&C->GetMagazineAmmo()==17&&FMath::IsNearlyEqual(C->GetADSSeconds(),float(S.ADS),.0001f),TEXT("runtime capacity and ADS match the catalog drum"));
  Check(FMath::IsNearlyEqual(C->GetReloadSeconds(false),float(S.Reload),.0001f)&&FMath::IsNearlyEqual(C->GetReloadSeconds(true),float(S.EmptyReload),.0001f),TEXT("catalog and gameplay share the drum reload contract"));
 });
 Later(3.5f,[this](){if(GunsmithPanel)GunsmithPanel->SetSidePreview(true);});
 Later(4.f,[this,Dir](){FScreenshotRequest::RequestScreenshot(Dir/TEXT("drum-panel.png"),true,false);});
 Later(4.5f,[this](){if(GunsmithPanel)GunsmithPanel->SetAimPreview(true);});
 Later(5.5f,[this,C,Check,Dir](){float E;Check(C->ValidateGunsmithSight(E)&&C->ValidateDrumAttachment()&&C->ValidateFoldingSights(true),TEXT("drum and holographic combination keeps ADS and folding sights"));FScreenshotRequest::RequestScreenshot(Dir/TEXT("drum-ads.png"),true,false);});
 Later(6.f,[this](){CloseGunsmith();});
 Later(6.7f,[this,Dir](){FScreenshotRequest::RequestScreenshot(Dir/TEXT("drum-hip.png"),true,false);});
 Later(7.f,[this](){InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::R,IE_Pressed,1));});
 Later(7.1f,[this,C,Check](){InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::R,IE_Released,0));Check(C->IsReloading(),TEXT("normal reload starts from actual input"));});
 Later(8.4f,[this,C,Check,Dir](){Check(C->ValidateDrumAttachment()&&C->GetMagazineAmmo()==17,TEXT("withdrawn drum follows animated magazine bone without early refill"));FScreenshotRequest::RequestScreenshot(Dir/TEXT("drum-withdraw.png"),true,false);});
 Later(9.6f,[this,C,Check,Dir](){Check(C->ValidateDrumAttachment(),TEXT("drum stays attached during insertion"));FScreenshotRequest::RequestScreenshot(Dir/TEXT("drum-insert.png"),true,false);});
 Later(float(7.f+DrumNormalReload-.4f),[C,Check](){Check(C->IsReloading()&&C->GetMagazineAmmo()==17,TEXT("normal reload still running before the catalog duration"));});
 Later(12.f,[P,C,Check,DrumCapacity](){Check(!C->IsReloading()&&C->GetMagazineAmmo()==DrumCapacity&&P->AmmoCount()==(C->HasInfiniteReserveAmmo()?140:140-(DrumCapacity-17)),TEXT("normal reload respects scene reserve policy"));});
 Later(13.f,[this,P,C,Check,Ammo](){auto S=P->Snapshot();for(auto& I:S.Items)if(I.InstanceId==P->Equipped()->InstanceId)I.Magazine=0;Ammo(S,140);Check(P->CommitState(S),TEXT("seed empty drum"));if(!C->HasInfiniteReserveAmmo())InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::R,IE_Pressed,1));});
 Later(13.1f,[this,C,Check](){InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::R,IE_Released,0));Check(C->IsReloading(),TEXT("empty reload starts"));});
 Later(16.1f,[this,C,Check,Dir](){Check(C->ValidateDrumAttachment()&&C->GetMagazineAmmo()==0,TEXT("empty drum stays empty through seating action"));FScreenshotRequest::RequestScreenshot(Dir/TEXT("drum-empty-insert.png"),true,false);});
 Later(float(13.f+DrumEmptyReload-.5f),[this,C,Check,Dir](){Check(C->IsReloading()&&C->GetMagazineAmmo()==0&&C->ValidateDrumAttachment(),TEXT("empty reload waits for bolt release and full duration"));FScreenshotRequest::RequestScreenshot(Dir/TEXT("drum-bolt-release.png"),true,false);});
 Later(19.5f,[P,C,Check,DrumCapacity](){Check(!C->IsReloading()&&C->GetMagazineAmmo()==DrumCapacity&&P->AmmoCount()==(C->HasInfiniteReserveAmmo()?140:140-DrumCapacity),TEXT("empty reload fills the drum and respects scene reserve policy"));});
 Later(20.f,[this,P,G,C,Check,DrumCapacity,DrumOverflow,FactoryCapacity](){
  Check(OpenGunsmith(),TEXT("open installed full drum"));if(!GunsmithPanel)return;GunsmithPanel->ChooseDrum(false);
  Check(!C->HasGunsmithDrum()&&C->GetMagazineAmmo()==DrumCapacity&&C->GetMagazineCapacity()==DrumCapacity,TEXT("removal preview retains installed full magazine"));
  Check(P->SaveNow()&&!C->HasGunsmithDrum(),TEXT("autosave preserves standard-magazine preview"));
  const auto Original=P->Snapshot();auto Full=Original;Full.Items.RemoveAll([](const auto& I){return I.Place==0;});
  for(int32 Cell=0;Cell<72;++Cell){auto A=P->CreateItem(TEXT("ammo_556"));A.Count=A.StackMax;A.Cell=Cell;Full.Items.Add(A);}
  Check(P->CommitState(Full),TEXT("fill isolated backpack with full compatible stacks"));
  Check(!GunsmithPanel->ApplyDraft()&&P->Equipped()->Magazine==DrumCapacity&&C->GetMagazineCapacity()==DrumCapacity&&G->Installed(*P->Equipped()).FindRef(TEXT("magazine"))==TEXT("large_drum"),TEXT("no room for overflow rejects removal atomically"));
  Check(P->CommitState(Original),TEXT("restore isolated backpack"));P->AuditFailNextSave=true;
  Check(!GunsmithPanel->ApplyDraft()&&P->Equipped()->Magazine==DrumCapacity&&P->AmmoCount()==(C->HasInfiniteReserveAmmo()?140:140-DrumCapacity),TEXT("save failure rolls back overflow transfer"));
  Check(GunsmithPanel->ApplyDraft()&&C->GetMagazineCapacity()==FactoryCapacity&&C->GetMagazineAmmo()==FactoryCapacity&&P->AmmoCount()==(C->HasInfiniteReserveAmmo()?140+DrumOverflow:140-FactoryCapacity),TEXT("removal returns the drum overflow exactly once"));
  CloseGunsmith();Check(P->ReloadProfile()&&!C->HasGunsmithDrum()&&C->GetMagazineCapacity()==30,TEXT("saved removal restores standard magazine"));
 });
 Later(21.f,[this,Dir](){FScreenshotRequest::RequestScreenshot(Dir/TEXT("drum-removed.png"),true,false);});
 Later(22.f,[this,P,C,Check,Ammo](){if(!OpenGunsmith()||!GunsmithPanel){Check(false,TEXT("reopen for saved fixture"));return;}GunsmithPanel->ChooseDrum(true);Check(GunsmithPanel->ApplyDraft(),TEXT("reinstall drum"));CloseGunsmith();auto S=P->Snapshot();for(auto& I:S.Items)if(I.InstanceId==P->Equipped()->InstanceId)I.Magazine=17;Ammo(S,140);Check(P->CommitState(S),TEXT("persist seventeen rounds for restart"));});
 Later(23.f,[this](){InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Pressed,1));});
 Later(23.1f,[this](){InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Released,0));});
 Later(23.5f,[P,C,Check](){Check(C->GetMagazineAmmo()<17&&C->GetMagazineAmmo()>=15&&C->ValidateDrumAttachment(),TEXT("firing uses installed drum and keeps its attachment"));auto S=P->Snapshot();for(auto& I:S.Items)if(I.InstanceId==P->Equipped()->InstanceId)I.Magazine=17;Check(P->CommitState(S),TEXT("reset restart fixture after firing"));});
 Later(24.f,[this,P,C,Check](){auto S=P->Snapshot();if(!P->Equipped(6)){auto I=P->CreateItem(TEXT("ue_m4a1"));I.Place=1;I.Cell=6;I.Magazine=11;S.Items.Add(I);}S.ActiveWeaponSlot=6;Check(P->CommitState(S)&&!C->HasGunsmithDrum()&&C->GetMagazineCapacity()==30&&C->GetMagazineAmmo()==11,TEXT("other M4 retains standard magazine and its own rounds"));});
 Later(26.f,[P,C,Check,DrumCapacity](){auto S=P->Snapshot();S.ActiveWeaponSlot=9;Check(P->CommitState(S)&&C->HasGunsmithDrum()&&C->GetMagazineCapacity()==DrumCapacity&&C->GetMagazineAmmo()==17,TEXT("switch back restores instance drum"));});
 Later(29.f,[this,Counts](){UE_LOG(LogTemp,Display,TEXT("M4_DRUM: COMPLETE checks=%d failures=%d"),Counts->X,Counts->Y);ConsoleCommand(TEXT("quit"));});
}
