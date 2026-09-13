#include "VoxelBuildComponent.h"
#include "VoxelCollapseFragment.h"
#include "VoxelBuildWorld.h"
#include "VoxelBuildPalette.h"
#include "VoxelBuildWidget.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
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
    PaletteAsset=TSoftObjectPtr<UVoxelBuildPalette>(FSoftObjectPath(TEXT("/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette.DA_VoxelBuildPalette")));
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
    // AController is hidden by default. A component owned by it cannot be
    // made visible with SetVisibility alone, so the ghost needs its own Actor.
    FActorSpawnParameters PreviewSpawn;PreviewSpawn.Owner=PC;PreviewSpawn.ObjectFlags|=RF_Transient;
    PreviewSpawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    PreviewActor=GetWorld()->SpawnActor<AActor>(AActor::StaticClass(),FVector::ZeroVector,FRotator::ZeroRotator,PreviewSpawn);
    PreviewActor->SetActorHiddenInGame(false);PreviewActor->SetActorEnableCollision(false);
    auto* PreviewRoot=NewObject<USceneComponent>(PreviewActor,TEXT("VoxelPreviewRoot"));
    PreviewActor->AddInstanceComponent(PreviewRoot);PreviewActor->SetRootComponent(PreviewRoot);
    PreviewRoot->SetMobility(EComponentMobility::Movable);PreviewRoot->RegisterComponent();
    Preview=NewObject<UStaticMeshComponent>(PreviewActor,TEXT("VoxelPlacementGhost"));
    PreviewActor->AddInstanceComponent(Preview);Preview->SetupAttachment(PreviewRoot);
    Preview->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
    Preview->SetCollisionEnabled(ECollisionEnabled::NoCollision);Preview->SetCastShadow(false);
    Preview->SetMobility(EComponentMobility::Movable);
    Preview->SetCanEverAffectNavigation(false);Preview->SetVisibility(false);Preview->RegisterComponent();
    FoundationPreview=NewObject<UInstancedStaticMeshComponent>(PreviewActor,TEXT("VoxelFoundationGhost"));
    PreviewActor->AddInstanceComponent(FoundationPreview);FoundationPreview->SetupAttachment(PreviewRoot);
    FoundationPreview->SetStaticMesh(Preview->GetStaticMesh());FoundationPreview->SetMobility(EComponentMobility::Movable);
    FoundationPreview->SetCollisionEnabled(ECollisionEnabled::NoCollision);FoundationPreview->SetCastShadow(false);
    FoundationPreview->SetCanEverAffectNavigation(false);FoundationPreview->SetVisibility(false);FoundationPreview->RegisterComponent();
    auto* Material=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Building/Voxels/Rounded/M_Voxel_PlacementPreview.M_Voxel_PlacementPreview"));
    if(!Material)Material=Palette->PreviewMaterial.LoadSynchronous();
    if(Material)
    {PreviewMID=UMaterialInstanceDynamic::Create(Material,this);Preview->SetMaterial(0,PreviewMID);FoundationPreview->SetMaterial(0,PreviewMID);}
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
    if(Enabled)bSnapEnabled=true;
    if(Enabled&&BuildWorld->UnsupportedBlockCount()>0)
    {
        Feedback=FString::Printf(TEXT("已有 %d 格需要补充支撑，原建筑已保留"),BuildWorld->UnsupportedBlockCount());
        FeedbackTime=4;bFeedbackValid=false;
    }
    if(Preview)Preview->SetVisibility(false);
    if(FoundationPreview)FoundationPreview->SetVisibility(false);
    if(Widget)Widget->SetVisibility(Enabled?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    if(Enabled){UpdateTarget();UpdateWidget();}
}

void UVoxelBuildComponent::SelectMaterial(FName Id)
{
    if(Palette&&Palette->Find(Id)){SelectedMaterial=Id;FeedbackTime=0;TargetUpdateAt=0;}
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
    Placement.Reset();Removal.Reset();bCanPlace=false;PlacementVolume={};HitCell={};
    PlacementMaterial=SelectedMaterial;bPlacementSnap=bSnapEnabled;
    auto* PC=Cast<APlayerController>(GetOwner());
    if(!PC||!PC->PlayerCameraManager||!BuildWorld)return;
    const FVector Start=PC->PlayerCameraManager->GetCameraLocation();
    const FVector Direction=PC->PlayerCameraManager->GetCameraRotation().Vector();
    const FVector End=Start+Direction*600;const FIntVector Size=BrushSize();const FVector Half=FVector(Size)*10;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(VoxelAim),true,PC->GetPawn());
    const bool HasHit=GetWorld()->LineTraceSingleByChannel(Hit,Start,End,ECC_Visibility,Query);
    const bool BuildingHit=HasHit&&BuildWorld->ResolveHit(Hit,HitCell);
    if(BuildingHit)FillBrush(HitCell.Cell,Removal);
    if(!HasHit)
    {
        PlacementOrigin=Start+Direction*250-Half;
        if(bSnapEnabled)PlacementOrigin=AVoxelBuildWorld::CellMin(AVoxelBuildWorld::ToCell(PlacementOrigin));
        FillBrush(FIntVector(Size.X/2,Size.Y/2,0),Placement);
        TargetMessage=TEXT("未命中可放置表面 · 瞄准 6 米内的地面或方块");
    }
    else if(!BuildingHit)
    {
        FString GroundingMessage;
        if(BuildWorld->ResolveGroundPlacement(Hit,Size,bSnapEnabled,PlacementOrigin,Placement,GroundingMessage))
        {
            ValidatePlacement();
            if(bCanPlace)TargetMessage=GroundingMessage+TEXT("\n")+TargetMessage;
        }
        else TargetMessage=GroundingMessage;
    }
    else if(bSnapEnabled)
    {
        PlacementVolume=BuildingHit?HitCell.Volume:FGuid();PlacementOrigin=BuildWorld->VolumeOrigin(PlacementVolume);
        FIntVector Base=AVoxelBuildWorld::ToCell(Hit.ImpactPoint+Hit.ImpactNormal*.5-PlacementOrigin);
        if(BuildingHit)
        {
            int32 Axis=0;const FVector N=Hit.ImpactNormal.GetAbs();if(N.Y>N.X)Axis=1;if(N.Z>N[Axis])Axis=2;
            Base=HitCell.Cell;
            if(Axis==2)Base.Z+=Hit.ImpactNormal.Z>0?1:-Size.Z;
            else Base[Axis]+=Hit.ImpactNormal[Axis]>0?1+Size[Axis]/2:-(Size[Axis]-Size[Axis]/2);
        }
        FillBrush(Base,Placement);
        ValidatePlacement();
    }
    else
    {
        // Continuous world position: no floor/round/quantization in free mode.
        PlacementOrigin=Hit.ImpactPoint+Hit.ImpactNormal*FVector::DotProduct(Hit.ImpactNormal.GetAbs(),Half)-Half;
        FillBrush(FIntVector(Size.X/2,Size.Y/2,0),Placement);
        ValidatePlacement();
    }
    UpdatePreview(Size);
}

void UVoxelBuildComponent::UpdatePreview(FIntVector Size)
{
    if(Preview&&!Placement.IsEmpty())
    {
        const FVector Half=FVector(Size)*10;
        const FVector Min=PlacementOrigin+AVoxelBuildWorld::CellMin(Placement[0]);
        Preview->SetWorldLocation(Min+Half);Preview->SetWorldScale3D(FVector(Size)*.2+FVector(.0002));
        if(PreviewMID)
        {
            PreviewMID->SetVectorParameterValue(TEXT("Tint"),bCanPlace?FLinearColor(.06f,1.f,.15f):FLinearColor(1.f,.035f,.02f));
            PreviewMID->SetVectorParameterValue(TEXT("PreviewOrigin"),FLinearColor(Min.X,Min.Y,Min.Z));
        }
        Preview->SetHiddenInGame(false);
        Preview->SetVisibility(true);
        // One instanced box per foundation column, not an Actor per voxel.
        // All transforms use the same world-space plan that is committed.
        if(FoundationPreview)
        {
            TMap<FIntPoint,int32> Bottoms;
            const int32 MainCells=Size.X*Size.Y*Size.Z;
            for(int32 I=MainCells;I<Placement.Num();++I)
            {
                const auto Cell=Placement[I];const FIntPoint Column(Cell.X,Cell.Y);
                if(auto* Bottom=Bottoms.Find(Column))*Bottom=FMath::Min(*Bottom,Cell.Z);
                else Bottoms.Add(Column,Cell.Z);
            }
            TArray<FTransform> Transforms;
            for(const auto& Column:Bottoms)
            {
                const FVector Bottom=PlacementOrigin+AVoxelBuildWorld::CellMin(FIntVector(Column.Key.X,Column.Key.Y,Column.Value));
                const double Height=Min.Z-Bottom.Z;
                Transforms.Emplace(FQuat::Identity,Bottom+FVector(10,10,Height*.5),FVector(.2,.2,Height/100.));
            }
            if(FoundationPreview->GetInstanceCount()==Transforms.Num())
            {
                if(!Transforms.IsEmpty())FoundationPreview->BatchUpdateInstancesTransforms(0,Transforms,true,true,true);
            }
            else
            {
                FoundationPreview->ClearInstances();
                if(!Transforms.IsEmpty())FoundationPreview->AddInstances(Transforms,false,true,false);
            }
            FoundationPreview->SetHiddenInGame(false);FoundationPreview->SetVisibility(!Transforms.IsEmpty());
        }
    }
}

void UVoxelBuildComponent::ValidatePlacement()
{
    const double Now=GetWorld()->GetTimeSeconds();
    const bool Changed=CheckedRevision!=BuildWorld->StructureRevision()||CheckedMaterial!=PlacementMaterial||
        bCheckedSnap!=bPlacementSnap||CheckedVolume!=PlacementVolume||CheckedOrigin!=PlacementOrigin||CheckedCells!=Placement;
    if(Changed||Now>=PlacementCheckAt)
    {
        bCheckedValid=bPlacementSnap?BuildWorld->CanPlaceInVolume(PlacementVolume,Placement,PlacementMaterial,CheckedMessage):
            BuildWorld->CanPlaceFree(PlacementOrigin,Placement,PlacementMaterial,CheckedMessage);
        CheckedRevision=BuildWorld->StructureRevision();CheckedMaterial=PlacementMaterial;bCheckedSnap=bPlacementSnap;
        CheckedVolume=PlacementVolume;CheckedOrigin=PlacementOrigin;CheckedCells=Placement;
        PlacementCheckAt=Now+.1;
    }
    bCanPlace=bCheckedValid;TargetMessage=CheckedMessage;
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
    {if(Pressed){Brush=(Brush+(Key==EKeys::MouseScrollUp?1:2))%3;FeedbackTime=0;TargetUpdateAt=0;}return true;}
    if(Key==EKeys::R){if(Pressed){bRotate=!bRotate;FeedbackTime=0;TargetUpdateAt=0;}return true;}
    if(Key==EKeys::F){if(Pressed){bSnapEnabled=!bSnapEnabled;FeedbackTime=0;TargetUpdateAt=0;}return true;}
    if(Key==EKeys::LeftControl||Key==EKeys::RightControl)
    {bUndoModifier=Event.Event!=IE_Released;return true;}
    if(Key==EKeys::Z&&bUndoModifier)
    {if(Pressed){bFeedbackValid=BuildWorld->Undo();Feedback=BuildWorld->ResultMessage();FeedbackTime=2;}return true;}
    if(Key==EKeys::MiddleMouseButton)
    {if(Pressed&&!Removal.IsEmpty())SelectMaterial(BuildWorld->VolumeMaterialAt(HitCell.Volume,HitCell.Cell));return true;}
    if(Key==EKeys::LeftMouseButton||Key==EKeys::RightMouseButton)
    {
        if(Pressed)
        {
            // Input runs before the next camera/preview tick. Recasting here
            // would commit an unseen target. The world revalidates this exact
            // displayed plan without changing its origin or cells.
            if(Key==EKeys::LeftMouseButton)
            {
                if(bCanPlace)
                {
                    if(bPlacementSnap)bFeedbackValid=BuildWorld->EditVolumeCells(PlacementVolume,Placement,PlacementMaterial);
                    else bFeedbackValid=BuildWorld->PlaceFree(PlacementOrigin,Placement,PlacementMaterial);
                    Feedback=BuildWorld->ResultMessage();
                }
                else {bFeedbackValid=false;Feedback=TargetMessage;}
            }
            else if(!Removal.IsEmpty()){bFeedbackValid=BuildWorld->EditVolumeCells(HitCell.Volume,Removal,NAME_None);Feedback=BuildWorld->ResultMessage();}
            else if(auto* Debris=Cast<AVoxelCollapseFragment>(Hit.GetActor()))
            {BuildWorld->QueueFragmentDamage(Debris,Hit.ImpactPoint-Hit.ImpactNormal*.25,1000000,0,0);bFeedbackValid=true;Feedback=TEXT("已提交残骸拆除");}
            else {bFeedbackValid=false;Feedback=TEXT("只能拆除自己建造的体素和残骸");}
            FeedbackTime=2;
            PlacementCheckAt=0;TargetUpdateAt=0;
        }
        return true;
    }
    // Consume weapon selection/reload/interaction shortcuts while building.
    if(Key==EKeys::G||Key==EKeys::Three||Key==EKeys::Four||Key==EKeys::E)return true;
    return false;
}

void UVoxelBuildComponent::UpdateWidget()
{
    if(!Widget||!Palette||!BuildWorld)return;
    const auto* Entry=Palette->Find(SelectedMaterial);const FIntVector Size=BrushSize()*20;
    const FString Name=Entry?Entry->DisplayName.ToString():SelectedMaterial.ToString();
    const TCHAR* Shape=Brush==0?TEXT("单格"):Brush==1?TEXT("地板"):TEXT("墙面");
    Widget->ShowState(Name,FString::Printf(TEXT("%s · %d × %d × %d cm"),Shape,Size.X,Size.Y,Size.Z),
        (FeedbackTime>0?Feedback:TargetMessage)+TEXT("\n")+BuildWorld->StructureStatus(),
        FeedbackTime>0?bFeedbackValid:bCanPlace,BuildWorld->BlockCount(),bSnapEnabled);
}

void UVoxelBuildComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(!BuildWorld&&!bInitializeFailed){InitializeCountdown-=Delta;if(InitializeCountdown<=0){InitializeCountdown=.5f;TryInitializeWorld();}}
    if(!bActive)return;
    auto* PC=Cast<APlayerController>(GetOwner());
    if(!PC||!PC->GetPawn()||PC->bShowMouseCursor||PC->IsMoveInputIgnored()||PC->IsLookInputIgnored())
    {SetBuildMode(false);return;}
    FeedbackTime=FMath::Max(0.f,FeedbackTime-Delta);
    // Bound terrain probes and draft connectivity work independently of FPS.
    // Keep the displayed plan fixed between updates, including its validity.
    const double Now=GetWorld()->GetTimeSeconds();
    if(Now>=TargetUpdateAt){UpdateTarget();TargetUpdateAt=Now+1./30.;}
    UpdateWidget();
}

void UVoxelBuildComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    SetBuildMode(false);
    if(PreviewActor)PreviewActor->Destroy();if(Widget)Widget->RemoveFromParent();
    Super::EndPlay(Reason);
}
