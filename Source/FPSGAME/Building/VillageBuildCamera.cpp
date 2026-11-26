#include "VoxelBuildComponent.h"
#include "VillageBuildDefense.h"
#include "../UI/ColdSteelUIStyle.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "UnrealClient.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SViewport.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
    constexpr double SurveyHeight=4200.;
    constexpr double SurveyPanSpeed=2600.;

    bool CursorInPlayerView(const APlayerController& PC,FVector2D& Cursor,FVector2D& Origin,FVector2D& Size)
    {
        const ULocalPlayer* Player=PC.GetLocalPlayer();
        auto* Client=Player?Player->ViewportClient.Get():nullptr;
        if(!Client || !Client->Viewport || !Client->Viewport->IsForegroundWindow() || !Client->GetMousePosition(Cursor))
            return false;
        const FVector2D FullSize(Client->Viewport->GetSizeXY());
        Size=FullSize*Player->Size;
        Origin=FullSize*Player->Origin;
        return Size.X>1. && Size.Y>1. && Cursor.X>=Origin.X && Cursor.Y>=Origin.Y
            && Cursor.X<Origin.X+Size.X && Cursor.Y<Origin.Y+Size.Y;
    }
}

void UVoxelBuildComponent::SyncVillageCamera()
{
    if(!bActive || !VillageBuildDefense::IsVillageRecipe(SelectedComponent))
    {
        LeaveVillageCamera(true);
        return;
    }
    if(VillageCameraOverlay)VillageCameraOverlay->SetVisibility(bPanelOpen?EVisibility::Collapsed:EVisibility::Visible);
    if(bPanelOpen || VillageCamera)return;
    auto* PC=Cast<APlayerController>(GetOwner());
    APawn* Pawn=PC?PC->GetPawn():nullptr;
    auto* Player=PC?PC->GetLocalPlayer():nullptr;
    if(!Player || !Player->ViewportClient || !Player->ViewportClient->Viewport || !Pawn || !PC->PlayerCameraManager)return;
    VillageBuilderHealth=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    if(VillageBuilderHealth.IsValid() && VillageBuilderHealth->IsDead()){SetBuildMode(false);return;}

    FActorSpawnParameters Spawn;
    Spawn.ObjectFlags|=RF_Transient;
    Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    VillageCamera=GetWorld()->SpawnActor<ACameraActor>(ACameraActor::StaticClass(),FTransform::Identity,Spawn);
    if(!VillageCamera)return;
    PreviousVillageView=PC->GetViewTarget();
    VillageCameraPawn=Pawn;
    VillageCameraYaw=PC->GetControlRotation().Yaw;
    bVillageVertical=false;
    VillageFocus=Pawn->GetActorLocation()+FRotator(0.,VillageCameraYaw,0.).Vector()*900.;
    VillageCamera->GetCameraComponent()->SetFieldOfView(65.f);
    VillageCamera->GetCameraComponent()->bConstrainAspectRatio=false;
    PositionVillageCamera();
    PC->SetViewTarget(VillageCamera);
    PC->PlayerCameraManager->UpdateCamera(0.f);
    PC->FlushPressedKeys();
    PC->SetIgnoreMoveInput(true);
    PC->SetIgnoreLookInput(true);
    bVillageDisabledPawn=Pawn->InputEnabled();
    Pawn->ConsumeMovementInputVector();
    if(auto* Character=Cast<ACharacter>(Pawn))
    {
        Character->StopJumping();
        if(Character->GetCharacterMovement()->IsMovingOnGround())
            Character->GetCharacterMovement()->StopMovementImmediately();
    }
    if(bVillageDisabledPawn)Pawn->DisableInput(PC);

    // A transparent canvas above the gameplay HUD keeps placement clicks on the viewport.
    // The drawer regains its own hit targets when the catalog is opened.
    VillageCameraOverlay=SNew(SOverlay).Visibility(EVisibility::Visible)
        +SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Bottom).Padding(8.f,0.f,8.f,32.f)
        [
            SAssignNew(VillageCameraCaption,STextBlock)
            .Font(ColdSteelUI::TextFont(14.f * .75f))
            .Justification(ETextJustify::Center)
            .ColorAndOpacity(FLinearColor::White).ShadowColorAndOpacity(FLinearColor::Black)
            .ShadowOffset(FVector2D(1.,1.)).Visibility(EVisibility::HitTestInvisible)
        ];
    LastWidgetCheapKey=MAX_uint64;
    Player->ViewportClient->AddViewportWidgetForPlayer(Player,VillageCameraOverlay.ToSharedRef(),22);
    SetVillageCursorMode();
    const FVector2D FullSize(Player->ViewportClient->Viewport->GetSizeXY());
    const FVector2D Center=(Player->Origin+Player->Size*.5)*FullSize;
    PC->SetMouseLocation(FMath::RoundToInt(Center.X),FMath::RoundToInt(Center.Y));
}

void UVoxelBuildComponent::SetVillageCursorMode()
{
    auto* PC=Cast<APlayerController>(GetOwner());
    auto* Player=PC?PC->GetLocalPlayer():nullptr;
    if(!Player || !Player->ViewportClient)return;
    FInputModeGameAndUI Mode;
    Mode.SetWidgetToFocus(Player->ViewportClient->GetGameViewportWidget());
    Mode.SetHideCursorDuringCapture(false);
    Mode.SetLockMouseToViewportBehavior(EMouseLockMode::LockAlways);
    PC->SetInputMode(Mode);
    PC->bShowMouseCursor=true;
}

void UVoxelBuildComponent::LeaveVillageCamera(bool RestoreGameInput)
{
    if(!VillageCamera)return;
    if(auto* PC=Cast<APlayerController>(GetOwner()))
    {
        auto* Player=PC->GetLocalPlayer();
        if(VillageCameraOverlay && Player && Player->ViewportClient)
            Player->ViewportClient->RemoveViewportWidgetForPlayer(Player,VillageCameraOverlay.ToSharedRef());
        if(PC->GetViewTarget()==VillageCamera)
        {
            AActor* View=PreviousVillageView.Get();
            if(!View || PC->GetPawn()!=VillageCameraPawn.Get())View=PC->GetPawn();
            PC->SetViewTarget(View?View:PC);
        }
        if(bVillageDisabledPawn && VillageCameraPawn.IsValid())
            VillageCameraPawn->EnableInput(nullptr);
        PC->SetIgnoreMoveInput(false);
        PC->SetIgnoreLookInput(false);
        if(RestoreGameInput && !bPanelOpen)
        {
            PC->bShowMouseCursor=false;
            PC->SetInputMode(FInputModeGameOnly());
        }
    }
    VillageCameraOverlay.Reset();
    VillageCameraCaption.Reset();
    VillageBuilderHealth.Reset();
    VillageCamera->Destroy();
    VillageCamera=nullptr;
    VillageCameraPawn.Reset();
    PreviousVillageView.Reset();
    bVillageDisabledPawn=false;
}

void UVoxelBuildComponent::PositionVillageCamera()
{
    if(const auto* Hills=VillageWorld.Get())
        VillageFocus.Z=Hills->Height(VillageFocus.X,VillageFocus.Y);
    const FRotator Rotation(bVillageVertical?-90.:-45.,VillageCameraYaw,0.);
    const FVector Position=VillageFocus-Rotation.Vector()*(SurveyHeight/-Rotation.Vector().Z);
    VillageCamera->SetActorLocationAndRotation(Position,Rotation);
}

void UVoxelBuildComponent::UpdateVillageCamera(float DeltaSeconds)
{
    const auto* PC=CastChecked<APlayerController>(GetOwner());
    FVector2D Cursor,Origin,Size;
    if(!CursorInPlayerView(*PC,Cursor,Origin,Size))return;
    const FVector2D Local=Cursor-Origin;
    const double Margin=FMath::Clamp(Size.GetMin()*.04,12.,42.);
    const auto Edge=[Margin](double P,double Extent)
    {
        return FMath::Clamp((P-Extent+1.+Margin)/Margin,0.,1.)-FMath::Clamp((Margin-P)/Margin,0.,1.);
    };
    const FVector Screen(-Edge(Local.Y,Size.Y),Edge(Local.X,Size.X),0.);
    if(Screen.IsNearlyZero())return;
    const FVector Move=FRotator(0.,VillageCameraYaw,0.).RotateVector(Screen.GetClampedToMaxSize(1.));
    const FVector Anchor=PC->GetPawn()->GetActorLocation();
    const FVector Offset=(VillageFocus+Move*(SurveyPanSpeed*DeltaSeconds)-Anchor).GetClampedToMaxSize2D(VillageBuildDefense::SurveyRadius);
    VillageFocus.X=Anchor.X+Offset.X;
    VillageFocus.Y=Anchor.Y+Offset.Y;
    PositionVillageCamera();
}

bool UVoxelBuildComponent::VillageCursorRay(FVector& Origin,FVector& Direction) const
{
    const auto* PC=CastChecked<APlayerController>(GetOwner());
    FVector2D Cursor,TopLeft,Size;
    return CursorInPlayerView(*PC,Cursor,TopLeft,Size)
        && PC->DeprojectScreenPositionToWorld(Cursor.X,Cursor.Y,Origin,Direction);
}
