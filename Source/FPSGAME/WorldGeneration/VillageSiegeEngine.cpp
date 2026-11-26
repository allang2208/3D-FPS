#include "VillageSiegeEngine.h"
#include "VillageSiegeUpgrades.h"
#include "TemperateHillsWorld.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "VillageSiegeUseTargets.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Monsters/WildlifeSubsystem.h"
#include "../Monsters/WolfMonster.h"
#include "../Weapons/FPSMeleeLightningComponent.h"
#include "Components/SphereComponent.h"
#include "Components/AudioComponent.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundWave.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "Engine/OverlapResult.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/ProjectileMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"
#include "TimerManager.h"

namespace
{
    const FVector Hinge(0,0,110);
    const FVector LimbRoot(67,0,147);
    const FVector Nock(-140,0,97);
    const FVector BoltRest(81,0,153);
    const FVector ArmPivot(0,0,305);
    const FVector WeightPivot(66.25,0,365.92);
    const FVector SlingPin(-273,0,72);
    const FVector PouchSeat(-58,0,-20);
    constexpr double BoltAngle = 17.745;
    constexpr double WinchStart=1.03,WinchEnd=3.08;
    constexpr double TrebuchetReleaseAt=1.08;
    constexpr double TrebuchetReloadSeconds=10.;
    constexpr double TrebuchetCycle=TrebuchetReleaseAt+TrebuchetReloadSeconds;
    constexpr float HaulPlaybackRate=.72f;
    // Work backwards from readiness to keep the four recorded hauling strokes and seating knock in sync.
    constexpr double HaulTime(double Original) { return TrebuchetCycle-(7.8-Original)/HaulPlaybackRate; }
    constexpr double TrebuchetReturnStart=HaulTime(2.58), TrebuchetArmRest=HaulTime(6.85);
    constexpr double TrebuchetStoneApproach=HaulTime(6.6), TrebuchetStoneSeated=HaulTime(7.3);
    const FSoftObjectPath StoneImpactFX(TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/SiegeEngines/FX/NS_TrebuchetStoneImpact.NS_TrebuchetStoneImpact"));
    constexpr TCHAR StoneImpactPath[]=TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/SiegeEngines/Audio/S_TrebuchetImpact.S_TrebuchetImpact");

    // Short impulses, secondary settling and a longer recovery each get their own curve.
    double Ease(double T,double A,double B)
    {
        const double F=FMath::Clamp((T-A)/(B-A),0.,1.);
        return F*F*(3.-2.*F);
    }
    FRotator ArmPose(double T)
    {
        // Release occurs inside the fast stroke. The arm decelerates beyond it.
        return FRotator(-133.*Ease(T,.64,1.31)+15.*Ease(T,1.31,1.81)
            -4.*Ease(T,1.81,2.23)+122.*Ease(T,TrebuchetReturnStart,TrebuchetArmRest),0,0);
    }
    FTransform SlingPose(double T,const FRotator& Arm)
    {
        const double Swing=Arm.Pitch*.85-54.*Ease(T,.95,1.50)+70.*Ease(T,1.50,2.10)
            -28.*Ease(T,2.10,2.58)+12.*Ease(T,2.58,3.3);
        return FTransform(FRotator(Swing,0,0),ArmPivot+Arm.RotateVector(SlingPin-ArmPivot));
    }
    bool IsThreat(AActor* Actor,AActor* Engine)
    {
        auto* Pawn=Cast<APawn>(Actor);
        if(!Pawn || Pawn->IsHidden() || Pawn->ActorHasTag(TEXT("NPC")) ||
            Pawn->ActorHasTag(TEXT("WildlifeSpawned")) || !UFPSMeleeLightningComponent::IsEnemy(Pawn,Engine))
            return false;
        return !Pawn->IsA<AWolfMonster>() || !UWildlifeSubsystem::IsCatalogClass(FSoftObjectPath(Pawn->GetClass()));
    }
    float GravityScale(bool bStone){return bStone?1.35f:.42f;}
    double FlightTime(bool bStone,const FVector& Start,const FVector& End)
    {
        const double Distance=FVector::Dist2D(Start,End);
        return bStone?FMath::Clamp(Distance/2200.,1.65,3.55):FMath::Clamp(Distance/4600.,.16,1.5);
    }
    FVector LaunchVelocity(UWorld* World,bool bStone,const FVector& Start,const FVector& End)
    {
        const double Seconds=FlightTime(bStone,Start,End);
        return (End-Start)/Seconds - FVector(0,0,.5*World->GetGravityZ()*GravityScale(bStone)*Seconds);
    }
}

FSoftObjectPath AVillageSiegeEngine::MeshAsset(const TCHAR* Suffix)
{
    return FSoftObjectPath(FString::Printf(TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/SiegeEngines/SM_%s.SM_%s"),Suffix,Suffix));
}

AVillageSiegeEngine::AVillageSiegeEngine()
{
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.bStartWithTickEnabled=false;
    Carriage=CreateDefaultSubobject<USceneComponent>(TEXT("Carriage"));
    Carriage->SetupAttachment(RootComponent);
}

double AVillageSiegeEngine::Clock() const
{
    const auto* State=GetWorld()->GetGameState();
    return State?State->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
}

void AVillageSiegeEngine::BeginPlay()
{
    Super::BeginPlay();
    GetWorld()->GetSubsystem<UVillageSiegeUseTargets>()->Register(*this);
    if(HasAuthority())
        GetWorldTimerManager().SetTimer(SearchTimer,this,&AVillageSiegeEngine::FindTarget,.85f,true,.15f+FMath::FRand()*.6f);
    OnRep_Shot();
}

void AVillageSiegeEngine::EndPlay(const EEndPlayReason::Type Reason)
{
    if(auto* Targets=GetWorld()->GetSubsystem<UVillageSiegeUseTargets>())Targets->Remove(*this);
    Super::EndPlay(Reason);
}

void AVillageSiegeEngine::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AVillageSiegeEngine,Shot);
    DOREPLIFETIME(AVillageSiegeEngine,OperatorPawn);
    DOREPLIFETIME(AVillageSiegeEngine,ManualBearing);
}

void AVillageSiegeEngine::AddPart(const TCHAR* Key,const TCHAR* Suffix)
{
    auto* Mesh=Cast<UStaticMesh>(MeshAsset(Suffix).TryLoad());
    if(!Mesh)return;
    auto* Part=NewObject<UStaticMeshComponent>(this,FName(Key));
    AddInstanceComponent(Part);
    Part->SetupAttachment(Carriage);
    Part->SetStaticMesh(Mesh);
    Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Part->SetGenerateOverlapEvents(false);
    Part->SetCanEverAffectNavigation(false);
    Part->RegisterComponent();
    Parts.Add(Key,Part);
}

void AVillageSiegeEngine::OnRep_Setup()
{
    if(MeshPath.IsNull())return;
    bStone=MeshPath==MeshAsset(TEXT("TrebuchetBase"));
    if(bStone && Masonry->GetAttachParent()!=Carriage)
        Masonry->AttachToComponent(Carriage,FAttachmentTransformRules::KeepRelativeTransform);
    if(bStone && GetNetMode()!=NM_DedicatedServer && !StoneImpactFXHandle.IsValid())
        StoneImpactFXHandle=UAssetManager::GetStreamableManager().RequestAsyncLoad(StoneImpactFX);
    Super::OnRep_Setup();
    if(GetNetMode()==NM_DedicatedServer || !Parts.IsEmpty())return;
    SetUpSiegeAudio();
    if(bStone)
    {
        AddPart(TEXT("Arm"),TEXT("TrebuchetArm"));
        AddPart(TEXT("Weight"),TEXT("TrebuchetWeight"));
        AddPart(TEXT("Sling"),TEXT("TrebuchetSling"));
        AddPart(TEXT("Round"),TEXT("TrebuchetStone"));
    }
    else
    {
        for(const TCHAR* Name:{TEXT("Stock"),TEXT("LimbL"),TEXT("LimbR"),TEXT("StringL"),TEXT("StringR"),TEXT("Windlass"),TEXT("Bolt")})
            AddPart(Name,*(FString(TEXT("Ballista"))+Name));
    }
    ApplyHealth();
    OnRep_Shot();
}

void AVillageSiegeEngine::ApplyHealth()
{
    Super::ApplyHealth();
    Carriage->SetVisibility(GetHealth()>0.f,true);
    if(GetHealth()<=0.f)
    {
        SetActorTickEnabled(false);
        UpdateSiegeAudio(0.);
        if(HasAuthority())
        {
            GetWorldTimerManager().ClearTimer(ReleaseTimer);
            if(Shot.Started>=0.)
            {
                FlushNetDormancy();
                Shot.Started=-1.;
                ForceNetUpdate();
            }
            Tracked.Reset();
        }
    }
    else if(!MeshPath.IsNull())Pose(Shot.Started>=0.?Clock()-Shot.Started:0.);
}

void AVillageSiegeEngine::PresentCollapse(const FVector& Direction,int32 NoiseSeed,float Travel)
{
    // These are machines. Their destroyed state clears the mechanism from the repair site.
    Carriage->SetVisibility(false,true);
}

void AVillageSiegeEngine::SetUpSiegeAudio()
{
    if(TensionAudio)return;
    auto Add=[this](const TCHAR* Name,FVector Offset,float Near,float Far)
    {
        const FString Path=FString::Printf(TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/SiegeEngines/Audio/%s.%s"),Name,Name);
        auto* Audio=NewObject<UAudioComponent>(this,FName(Name));
        AddInstanceComponent(Audio);
        Audio->bAutoActivate=false;
        Audio->bStopWhenOwnerDestroyed=true;
        Audio->bOverrideAttenuation=true;
        auto& Range=Audio->AttenuationOverrides;
        Range.bAttenuate=true;
        Range.bSpatialize=true;
        Range.DistanceAlgorithm=EAttenuationDistanceModel::NaturalSound;
        Range.AttenuationShapeExtents=FVector(Near,0.,0.);
        Range.FalloffDistance=Far-Near;
        Audio->SetupAttachment(Carriage);
        Audio->SetRelativeLocation(Offset);
        Audio->SetSound(LoadObject<USoundWave>(nullptr,*Path));
        Audio->RegisterComponent();
        return Audio;
    };
    if(bStone)
    {
        TensionAudio=Add(TEXT("S_TrebuchetWindup"),WeightPivot,320.f,3100.f);
        ReleaseAudio=Add(TEXT("S_TrebuchetRelease"),ArmPivot,520.f,7800.f);
        ReloadAudio=Add(TEXT("S_TrebuchetReload"),SlingPin+PouchSeat,280.f,2500.f);
        ReloadAudio->SetPitchMultiplier(HaulPlaybackRate);
        return;
    }
    TensionAudio=Add(TEXT("S_BallistaTension"),LimbRoot-Hinge,220.f,2400.f);
    ReleaseAudio=Add(TEXT("S_BallistaRelease"),BoltRest-Hinge,420.f,6200.f);
    ReloadAudio=Add(TEXT("S_BallistaWindlass"),FVector(-149.,0.,84.)-Hinge,200.f,2000.f);
}

void AVillageSiegeEngine::UpdateSiegeAudio(double Elapsed)
{
    if(!TensionAudio)return;
    if(GetHealth()<=0.f || Shot.Started<0.)
    {
        if(AudioShotStart>=0.)
        {
            TensionAudio->Stop();
            ReleaseAudio->Stop();
            ReloadAudio->Stop();
            AudioShotStart=-1.;
        }
        return;
    }
    if(AudioShotStart!=Shot.Started)
    {
        AudioShotStart=Shot.Started;
        NextSound=ESiegeSoundPhase::Tension;
        ReloadAudio->Stop();
    }
    if(NextSound==ESiegeSoundPhase::Tension)
    {
        NextSound=ESiegeSoundPhase::Release;
        const double WindupEnd=bStone ? ReleaseAt() : .51;
        if(!Shot.bReleased && Elapsed<WindupEnd)TensionAudio->Play(Elapsed);
    }
    if(!Shot.bReleased)return;
    if(NextSound==ESiegeSoundPhase::Release)
    {
        NextSound=ESiegeSoundPhase::Reload;
        TensionAudio->Stop();
        // Preserve the initial crack on delivery, but never replay an old release for a late joiner.
        if(Elapsed<ReleaseAt()+.28)ReleaseAudio->Play();
    }
    Elapsed=AnimationTime(Elapsed);
    const double ReloadStart=bStone ? TrebuchetReturnStart : WinchStart;
    if(NextSound==ESiegeSoundPhase::Reload && Elapsed>=ReloadStart)
    {
        NextSound=ESiegeSoundPhase::Done;
        const double ReloadEnd=bStone ? HaulTime(7.36) : WinchEnd;
        if(Elapsed<ReloadEnd)
        {
            const float BaseRate=bStone?HaulPlaybackRate:1.f;
            ReloadAudio->SetPitchMultiplier(BaseRate*VillageSiegeUpgrades::Value(bStone,VillageSiegeUpgrades::Reload,0)/(Duration()-ReleaseAt()));
            ReloadAudio->Play((Elapsed-ReloadStart)*BaseRate);
        }
    }
}

void AVillageSiegeEngine::OnRep_Shot()
{
    const double T=Shot.Started>=0.?FMath::Max(0.,Clock()-Shot.Started):0.;
    UpdateSiegeAudio(T);
    if(GetHealth()<=0.f || MeshPath.IsNull())return;
    Pose(T);
    SetActorTickEnabled(Shot.Started>=0. && T<Duration());
}

void AVillageSiegeEngine::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    const double T=FMath::Max(0.,Clock()-Shot.Started);
    UpdateSiegeAudio(T);
    Pose(T);
    if(T>=Duration() || GetHealth()<=0.f)SetActorTickEnabled(false);
}

void AVillageSiegeEngine::Pose(double T)
{
    T=AnimationTime(T);
    if(GetHealth()<=0.f)return;
    // Lock the bearing through release. Both the visible rig and its chassis collision use this pivot.
    const bool FollowSight=(IsOccupied() || LocalSightBearing.IsSet()) && (Shot.Started<0. || T>=ReleaseAt());
    const FRotator Aim(Shot.Pitch,Shot.Yaw,0.);
    const double Turn=Shot.Started<0.?1.:Ease(T,0.,.44);
    const FRotator Facing=FollowSight?LocalSightBearing.Get(ManualBearing):
        Shot.TraverseFrom+(Aim-Shot.TraverseFrom).GetNormalized()*Turn;
    Carriage->SetRelativeLocationAndRotation(bStone?FVector::ZeroVector:Hinge,Facing);
    auto Set=[this](FName Key,const FVector& Pos,const FRotator& Rot=FRotator::ZeroRotator,
        FVector Scale=FVector::OneVector,bool Visible=true)
    {
        const FTransform Local(Rot,Pos,Scale);
        if(Visible)UsePartPoses.FindOrAdd(Key)=Local;
        else UsePartPoses.Remove(Key);
        if(auto* Part=Parts.FindRef(Key).Get())
        {
            Part->SetRelativeTransform(Local);
            if(Part->IsVisible()!=Visible)Part->SetVisibility(Visible);
        }
    };
    if(bStone)
    {
        // The counterweight follows its hinge after the arm reverses.
        const double Swing=17.*Ease(T,.78,1.19)-29.*Ease(T,1.19,1.77)+18.*Ease(T,1.77,2.31)-6.*Ease(T,2.31,3.0);
        const FRotator Arm=ArmPose(T);
        const FTransform Sling=SlingPose(T,Arm);
        Set(TEXT("Sling"),Sling.GetLocation(),Sling.Rotator());
        Set(TEXT("Arm"),ArmPivot,Arm);
        Set(TEXT("Weight"),ArmPivot+Arm.RotateVector(WeightPivot-ArmPivot),FRotator(Swing,0,0));
        const double Reload=Ease(T,TrebuchetStoneApproach,TrebuchetStoneSeated);
        Set(TEXT("Round"),Sling.TransformPosition(PouchSeat)+FVector(0,0,29*(1.-Reload)*(T>=TrebuchetStoneApproach?1.:0.)),
            FRotator::ZeroRotator,FVector::OneVector,T<ReleaseAt() || T>=TrebuchetStoneApproach);
        return;
    }
    const double Stroke=Ease(T,.525,.58)-.085*Ease(T,.58,.665)+.085*Ease(T,.665,.79)-Ease(T,WinchStart,WinchEnd);
    const double Kick=Ease(T,.53,.60)-Ease(T,.60,.94);
    const FVector Shift= -Hinge+FVector(-7.*Kick,0,0);
    Set(TEXT("Stock"),Shift);
    Set(TEXT("Windlass"),Shift+FVector(-149,0,84),FRotator(360.*Ease(T,WinchStart,WinchEnd),0,0));
    const FVector Cord=Nock+FVector(142.,0,45.)*Stroke;
    for(int32 Side:{-1,1})
    {
        const FRotator Flex(0,Side*-7.*Stroke,0);
        const FVector TipAtRest(21,Side*96,139);
        const FVector Tip=LimbRoot+Flex.RotateVector(TipAtRest-LimbRoot);
        const FVector CordToTip=Tip-Cord;
        Set(Side>0?TEXT("LimbR"):TEXT("LimbL"),Shift+LimbRoot,Flex);
        Set(Side>0?TEXT("StringR"):TEXT("StringL"),Shift+Cord,CordToTip.Rotation(),
            FVector(CordToTip.Size()/(TipAtRest-Nock).Size(),1,1));
    }
    const double Reload=Ease(T,3.08,3.58);
    const FVector BoltTravel=T<ReleaseAt()?FVector(142,0,45)*Stroke:FVector(-40,0,16)*(1.-Reload);
    Set(TEXT("Bolt"),Shift+BoltRest+BoltTravel,FRotator(BoltAngle,0,0),FVector::OneVector,T<ReleaseAt() || T>=3.08);
}

FVector AVillageSiegeEngine::ReleaseOrigin(const FVillageSiegeShot& Plan) const
{
    const FVector Local=bStone?FRotator(0.,Plan.Yaw,0.).RotateVector(SlingPose(ReleaseAt(),ArmPose(ReleaseAt())).TransformPosition(PouchSeat)):
        Hinge+FRotator(Plan.Pitch,Plan.Yaw,0).RotateVector(BoltRest+FVector(136.,0,45.)-Hinge);
    return GetActorTransform().TransformPosition(Local);
}

uint16 AVillageSiegeEngine::CurrentRanks() const
{
    const auto* Village=Cast<ATemperateHillsWorld>(GetOwner());
    return Village ? Village->GetSiegeRanks() : 0;
}

double AVillageSiegeEngine::Range() const
{
    return VillageSiegeUpgrades::Installed(CurrentRanks(),bStone,VillageSiegeUpgrades::Reach);
}

double AVillageSiegeEngine::BlastRadius() const
{
    return VillageSiegeUpgrades::Installed(CurrentRanks(),true,VillageSiegeUpgrades::Special);
}

double AVillageSiegeEngine::Duration() const
{
    return ReleaseAt()+VillageSiegeUpgrades::Installed(Shot.UpgradeRanks,bStone,VillageSiegeUpgrades::Reload);
}

double AVillageSiegeEngine::AnimationTime(double Elapsed) const
{
    if(Elapsed<=ReleaseAt())return Elapsed;
    return ReleaseAt()+(Elapsed-ReleaseAt())*VillageSiegeUpgrades::Value(bStone,VillageSiegeUpgrades::Reload,0)/(Duration()-ReleaseAt());
}

double AVillageSiegeEngine::ReleaseAt() const
{
    return bStone?TrebuchetReleaseAt:.58;
}

bool AVillageSiegeEngine::GetReloadProgress(float& Fraction) const
{
    if(!Shot.bReleased || Shot.Started<0.)return false;
    const double Remaining=Shot.Started+Duration()-Clock();
    if(Remaining<=-.75)return false;
    Fraction=Remaining<=0.?1.f:FMath::Min(.99999f,float(FMath::Max(0.,1.-Remaining/(Duration()-ReleaseAt()))));
    return true;
}

double AVillageSiegeEngine::ReloadRemaining() const
{
    return Shot.Started<0.?0.:FMath::Max(0.,Shot.Started+Duration()-Clock());
}

bool AVillageSiegeEngine::CanOperate() const
{
    const auto* Carrier=Cast<AVoxelBuildPrefabActor>(GetAttachParentActor());
    return GetHealth()>0.f && Carrier && !Carrier->IsFalling();
}

void AVillageSiegeEngine::CancelWindup()
{
    if(!GetWorldTimerManager().IsTimerActive(ReleaseTimer))return;
    GetWorldTimerManager().ClearTimer(ReleaseTimer);
    FlushNetDormancy();
    Tracked.Reset();
    Shot.Started=-1.;
    OnRep_Shot();
    ForceNetUpdate();
}

bool AVillageSiegeEngine::Claim(APawn* Pawn)
{
    if(!HasAuthority() || !Pawn || IsOccupied() || !CanOperate())return false;
    Pose(Shot.Started<0.?0.:FMath::Max(0.,Clock()-Shot.Started));
    const FRotator Current=Carriage->GetRelativeRotation();
    CancelWindup();
    FlushNetDormancy();
    ManualBearing=FRotator(bStone?0.:Current.Pitch,Current.Yaw,0.);
    OperatorPawn=Pawn;
    OnRep_Shot();
    ForceNetUpdate();
    return true;
}

FRotator AVillageSiegeEngine::ClaimedAim() const
{
    return FRotator(bStone?0.:FMath::Clamp(ManualBearing.Pitch+BoltAngle,-48.,40.),ManualBearing.Yaw,0.);
}

void AVillageSiegeEngine::Vacate(APawn* Pawn)
{
    if(!HasAuthority() || OperatorPawn!=Pawn)return;
    if(bManualShot)CancelWindup();
    FlushNetDormancy();
    Shot.TraverseFrom=ManualBearing;
    Shot.Yaw=ManualBearing.Yaw;
    Shot.Pitch=ManualBearing.Pitch;
    OperatorPawn=nullptr;
    ManualBearing=FRotator::ZeroRotator;
    OnRep_Shot();
    ForceNetUpdate();
}

bool AVillageSiegeEngine::MakePlan(const FVector& Point,FVillageSiegeShot& Plan) const
{
    const FVector Eye=GetActorLocation()+FVector(0,0,bStone?305.:145.);
    const double Yaw=GetActorTransform().InverseTransformVectorNoScale(Point-Eye).Rotation().Yaw;
    Plan.Aim=Point;
    Plan.Yaw=Yaw;
    if(!bStone)
    {
        for(int32 Pass=0;Pass<2;++Pass)
        {
            const FVector Velocity=LaunchVelocity(GetWorld(),false,ReleaseOrigin(Plan),Point);
            Plan.Pitch=GetActorTransform().InverseTransformVectorNoScale(Velocity).Rotation().Pitch-BoltAngle;
            if(Plan.Pitch< -66. || Plan.Pitch>23.)return false;
        }
    }
    return true;
}

void AVillageSiegeEngine::ManualSight(const APawn* Pawn,float Yaw,float Elevation,FVillageSiegeSight& Sight,bool Preview) const
{
    Sight.Arc.Reset();
    Sight.Plan=FVillageSiegeShot{};
    Sight.HasImpact=false;
    Sight.CanFire=false;
    if(!FMath::IsFinite(Yaw)||!FMath::IsFinite(Elevation))return;
    const FTransform Frame=GetActorTransform();
    const FVector Eye=GetActorLocation()+FVector(0,0,bStone?305.:145.);
    const FRotator Horizontal(0.,ResolveAimYaw(Yaw),0.);
    const FVector Forward=Frame.TransformVectorNoScale(Horizontal.Vector());
    FCollisionQueryParams Query(SCENE_QUERY_STAT(VillageSiegeManualSight),false,this);
    Query.AddIgnoredActor(GetAttachParentActor());
    Query.AddIgnoredActor(Pawn);
    FHitResult Hit;
    FVector Point;
    bool Surface=true;
    if(bStone)
    {
        const double Fraction=FMath::Clamp((Elevation+28.)/52.,0.,1.);
        const double Distance=FMath::Lerp(MinimumRange()+5.,Range()-5.,Fraction);
        const FVector Column=Eye+Forward*Distance;
        Surface=GetWorld()->LineTraceSingleByChannel(Hit,Column+FVector(0,0,3000),Column-FVector(0,0,12000),ECC_WorldDynamic,Query) && Hit.IsValidBlockingHit();
        Point=Surface?Hit.ImpactPoint:Column;
        Sight.Camera=Eye-Forward*560.+FVector(0,0,815);
        Sight.View=(Point+FVector(0,0,250)-Sight.Camera).Rotation();
    }
    else
    {
        Sight.View=Frame.TransformRotation(FRotator(FMath::Clamp(double(Elevation),-48.,40.),Horizontal.Yaw,0.).Quaternion()).Rotator();
        Sight.Camera=Eye+Forward*40.+FVector(0,0,45.);
        const FVector Dir=Sight.View.Vector(),Offset=Sight.Camera-Eye;
        // Intersect the sight ray with the range sphere, including the scope's offset above the pivot.
        const double Along=FVector::DotProduct(Offset,Dir);
        const double Far=-Along+FMath::Sqrt(FMath::Max(0.,FMath::Square(Range()-1.)-Offset.SizeSquared()+Along*Along));
        Point=Sight.Camera+Dir*Far;
        if(GetWorld()->LineTraceSingleByChannel(Hit,Sight.Camera,Point,ECC_Visibility,Query))Point=Hit.ImpactPoint;
    }
    const double Distance=bStone?FVector::Dist2D(Eye,Point):FVector::Distance(Eye,Point);
    Sight.CanFire=Surface && Distance>=MinimumRange() && Distance<Range() && MakePlan(Point,Sight.Plan);
    if(!Sight.CanFire)
    {
        // The turntable follows the sight even when a nearby obstacle prevents a shot.
        Sight.Plan.Yaw=Horizontal.Yaw;
        Sight.Plan.Pitch=bStone?0.:FMath::Clamp(double(Elevation)-BoltAngle,-66.,23.);
    }
    if(!bStone || !Sight.CanFire)return;
    const FVector Start=ReleaseOrigin(Sight.Plan);
    const FVector Velocity=LaunchVelocity(GetWorld(),true,Start,Sight.Plan.Aim);
    FPredictProjectilePathParams Path(AVillageSiegeMissile::StoneBodyRadius,Start,Velocity,
        FlightTime(true,Start,Sight.Plan.Aim),ECC_WorldDynamic,const_cast<AVillageSiegeEngine*>(this));
    Path.ActorsToIgnore.Add(GetAttachParentActor());
    if(Pawn)Path.ActorsToIgnore.Add(const_cast<APawn*>(Pawn));
    Path.OverrideGravityZ=GetWorld()->GetGravityZ()*GravityScale(true);
    Path.SimFrequency=20.f;
    FPredictProjectilePathResult Result;
    Sight.HasImpact=UGameplayStatics::PredictProjectilePath(this,Path,Result) && Result.HitResult.IsValidBlockingHit();
    Sight.CanFire=Sight.HasImpact;
    if(!Preview || !Sight.HasImpact)return;
    Sight.Impact=Result.HitResult.ImpactPoint;
    Sight.ImpactNormal=Result.HitResult.ImpactNormal.GetSafeNormal(UE_SMALL_NUMBER,FVector::UpVector);
    const APawn* HitPawn=Cast<APawn>(Result.HitResult.GetActor());
    Sight.bHitUnit=HitPawn && !HitPawn->IsA<AVillageDefenseSection>();
    // UE's last sample is the centre of the swept stone. The sight line lands on the contact surface.
    for(const auto& Sample:Result.PathData)Sight.Arc.Add(Sample.Location);
    if(!Sight.Arc.IsEmpty())Sight.Arc.Last()=Sight.Impact;
}

void AVillageSiegeEngine::DisplaySight(const FVillageSiegeShot* Plan)
{
    if(Plan)LocalSightBearing.Emplace(Plan->Pitch,Plan->Yaw,0.);
    else LocalSightBearing.Reset();
    OnRep_Shot();
}

void AVillageSiegeEngine::SetManualBearing(APawn* Pawn,const FRotator& Bearing)
{
    if(!HasAuthority() || !IsOperatedBy(Pawn) || Bearing.ContainsNaN())return;
    const FRotator Facing(bStone?0.:FMath::Clamp(FRotator::NormalizeAxis(Bearing.Pitch),-66.,23.),ResolveAimYaw(Bearing.Yaw),0.);
    if(Facing.Equals(ManualBearing,.1))return;
    FlushNetDormancy();
    ManualBearing=Facing;
    OnRep_Shot();
    ForceNetUpdate();
}

void AVillageSiegeEngine::FireManual(APawn* Pawn,float Yaw,float Elevation)
{
    if(!HasAuthority() || !IsOperatedBy(Pawn) || !CanOperate() || ReloadRemaining()>0.)return;
    FVillageSiegeSight Sight;
    ManualSight(Pawn,Yaw,Elevation,Sight,false);
    if(Sight.CanFire)StartShot(Sight.Plan,nullptr,true);
}

void AVillageSiegeEngine::FindTarget()
{
    if(IsOccupied() || GetHealth()<=0.f || ReloadRemaining()>0.)return;
    const auto* Carrier=Cast<AVoxelBuildPrefabActor>(GetAttachParentActor());
    if(!Carrier || Carrier->IsFalling())return;
    const double SearchRadius=Range();
    const double Minimum=MinimumRange();
    const FVector Eye=GetActorLocation()+FVector(0,0,bStone?305:145);
    TArray<FOverlapResult> Hits;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(VillageSiegeSearch),false,this);
    Params.AddIgnoredActor(Carrier);
    GetWorld()->OverlapMultiByObjectType(Hits,Eye,FQuat::Identity,FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeSphere(SearchRadius),Params);
    FVillageSiegeShot Best;
    APawn* Target=nullptr;
    TSet<AActor*> Seen;
    double Closest=SearchRadius*SearchRadius;
    for(const auto& Hit:Hits)
    {
        APawn* Unit=Cast<APawn>(Hit.GetActor());
        if(!Unit || Seen.Contains(Unit))continue;
        Seen.Add(Unit);
        if(!IsThreat(Unit,this))continue;
        const FVector Current=Unit->GetActorLocation();
        const double Distance=bStone?FVector::DistSquared2D(Current,Eye):FVector::DistSquared(Current,Eye);
        if(Distance>=Closest || Distance<Minimum*Minimum)continue;
        const double Travel=FlightTime(bStone,Eye,Current);
        const FVector Point=Current+Unit->GetVelocity().GetClampedToMaxSize(650.)*(Travel+ReleaseAt());
        FVillageSiegeShot Plan;
        if(!MakePlan(Point,Plan))continue;
        const FVector Origin=ReleaseOrigin(Plan);
        // Query the same arc used by the game missile. A parapet or overhead beam can block a shot.
        const FVector Velocity=LaunchVelocity(GetWorld(),bStone,Origin,Point);
        const double Time=FlightTime(bStone,Origin,Point);
        FVector Previous=Origin;
        bool bBlocked=false;
        FCollisionQueryParams Trace=Params;
        Trace.AddIgnoredActor(Unit);
        for(int32 N=1;N<=8;++N)
        {
            const double S=Time*N/8.;
            const FVector Next=Origin+Velocity*S+FVector(0,0,.5*GetWorld()->GetGravityZ()*GravityScale(bStone)*S*S);
            if(GetWorld()->SweepTestByChannel(Previous,Next,FQuat::Identity,bStone?ECC_WorldDynamic:ECC_Visibility,
                FCollisionShape::MakeSphere(bStone?AVillageSiegeMissile::StoneBodyRadius:4.f),Trace)){bBlocked=true;break;}
            Previous=Next;
        }
        if(bBlocked)continue;
        Closest=Distance;Best=Plan;Target=Unit;
    }
    if(Target)StartShot(Best,Target,false);
}

void AVillageSiegeEngine::StartShot(FVillageSiegeShot Plan,APawn* Target,bool Manual)
{
    FlushNetDormancy();
    Plan.Started=Clock();
    Plan.TraverseFrom=Manual?FRotator(Plan.Pitch,Plan.Yaw,0.):FRotator(Shot.Pitch,Shot.Yaw,0.);
    Plan.UpgradeRanks=CurrentRanks();
    Shot=Plan;
    Tracked=Target;
    bManualShot=Manual;
    ForceNetUpdate();
    OnRep_Shot();
    GetWorldTimerManager().SetTimer(ReleaseTimer,this,&AVillageSiegeEngine::Release,ReleaseAt(),false);
}

void AVillageSiegeEngine::Release()
{
    if(!HasAuthority() || GetHealth()<=0.f)return;
    const auto* Carrier=Cast<AVoxelBuildPrefabActor>(GetAttachParentActor());
    if(!Carrier || Carrier->IsFalling() || (bManualShot?!IsOccupied():!IsThreat(Tracked.Get(),this)))
    {
        FlushNetDormancy();Shot.Started=-1.;ForceNetUpdate();OnRep_Shot();
        return;
    }
    const FVector Start=ReleaseOrigin(Shot);
    const FVector Velocity=LaunchVelocity(GetWorld(),bStone,Start,Shot.Aim);
    const FTransform Transform(Velocity.Rotation(),Start);
    auto* Missile=GetWorld()->SpawnActorDeferred<AVillageSiegeMissile>(AVillageSiegeMissile::StaticClass(),Transform,this,this,
        ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
    if(Missile)
    {
        if(bManualShot)Missile->SetInstigator(OperatorPawn);
        Missile->Launch(bStone,Velocity,Shot.UpgradeRanks);
        Missile->FinishSpawning(Transform);
        FlushNetDormancy();
        Shot.bReleased=true;
        ForceNetUpdate();
        UpdateSiegeAudio(Clock()-Shot.Started);
    }
    else
    {
        FlushNetDormancy();
        Shot.Started=-1.;
        ForceNetUpdate();
        OnRep_Shot();
    }
    Tracked.Reset();
}

AVillageSiegeMissile::AVillageSiegeMissile()
{
    bReplicates=true;
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.bStartWithTickEnabled=false;
    SetReplicateMovement(false);
    InitialLifeSpan=8.f;
    Body=CreateDefaultSubobject<USphereComponent>(TEXT("FlightBody"));
    SetRootComponent(Body);
    Body->InitSphereRadius(4.f);
    Body->SetCollisionProfileName(TEXT("BlockAllDynamic"));
    Body->SetGenerateOverlapEvents(false);
    Body->SetCanEverAffectNavigation(false);
    Model=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Missile"));
    Model->SetupAttachment(Body);
    Model->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Movement=CreateDefaultSubobject<UProjectileMovementComponent>(TEXT("Flight"));
    Movement->SetUpdatedComponent(Body);
    Movement->bRotationFollowsVelocity=true;
    Movement->bInitialVelocityInLocalSpace=false;
    Movement->bForceSubStepping=true;
}

void AVillageSiegeMissile::Launch(bool bStoneShot,const FVector& InitialVelocity,uint16 Ranks)
{
    UpgradeRanks=Ranks;
    bStone=bStoneShot;
    FlightOrigin=GetActorLocation();
    FlightVelocity=InitialVelocity;
    const auto* State=GetWorld()->GetGameState();
    FlightStart=State?State->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
    Movement->Velocity=InitialVelocity;
    Movement->ProjectileGravityScale=GravityScale(bStone);
    Body->SetSphereRadius(bStone?StoneBodyRadius:4.f);
}

void AVillageSiegeMissile::BeginPlay()
{
    Super::BeginPlay();
    OnRep_Model();
    if(HasAuthority())
    {
        Body->IgnoreActorWhenMoving(GetOwner(),true);
        if(GetInstigator())Body->IgnoreActorWhenMoving(GetInstigator(),true);
        if(GetOwner())Body->IgnoreActorWhenMoving(GetOwner()->GetAttachParentActor(),true);
        Movement->OnProjectileStop.AddDynamic(this,&AVillageSiegeMissile::Impact);
    }
    else
    {
        Movement->Deactivate();
        Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        SetActorTickEnabled(true);
    }
}

void AVillageSiegeMissile::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    const auto* State=GetWorld()->GetGameState();
    if(!State || FlightStart<0.)return;
    const double Age=FMath::Max(0.,State->GetServerWorldTimeSeconds()-FlightStart);
    const FVector Gravity(0,0,GetWorld()->GetGravityZ()*GravityScale(bStone));
    SetActorLocationAndRotation(FVector(FlightOrigin)+FVector(FlightVelocity)*Age+Gravity*(.5*Age*Age),
        (FVector(FlightVelocity)+Gravity*Age).Rotation());
}

void AVillageSiegeMissile::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME_CONDITION(AVillageSiegeMissile,bStone,COND_InitialOnly);
    DOREPLIFETIME_CONDITION(AVillageSiegeMissile,FlightOrigin,COND_InitialOnly);
    DOREPLIFETIME_CONDITION(AVillageSiegeMissile,FlightVelocity,COND_InitialOnly);
    DOREPLIFETIME_CONDITION(AVillageSiegeMissile,FlightStart,COND_InitialOnly);
}

void AVillageSiegeMissile::OnRep_Model()
{
    if(GetNetMode()==NM_DedicatedServer)return;
    Model->SetStaticMesh(Cast<UStaticMesh>(AVillageSiegeEngine::MeshAsset(bStone?TEXT("TrebuchetStone"):TEXT("BallistaBolt")).TryLoad()));
    if(bStone && !StoneImpactSound)
        StoneImpactSound=LoadObject<USoundWave>(nullptr,StoneImpactPath);
}

void AVillageSiegeMissile::PlayStoneImpact_Implementation(FVector_NetQuantize HitPoint,FVector_NetQuantize SurfacePoint,FVector_NetQuantizeNormal SurfaceNormal,bool bSurfaceHit,float EffectRadius)
{
    if(GetNetMode()==NM_DedicatedServer)return;
    // A close-range hit can arrive before the initial model notification.
    if(!StoneImpactSound)StoneImpactSound=LoadObject<USoundWave>(nullptr,StoneImpactPath);
    if(StoneImpactSound)UGameplayStatics::PlaySoundAtLocation(this,StoneImpactSound,HitPoint);
    if(!bSurfaceHit)return;

    // The plume lives in the world so it can finish after the projectile is destroyed.
    const FVector Normal=SurfaceNormal.GetSafeNormal(UE_SMALL_NUMBER,FVector::UpVector);
    const FVector Origin=FVector(SurfacePoint)+Normal*2.;
    const FRotator Rotation=FRotationMatrix::MakeFromZ(Normal).Rotator();
    const auto SpawnImpact=[World=TWeakObjectPtr<UWorld>(GetWorld()),Origin,Rotation,EffectRadius]
    {
        auto* Asset=Cast<UNiagaraSystem>(StoneImpactFX.ResolveObject());
        if(!World.IsValid() || !Asset)return;
        if(auto* FX=UNiagaraFunctionLibrary::SpawnSystemAtLocation(World.Get(),Asset,Origin,Rotation,
            FVector::OneVector,true,false,ENCPoolMethod::AutoRelease))
        {
            FX->SetVariableFloat(TEXT("User.Radius"),EffectRadius);
            FX->SetVariableFloat(TEXT("User.Seed"),float(GetTypeHash(Origin)%997));
            FX->Activate(true);
        }
    };
    if(StoneImpactFX.ResolveObject())SpawnImpact();
    else UAssetManager::GetStreamableManager().RequestAsyncLoad(StoneImpactFX,
        FStreamableDelegate::CreateLambda(SpawnImpact));
}

void AVillageSiegeMissile::Impact(const FHitResult& Hit)
{
    if(!HasAuthority() || IsActorBeingDestroyed())return;
    const float Damage=VillageSiegeUpgrades::Installed(UpgradeRanks,bStone,VillageSiegeUpgrades::Damage);
    if(!bStone)
    {
        AActor* Target=Hit.GetActor();
        if(IsThreat(Target,GetOwner()))
        {
            const TWeakObjectPtr<UMonsterCombatComponent> Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
            const double Penetration=VillageSiegeUpgrades::Installed(UpgradeRanks,false,VillageSiegeUpgrades::Special);
            const TGuardValue<const double*> ArmorContext(CombatFormulaRuntime::ActivePhysicalPenetration,&Penetration);
            const float Applied=UGameplayStatics::ApplyPointDamage(Target,Damage,GetActorForwardVector(),Hit,GetInstigatorController(),this,nullptr);
            if(auto* Shooter=Cast<AFPSGAMECharacter>(GetInstigator());Applied>0.f && Shooter && Shooter->IsPlayerControlled())
                Shooter->ClientBallistaHit(!Combat.IsValid() || Combat->IsDead() || Target->IsActorBeingDestroyed());
        }
    }
    else
    {
        const APawn* HitPawn=Cast<APawn>(Hit.GetActor());
        const float Radius=VillageSiegeUpgrades::Installed(UpgradeRanks,true,VillageSiegeUpgrades::Special);
        FHitResult Surface=Hit;
        bool bSurfaceHit=!HitPawn || HitPawn->IsA<AVillageDefenseSection>();
        if(!bSurfaceHit)
        {
            // A nearby capsule can stop the stone first. Look for a physical floor beneath
            // the contact, no farther than a grounded unit's feet. An airborne hit stays airborne.
            const FVector Start=Hit.ImpactPoint+FVector(0,0,2.);
            const double FootZ=HitPawn->GetActorLocation().Z-HitPawn->GetSimpleCollisionHalfHeight();
            const FVector End(Start.X,Start.Y,FMath::Max(FootZ-20.,Start.Z-220.));
            FCollisionQueryParams FloorQuery(SCENE_QUERY_STAT(VillageStoneImpactFloor),false,this);
            FloorQuery.AddIgnoredActor(HitPawn);
            FCollisionObjectQueryParams Floors(ECC_WorldStatic);
            Floors.AddObjectTypesToQuery(ECC_WorldDynamic);
            FHitResult Floor;
            if(End.Z<Start.Z && GetWorld()->LineTraceSingleByObjectType(Floor,Start,End,Floors,FloorQuery) &&
               Floor.IsValidBlockingHit() && Floor.ImpactNormal.Z>=.60 &&
               (!Cast<APawn>(Floor.GetActor()) || Cast<AVillageDefenseSection>(Floor.GetActor())))
            {
                Surface=Floor;
                bSurfaceHit=true;
            }
        }
        PlayStoneImpact(Hit.ImpactPoint,Surface.ImpactPoint,Surface.ImpactNormal,bSurfaceHit,Radius);
        const FVector Point=Hit.ImpactPoint;
        const FVector TraceStart=Point+Hit.ImpactNormal*8.;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(VillageStoneImpact),false,this);
        TArray<FOverlapResult> Hits;
        GetWorld()->OverlapMultiByObjectType(Hits,Point,FQuat::Identity,FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeSphere(Radius),Query);
        TSet<AActor*> Damaged;
        for(const auto& Item:Hits)
        {
            AActor* Unit=Item.GetActor();
            if(!IsThreat(Unit,GetOwner()) || Damaged.Contains(Unit))continue;
            Damaged.Add(Unit);
            FCollisionQueryParams Trace=Query;Trace.AddIgnoredActor(Unit);
            if(Unit!=Hit.GetActor() && GetWorld()->LineTraceTestByChannel(TraceStart,Unit->GetActorLocation(),ECC_Visibility,Trace))continue;
            const float Falloff=FMath::Clamp(1.-FVector::Distance(Point,Unit->GetActorLocation())/(2.*Radius),.5,1.);
            UGameplayStatics::ApplyDamage(Unit,Damage*Falloff,GetInstigatorController(),this,nullptr);
        }
    }
    Destroy();
}
