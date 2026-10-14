#include "ColdSteelHUDWidget.h"
#include "ColdSteelShopWidget.h"
#include "ColdSteelShopModel.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Engine/GameInstance.h"

void UColdSteelHUDWidget::OpenShop()
{
    if(bShopOpen)return;
    UWidgetBlueprintLibrary::CancelDragDrop();
    CloseWarehouse();HideForgingInstantly();HideSmeltingInstantly();HideWorkbenchInstantly();
    SetInventoryPage(1);SetInventoryOpen(true);HideItemTooltip(true);
    GetGameInstance()->GetSubsystem<UColdSteelShopModel>()->BeginSession();
    if(!ShopWidget)
    {
        ShopWidget=CreateWidget<UColdSteelShopWidget>(GetOwningPlayer());ShopWidget->Configure(this);
        auto* Root=CastChecked<UCanvasPanel>(WidgetTree->RootWidget);
        ShopSlot=Root->AddChildToCanvas(ShopWidget);
        ShopSlot->SetAnchors(FAnchors(1,0,1,1));ShopSlot->SetAlignment(FVector2D(1,0));ShopSlot->SetAutoSize(false);ShopSlot->SetZOrder(40);
        // Give the first frame the same full-height allocation as the backpack;
        // UpdateInventoryLayout refits both drawers to the viewport on the next tick.
        const float Scale=ColdSteelUI::PixelScale(this);
        ShopSlot->SetOffsets(FMargin(-(InventoryWidth+ColdSteelUI::NavigationDrawerInset)/Scale,12/Scale,InventoryWidth/Scale,12/Scale));
    }
    bShopOpen=true;InventoryLayoutSize=FVector2D::ZeroVector;
    ShopWidget->ResetSession();ShopWidget->SetVisibility(ESlateVisibility::HitTestInvisible);ShopWidget->SetRenderOpacity(0);
}
void UColdSteelHUDWidget::CloseShop()
{
    if(!bShopOpen)return;
    UWidgetBlueprintLibrary::CancelDragDrop();bShopOpen=false;
    ShopWidget->CancelConfirmation();ShopWidget->SetVisibility(ESlateVisibility::HitTestInvisible);
    GetGameInstance()->GetSubsystem<UColdSteelShopModel>()->EndSession();
}
void UColdSteelHUDWidget::ToggleShop(){if(bShopOpen)SetInventoryOpen(false);else OpenShop();}
bool UColdSteelHUDWidget::AddShopSaleItem(const FString& Id){return bShopOpen&&ShopWidget&&ShopWidget->AddToSale(Id);}
bool UColdSteelHUDWidget::HandleShopConfirmationKey(const FKey& Key)
{
    if(!bShopOpen||!ShopWidget||!ShopWidget->IsConfirming())return false;
    if(Key==EKeys::Escape||Key==EKeys::O||Key==EKeys::Tab)ShopWidget->CancelConfirmation();
    return true;
}
void UColdSteelHUDWidget::TickShop(float Delta)
{
    if(!ShopWidget)return;
    // Reveal from behind the backpack only after its drawer has reached its dock.
    const float Target=bShopOpen&&DrawerProgress>1.f-KINDA_SMALL_NUMBER?1.f:0.f;
    ShopMotion=FMath::FInterpConstantTo(ShopMotion,Target,Delta,4.f);
    const float S=ColdSteelUI::PixelScale(this),Ease=ColdSteelUI::EaseSmooth(ShopMotion);
    const float DrawerOffset=(1.f-ColdSteelUI::EaseSmooth(DrawerProgress))*(InventoryWidth+ColdSteelUI::NavigationDrawerInset);
    ShopWidget->SetRenderTranslation(FVector2D(((1-Ease)*InventoryWidth+DrawerOffset)/S,0));ShopWidget->SetRenderOpacity(Ease);
    const bool Ready=bShopOpen&&ShopMotion>1.f-KINDA_SMALL_NUMBER;
    ShopSlot->SetZOrder(Ready?42:40);
    ShopWidget->SetVisibility(ShopMotion<=0?ESlateVisibility::Collapsed:Ready?ESlateVisibility::Visible:ESlateVisibility::HitTestInvisible);
}
