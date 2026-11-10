#include "EnhancementWorldView.h"
#include "EnhancementRitualEffect.h"
#include "AlchemyInteractionAssets.h"
#include "Components/MeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Materials/MaterialInterface.h"
#include "VoxelBuildPrefabActor.h"
#include "VoxelBuildWorld.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "WorkstationViewRestore.h"
#include "../UI/ColdSteelPickup.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "Camera/CameraComponent.h"
#include "Camera/CameraTypes.h"
#include "../UI/ColdSteelEnhancementLayoutMetrics.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"

namespace
{
    constexpr float PlacementHeight=28.f;
    constexpr float PlacementFallSeconds=.28f;
    constexpr float PlacementBounceSeconds=.18f;
    constexpr float PlacementSettleSeconds=.08f;
    constexpr float PlacementDuration=PlacementFallSeconds+PlacementBounceSeconds+PlacementSettleSeconds;
    constexpr float PlacementLoadLimit=2.f;
}

AEnhancementWorldView::AEnhancementWorldView()
{
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.bStartWithTickEnabled=false;
    PrimaryActorTick.TickInterval=.1f;SetReplicates(false);
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Camera=CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
    Camera->SetupAttachment(RootComponent);Camera->FieldOfView=55.f;
}
bool AEnhancementWorldView::Begin(APlayerController* Controller,AVoxelBuildPrefabActor* Bench)
{
    End();
    if(!Controller||!Controller->IsLocalController()||!Controller->GetPawn()||
        !ColdSteelWorldInteraction::IsEnhancementBench(Bench))return false;
    const auto* Body=Bench->Body();
    if(!Body||!Body->GetStaticMesh()||!Body->DoesSocketExist(TEXT("ArcaneItem"))||!Body->DoesSocketExist(TEXT("ArcaneCamera")))return false;
    Player=Controller;Station=Bench;WorkingPawn=Controller->GetPawn();SetOwner(Controller);
    bEntered=true;SessionCheckElapsed=0.f;
    if(!IsSessionValid()){bEntered=false;return false;}
    PreviousView=Controller->GetViewTarget();
    const auto OutlinePath=AlchemyInteraction::Asset(TEXT("M_AlchemyHoverOutline"));
    OutlineLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(OutlinePath,FStreamableDelegate::CreateWeakLambda(this,[this,OutlinePath]()
    {
        if(bEntered)if(auto* Material=Cast<UMaterialInterface>(OutlinePath.ResolveObject()))
            Camera->AddOrUpdateBlendable(Material,1.f);
    }));
    FActorSpawnParameters EffectSpawn;EffectSpawn.Owner=Controller;EffectSpawn.ObjectFlags=RF_Transient;
    EffectSpawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    RitualEffect=GetWorld()->SpawnActor<AEnhancementRitualEffect>(FVector::ZeroVector,FRotator::ZeroRotator,EffectSpawn);
    ColdSteelWorkstationView::BeginIdle(this,WorkingPawn.Get());
    if(!Controller->HiddenActors.Contains(WorkingPawn.Get())){Controller->HiddenActors.Add(WorkingPawn.Get());bHidPawn=true;}
    UpdatePose();SetActorTickEnabled(true);Controller->SetViewTargetWithBlend(this,.3f,VTBlend_Cubic);
    return true;
}
bool AEnhancementWorldView::IsSessionValid() const
{
    if(!bEntered||!Player.IsValid()||!WorkingPawn.IsValid()||Player->GetPawn()!=WorkingPawn.Get()||
        !Station.IsValid()||Station->IsActorBeingDestroyed()||!ColdSteelWorldInteraction::IsEnhancementBench(Station.Get()))return false;
    // Reach is measured from the possessed pawn, never the tabletop camera.
    const auto* Building=Cast<AVoxelBuildWorld>(Station->GetOwner());
    const auto* Health=WorkingPawn->FindComponentByClass<UFPSCombatHealthComponent>();
    if(!Building||Building->PrefabActorAt(Station->AnchorCell())!=Station.Get()||!Health||Health->IsDead())return false;
    const auto* Body=Station->Body();
    if(!Body||!Body->GetStaticMesh()||!Body->DoesSocketExist(TEXT("ArcaneItem"))||!Body->DoesSocketExist(TEXT("ArcaneCamera")))return false;
    const FVector ItemSocket=Body->GetSocketLocation(TEXT("ArcaneItem")),CameraSocket=Body->GetSocketLocation(TEXT("ArcaneCamera"));
    if(ItemSocket.ContainsNaN()||CameraSocket.ContainsNaN()||FVector::DistSquared(ItemSocket,CameraSocket)<1.f)return false;
    const FVector Eye=WorkingPawn->GetPawnViewLocation(),Near=Body->Bounds.GetBox().GetClosestPointTo(Eye);
    if(FVector::DistSquared(Eye,Near)>FMath::Square(300.f))return false;
    FHitResult Hit;FCollisionQueryParams Params(SCENE_QUERY_STAT(EnhancementReach),false,WorkingPawn.Get());
    return !GetWorld()->LineTraceSingleByChannel(Hit,Eye,Near,ECC_Visibility,Params)||Hit.GetActor()==Station.Get();
}
bool AEnhancementWorldView::HasActiveSession(const APlayerController* Controller)
{
    if(!Controller||!Controller->GetWorld())return false;
    for(TActorIterator<AEnhancementWorldView> It(Controller->GetWorld());It;++It)
        if(It->Player.Get()==Controller&&It->IsSessionValid())return true;
    return false;
}
void AEnhancementWorldView::UpdatePose()
{
    if(!Station.IsValid())return;
    const auto* Body=Station->Body();
    if(!Body||!Body->DoesSocketExist(TEXT("ArcaneItem"))||!Body->DoesSocketExist(TEXT("ArcaneCamera")))return;
    SetActorTransform(Body->GetComponentTransform());
    // The importer must author these sockets after resolving the actual UE import axes.
    // Source/FBX-node coordinates are not interchangeable with imported mesh space.
    const FVector Focus=Body->GetSocketTransform(TEXT("ArcaneItem"),RTS_Component).GetLocation();
    const FVector SocketEye=Body->GetSocketTransform(TEXT("ArcaneCamera"),RTS_Component).GetLocation();
    FVector EyeDirection=(SocketEye-Focus).GetSafeNormal();
    // Preserve the socket-authored front side, with enough elevation to read the tabletop.
    const FVector Horizontal=FVector(EyeDirection.X,EyeDirection.Y,0).GetSafeNormal();
    if(!Horizontal.IsNearlyZero())EyeDirection=(Horizontal+FVector::UpVector*.78f).GetSafeNormal();
    int32 ViewWidth=1920,ViewHeight=1080;if(Player.IsValid())Player->GetViewportSize(ViewWidth,ViewHeight);
    const auto Layout=FColdSteelEnhancementLayoutMetrics::ForViewport(FVector2D(ViewWidth,ViewHeight));
    const float W=FMath::Max(1.f,float(ViewWidth)),H=FMath::Max(1.f,float(ViewHeight));
    // Fit the real rune surface plus a lifted weapon into only the unobstructed scene.
    // Widen before pulling back so the camera does not retreat through nearby walls.
    const float HorizontalFit=84.f*W/FMath::Max(1.f,float(Layout.SceneSize.X)*.84f);
    const float VerticalFit=66.f*W/FMath::Max(1.f,float(Layout.SceneSize.Y)*.78f);
    const float Fit=FMath::Max(HorizontalFit,VerticalFit);
    const float Distance=FMath::Max(float(FVector::Distance(SocketEye,Focus)),FMath::Max(165.f,Fit/FMath::Tan(FMath::DegreesToRadians(62.f))));
    const FVector Eye=Focus+EyeDirection*Distance;
    Camera->FieldOfView=FMath::Clamp(FMath::RadiansToDegrees(2.f*FMath::Atan(Fit/Distance)),50.f,124.f);
    Camera->bConstrainAspectRatio=false;Camera->bOverrideAspectRatioAxisConstraint=true;
    Camera->AspectRatioAxisConstraint=EAspectRatioAxisConstraint::AspectRatio_MaintainXFOV;
    Camera->SetRelativeLocationAndRotation(Eye,(Focus-Eye).Rotation());
    UpdateDisplayPose();
}
void AEnhancementWorldView::UpdateDisplayPose()
{
    if(!Station.IsValid()||!Station->Body()||!Station->Body()->DoesSocketExist(TEXT("ArcaneItem")))return;
    const FVector Focus=Station->Body()->GetSocketTransform(TEXT("ArcaneItem"),RTS_Component).GetLocation();
    if(IsValid(Display))
    {
        const FVector Extent=Display->Body->GetUnscaledBoxExtent();
        int32 Long=0,Thin=0;
        for(int32 Axis=1;Axis<3;++Axis){if(Extent[Axis]>Extent[Long])Long=Axis;if(Extent[Axis]<Extent[Thin])Thin=Axis;}
        if(Long==Thin)Thin=(Long+1)%3;
        FVector Along=FVector::ZeroVector,Normal=FVector::ZeroVector;Along[Long]=1;Normal[Thin]=1;
        const FQuat Rotation=FRotationMatrix::MakeFromXZ(Along,Normal).ToQuat().Inverse();
        const float Scale=FMath::Min(1.f,120.f/FMath::Max(1.f,float(Extent[Long]*2)));
        // ArcaneItem is the rune surface. Lift by the shown weapon thickness so it cannot sink into the stone.
        const FVector DisplayCenter=Focus+FVector(0,0,Extent[Thin]*Scale+2.f+PlacementOffset());
        Display->SetActorTransform(FTransform(Rotation,DisplayCenter,FVector(Scale))*GetActorTransform());
    }
}
void AEnhancementWorldView::CalcCamera(float DeltaTime,FMinimalViewInfo& OutResult)
{
    Camera->GetCameraView(DeltaTime,OutResult);
    int32 W=1920,H=1080;if(Player.IsValid())Player->GetViewportSize(W,H);
    if(W<=0||H<=0)return;
    const auto Layout=FColdSteelEnhancementLayoutMetrics::ForViewport(FVector2D(W,H));
    const FVector2D Target=Layout.ScenePosition+Layout.SceneSize*FVector2D(.5f,Layout.bStacked?.56f:.60f);
    // Off-axis projection moves the optical center without turning away from the weapon.
    OutResult.OffCenterProjectionOffset=FVector2D(1.f-2.f*Target.X/W,2.f*Target.Y/H-1.f);
}

bool AEnhancementWorldView::SetItem(const FString& Id)
{
    if(!IsSessionValid())return false;
    if(Id.IsEmpty())
    {StopPlacement();if(RitualEffect)RitualEffect->Stop();if(Display){Display->Destroy();Display=nullptr;}SelectedId.Reset();SelectedData.Reset();return true;}
    const auto* Item=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>()->BenchItem();
    if(!Item||Item->InstanceId!=Id)return false;
    if(SelectedId==Id&&SelectedData==Item->Data&&IsValid(Display))return true;
    // Same-item data updates may rebuild geometry, but never restart its fall.
    if(SelectedId!=Id)StopPlacement();
    if(RitualEffect)RitualEffect->Stop();
    if(Display){Display->Destroy();Display=nullptr;}
    SelectedId=Id;SelectedData=Item->Data;
    FActorSpawnParameters Spawn;Spawn.Owner=Player.Get();Spawn.ObjectFlags=RF_Transient;
    Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    Display=GetWorld()->SpawnActor<AColdSteelPickup>(FVector::ZeroVector,FRotator::ZeroRotator,Spawn);
    if(!Display)return false;
    if(!Display->InitializeWorkbenchDisplay(*Item)){Display->Destroy();Display=nullptr;return false;}
    if(bPlacementWaiting)Display->SetActorHiddenInGame(true);
    UpdatePose();ApplyItemHover();return true;
}
void AEnhancementWorldView::Tick(float Delta)
{
    Super::Tick(Delta);
    // Keep reach/line-trace and camera work at the existing 10 Hz budget.
    // Only the short cosmetic flight needs a per-frame transform update.
    SessionCheckElapsed+=Delta;
    if(SessionCheckElapsed>=.1f)
    {
        SessionCheckElapsed=0.f;
        if(!IsSessionValid()){End();return;}
        UpdatePose();
        if(bItemHovered)ApplyItemHover();
    }
    if(bPlacementWaiting)
    {
        PlacementWait+=Delta;
        if(!IsValid(Display)){StopPlacement();return;}
        if(Display->IsWorkbenchDisplayReady())
        {
            bPlacementWaiting=false;PlacementTime=0.f;PlacementStartedAt=GetWorld()->GetTimeSeconds();
            Display->SetActorHiddenInGame(false);SetActorTickInterval(0.f);
            UpdateDisplayPose();ApplyItemHover();
        }
        else if(PlacementWait>=PlacementLoadLimit){StopPlacement();UpdateDisplayPose();}
        return;
    }
    if(PlacementTime>=0.f)
    {
        if(!IsValid(Display)){StopPlacement();return;}
        PlacementTime=float(GetWorld()->GetTimeSeconds()-PlacementStartedAt);
        if(PlacementTime>=PlacementDuration)StopPlacement();
        UpdateDisplayPose();
    }
}
void AEnhancementWorldView::End()
{
    StopPlacement();SetActorTickEnabled(false);bItemHovered=false;
    if(OutlineLoad){OutlineLoad->CancelHandle();OutlineLoad.Reset();}
    Camera->PostProcessSettings.WeightedBlendables.Array.Reset();
    if(RitualEffect){RitualEffect->Destroy();RitualEffect=nullptr;}
    if(Display){Display->Destroy();Display=nullptr;}SelectedId.Reset();SelectedData.Reset();
    if(bEntered)
    {
        if(bHidPawn&&Player.IsValid())Player->HiddenActors.Remove(WorkingPawn.Get());
        ColdSteelWorkstationView::Restore(Player.Get(),this,WorkingPawn.Get(),PreviousView.Get(),.25f);
    }
    bEntered=false;bHidPawn=false;Station.Reset();WorkingPawn.Reset();PreviousView.Reset();Player.Reset();
}
void AEnhancementWorldView::EndPlay(const EEndPlayReason::Type Reason)
{End();Super::EndPlay(Reason);}

float AEnhancementWorldView::PlacementOffset() const
{
    if(bPlacementWaiting)return PlacementHeight;
    if(PlacementTime<0.f)return 0.f;
    if(PlacementTime<PlacementFallSeconds)
    {
        const float T=PlacementTime/PlacementFallSeconds;
        return PlacementHeight*(1.f-T*T); // Accelerating fall, zero penetration.
    }
    if(PlacementTime<PlacementFallSeconds+PlacementBounceSeconds)
    {
        const float T=(PlacementTime-PlacementFallSeconds)/PlacementBounceSeconds;
        return 3.f*4.f*T*(1.f-T);
    }
    const float T=FMath::Clamp((PlacementTime-PlacementFallSeconds-PlacementBounceSeconds)/PlacementSettleSeconds,0.f,1.f);
    return .55f*4.f*T*(1.f-T);
}
void AEnhancementWorldView::StopPlacement()
{
    PlacementTime=-1.f;PlacementWait=0.f;bPlacementWaiting=false;
    SetActorTickInterval(.1f);
    if(IsValid(Display))Display->SetActorHiddenInGame(false);
}
void AEnhancementWorldView::PlayPlacement(const FString& Id)
{
    if(Id.IsEmpty()||!SetItem(Id)||!IsValid(Display))return;
    StopPlacement();
    bPlacementWaiting=!Display->IsWorkbenchDisplayReady();
    PlacementTime=bPlacementWaiting?-1.f:0.f;PlacementStartedAt=GetWorld()->GetTimeSeconds();
    // Wait for the authored bow/staff bounds, not their streaming placeholder.
    // The bounded wait never blocks loading and cannot turn into a late replay.
    Display->SetActorHiddenInGame(bPlacementWaiting);
    PrimaryActorTick.UpdateTickIntervalAndCoolDown(bPlacementWaiting?.05f:0.f);
    UpdateDisplayPose();
}
void AEnhancementWorldView::PlayRitual(bool bEnchant)
{
    StopPlacement();UpdateDisplayPose();
    if(IsSessionValid()&&IsValid(Display)&&IsValid(RitualEffect))RitualEffect->Play(Display,Camera,bEnchant,Station->Body());
}


bool AEnhancementWorldView::HitItem(FVector2D Pixel) const
{
    if(!bEntered||!Player.IsValid()||!IsValid(Display)||Display->IsHidden()
        ||!Display->Body||!Display->IsWorkbenchDisplayReady()||Pixel.ContainsNaN())return false;
    int32 Width=0,Height=0;Player->GetViewportSize(Width,Height);
    if(Width<=0||Height<=0)return false;
    const auto Layout=FColdSteelEnhancementLayoutMetrics::ForViewport(FVector2D(Width,Height));
    if(Pixel.X<Layout.ScenePosition.X||Pixel.Y<Layout.ScenePosition.Y
        ||Pixel.X>Layout.ScenePosition.X+Layout.SceneSize.X||Pixel.Y>Layout.ScenePosition.Y+Layout.SceneSize.Y)return false;

    // Keep the precise path, but do not make a thin/stale physics box the only
    // way to grab a cosmetic item. The visible assembly owns the fallback area.
    FVector Origin,Direction;
    if(Player->DeprojectScreenPositionToWorld(Pixel.X,Pixel.Y,Origin,Direction))
    {
        const FTransform Transform=Display->Body->GetComponentTransform();
        const FVector Start=Transform.InverseTransformPosition(Origin);
        const FVector End=Transform.InverseTransformPosition(Origin+Direction*10000.f);
        const FVector Extent=Display->Body->GetUnscaledBoxExtent()+FVector(1.f);
        if(FMath::LineBoxIntersection(FBox(-Extent,Extent),Start,End,End-Start))return true;
    }
    FBox VisibleBounds(ForceInit);
    TInlineComponentArray<UMeshComponent*> Parts(Display);
    for(const auto* Part:Parts)
        if(Part->IsRegistered()&&Part->IsVisible()&&!Part->bHiddenInGame)
        {
            const FBox Bounds=Part->Bounds.GetBox();
            if(Bounds.IsValid&&!Bounds.Min.ContainsNaN()&&!Bounds.Max.ContainsNaN())VisibleBounds+=Bounds;
        }
    if(!VisibleBounds.IsValid)return false;
    FBox2D ScreenBounds(ForceInit);
    for(int32 Corner=0;Corner<8;++Corner)
    {
        const FVector WorldPoint((Corner&1)?VisibleBounds.Max.X:VisibleBounds.Min.X,
            (Corner&2)?VisibleBounds.Max.Y:VisibleBounds.Min.Y,(Corner&4)?VisibleBounds.Max.Z:VisibleBounds.Min.Z);
        FVector2D ScreenPoint;
        if(!Player->ProjectWorldLocationToScreen(WorldPoint,ScreenPoint,false)||ScreenPoint.ContainsNaN())return false;
        ScreenBounds+=ScreenPoint;
    }
    // About 24 physical pixels at 1080p, bounded for compact/4K viewports.
    // One stored item exists, and the scene clamp prevents this margin from
    // intercepting inventory slots or management buttons. Hover and drag agree.
    const float Margin=FMath::Clamp(float(Height)/1080.f,.75f,1.5f)*24.f;
    return Pixel.X>=ScreenBounds.Min.X-Margin&&Pixel.X<=ScreenBounds.Max.X+Margin
        &&Pixel.Y>=ScreenBounds.Min.Y-Margin&&Pixel.Y<=ScreenBounds.Max.Y+Margin;
}
void AEnhancementWorldView::SetItemHovered(bool Hovered)
{
    if(bItemHovered==Hovered)return;
    bItemHovered=Hovered;ApplyItemHover();
}
void AEnhancementWorldView::ApplyItemHover()
{
    if(!IsValid(Display))return;
    TInlineComponentArray<UMeshComponent*> Parts(Display);
    for(auto* Part:Parts)
    {
        const bool Show=bItemHovered&&Part->IsVisible()&&!Part->bHiddenInGame;
        if(Show&&Part->CustomDepthStencilValue!=AlchemyInteraction::HoverStencil)
            Part->SetCustomDepthStencilValue(AlchemyInteraction::HoverStencil);
        if(Part->bRenderCustomDepth!=Show)Part->SetRenderCustomDepth(Show);
    }
}

FVector AEnhancementWorldView::RitualLocation() const
{
    // Callers must validate the session before projection; there is no guessed altar position.
    if(!Station.IsValid()||!Station->Body()||!Station->Body()->DoesSocketExist(TEXT("ArcaneItem")))return FVector::ZeroVector;
    return Station->Body()->GetSocketLocation(TEXT("ArcaneItem"));
}
