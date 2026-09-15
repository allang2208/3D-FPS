#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/GunsmithSystem.h"
#include "M4GunsmithWidget.h"
#include "ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/SBoxPanel.h"
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
    Later(.5f,[this](){if(GunsmithPanel&&GunsmithPanel->BodyScroll)GunsmithPanel->BodyScroll->ScrollDescendantIntoView(GunsmithPanel->OptionScroll,false);});
    Later(1,[this,Check](){auto* Panel=GunsmithPanel.Get();if(!Panel)return;
        Check(Panel->OptionCards.Num()==14,TEXT("fourteen options rendered without collapsing cards"));
        const auto First=Panel->OptionCards.FindChecked(TEXT("false"));Check(FMath::IsNearlyEqual(First->GetCachedGeometry().GetLocalSize().X,264.f,1.f),TEXT("card width remains fixed with many options"));
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
    auto FitCheck=[this,Check](const TCHAR* Label)
    {
        auto* Panel=GunsmithPanel.Get();if(!Panel)return;
        auto* C=Cast<AFPSGAMECharacter>(GetPawn());C->UpdateGunsmithCapture(Panel->Capture,false);Panel->SyncStudioPreview();Panel->Capture->CaptureScene();
        const auto View=Panel->Capture->GetComponentTransform();const float HalfW=Panel->Capture->OrthoWidth*.5f;
        const float HalfH=HalfW*Panel->PreviewTarget->SizeY/Panel->PreviewTarget->SizeX;
        bool Inside=true;int32 StaticCount=0;
        for(const auto& Pair:Panel->StudioCopies)if(auto* Mesh=Cast<UStaticMeshComponent>(Pair.Value);Mesh&&Mesh->IsVisible()&&Mesh->GetStaticMesh())
        {
            ++StaticCount;const FBox Box=Mesh->GetStaticMesh()->GetBoundingBox();
            for(int32 I=0;I<8;++I)
            {
                const FVector Point((I&1)?Box.Max.X:Box.Min.X,(I&2)?Box.Max.Y:Box.Min.Y,(I&4)?Box.Max.Z:Box.Min.Z);
                const FVector Projected=View.InverseTransformPosition(Mesh->GetComponentTransform().TransformPosition(Point));
                const auto& Projection=Panel->Capture->CustomProjectionMatrix;
                const double Depth=Projected.X*Projection.M[2][2]+Projection.M[3][2];
                Inside&=FMath::Abs(Projected.Y)<HalfW*.86f&&FMath::Abs(Projected.Z)<HalfH*.62f&&Depth>0.0&&Depth<1.0;
            }
        }
        Check(Inside&&StaticCount>=3,Label);
    };
    auto Extensions=MakeShared<TArray<UStaticMeshComponent*>>();
    Later(6,[this,FitCheck](){if(!GunsmithPanel)return;GunsmithPanel->ChooseOption(TEXT("muzzle"),TEXT("true"));GunsmithPanel->SetSidePreview(true);FitCheck(TEXT("suppressor optic and drum all fit with safe margins"));});
    Later(7,[](){FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("GunsmithWorkbenchAudit/workbench-long-muzzle.png"),true,false);});
    Later(8,[this,Extensions,FitCheck](){
        auto* Panel=GunsmithPanel.Get();if(!Panel)return;USkeletalMeshComponent* Rifle=nullptr;
        for(const auto& Pair:Panel->StudioCopies)if(auto* S=Cast<USkeletalMeshComponent>(Pair.Key.Get());S&&S->DoesSocketExist(TEXT("WPN_root"))){Rifle=S;break;}
        if(!Rifle)return;const FVector Axis=(Rifle->GetSocketLocation(TEXT("WPN_FrontSight"))-Rifle->GetSocketLocation(TEXT("WPN_RearSight"))).GetSafeNormal();
        const FVector Center=Rifle->GetSocketLocation(TEXT("WPN_SOCKET_Magazine"));
        for(int32 Side:{-1,1})
        {
            auto* Extension=NewObject<UStaticMeshComponent>(GetPawn(),NAME_None,RF_Transient);Extension->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
            Extension->SetupAttachment(Extensions->IsEmpty()?static_cast<USceneComponent*>(Rifle):(*Extensions)[0]);Extension->SetCollisionEnabled(ECollisionEnabled::NoCollision);Extension->RegisterComponent();
            Extension->SetWorldLocation(Center+Axis*Side*90.f);Extension->SetWorldRotation(FRotationMatrix::MakeFromX(Axis).Rotator());Extension->SetWorldScale3D(FVector(.8,.06,.06));Extensions->Add(Extension);
        }
        FitCheck(TEXT("future front and rear extensions including nested attachments fit"));
    });
    Later(9,[](){FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("GunsmithWorkbenchAudit/workbench-extended.png"),true,false);});
    Later(10,[this,FitCheck](){if(GunsmithPanel){GunsmithPanel->RotatePreview(FVector2D(210,-100));FitCheck(TEXT("dragged extended assembly remains inside frame"));}});
    Later(11,[](){FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("GunsmithWorkbenchAudit/workbench-extended-rotated.png"),true,false);});
    Later(12,[this,Extensions,FitCheck](){for(int32 I=Extensions->Num()-1;I>=0;--I)(*Extensions)[I]->DestroyComponent();if(GunsmithPanel){GunsmithPanel->SetSidePreview(true);FitCheck(TEXT("removing extensions restores close centered framing"));}});
    if(!FParse::Param(FCommandLine::Get(),TEXT("ColdGlassResize")))
    {
        Later(14,[this,Check,Counts](){CloseGunsmith();UE_LOG(LogTemp,Display,TEXT("WORKBENCH: COMPLETE checks=%d failures=%d"),Counts->X,Counts->Y);ConsoleCommand(TEXT("quit"));});
        return;
    }
    const FString ShotDir=FPaths::ProjectSavedDir()/TEXT("GunsmithWorkbenchAudit");
    auto SafeFrame=[this,Check](){
        if(!GunsmithPanel){Check(false,TEXT("responsive workbench remains open"));return;}
        const auto Root=GunsmithPanel->TakeWidget()->GetCachedGeometry();
        const auto Rail=GunsmithPanel->CategoryScroll->GetCachedGeometry();
        const auto Footer=GunsmithPanel->FooterContent->GetCachedGeometry();
        Check(Rail.GetAbsolutePosition().X>=Root.GetAbsolutePosition().X&&Rail.GetAbsolutePosition().X+Rail.GetAbsoluteSize().X<=Root.GetAbsolutePosition().X+Root.GetAbsoluteSize().X+2,TEXT("responsive rail horizontal bounds fit"));
        Check(Footer.GetAbsolutePosition().Y+Footer.GetAbsoluteSize().Y<=Root.GetAbsolutePosition().Y+Root.GetAbsoluteSize().Y+2,TEXT("responsive footer remains reachable"));
        Check(Footer.GetLocalSize().Y<=48.f,TEXT("responsive action buttons keep single-line labels"));
        Check(GunsmithPanel->Overview.Num()==20&&GunsmithPanel->OptionCards.Num()==2,TEXT("reflow preserves overview and restored option data"));
    };
    Later(14,[this](){ConsoleCommand(TEXT("r.SetRes 1280x720w"));});
    Later(16,[this,Check,SafeFrame,ShotDir](){SafeFrame();Check(GunsmithPanel&&GunsmithPanel->LayoutMode==1,TEXT("1280 viewport uses compact three columns"));FScreenshotRequest::RequestScreenshot(ShotDir/TEXT("coldglass-1280.png"),true,false);});
    Later(17,[this](){ConsoleCommand(TEXT("r.SetRes 960x540w"));});
    Later(19,[this,Check,SafeFrame,ShotDir](){SafeFrame();Check(GunsmithPanel&&GunsmithPanel->LayoutMode==2&&GunsmithPanel->BodyScroll,TEXT("960 viewport reflows with main scrolling"));FScreenshotRequest::RequestScreenshot(ShotDir/TEXT("coldglass-960-top.png"),true,false);});
    Later(20,[this](){if(GunsmithPanel){if(GunsmithPanel->BodyScroll)GunsmithPanel->BodyScroll->ScrollToEnd();GunsmithPanel->OverviewScroll->ScrollToEnd();}});
    Later(21,[this,Check,ShotDir](){if(!GunsmithPanel)return;const auto Scroll=GunsmithPanel->OverviewScroll->GetCachedGeometry();
        const auto Last=GunsmithPanel->OverviewList->GetChildren()->GetChildAt(19)->GetCachedGeometry();
        const FVector2D At=Scroll.AbsoluteToLocal(Last.GetAbsolutePosition());
        Check(At.Y+Last.GetLocalSize().Y<=Scroll.GetLocalSize().Y+2,TEXT("narrow window reaches final mechanical-sight row"));
        const auto Body=GunsmithPanel->BodyHost->GetCachedGeometry();const auto Inspector=GunsmithPanel->InspectorContent->GetCachedGeometry();
        const auto InspectorAt=Body.AbsoluteToLocal(Inspector.GetAbsolutePosition());
        Check(InspectorAt.Y>=-2&&InspectorAt.Y+Inspector.GetLocalSize().Y<=Body.GetLocalSize().Y+2,TEXT("narrow summary keeps its heading and comparison controls visible"));
        FScreenshotRequest::RequestScreenshot(ShotDir/TEXT("coldglass-960-summary.png"),true,false);
    });
    Later(22,[this](){ConsoleCommand(TEXT("r.SetRes 1920x1080w"));});
    Later(24,[this,Check,SafeFrame,ShotDir](){SafeFrame();Check(GunsmithPanel&&GunsmithPanel->LayoutMode==0&&!GunsmithPanel->BodyScroll,TEXT("resize back restores wide layout without reopening"));FScreenshotRequest::RequestScreenshot(ShotDir/TEXT("coldglass-1920-restored.png"),true,false);});
    const float OriginalScale=FSlateApplication::Get().GetApplicationScale();
    Later(25,[OriginalScale](){FSlateApplication::Get().SetApplicationScale(OriginalScale*1.25f);});
    Later(27,[SafeFrame,ShotDir](){SafeFrame();FScreenshotRequest::RequestScreenshot(ShotDir/TEXT("coldglass-ui-scale-125.png"),true,false);});
    Later(28,[OriginalScale](){FSlateApplication::Get().SetApplicationScale(OriginalScale*1.5f);});
    Later(30,[SafeFrame,ShotDir](){SafeFrame();FScreenshotRequest::RequestScreenshot(ShotDir/TEXT("coldglass-ui-scale-150.png"),true,false);});
    Later(31,[OriginalScale](){FSlateApplication::Get().SetApplicationScale(OriginalScale);});
    Later(32,[this,Check,Counts](){
        FSlateApplication::Get().ProcessKeyDownEvent(FKeyEvent(EKeys::Escape,FModifierKeysState(),0,false,0,0));
        Check(!GunsmithPanel&&!bShowMouseCursor&&!IsMoveInputIgnored()&&!IsLookInputIgnored(),TEXT("Escape closes workbench and restores gameplay input"));
        CloseGunsmith();UE_LOG(LogTemp,Display,TEXT("WORKBENCH: COMPLETE checks=%d failures=%d"),Counts->X,Counts->Y);ConsoleCommand(TEXT("quit"));
    });
}
