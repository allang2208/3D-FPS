#include "ColdSteelHUDWidget.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelInventoryPopup.h"
#include "ColdSteelStatusModel.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/BackgroundBlur.h"
#include "Components/Border.h"
#include "Components/CanvasPanel.h"
#include "Components/ScrollBox.h"
#include "Components/TextBlock.h"
#include "Components/EditableTextBox.h"
#include "Engine/GameInstance.h"
#include "Framework/Application/SlateApplication.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Widgets/Layout/SBackgroundBlur.h"
#include "TimerManager.h"
#include "UnrealClient.h"

void UColdSteelHUDWidget::RunInventoryGlassAudit()
{
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Model||!Model->IsAudit())return;
    struct FRun{int32 Phase=0,Checks=0,Failures=0;FTimerHandle Timer;FColdSteelProfile Before;FString Gun,Potion;FVector2D View;float AppScale;};
    auto Run=MakeShared<FRun>();Run->Before=Model->Snapshot();Run->View=UWidgetLayoutLibrary::GetViewportSize(this);Run->AppScale=FSlateApplication::Get().GetApplicationScale();
    for(const auto& Item:Model->Items())if(Item.Place==0){if(Item.Count>1)Run->Potion=Item.InstanceId;else Run->Gun=Item.InstanceId;}
    auto Check=[Run](bool Good,const TCHAR* Name){++Run->Checks;if(!Good)++Run->Failures;UE_LOG(LogTemp,Display,TEXT("InventoryGlassAudit: %s %s"),Good?TEXT("PASS"):TEXT("FAIL"),Name);};
    GetWorld()->GetTimerManager().SetTimer(Run->Timer,FTimerDelegate::CreateWeakLambda(this,[this,Model,Run,Check](){
        auto* Scroll=Cast<UScrollBox>(EquipmentPage);auto* Board=Scroll?Cast<UColdSteelInventoryWidget>(Scroll->GetChildAt(0)):nullptr;if(!Board)return;
        const auto Root=GetCachedGeometry(),Panel=InventoryPanel->GetCachedGeometry();const auto Geometry=Board->GetCachedGeometry();const auto Layout=Board->Layout(Geometry);
        auto Safe=[&](){
            const auto At=Root.AbsoluteToLocal(Panel.GetAbsolutePosition());
            Check(At.X>=0&&At.Y>=0&&At.X+Panel.GetLocalSize().X<=Root.GetLocalSize().X+1&&At.Y+Panel.GetLocalSize().Y<=Root.GetLocalSize().Y+1,TEXT("drawer corners stay inside viewport"));
            int32 Place,Cell;bool Hits=true;for(int32 N=0;N<15;++N){const auto Local=FVector2D(12+(N%3)*(Layout.GearWidth+6)+Layout.GearWidth*.5,Layout.GearY+(N/3)*Layout.GearPitch+Layout.GearHeight*.5)/Board->Scale;Hits&=Board->Hit(Geometry,Geometry.LocalToAbsolute(Local),Place,Cell)&&Place==1&&Cell==N;}
            for(int32 N=0;N<72;++N){const auto Local=FVector2D(12+(N%18+.5f)*Layout.Cell,Layout.BagY+(N/18+.5f)*Layout.Cell)/Board->Scale;Hits&=Board->Hit(Geometry,Geometry.LocalToAbsolute(Local),Place,Cell)&&Place==0&&Cell==N;}
            Check(Hits,TEXT("all equipment and bag cells retain exact hit mapping after reflow"));
            Check(InventoryWidth>=FMath::Min(720.f,float(InventoryLayoutSize.X)-24.f)-1,TEXT("narrow drawer keeps useful item width"));
        };
        auto Shot=[&](const TCHAR* Name){HideItemTooltip(true);const FString Dir=FPaths::ProjectSavedDir()/TEXT("InventoryColdGlass20260912/final");IFileManager::Get().MakeDirectory(*Dir,true);FScreenshotRequest::RequestScreenshot(Dir/(FString(Name)+TEXT(".png")),true,false);};
        auto PopupInside=[&](){
            if(!Board->ItemMenu){Check(false,TEXT("popup exists"));return;}
            const auto* PopupRoot=Cast<UCanvasPanel>(Board->ItemMenu->WidgetTree->RootWidget);const auto Popup=PopupRoot->GetChildAt(0)->GetCachedGeometry();const auto At=Root.AbsoluteToLocal(Popup.GetAbsolutePosition());
            Check(At.X>=0&&At.Y>=0&&At.X+Popup.GetLocalSize().X<=Root.GetLocalSize().X+1&&At.Y+Popup.GetLocalSize().Y<=Root.GetLocalSize().Y+1,TEXT("bottom-right popup clamps to viewport"));
        };
        switch(Run->Phase++)
        {
        case 0:{Board->CancelInteraction();Scroll->ScrollToStart();Safe();const auto Blur=StaticCastSharedPtr<SBackgroundBlur>(InventoryBlur->GetCachedWidget());const auto* Allow=IConsoleManager::Get().FindConsoleVariable(TEXT("Slate.AllowBackgroundBlurWidgets"));
            UE_LOG(LogTemp,Display,TEXT("InventoryGlassRender: allow=%d fallback=%d strength=%.1f opacity=%.2f"),Allow?Allow->GetInt():-1,Blur->IsUsingLowQualityFallbackBrush(),InventoryBlur->GetBlurStrength(),InventoryBlur->GetRenderOpacity());
            Check(Allow&&Allow->GetInt()!=0&&!Blur->IsUsingLowQualityFallbackBrush()&&InventoryBlur->GetBlurStrength()>=5&&InventoryBlur->GetCachedGeometry().GetLocalSize().X<Root.GetLocalSize().X,TEXT("real blur stays within the glass drawer"));
            Check(InventoryTitleText->GetFont().CompositeFont->DefaultTypeface.Fonts[0].Font.GetFontFilename().EndsWith(TEXT("NotoSansSC-Medium.otf")),TEXT("drawer title uses project Noto medium font"));break;
        }
        case 1:Shot(TEXT("overview-1920"));break;
        case 2:Board->SelectItem(Run->Gun);Board->OpenItemMenu(Root.LocalToAbsolute(Root.GetLocalSize()-FVector2D(4,4)),false);break;
        case 3:PopupInside();Shot(TEXT("item-menu"));break;
        case 4:Board->ItemMenu->Close();Board->SelectItem(Run->Potion);Board->OpenItemMenu(Root.LocalToAbsolute(Root.GetLocalSize()-FVector2D(4,4)),true);break;
        case 5:PopupInside();Check(Board->ItemMenu->Quantity&&Board->ItemMenu->Quantity->GetWidgetStyle().TextStyle.Font.CompositeFont->DefaultTypeface.Fonts[0].Font.GetFontFilename().EndsWith(TEXT("JetBrainsMono-Regular.ttf")),TEXT("split quantity uses project numeric font"));Shot(TEXT("split-menu"));break;
        case 6:Board->CancelInteraction();GetOwningPlayer()->ConsoleCommand(TEXT("r.SetRes 1280x720w"));break;
        case 7:Safe();Scroll->ScrollToStart();Shot(TEXT("overview-1280"));break;
        case 8:GetOwningPlayer()->ConsoleCommand(TEXT("r.SetRes 960x540w"));break;
        case 9:Safe();Scroll->ScrollToStart();Shot(TEXT("overview-960"));break;
        case 10:Scroll->ScrollToEnd();break;
        case 11:{const auto View=Scroll->GetCachedGeometry();const auto End=View.AbsoluteToLocal(Geometry.LocalToAbsolute(FVector2D(12,Layout.HotY+85)/Board->Scale));Check(End.Y<=View.GetLocalSize().Y+2&&End.Y>=0,TEXT("small viewport reaches quick items and final instructions"));Shot(TEXT("bottom-960"));break;}
        case 12:GetOwningPlayer()->ConsoleCommand(TEXT("r.SetRes 1920x1080w"));break;
        case 13:FSlateApplication::Get().SetApplicationScale(Run->AppScale*1.5f);break;
        case 14:Safe();Scroll->ScrollToStart();Shot(TEXT("ui-scale-150"));break;
        case 15:FSlateApplication::Get().SetApplicationScale(Run->AppScale);GetOwningPlayer()->ConsoleCommand(FString::Printf(TEXT("r.SetRes %dx%dw"),int32(Run->View.X),int32(Run->View.Y)));break;
        case 16:InventoryBlur->SetBlurStrength(0);break;
        case 17:Shot(TEXT("blur-control-disabled"));break;
        case 18:InventoryBlur->SetBlurStrength(9);break;
        case 19:Shot(TEXT("blur-control-enabled"));break;
        default:{bool Same=Model->Items().Num()==Run->Before.Items.Num();for(const auto& Old:Run->Before.Items){const auto* Item=Model->FindItem(Old.InstanceId);Same&=Item&&Item->Data==Old.Data&&Item->Place==Old.Place&&Item->Cell==Old.Cell&&Item->Count==Old.Count&&Item->Magazine==Old.Magazine;}
            Check(Same,TEXT("theme resize and popup browsing preserve instance data"));SetInventoryOpen(false);Check(!GetOwningPlayer()->bShowMouseCursor&&!GetOwningPlayer()->IsMoveInputIgnored()&&!GetOwningPlayer()->IsLookInputIgnored(),TEXT("closing themed inventory restores gameplay input"));
            GetWorld()->GetTimerManager().ClearTimer(Run->Timer);UE_LOG(LogTemp,Display,TEXT("InventoryGlassAudit: COMPLETE checks=%d failures=%d"),Run->Checks,Run->Failures);GetOwningPlayer()->ConsoleCommand(TEXT("quit"));break;}
        }
    }),1.f,true);
}
