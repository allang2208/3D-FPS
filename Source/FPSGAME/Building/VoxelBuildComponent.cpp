#include "VoxelBuildComponent.h"
#include "VoxelBuildWorld.h"
#include "VoxelBuildPalette.h"
#include "VoxelBuildWidget.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/GameInstance.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"

UVoxelBuildComponent::UVoxelBuildComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
    PaletteAsset=TSoftObjectPtr<UVoxelBuildPalette>(FSoftObjectPath(TEXT("/Game/Building/Voxels/DA_VoxelBuildPalette.DA_VoxelBuildPalette")));
}

void UVoxelBuildComponent::TryInitializeWorld()
{
    auto* PC=Cast<APlayerController>(GetOwner());
    if(!PC||!PC->IsLocalController()||!PC->GetPawn())return;
    if(GetNetMode()!=NM_Standalone){InitializationMessage=TEXT("体素初版仅用于单机世界");bInitializeFailed=true;return;}
    const FString Map=UGameplayStatics::GetCurrentLevelName(this,true);
    if(Map!=TEXT("DayNight_Lighting")&&Map!=TEXT("L_Normandy_FPS_Test")&&Map!=TEXT("L_MilitaryTrench_FPS_Test")&&Map!=TEXT("L_TemperateHills_Initial"))
    {InitializationMessage=TEXT("当前场景尚未开放体素建造");bInitializeFailed=true;return;}
    auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model||Model->ProfileSlot().IsEmpty())return;
    FString Key=Model->ProfileSlot()+TEXT("|")+Map;
    if(Map==TEXT("L_TemperateHills_Initial"))
    {
        ATemperateHillsWorld* Hills=nullptr;for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It){Hills=*It;break;}
        if(!Hills||!Hills->bReady||!Hills->WorldId.IsValid())return;
        Key+=TEXT("|")+Hills->WorldId.ToString(EGuidFormats::Digits);
    }
    Palette=PaletteAsset.LoadSynchronous();
    if(!Palette){InitializationMessage=TEXT("体素材质资源尚未生成");bInitializeFailed=true;return;}
    BuildWorld=GetWorld()->SpawnActor<AVoxelBuildWorld>();
    if(!BuildWorld||!BuildWorld->Initialize(Key,Palette))
    {InitializationMessage=BuildWorld?BuildWorld->ResultMessage():TEXT("无法创建建筑世界");bInitializeFailed=true;return;}
    Preview=NewObject<UStaticMeshComponent>(GetOwner(),TEXT("VoxelPlacementGhost"));
    Preview->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
    Preview->SetCollisionEnabled(ECollisionEnabled::NoCollision);Preview->SetCastShadow(false);
    Preview->SetCanEverAffectNavigation(false);Preview->SetVisibility(false);Preview->RegisterComponent();
    if(auto* Material=Palette->PreviewMaterial.LoadSynchronous())
    {PreviewMID=UMaterialInstanceDynamic::Create(Material,this);Preview->SetMaterial(0,PreviewMID);}
    Widget=CreateWidget<UVoxelBuildWidget>(PC);if(Widget){Widget->AddToPlayerScreen(18);Widget->SetVisibility(ESlateVisibility::Collapsed);}
}

void UVoxelBuildComponent::SetBuildMode(bool Enabled)
{
    auto* PC=Cast<APlayerController>(GetOwner());
    if(Enabled&&(!PC||PC->bShowMouseCursor||PC->IsMoveInputIgnored()||PC->IsLookInputIgnored()))return;
    if(Enabled&&(!BuildWorld||!BuildWorld->IsReady()))
    {
        // Pressing V may retry after assets have been authored in the same session.
        if(!BuildWorld){bInitializeFailed=false;TryInitializeWorld();}
        if(!BuildWorld||!BuildWorld->IsReady())
        {if(GEngine)GEngine->AddOnScreenDebugMessage(-1,4.f,FColor::Yellow,InitializationMessage);return;}
    }
    if(bActive==Enabled)return;
    if(auto* Character=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr)Character->SuspendWeaponForMenu();
    bActive=Enabled;FeedbackTime=0;bUndoModifier=false;
    if(Preview)Preview->SetVisibility(false);
    if(Widget)Widget->SetVisibility(Enabled?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    if(Enabled){UpdateTarget();UpdateWidget();}
}

void UVoxelBuildComponent::SelectMaterial(FName Id)
{
    if(Palette&&Palette->Find(Id)){SelectedMaterial=Id;FeedbackTime=0;}
}

FIntVector UVoxelBuildComponent::BrushSize() const
{
    if(Brush==1)return FIntVector(5,5,1);
    if(Brush==2)return bRotate?FIntVector(1,5,5):FIntVector(5,1,5);
    return FIntVector(1,1,1);
}

void UVoxelBuildComponent::FillBrush(FIntVector Base,TArray<FIntVector>& Result) const
{
    const FIntVector Size=BrushSize();Result.Reset();
    // Center horizontal dimensions around the aimed cell; walls grow upward.
    Base.X-=Size.X/2;Base.Y-=Size.Y/2;
    for(int32 Z=0;Z<Size.Z;++Z)for(int32 Y=0;Y<Size.Y;++Y)for(int32 X=0;X<Size.X;++X)Result.Add(Base+FIntVector(X,Y,Z));
}

void UVoxelBuildComponent::UpdateTarget()
{
    Placement.Reset();Removal.Reset();bCanPlace=false;
    if(Preview)Preview->SetVisibility(false);
    auto* PC=Cast<APlayerController>(GetOwner());
    if(!PC||!PC->PlayerCameraManager||!BuildWorld)return;
    const FVector Start=PC->PlayerCameraManager->GetCameraLocation();
    const FVector End=Start+PC->PlayerCameraManager->GetCameraRotation().Vector()*600;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(VoxelAim),true,PC->GetPawn());
    if(!GetWorld()->LineTraceSingleByChannel(Hit,Start,End,ECC_Visibility,Query))
    {TargetMessage=TEXT("瞄准 6 米内的地面或方块");return;}
    FIntVector Base=AVoxelBuildWorld::ToCell(Hit.ImpactPoint+Hit.ImpactNormal*.5);
    if(BuildWorld->OwnsSurface(Hit.GetComponent()))
    {
        const FIntVector Inside=AVoxelBuildWorld::ToCell(Hit.ImpactPoint-Hit.ImpactNormal*.5);
        FillBrush(Inside,Removal);
        // Align the whole brush beyond the targeted face, including wide walls.
        int32 Axis=0;const FVector N=Hit.ImpactNormal.GetAbs();if(N.Y>N.X)Axis=1;if(N.Z>N[Axis])Axis=2;
        const FIntVector Size=BrushSize();Base=Inside;
        if(Axis==2)Base.Z+=Hit.ImpactNormal.Z>0?1:-Size.Z;
        else Base[Axis]+=Hit.ImpactNormal[Axis]>0?1+Size[Axis]/2:-(Size[Axis]-Size[Axis]/2);
    }
    FillBrush(Base,Placement);
    bCanPlace=BuildWorld->CanPlace(Placement,SelectedMaterial,TargetMessage);
    if(Preview&&!Placement.IsEmpty())
    {
        const FIntVector Size=BrushSize();const FVector Min=AVoxelBuildWorld::CellMin(Placement[0]);
        Preview->SetWorldLocation(Min+FVector(Size)*10);Preview->SetWorldScale3D(FVector(Size)*.2+FVector(.001));
        if(PreviewMID)PreviewMID->SetVectorParameterValue(TEXT("Tint"),bCanPlace?FLinearColor(.2f,.7f,.48f):FLinearColor(.9f,.22f,.18f));
        Preview->SetVisibility(true);
    }
}

bool UVoxelBuildComponent::HandleInput(const FInputKeyEventArgs& Event,bool bMenuOpen)
{
    auto* PC=Cast<APlayerController>(GetOwner());
    if(!PC)return false;
    if(bMenuOpen||PC->bShowMouseCursor||PC->IsMoveInputIgnored()||PC->IsLookInputIgnored())
    {if(bActive)SetBuildMode(false);return false;}
    const FKey Key=Event.Key;const bool Pressed=Event.Event==IE_Pressed;
    if(Key==EKeys::V){if(Pressed)SetBuildMode(!bActive);return true;}
    if(!bActive)return false;
    if(Key==EKeys::Escape){if(Pressed)SetBuildMode(false);return true;}
    if(Pressed&&(Key==EKeys::Tab||Key==EKeys::B||Key==EKeys::K||Key==EKeys::J||Key==EKeys::F6||Key==EKeys::LeftAlt))
    {SetBuildMode(false);return false;}
    if(Key==EKeys::One||Key==EKeys::Two)
    {if(Pressed)SelectMaterial(Key==EKeys::One?FName(TEXT("wood")):FName(TEXT("stone")));return true;}
    if(Key==EKeys::MouseScrollUp||Key==EKeys::MouseScrollDown)
    {if(Pressed){Brush=(Brush+(Key==EKeys::MouseScrollUp?1:2))%3;FeedbackTime=0;}return true;}
    if(Key==EKeys::R){if(Pressed){bRotate=!bRotate;FeedbackTime=0;}return true;}
    if(Key==EKeys::LeftControl||Key==EKeys::RightControl)
    {bUndoModifier=Event.Event!=IE_Released;return true;}
    if(Key==EKeys::Z&&bUndoModifier)
    {if(Pressed){BuildWorld->Undo();Feedback=BuildWorld->ResultMessage();FeedbackTime=2;}return true;}
    if(Key==EKeys::MiddleMouseButton)
    {if(Pressed){UpdateTarget();if(!Removal.IsEmpty())SelectMaterial(BuildWorld->MaterialAt(AVoxelBuildWorld::ToCell(Hit.ImpactPoint-Hit.ImpactNormal*.5)));}return true;}
    if(Key==EKeys::LeftMouseButton||Key==EKeys::RightMouseButton)
    {
        if(Pressed)
        {
            UpdateTarget();
            if(Key==EKeys::LeftMouseButton)
            {if(bCanPlace){BuildWorld->EditCells(Placement,SelectedMaterial);Feedback=BuildWorld->ResultMessage();}else Feedback=TargetMessage;}
            else {if(!Removal.IsEmpty()){BuildWorld->EditCells(Removal,NAME_None);Feedback=BuildWorld->ResultMessage();}else Feedback=TEXT("只能拆除自己建造的体素");}
            FeedbackTime=2;
        }
        return true;
    }
    // Consume weapon selection/reload/interaction shortcuts while building.
    if(Key==EKeys::G||Key==EKeys::Three||Key==EKeys::Four||Key==EKeys::E||Key==EKeys::F)return true;
    return false;
}

void UVoxelBuildComponent::UpdateWidget()
{
    if(!Widget||!Palette||!BuildWorld)return;
    const auto* Entry=Palette->Find(SelectedMaterial);const FIntVector Size=BrushSize()*20;
    const FString Name=Entry?Entry->DisplayName.ToString():SelectedMaterial.ToString();
    const TCHAR* Shape=Brush==0?TEXT("单格"):Brush==1?TEXT("地板"):TEXT("墙面");
    Widget->ShowState(Name,FString::Printf(TEXT("%s · %d × %d × %d cm"),Shape,Size.X,Size.Y,Size.Z),
        FeedbackTime>0?Feedback:TargetMessage,bCanPlace,BuildWorld->BlockCount());
}

void UVoxelBuildComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(!BuildWorld&&!bInitializeFailed){InitializeCountdown-=Delta;if(InitializeCountdown<=0){InitializeCountdown=.5f;TryInitializeWorld();}}
    if(!bActive)return;
    auto* PC=Cast<APlayerController>(GetOwner());
    if(!PC||!PC->GetPawn()||PC->bShowMouseCursor||PC->IsMoveInputIgnored()||PC->IsLookInputIgnored())
    {SetBuildMode(false);return;}
    FeedbackTime=FMath::Max(0.f,FeedbackTime-Delta);UpdateTarget();UpdateWidget();
}

void UVoxelBuildComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    SetBuildMode(false);
    if(Preview)Preview->DestroyComponent();if(Widget)Widget->RemoveFromParent();
    Super::EndPlay(Reason);
}
