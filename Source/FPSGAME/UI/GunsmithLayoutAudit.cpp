#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/GunsmithSystem.h"
#include "M4GunsmithWidget.h"
#include "ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Components/StaticMeshComponent.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SWindow.h"
#include "Framework/Application/SlateApplication.h"
#include "InputCoreTypes.h"
#include "TimerManager.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"

void AFPSGAMEPlayerController::RunGunsmithLayoutStress(TSharedPtr<FIntPoint> Counts)
{
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!P->IsAudit()||!P->ProfileSlot().Contains(TEXT("WorkbenchAudit")))return;
    auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    auto Check=[Counts](bool Pass,const TCHAR* Name){++Counts->X;if(!Pass)++Counts->Y;UE_LOG(LogTemp,Display,TEXT("WORKBENCH: %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Name);};
    Check(OpenGunsmith(),TEXT("open layout stress in isolated profile"));if(!GunsmithPanel){ConsoleCommand(TEXT("quit"));return;}
    auto* W=const_cast<FGunsmithWeapon*>(G->Weapon(G->Definition()));
    auto Original=MakeShared<TArray<FGunsmithOption>>(W->Options.FindChecked(TEXT("magazine")));
    // These options exist only for this audit process and are never saved or written into the catalog.
    for(int32 N=0;N<12;++N){FGunsmithOption O;O.Id=FString::Printf(TEXT("audit_scroll_%d"),N);O.Name=FString::Printf(TEXT("滚动验证配件 %02d"),N+1);O.Description=TEXT("用于验证未来新增配件时，卡片保持固定尺寸、长说明不会撑开预览，鼠标滚轮可浏览到列表末尾。此条目仅存在于临时验收数据中。");O.Magazine=N+1;W->Options.FindChecked(TEXT("magazine")).Add(O);}
    GunsmithPanel->SelectCategory(TEXT("magazine"));GunsmithPanel->RefreshPresentation();
    auto Later=[this](float T,TFunction<void()> F){FTimerHandle H;GetWorldTimerManager().SetTimer(H,[F](){F();},T,false);};
    auto ScrollOffset=MakeShared<float>(0.f);
    Later(1,[this,Check](){auto* Panel=GunsmithPanel.Get();if(!Panel)return;
        Check(Panel->OptionCards.Num()==14,TEXT("fourteen options rendered without collapsing cards"));
        const auto First=Panel->OptionCards.FindChecked(TEXT("false"));Check(FMath::IsNearlyEqual(First->GetCachedGeometry().GetLocalSize().X,310.f,1.f),TEXT("card width remains fixed with many options"));
        // Replacing an attachment mesh on the same source component must refresh its studio copy.
        bool MeshUpdated=false;
        for(const auto& Pair:Panel->StudioCopies)if(auto* Source=Cast<UStaticMeshComponent>(Pair.Key.Get());Source&&Source->GetName().Contains(TEXT("LargeDrum")))
        {
            UStaticMesh* Saved=Source->GetStaticMesh();auto* Cube=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));if(!Saved||!Cube)break;
            auto* C=Cast<AFPSGAMECharacter>(GetPawn());Source->SetStaticMesh(Cube);C->UpdateGunsmithCapture(Panel->Capture,false);Panel->SyncStudioPreview();
            MeshUpdated=Cast<UStaticMeshComponent>(Pair.Value)->GetStaticMesh()==Cube;
            Source->SetStaticMesh(Saved);C->UpdateGunsmithCapture(Panel->Capture,false);Panel->SyncStudioPreview();break;
        }
        Check(MeshUpdated,TEXT("studio copy follows mesh replacement on existing attachment component"));
        auto& App=FSlateApplication::Get();const auto Geometry=Panel->OptionScroll->GetCachedGeometry();const FVector2D At=Geometry.LocalToAbsolute(Geometry.GetLocalSize()*.5f);const TSet<FKey> None;
        App.ProcessMouseMoveEvent(FPointerEvent(0,At,At,None,FKey(),0,FModifierKeysState()),false);
        App.ProcessMouseWheelOrGestureEvent(FPointerEvent(0,At,At,None,FKey(),-8.f,FModifierKeysState()),nullptr);
    });
    Later(2,[this,Check](){auto* Panel=GunsmithPanel.Get();if(!Panel)return;
        Check(Panel->OptionScroll->GetScrollOffset()>100,TEXT("ordinary mouse wheel scrolls attachment strip horizontally"));
        Check(Panel->GetPreviewOrbit().IsNearlyZero(),TEXT("scrolling attachments does not rotate rifle"));
        Panel->OptionScroll->ScrollToEnd();
    });
    Later(3,[this,ScrollOffset,Check](){auto* Panel=GunsmithPanel.Get();if(!Panel)return;
        *ScrollOffset=Panel->OptionScroll->GetScrollOffset();auto Card=Panel->OptionCards.FindChecked(TEXT("audit_scroll_11"));
        auto& App=FSlateApplication::Get();auto Window=App.FindWidgetWindow(Card.ToSharedRef());if(!Window)return;
        const auto Geometry=Card->GetCachedGeometry();const FVector2D At=Geometry.LocalToAbsolute(Geometry.GetLocalSize()*.5f);const TSet<FKey> Held{EKeys::LeftMouseButton},None;
        App.ProcessMouseMoveEvent(FPointerEvent(0,At,At,None,FKey(),0,FModifierKeysState()),false);
        App.ProcessMouseButtonDownEvent(Window->GetNativeWindow(),FPointerEvent(0,At,At,Held,EKeys::LeftMouseButton,0,FModifierKeysState()));
        App.ProcessMouseButtonUpEvent(FPointerEvent(0,At,At,None,EKeys::LeftMouseButton,0,FModifierKeysState()));
        Check(Panel->OptionCards.FindChecked(TEXT("audit_scroll_11"))==Card,TEXT("selection preserves clicked widget and focus target"));
    });
    Later(4,[this,G,Check,ScrollOffset](){auto* Panel=GunsmithPanel.Get();if(!Panel)return;
        Check(G->Draft().FindRef(TEXT("magazine"))==TEXT("audit_scroll_11"),TEXT("new option ID selected correctly instead of removing attachment"));
        Check(FMath::IsNearlyEqual(Panel->OptionScroll->GetScrollOffset(),*ScrollOffset,1.f),TEXT("selection preserves list scroll position"));
        Check(G->Message()==TEXT("预览已更新，应用后保存"),TEXT("new selection clears stale saved status"));
        Panel->SetCompareFactory(true);Check(FMath::IsNearlyEqual(Panel->OptionScroll->GetScrollOffset(),*ScrollOffset,1.f),TEXT("changing stat comparison preserves attachment scroll"));
        FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("GunsmithWorkbenchAudit/workbench-scroll.png"),true,false);
    });
    Later(5,[this,G,W,Original,Check](){if(!GunsmithPanel)return;
        GunsmithPanel->SelectCategory(TEXT("optic"));Check(GunsmithPanel->OptionScroll->GetScrollOffset()==0,TEXT("category switch resets scroll to first item"));
        G->Undo();W->Options.FindChecked(TEXT("magazine"))=*Original;GunsmithPanel->SelectCategory(TEXT("magazine"));
        GunsmithPanel->ChooseDrum(true);Check(G->Pending()==0&&GunsmithPanel->OptionCards.Num()==2,TEXT("temporary options removed and installed configuration restored"));
    });
    Later(6,[this,Check,Counts](){CloseGunsmith();UE_LOG(LogTemp,Display,TEXT("WORKBENCH: COMPLETE checks=%d failures=%d"),Counts->X,Counts->Y);ConsoleCommand(TEXT("quit"));});
}
