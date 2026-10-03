#include "FPSIceSpikeVolley.h"
#include "FPSIceWall.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "FPSIceSpikeComponent.h"
#include "FPSFireballComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "Components/StaticMeshComponent.h"
#include "Components/LineBatchComponent.h"
#include "FPSMagicPreview.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Perception/AISense_Hearing.h"
#include "NiagaraComponent.h"
#include "HAL/IConsoleManager.h"
#include "Net/UnrealNetwork.h"
#include "NetCastUtils.h"

// Live tuning while the user dials the hover by eye; 0 / 1 are the values to bake.
static TAutoConsoleVariable<float> IceSpikeHoverDropCM(TEXT("fps.IceSpike.HoverDropCM"),0.f,
    TEXT("Extra downward offset of the hovered ice spike row, in cm."));
static TAutoConsoleVariable<float> IceSpikeDriftScale(TEXT("fps.IceSpike.DriftScale"),1.f,
    TEXT("Multiplier on the ice spike hover drift amplitude."));
static TAutoConsoleVariable<float> IceSpikeWingGap(TEXT("fps.IceSpike.WingGap"),1.4f,
    TEXT("Half width of the empty centre gap in slot units; .15 is the tightest useful gap."));
static TAutoConsoleVariable<float> IceSpikeSlotSpacing(TEXT("fps.IceSpike.SlotSpacing"),26.f,
    TEXT("Upper bound of the slot pitch in cm; the frame width still compresses it per count."));

namespace
{
UStaticMeshComponent* AddIceMesh(AActor* Owner,UStaticMesh* Mesh,UMaterialInterface* Material)
{
    auto* C=NewObject<UStaticMeshComponent>(Owner);Owner->AddInstanceComponent(C);C->SetupAttachment(Owner->GetRootComponent());
    C->SetStaticMesh(Mesh);C->SetMaterial(0,Material);C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    C->SetCanEverAffectNavigation(false);C->SetReceivesDecals(false);C->RegisterComponent();return C;
}
}
AFPSIceSpikeVolley::AFPSIceSpikeVolley()
{
    PrimaryActorTick.bCanEverTick=true;SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("VolleyRoot")));
    // 联机：服务端全量模拟，复制逐锥位置/方向/存活位；远端只摆表现壳。
    bReplicates=true;
}
void AFPSIceSpikeVolley::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AFPSIceSpikeVolley,NetShooter);
    DOREPLIFETIME(AFPSIceSpikeVolley,NetSource);
    DOREPLIFETIME(AFPSIceSpikeVolley,bNetFlying);
    DOREPLIFETIME(AFPSIceSpikeVolley,NetCount);
    DOREPLIFETIME(AFPSIceSpikeVolley,NetCastSpeed);
    DOREPLIFETIME(AFPSIceSpikeVolley,NetSpeed);
    DOREPLIFETIME(AFPSIceSpikeVolley,NetGravity);
    DOREPLIFETIME(AFPSIceSpikeVolley,NetHoverDuration);
    DOREPLIFETIME(AFPSIceSpikeVolley,NetPos);
    DOREPLIFETIME(AFPSIceSpikeVolley,NetDir);
    DOREPLIFETIME(AFPSIceSpikeVolley,NetAlive);
}
void AFPSIceSpikeVolley::Prepare(UFPSIceSpikeComponent* InSource,APawn* InShooter,const FIceSpikeCast& Snapshot,const TArray<TObjectPtr<UStaticMesh>>& Spikes,UStaticMesh* Shard,UMaterialInterface* Material,UMaterialInterface* ShellMaterial,UParticleSystem* FX,USoundBase* Sound,UNiagaraSystem* Motes,UNiagaraSystem* ColdMist)
{
    Source=InSource;Shooter=InShooter;Cast=Snapshot;ShardMesh=Shard;IceMaterial=Material;ImpactFX=FX;ImpactSound=Sound;
    // 联机：服务端把表现所需的最小口径写进复制态——远端副本据此自建壳。
    NetShooter=InShooter;NetSource=InSource;NetCount=Snapshot.Count;
    NetCastSpeed=Snapshot.CastSpeed;NetSpeed=Snapshot.Speed;NetGravity=Snapshot.Gravity;NetHoverDuration=Snapshot.HoverDuration;
    for(int32 I=0;I<Snapshot.Count&&I<32;++I)NetAlive|=1u<<I;
    AddTickPrerequisiteActor(InShooter);AddTickPrerequisiteComponent(InSource);
    if(auto* Hands=InShooter->FindComponentByClass<UFPSFireballComponent>())AddTickPrerequisiteComponent(Hands);
    Flights.SetNum(Cast.Count);
    for(int32 I=0;I<Cast.Count;++I)
    {
        // Randomise each spike once; continuous noise supplies smooth, frame-independent drift.
        Flights[I].HoverNoiseSeed=FVector2D(FMath::FRandRange(0.f,512.f),FMath::FRandRange(0.f,512.f));
        Flights[I].HoverNoiseRate=FVector2D(FMath::FRandRange(.22f,.36f),FMath::FRandRange(.18f,.30f));
        auto* Spike=Spikes[I%Spikes.Num()].Get();
        auto* Core=AddIceMesh(this,Spike,ShellMaterial);Core->SetCastShadow(false);Cores.Add(Core);
        auto* Heart=AddIceMesh(this,Spike,Material);Heart->AttachToComponent(Core,FAttachmentTransformRules::KeepRelativeTransform);
        Heart->SetRelativeScale3D(FVector(.965f,.78f,.78f));Heart->SetCastShadow(false);Hearts.Add(Heart);
        auto* Trail=NewObject<UNiagaraComponent>(this);AddInstanceComponent(Trail);Trail->SetupAttachment(GetRootComponent());Trail->SetAsset(Motes);Trail->SetAutoActivate(false);Trail->SetCastShadow(false);Trail->RegisterComponent();Trail->AddTickPrerequisiteActor(this);Trails.Add(Trail);
        auto* VaporHost=GetWorld()->SpawnActor<AActor>(GetActorLocation(),FRotator::ZeroRotator);
        auto* Vapor=NewObject<UNiagaraComponent>(VaporHost);VaporHost->AddInstanceComponent(Vapor);VaporHost->SetRootComponent(Vapor);
        Vapor->SetAsset(ColdMist);Vapor->SetAutoActivate(false);Vapor->SetCastShadow(false);Vapor->RegisterComponent();
        Vapor->AddTickPrerequisiteActor(this);Vapors.Add(Vapor);VaporHosts.Add(VaporHost);
    }
    UpdateHover();
    for(const auto& Vapor:Vapors)Vapor->Activate(true);
    for(const auto& Trail:Trails)Trail->Activate(true);
}
void AFPSIceSpikeVolley::UpdateVapor(int32 Index,const FVector& Previous,float Strength)
{
    auto* Vapor=Vapors[Index].Get();auto* Core=Cores[Index].Get();
    Vapor->SetWorldLocation(Flights[Index].Position);
    Vapor->SetVariablePosition(TEXT("User.PreviousPosition"),Previous);
    Vapor->SetVariablePosition(TEXT("User.CurrentPosition"),Flights[Index].Position);
    Vapor->SetVariableVec3(TEXT("User.FlightDirection"),Core->GetForwardVector());
    Vapor->SetVariableVec3(TEXT("User.Side"),Core->GetRightVector());
    Vapor->SetVariableVec3(TEXT("User.Up"),Core->GetUpVector());
    Vapor->SetVariableFloat(TEXT("User.Flight"),bFlying?1.f:0.f);
    Vapor->SetVariableFloat(TEXT("User.Strength"),Strength);
    if(Age>=Flights[Index].NextFluidEnvironment)
    {
        if(auto* Fluid=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>())
        {
            const int32 Wanted=bFlying?8:2;
            const int32 Granted=Fluid->AllocateDetail(Flights[Index].Position,Wanted,false);
            Vapor->SetVariableFloat(TEXT("User.DetailReduction"),1.f-float(Granted)/Wanted);
            Vapor->SetVariableVec3(TEXT("User.Wind"),Fluid->WindAt(Flights[Index].Position)*.25f);
        }
        Flights[Index].NextFluidEnvironment=Age+.10f;
    }
    Vapor->SetVariableFloat(TEXT("User.ReleasePulse"),bFlying?FMath::Clamp(1.f-FlightAge/.16f,0.f,1.f):0.f);
    auto* Trail=Trails[Index].Get();Trail->SetWorldLocation(Flights[Index].Position);
    Trail->SetVariablePosition(TEXT("User.PreviousPosition"),Previous);Trail->SetVariablePosition(TEXT("User.CurrentPosition"),Flights[Index].Position);
    Trail->SetVariableVec3(TEXT("User.FlightDirection"),Core->GetForwardVector());
    Trail->SetVariableVec3(TEXT("User.Side"),Core->GetRightVector());Trail->SetVariableVec3(TEXT("User.Up"),Core->GetUpVector());
    Trail->SetVariableFloat(TEXT("User.Flight"),bFlying?1.f:0.f);Trail->SetVariableFloat(TEXT("User.Strength"),Strength);
}
int32 AFPSIceSpikeVolley::RemainingCount() const
{int32 Count=0;for(const auto& F:Flights)if(F.bActive)++Count;return Count;}
void AFPSIceSpikeVolley::UpdateHover()
{
    if(!Shooter.IsValid())return;
    const auto* Camera=Shooter->FindComponentByClass<UCameraComponent>();
    const FVector Eye=Camera?Camera->GetComponentLocation():Shooter->GetPawnViewLocation();
    const FRotator ViewRotation=Camera?Camera->GetComponentRotation():Shooter->GetViewRotation();
    const FRotationMatrix ViewBasis(ViewRotation);
    const FVector Forward=ViewBasis.GetUnitAxis(EAxis::X),Right=ViewBasis.GetUnitAxis(EAxis::Y),Up=ViewBasis.GetUnitAxis(EAxis::Z);
    // The player camera maintains vertical FOV, using its configured aspect to store horizontal FOV.
    const float TanVertical=Camera?FMath::Tan(FMath::DegreesToRadians(Camera->FieldOfView*.5f))/FMath::Max(.1f,Camera->AspectRatio):FMath::Tan(FMath::DegreesToRadians(37.5f));
    float ViewAspect=Camera?Camera->AspectRatio:16.f/9.f;
    if(const auto* PC=::Cast<APlayerController>(Shooter->GetController()))
    {
        int32 Width=0,Height=0;PC->GetViewportSize(Width,Height);
        if(Width>0&&Height>0)ViewAspect=float(Width)/Height;
    }
    // SM_IceSpike_01..03 are a 54 cm shard along local +X with a 12.2 x 11.0 cm
    // cross-section (engine-authoring.json extent 27 / 6.1 / 5.49). The tip points
    // away from the camera, so the thick base is the nearest and largest silhouette.
    constexpr float MeshHalfLength=27.f,MeshMaxRadius=6.1f;
    // Deeper than the first pass: at 44 cm the base disc alone covered more than half
    // the vertical view, so only the pointed tip could ever reach the frame. Placing
    // the row further out fits the whole 54 cm shard inside the top band instead of
    // having the upper frustum edge cut it ahead of its centre.
    constexpr float ForwardDistance=72.f;
    const float BaseDepth=ForwardDistance-MeshHalfLength;
    // Height of the upper frustum edge at the base's own depth, minus the base radius:
    // the highest point that still keeps the complete shard on screen.
    const float VisibleHeight=BaseDepth*TanVertical-MeshMaxRadius;
    // .8 rather than .72: the melee sword sweeps the right side of the frame, so the wings
    // are allowed to use more of the width before the frame cap compresses them.
    const float HalfRowWidth=ForwardDistance*TanVertical*ViewAspect*.8f;
    // The melee weapon sweeps through the middle of the view, so the row keeps the aim
    // axis clear and fills a left and a right wing instead. Both wings share one slot
    // ladder, so a level-up shard always lands one step further out and same-wing
    // neighbours stay two steps apart - a new count never crowds an existing shard.
    const float GapUnits=FMath::Max(.15f,IceSpikeWingGap.GetValueOnGameThread());
    const float LadderTop=GapUnits+FMath::Max(0,(Flights.Num()-1)/2);
    const float PitchCap=FMath::Max(6.f,IceSpikeSlotSpacing.GetValueOnGameThread());
    const float Spacing=FMath::Min(PitchCap,HalfRowWidth/LadderTop);
    const float WingGap=GapUnits*Spacing;
    const float DriftScale=FMath::Max(0.f,IceSpikeDriftScale.GetValueOnGameThread());
    const float SideDrift=FMath::Min(7.f,Spacing*.34f)*DriftScale;
    // Leaning on a bigger bob must not push the base out of frame, so the amplitude
    // comes off the height: the shard stays whole even at the top of the drift.
    const float VerticalDrift=FMath::Min(5.5f,VisibleHeight*.24f)*DriftScale;
    const float OverheadHeight=FMath::Max(4.f,VisibleHeight-VerticalDrift-IceSpikeHoverDropCM.GetValueOnGameThread());
    float Grow=FMath::Clamp(Age*Cast.CastSpeed/.95f,0.f,1.f);Grow=Grow*Grow*(3-2*Grow);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(IceSpikeHover),false,Shooter.Get());Query.AddIgnoredActor(this);
    for(int32 I=0;I<Flights.Num();++I)
    {
        // Even indices take the left wing, so an odd count keeps its extra shard away
        // from the right-handed melee weapon.
        const float Slot=(I%2==0?-1.f:1.f)*(WingGap+float(I/2)*Spacing);
        const auto& Flight=Flights[I];
        const float DriftX=FMath::PerlinNoise1D(Flight.HoverNoiseSeed.X+Age*Flight.HoverNoiseRate.X)*SideDrift*Grow;
        const float DriftY=FMath::PerlinNoise1D(Flight.HoverNoiseSeed.Y+Age*Flight.HoverNoiseRate.Y)*VerticalDrift*Grow;
        // Slot is already a cm offset from the aim axis (position already includes Spacing),
        // so it is added once here; each spike still meanders independently without orbit or spin.
        FVector Desired=Eye+Forward*ForwardDistance+Right*(Slot+DriftX)+Up*(OverheadHeight+DriftY);
        FHitResult Cover;
        if(GetWorld()->SweepSingleByChannel(Cover,Eye,Desired,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(18),Query))Desired=Cover.Location;
        const FVector Previous=Age==0?Desired:Flights[I].Position;
        Flights[I].Position=Desired;
        auto* Core=Cores[I].Get();Core->SetWorldLocation(Desired);
        FRotator Facing=ViewRotation;Facing.Roll+=I*113.f;
        Core->SetWorldRotation(Facing);
        Core->SetWorldScale3D(FVector::OneVector*FMath::Max(.01f,Grow));
        Core->SetVisibility(!Camera||FVector::DistSquared(Camera->GetComponentLocation(),Desired)>FMath::Square(35.f),true);
        UpdateVapor(I,Previous,Core->IsVisible()?Grow:0.f);
    }
}
void AFPSIceSpikeVolley::SetAimPreviewActive(bool bActive)
{
    bAimPreview=bActive;
    bPreviewLaunchLocked=false;
    if(bActive)PreviewPoints.Reset();
    // Lines carry a short lifetime, so stopping the refresh is enough to clear the preview.
    if(!bActive)FPSMagicPreview::Clear(AimPreviewLines);
}

void AFPSIceSpikeVolley::CommitAimPreview()
{
    if(!bAimPreview||bFlying||bFinished||!Shooter.IsValid())return;
    if(PreviewPoints.IsEmpty())RefreshAimPreview();
    SetAimPreviewActive(false);
    bPreviewLaunchLocked=true;
}

void AFPSIceSpikeVolley::RefreshAimPreview()
{
    if(!Shooter.IsValid())return;
    // One frame of segments only: drop the previous frame so panning the view cannot smear
    // the shard lines across the screen.
    FPSMagicPreview::BeginRefresh(AimPreviewLines,this);
    const FVector AimPoint=FPSMagicPreview::AimPoint(Shooter.Get(),this);
    PreviewAimPoint=AimPoint;
    for(FFlight& F:Flights)
    {
        if(!F.bActive)continue;
        // Same arc Launch() builds: from this shard's hover offset to the shared aim point, then
        // dropping under the cast's gravity.
        const FVector ToAim=AimPoint-F.Position;
        F.LaunchPosition=F.Position;
        F.LaunchVelocity=FPSMagicPreview::LaunchVelocity(F.Position,AimPoint,Cast.Speed,Shooter->GetActorForwardVector());
        F.Remaining=FMath::Min(float(ToAim.Size()),Cast.Range);
        F.bAimEndpoint=ToAim.Size()<Cast.Range;
        // Shared prediction: an already dead body is passed through, walls and living enemies stop it.
        FPSMagicPreview::SamplePath(Shooter.Get(),this,F.LaunchPosition,F.LaunchVelocity,Cast.Gravity,
            F.Remaining,18.f,PreviewPoints);
        FPSMagicPreview::DrawPath(AimPreviewLines,PreviewPoints);
    }
}

void AFPSIceSpikeVolley::LaunchAt(const FVector& AimPoint)
{
    if(bFinished||bFlying||!Shooter.IsValid())return;
    PreviewAimPoint=AimPoint;bPreviewLaunchLocked=true;Launch();
}
void AFPSIceSpikeVolley::Launch()
{
    if(bFinished||bFlying||!Shooter.IsValid())return;
    bNetFlying=true; // 先于弹道写入复制，远端第一时间进入飞行表现
    // The contact callback runs ahead of the volley tick: use this frame's
    // followed positions, not the previous frame or the key-release origins.
    UpdateHover();
    const bool bUsePreview=bPreviewLaunchLocked;
    const FVector AimPoint=bUsePreview?PreviewAimPoint:FPSMagicPreview::AimPoint(Shooter.Get(),this);
    SetAimPreviewActive(false);
    bFlying=true;FlightAge=0;
    for(int32 I=0;I<Flights.Num();++I)
    {
        // Each shard keeps its own hover offset and flies to the shared aim point, so the volley
        // converges on what the crosshair covers. Gravity then bends every arc the same way.
        auto& F=Flights[I];
        const float ToAimDistance=FVector::Distance(AimPoint,F.Position);
        F.Remaining=FMath::Min(ToAimDistance,Cast.Range);F.bAimEndpoint=ToAimDistance<Cast.Range;
        F.LaunchPosition=F.Position;
        F.LaunchVelocity=FPSMagicPreview::LaunchVelocity(F.Position,AimPoint,Cast.Speed,Shooter->GetActorForwardVector());
        F.Direction=F.LaunchVelocity.GetSafeNormal();
        FRotator Facing=F.Direction.Rotation();Facing.Roll=I*113.f;
        Cores[I]->SetWorldLocation(F.Position);Cores[I]->SetWorldRotation(Facing);Cores[I]->SetWorldScale3D(FVector::OneVector);Cores[I]->SetVisibility(true,true);
        auto* Trail=Trails[I].Get();Trail->SetWorldLocation(F.Position);Trail->SetVariablePosition(TEXT("User.PreviousPosition"),F.Position);Trail->SetVariablePosition(TEXT("User.CurrentPosition"),F.Position);
        Trail->SetVariableVec3(TEXT("User.FlightDirection"),F.Direction);Trail->SetVariableFloat(TEXT("User.FlightSpeed"),Cast.Speed);
        UpdateVapor(I,F.Position,1.f);
    }
}
void AFPSIceSpikeVolley::Tick(float Delta)
{
    Super::Tick(Delta);
    // 远端副本：不跑弹道/伤害，复制字段驱动表现壳（位置→网格、存活位→碎裂 FX）。
    if(!HasAuthority())
    {
        ResolveNetInit();
        if(bNetInit)NetPresent(Delta);
        return;
    }
    if(bFinished)return;
    if(!Shooter.IsValid()||!Source.IsValid()){Destroy();return;}
    if(auto* H=Shooter->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead()){Destroy();return;}
    Age+=Delta;
    if(!bFlying)
    {
        if(Age>=Cast.HoverDuration){Destroy();return;}
        UpdateHover();
        if(bAimPreview)RefreshAimPreview();
        // 悬停位置也走复制——远端能看到凝聚在施法者眼前的锥列。
        SyncNetFlights();
        return;
    }
    FlightAge+=Delta;
    auto* M=NetCast::AuthorityModel(Shooter.Get(),GetGameInstance());
    const FVector Gravity(0,0,-Cast.Gravity);
    for(int32 I=0;I<Flights.Num();++I)
    {
        auto& F=Flights[I];if(!F.bActive)continue;
        const FVector Previous=F.Position;
        // Ballistic step: the analytic position comes from the shared launch state, so the drop is
        // frame-rate independent and the preview line reproduces exactly this arc.
        const FVector Next=FPSMagicPreview::LimitStep(Previous,
            F.LaunchPosition+F.LaunchVelocity*FlightAge+.5f*Gravity*FlightAge*FlightAge,F.Remaining);
        const float Step=FVector::Distance(Previous,Next);const FVector End=Next;
        F.Direction=(F.LaunchVelocity+Gravity*FlightAge).GetSafeNormal(UE_SMALL_NUMBER,FVector::ForwardVector);
        Trails[I]->SetVariablePosition(TEXT("User.PreviousPosition"),F.Position);
        FCollisionQueryParams Query(SCENE_QUERY_STAT(IceSpikeFlight),false,Shooter.Get());Query.AddIgnoredActor(this);FHitResult Hit;
        // A body that is already down does not consume a spike: the volley converges on one
        // aim point, so the spikes arriving after the kill fly through the corpse and carry
        // on to whatever stands behind it. Walls and live enemies still stop them.
        bool bBlocked=false;
        for(int32 Pass=0;Pass<8;++Pass)
        {
            bBlocked=GetWorld()->SweepSingleByChannel(Hit,F.Position,End,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(18),Query);
            if(!bBlocked)break;
            const auto* Blocking=IsValid(Hit.GetActor())?Hit.GetActor()->FindComponentByClass<UMonsterCombatComponent>():nullptr;
            if(!Blocking||!Blocking->IsDead())break;
            Query.AddIgnoredActor(Hit.GetActor());
        }
        if(bBlocked)
        {
            const FHitResult First=Hit;
            UWardBreakableGlass::BreakHit(First,F.Direction);
            // Source hit loop settles overlapping contacts before destroying a spike.
            // Limit that cluster to one diameter, independent of frame time; never pierce a wall.
            TSet<AActor*> Settled;
            const FVector ClusterEnd=F.Position+F.Direction*FMath::Min(Step,FVector::Distance(F.Position,First.Location)+36.f);
            do
            {
                AActor* Target=Hit.GetActor();
                if(::Cast<AFPSIceWall>(Target))
                {if(M)M->ApplyIceSpikeHit(Shooter.Get(),Hit,Cast,Rewards);break;}
                if(!Target||!Target->FindComponentByClass<UMonsterCombatComponent>()||Settled.Contains(Target))break;
                Settled.Add(Target);if(M)M->ApplyIceSpikeHit(Shooter.Get(),Hit,Cast,Rewards);
                Query.AddIgnoredActor(Target);
            }
            while(GetWorld()->SweepSingleByChannel(Hit,F.Position,ClusterEnd,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(18),Query));
            F.Position=First.Location;Shatter(I,First.ImpactPoint,First.ImpactNormal,true);
        }
        else
        {
            F.Position=End;F.Remaining-=Step;Cores[I]->SetWorldLocation(End);
            if(F.Remaining<=UE_KINDA_SMALL_NUMBER)Shatter(I,End,-F.Direction,F.bAimEndpoint);
        }
        if(F.bActive)UpdateVapor(I,Previous,1.f);
    }
    for(int32 I=0;I<Flights.Num();++I){Trails[I]->SetWorldLocation(Flights[I].Position);Trails[I]->SetVariablePosition(TEXT("User.CurrentPosition"),Flights[I].Position);}
    SyncNetFlights();
    if(RemainingCount()==0)Destroy();
}
// 服务端把每锥位置/方向/存活写进复制态；远端 OnRep_Spikes 据此摆壳。
void AFPSIceSpikeVolley::SyncNetFlights()
{
    NetPos.SetNum(Flights.Num());NetDir.SetNum(Flights.Num());NetAlive=0;
    for(int32 I=0;I<Flights.Num();++I)
    {
        NetPos[I]=Flights[I].Position;NetDir[I]=Flights[I].Direction;
        if(Flights[I].bActive&&I<32)NetAlive|=1u<<I;
    }
}
void AFPSIceSpikeVolley::Shatter(int32 Index,const FVector& Position,const FVector& Normal,bool bEffect)
{
    Flights[Index].bActive=false;Cores[Index]->SetVisibility(false,true);Trails[Index]->Deactivate();
    // Let already emitted condensation dissipate after its spike/volley disappears.
    auto* Vapor=Vapors[Index].Get();Vapor->SetVariableFloat(TEXT("User.Strength"),0.f);
    if(VaporHosts[Index].IsValid())VaporHosts[Index]->SetLifeSpan(.85f);
    if(!bEffect)return;
    if(auto* Fluid=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>())Fluid->EmitColdImpact(Position,Normal);
    if(ImpactFX)UGameplayStatics::SpawnEmitterAtLocation(GetWorld(),ImpactFX,Position,Normal.Rotation(),FVector(.7f),true,EPSCPoolMethod::AutoRelease);
    if(ShardMesh&&IceMaterial)if(auto* F=GetWorld()->SpawnActor<AFPSIceSpikeFragments>(Position,FRotator::ZeroRotator))F->Setup(ShardMesh,IceMaterial,Normal);
    const double Now=GetWorld()->GetTimeSeconds();
    if(ImpactSound&&Now-LastSound>=.09){UGameplayStatics::PlaySoundAtLocation(this,ImpactSound,Position,.65f,FMath::FRandRange(.94f,1.06f));LastSound=Now;}
    UAISense_Hearing::ReportNoiseEvent(this,Position,.4f,Shooter.Get(),900,TEXT("IceSpike"));
}
void AFPSIceSpikeVolley::Finish()
{
    if(bFinished)return;bFinished=true;
    if(!Shooter.IsValid())return;
    // 权威模型：服务端结算远端玩家时取影子档案，主机/单机回退本地单例。
    if(auto* M=NetCast::AuthorityModel(Shooter.Get(),GetGameInstance()))M->FinishIceSpikeCast(Rewards);
    const auto* Health=Shooter->FindComponentByClass<UFPSCombatHealthComponent>();
    if(bFlying&&Health&&!Health->IsDead()&&(Cast.bGrantChain||Cast.CastHasteStacks>0))
    {auto* Status=UCombatStatusFormula::GetOrAdd(Shooter.Get());if(Cast.bGrantChain)Status->AddChainSpell();Status->AddHaste(Cast.CastHasteStacks,Cast.CastHasteDuration);}
    if(Source.IsValid())Source->VolleyFinished(this);Source.Reset();
}

// ══ 远端副本（非权威）：素材自载 + 复制字段驱动的表现壳 ═════════════════
void AFPSIceSpikeVolley::ResolveNetInit()
{
    if(bNetInit||NetCount<=0||!IsValid(NetShooter.Get())||!IsValid(NetSource.Get()))return;
    // 与组件 BeginPlay 同口径的素材自载——远端副本不跑 Prepare，资产各自现拉。
    TArray<TObjectPtr<UStaticMesh>> Meshes;
    for(int32 I=1;I<=3;++I)Meshes.Add(LoadObject<UStaticMesh>(nullptr,*FString::Printf(TEXT("/Game/Skills/IceSpike/FrostV2/SM_IceSpike_%02d.SM_IceSpike_%02d"),I,I)));
    ShardMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Skills/IceSpike/SM_IceShard.SM_IceShard"));
    IceMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Skills/IceSpike/FrostV2/M_IceHeart.M_IceHeart"));
    auto* ShellMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Skills/IceSpike/FrostV2/M_IceShell.M_IceShell"));
    ImpactFX=LoadObject<UParticleSystem>(nullptr,TEXT("/Game/Skills/IceSpike/P_IceSpikeImpact.P_IceSpikeImpact"));
    ImpactSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Skills/IceSpike/S_IceImpact.S_IceImpact"));
    auto* MotesAsset=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Skills/IceSpike/FrostV2/NS_FrostCrystals.NS_FrostCrystals"));
    auto* ColdMistAsset=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Skills/IceSpike/FrostV2/NS_ColdMist.NS_ColdMist"));
    if(Meshes.Contains(nullptr)||!ShardMesh||!IceMaterial||!ShellMaterial||!MotesAsset||!ColdMistAsset)return;

    Shooter=NetShooter;Source=NetSource;NetAliveLocal=NetAlive;
    Cast.Count=NetCount;Cast.CastSpeed=NetCastSpeed;Cast.Speed=NetSpeed;Cast.Gravity=NetGravity;Cast.HoverDuration=NetHoverDuration;
    Flights.SetNum(NetCount);
    for(int32 I=0;I<NetCount;++I)
    {
        Flights[I].bActive=(NetAlive>>I)&1u;
        if(I<NetPos.Num())Flights[I].Position=NetPos[I];
        if(I<NetDir.Num())Flights[I].Direction=NetDir[I];
        auto* Spike=Meshes[I%Meshes.Num()].Get();
        auto* Core=AddIceMesh(this,Spike,ShellMaterial);Core->SetCastShadow(false);Cores.Add(Core);
        auto* Heart=AddIceMesh(this,Spike,IceMaterial);Heart->AttachToComponent(Core,FAttachmentTransformRules::KeepRelativeTransform);
        Heart->SetRelativeScale3D(FVector(.965f,.78f,.78f));Heart->SetCastShadow(false);Hearts.Add(Heart);
        auto* Trail=NewObject<UNiagaraComponent>(this);AddInstanceComponent(Trail);Trail->SetupAttachment(GetRootComponent());Trail->SetAsset(MotesAsset);Trail->SetAutoActivate(false);Trail->SetCastShadow(false);Trail->RegisterComponent();Trail->AddTickPrerequisiteActor(this);Trails.Add(Trail);
        auto* VaporHost=GetWorld()->SpawnActor<AActor>(GetActorLocation(),FRotator::ZeroRotator);
        auto* Vapor=NewObject<UNiagaraComponent>(VaporHost);VaporHost->AddInstanceComponent(Vapor);VaporHost->SetRootComponent(Vapor);
        Vapor->SetAsset(ColdMistAsset);Vapor->SetAutoActivate(false);Vapor->SetCastShadow(false);Vapor->RegisterComponent();
        Vapor->AddTickPrerequisiteActor(this);Vapors.Add(Vapor);VaporHosts.Add(VaporHost);
    }
    AddTickPrerequisiteActor(Shooter.Get());
    for(const auto& Vapor:Vapors)Vapor->Activate(true);
    for(const auto& Trail:Trails)Trail->Activate(true);
    bNetInit=true;
    // 施法者本机：认领成 Active——发射队列/取消链照常读它。
    if(Source.IsValid()&&Shooter->IsLocallyControlled())Source->AdoptNetVolley(this);
}
void AFPSIceSpikeVolley::OnRep_Spikes()
{
    if(!bNetInit)return;
    for(int32 I=0;I<Flights.Num()&&I<NetPos.Num();++I)
    {
        Flights[I].Position=NetPos[I];
        if(I<NetDir.Num())Flights[I].Direction=NetDir[I];
    }
    const uint32 Was=NetAliveLocal;NetAliveLocal=NetAlive;
    for(int32 I=0;I<Flights.Num()&&I<32;++I)
        if(((Was>>I)&1u)&&!((NetAlive>>I)&1u)){Flights[I].bActive=false;NetShatter(I,NetPos[I]);}
}
void AFPSIceSpikeVolley::NetShatter(int32 Index,const FVector& Position)
{
    if(Index>=Cores.Num())return;
    Cores[Index]->SetVisibility(false,true);if(Index<Trails.Num())Trails[Index]->Deactivate();
    if(Index<Vapors.Num())Vapors[Index]->SetVariableFloat(TEXT("User.Strength"),0.f);
    if(Index<VaporHosts.Num()&&VaporHosts[Index].IsValid())VaporHosts[Index]->SetLifeSpan(.85f);
    if(auto* Fluid=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>())Fluid->EmitColdImpact(Position,-Flights[Index].Direction);
    if(ImpactFX)UGameplayStatics::SpawnEmitterAtLocation(GetWorld(),ImpactFX,Position,(-Flights[Index].Direction).Rotation(),FVector(.7f),true,EPSCPoolMethod::AutoRelease);
    if(ShardMesh&&IceMaterial)if(auto* F=GetWorld()->SpawnActor<AFPSIceSpikeFragments>(Position,FRotator::ZeroRotator))F->Setup(ShardMesh,IceMaterial,-Flights[Index].Direction);
    const double Now=GetWorld()->GetTimeSeconds();
    if(ImpactSound&&Now-LastSound>=.09){UGameplayStatics::PlaySoundAtLocation(this,ImpactSound,Position,.65f,FMath::FRandRange(.94f,1.06f));LastSound=Now;}
}
void AFPSIceSpikeVolley::NetPresent(float Delta)
{
    NetAge+=Delta;
    const auto* Camera=IsValid(NetShooter.Get())?NetShooter->FindComponentByClass<UCameraComponent>():nullptr;
    const float Grow=FMath::Clamp(NetAge*NetCastSpeed/.95f,0.f,1.f);
    const float Scale=bNetFlying?1.f:Grow*Grow*(3-2*Grow);
    for(int32 I=0;I<Flights.Num();++I)
    {
        if(I>=Cores.Num())break;
        auto* Core=Cores[I].Get();
        Core->SetWorldLocation(Flights[I].Position);
        FRotator Facing=Flights[I].Direction.Rotation();Facing.Roll+=I*113.f;
        Core->SetWorldRotation(Facing);Core->SetWorldScale3D(FVector::OneVector*FMath::Max(.01f,Scale));
        Core->SetVisibility(Flights[I].bActive&&(!Camera||FVector::DistSquared(Camera->GetComponentLocation(),Flights[I].Position)>FMath::Square(35.f)),true);
        if(Flights[I].bActive&&I<Trails.Num()&&I<Vapors.Num())
        {
            auto* Trail=Trails[I].Get();auto* Vapor=Vapors[I].Get();
            Trail->SetWorldLocation(Flights[I].Position);
            Trail->SetVariablePosition(TEXT("User.CurrentPosition"),Flights[I].Position);
            Trail->SetVariableVec3(TEXT("User.FlightDirection"),Flights[I].Direction);
            Trail->SetVariableFloat(TEXT("User.Flight"),bNetFlying?1.f:0.f);
            Trail->SetVariableFloat(TEXT("User.FlightSpeed"),NetSpeed);
            Vapor->SetWorldLocation(Flights[I].Position);
            Vapor->SetVariablePosition(TEXT("User.CurrentPosition"),Flights[I].Position);
            Vapor->SetVariableVec3(TEXT("User.FlightDirection"),Core->GetForwardVector());
            Vapor->SetVariableVec3(TEXT("User.Side"),Core->GetRightVector());
            Vapor->SetVariableVec3(TEXT("User.Up"),Core->GetUpVector());
            Vapor->SetVariableFloat(TEXT("User.Flight"),bNetFlying?1.f:0.f);
            Vapor->SetVariableFloat(TEXT("User.Strength"),Scale);
        }
    }
    if(bAimPreview)RefreshAimPreview();
}
void AFPSIceSpikeVolley::EndPlay(EEndPlayReason::Type Reason)
{
    for(int32 I=0;I<Vapors.Num();++I)if(VaporHosts[I].IsValid())
    {
        Vapors[I]->SetVariableFloat(TEXT("User.Strength"),0.f);VaporHosts[I]->SetLifeSpan(.85f);
    }
    Finish();Super::EndPlay(Reason);
}

AFPSIceSpikeFragments::AFPSIceSpikeFragments()
{PrimaryActorTick.bCanEverTick=true;SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("FragmentRoot")));}
void AFPSIceSpikeFragments::Setup(UStaticMesh* Mesh,UMaterialInterface* Material,const FVector& Normal)
{
    for(int32 I=0;I<12;++I)
    {
        auto* C=AddIceMesh(this,Mesh,Material);C->SetRelativeScale3D(FVector(FMath::FRandRange(.25f,.65f)));C->SetRelativeRotation(FMath::VRand().Rotation());
        Shards.Add(C);Velocities.Add((Normal*.75f+FMath::VRand()).GetSafeNormal()*FMath::FRandRange(100.f,240.f));Spins.Add(FRotator(90+I*31,180-I*17,80+I*11));
    }
    SetLifeSpan(.65f);
}
void AFPSIceSpikeFragments::Tick(float Delta)
{
    Super::Tick(Delta);Age+=Delta;
    for(int32 I=0;I<Shards.Num();++I)
    {
        auto* C=Shards[I].Get();C->AddWorldOffset(Velocities[I]*Delta-FVector(0,0,375.f*Delta*Delta));Velocities[I].Z-=750.f*Delta;
        C->AddLocalRotation(Spins[I]*Delta);
        if(Age>.42f)C->SetVisibility(false);
    }
}
