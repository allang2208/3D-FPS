#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Building/EnhancementWorldView.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Building/VoxelBuildComponent.h"
#include "ColdSteelEnhancementWidget.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelWorldInteraction.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelHUDWidget.h"
#include "WeatherControlWidget.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "GameFramework/CharacterMovementComponent.h"

bool AFPSGAMEPlayerController::OpenEnhancement(const FString& Id)
{
    if(EnhancementPanel)
    {
        if(!IsEnhancementSessionValid())return false;
        const auto* Item=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->FindItem(Id);
        if(!Item||!GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>()->Supports(*Item))return false;
        EnhancementPanel->SelectItem(Id);return true;
    }
    return OpenEnhancement(ColdSteelWorldInteraction::TraceTarget(this),Id);
}
bool AFPSGAMEPlayerController::OpenEnhancement(AActor* Station,const FString& Id)
{
    if(!IsLocalController()||!GetWorld()||!GetPawn()||EnhancementPanel||GunsmithPanel||AlchemyPanel||WoodworkingPanel||ExpeditionPanel
        ||(ColdSteelHUD&&(ColdSteelHUD->IsWorldForging()||ColdSteelHUD->IsGunAssembly())))return false;
    if(!ColdSteelWorldInteraction::IsEnhancementBench(Station)||ColdSteelWorldInteraction::TraceTarget(this)!=Station)return false;
    const bool HadBag=ColdSteelHUD&&ColdSteelHUD->IsInventoryOpen();
    if((IsMoveInputIgnored()||IsLookInputIgnored())&&!HadBag)return false;
    bEnhancementReturnToInventory=HadBag;bEnhancementReturnToCursor=IsCursorOnlyInteraction();
    UWidgetBlueprintLibrary::CancelDragDrop();
    if(WeatherPanel&&WeatherPanel->IsPanelOpen())WeatherPanel->SetPanelOpen(false);
    if(VoxelBuilder&&VoxelBuilder->IsPanelOpen())VoxelBuilder->ClosePanel();
    if(ColdSteelHUD){ColdSteelHUD->CancelQuickDrag();ColdSteelHUD->HideItemTooltip(true);if(HadBag)ColdSteelHUD->ToggleInventory();}
    FActorSpawnParameters Spawn;Spawn.Owner=this;Spawn.ObjectFlags=RF_Transient;
    Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    EnhancementWorld=GetWorld()->SpawnActor<AEnhancementWorldView>(FVector::ZeroVector,FRotator::ZeroRotator,Spawn);
    if(!EnhancementWorld||!EnhancementWorld->Begin(this,Cast<AVoxelBuildPrefabActor>(Station)))
    {
        if(EnhancementWorld)EnhancementWorld->Destroy();EnhancementWorld=nullptr;
        if(HadBag&&ColdSteelHUD&&!ColdSteelHUD->IsInventoryOpen())ColdSteelHUD->ToggleInventory();
        bEnhancementReturnToInventory=false;bEnhancementReturnToCursor=false;return false;
    }
    EnhancementStation=Station;
    EnhancementPanel=CreateWidget<UColdSteelEnhancementWidget>(this);
    if(!EnhancementPanel)
    {
        EnhancementWorld->End();EnhancementWorld->Destroy();EnhancementWorld=nullptr;EnhancementStation.Reset();
        if(HadBag&&ColdSteelHUD&&!ColdSteelHUD->IsInventoryOpen())ColdSteelHUD->ToggleInventory();
        bEnhancementReturnToInventory=false;bEnhancementReturnToCursor=false;return false;
    }
    if(auto* C=Cast<AFPSGAMECharacter>(GetPawn()))
    {C->PrepareForPanelInput();if(auto* Movement=C->GetCharacterMovement())Movement->StopMovementImmediately();}
    EnhancementPanel->ConfigureWorld(EnhancementWorld);
    EnhancementPanel->SetVisibility(ESlateVisibility::SelfHitTestInvisible);EnhancementPanel->AddToViewport(60);
    if(ColdSteelHUD)ColdSteelHUD->SetEnhancementManagement(true);
    FlushPressedKeys();SetIgnoreMoveInput(true);SetIgnoreLookInput(true);bShowMouseCursor=true;
    FInputModeUIOnly Mode;Mode.SetWidgetToFocus(EnhancementPanel->TakeWidget());Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);SetInputMode(Mode);
    EnhancementPanel->SetKeyboardFocus();
    // Empty opening intent resumes persistent escrow; only the explicit retrieve
    // control sends SelectItem(""). Bind the receipt listener before any request.
    if(!Id.IsEmpty())EnhancementPanel->SelectItem(Id);
    return true;
}
bool AFPSGAMEPlayerController::IsEnhancementSessionValid() const
{return EnhancementPanel&&EnhancementWorld&&EnhancementWorld->IsSessionValid();}
AActor* AFPSGAMEPlayerController::GetEnhancementStation() const
{return IsEnhancementSessionValid()?EnhancementStation.Get():nullptr;}
bool AFPSGAMEPlayerController::IsEnhancementPanelUnderLocation(FVector2D Position) const
{return EnhancementPanel&&(EnhancementPanel->ContainsManagement(Position)||EnhancementPanel->ContainsRitual(Position));}
bool AFPSGAMEPlayerController::HandleEnhancementItemDrop(UColdSteelItemDrag* Drag,FVector2D Position)
{return IsEnhancementSessionValid()&&EnhancementPanel->HandleItemDrop(Drag,Position);}
void AFPSGAMEPlayerController::CloseEnhancement()
{
    if(!EnhancementPanel)return;
    UWidgetBlueprintLibrary::CancelDragDrop();
    auto* Closing=EnhancementPanel.Get();EnhancementPanel=nullptr;Closing->RemoveFromParent();
    if(ColdSteelHUD)ColdSteelHUD->SetEnhancementManagement(false);
    if(EnhancementWorld){EnhancementWorld->End();EnhancementWorld->Destroy();EnhancementWorld=nullptr;}EnhancementStation.Reset();
    if(auto* C=Cast<AFPSGAMECharacter>(GetPawn()))C->ApplyColdSteelProfile(GetGameInstance()->GetSubsystem<UColdSteelStatusModel>());
    FlushPressedKeys();SetIgnoreMoveInput(false);SetIgnoreLookInput(false);bShowMouseCursor=bEnhancementReturnToCursor;
    if(bEnhancementReturnToCursor){FInputModeGameAndUI Mode;Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);Mode.SetHideCursorDuringCapture(false);SetInputMode(Mode);}
    else SetInputMode(FInputModeGameOnly());
    if(bEnhancementReturnToInventory&&ColdSteelHUD&&!ColdSteelHUD->IsInventoryOpen())ColdSteelHUD->ToggleInventory();
    bEnhancementReturnToInventory=false;bEnhancementReturnToCursor=false;
}
void UColdSteelHUDWidget::SetEnhancementManagement(bool Open)
{
    if(bEnhancementManagement==Open&&bInventoryOpen==Open)return;
    if(Open){HideForgingInstantly();HideWorkbenchInstantly();HideSmeltingInstantly();CloseWarehouse();CloseShop();SetInventoryTab(false);}
    bEnhancementManagement=Open;InventoryLayoutSize=FVector2D::ZeroVector;
    TGuardValue<bool> Guard(bEnhancementInventoryTransition,true);SetInventoryOpen(Open);
}
