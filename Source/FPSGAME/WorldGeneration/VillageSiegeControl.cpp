#include "VillageSiegeControl.h"
#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/ColdSteelUIStyle.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../Skills/FPSMagicPreview.h"
#include "Components/LineBatchComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/PawnMovementComponent.h"
#include "GameFramework/PlayerInput.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"
#include "../Building/VoxelBuildGrounding.h"
#include "Net/UnrealNetwork.h"

namespace
{
    constexpr int32 ImpactOutlineSides=40;
    void HideAppearanceBranch(const USceneComponent& Node,TSet<FPrimitiveComponentId>& Hidden)
    {
        if(const auto* Part=Cast<UPrimitiveComponent>(&Node);Part && Part->IsRegistered())
            Hidden.Add(Part->GetPrimitiveSceneId());
        for(const USceneComponent* Child:Node.GetAttachChildren())
            if(IsValid(Child) && (Child->GetOwner()==Node.GetOwner() || !Cast<APawn>(Child->GetOwner())))
                HideAppearanceBranch(*Child,Hidden);
    }

    constexpr double GroundLift=1.5;
    constexpr double MinGroundNormalZ=.45;
    constexpr double GroundSearchDepth=12000.;

    bool TraceFixedSurface(UWorld& World,const FVector& Start,const FVector& End,const FCollisionQueryParams& Query,FHitResult& Hit)
    {
        if(!World.LineTraceSingleByChannel(Hit,Start,End,ECC_WorldDynamic,Query))return false;
        if(VoxelGrounding::IsFixedBuildingSurface(Hit))return true;
        FCollisionQueryParams Filter=Query;
        while(AActor* Blocker=Hit.GetActor())
        {
            // A pawn or a loose prop can block the stone, but cannot carry the ground indicator.
            Filter.AddIgnoredActor(Blocker);
            if(!World.LineTraceSingleByChannel(Hit,Start,End,ECC_WorldDynamic,Filter))break;
            if(VoxelGrounding::IsFixedBuildingSurface(Hit))return true;
        }
        return false;
    }

    bool GroundBelow(UWorld& World,const FVector& Top,double Depth,const FCollisionQueryParams& Query,FHitResult& Hit)
    {
        return TraceFixedSurface(World,Top,Top-FVector(0,0,Depth),Query,Hit) &&
            Hit.IsValidBlockingHit() && Hit.ImpactNormal.Z>=MinGroundNormalZ;
    }

    void BuildImpactOutline(UWorld& World,const FVector& Impact,const FVector& ImpactNormal,bool bHitUnit,
        const FCollisionQueryParams& Query,TArray<FBatchedLine>& Lines,double Radius)
    {
        Lines.Reset(ImpactOutlineSides);
        // Project down beside a wall face, or through a struck unit to the floor beneath it.
        const FVector Offset=!bHitUnit && ImpactNormal.Z<MinGroundNormalZ?ImpactNormal*2.:FVector::ZeroVector;
        FHitResult Foot;
        if(!GroundBelow(World,Impact+FVector(0,0,2.)+Offset,GroundSearchDepth,Query,Foot))return;
        const FVector Ground=Foot.ImpactPoint,Normal=Foot.ImpactNormal;
        FVector X,Y;
        Normal.FindBestAxisVectors(X,Y);
        const auto Sample=[&](FVector Expected,FHitResult& Hit)
        {
            // Keep the same reference layer for every column, including subdivisions at a ledge.
            // A rim over a drop can still be drawn on the ground below, without spanning the gap.
            const FVector Delta=Expected-Ground;
            const double PlaneZ=Ground.Z-(Normal.X*Delta.X+Normal.Y*Delta.Y)/Normal.Z;
            const FVector Top(Expected.X,Expected.Y,PlaneZ+100.);
            return GroundBelow(World,Top,GroundSearchDepth+100.,Query,Hit);
        };
        const FLinearColor Color=FPSMagicPreview::LineColor();
        const auto DrawEdge=[&](auto&& Self,const FHitResult& A,const FHitResult& B,int32 Subdivisions)->void
        {
            const FVector D=B.ImpactPoint-A.ImpactPoint;
            // Different decks, steps and sharp lips must not be joined by a floating diagonal.
            const FVector Start=A.ImpactPoint+FVector(0,0,GroundLift),End=B.ImpactPoint+FVector(0,0,GroundLift);
            FHitResult Obstacle;
            if(FMath::Abs(D|A.ImpactNormal)<=GroundLift && FMath::Abs(D|B.ImpactNormal)<=GroundLift &&
                !TraceFixedSurface(World,Start,End,Query,Obstacle))
            {
                Lines.Emplace(Start,End,Color,0.f,1.f,SDPG_World);
                return;
            }
            FHitResult Middle;
            if(Subdivisions>0 && Sample((A.ImpactPoint+B.ImpactPoint)*.5,Middle))
            {
                Self(Self,A,Middle,Subdivisions-1);
                Self(Self,Middle,B,Subdivisions-1);
            }
        };
        FHitResult Samples[ImpactOutlineSides];
        bool Valid[ImpactOutlineSides];
        for(int32 I=0;I<ImpactOutlineSides;++I)
        {
            const double Angle=UE_TWO_PI*I/ImpactOutlineSides;
            Valid[I]=Sample(Ground+(X*FMath::Cos(Angle)+Y*FMath::Sin(Angle))*Radius,Samples[I]);
        }
        for(int32 I=0;I<ImpactOutlineSides;++I)
        {
            const int32 J=(I+1)%ImpactOutlineSides;
            if(!Valid[I] || !Valid[J])continue;
            // A clear line-of-sight alone also passes above holes. Ground the middle of the chord.
            FHitResult Middle;
            if(!Sample((Samples[I].ImpactPoint+Samples[J].ImpactPoint)*.5,Middle))continue;
            DrawEdge(DrawEdge,Samples[I],Middle,2);
            DrawEdge(DrawEdge,Middle,Samples[J],2);
        }
    }

    bool Living(const APawn* Pawn)
    {
        if(!IsValid(Pawn) || Pawn->IsActorBeingDestroyed())return false;
        const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
        return !Health || !Health->IsDead();
    }
}

UVillageSiegeControl::UVillageSiegeControl()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
}

void UVillageSiegeControl::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UVillageSiegeControl,EntryAim);
    DOREPLIFETIME(UVillageSiegeControl,Station);
}

void UVillageSiegeControl::ServerEnter_Implementation(AVillageSiegeEngine* Engine,APawn* RequestPawn)
{
    auto* PC=CastChecked<AFPSGAMEPlayerController>(GetOwner());
    if(Active() || !IsValid(Engine) || !Living(RequestPawn) || RequestPawn!=PC->GetPawn() || PC->IsInBuildMode() ||
        AFPSGAMEPlayerController::BlocksOngoingActions(PC) || ColdSteelWorldInteraction::TraceUseTargets(PC).Target!=Engine)return;
    if(!Engine->Claim(RequestPawn))return;
    EntryAim=Engine->ClaimedAim();
    Station=Engine;
    SeatPawn=RequestPawn;
    SeatLocation=RequestPawn->GetActorLocation();
    if(auto* Move=RequestPawn->GetMovementComponent())Move->StopMovementImmediately();
    OnRep_Station();
    PC->ForceNetUpdate();
}

bool UVillageSiegeControl::SessionValid() const
{
    const auto* PC=CastChecked<AFPSGAMEPlayerController>(GetOwner());
    const APawn* Pawn=SeatPawn.Get();
    return Active() && Station->CanOperate() && Living(Pawn) && Pawn==PC->GetPawn() && Station->IsOperatedBy(Pawn) &&
        FVector::DistSquared(Pawn->GetActorLocation(),SeatLocation)<=FMath::Square(160.);
}

void UVillageSiegeControl::ReleaseSeat()
{
    if(IsValid(Station))Station->Vacate(SeatPawn.Get());
    Station=nullptr;
    SeatPawn.Reset();
    OnRep_Station();
    GetOwner()->ForceNetUpdate();
}

void UVillageSiegeControl::ServerLeave_Implementation(AVillageSiegeEngine* Engine)
{
    if(Station && Station==Engine)ReleaseSeat();
}

void UVillageSiegeControl::ServerPointSiege_Implementation(AVillageSiegeEngine* Engine,FRotator Bearing)
{
    if(Active() && Engine==Station && SessionValid())Station->SetManualBearing(SeatPawn.Get(),Bearing);
}

void UVillageSiegeControl::ServerFire_Implementation(AVillageSiegeEngine* Engine,float Yaw,float Elevation)
{
    if(!Station || Station!=Engine)return;
    if(!SessionValid()){ReleaseSeat();return;}
    Station->FireManual(SeatPawn.Get(),Yaw,Elevation);
}

float UVillageSiegeControl::BaseFieldOfView() const
{
    if(!IsValid(Station))return 64.f;
    return Station->IsTrebuchet()?76.f:(Station->IsLightningSpire()?70.f:64.f);
}

void UVillageSiegeControl::ConfigureCameraPostProcess() const
{
    if(!IsValid(Camera))return;
    UCameraComponent* Cam=Camera->GetCameraComponent();
    if(!Cam)return;
    const auto* PC=Cast<APlayerController>(GetOwner());
    const APawn* Pawn=PC?PC->GetPawn():nullptr;
    if(const auto* PawnCam=Pawn?Pawn->FindComponentByClass<UCameraComponent>():nullptr)
        Cam->PostProcessSettings=PawnCam->PostProcessSettings;

    Cam->bConstrainAspectRatio=false;
    Cam->bOverrideAspectRatioAxisConstraint=true;
    Cam->AspectRatioAxisConstraint=EAspectRatioAxisConstraint::AspectRatio_MaintainYFOV;
    Cam->PostProcessBlendWeight=1.f;
    Cam->FieldOfView=BaseFieldOfView();

    FPostProcessSettings& S=Cam->PostProcessSettings;
    S.bOverride_MotionBlurAmount=true;
    S.MotionBlurAmount=0.f;
    S.bOverride_MotionBlurMax=true;
    S.MotionBlurMax=0.f;
    S.bOverride_LensFlareIntensity=true;
    S.LensFlareIntensity=0.f;
    S.bOverride_BloomDirtMaskIntensity=true;
    S.BloomDirtMaskIntensity=0.f;
    S.bOverride_BloomMethod=true;
    S.BloomMethod=BM_SOG;
    S.bOverride_BloomIntensity=true;
    S.BloomIntensity=0.15f;
    S.bOverride_BloomGaussianIntensity=true;
    S.BloomGaussianIntensity=1.f;
    S.bOverride_BloomThreshold=true;
    S.BloomThreshold=2.f;
}

void UVillageSiegeControl::CreateOverlay()
{
    DestroyOverlay();
    auto* PC=Cast<APlayerController>(GetOwner());
    auto* Player=PC?PC->GetLocalPlayer():nullptr;
    if(!Player || !Player->ViewportClient || !IsValid(Station))return;
    SiegeOverlay=SNew(SOverlay).Visibility(EVisibility::HitTestInvisible)
        +SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Bottom).Padding(8.f,0.f,8.f,32.f)
        [
            SAssignNew(HintTextBlock,STextBlock)
            .Font(ColdSteelUI::TextFont(14.f*.75f))
            .Justification(ETextJustify::Center)
            .ShadowColorAndOpacity(FLinearColor::Black)
            .ShadowOffset(FVector2D(1.,1.))
            .Visibility(EVisibility::HitTestInvisible)
        ];
    LastHintHotOilCharge=-2;
    UpdateOverlayHint();
    Player->ViewportClient->AddViewportWidgetForPlayer(Player,SiegeOverlay.ToSharedRef(),22);
}

void UVillageSiegeControl::UpdateOverlayHint()
{
    if(!HintTextBlock.IsValid() || !IsValid(Station))return;
    int32 State=-1;
    if(Station->IsTrebuchet() && Station->HasTrebuchetHotOil())
        State=Station->IsNextShotHotOil()?3:FMath::Clamp(Station->HotOilChargeCount(),0,2);
    if(State==LastHintHotOilCharge)return;
    LastHintHotOilCharge=State;
    FString Hint;
    FLinearColor Color(0.95f,0.95f,0.95f,0.88f);
    if(Station->IsTrebuchet())
    {
        if(State==3)
        {
            Hint=TEXT("配重投石机  ·  【下一发：热油弹（友方免伤）】  ·  左键发射  ·  鼠标上下调节射程  ·  E / Esc 退出");
            Color=ColdSteelUI::HUDGoldLight;
        }
        else if(State>=0)
        {
            Hint=FString::Printf(TEXT("配重投石机  ·  热油充能 %d/3  ·  左键发射  ·  鼠标上下调节射程  ·  E / Esc 退出"),State);
        }
        else Hint=TEXT("配重投石机  ·  左键发射  ·  鼠标上下调节射程  ·  E / Esc 退出");
    }
    else
    {
        Hint=FString::Printf(TEXT("%s  ·  左键发射  ·  长按右键缩放  ·  E / Esc 退出"),Station->DisplayName());
    }
    HintTextBlock->SetText(FText::FromString(Hint));
    HintTextBlock->SetColorAndOpacity(Color);
}

void UVillageSiegeControl::DestroyOverlay()
{
    HintTextBlock.Reset();
    LastHintHotOilCharge=-2;
    if(!SiegeOverlay.IsValid())return;
    if(const auto* PC=Cast<APlayerController>(GetOwner()))
        if(auto* Player=PC->GetLocalPlayer();Player && Player->ViewportClient)
            Player->ViewportClient->RemoveViewportWidgetForPlayer(Player,SiegeOverlay.ToSharedRef());
    SiegeOverlay.Reset();
}

void UVillageSiegeControl::OnRep_Station()
{
    auto* PC=CastChecked<AFPSGAMEPlayerController>(GetOwner());
    SetComponentTickEnabled(Active());
    if(!PC->IsLocalController())return;
    RestoreView();
    if(!Active())return;
    AimYaw=EntryAim.Yaw;
    AimElevation=EntryAim.Pitch;
    LastBearingSend=-2.;
    bZooming=false;
    bFireHeld=false;
    bAimDirty=true;
    bHasTrebuchetGroundZ=false;
    CachedTrebuchetGroundZ=Station->GetActorLocation().Z-200.;
    NextPreview=-1.;
    CachedHiddenStation.Reset();
    CachedHiddenCamera.Reset();
    CachedHiddenIds.Reset();
    NextHiddenRefreshAt=-1.;
    PreviousView=PC->GetViewTarget();
    FActorSpawnParameters Spawn;
    Spawn.Owner=PC;
    Spawn.Instigator=PC->GetPawn();
    Spawn.ObjectFlags|=RF_Transient;
    Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    Camera=GetWorld()->SpawnActor<ACameraActor>(ACameraActor::StaticClass(),Station->GetActorTransform(),Spawn);
    if(!Camera){ServerLeave(Station);return;}
    ConfigureCameraPostProcess();
    ViewedStation=Station;
    if(auto* Character=Cast<AFPSGAMECharacter>(PC->GetPawn()))Character->SuspendWeaponForMenu();
    if(PC->PlayerInput)PC->PlayerInput->FlushPressedKeys();
    PC->SetIgnoreMoveInput(true);
    bMoveLocked=true;
    CreateOverlay();
    ApplyCameraPose(0.f);
    UpdatePreviewOverlay(true);
    PC->SetViewTarget(Camera);
}

void UVillageSiegeControl::AddHiddenOperatorComponents(const AActor* ViewTarget,TSet<FPrimitiveComponentId>& Hidden) const
{
    if(!Active() || !IsValid(Camera) || ViewTarget!=Camera)return;
    const double Now=GetWorld()?GetWorld()->GetTimeSeconds():0.;
    if(CachedHiddenStation.Get()!=Station.Get() || CachedHiddenCamera.Get()!=Camera.Get() || Now>=NextHiddenRefreshAt)
    {
        CachedHiddenStation=Station;
        CachedHiddenCamera=Camera;
        NextHiddenRefreshAt=Now+.5;
        TSet<FPrimitiveComponentId> Fresh;
        if(Station->IsLightningSpire())
            Station->ForEachComponent<USceneComponent>(false,[&](USceneComponent* Part)
            {
                const USceneComponent* Parent=Part->GetAttachParent();
                if(!Parent || Parent->GetOwner()!=Station)HideAppearanceBranch(*Part,Fresh);
            });
        const APawn* Operator=Camera->GetInstigator();
        if(IsValid(Operator))
        {
            // Start at each locally owned component root, including unattached first-person parts.
            Operator->ForEachComponent<USceneComponent>(false,[&](USceneComponent* Part)
            {
                const USceneComponent* Parent=Part->GetAttachParent();
                if(!Parent || Parent->GetOwner()!=Operator)HideAppearanceBranch(*Part,Fresh);
            });
        }
        CachedHiddenIds=Fresh.Array();
    }
    Hidden.Append(CachedHiddenIds);
}

void UVillageSiegeControl::RestoreView()
{
    DestroyOverlay();
    bZooming=false;
    bFireHeld=false;
    bAimDirty=false;
    bHasTrebuchetGroundZ=false;
    CachedHiddenStation.Reset();
    CachedHiddenCamera.Reset();
    CachedHiddenIds.Reset();
    NextHiddenRefreshAt=-1.;
    auto* PC=CastChecked<AFPSGAMEPlayerController>(GetOwner());
    if(bMoveLocked){PC->SetIgnoreMoveInput(false);bMoveLocked=false;}
    FPSMagicPreview::Clear(TrajectoryLines);
    TrajectoryLines=nullptr;
    ImpactOutline.Reset();
    OutlineRefreshAt=-1.;
    if(IsValid(Camera))
    {
        if(PC->GetViewTarget()==Camera)
        {
            AActor* ReturnTo=PreviousView.Get();
            if(!IsValid(ReturnTo) || Cast<APawn>(ReturnTo))ReturnTo=PC->GetPawn();
            if(ReturnTo)PC->SetViewTarget(ReturnTo);
        }
        Camera->Destroy();
    }
    if(auto* Engine=ViewedStation.Get())Engine->DisplaySight(nullptr);
    ViewedStation.Reset();
    Camera=nullptr;
    PreviousView.Reset();
    Sight.Arc.Reset();
}

void UVillageSiegeControl::EndPlay(const EEndPlayReason::Type Reason)
{
    if(GetOwner()->HasAuthority() && IsValid(Station))Station->Vacate(SeatPawn.Get());
    RestoreView();
    Super::EndPlay(Reason);
}

void UVillageSiegeControl::DrawImpactOutline(const FVector& Normal,double Now)
{
    // Terrain and roof lips need a surface contour; coalesce drag updates to keep high FPS.
    const double Radius=Station->BlastRadius();
    const double SnapTol=bAimDirty?24.:3.;
    if(Now>=OutlineRefreshAt || OutlineRadius!=Radius || bOutlineHitUnit!=Sight.bHitUnit ||
        !OutlineCenter.Equals(Sight.Impact,SnapTol) || !OutlineNormal.Equals(Normal,.02))
    {
        OutlineCenter=Sight.Impact;
        OutlineNormal=Normal;
        OutlineRadius=Radius;
        bOutlineHitUnit=Sight.bHitUnit;
        OutlineRefreshAt=Now+(bAimDirty?.10:.25);
        FCollisionQueryParams Query(SCENE_QUERY_STAT(SiegeImpactOutline),false,Station);
        Query.AddIgnoredActor(Camera->GetInstigator());
        Query.AddIgnoredActor(Station->GetAttachParentActor());
        BuildImpactOutline(*GetWorld(),OutlineCenter,Normal,Sight.bHitUnit,Query,ImpactOutline,Radius);
    }
    TrajectoryLines->DrawLines(ImpactOutline);
}

void UVillageSiegeControl::SendBearingIfDue(double Now,const FRotator& Bearing)
{
    const double Elapsed=Now-LastBearingSend;
    if(Elapsed>=.1 && (!Bearing.Equals(LastSentBearing,.25) || Elapsed>=1.))
    {
        LastBearingSend=Now;
        LastSentBearing=Bearing;
        ServerPointSiege(Station,Bearing);
    }
}

void UVillageSiegeControl::ApplyCameraPose(float DeltaSeconds)
{
    if(!IsValid(Camera) || !IsValid(Station))return;
    FVector CamLoc;
    FRotator CamRot,Facing;
    Station->ComputeManualCamera(AimYaw,AimElevation,CachedTrebuchetGroundZ,CamLoc,CamRot,Facing);
    Camera->SetActorLocationAndRotation(CamLoc,CamRot);

    if(auto* Cam=Camera->GetCameraComponent())
    {
        const float TargetFOV=(bZooming && !Station->IsTrebuchet())?(Station->IsLightningSpire()?46.f:42.f):BaseFieldOfView();
        if(DeltaSeconds>0.f && !FMath::IsNearlyEqual(Cam->FieldOfView,TargetFOV,.05f))
            Cam->SetFieldOfView(FMath::FInterpTo(Cam->FieldOfView,TargetFOV,DeltaSeconds,14.f));
        else if(DeltaSeconds<=0.f)
            Cam->SetFieldOfView(TargetFOV);
    }

    FVillageSiegeShot Plan;
    Plan.Yaw=Facing.Yaw;
    Plan.Pitch=Facing.Pitch;
    Station->DisplaySight(&Plan);
    SendBearingIfDue(GetWorld()->GetTimeSeconds(),Facing);
}

void UVillageSiegeControl::UpdatePreviewOverlay(bool bForce)
{
    if(!IsValid(Camera) || !IsValid(Station))return;
    const double Now=GetWorld()->GetTimeSeconds();
    const bool bMoved=bForce || bAimDirty ||
        !FMath::IsNearlyEqual(LastPreviewYaw,AimYaw,.05f) ||
        !FMath::IsNearlyEqual(LastPreviewElevation,AimElevation,.05f);

    if(!Station->IsTrebuchet() && !Station->IsLightningSpire())
    {
        // Ballista needs zero raycasts while aiming; server verifies final impact on fire.
        Sight.CanFire=true;
        Sight.bHitUnit=false;
        bAimDirty=false;
        LastPreviewYaw=AimYaw;
        LastPreviewElevation=AimElevation;
        return;
    }

    const double Interval=Station->IsTrebuchet()?(1./20.):(1./15.);
    const double Heartbeat=Station->IsTrebuchet()?.30:.16;
    if(!bForce && Now<NextPreview)return;
    if(!bMoved && Now<NextPreview+Heartbeat)return;

    const auto* PC=CastChecked<AFPSGAMEPlayerController>(GetOwner());
    Station->ManualSight(PC->GetPawn(),AimYaw,AimElevation,Sight,true);
    LastPreviewYaw=AimYaw;
    LastPreviewElevation=AimElevation;
    bAimDirty=false;
    NextPreview=Now+Interval;

    if(Station->IsTrebuchet())
    {
        if(Sight.HasImpact)
        {
            CachedTrebuchetGroundZ=bHasTrebuchetGroundZ
                ?FMath::Lerp(CachedTrebuchetGroundZ,Sight.Impact.Z,.45)
                :Sight.Impact.Z;
            bHasTrebuchetGroundZ=true;
            // Re-align camera smoothly once initial terrain elevation is sampled.
            if(bForce)ApplyCameraPose(0.f);
        }
        FPSMagicPreview::BeginRefresh(TrajectoryLines,Camera);
        TrajectoryLines->SetOnlyOwnerSee(true);
        if(Sight.HasImpact)
        {
            const FVector Normal=Sight.bHitUnit?FVector::UpVector:Sight.ImpactNormal;
            DrawImpactOutline(Normal,Now);
            FPSMagicPreview::DrawPath(TrajectoryLines,Sight.Arc,FPSMagicPreview::LineThickness,0.f,true);
        }
        else OutlineRefreshAt=-1.;
    }
}

void UVillageSiegeControl::UpdateSight()
{
    ApplyCameraPose(0.f);
    UpdatePreviewOverlay(true);
}

void UVillageSiegeControl::TryFireManual()
{
    if(!IsValid(Camera) || !IsValid(Station) || Station->ReloadRemaining()>0.)return;
    UpdatePreviewOverlay(true);
    if(Sight.CanFire)ServerFire(Station,AimYaw,AimElevation);
}

void UVillageSiegeControl::TickComponent(float Delta,ELevelTick Tick,FActorComponentTickFunction* Function)
{
    Super::TickComponent(Delta,Tick,Function);
    if(GetOwner()->HasAuthority() && !SessionValid()){ReleaseSeat();return;}
    if(!Active()){OnRep_Station();return;}
    if(!Camera)return;
    ApplyCameraPose(Delta);
    UpdatePreviewOverlay(false);
    UpdateOverlayHint();
    if(bFireHeld && Station->ReloadRemaining()<=0.)TryFireManual();
}

bool UVillageSiegeControl::HandleInput(const FInputKeyEventArgs& Event)
{
    if(!Active())return false;
    const auto* PC=Cast<APlayerController>(GetOwner());
    if(Event.Key==EKeys::MouseX || Event.Key==EKeys::MouseY)
    {
        double Scale=1.;
        bool bInvert=false;
        if(PC && PC->PlayerInput)
        {
            FInputAxisProperties Props;
            if(PC->PlayerInput->GetAxisProperties(Event.Key,Props))
            {
                Scale=FMath::Clamp(double(Props.Sensitivity)/.07,.25,3.);
                bInvert=(Event.Key==EKeys::MouseY) && (Props.bInvert!=0);
            }
        }
        const double ZoomMul=bZooming?.52:1.;
        const double Delta=Event.AmountDepressed*.12*Scale*ZoomMul*(bInvert?-1.:1.);
        if(Event.Key==EKeys::MouseX)
            AimYaw=Station->ResolveAimYaw(AimYaw+Delta);
        else
        {
            const bool Stone=Station->IsTrebuchet();
            const bool Spire=Station->IsLightningSpire();
            AimElevation=FMath::Clamp(AimElevation+float(Delta),
                Stone?-28.f:(Spire?-76.f:-48.f),Stone?24.f:(Spire?35.f:40.f));
        }
        bAimDirty=true;
        ApplyCameraPose(0.f);
        return true;
    }
    if(Event.Key==EKeys::RightMouseButton)
    {
        if(Event.Event==IE_Pressed && !Station->IsTrebuchet())bZooming=true;
        else if(Event.Event==IE_Released)bZooming=false;
        return true;
    }
    if(Event.Key==EKeys::LeftMouseButton)
    {
        if(Event.Event==IE_Pressed){bFireHeld=true;TryFireManual();}
        else if(Event.Event==IE_Released)bFireHeld=false;
        return true;
    }
    if(Event.Event==IE_Pressed && (Event.Key==EKeys::E || Event.Key==EKeys::Escape))
        ServerLeave(Station);
    return true;
}

#include "VillageSiegePreviewTests.inl"
