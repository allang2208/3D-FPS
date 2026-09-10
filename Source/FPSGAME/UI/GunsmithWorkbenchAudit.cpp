#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/GunsmithSystem.h"
#include "M4GunsmithWidget.h"
#include "ColdSteelStatusModel.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/GameInstance.h"
#include "Engine/Engine.h"
#include "TimerManager.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "UnrealClient.h"
#include "Framework/Application/SlateApplication.h"
#include "Widgets/SWindow.h"
#include "InputCoreTypes.h"

void AFPSGAMEPlayerController::RunGunsmithWorkbenchAudit()
{
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();auto* C=Cast<AFPSGAMECharacter>(GetPawn());
    if(!C||!P->IsAudit()||!P->ProfileSlot().Contains(TEXT("WorkbenchAudit")))return;
    const FString Dir=FPaths::ProjectSavedDir()/TEXT("GunsmithWorkbenchAudit");IFileManager::Get().MakeDirectory(*Dir,true);
    auto Counts=MakeShared<FIntPoint>(0,0);auto Check=[Counts](bool Pass,const TCHAR* Name){++Counts->X;if(!Pass)++Counts->Y;UE_LOG(LogTemp,Display,TEXT("WORKBENCH: %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Name);};
    auto PreviewWorlds=[](){int32 N=0;for(const auto& Context:GEngine->GetWorldContexts())if(Context.WorldType==EWorldType::GamePreview&&Context.World())++N;return N;};
    const int32 BaselineWorlds=PreviewWorlds();
    auto Later=[this](float T,TFunction<void()> F){FTimerHandle H;GetWorldTimerManager().SetTimer(H,[F](){F();},T,false);};
    auto S=P->Snapshot();S.Items.Reset();auto I=P->CreateItem(TEXT("ue_m4a1"));I.Place=1;I.Cell=9;I.Magazine=17;S.Items.Add(I);S.ActiveWeaponSlot=9;
    Check(P->CommitState(S),TEXT("seed isolated profile"));
    Later(3,[this,C,G,Check,PreviewWorlds,BaselineWorlds](){Check(OpenGunsmith(),TEXT("open workbench"));if(!GunsmithPanel)return;
        Check(GunsmithPanel->HasWorkbenchCapture(),TEXT("live model render target created"));
        Check(PreviewWorlds()==BaselineWorlds+1,TEXT("isolated studio world created"));
        GunsmithPanel->Choose(true);GunsmithPanel->ChooseDrum(true);
        const auto& Rows=GunsmithPanel->GetOverviewRows();
        Check(Rows.Num()==18&&Rows.ContainsByPredicate([](const auto& R){return R.Label==TEXT("枪械稳定性 ↑");}),TEXT("all eighteen overview rows include quantified handling"));
        const auto* Capacity=Rows.FindByPredicate([](const auto& R){return R.Label==TEXT("弹匣容量");});
        const auto* ADS=Rows.FindByPredicate([](const auto& R){return R.Label==TEXT("开镜耗时");});
        const auto* Reload=Rows.FindByPredicate([](const auto& R){return R.Label==TEXT("普通换弹");});
        const auto* Speed=Rows.FindByPredicate([](const auto& R){return R.Label==TEXT("子弹速度");});
        Check(Capacity&&Capacity->Current==TEXT("30 发")&&Capacity->Final==TEXT("50 发")&&Capacity->Benefit==1,TEXT("capacity before after and benefit"));
        Check(ADS&&ADS->Current==TEXT("240 ms")&&ADS->Final==TEXT("209 ms")&&ADS->Benefit==1,TEXT("faster ADS uses lower-is-better semantics"));
        Check(Reload&&Reload->Benefit==-1&&Reload->Final==FString::Printf(TEXT("%.2f s"),G->Calculate(G->Definition(),G->Draft()).Reload),TEXT("reload display derives from current catalog"));
        Check(Speed&&Speed->Final==TEXT("即时命中"),TEXT("hitscan does not display zero projectile speed"));
        Check(C->GetMagazineCapacity()==30&&C->GetMagazineAmmo()==17,TEXT("presentation preview preserves live ammo"));
    });
    Later(4,[this,C,G,Check](){
        if(!GunsmithPanel)return;auto Surface=GunsmithPanel->GetPreviewSurface();auto& App=FSlateApplication::Get();
        auto Window=App.FindWidgetWindow(Surface.ToSharedRef());Check(Window.IsValid(),TEXT("preview input has a Slate window"));if(!Window)return;
        const auto Geometry=Surface->GetCachedGeometry();const FVector2D Start=Geometry.LocalToAbsolute(Geometry.GetLocalSize()*.5f);
        const FVector2D End=Geometry.LocalToAbsolute(Geometry.GetLocalSize()*.5f+FVector2D(140,-50));
        const auto Facing=C->GetControlRotation();const TSet<FKey> Held{EKeys::LeftMouseButton},None;
        App.ProcessMouseMoveEvent(FPointerEvent(0,Start,Start,None,FKey(),0,FModifierKeysState()),false);
        App.ProcessMouseButtonDownEvent(Window->GetNativeWindow(),FPointerEvent(0,Start,Start,Held,EKeys::LeftMouseButton,0,FModifierKeysState()));
        Check(Surface->HasMouseCapture(),TEXT("left drag captures preview surface"));
        App.ProcessMouseMoveEvent(FPointerEvent(0,End,Start,Held,FKey(),0,FModifierKeysState()),false);
        const auto Orbit=GunsmithPanel->GetPreviewOrbit();Check(Orbit.X>40&&Orbit.Y>10,TEXT("routed mouse movement rotates both axes"));
        const FVector2D Outside=Geometry.LocalToAbsolute(FVector2D(Geometry.GetLocalSize().X+80,Geometry.GetLocalSize().Y*.5f));
        App.ProcessMouseButtonUpEvent(FPointerEvent(0,Outside,End,None,EKeys::LeftMouseButton,0,FModifierKeysState()));
        Check(!Surface->HasMouseCapture(),TEXT("release outside preview clears mouse capture"));
        App.ProcessMouseMoveEvent(FPointerEvent(0,Outside+FVector2D(30,0),Outside,None,FKey(),0,FModifierKeysState()),false);
        Check(GunsmithPanel->GetPreviewOrbit().Equals(Orbit,.01),TEXT("mouse motion after release does not rotate"));
        Check(C->GetControlRotation().Equals(Facing,.01)&&G->Pending()==2&&C->GetMagazineAmmo()==17,TEXT("drag preserves player facing configuration and ammo"));
    });
    Later(5.5f,[Dir](){FScreenshotRequest::RequestScreenshot(Dir/TEXT("workbench-rotated.png"),true,false);});
    Later(6,[this,Check](){if(!GunsmithPanel)return;auto Surface=GunsmithPanel->GetPreviewSurface();auto& App=FSlateApplication::Get();auto Window=App.FindWidgetWindow(Surface.ToSharedRef());if(!Window)return;
        const auto Geometry=Surface->GetCachedGeometry();const FVector2D At=Geometry.LocalToAbsolute(Geometry.GetLocalSize()*.5f);const TSet<FKey> Held{EKeys::LeftMouseButton};
        App.ProcessMouseButtonDoubleClickEvent(Window->GetNativeWindow(),FPointerEvent(0,At,At,Held,EKeys::LeftMouseButton,0,FModifierKeysState()));
        Check(GunsmithPanel->GetPreviewOrbit().IsNearlyZero()&&!Surface->HasMouseCapture(),TEXT("double click restores horizontal pose"));
    });
    Later(7,[Dir](){FScreenshotRequest::RequestScreenshot(Dir/TEXT("workbench-draft.png"),true,false);});
    Later(8,[this,P,G,Check](){if(!GunsmithPanel)return;P->AuditFailNextSave=true;Check(!GunsmithPanel->ApplyDraft()&&G->Pending()==2,TEXT("failed save retains draft"));Check(GunsmithPanel->ApplyDraft(),TEXT("apply uses existing transaction"));
        bool Unchanged=true;for(const auto& R:GunsmithPanel->GetOverviewRows())Unchanged&=R.Delta==TEXT("—");Check(Unchanged,TEXT("after application current comparison has no deltas"));
        GunsmithPanel->SetCompareFactory(true);const auto& Rows=GunsmithPanel->GetOverviewRows();Check(Rows[1].Current==TEXT("30 发")&&Rows[1].Delta==TEXT("+20 发"),TEXT("factory comparison retains cumulative attachment impact"));
        GunsmithPanel->SelectCategory(TEXT("optic"));
    });
    Later(10,[Dir](){FScreenshotRequest::RequestScreenshot(Dir/TEXT("workbench-factory.png"),true,false);});
    Later(11,[this](){if(GunsmithPanel)GunsmithPanel->SetAimPreview(true);});
    Later(13,[C,Check,Dir](){float E=0;Check(C->ValidateGunsmithSight(E)&&C->ValidateFoldingSights(true),TEXT("live ADS and folding sights preserved"));FScreenshotRequest::RequestScreenshot(Dir/TEXT("workbench-ads.png"),true,false);});
    Later(14,[this,P,C,Check,PreviewWorlds,BaselineWorlds](){auto* Panel=GunsmithPanel.Get();if(!Panel)return;
        auto Surface=Panel->GetPreviewSurface();auto& App=FSlateApplication::Get();auto Window=App.FindWidgetWindow(Surface.ToSharedRef());
        if(Window){const auto Geometry=Surface->GetCachedGeometry();const FVector2D At=Geometry.LocalToAbsolute(Geometry.GetLocalSize()*.5f);const TSet<FKey> Held{EKeys::LeftMouseButton};App.ProcessMouseButtonDownEvent(Window->GetNativeWindow(),FPointerEvent(0,At,At,Held,EKeys::LeftMouseButton,0,FModifierKeysState()));}
        Check(Surface->HasMouseCapture(),TEXT("begin captured drag before closing"));CloseGunsmith();Check(!Surface->HasMouseCapture(),TEXT("closing during drag releases pointer"));
        Check(!Panel->HasWorkbenchCapture()&&PreviewWorlds()==BaselineWorlds,TEXT("close releases capture and studio world"));Check(C->HasGunsmithDrum()&&C->GetMagazineCapacity()==50,TEXT("closing preserves applied configuration"));Check(P->ReloadProfile()&&C->HasGunsmithDrum(),TEXT("saved configuration restores"));});
    Later(15,[this,G,Check](){Check(OpenGunsmith(),TEXT("reopen workbench"));if(!GunsmithPanel)return;GunsmithPanel->ChooseDrum(false);G->Undo();GunsmithPanel->ChooseDrum(G->Draft().FindRef(TEXT("magazine"))==TEXT("large_drum"));Check(G->Pending()==0,TEXT("undo retains installed drum"));CloseGunsmith();});
    Later(16,[this,P,Check](){auto State=P->Snapshot();auto Other=P->CreateItem(TEXT("ue_m4a1"));Other.Place=0;Other.Cell=0;Other.Magazine=11;State.Items.Add(Other);Check(P->CommitState(State)&&OpenGunsmith(Other.InstanceId),TEXT("inventory instance opens with explicit unequipped placeholder"));});
    Later(18,[Dir](){FScreenshotRequest::RequestScreenshot(Dir/TEXT("workbench-unequipped.png"),true,false);});
    Later(19,[this,Check,Counts,PreviewWorlds,BaselineWorlds](){auto* Panel=GunsmithPanel.Get();CloseGunsmith();Check(Panel&&!Panel->HasWorkbenchCapture()&&PreviewWorlds()==BaselineWorlds,TEXT("repeated close leaves no captures or studio worlds"));if(FParse::Param(FCommandLine::Get(),TEXT("GunsmithLayoutStress"))){RunGunsmithLayoutStress(Counts);return;}UE_LOG(LogTemp,Display,TEXT("WORKBENCH: COMPLETE checks=%d failures=%d"),Counts->X,Counts->Y);ConsoleCommand(TEXT("quit"));});
}
