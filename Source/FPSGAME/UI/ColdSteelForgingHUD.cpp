#include "ColdSteelHUDWidget.h"
#include "ColdSteelForgingWidget.h"
#include "ColdSteelUIStyle.h"
#include "../Building/ForgingSystem.h"
#include "../Building/ForgeInteraction.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Building/VoxelBuildWorld.h"
#include "Engine/GameInstance.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"

void UColdSteelHUDWidget::BuildForging(UCanvasPanel* Root)
{
    ForgingWidget=CreateWidget<UColdSteelForgingWidget>(GetOwningPlayer());ForgingWidget->Configure(this);
    ForgingSlot=Root->AddChildToCanvas(ForgingWidget);ForgingSlot->SetAnchors(FAnchors(1,0,1,1));ForgingSlot->SetAlignment(FVector2D(1,0));
    ForgingSlot->SetOffsets(FMargin(0,ReferenceUnits(12),ReferenceUnits(720),ReferenceUnits(12)));ForgingSlot->SetZOrder(42);
    ForgingWidget->SetVisibility(ESlateVisibility::Collapsed);
}
void UColdSteelHUDWidget::OpenForging(AActor* Station)
{
    auto* Piece=Cast<AVoxelBuildPrefabActor>(Station);auto* World=Piece?Cast<AVoxelBuildWorld>(Piece->GetOwner()):nullptr;
    if(!Piece||Piece->PrefabId()!=VoxelCastingStationId||Piece->IsFalling()||!World||!World->HasPrefabAt(Piece->AnchorCell()))return;
    if(bForgingOpen&&ForgingStation.Get()==Station)return;
    HideForgingInstantly();HideSmeltingInstantly();HideWorkbenchInstantly();CloseWarehouse();
    if(!bInventoryOpen){SetInventoryTab(false);SetInventoryOpen(true);}
    ForgingWorld=World;ForgingCell=Piece->AnchorCell();ForgingStation=Station;bForgingOpen=true;bForgeRiding=false;
    ForgingWidget->SetStation(World,ForgingCell);ForgingWidget->SetKeyboardFocus();
    ForgeInteraction=GetWorld()->SpawnActor<AForgeInteraction>();
    if(ForgeInteraction)ForgeInteraction->Prepare(GetOwningPlayer(),Piece,this);
}
void UColdSteelHUDWidget::OpenForgingSmelting()
{
    AActor* Station=ForgingStation.Get();if(Station)OpenSmelting(Station);
}
void UColdSteelHUDWidget::CloseForging()
{
    if(!bForgingOpen)return;bForgingOpen=false;
    if(auto* S=GetGameInstance()->GetSubsystem<UColdSteelForgingSystem>();S&&S->Active()){FString Reason;S->Finish(Reason);}
    ForgingWorld.Reset();ForgingStation.Reset();if(ForgingWidget)ForgingWidget->SetInputReady(false);
    if(ForgeInteraction&&!ForgeInteraction->IsRunning()){ForgeInteraction->Destroy();ForgeInteraction=nullptr;}
    if(bInventoryOpen){bForgeRiding=true;SetInventoryOpen(false);}
}
void UColdSteelHUDWidget::HideForgingInstantly()
{
    if(ForgeInteraction)
    {
        if(ForgeInteraction->IsRunning())ForgeInteraction->Stop(false);
        if(ForgeInteraction){ForgeInteraction->Destroy();ForgeInteraction=nullptr;}
    }
    if(bForgingOpen)if(auto* S=GetGameInstance()->GetSubsystem<UColdSteelForgingSystem>();S&&S->Active()){FString Reason;S->Finish(Reason);}
    bForgingOpen=false;bForgeRiding=false;ForgeMotion=0;ForgingWorld.Reset();ForgingStation.Reset();
    if(ForgingWidget){ForgingWidget->SetInputReady(false);ForgingWidget->SetVisibility(ESlateVisibility::Collapsed);ForgingWidget->SetRenderTranslation(FVector2D::ZeroVector);}
    if(ForgingSlot)ForgingSlot->SetZOrder(42);
}
void UColdSteelHUDWidget::TickForging(float DeltaTime,float DrawerEase)
{
    if(!ForgingWidget)return;
    if(bForgingOpen&&(!ForgingStation.IsValid()||!ForgingWorld.IsValid()||!ForgingWorld->HasPrefabAt(ForgingCell)))CloseForging();
    const float S=ColdSteelUI::PixelScale(this);
    if(bForgeRiding)
    {
        ForgeMotion=FMath::FInterpConstantTo(ForgeMotion,0.f,DeltaTime,4.f);
        ForgingWidget->SetVisibility(DrawerProgress>KINDA_SMALL_NUMBER?ESlateVisibility::SelfHitTestInvisible:ESlateVisibility::Collapsed);
        ForgingSlot->SetZOrder(40);
        ForgingWidget->SetRenderTranslation(FVector2D((1.f-DrawerEase)*(InventoryWidth+ColdSteelUI::NavigationDrawerInset+ForgeSlidePx)/S,0));
        if(DrawerProgress<=KINDA_SMALL_NUMBER){bForgeRiding=false;ForgingWidget->SetRenderTranslation(FVector2D::ZeroVector);}
    }
    else
    {
        if(bForgingOpen&&ForgeWidth>1)ForgeSlidePx=ForgeWidth+24;
        const float Target=bForgingOpen&&DrawerProgress>1.f-KINDA_SMALL_NUMBER&&ForgeWidth>1?1.f:0.f;
        ForgeMotion=FMath::FInterpConstantTo(ForgeMotion,Target,DeltaTime,4.f);
        ForgingWidget->SetVisibility(ForgeMotion>KINDA_SMALL_NUMBER?ESlateVisibility::SelfHitTestInvisible:ESlateVisibility::Collapsed);
        ForgingSlot->SetZOrder(ForgeMotion>1.f-KINDA_SMALL_NUMBER?42:40);
        ForgingWidget->SetRenderTranslation(FVector2D((1.f-ColdSteelUI::EaseSmooth(ForgeMotion))*FMath::Max(ForgeSlidePx,24.f)/S,0));
    }
    ForgingWidget->SetInputReady(bForgingOpen&&!bForgeRiding&&ForgeMotion>1.f-KINDA_SMALL_NUMBER);
}
bool UColdSteelHUDWidget::CanStartWorldForging(FString& Reason) const
{
    if(!ForgeInteraction){Reason=TEXT("铸造台未就绪");return false;}
    return ForgeInteraction->Ready(Reason);
}
bool UColdSteelHUDWidget::IsWorldForging() const
{return ForgeInteraction&&ForgeInteraction->IsRunning();}
bool UColdSteelHUDWidget::HandleWorldForgeInput(const FInputKeyEventArgs& Event)
{return ForgeInteraction&&ForgeInteraction->HandleInput(Event);}
bool UColdSteelHUDWidget::StartWorldForging(FName Recipe,FString& Reason)
{
    if(!bForgingOpen||!ForgeInteraction||!ForgeInteraction->Start(Recipe,Reason))return false;
    // Retain the station/job while the same paired drawer slides out. CloseForging must
    // not finalize the just-started job when SetInventoryOpen closes the inventory.
    bForgingOpen=false;bForgeRiding=true;ForgingWidget->SetInputReady(false);
    SetInventoryOpen(false);ForgeInteraction->Enter();return true;
}
void UColdSteelHUDWidget::CompleteWorldForging(AForgeInteraction* Interaction,bool bReturnPanel)
{
    if(ForgeInteraction!=Interaction)return;
    AActor* Station=ForgingStation.Get();ForgeInteraction=nullptr;
    if(bReturnPanel&&Station)OpenForging(Station);
    else HideForgingInstantly();
}
