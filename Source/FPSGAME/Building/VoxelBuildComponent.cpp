#include "VoxelBuildComponent.h"
#include "VoxelCollapseFragment.h"
#include "VoxelBuildWorld.h"
#include "VoxelBuildPalette.h"
#include "VoxelBuildPrefabActor.h"
#include "VoxelBuildWidget.h"
#include "VoxelJointStrength.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/GameInstance.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"

namespace
{
    /**
     * Cone aim assist for snap mode: the centre ray rarely lands exactly on a voxel face once the
     * player drifts a little, which used to drop the ghost into the air. Probe a small cone
     * (8 directions x 1.5 deg / 3 deg) and return the first voxel hit so the ghost stays glued to a
     * surface until there really is nothing snappable in view.
     */
    bool TrySnapAssist(UWorld* World,AVoxelBuildWorld* BuildWorld,const FVector& Start,const FVector& Direction,
        const FCollisionQueryParams& Query,FHitResult& OutHit,FVoxelBuildKey& OutCell)
    {
        if(!World||!BuildWorld)return false;
        const FQuat Basis=FRotationMatrix::MakeFromX(Direction).ToQuat();
        const FVector End=Start+Direction*600;
        for(const float Angle:{1.5f,3.f})
        {
            const float Spread=FMath::Tan(FMath::DegreesToRadians(Angle));
            for(int32 Index=0;Index<8;++Index)
            {
                const float Theta=2.f*PI*float(Index)/8.f;
                const FVector Offset=Basis.RotateVector(FVector(0.f,FMath::Cos(Theta),FMath::Sin(Theta))*Spread);
                const FVector ProbeDirection=(Direction+Offset).GetSafeNormal();
                FHitResult Probe;
                if(World->LineTraceSingleByChannel(Probe,Start,Start+ProbeDirection*600,ECC_Visibility,Query)
                    &&BuildWorld->ResolveHit(Probe,OutCell))
                {OutHit=Probe;return true;}
            }
        }
        return false;
    }

    // TEMPORARY diagnostics for the 2026-09-16 "cannot build above 2 m" report.
    FString LastPreviewReject;
    // Cells dropped from the current plan because the local player's body is there (see
    // ClipLocalPlayerCells). File scope keeps the fix hot-patchable; there is one local builder.
    int32 ClippedPlayerCells=0;
    // True when the current plan grows the aimed column upward instead of placing beside it.
    bool GrowUpPlan=false;
    // Interaction smoothing: the ghost follows the camera every frame, but a momentary aim miss
    // keeps the previous snapped plan briefly instead of jumping to the floating fallback position.
    double LastSnapTime=-10.;
    double GroundSampleAt=-10.;
    // Gold edge highlight on the snapped neighbour block. Held here (not as UPROPERTY members) so the
    // change stays a body-only hot patch; the components are owned by the preview Actor, and the
    // pointers are refreshed in TryInitializeWorld, so they are GC-safe and never dangle across maps.
    UInstancedStaticMeshComponent* AimEdgeComponent=nullptr;
    UMaterialInstanceDynamic* AimEdgeMaterial=nullptr;
    FIntVector AimEdgeCell(INT32_MAX);
    bool bAimEdgeGold=false;
    uint32 AimEdgeSignature=0;
    int32 AimEdgeCount=-1;
    // Set when the last update had to use the cone aim assist instead of the centre ray.
    bool LastAimWasAssisted=false;

    /** Re-resolves the gold outline component from the preview Actor when the cached pointer is gone.

        The cache above is a file-scope pointer, and a Live Coding reload can drop it while the old
        instance buffer stays registered and visible - nothing could clear it any more, which is the
        "outline survives leaving build mode" report. The preview Actor is a UPROPERTY member, so
        looking the component up by name whenever the cache is empty always finds the live one. */
    UInstancedStaticMeshComponent* FindAimEdge(AActor* PreviewActor)
    {
        if(AimEdgeComponent&&AimEdgeComponent->IsValidLowLevelFast())return AimEdgeComponent;
        AimEdgeComponent=nullptr;
        if(!PreviewActor)return nullptr;
        for(UActorComponent* Component:PreviewActor->GetComponents())
            if(auto* Instanced=Cast<UInstancedStaticMeshComponent>(Component))
                if(Instanced->GetFName()==FName(TEXT("VoxelAimEdges"))){AimEdgeComponent=Instanced;break;}
        return AimEdgeComponent;
    }
    /** Drops and hides the gold outline. Safe to call repeatedly and works even if the cache was lost. */
    void ClearAimHighlight(AActor* PreviewActor)
    {
        if(auto* Edges=FindAimEdge(PreviewActor)){Edges->ClearInstances();Edges->SetVisibility(false);}
        AimEdgeCell=FIntVector(INT32_MAX);AimEdgeSignature=0;AimEdgeCount=-1;
    }

    FString StrengthText(double Pascal)
    {
        return Pascal>=1000000.?FString::Printf(TEXT("%.1f MPa"),Pascal/1000000.):FString::Printf(TEXT("%.0f kPa"),Pascal/1000.);
    }
    FString MassText(double Kilograms)
    {
        return Kilograms>=1000.?FString::Printf(TEXT("%.1f t"),Kilograms/1000.):FString::Printf(TEXT("%.1f kg"),Kilograms);
    }
    FString SpanText(double Meters,double CapMeters)
    {
        if(Meters<=0.)return TEXT("单格就断");
        return Meters>=CapMeters?FString::Printf(TEXT("≥ %.1f m"),Meters):FString::Printf(TEXT("%.1f m"),Meters);
    }
    // Number row while building: the Nth entry of the palette (materials first, then components).
    int32 NumberKeyIndex(const FKey& Key)
    {
        static const FKey Keys[]={EKeys::One,EKeys::Two,EKeys::Three,EKeys::Four,EKeys::Five,EKeys::Six,EKeys::Seven,EKeys::Eight,EKeys::Nine};
        for(int32 Index=0;Index<UE_ARRAY_COUNT(Keys);++Index)if(Key==Keys[Index])return Index;
        return INDEX_NONE;
    }
    // Last frame the drawer widget consumed a key itself; keeps the same press from running twice.
    // File scope instead of a member so the change stays a function-body patch.
    uint64 DrawerKeyFrame=0;
}

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
    Preview->SetStaticMesh(GhostMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
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
    // Gold edge highlight for the block being snapped against: twelve thin bars with their own MID.
    AimEdgeComponent=NewObject<UInstancedStaticMeshComponent>(PreviewActor,TEXT("VoxelAimEdges"));
    PreviewActor->AddInstanceComponent(AimEdgeComponent);AimEdgeComponent->SetupAttachment(PreviewRoot);
    AimEdgeComponent->SetStaticMesh(Preview->GetStaticMesh());AimEdgeComponent->SetMobility(EComponentMobility::Movable);
    AimEdgeComponent->SetCollisionEnabled(ECollisionEnabled::NoCollision);AimEdgeComponent->SetCastShadow(false);
    AimEdgeComponent->SetCanEverAffectNavigation(false);AimEdgeComponent->SetVisibility(false);
    UMaterialInterface* EdgeMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Building/Voxels/Rounded/M_VoxelAimEdge.M_VoxelAimEdge"));
    bAimEdgeGold=EdgeMaterial!=nullptr;
    if(!EdgeMaterial)EdgeMaterial=Material;
    if(EdgeMaterial){AimEdgeMaterial=UMaterialInstanceDynamic::Create(EdgeMaterial,this);AimEdgeComponent->SetMaterial(0,AimEdgeMaterial);}
    AimEdgeComponent->RegisterComponent();
    ClearAimHighlight(PreviewActor);
    // Above the gameplay HUD so the flush-right drawer covers the panel navigation entries.
    Widget=CreateWidget<UVoxelBuildWidget>(PC);if(Widget){Widget->AddToPlayerScreen(21);Widget->SetVisibility(ESlateVisibility::Collapsed);}
    PushPanelContent();
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
    // The gold snapped-neighbour outline is not refreshed once build mode stops, so clear it here.
    ClearAimHighlight(PreviewActor);
    // Entering build mode opens the drawer with the cursor; picking an entry returns to aiming.
    SetPanelOpen(Enabled);
    if(Enabled){PlacementCheckAt=0;TargetUpdateAt=0;UpdateWidget();}
}

void UVoxelBuildComponent::SetPanelOpen(bool Open)
{
    if(bPanelOpen==Open)return;
    bPanelOpen=Open;
    // Visibility first: Slate cannot focus a collapsed widget.
    if(Widget)Widget->SetDrawerOpen(Open);
    if(auto* PC=Cast<APlayerController>(GetOwner()))
    {
        if(Open)
        {
            // The drawer owns cursor and keyboard; the world keeps running without gameplay input.
            PC->SetIgnoreMoveInput(true);PC->SetIgnoreLookInput(true);PC->bShowMouseCursor=true;
            FInputModeUIOnly Mode;Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
            if(Widget)Mode.SetWidgetToFocus(Widget->TakeWidget());
            PC->SetInputMode(Mode);
            if(Widget)Widget->SetKeyboardFocus();
        }
        else
        {
            PC->SetIgnoreMoveInput(false);PC->SetIgnoreLookInput(false);PC->bShowMouseCursor=false;
            PC->SetInputMode(FInputModeGameOnly());
        }
    }
    if(Preview)Preview->SetVisibility(false);
    if(FoundationPreview)FoundationPreview->SetVisibility(false);
    ClearAimHighlight(PreviewActor);
    if(!Open&&bActive){PlacementCheckAt=0;TargetUpdateAt=0;UpdateTarget();UpdateWidget();}
}

bool UVoxelBuildComponent::HandlePanelKey(const FKey& Key)
{
    if(!Palette)return false;
    if(Key==EKeys::Zero){SelectComponent(NAME_None);return true;}
    const int32 Index=NumberKeyIndex(Key);
    if(Index==INDEX_NONE)return false;
    if(Palette->Materials.IsValidIndex(Index)){SelectMaterial(Palette->Materials[Index].Id);return true;}
    const int32 ComponentIndex=Index-Palette->Materials.Num();
    if(Palette->Components.IsValidIndex(ComponentIndex)){SelectComponentByIndex(ComponentIndex);return true;}
    return false;
}

bool UVoxelBuildComponent::HandleDrawerKey(const FKey& Key)
{
    // The drawer owns focus while it is open, so its own B/Esc cycle lives here.
    DrawerKeyFrame=GFrameCounter;
    if(Key==EKeys::B)
    {
        if(bPanelOpen)SetBuildMode(false);else SetPanelOpen(true);
        return true;
    }
    if(Key==EKeys::Escape)
    {
        if(bPanelOpen)SetPanelOpen(false);else SetBuildMode(false);
        return true;
    }
    return HandlePanelKey(Key);
}

void UVoxelBuildComponent::SelectMaterial(FName Id)
{
    if(Palette&&Palette->Find(Id))
    {
        SelectedMaterial=Id;SelectedComponent=NAME_None;ComponentYaw=0;
        FeedbackTime=0;TargetUpdateAt=0;PlacementCheckAt=0;
        if(Widget)Widget->SetSelection(SelectedMaterial,SelectedComponent);
        SetPanelOpen(false);
    }
}

void UVoxelBuildComponent::SelectComponent(FName Id)
{
    // Selecting a component leaves voxel material selection untouched; 1/2 returns to voxels.
    SelectedComponent=(Palette&&Palette->FindComponent(Id))?Id:NAME_None;
    ComponentYaw=0;AimedPrefab=nullptr;bPrefabValid=false;
    FeedbackTime=0;TargetUpdateAt=0;PlacementCheckAt=0;
    if(Widget)Widget->SetSelection(SelectedMaterial,SelectedComponent);
    if(bActive)SetPanelOpen(false);
}

void UVoxelBuildComponent::SelectComponentByIndex(int32 Index)
{
    if(!Palette||!Palette->Components.IsValidIndex(Index))return;
    SelectComponent(Palette->Components[Index].Id);
}

const FVoxelBuildPrefab* UVoxelBuildComponent::SelectedPrefab() const
{
    return (Palette&&!SelectedComponent.IsNone())?Palette->FindComponent(SelectedComponent):nullptr;
}

void UVoxelBuildComponent::PushPanelContent()
{
    if(!Widget||!Palette)return;
    TArray<FVoxelBuildPanelCard> Materials,Components;
    for(const FVoxelBuildMaterial& Entry:Palette->Materials)
    {
        if(Entry.Id.IsNone())continue;
        const FVoxelPhysicalMaterial Physics=Palette->Physical(Entry.Id);
        VoxelJointStrength::FMaterial Joint;
        Joint.DensityKgM3=Physics.DensityKgM3;Joint.CompressionPa=Physics.CompressionPa;
        Joint.TensionPa=Physics.TensionPa;Joint.ShearPa=Physics.ShearPa;
        // Offline-verified numbers from the same header Tools/Building/voxel_stress_probe.cpp uses.
        // Sweep long enough to reach the real limit after the 2026-09-16 strength doubling (wood
        // 4.4 m / stone 4.0 m); the probe scans the same 25 cells.
        constexpr int32 SpanSweepCells=25;
        const double SpanSelf=VoxelJointStrength::MaxSpanMeters(Joint,0.,SpanSweepCells);
        const double SpanLoaded=VoxelJointStrength::MaxSpanMeters(Joint,100.,SpanSweepCells);
        const double CellAreaM2=0.04;
        const double CellLoadT=Physics.CompressionPa*CellAreaM2/9.81/1000.;
        FVoxelBuildPanelCard Card;
        Card.Id=Entry.Id;
        Card.Caption=Entry.DisplayName.IsEmpty()?Entry.Id.ToString():Entry.DisplayName.ToString();
        Card.Detail=Entry.Id.ToString();
        Card.bComponent=false;
        Card.Subtitle=FString::Printf(TEXT("体素 · %s · 20 cm 立方"),Physics.DensityKgM3>=2000.?TEXT("石材类"):TEXT("木材类"));
        Card.Rows.Add({TEXT("物理参数"),TEXT("")});
        Card.Rows.Add({TEXT("密度"),FString::Printf(TEXT("%.0f kg/m³"),Physics.DensityKgM3)});
        Card.Rows.Add({TEXT("单格质量"),FString::Printf(TEXT("%s（20×20×20 cm）"),*MassText(Joint.MassPerCellKg()))});
        Card.Rows.Add({TEXT("抗压"),StrengthText(Physics.CompressionPa)});
        Card.Rows.Add({TEXT("抗拉"),StrengthText(Physics.TensionPa)});
        Card.Rows.Add({TEXT("抗剪"),StrengthText(Physics.ShearPa)});
        Card.Rows.Add({TEXT("耐久 / 单点冲击"),FString::Printf(TEXT("%.0f / %.0f J"),Physics.Durability,Physics.JoulesPerDamage)});
        Card.Rows.Add({TEXT("建造能力"),TEXT("")});
        Card.Rows.Add({TEXT("保证净跨"),TEXT("2.0 m")});
        Card.Rows.Add({TEXT("最长挑空（自重）"),SpanText(SpanSelf,SpanSweepCells*0.2)});
        Card.Rows.Add({TEXT("最长挑空（跨中站人）"),SpanText(SpanLoaded,SpanSweepCells*0.2)});
        Card.Rows.Add({TEXT("每平方米承重"),FString::Printf(TEXT("%s/m²"),*MassText(Joint.LoadPerSquareMeterT()*1000.))});
        Card.Rows.Add({TEXT("单格承重（20×20 cm 面）"),MassText(CellLoadT*1000.)});
        Card.Note=TEXT("净跨 2.0 m 以内最稳（含跨中站人）；超过上限会断键、失去地基连接并倒塌成残骸。墙与柱没有实际跨度上限。");
        Materials.Add(MoveTemp(Card));
    }
    for(const FVoxelBuildPrefab& Entry:Palette->Components)
    {
        if(Entry.Id.IsNone())continue;
        FVoxelBuildPanelCard Card;
        Card.Id=Entry.Id;
        Card.Caption=Entry.DisplayName.IsEmpty()?Entry.Id.ToString():Entry.DisplayName.ToString();
        Card.Detail=FString::Printf(TEXT("%d × %d × %d cm"),Entry.Footprint.X*20,Entry.Footprint.Y*20,Entry.Footprint.Z*20);
        Card.bComponent=true;
        Card.Subtitle=TEXT("构件 · 20 cm 格吸附");
        Card.Rows.Add({TEXT("占格尺寸"),Card.Detail});
        Card.Rows.Add({TEXT("20 cm 占格"),FString::Printf(TEXT("%d × %d × %d"),Entry.Footprint.X,Entry.Footprint.Y,Entry.Footprint.Z)});
        Card.Rows.Add({TEXT("网格"),Entry.Mesh.IsNull()?TEXT("—"):Entry.Mesh.GetAssetName()});
        Card.Rows.Add({TEXT("材质"),Entry.Surface.IsNull()?TEXT("—"):Entry.Surface.GetAssetName()});
        Card.Note=TEXT("构件按 20 cm 网格放置（R 旋转 90°、右键拆除）。构件不参与承重：它不与体素焊合，也不提供支撑路径。");
        Components.Add(MoveTemp(Card));
    }
    Widget->SetContent(Materials,Components);
    Widget->SetSelection(SelectedMaterial,SelectedComponent);
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
    PlacementMaterial=SelectedMaterial;bPlacementSnap=bSnapEnabled;
    // The gold snapped-neighbour highlight is refreshed only by the snapped branch below. Only the
    // visibility is lowered here: the instance buffer and its signature cache stay, so the steady
    // state really is "rebuild only when the touching blocks change".
    if(auto* Edges=FindAimEdge(PreviewActor))Edges->SetVisibility(false);
    auto* PC=Cast<APlayerController>(GetOwner());
    if(!PC||!PC->PlayerCameraManager||!BuildWorld)return;
    const FVector Start=PC->PlayerCameraManager->GetCameraLocation();
    const FVector Direction=PC->PlayerCameraManager->GetCameraRotation().Vector();
    const FVector End=Start+Direction*600;const FIntVector Size=BrushSize();const FVector Half=FVector(Size)*10;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(VoxelAim),true,PC->GetPawn());
    bool HasHit=GetWorld()->LineTraceSingleByChannel(Hit,Start,End,ECC_Visibility,Query);
    bool BuildingHit=HasHit&&BuildWorld->ResolveHit(Hit,HitCell);
    LastAimWasAssisted=false;
    // Snap mode stays glued to a voxel surface inside a small cone: drifting the aim a little must
    // only switch which surface is snapped, not drop the ghost into the air. Only a real turn away
    // from every snappable surface falls through to the floating fallback below.
    if(!BuildingHit&&bSnapEnabled&&TrySnapAssist(GetWorld(),BuildWorld,Start,Direction,Query,Hit,HitCell))
    {
        HasHit=true;BuildingHit=true;LastAimWasAssisted=true;
    }
    // Removal is the only thing rebuilt every frame; the placement plan is only cleared by the
    // branch that actually recomputes it, so the throttled branches (terrain sampling, aim miss)
    // keep the previous plan and its validity instead of dropping the click.
    Removal.Reset();
    if(BuildingHit)FillBrush(HitCell.Cell,Removal);
    if(SelectedPrefab()){Placement.Reset();bCanPlace=false;UpdatePrefabTarget(HasHit);UpdatePrefabPreview();return;}
    const double Now=GetWorld()->GetTimeSeconds();
    if(!HasHit)
    {
        // Momentary aim miss: keep the previous snapped ghost so it does not teleport away. Only in
        // snap mode - free placement (F) must follow the aim instead of holding a snapped plan.
        if(bSnapEnabled&&!Placement.IsEmpty()&&Now-LastSnapTime<.35)
        {bCanPlace=false;TargetMessage=TEXT("未命中可放置表面 · 瞄准 6 米内的地面或方块");UpdatePreview(Size);return;}
        Placement.Reset();bCanPlace=false;PlacementVolume={};HitCell={};
        PlacementOrigin=Start+Direction*250-Half;
        if(bSnapEnabled)PlacementOrigin=AVoxelBuildWorld::CellMin(AVoxelBuildWorld::ToCell(PlacementOrigin));
        FillBrush(FIntVector(Size.X/2,Size.Y/2,0),Placement);
        TargetMessage=TEXT("未命中可放置表面 · 瞄准 6 米内的地面或方块");
        if(FoundationPreview){FoundationPreview->ClearInstances();FoundationPreview->SetVisibility(false);}
    }
    else if(!BuildingHit)
    {
        // Terrain footprint sampling is expensive, so snap mode keeps the previous plan between
        // samples. Free placement must follow the aim continuously, so it is never throttled.
        if(bSnapEnabled&&Now<GroundSampleAt)return;
        GroundSampleAt=Now+1./20.;
        Placement.Reset();bCanPlace=false;PlacementVolume={};
        FString GroundingMessage;
        if(BuildWorld->ResolveGroundPlacement(Hit,Size,bSnapEnabled,PlacementOrigin,Placement,GroundingMessage))
        {
            ClippedPlayerCells=ClipLocalPlayerCells(Placement,PlacementOrigin);
            GrowUpPlan=false;
            ValidatePlacement();
            if(bCanPlace)TargetMessage=GroundingMessage+TEXT("\n")+TargetMessage;
        }
        else TargetMessage=GroundingMessage;
    }
    else if(bSnapEnabled)
    {
        Placement.Reset();bCanPlace=false;
        PlacementVolume=BuildingHit?HitCell.Volume:FGuid();PlacementOrigin=BuildWorld->VolumeOrigin(PlacementVolume);
        FIntVector Base=AVoxelBuildWorld::ToCell(Hit.ImpactPoint+Hit.ImpactNormal*.5-PlacementOrigin);
        bool bGrowUp=false;
        if(BuildingHit)
        {
            int32 Axis=0;const FVector N=Hit.ImpactNormal.GetAbs();if(N.Y>N.X)Axis=1;if(N.Z>N[Axis])Axis=2;
            Base=HitCell.Cell;
            if(Axis==2)Base.Z+=Hit.ImpactNormal.Z>0?1:-Size.Z;
            else Base[Axis]+=Hit.ImpactNormal[Axis]>0?1+Size[Axis]/2:-(Size[Axis]-Size[Axis]/2);
            // Looking up at a column's side means "put the next course on top of it". Once a wall is
            // taller than the player's eyes its top face is almost impossible to hit, which used to
            // make raising it impossible (2026-09-16 report: hit=0 above 2 m).
            if(Axis!=2&&Direction.Z>.05f)
            {
                const FIntVector Above=HitCell.Cell+FIntVector(0,0,1);
                if(BuildWorld->VolumeMaterialAt(HitCell.Volume,Above).IsNone()){Base=Above;bGrowUp=true;}
            }
        }
        FillBrush(Base,Placement);
        ClippedPlayerCells=ClipLocalPlayerCells(Placement,PlacementOrigin);
        ValidatePlacement();
        GrowUpPlan=bGrowUp;
        LastSnapTime=Now;
        // Aim cursor on the hit face plus corner markers on the plan. The plan's faces can be hidden
        // inside existing blocks when stacking upward; corners and the cursor stay readable.
        if(FoundationPreview)
        {
            FBox Plan(ForceInit);
            for(const FIntVector& Cell:Placement)
            {
                const FVector Min=PlacementOrigin+AVoxelBuildWorld::CellMin(Cell);
                Plan+=FBox(Min,Min+FVector(20));
            }
            const FVector CursorPoint=Hit.ImpactPoint+Hit.ImpactNormal*1.5f;
            const FVector PlanMin=Plan.IsValid?Plan.Min:FVector::ZeroVector;
            const FVector PlanMax=Plan.IsValid?Plan.Max:FVector::ZeroVector;
            // Rebuild only when the cursor or the plan box actually moved: the steady state must not
            // allocate or touch the instance buffer every frame.
            static FVector LastCursorPoint(TNumericLimits<double>::Max());
            static FVector LastCursorNormal=FVector::ZeroVector;
            static FVector LastPlanMin=FVector::ZeroVector,LastPlanMax=FVector::ZeroVector;
            const bool bCursorMoved=!LastCursorPoint.Equals(CursorPoint,.05f)||!LastCursorNormal.Equals(Hit.ImpactNormal,.01f);
            const bool bPlanMoved=!LastPlanMin.Equals(PlanMin,.05f)||!LastPlanMax.Equals(PlanMax,.05f);
            if(bCursorMoved||bPlanMoved)
            {
                LastCursorPoint=CursorPoint;LastCursorNormal=Hit.ImpactNormal;LastPlanMin=PlanMin;LastPlanMax=PlanMax;
                TArray<FTransform> Marks;
                Marks.Emplace(FRotationMatrix::MakeFromZ(Hit.ImpactNormal).ToQuat(),CursorPoint,FVector(.09f,.09f,.012f));
                if(Plan.IsValid)
                {
                    const FVector Extent=Plan.GetExtent()*2;
                    for(int32 Index=0;Index<8;++Index)
                    {
                        const FVector Corner(Plan.Min.X+((Index&1)?Extent.X:0),Plan.Min.Y+((Index&2)?Extent.Y:0),
                            Plan.Min.Z+((Index&4)?Extent.Z:0));
                        Marks.Emplace(FQuat::Identity,Corner,FVector(.03f,.03f,.03f));
                    }
                }
                if(FoundationPreview->GetInstanceCount()==Marks.Num())
                {
                    FoundationPreview->BatchUpdateInstancesTransforms(0,Marks,true,true,true);
                }
                else
                {
                    FoundationPreview->ClearInstances();FoundationPreview->AddInstances(Marks,false,true,false);
                }
                FoundationPreview->SetHiddenInGame(false);FoundationPreview->SetVisibility(true);
            }
        }
        // Gold edges on every existing block that touches the plan (blink is driven in TickComponent).
        if(auto* Edges=FindAimEdge(PreviewActor))
        {
            // A pure gold emissive reads better than the placement material's world grid, whose thin
            // bars sample mostly dark pattern. Swap lazily so a live world picks it up without re-entry.
            static bool bGoldChecked=false;
            static UMaterialInterface* GoldMaterial=nullptr;
            static UMaterialInstanceDynamic* GoldMID=nullptr;
            static bool bAimEdgeLogged=false;
            // Retry until the gold material loads: a failed first attempt must never latch, and the
            // component is re-assigned whenever it is not on that MID (self-healing after edits).
            if(!GoldMaterial)GoldMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Building/Voxels/Rounded/M_VoxelAimEdge.M_VoxelAimEdge"));
            if(GoldMaterial&&(!AimEdgeMaterial||AimEdgeMaterial!=GoldMID))
            {
                AimEdgeMaterial=UMaterialInstanceDynamic::Create(GoldMaterial,this);
                GoldMID=AimEdgeMaterial;bAimEdgeGold=true;
                Edges->SetMaterial(0,AimEdgeMaterial);
            }
            if(!bAimEdgeLogged)
            {
                bAimEdgeLogged=true;
                UE_LOG(LogTemp,Warning,TEXT("VOXEL_AIMEDGE gold=%d material=%s"),
                    GoldMaterial?1:0,GoldMaterial?*GoldMaterial->GetPathName():TEXT("NOT FOUND (edges keep the preview material)"));
            }
            // Cheap signature pass (no allocation): only rebuild the instance buffer when the set of
            // touching blocks actually changes, so the steady state costs a handful of map lookups.
            static const FIntVector Directions[6]={{1,0,0},{-1,0,0},{0,1,0},{0,-1,0},{0,0,1},{0,0,-1}};
            uint32 Signature=0;int32 Count=0;
            for(const FIntVector& Cell:Placement)
            {
                for(const FIntVector& Dir:Directions)
                {
                    const FIntVector Neighbour=Cell+Dir;
                    if(BuildWorld->VolumeMaterialAt(HitCell.Volume,Neighbour).IsNone())continue;
                    Signature+=GetTypeHash(Neighbour);++Count;
                }
            }
            if(Signature!=AimEdgeSignature||Count!=AimEdgeCount||AimEdgeCell!=HitCell.Cell)
            {
                AimEdgeSignature=Signature;AimEdgeCount=Count;AimEdgeCell=HitCell.Cell;
                constexpr float Bar=.012f,Span=.21f;
                TArray<FTransform> Bars;
                auto Open=[&](FIntVector Cell,FIntVector Offset)
                {return BuildWorld->VolumeMaterialAt(HitCell.Volume,Cell+Offset).IsNone();};
                // One gold wireframe per touching block, drawing only edges that border open space:
                // edges buried against a neighbour sit inside that cell and would never be visible.
                auto AddBlockEdges=[&](FIntVector Cell)
                {
                    const FVector CellMin=BuildWorld->VolumeOrigin(HitCell.Volume)+AVoxelBuildWorld::CellMin(Cell);
                    const FVector Low=CellMin-FVector(.5f),High=CellMin+FVector(20.5f);
                    const FVector Center=(Low+High)*.5f;
                    for(int32 I=0;I<4;++I)
                    {
                        const int32 Sy=(I&1)?1:-1,Sz=(I&2)?1:-1;
                        if(!Open(Cell,FIntVector(0,Sy,0))&&!Open(Cell,FIntVector(0,0,Sz)))continue;
                        Bars.Emplace(FQuat::Identity,FVector(Center.X,(I&1)?High.Y:Low.Y,(I&2)?High.Z:Low.Z),FVector(Span,Bar,Bar));
                    }
                    for(int32 I=0;I<4;++I)
                    {
                        const int32 Sx=(I&1)?1:-1,Sz=(I&2)?1:-1;
                        if(!Open(Cell,FIntVector(Sx,0,0))&&!Open(Cell,FIntVector(0,0,Sz)))continue;
                        Bars.Emplace(FQuat::Identity,FVector((I&1)?High.X:Low.X,Center.Y,(I&2)?High.Z:Low.Z),FVector(Bar,Span,Bar));
                    }
                    for(int32 I=0;I<4;++I)
                    {
                        const int32 Sx=(I&1)?1:-1,Sy=(I&2)?1:-1;
                        if(!Open(Cell,FIntVector(Sx,0,0))&&!Open(Cell,FIntVector(0,Sy,0)))continue;
                        Bars.Emplace(FQuat::Identity,FVector((I&1)?High.X:Low.X,(I&2)?High.Y:Low.Y,Center.Z),FVector(Bar,Bar,Span));
                    }
                };
                for(const FIntVector& Cell:Placement)
                {
                    for(const FIntVector& Dir:Directions)
                    {
                        const FIntVector Neighbour=Cell+Dir;
                        if(BuildWorld->VolumeMaterialAt(HitCell.Volume,Neighbour).IsNone())continue;
                        AddBlockEdges(Neighbour);
                    }
                }
                if(Bars.IsEmpty())Edges->ClearInstances();
                else if(Edges->GetInstanceCount()==Bars.Num())Edges->BatchUpdateInstancesTransforms(0,Bars,true,true,true);
                else{Edges->ClearInstances();Edges->AddInstances(Bars,false,true,false);}
            }
            // Visibility comes from the cached touching count, outside the rebuild test, so a frame
            // that keeps the same neighbours still lights the outline up instead of leaving it hidden.
            Edges->SetHiddenInGame(false);Edges->SetVisibility(Count>0);
        }
    }
    else
    {
        Placement.Reset();bCanPlace=false;
        // Continuous world position: no floor/round/quantization in free mode.
        PlacementOrigin=Hit.ImpactPoint+Hit.ImpactNormal*FVector::DotProduct(Hit.ImpactNormal.GetAbs(),Half)-Half;
        FillBrush(FIntVector(Size.X/2,Size.Y/2,0),Placement);
        ClippedPlayerCells=ClipLocalPlayerCells(Placement,PlacementOrigin);
        GrowUpPlan=false;
        ValidatePlacement();
        if(FoundationPreview){FoundationPreview->ClearInstances();FoundationPreview->SetVisibility(false);}
    }
    UpdatePreview(Size);

    // TEMPORARY diagnostics for the 2026-09-16 "cannot build above 2 m" report: one line whenever
    // the aim or plan state changes, so a single reproduction in game tells where it stops.
    static FString LastAimSignature;
    const FString AimSignature=FString::Printf(TEXT("%d|%d|%d,%d,%d|%d|%d|%d|%d|%d"),HasHit?1:0,BuildingHit?1:0,
        HitCell.Cell.X,HitCell.Cell.Y,HitCell.Cell.Z,Placement.Num(),bCanPlace?1:0,GrowUpPlan?1:0,LastAimWasAssisted?1:0,
        bSnapEnabled?1:0);
    if(AimSignature!=LastAimSignature)
    {
        LastAimSignature=AimSignature;
        static double LastAimLog=-10.;
        if(Now-LastAimLog<.5)return;   // keep the diagnostic readable now that it runs per frame
        LastAimLog=Now;
        UE_LOG(LogTemp,Warning,TEXT("VOXEL_AIM hit=%d building=%d cell=%d,%d,%d plan=%d valid=%d grow=%d assist=%d snap=%d origin=%.1f,%.1f,%.1f message=%s"),
            HasHit?1:0,BuildingHit?1:0,HitCell.Cell.X,HitCell.Cell.Y,HitCell.Cell.Z,Placement.Num(),bCanPlace?1:0,GrowUpPlan?1:0,
            LastAimWasAssisted?1:0,bSnapEnabled?1:0,PlacementOrigin.X,PlacementOrigin.Y,PlacementOrigin.Z,*TargetMessage);
    }
}

void UVoxelBuildComponent::UpdatePrefabTarget(bool bHit)
{
    AimedPrefab=nullptr;bPrefabAimHit=bHit;bPrefabValid=false;bCanPlace=false;PrefabMessage=TEXT("");
    const FVoxelBuildPrefab* Prefab=SelectedPrefab();
    if(!Prefab||!BuildWorld){TargetMessage=TEXT("构件定义已失效");PrefabMessage=TargetMessage;return;}
    if(bHit)AimedPrefab=Cast<AVoxelBuildPrefabActor>(Hit.GetActor());
    const FIntVector Footprint=AVoxelBuildPrefabActor::RotatedFootprint(Prefab->Footprint,ComponentYaw);
    // Removing voxels stays available while a component is selected: right click the aimed block.
    if(BuildWorld->ResolveHit(Hit,HitCell))FillBrush(HitCell.Cell,Removal);
    if(!bHit)
    {
        PrefabCell=AVoxelBuildWorld::ToCell(Hit.ImpactPoint);
        PrefabMessage=TEXT("未命中可放置表面 · 瞄准 6 米内的地面或结构");
        TargetMessage=PrefabMessage;
        return;
    }
    // The 20 cm footprint is centred on the aimed column and always lands on lattice multiples.
    const FVector Base=Hit.ImpactPoint+Hit.ImpactNormal*.5;
    FIntVector Cell=AVoxelBuildWorld::ToCell(Base);
    Cell.X-=Footprint.X/2;Cell.Y-=Footprint.Y/2;
    PrefabCell=Cell;
    bPrefabValid=BuildWorld->CanPlacePrefab(Prefab->Id,Cell,ComponentYaw,PrefabMessage);
    bCanPlace=bPrefabValid;TargetMessage=PrefabMessage;
}

void UVoxelBuildComponent::UpdatePrefabPreview()
{
    if(!Preview)return;
    if(FoundationPreview){FoundationPreview->ClearInstances();FoundationPreview->SetVisibility(false);}
    const FVoxelBuildPrefab* Prefab=SelectedPrefab();
    UStaticMesh* Mesh=Prefab?Prefab->Mesh.LoadSynchronous():nullptr;
    if(!Prefab||!Mesh||!bPrefabAimHit){Preview->SetVisibility(false);return;}
    Preview->SetStaticMesh(Mesh);
    const FTransform Transform=AVoxelBuildPrefabActor::ComputeTransform(*Prefab,Mesh,PrefabCell,ComponentYaw);
    Preview->SetWorldLocationAndRotation(Transform.GetLocation(),Transform.GetRotation());
    Preview->SetWorldScale3D(FVector(1));
    if(PreviewMID)
    {
        PreviewMID->SetVectorParameterValue(TEXT("Tint"),bPrefabValid?FLinearColor(.06f,1.f,.15f):FLinearColor(1.f,.035f,.02f));
        const FVector Min=FVector(PrefabCell)*20.;
        PreviewMID->SetVectorParameterValue(TEXT("PreviewOrigin"),FLinearColor(Min.X,Min.Y,Min.Z));
    }
    Preview->SetHiddenInGame(false);Preview->SetVisibility(true);
}

void UVoxelBuildComponent::UpdatePreview(FIntVector Size)
{
    // Component previews switch the ghost mesh; the voxel brush always uses the 20 cm cube.
    if(Preview&&GhostMesh&&Preview->GetStaticMesh()!=GhostMesh)Preview->SetStaticMesh(GhostMesh);
    if(Preview&&!Placement.IsEmpty())
    {
        const FVector Half=FVector(Size)*10;
        const FVector Min=PlacementOrigin+AVoxelBuildWorld::CellMin(Placement[0]);
        Preview->SetWorldLocation(Min+Half);
        // ~1.2 cm larger on every side (cube is 100 cm): the ghost stays visible when the next cell
        // touches or sits inside existing blocks, which is exactly the upward-building case.
        Preview->SetWorldScale3D(FVector(Size)*.2+FVector(.024));
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

int32 UVoxelBuildComponent::ClipLocalPlayerCells(TArray<FIntVector>& Cells,FVector Origin) const
{
    // The world refuses any cell that intersects a character, and one refused cell rejects the whole
    // brush. Standing on your own wall therefore used to block the next 5-cell-high wall brush
    // entirely. Drop only the cells that really contain the local player; the rest is still built.
    auto* PC=Cast<APlayerController>(GetOwner());
    APawn* Pawn=PC?PC->GetPawn():nullptr;
    UCapsuleComponent* Capsule=Pawn?Pawn->FindComponentByClass<UCapsuleComponent>():nullptr;
    if(!Capsule||!Capsule->IsCollisionEnabled()||Cells.IsEmpty())return 0;
    // Runs every frame now, so bail out unless the plan's box actually overlaps the body box:
    // building away from yourself is the common case and must stay allocation free.
    FBox PlanBounds(ForceInit);
    for(const FIntVector& Cell:Cells)
    {
        const FVector Min=Origin+AVoxelBuildWorld::CellMin(Cell);
        PlanBounds+=FBox(Min,Min+FVector(20));
    }
    if(!PlanBounds.Intersect(Capsule->Bounds.GetBox()))return 0;
    const float Radius=Capsule->GetScaledCapsuleRadius();
    const float Half=Capsule->GetScaledCapsuleHalfHeight();
    const FVector Up=Capsule->GetUpVector();
    const FVector A=Capsule->GetComponentLocation()+Up*FMath::Max(0.f,Half-Radius);
    const FVector B=Capsule->GetComponentLocation()-Up*FMath::Max(0.f,Half-Radius);
    const TArray<FIntVector> Original=Cells;
    const int32 Removed=Cells.RemoveAll([&](const FIntVector& Cell)
    {
        const FVector Min=Origin+AVoxelBuildWorld::CellMin(Cell);
        const FBox Box(Min+FVector(.25),Min+FVector(19.75));
        const FVector Nearest=FMath::ClosestPointOnSegment(Box.GetCenter(),A,B);
        return FVector::DistSquared(Box.GetClosestPointTo(Nearest),Nearest)<double(Radius)*Radius;
    });
    if(Cells.IsEmpty())
    {
        // Nothing left to build: keep the original plan so the normal "位置被角色占用" message shows.
        Cells=Original;return 0;
    }
    return Removed;
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
        // TEMPORARY diagnostics for the 2026-09-16 "cannot build above 2 m" report.
        if(!bCheckedValid&&!LastPreviewReject.Equals(CheckedMessage))
        {
            LastPreviewReject=CheckedMessage;
            UE_LOG(LogTemp,Warning,TEXT("VOXEL_REJECT stage=preview origin=%.1f,%.1f,%.1f snap=%d cells=%d message=%s"),
                PlacementOrigin.X,PlacementOrigin.Y,PlacementOrigin.Z,bPlacementSnap?1:0,Placement.Num(),*CheckedMessage);
        }
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
    const FKey Key=Event.Key;const bool Pressed=Event.Event==IE_Pressed;
    // Other menus still end building; our own drawer keeps the cursor and stays open.
    if(bMenuOpen){if(bActive)SetBuildMode(false);return false;}
    if(!bPanelOpen&&(PC->bShowMouseCursor||PC->IsMoveInputIgnored()||PC->IsLookInputIgnored()))
    {if(bActive)SetBuildMode(false);return false;}
    // A key the focused drawer widget already handled must not run twice in the same frame.
    const bool bDrawerHandled=GFrameCounter==DrawerKeyFrame;
    if(Key==EKeys::B)
    {
        if(Pressed&&!bDrawerHandled)
        {
            if(!bActive)SetBuildMode(true);          // enter building, drawer open
            else if(bPanelOpen)SetBuildMode(false);  // second B in the drawer: leave building
            else SetPanelOpen(true);                 // back to the drawer from placing
        }
        return true;
    }
    if(!bActive)return false;
    if(Key==EKeys::Escape)
    {
        if(Pressed&&!bDrawerHandled){if(bPanelOpen)SetPanelOpen(false);else SetBuildMode(false);}
        return true;
    }
    if(Pressed&&(Key==EKeys::Tab||Key==EKeys::K||Key==EKeys::J||Key==EKeys::F6||Key==EKeys::LeftAlt))
    {SetBuildMode(false);return false;}
    if(Pressed&&HandlePanelKey(Key))return true;
    // Placement commands belong to the aiming state; the drawer does not move or build.
    if(bPanelOpen)return false;
    if(Key==EKeys::MouseScrollUp||Key==EKeys::MouseScrollDown)
    {if(Pressed){Brush=(Brush+(Key==EKeys::MouseScrollUp?1:2))%3;FeedbackTime=0;TargetUpdateAt=0;}return true;}
    if(Key==EKeys::R)
    {
        // Components turn in quarter turns; the voxel wall brush keeps its single toggle.
        if(Pressed){if(SelectedPrefab())ComponentYaw=(ComponentYaw+1)%4;else bRotate=!bRotate;FeedbackTime=0;TargetUpdateAt=0;}
        return true;
    }
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
                if(SelectedPrefab())PlacePrefab();
                else if(bCanPlace)
                {
                    if(bPlacementSnap)bFeedbackValid=BuildWorld->EditVolumeCells(PlacementVolume,Placement,PlacementMaterial);
                    else bFeedbackValid=BuildWorld->PlaceFree(PlacementOrigin,Placement,PlacementMaterial);
                    Feedback=BuildWorld->ResultMessage();
                }
                else {bFeedbackValid=false;Feedback=TargetMessage;}
            }
            else if(auto* Piece=Cast<AVoxelBuildPrefabActor>(AimedPrefab.Get()))
            {bFeedbackValid=BuildWorld->RemovePrefab(Piece);Feedback=BuildWorld->ResultMessage();}
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
    if(Key==EKeys::G||Key==EKeys::Three||Key==EKeys::Four||Key==EKeys::Five||Key==EKeys::E)return true;
    return false;
}

void UVoxelBuildComponent::UpdateWidget()
{
    if(!Widget||!Palette||!BuildWorld)return;
    Widget->SetSelection(SelectedMaterial,SelectedComponent);
    if(bPanelOpen)
    {
        Widget->ShowState(TEXT("选择要建造的对象"),TEXT("点击卡片或按 1-9 · 选中后自动回到建造"),
            TEXT("面板已接管光标 · 游戏操作暂停 · Esc 关闭后继续建造"),true,bSnapEnabled);
        return;
    }
    const FString ClipNote=ClippedPlayerCells>0?FString::Printf(TEXT(" · 已跳过 %d 格（角色所在位置）"),ClippedPlayerCells):FString();
    const FString Message=(FeedbackTime>0?Feedback:(SelectedPrefab()?PrefabMessage:TargetMessage))+ClipNote+TEXT("\n")+BuildWorld->StructureStatus();
    if(const FVoxelBuildPrefab* Prefab=SelectedPrefab())
    {
        const FIntVector Footprint=AVoxelBuildPrefabActor::RotatedFootprint(Prefab->Footprint,ComponentYaw);
        Widget->ShowState(FString::Printf(TEXT("%s · 构件 %d 件 · 体素 %d 格"),*Prefab->DisplayName.ToString(),BuildWorld->PrefabCount(),BuildWorld->BlockCount()),
            FString::Printf(TEXT("构件 · %d × %d × %d cm · %d°"),Footprint.X*20,Footprint.Y*20,Footprint.Z*20,ComponentYaw*90),
            Message,FeedbackTime>0?bFeedbackValid:bPrefabValid,bSnapEnabled);
        return;
    }
    const auto* Entry=Palette->Find(SelectedMaterial);const FIntVector Size=BrushSize()*20;
    const FString Name=Entry?Entry->DisplayName.ToString():SelectedMaterial.ToString();
    const TCHAR* Shape=Brush==0?TEXT("单格"):Brush==1?TEXT("地板"):TEXT("墙面");
    // Where the plan actually lands: layer index and cell, so upward building is unambiguous.
    const FIntVector FirstCell=Placement.IsEmpty()?FIntVector::ZeroValue:Placement[0];
    const FString Where=Placement.IsEmpty()?FString():
        FString::Printf(TEXT(" · 第 %d 层 格(%d,%d,%d)"),FirstCell.Z+1,FirstCell.X,FirstCell.Y,FirstCell.Z);
    Widget->ShowState(FString::Printf(TEXT("%s · 已建造 %d 格"),*Name,BuildWorld->BlockCount()),
        FString::Printf(TEXT("%s · %d × %d × %d cm%s"),Shape,Size.X,Size.Y,Size.Z,*Where),
        Message,FeedbackTime>0?bFeedbackValid:bCanPlace,bSnapEnabled);
}

void UVoxelBuildComponent::PlacePrefab()
{
    const FVoxelBuildPrefab* Prefab=SelectedPrefab();
    if(!Prefab){bFeedbackValid=false;Feedback=TEXT("请先选择构件");FeedbackTime=2;return;}
    if(!bPrefabValid){bFeedbackValid=false;Feedback=PrefabMessage;FeedbackTime=2;return;}
    bFeedbackValid=BuildWorld->PlacePrefab(Prefab->Id,PrefabCell,ComponentYaw);
    Feedback=BuildWorld->ResultMessage();FeedbackTime=2;
    PlacementCheckAt=0;TargetUpdateAt=0;
}

void UVoxelBuildComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(!BuildWorld&&!bInitializeFailed){InitializeCountdown-=Delta;if(InitializeCountdown<=0){InitializeCountdown=.5f;TryInitializeWorld();}}
    if(!bActive)
    {
        // Safety net: no exit path (drawer, other menu, Live Coding reload, level change) may leave
        // the gold outline behind. Costs one visibility query per frame while not building.
        if(AimEdgeComponent&&(AimEdgeComponent->IsVisible()||AimEdgeComponent->GetInstanceCount()>0))
            ClearAimHighlight(PreviewActor);
        return;
    }
    auto* PC=Cast<APlayerController>(GetOwner());
    if(!PC||!PC->GetPawn()){SetBuildMode(false);return;}
    // The drawer holds the cursor itself; only a foreign cursor/no-input state ends building.
    if(!bPanelOpen&&(PC->bShowMouseCursor||PC->IsMoveInputIgnored()||PC->IsLookInputIgnored()))
    {SetBuildMode(false);return;}
    FeedbackTime=FMath::Max(0.f,FeedbackTime-Delta);
    if(bPanelOpen)
    {
        if(Preview)Preview->SetVisibility(false);
        if(FoundationPreview)FoundationPreview->SetVisibility(false);
        UpdateWidget();
        return;
    }
    // Bound terrain probes and draft connectivity work independently of FPS.
    // Keep the displayed plan fixed between updates, including its validity.
    // The aim follows the camera every frame; only the expensive branches inside UpdateTarget are
    // throttled, so the ghost no longer lags behind the crosshair.
    UpdateTarget();
    // Gold blink on the snapped neighbour: one vector parameter per frame, nothing else.
    if(AimEdgeMaterial&&AimEdgeComponent&&AimEdgeComponent->IsVisible())
    {
        const float Pulse=.5f+.5f*FMath::Sin(float(GetWorld()->GetTimeSeconds())*5.f);
        // Emissive is around 1.0 in daylight terms, which reads as dull grey against a bright sky;
        // push it into HDR range so the gold stays gold and glows.
        AimEdgeMaterial->SetVectorParameterValue(TEXT("Tint"),FLinearColor(1.f,.74f,.2f)*(1.2f+2.4f*Pulse));
    }
    UpdateWidget();
}

void UVoxelBuildComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    SetBuildMode(false);
    if(PreviewActor)PreviewActor->Destroy();if(Widget)Widget->RemoveFromParent();
    // The preview Actor owns the outline component, so both caches must not outlive it.
    AimEdgeComponent=nullptr;AimEdgeMaterial=nullptr;
    Super::EndPlay(Reason);
}
