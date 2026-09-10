#include "ColdSteelHUDWidget.h"
#include "ColdSteelItemTooltip.h"
#include "ColdSteelWarehouseWidget.h"
#include "ColdSteelWarehouseChest.h"
#include "ColdSteelStatusModel.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/Button.h"
#include "Components/Border.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/TextBlock.h"
#include "ColdSteelUIStyle.h"
#include "GameFramework/PlayerController.h"
#include "Engine/GameInstance.h"
#include "Framework/Application/SlateApplication.h"
void UColdSteelHUDWidget::BuildWarehouse(UCanvasPanel* Root)
{
    WarehouseWidget=CreateWidget<UColdSteelWarehouseWidget>(GetOwningPlayer());WarehouseWidget->Configure(this);
    WarehouseSlot=Root->AddChildToCanvas(WarehouseWidget);WarehouseSlot->SetAnchors(FAnchors(.55f,0,.55f,1));WarehouseSlot->SetAlignment(FVector2D(1,0));WarehouseSlot->SetOffsets(FMargin(0,0,ReferenceUnits(380),0));WarehouseSlot->SetZOrder(40);WarehouseWidget->SetVisibility(ESlateVisibility::Collapsed);
}
void UColdSteelHUDWidget::OpenWarehouse(AColdSteelWarehouseChest* Chest)
{
    if(!Chest||!Chest->CanInteract(GetOwningPlayerPawn()))return;
    if(bWarehouseOpen)return;
    WarehouseChest=Chest;SetInventoryTab(false);SetInventoryOpen(true);
    auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();M->GrantStartingArmory();M->bWarehouseOpen=true;
    bWarehouseOpen=true;WarehouseStart=WarehouseMotion;WarehouseElapsed=0;
    WarehouseWidget->ResetPage();WarehouseWidget->SetVisibility(ESlateVisibility::Visible);WarehouseWidget->SetKeyboardFocus();Chest->SetOpen(true);
}
void UColdSteelHUDWidget::CloseWarehouse()
{
    HideItemTooltip(true);
    if(!bWarehouseOpen)return;
    HideWarehouseDetails();
    FSlateApplication::Get().CancelDragDrop();bWarehouseOpen=false;
    GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->bWarehouseOpen=false;
    WarehouseStart=WarehouseMotion;WarehouseElapsed=0;WarehouseWidget->SetVisibility(ESlateVisibility::HitTestInvisible);
    if(bInventoryOpen&&CloseButton)CloseButton->SetKeyboardFocus();
}
void UColdSteelHUDWidget::ShowWarehouseDetails(UWidget* Details)
{
    if(!bWarehouseOpen||!Details)return;HideWarehouseDetails();
    auto* Root=Cast<UCanvasPanel>(WidgetTree->RootWidget);if(!Root)return;
    WarehouseDetails=MakeSurface(ColdSteelUI::Tooltip,12,ColdSteelUI::Border);WarehouseDetails->SetPadding(FMargin(ReferenceUnits(8)));
    auto* Stack=WidgetTree->ConstructWidget<UVerticalBox>();WarehouseDetails->SetContent(Stack);
    auto* Close=WidgetTree->ConstructWidget<UButton>();Close->SetContent(MakeReferenceText(TEXT("关闭详情 ×"),14,ColdSteelUI::TextPrimary));Close->OnClicked.AddDynamic(this,&ThisClass::HideWarehouseDetails);Stack->AddChildToVerticalBox(Close)->SetHorizontalAlignment(HAlign_Right);
    auto* Vertical=WidgetTree->ConstructWidget<UScrollBox>();Stack->AddChildToVerticalBox(Vertical)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    auto* Horizontal=WidgetTree->ConstructWidget<UScrollBox>();Horizontal->SetOrientation(Orient_Horizontal);Horizontal->SetAlwaysShowScrollbar(true);Vertical->AddChild(Horizontal);
    auto* Min=WidgetTree->ConstructWidget<USizeBox>();Min->SetMinDesiredWidth(ReferenceUnits(460));Min->SetContent(Details);Horizontal->AddChild(Min);
    auto* DetailSlot=Root->AddChildToCanvas(WarehouseDetails);DetailSlot->SetZOrder(150);DetailSlot->SetAnchors(FAnchors(.5f,.5f));DetailSlot->SetAlignment(FVector2D(.5f,.5f));
    int32 W,H;GetOwningPlayer()->GetViewportSize(W,H);DetailSlot->SetSize(FVector2D(ReferenceUnits(FMath::Min(760,W-32)),ReferenceUnits(FMath::Min(430,H-32))));
}
void UColdSteelHUDWidget::HideWarehouseDetails(){if(WarehouseDetails){WarehouseDetails->RemoveFromParent();WarehouseDetails=nullptr;}}
void UColdSteelHUDWidget::TickWarehouse(const FGeometry& G,float Delta)
{
    if(!WarehouseWidget)return;
    if(bWarehouseOpen&&(!WarehouseChest.IsValid()||!WarehouseChest->IsWithinReach(GetOwningPlayerPawn())))CloseWarehouse();
    WarehouseElapsed=FMath::Min(.3f,WarehouseElapsed+Delta);
    const float T=WarehouseElapsed/.3f;
    auto Bezier=[](float X,float A,float B){float Low=0,High=1,U=0;for(int N=0;N<16;++N){U=(Low+High)*.5f;float V=3*(1-U)*(1-U)*U*A+3*(1-U)*U*U*B+U*U*U;if(V<X)Low=U;else High=U;}return 3*(1-U)*U*U+U*U*U;};
    WarehouseMotion=FMath::Lerp(WarehouseStart,bWarehouseOpen?1.f:0.f,Bezier(T,.4f,.2f));
    int32 Width,Height;GetOwningPlayer()->GetViewportSize(Width,Height);
    const float Pixels=Width<=1100?FMath::Min(380.f,Width*.44f):380.f;
    WarehouseSlot->SetOffsets(FMargin(0,0,ReferenceUnits(Pixels),0));
    WarehouseWidget->SetRenderTranslation(FVector2D((1-WarehouseMotion)*ReferenceUnits(Pixels),0));WarehouseWidget->SetRenderOpacity(WarehouseMotion);
    if(!bWarehouseOpen&&T>=1){WarehouseWidget->SetVisibility(ESlateVisibility::Collapsed);if(WarehouseChest.IsValid())WarehouseChest->SetOpen(false);WarehouseChest.Reset();}
}
FReply UColdSteelHUDWidget::NativeOnPreviewMouseButtonDown(const FGeometry& G,const FPointerEvent& E)
{
    if(bInventoryOpen&&E.GetEffectingButton()==EKeys::LeftMouseButton&&!UWidgetBlueprintLibrary::IsDragDropping()){
        const FVector2D Position=E.GetScreenSpacePosition();
        const bool InBag=InventoryPanel&&InventoryPanel->GetCachedGeometry().IsUnderLocation(Position);
        const bool InWarehouse=bWarehouseOpen&&WarehouseWidget&&WarehouseWidget->GetCachedGeometry().IsUnderLocation(Position);
        const bool InDetails=WarehouseDetails&&WarehouseDetails->GetCachedGeometry().IsUnderLocation(Position);
        const auto Inside=[&](UWidget* W){return W&&W->IsVisible()&&W->GetCachedGeometry().IsUnderLocation(Position);};
        const bool InTooltip=Inside(ItemTooltip)||Inside(StatusTooltip)||Inside(EquipmentTooltip);
        if(!InBag&&!InWarehouse&&!InDetails&&!InTooltip){SetInventoryOpen(false);return FReply::Handled();}
    }
    return Super::NativeOnPreviewMouseButtonDown(G,E);
}

FReply UColdSteelHUDWidget::NativeOnMouseButtonDown(const FGeometry& G,const FPointerEvent& E){return Super::NativeOnMouseButtonDown(G,E);}
