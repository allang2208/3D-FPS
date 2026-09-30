#include "ColdSteelHUDWidget.h"
#include "ColdSteelWorkbenchWidget.h"
#include "ColdSteelGunAssemblyWidget.h"
#include "../Building/GunAssemblySystem.h"
#include "Engine/GameInstance.h"
#include "ColdSteelUIStyle.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Building/VoxelBuildTypes.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Building/GunAssemblyInteraction.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/Button.h"

void UColdSteelHUDWidget::BuildWorkbench(UCanvasPanel* Root)
{
    // 与打铁/枪械装配面板同一挂载（BuildForging）：锚右缘、上下 12px、全宽 720 基准（2026-09-28 制造栏复制升级）；
    // 槽位＝屏幕左缘→面板右缘的全宽命中区，面板本体在内部按推送坐标重排。
    WorkbenchWidget=CreateWidget<UColdSteelWorkbenchWidget>(GetOwningPlayer());
    WorkbenchWidget->Configure(this);
    WorkbenchSlot=Root->AddChildToCanvas(WorkbenchWidget);
    WorkbenchSlot->SetAnchors(FAnchors(1,0,1,1));
    WorkbenchSlot->SetAlignment(FVector2D(1,0));
    WorkbenchSlot->SetOffsets(FMargin(0,ReferenceUnits(12),ReferenceUnits(720),ReferenceUnits(12)));
    WorkbenchSlot->SetZOrder(42);
    WorkbenchWidget->SetVisibility(ESlateVisibility::Collapsed);
    GunAssemblyWidget=CreateWidget<UColdSteelGunAssemblyWidget>(GetOwningPlayer());GunAssemblyWidget->Configure(this);
    GunAssemblySlot=Root->AddChildToCanvas(GunAssemblyWidget);
    GunAssemblySlot->SetAnchors(FAnchors(1,0,1,1));GunAssemblySlot->SetAlignment(FVector2D(1,0));
    GunAssemblySlot->SetOffsets(FMargin(0,ReferenceUnits(12),ReferenceUnits(720),ReferenceUnits(12)));
    GunAssemblySlot->SetZOrder(42);GunAssemblyWidget->SetVisibility(ESlateVisibility::Collapsed);
}

void UColdSteelHUDWidget::OpenWorkbench(AActor* Workbench)
{
    auto* Piece=Cast<AVoxelBuildPrefabActor>(Workbench);
    auto* World=Piece?Cast<AVoxelBuildWorld>(Piece->GetOwner()):nullptr;
    if(!Piece||(Piece->PrefabId()!=VoxelWorkbenchId&&Piece->PrefabId()!=VoxelGunWorkbenchId)
        ||Piece->IsFalling()||!World||!World->HasPrefabAt(Piece->AnchorCell()))return;
    if(GunAssemblyInteraction){auto* Previous=GunAssemblyInteraction.Get();GunAssemblyInteraction=nullptr;if(Previous->IsRunning())Previous->Stop(false);Previous->Destroy();}
    GunWorkbenchStation.Reset();
    // 工作台 E＝背包＋制作面板一起开（高炉同款生命周期）；打开背包本身永远不带出面板。
    if(bSmeltingOpen)HideSmeltingInstantly();   // 同贴位互斥：瞬收冶炼面板，避免两层叠画
    if(bForgingOpen||bForgeRiding)HideForgingInstantly();
    if(!bInventoryOpen){SetInventoryTab(false);SetInventoryOpen(true);}
    WorkbenchWorld=World;WorkbenchCell=Piece->AnchorCell();
    bWorkbenchOpen=true;bWorkbenchRiding=false;   // 弹出相位：抽屉到位后面板从其左缘滑出
    bGunWorkbenchPanel=Piece->PrefabId()==VoxelGunWorkbenchId;
    WorkbenchWidget->SetVisibility(ESlateVisibility::Collapsed);GunAssemblyWidget->SetVisibility(ESlateVisibility::Collapsed);
    WorkbenchWidget->SetInputReady(false);
    if(Piece->PrefabId()==VoxelGunWorkbenchId)
    {
        GunWorkbenchStation=Piece;GunAssemblyInteraction=GetWorld()->SpawnActor<AGunAssemblyInteraction>();
        if(GunAssemblyInteraction)GunAssemblyInteraction->Prepare(GetOwningPlayer(),Piece,this);
    }
    if(bGunWorkbenchPanel&&GunAssemblyWidget)
    {GunAssemblyWidget->OpenStation();GunAssemblyWidget->SetKeyboardFocus();}
    else if(WorkbenchWidget)
    {
        WorkbenchWidget->SetWorkbench(World,WorkbenchCell);
        // 可见性与滑动进度统一由 NativeTick 的 WorkbenchMotion 驱动（与背包抽屉同动画）。
        WorkbenchWidget->SetKeyboardFocus();
    }
}

void UColdSteelHUDWidget::CloseWorkbench()
{
    if(!bWorkbenchOpen)return;
    bWorkbenchOpen=false;
    if(WorkbenchWidget)WorkbenchWidget->SetInputReady(false);
    WorkbenchWorld.Reset();
    if(GunAssemblyInteraction&&!GunAssemblyInteraction->IsRunning()){GunAssemblyInteraction->Destroy();GunAssemblyInteraction=nullptr;GunWorkbenchStation.Reset();}
    // 关闭＝制作栏＋背包一个整体向右缩回（冶炼定稿口径）：立即关抽屉，
    // 面板在 Tick 里与抽屉同一位移曲线刚体骑乘；背包本就开着时面板单独滑出。
    if(bInventoryOpen){bWorkbenchRiding=true;SetInventoryOpen(false);}
    if(bInventoryOpen&&CloseButton)CloseButton->SetKeyboardFocus();
}

void UColdSteelHUDWidget::HideWorkbenchInstantly()
{
    if(GunAssemblyInteraction){auto* Previous=GunAssemblyInteraction.Get();GunAssemblyInteraction=nullptr;if(Previous->IsRunning())Previous->Stop(false);Previous->Destroy();}
    GunWorkbenchStation.Reset();
    // 互斥瞬收：不播骑乘动画，直接归位收起（两面板共用同一贴位，开另一个前清场）。
    bWorkbenchOpen=false;
    bWorkbenchRiding=false;
    WorkbenchMotion=0.f;
    WorkbenchWorld.Reset();
    if(WorkbenchWidget)
    {
        WorkbenchWidget->SetVisibility(ESlateVisibility::Collapsed);
        WorkbenchWidget->SetInputReady(false);
        WorkbenchWidget->SetRenderTranslation(FVector2D::ZeroVector);
    }
    if(WorkbenchSlot)WorkbenchSlot->SetZOrder(42);
    if(GunAssemblyWidget){GunAssemblyWidget->SetVisibility(ESlateVisibility::Collapsed);GunAssemblyWidget->SetRenderTranslation(FVector2D::ZeroVector);GunAssemblyWidget->SetInputReady(false);}
    if(GunAssemblySlot)GunAssemblySlot->SetZOrder(42);
}

bool UColdSteelHUDWidget::SelectGunAssemblyRecipe(FName Recipe)
{
    if(!bWorkbenchOpen||!bGunWorkbenchPanel||IsGunAssembly())return false;
    auto* System=GetGameInstance()->GetSubsystem<UGunAssemblySystem>();
    auto* Station=Cast<AVoxelBuildPrefabActor>(GunWorkbenchStation.Get());
    if(!System||!Station||!System->SelectRecipe(Recipe))return false;
    if(GunAssemblyInteraction)GunAssemblyInteraction->Destroy();
    GunAssemblyInteraction=GetWorld()->SpawnActor<AGunAssemblyInteraction>();
    if(GunAssemblyInteraction)GunAssemblyInteraction->Prepare(GetOwningPlayer(),Station,this);
    return GunAssemblyInteraction!=nullptr;
}

bool UColdSteelHUDWidget::CanStartGunAssembly(FString& Reason) const
{if(!GunAssemblyInteraction){Reason=TEXT("枪械工作台未就绪");return false;}return GunAssemblyInteraction->Ready(Reason);}
bool UColdSteelHUDWidget::StartGunAssembly(FString& Reason)
{
    if(!bWorkbenchOpen||!GunAssemblyInteraction||!GunAssemblyInteraction->Start(Reason))return false;
    bWorkbenchOpen=false;bWorkbenchRiding=true;SetInventoryOpen(false);GunAssemblyInteraction->Enter();return true;
}
bool UColdSteelHUDWidget::IsGunAssembly() const
{return GunAssemblyInteraction&&GunAssemblyInteraction->IsRunning();}
bool UColdSteelHUDWidget::HandleGunAssemblyInput(const FInputKeyEventArgs& Event)
{return GunAssemblyInteraction&&GunAssemblyInteraction->HandleInput(Event);}
void UColdSteelHUDWidget::CompleteGunAssembly(AGunAssemblyInteraction* Interaction,bool bReturnPanel)
{
    if(GunAssemblyInteraction!=Interaction)return;
    AActor* Station=GunWorkbenchStation.Get();GunAssemblyInteraction=nullptr;
    if(bReturnPanel&&Station)OpenWorkbench(Station);else HideWorkbenchInstantly();
}
