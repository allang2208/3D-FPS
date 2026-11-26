#include "VillageSiegeControl.h"
#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../Skills/FPSMagicPreview.h"
#include "Components/LineBatchComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/World.h"
#include "GameFramework/PawnMovementComponent.h"
#include "GameFramework/PlayerInput.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
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
    PreviousView=PC->GetViewTarget();
    FActorSpawnParameters Spawn;
    Spawn.Owner=PC;
    Spawn.Instigator=PC->GetPawn();
    Spawn.ObjectFlags|=RF_Transient;
    Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    Camera=GetWorld()->SpawnActor<ACameraActor>(ACameraActor::StaticClass(),Station->GetActorTransform(),Spawn);
    if(!Camera){ServerLeave(Station);return;}
    Camera->GetCameraComponent()->bConstrainAspectRatio=false;
    Camera->GetCameraComponent()->FieldOfView=Station->IsTrebuchet()?76.f:64.f;
    ViewedStation=Station;
    if(auto* Character=Cast<AFPSGAMECharacter>(PC->GetPawn()))Character->SuspendWeaponForMenu();
    if(PC->PlayerInput)PC->PlayerInput->FlushPressedKeys();
    PC->SetIgnoreMoveInput(true);
    bMoveLocked=true;
    UpdateSight();
    PC->SetViewTarget(Camera);
}

void UVillageSiegeControl::AddHiddenOperatorComponents(const AActor* ViewTarget,TSet<FPrimitiveComponentId>& Hidden) const
{
    if(!Active() || !IsValid(Camera) || ViewTarget!=Camera)return;
    const APawn* Operator=Camera->GetInstigator();
    if(!IsValid(Operator))return;
    // Start at each locally owned component root, including unattached first-person parts.
    Operator->ForEachComponent<USceneComponent>(false,[&](USceneComponent* Part)
    {
        const USceneComponent* Parent=Part->GetAttachParent();
        if(!Parent || Parent->GetOwner()!=Operator)HideAppearanceBranch(*Part,Hidden);
    });
}

void UVillageSiegeControl::RestoreView()
{
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
    // Terrain and roof lips need a surface contour; a single plane cuts through them.
    const double Radius=Station->BlastRadius();
    if(Now>=OutlineRefreshAt || OutlineRadius!=Radius || bOutlineHitUnit!=Sight.bHitUnit ||
        !OutlineCenter.Equals(Sight.Impact,3.) || !OutlineNormal.Equals(Normal,.01))
    {
        OutlineCenter=Sight.Impact;
        OutlineNormal=Normal;
        OutlineRadius=Radius;
        bOutlineHitUnit=Sight.bHitUnit;
        OutlineRefreshAt=Now+.25;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(SiegeImpactOutline),false,Station);
        Query.AddIgnoredActor(Camera->GetInstigator());
        Query.AddIgnoredActor(Station->GetAttachParentActor());
        BuildImpactOutline(*GetWorld(),OutlineCenter,Normal,Sight.bHitUnit,Query,ImpactOutline,Radius);
    }
    TrajectoryLines->DrawLines(ImpactOutline);
}

void UVillageSiegeControl::UpdateSight()
{
    const auto* PC=CastChecked<AFPSGAMEPlayerController>(GetOwner());
    Station->ManualSight(PC->GetPawn(),AimYaw,AimElevation,Sight,true);
    Camera->SetActorLocationAndRotation(Sight.Camera,Sight.View);
    Station->DisplaySight(&Sight.Plan);
    const double Now=GetWorld()->GetTimeSeconds();
    if(Station->IsTrebuchet())
    {
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
    const FRotator Bearing(Sight.Plan.Pitch,Sight.Plan.Yaw,0.);
    const double Elapsed=Now-LastBearingSend;
    if(Elapsed>=.1 && (!Bearing.Equals(LastSentBearing,.2) || Elapsed>=1.))
    {
        LastBearingSend=Now;
        LastSentBearing=Bearing;
        ServerPointSiege(Station,Bearing);
    }
    NextPreview=Now+1./30.;
}

void UVillageSiegeControl::TickComponent(float Delta,ELevelTick Tick,FActorComponentTickFunction* Function)
{
    Super::TickComponent(Delta,Tick,Function);
    if(GetOwner()->HasAuthority() && !SessionValid()){ReleaseSeat();return;}
    if(!Active()){OnRep_Station();return;}
    if(Camera && GetWorld()->GetTimeSeconds()>=NextPreview)UpdateSight();
}

bool UVillageSiegeControl::HandleInput(const FInputKeyEventArgs& Event)
{
    if(!Active())return false;
    if(Event.Key==EKeys::MouseX)
        AimYaw=Station->ResolveAimYaw(AimYaw+Event.AmountDepressed*.12);
    else if(Event.Key==EKeys::MouseY)
    {
        const bool Stone=Station->IsTrebuchet();
        AimElevation=FMath::Clamp(AimElevation+float(Event.AmountDepressed)*.12f,Stone?-28.f:-48.f,Stone?24.f:40.f);
    }
    else if(Event.Event==IE_Pressed)
    {
        if(Event.Key==EKeys::E || Event.Key==EKeys::Escape)ServerLeave(Station);
        else if(Event.Key==EKeys::LeftMouseButton && Camera)
        {
            UpdateSight();
            if(Sight.CanFire && Station->ReloadRemaining()<=0.)ServerFire(Station,AimYaw,AimElevation);
        }
    }
    return true;
}

#include "VillageSiegePreviewTests.inl"
