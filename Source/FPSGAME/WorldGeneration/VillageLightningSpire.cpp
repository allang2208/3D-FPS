#include "VillageLightningSpire.h"
#include "VillageDefenseCombat.h"
#include "VillageSiegeUpgrades.h"
#include "VillageSiegeUseTargets.h"
#include "../FPSGAMECharacter.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Skills/FPSLightningArc.h"
#include "../Skills/LightningDamage.h"
#include "../Skills/LightningTypes.h"
#include "../Skills/ColdSteelSpellFeedback.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/OverlapResult.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraSystem.h"
#include "Sound/SoundBase.h"
#include "TimerManager.h"

namespace
{
    constexpr double SpireAutoWindup=0.18;
    constexpr double SpireManualWindup=0.05;
    constexpr double SpireChainRange=800.;
    constexpr int32 SpireMaxTargets=3;
    constexpr float SpireChainDecay=0.15f;
    constexpr float SpirePrimaryStun=0.65f;
    constexpr float SpireChainStun=0.35f;
    constexpr float SpireOverloadStun=1.20f;
    constexpr double SpireOverloadRange=225.;
    constexpr double SpireManualMagneticRadius=165.;
    constexpr double SpireMaxHeightDelta=3600.;
    const FSoftObjectPath ChainArcPath(TEXT("/Game/Skills/Lightning/NS_LightningChain.NS_LightningChain"));
    const FSoftObjectPath LightningSoundPaths[2]={
        FSoftObjectPath(TEXT("/Game/Skills/Lightning/S_LightningCast1.S_LightningCast1")),
        FSoftObjectPath(TEXT("/Game/Skills/Lightning/S_LightningCast2.S_LightningCast2"))
    };

    UStaticMeshComponent* MakeSpirePart(AVillageLightningSpire* Owner,USceneComponent* Parent,const TCHAR* Name,const FSoftObjectPath& Mesh,FVector Offset)
    {
        auto* Comp=NewObject<UStaticMeshComponent>(Owner,Name);
        Owner->AddInstanceComponent(Comp);
        Comp->SetupAttachment(Parent);
        Comp->SetRelativeLocation(Offset);
        Comp->SetStaticMesh(Cast<UStaticMesh>(Mesh.TryLoad()));
        Comp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Comp->SetGenerateOverlapEvents(false);
        Comp->SetCanEverAffectNavigation(false);
        Comp->RegisterComponent();
        return Comp;
    }

    FLightningCast MakeSpireCastVisual(float Duration,float Fade,int32 Segments,float Jitter)
    {
        FLightningCast V;
        V.Duration=Duration;
        V.Fade=Fade;
        V.Segments=Segments;
        V.Jitter=Jitter;
        V.ChainRange=float(SpireChainRange);
        V.OverloadStacks=5;
        V.OverloadStun=SpireOverloadStun;
        V.OverloadRange=float(SpireOverloadRange);
        V.ElectricBonusPerStack=0.03f;
        return V;
    }
}

FSoftObjectPath AVillageLightningSpire::MeshAsset(const TCHAR* Suffix)
{
    return FSoftObjectPath(FString::Printf(
        TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/LightningSpire/SM_LightningSpire%s.SM_LightningSpire%s"),
        Suffix,Suffix));
}

AVillageLightningSpire::AVillageLightningSpire()
{
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.TickInterval=0.033f;
    RepairSoulCost=140;
}

void AVillageLightningSpire::BeginPlay()
{
    if(GetNetMode()!=NM_DedicatedServer)EnsureFXAssets();
    Super::BeginPlay();
    SetActorTickEnabled(GetNetMode()!=NM_DedicatedServer && GetHealth()>0.f);
}

void AVillageLightningSpire::EnsureFXAssets()
{
    if(!ChainArcAsset)ChainArcAsset=Cast<UNiagaraSystem>(ChainArcPath.TryLoad());
    if(CastSounds.IsEmpty() || CastSounds.Contains(nullptr))
    {
        CastSounds.Reset();
        for(const auto& P:LightningSoundPaths)CastSounds.Add(Cast<USoundBase>(P.TryLoad()));
    }
    if(GetNetMode()!=NM_DedicatedServer && !FXHandle.IsValid())
    {
        TArray<FSoftObjectPath> Paths{ChainArcPath,LightningSoundPaths[0],LightningSoundPaths[1]};
        FXHandle=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths);
    }
}

void AVillageLightningSpire::OnRep_Setup()
{
    Super::OnRep_Setup();
    if(GetNetMode()==NM_DedicatedServer || Mast)return;
    Carriage->SetRelativeLocation(FVector(0.,0.,118.));
    Mast=MakeSpirePart(this,Carriage,TEXT("SpireMast"),MeshAsset(TEXT("Mast")),FVector::ZeroVector);
    Crystal=MakeSpirePart(this,Carriage,TEXT("SpireCrystal"),MeshAsset(TEXT("Crystal")),FVector(0.,0.,166.));
    Rings=MakeSpirePart(this,Carriage,TEXT("SpireRings"),MeshAsset(TEXT("Rings")),FVector(0.,0.,166.));
    if(Mast)Parts.Add(TEXT("Mast"),Mast);
    if(Crystal)Parts.Add(TEXT("Crystal"),Crystal);
    if(Rings)Parts.Add(TEXT("Rings"),Rings);

    CrownLight=NewObject<UPointLightComponent>(this,TEXT("SpireCrownGlow"));
    AddInstanceComponent(CrownLight);
    CrownLight->SetupAttachment(Carriage);
    CrownLight->SetRelativeLocation(FVector(0.,0.,242.));
    CrownLight->SetIntensityUnits(ELightUnits::Lumens);
    CrownLight->SetLightColor(FLinearColor(.26f,.78f,1.f));
    CrownLight->SetCastShadows(false);
    CrownLight->SetCastVolumetricShadow(false);
    CrownLight->SetVolumetricScatteringIntensity(0.08f);
    CrownLight->bAffectTranslucentLighting=false;
    CrownLight->SetMaxDrawDistance(4200.f);
    CrownLight->SetMaxDistanceFadeRange(500.f);
    CrownLight->RegisterComponent();

    EnsureFXAssets();
    ApplyVisualPower(.95f,320.f,450.f);
    ApplyHealth();
    OnRep_Shot();
}

void AVillageLightningSpire::ApplyVisualPower(float Power,float LightLumens,float LightRadius)
{
    if(!FMath::IsNearlyEqual(LastChargePower,Power,.02f))
    {
        LastChargePower=Power;
        for(UStaticMeshComponent* Comp:{Masonry.Get(),Mast.Get(),Crystal.Get(),Rings.Get()})
            if(Comp)Comp->SetCustomPrimitiveDataFloat(0,Power);
    }
    if(CrownLight)
    {
        CrownLight->SetAttenuationRadius(LightRadius);
        CrownLight->SetIntensity(LightLumens);
        CrownLight->SetVisibility(GetHealth()>0.f);
    }
}

void AVillageLightningSpire::ApplyHealth()
{
    Super::ApplyHealth();
    const bool bAlive=GetHealth()>0.f;
    if(CrownLight)CrownLight->SetVisibility(bAlive);
    SetActorTickEnabled(GetNetMode()!=NM_DedicatedServer && bAlive);
}

void AVillageLightningSpire::OnRep_Shot()
{
    if(Shot.bReleased && Shot.Started>LastFlashStart)LastFlashStart=Shot.Started+ReleaseAt();
    if(GetHealth()<=0.f || MeshPath.IsNull())return;
    const double T=Shot.Started>=0.?FMath::Max(0.,Clock()-Shot.Started):0.;
    Pose(T);
}

void AVillageLightningSpire::Pose(double T)
{
    if(GetHealth()<=0.f)return;
    const bool FollowSight=(IsOccupied() || LocalSightBearing.IsSet()) && (Shot.Started<0. || T>=ReleaseAt());
    const FRotator Aim(0.,Shot.Yaw,0.);
    const double Turn=Shot.Started<0.?1.:FMath::Clamp(T/0.20,0.,1.);
    const FRotator Target=FollowSight?LocalSightBearing.Get(ManualBearing):Shot.TraverseFrom+(Aim-Shot.TraverseFrom).GetNormalized()*Turn;
    Carriage->SetRelativeLocationAndRotation(FVector(0.,0.,118.),FRotator(0.,Target.Yaw,0.));
    UsePartPoses.FindOrAdd(TEXT("Mast"))=FTransform::Identity;
}

void AVillageLightningSpire::Tick(float DeltaSeconds)
{
    if(GetHealth()<=0.f)return;
    const double Now=Clock();
    if(Shot.Started>=0.)Pose(FMath::Max(0.,Now-Shot.Started));
    if(GetNetMode()==NM_DedicatedServer)return;

    const bool bCharging=Shot.Started>=0. && !Shot.bReleased;
    const double FlashAge=Now-LastFlashStart;
    const bool bFlashing=FlashAge>=0. && FlashAge<0.45;
    if(!bCharging && !bFlashing && !IsOccupied() && Masonry && !Masonry->WasRecentlyRendered(.4f))return;

    const float SpinMul=bCharging?3.6f:(bFlashing?5.0f:1.0f);
    CrystalYaw=FRotator::NormalizeAxis(CrystalYaw+34.f*SpinMul*DeltaSeconds);
    RingRot.Yaw=FRotator::NormalizeAxis(RingRot.Yaw+28.f*SpinMul*DeltaSeconds);
    RingRot.Pitch=FRotator::NormalizeAxis(RingRot.Pitch+18.f*SpinMul*DeltaSeconds);
    if(Crystal)Crystal->SetRelativeLocationAndRotation(
        FVector(0.,0.,166.+3.2*FMath::Sin(GetWorld()->GetTimeSeconds()*2.4)),FRotator(0.,CrystalYaw,0.));
    if(Rings)Rings->SetRelativeRotation(RingRot);

    if(bFlashing)
    {
        const float K=1.f-FMath::Clamp(float(FlashAge/0.45),0.f,1.f);
        ApplyVisualPower(FMath::Lerp(0.60f,2.85f,K*K),FMath::Lerp(320.f,4800.f,K*K),FMath::Lerp(450.f,1150.f,K));
    }
    else if(bCharging)
    {
        const float F=FMath::Clamp(float((Now-Shot.Started)/FMath::Max(0.05,ReleaseAt())),0.f,1.f);
        ApplyVisualPower(FMath::Lerp(1.05f,2.45f,F),FMath::Lerp(450.f,1600.f,F),FMath::Lerp(480.f,760.f,F));
    }
    else
    {
        const double Rem=ReloadRemaining();
        const float ReadyFrac=Rem<=0.?1.f:FMath::Clamp(1.f-float(Rem/FMath::Max(0.5,Duration()-ReleaseAt())),0.f,1.f);
        ApplyVisualPower(FMath::Lerp(0.55f,0.95f,ReadyFrac),FMath::Lerp(190.f,320.f,ReadyFrac),450.f);
    }
}

FVector AVillageLightningSpire::CrownWorldOrigin() const
{
    return GetActorTransform().TransformPosition(FVector(0.,0.,360.));
}

AActor* AVillageLightningSpire::FindSupportingStructure() const
{
    if(bSupportSampled && SupportStructure.IsValid())return SupportStructure.Get();
    bSupportSampled=true;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(VillageSpireSupport),false,this);
    Query.AddIgnoredActor(GetAttachParentActor());
    FHitResult Hit;
    const FVector Origin=GetActorLocation();
    if(GetWorld() && GetWorld()->LineTraceSingleByChannel(Hit,Origin+FVector(0.,0.,16.),Origin-FVector(0.,0.,120.),ECC_Visibility,Query))
        SupportStructure=Hit.GetActor();
    return SupportStructure.Get();
}

bool AVillageLightningSpire::InSpireRange(const FVector& Crown,const FVector& TargetPt,double MaxRange) const
{
    return FVector::DistSquared2D(Crown,TargetPt)<=FMath::Square(MaxRange) && FMath::Abs(TargetPt.Z-Crown.Z)<=SpireMaxHeightDelta;
}

bool AVillageLightningSpire::HasSpireLineOfSight(const FVector& Crown,const FVector& TargetPt,const AActor* Target,const AActor* Carrier,
    FVector& OutKnee,bool& bOutBent) const
{
    bOutBent=false;
    OutKnee=TargetPt;
    FCollisionQueryParams Direct(SCENE_QUERY_STAT(SpireDirectLos),false,this);
    Direct.AddIgnoredActor(Carrier);
    Direct.AddIgnoredActor(Target);
    if(!GetWorld()->LineTraceTestByChannel(Crown,TargetPt,ECC_Visibility,Direct))return true;

    // On tall Watchtower / Stone Gate roofs, the spire's own deck or merlons block steep downward
    // rays to wall-huggers. Route a single sky-arc knee over the own parapet edge while still letting
    // other buildings/rooftops block interior targets.
    AActor* Support=FindSupportingStructure();
    if(!Support || Support==Carrier)return false;
    const double Dist2D=FVector::Dist2D(Crown,TargetPt);
    const FVector HorizDir=Dist2D>1.?FVector(TargetPt.X-Crown.X,TargetPt.Y-Crown.Y,0.)/Dist2D:GetActorForwardVector();
    OutKnee=Crown+HorizDir*FMath::Clamp(Dist2D*0.6,260.,620.)+FVector(0.,0.,145.);

    FCollisionQueryParams OverParapet=Direct;
    OverParapet.AddIgnoredActor(Support);
    if(GetWorld()->LineTraceTestByChannel(Crown,OutKnee,ECC_Visibility,OverParapet))return false;
    if(GetWorld()->LineTraceTestByChannel(OutKnee,TargetPt,ECC_Visibility,OverParapet))return false;
    bOutBent=true;
    return true;
}

double AVillageLightningSpire::Range() const
{
    return VillageSiegeUpgrades::Installed(CurrentRanks(),VillageSiegeUpgrades::LightningSpire,VillageSiegeUpgrades::SpireReach);
}

double AVillageLightningSpire::ReleaseAt() const
{
    return bManualShot?SpireManualWindup:SpireAutoWindup;
}

double AVillageLightningSpire::Duration() const
{
    const double BaseCooldown=VillageSiegeUpgrades::Installed(Shot.UpgradeRanks,VillageSiegeUpgrades::LightningSpire,VillageSiegeUpgrades::SpireCooldown);
    return ReleaseAt()+(bManualShot?BaseCooldown*0.90:BaseCooldown);
}

FRotator AVillageLightningSpire::ClaimedAim() const
{
    return FRotator(-18.f,ManualBearing.Yaw,0.);
}

bool AVillageLightningSpire::Claim(APawn* Pawn)
{
    if(!HasAuthority() || !Pawn || IsOccupied() || !CanOperate())return false;
    Pose(Shot.Started<0.?0.:FMath::Max(0.,Clock()-Shot.Started));
    const FRotator Current=Carriage->GetRelativeRotation();
    CancelWindup();
    FlushNetDormancy();
    ManualBearing=FRotator(0.,Current.Yaw,0.);
    OperatorPawn=Pawn;
    OnRep_Shot();
    ForceNetUpdate();
    return true;
}

void AVillageLightningSpire::SetManualBearing(APawn* Pawn,const FRotator& Bearing)
{
    if(!HasAuthority() || !IsOperatedBy(Pawn) || Bearing.ContainsNaN())return;
    const FRotator Facing(0.,ResolveAimYaw(Bearing.Yaw),0.);
    if(Facing.Equals(ManualBearing,.1))return;
    FlushNetDormancy();
    ManualBearing=Facing;
    OnRep_Shot();
    ForceNetUpdate();
}

void AVillageLightningSpire::ComputeManualCamera(float Yaw,float Elevation,double CachedGroundZ,
    FVector& OutLocation,FRotator& OutRotation,FRotator& OutFacing) const
{
    const FRotator Horizontal(0.,ResolveAimYaw(Yaw),0.);
    const float Pitch=FMath::Clamp(Elevation,-76.f,35.f);
    OutLocation=CrownWorldOrigin()+FVector(0.,0.,24.);
    OutRotation=GetActorTransform().TransformRotation(FRotator(Pitch,Horizontal.Yaw,0.).Quaternion()).Rotator();
    OutFacing=FRotator(0.,Horizontal.Yaw,0.);
}

void AVillageLightningSpire::ManualSight(const APawn* Pawn,float Yaw,float Elevation,FVillageSiegeSight& Sight,bool Preview) const
{
    Sight.Arc.Reset();
    Sight.Plan=FVillageSiegeShot{};
    Sight.HasImpact=false;
    Sight.CanFire=false;
    if(!FMath::IsFinite(Yaw) || !FMath::IsFinite(Elevation))return;

    const FTransform Frame=GetActorTransform();
    const FRotator Horizontal(0.,ResolveAimYaw(Yaw),0.);
    const FVector Crown=CrownWorldOrigin();
    Sight.Camera=Crown+FVector(0.,0.,24.);
    const float Pitch=FMath::Clamp(Elevation,-76.f,35.f);
    Sight.View=Frame.TransformRotation(FRotator(Pitch,Horizontal.Yaw,0.).Quaternion()).Rotator();

    const FVector Dir=Sight.View.Vector();
    const double MaxRange=Range();
    const AActor* Carrier=GetAttachParentActor();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(VillageSpireSight),false,this);
    Query.AddIgnoredActor(Carrier);
    if(Pawn)Query.AddIgnoredActor(Pawn);

    FHitResult Hit;
    FVector End=Sight.Camera+Dir*(MaxRange+4000.);
    if(GetWorld()->LineTraceSingleByChannel(Hit,Sight.Camera,End,ECC_Visibility,Query) && Hit.IsValidBlockingHit())
        End=Hit.ImpactPoint;

    // Magnetic aim-assist to hostile enemies near crosshair ray (prioritizing agile/airborne threats).
    AActor* LockedEnemy=nullptr;
    double BestScore=DBL_MAX;
    FVector UnusedKnee;
    bool bUnusedBent=false;
    for(const TWeakObjectPtr<APawn>& Candidate:CachedThreatPawns(GetWorld()))
    {
        APawn* Unit=Candidate.Get();
        if(!Unit || !IsThreatUnit(Unit,const_cast<AVillageLightningSpire*>(this)))continue;
        const FVector TargetPt=Unit->GetActorLocation()+FVector(0.,0.,36.);
        if(!InSpireRange(Crown,TargetPt,MaxRange))continue;
        const FVector Offset=TargetPt-Sight.Camera;
        const double Along=FVector::DotProduct(Offset,Dir);
        if(Along<=0.)continue;
        const double Perp=(Offset-Dir*Along).Size();
        if(Perp>SpireManualMagneticRadius)continue;
        if(!HasSpireLineOfSight(Crown,TargetPt,Unit,Carrier,UnusedKnee,bUnusedBent))continue;
        const double Score=Perp/FMath::Max(1.,Along);
        if(Score<BestScore){BestScore=Score;LockedEnemy=Unit;}
    }

    if(LockedEnemy)
    {
        Sight.Plan.Aim=LockedEnemy->GetActorLocation()+FVector(0.,0.,36.);
        Sight.Impact=Sight.Plan.Aim;
        Sight.bHitUnit=true;
        Sight.HasImpact=true;
        Sight.CanFire=true;
    }
    else if(Hit.IsValidBlockingHit() && InSpireRange(Crown,Hit.ImpactPoint,MaxRange))
    {
        Sight.Plan.Aim=Hit.ImpactPoint;
        Sight.Impact=Hit.ImpactPoint;
        Sight.ImpactNormal=Hit.ImpactNormal;
        Sight.HasImpact=true;
        Sight.CanFire=true;
    }
    else
    {
        Sight.Plan.Aim=Crown+Dir*MaxRange;
        Sight.CanFire=false;
    }
    Sight.Plan.Yaw=Frame.InverseTransformVectorNoScale(Sight.Plan.Aim-Crown).Rotation().Yaw;
    Sight.Plan.Pitch=0.f;
}

void AVillageLightningSpire::FireManual(APawn* Pawn,float Yaw,float Elevation)
{
    if(!HasAuthority() || !IsOperatedBy(Pawn) || !CanOperate() || ReloadRemaining()>0.)return;
    FVillageSiegeSight Sight;
    ManualSight(Pawn,Yaw,Elevation,Sight,false);
    if(!Sight.CanFire)return;
    APawn* BestEnemy=nullptr;
    double BestDistSq=FMath::Square(180.);
    for(const TWeakObjectPtr<APawn>& Candidate:CachedThreatPawns(GetWorld()))
    {
        APawn* Unit=Candidate.Get();
        if(!Unit || !IsThreatUnit(Unit,this))continue;
        const double D=FVector::DistSquared(Unit->GetActorLocation()+FVector(0.,0.,36.),Sight.Plan.Aim);
        if(D<BestDistSq){BestDistSq=D;BestEnemy=Unit;}
    }
    bManualShot=true;
    StartShot(Sight.Plan,BestEnemy,true);
}

void AVillageLightningSpire::FindTarget()
{
    if(IsOccupied() || GetHealth()<=0.f || ReloadRemaining()>0.)return;
    const auto* Carrier=Cast<AVoxelBuildPrefabActor>(GetAttachParentActor());
    if(!Carrier || Carrier->IsFalling())return;
    const TArray<TWeakObjectPtr<APawn>>& Candidates=CachedThreatPawns(GetWorld());
    if(Candidates.IsEmpty())return;

    const double MaxDist=Range();
    const FVector Crown=CrownWorldOrigin();
    FVector UnusedKnee;
    bool bUnusedBent=false;

    APawn* BestUnit=nullptr;
    double BestScore=DBL_MAX;
    FVector BestAim=FVector::ZeroVector;
    for(const TWeakObjectPtr<APawn>& Candidate:Candidates)
    {
        APawn* Unit=Candidate.Get();
        if(!Unit || !IsThreatUnit(Unit,this))continue;
        const FVector TargetPt=Unit->GetActorLocation()+FVector(0.,0.,36.);
        if(!InSpireRange(Crown,TargetPt,MaxDist))continue;
        if(!HasSpireLineOfSight(Crown,TargetPt,Unit,Carrier,UnusedKnee,bUnusedBent))continue;

        double Score=FVector::Dist2D(TargetPt,Crown);
        if(const auto* Ch=Cast<ACharacter>(Unit);Ch && Ch->GetCharacterMovement() && Ch->GetCharacterMovement()->IsFalling())
            Score*=0.38;
        else if(Unit->GetVelocity().Size2D()>380.)
            Score*=0.62;
        if(const auto* Status=Unit->FindComponentByClass<UCombatStatusFormula>();Status && Status->ElectrifiedCount()<4)
            Score*=0.82;
        if(Score<BestScore){BestScore=Score;BestUnit=Unit;BestAim=TargetPt;}
    }
    if(!BestUnit)return;
    FVillageSiegeShot Plan;
    Plan.Aim=BestAim;
    Plan.Yaw=GetActorTransform().InverseTransformVectorNoScale(BestAim-Crown).Rotation().Yaw;
    Plan.Pitch=0.f;
    bManualShot=false;
    StartShot(Plan,BestUnit,false);
}

void AVillageLightningSpire::TriggerOverload(AActor* Origin,float SplashDamage,APawn* InstigatorPawn,AController* InstigatorCtrl,
    TSet<AActor*>& Overloaded,int32 Depth)
{
    if(!Origin || Depth>3 || Overloaded.Contains(Origin))return;
    Overloaded.Add(Origin);
    if(auto* Combat=Origin->FindComponentByClass<UMonsterCombatComponent>())
        Combat->ReceiveStun(InstigatorPawn,SpireOverloadStun,0);
    if(auto* Status=UCombatStatusFormula::GetOrAdd(Origin))
        Status->AddStun(SpireOverloadStun);

    const FVector Start=Origin->GetActorLocation()+FVector(0.,0.,36.);
    const FLightningCast Visual=MakeSpireCastVisual(.48f,.24f,9,.13f);
    for(const TWeakObjectPtr<APawn>& Candidate:CachedThreatPawns(GetWorld()))
    {
        APawn* Nearby=Candidate.Get();
        if(!Nearby || Nearby==Origin || !IsThreatUnit(Nearby,this))continue;
        const FVector End=Nearby->GetActorLocation()+FVector(0.,0.,36.);
        if(FVector::DistSquared(Start,End)>FMath::Square(SpireOverloadRange))continue;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(SpireOverloadLos),false,this);
        Query.AddIgnoredActor(Origin);Query.AddIgnoredActor(Nearby);
        if(GetWorld()->LineTraceTestByChannel(Start,End,ECC_Visibility,Query))continue;

        FActorSpawnParameters Spawn;
        Spawn.Owner=this;Spawn.Instigator=InstigatorPawn?InstigatorPawn:this;
        Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        if(auto* Arc=GetWorld()->SpawnActor<AFPSLightningArc>(Start,FRotator::ZeroRotator,Spawn))
            Arc->InitializeArc(ChainArcAsset,Start,End,Visual,1.15f,true,85.f);

        auto* VictimStatus=UCombatStatusFormula::GetOrAdd(Nearby);
        const FVector Dir=(End-Start).GetSafeNormal();
        FHitResult Hit(Nearby,Cast<UPrimitiveComponent>(Nearby->GetRootComponent()),End,-Dir);
        const TWeakObjectPtr<UMonsterCombatComponent> NearbyCombat=Nearby->FindComponentByClass<UMonsterCombatComponent>();
        const float Applied=UGameplayStatics::ApplyPointDamage(Nearby,SplashDamage,Dir,Hit,InstigatorCtrl,this,ULightningDamage::StaticClass());
        const bool bNearbyKilled=!NearbyCombat.IsValid() || NearbyCombat->IsDead() || Nearby->IsActorBeingDestroyed();
        if(Applied>0.f)
            VillageDefenseCombat::BroadcastDamageNumber(GetWorld(),Nearby,End,Applied,Applied,false,bNearbyKilled);
        if(VictimStatus && !VictimStatus->IsImmune())
            if(!bNearbyKilled)
                if(VictimStatus->AddElectrified(1,6.f,5,0.03f))
                    TriggerOverload(Nearby,SplashDamage,InstigatorPawn,InstigatorCtrl,Overloaded,Depth+1);
    }
}

void AVillageLightningSpire::Release()
{
    if(!HasAuthority() || GetHealth()<=0.f)return;
    const auto* Carrier=Cast<AVoxelBuildPrefabActor>(GetAttachParentActor());
    if(!Carrier || Carrier->IsFalling()){FlushNetDormancy();Shot.Started=-1.;ForceNetUpdate();OnRep_Shot();return;}

    EnsureFXAssets();
    const FVector Crown=CrownWorldOrigin();
    APawn* Primary=Cast<APawn>(Tracked.Get());
    if(Primary && (!IsThreatUnit(Primary,this) || !InSpireRange(Crown,Primary->GetActorLocation(),Range()+120.)))
        Primary=nullptr;
    if(!Primary)
    {
        double BestSq=FMath::Square(180.);
        for(const TWeakObjectPtr<APawn>& Candidate:CachedThreatPawns(GetWorld()))
        {
            APawn* Unit=Candidate.Get();
            if(!Unit || !IsThreatUnit(Unit,this))continue;
            const double D=FVector::DistSquared(Unit->GetActorLocation()+FVector(0.,0.,36.),Shot.Aim);
            if(D<BestSq){BestSq=D;Primary=Unit;}
        }
    }
    if(!bManualShot && !Primary)
    {
        FlushNetDormancy();Shot.Started=-1.;ForceNetUpdate();OnRep_Shot();
        return;
    }

    const FVector Impact=Primary?(Primary->GetActorLocation()+FVector(0.,0.,36.)):FVector(Shot.Aim);
    APawn* Shooter=bManualShot?OperatorPawn.Get():nullptr;
    AController* ShooterCtrl=Shooter?Shooter->GetController():nullptr;
    AActor* DamageCauser=Shooter?static_cast<AActor*>(Shooter):this;

    const FLightningCast PrimaryVisual=MakeSpireCastVisual(.58f,.30f,14,.11f);
    const FLightningCast ForkVisual=MakeSpireCastVisual(.44f,.24f,12,.16f);
    auto SpawnBolt=[&](const FVector& Start,const FVector& End,const FLightningCast& Vis,float Width,float Bright,bool bLight)
    {
        FActorSpawnParameters P;P.Owner=this;P.Instigator=Shooter?Shooter:this;
        P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        if(auto* Arc=GetWorld()->SpawnActor<AFPSLightningArc>(Start,FRotator::ZeroRotator,P))
            Arc->InitializeArc(ChainArcAsset,Start,End,Vis,Width,bLight,Bright);
    };

    // Route an arched bolt over our own parapet roof when hitting wall-huggers below; otherwise direct strike + crackle fork.
    FVector Knee=Impact;
    bool bBent=false;
    HasSpireLineOfSight(Crown,Impact,Primary,Carrier,Knee,bBent);
    const float MainWidth=bManualShot?2.85f:2.40f;
    const float MainBright=bManualShot?115.f:95.f;
    if(bBent)
    {
        SpawnBolt(Crown,Knee,PrimaryVisual,MainWidth,MainBright,false);
        SpawnBolt(Knee,Impact,PrimaryVisual,MainWidth,MainBright,true);
    }
    else
    {
        SpawnBolt(Crown,Impact,PrimaryVisual,MainWidth,MainBright,true);
        SpawnBolt(Crown,Impact+FVector(FMath::FRandRange(-28.,28.),FMath::FRandRange(-28.,28.),FMath::FRandRange(-12.,18.)),
            ForkVisual,1.15f,78.f,false);
    }
    MulticastDischargeFX(Crown,Impact);

    const float BaseDamage=float(VillageSiegeUpgrades::Installed(Shot.UpgradeRanks,VillageSiegeUpgrades::LightningSpire,VillageSiegeUpgrades::SpireDamage))
        *(bManualShot?1.20f:1.00f);
    const int32 ElectrifyStacks=FMath::RoundToInt(VillageSiegeUpgrades::Installed(
        Shot.UpgradeRanks,VillageSiegeUpgrades::LightningSpire,VillageSiegeUpgrades::SpireElectrify));

    TSet<AActor*> HitSet;
    TSet<AActor*> Overloaded;
    bool bAnyKilled=false,bAnyApplied=false;
    if(!Primary && bManualShot)
    {
        // Manual ground surge AOE when striking terrain beside agile/leaping enemies.
        const double SurgeRadiusSq=FMath::Square(BlastRadius());
        for(const TWeakObjectPtr<APawn>& Candidate:CachedThreatPawns(GetWorld()))
        {
            APawn* Unit=Candidate.Get();
            if(!Unit || !IsThreatUnit(Unit,this))continue;
            const FVector TargetPt=Unit->GetActorLocation()+FVector(0.,0.,36.);
            if(FVector::DistSquared(Impact,TargetPt)>SurgeRadiusSq)continue;
            HitSet.Add(Unit);
            auto* Status=UCombatStatusFormula::GetOrAdd(Unit);
            const FVector Dir=(TargetPt-Impact).GetSafeNormal();
            FHitResult Hit(Unit,Cast<UPrimitiveComponent>(Unit->GetRootComponent()),TargetPt,-Dir);
            const TWeakObjectPtr<UMonsterCombatComponent> Combat=Unit->FindComponentByClass<UMonsterCombatComponent>();
            const float Applied=UGameplayStatics::ApplyPointDamage(Unit,BaseDamage*0.65f,Dir,Hit,ShooterCtrl,DamageCauser,ULightningDamage::StaticClass());
            if(Applied>0.f)
            {
                bAnyApplied=true;
                const bool bKilled=!Combat.IsValid() || Combat->IsDead() || Unit->IsActorBeingDestroyed();
                bAnyKilled|=bKilled;
                VillageDefenseCombat::BroadcastDamageNumber(GetWorld(),Unit,TargetPt,Applied,Applied,false,bKilled);
                if(!bKilled && Status && !Status->IsImmune())
                {
                    if(Combat.IsValid())Combat->ReceiveStun(Shooter,0.45f,0);
                    Status->AddStun(0.45f);
                    if(Status->AddElectrified(ElectrifyStacks,6.f,5,0.03f))
                        TriggerOverload(Unit,BaseDamage*0.70f,Shooter,ShooterCtrl,Overloaded,0);
                }
            }
        }
    }
    AActor* Current=Primary;
    FVector FromPt=bBent?Knee:Crown;
    for(int32 Hop=0;Hop<SpireMaxTargets && Current;++Hop)
    {
        HitSet.Add(Current);
        const FVector TargetPt=Current->GetActorLocation()+FVector(0.,0.,36.);
        if(Hop>0)
        {
            const FLightningCast ChainVis=MakeSpireCastVisual(.50f,.26f,11,.12f);
            SpawnBolt(FromPt,TargetPt,ChainVis,Hop==1?1.65f:1.30f,82.f,true);
        }
        const float HopMul=FMath::Pow(1.f-SpireChainDecay,float(Hop));
        auto* Status=UCombatStatusFormula::GetOrAdd(Current);
        const float RawDamage=BaseDamage*HopMul;
        const FVector Dir=(TargetPt-FromPt).GetSafeNormal();
        FHitResult Hit(Current,Cast<UPrimitiveComponent>(Current->GetRootComponent()),TargetPt,-Dir);
        const TWeakObjectPtr<UMonsterCombatComponent> Combat=Current->FindComponentByClass<UMonsterCombatComponent>();
        const float Applied=UGameplayStatics::ApplyPointDamage(Current,RawDamage,Dir,Hit,ShooterCtrl,DamageCauser,ULightningDamage::StaticClass());
        if(Applied>0.f)
        {
            bAnyApplied=true;
            const bool bKilled=!Combat.IsValid() || Combat->IsDead() || Current->IsActorBeingDestroyed();
            bAnyKilled|=bKilled;
            VillageDefenseCombat::BroadcastDamageNumber(GetWorld(),Current,TargetPt,Applied,Applied,false,bKilled);
            if(!bKilled && Status && !Status->IsImmune())
            {
                const float StunSec=Hop==0?SpirePrimaryStun:SpireChainStun;
                if(Combat.IsValid())Combat->ReceiveStun(Shooter,StunSec,0);
                Status->AddStun(StunSec);
                if(Status->AddElectrified(ElectrifyStacks,6.f,5,0.03f))
                    TriggerOverload(Current,BaseDamage*0.70f,Shooter,ShooterCtrl,Overloaded,0);
            }
        }
        // Pick next unhit enemy within 800 cm for chain jump (elevated LOS slightly so curbs don't occlude).
        FromPt=TargetPt;
        AActor* Next=nullptr;
        double NextSq=FMath::Square(SpireChainRange);
        for(const TWeakObjectPtr<APawn>& Candidate:CachedThreatPawns(GetWorld()))
        {
            APawn* Cand=Candidate.Get();
            if(!Cand || HitSet.Contains(Cand) || !IsThreatUnit(Cand,this))continue;
            const FVector CandPt=Cand->GetActorLocation()+FVector(0.,0.,36.);
            const double D=FVector::DistSquared(FromPt,CandPt);
            if(D>=NextSq)continue;
            FCollisionQueryParams Los(SCENE_QUERY_STAT(SpireChainLos),false,this);
            Los.AddIgnoredActor(Current);Los.AddIgnoredActor(Cand);
            if(GetWorld()->LineTraceTestByChannel(FromPt+FVector(0.,0.,34.),CandPt+FVector(0.,0.,34.),ECC_Visibility,Los))continue;
            NextSq=D;Next=Cand;
        }
        Current=Next;
    }

    if(bAnyApplied && Shooter)
        if(auto* Player=Cast<AFPSGAMECharacter>(Shooter);Player && Player->IsPlayerControlled())
            Player->ClientBallistaHit(bAnyKilled);

    FlushNetDormancy();
    Shot.bReleased=true;
    ForceNetUpdate();
    OnRep_Shot();
    Tracked.Reset();
}

void AVillageLightningSpire::MulticastDischargeFX_Implementation(FVector_NetQuantize Origin,FVector_NetQuantize Impact)
{
    if(GetNetMode()==NM_DedicatedServer)return;
    EnsureFXAssets();
    LastFlashStart=Clock();
    if(!CastSounds.IsEmpty())
    {
        USoundBase* Sound=CastSounds[FMath::RandRange(0,CastSounds.Num()-1)];
        if(Sound)
        {
            const float Pitch=FMath::FRandRange(0.86f,0.96f);
            UGameplayStatics::PlaySoundAtLocation(this,Sound,Origin,1.15f,Pitch);
            if(FVector::DistSquared(Origin,Impact)>FMath::Square(600.))
                UGameplayStatics::PlaySoundAtLocation(this,Sound,Impact,0.85f,Pitch*0.95f);
        }
    }
}
