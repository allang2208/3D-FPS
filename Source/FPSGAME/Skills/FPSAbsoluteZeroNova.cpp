#include "FPSAbsoluteZeroNova.h"
#include "FPSFrostSurfaceMesh.h"
#include "FPSIceWall.h"
#include "FPSIceWallComponent.h"
#include "IceWallPlacement.h"
#include "IceWallLandingCameraShake.h"
#include "BlizzardEnvironment.h"
#include "MagicOcclusion.h"
#include "HolyLightTargets.h"
#include "NetCastUtils.h"
#include "../Combat/RangedAttackQuery.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Net/UnrealNetwork.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "Particles/ParticleSystem.h"
#include "Sound/SoundBase.h"

namespace
{
constexpr float TotalVisualSeconds=3.65f;
constexpr float SpikeHoldBaseSeconds=1.42f;
constexpr float SpikeShatterCollapseSeconds=.16f;
constexpr int32 MaxShatterBursts=14;
}

const TCHAR* const* AFPSAbsoluteZeroNova::AssetPaths()
{
    static const TCHAR* Paths[AssetCount]={
        FrostSurfaceMesh::SheetMaterialPath,                                                      // 0: terrain-conforming frost ice sheet
        FrostSurfaceMesh::SigilMaterialPath,                                                      // 1: ground crystal windup sigil
        TEXT("/Game/Skills/IceSpike/FrostV2/M_IceSpikeHeartV3.M_IceSpikeHeartV3"),                // 2: frost heart V3 material (ISM-enabled opaque glacier for shards/splinters)
        TEXT("/Game/Skills/IceSpike/SM_IceShard.SM_IceShard"),                                    // 3: flying shrapnel & 3D tumbling burst splinters
        TEXT("/Game/Skills/IceWall/SlamV3/NS_IceWallLanding.NS_IceWallLanding"),                  // 4: center ground frost burst
        FrostSurfaceMesh::InwardMistPath,                                                         // 5: inward-suction windup cold mist
        TEXT("/Game/Skills/IceSpike/P_IceSpikeImpact.P_IceSpikeImpact"),                          // 6: impact shatter burst
        TEXT("/Game/Skills/Blizzard/StormV2/S_BlizzardIceLanding.S_BlizzardIceLanding"),          // 7: main nova boom
        TEXT("/Game/Skills/IceSpike/S_IceImpact.S_IceImpact"),                                    // 8: crisp ice shatter
        TEXT("/Game/Skills/IceWall/BlockV1/S_IceWallCast.S_IceWallCast"),                         // 9: channel hum
        TEXT("/Game/Skills/AbsoluteZero/SM_AZ_GlacierSpire_01.SM_AZ_GlacierSpire_01"),            // 10: sculpted glacier monolith 1 (pivot at base Z=0, +Z 1m)
        TEXT("/Game/Skills/AbsoluteZero/SM_AZ_GlacierSpire_02.SM_AZ_GlacierSpire_02"),            // 11: sculpted glacier horn 2
        TEXT("/Game/Skills/AbsoluteZero/SM_AZ_GlacierSpire_03.SM_AZ_GlacierSpire_03"),            // 12: sculpted twin-peak obelisk 3
        TEXT("/Game/Skills/AbsoluteZero/SM_AZ_IceFangCluster.SM_AZ_IceFangCluster"),              // 13: sculpted triple-fang cluster
        FrostSurfaceMesh::SpireMaterialPath,                                                      // 14: IceSpike-derived opaque dark-glacier spire core
        FrostSurfaceMesh::ShockRingMaterialPath,                                                  // 15: 360-deg expanding cryo shockwave ring material
        FrostSurfaceMesh::BurstWavePath,                                                          // 16: 360-deg outward billowing cryo mist + fine frost powder
        FrostSurfaceMesh::SpireShellMaterialPath                                                  // 17: IceSpike-derived translucent glossy outer crystal coat
    };
    return Paths;
}

bool AFPSAbsoluteZeroNova::HasBasicAssets(const TArray<TObjectPtr<UObject>>& InAssets)
{
    return InAssets.Num()==AssetCount&&(Cast<UMaterialInterface>(InAssets[0])||Cast<UMaterialInterface>(InAssets[1])||Cast<UStaticMesh>(InAssets[10]));
}

AFPSAbsoluteZeroNova::AFPSAbsoluteZeroNova()
{
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.TickGroup=TG_PostUpdateWork;
    bReplicates=true;
    SetNetCullDistanceSquared(FMath::Square(15000.f));
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

void AFPSAbsoluteZeroNova::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AFPSAbsoluteZeroNova,NetCaster);
    DOREPLIFETIME(AFPSAbsoluteZeroNova,NetCast);
    DOREPLIFETIME(AFPSAbsoluteZeroNova,NetCenter);
    DOREPLIFETIME(AFPSAbsoluteZeroNova,NetWalls);
    DOREPLIFETIME(AFPSAbsoluteZeroNova,NetStartedAt);
    DOREPLIFETIME(AFPSAbsoluteZeroNova,bNetActivated);
}

void AFPSAbsoluteZeroNova::LoadAssetsSync()
{
    if(HasBasicAssets(Assets))return;
    Assets.Reset();
    const TCHAR* const* Paths=AssetPaths();
    for(int32 I=0;I<AssetCount;++I)Assets.Add(StaticLoadObject(UObject::StaticClass(),nullptr,Paths[I]));
}

bool AFPSAbsoluteZeroNova::InitializeNova(APawn* Shooter,const FAbsoluteZeroCast& Spell,const FVector& GroundCenter,const TArray<TObjectPtr<UObject>>& InAssets)
{
    if((HasAuthority()&&!Shooter)||!HasBasicAssets(InAssets))return false;
    Assets=InAssets;
    Caster=Shooter;
    CastSnapshot=Spell;
    Center=GroundCenter;
    SetActorLocation(Center);

    if(HasAuthority())
    {
        RewardModel=NetCast::AuthorityModel(Shooter,GetGameInstance());
        NetCaster=Shooter;
        NetCast=Spell;
        NetCenter=Center;
        QueuedWalls.Reset();
        NetWalls.Reset();

        // Collect ONLY the caster's own Solid IceWalls inside the nova radius (up to MaxDetonatedWalls).
        if(Spell.MaxDetonatedWalls>0)
        {
            if(const auto* WallComp=Shooter->FindComponentByClass<UFPSIceWallComponent>())
            {
                struct FCandidate { AFPSIceWall* Wall; float Dist; };
                TArray<FCandidate> Candidates;
                for(const auto& WeakWall:WallComp->ActiveWalls())
                {
                    AFPSIceWall* Wall=WeakWall.Get();
                    if(!IsValid(Wall)||!Wall->IsSolid())continue;
                    const FIceWallPlacement& Plan=Wall->Placement();
                    if(!Plan.bValid)continue;
                    const FVector Local=Plan.Rotation.UnrotateVector(Center-Plan.Location);
                    const float ClampedAlong=FMath::Clamp(float(Local.Y),Plan.MinAlong(),Plan.MaxAlong());
                    const FVector Closest=Plan.Location+Plan.Rotation.RotateVector(FVector(0.f,ClampedAlong,0.f));
                    const float Dist2D=FVector::Dist2D(Center,Closest);
                    const float VertGap=FMath::Abs(Center.Z-Plan.Location.Z);
                    if(Dist2D<=Spell.Radius+40.f&&VertGap<=360.f)
                        Candidates.Add({Wall,Dist2D});
                }
                Candidates.Sort([](const FCandidate& A,const FCandidate& B){return A.Dist<B.Dist;});
                const int32 Take=FMath::Min(Spell.MaxDetonatedWalls,Candidates.Num());
                for(int32 I=0;I<Take;++I)
                {
                    AFPSIceWall* Wall=Candidates[I].Wall;
                    const FIceWallPlacement& Plan=Wall->Placement();
                    const FIceWallCast& WSnap=Wall->Snapshot();
                    const int32 PerSec=Plan.Shape==EIceWallShape::Low?1:2;
                    const int32 RawCount=FMath::Max(1,Plan.Sections.Num())*PerSec;
                    FQueuedWall Q;
                    Q.Wall=Wall;
                    Q.TriggerDistance=FMath::Max(60.f,Candidates[I].Dist);
                    Q.Snapshot.Location=Plan.Location;
                    Q.Snapshot.Rotation=Plan.Rotation;
                    Q.Snapshot.MinAlong=Plan.MinAlong();
                    Q.Snapshot.MaxAlong=Plan.MaxAlong();
                    Q.Snapshot.GroundZ=Plan.Location.Z+Plan.GroundMin();
                    Q.Snapshot.Height=WSnap.Height(Plan.Shape);
                    Q.Snapshot.HealthRatio=FMath::Clamp(Wall->Health/FMath::Max(1.f,Wall->MaxHealth),0.f,1.f);
                    Q.Snapshot.TriggerDistance=Q.TriggerDistance;
                    Q.Snapshot.ShardCount=FMath::Clamp(RawCount,4,Spell.MaxShardsPerWall);
                    Q.Snapshot.Seed=int32(GetUniqueID())^(I*7919+31337);
                    QueuedWalls.Add(Q);
                    NetWalls.Add(Q.Snapshot);
                }
            }
        }
    }
    return true;
}

void AFPSAbsoluteZeroNova::ActivateNova()
{
    if(bActivated)return;
    bActivated=true;
    Age=0.f;
    PreviousWaveRadius=0.f;
    if(HasAuthority())
    {
        const auto* GS=GetWorld()->GetGameState();
        NetStartedAt=GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
        bNetActivated=true;
        ForceNetUpdate();
        // Immediate inner-ring hit check so point-blank enemies react on frame 0.
        StepWaveAuthority(0.f,FMath::Min(CastSnapshot.Radius,220.f));
        PreviousWaveRadius=FMath::Min(CastSnapshot.Radius,220.f);
    }
    if(GetNetMode()!=NM_DedicatedServer)BuildClientVisuals();
}

void AFPSAbsoluteZeroNova::BuildClientVisuals()
{
    if(bClientInitialized||GetNetMode()==NM_DedicatedServer)return;
    LoadAssetsSync();
    bClientInitialized=true;
    const float InitialAge=Age;
    const bool bLateJoin=InitialAge>.75f;
    const float ExpandSec=FMath::Max(.08f,CastSnapshot.ExpandSeconds);
    const float InitialRadius=CastSnapshot.Radius*FMath::Clamp(InitialAge/ExpandSec,0.f,1.f);
    if(bLateJoin)bSecondTremorDone=true;

    ClientWallDetonated.Init(false,NetWalls.Num());
    if(bLateJoin)
    {
        for(int32 I=0;I<NetWalls.Num();++I)
            if(InitialRadius>=FMath::Max(60.f,NetWalls[I].TriggerDistance))
                ClientWallDetonated[I]=true;
    }

    // 1) Continuous terrain-conforming frost ice sheet (40x10 grid = 800 traces, smooth 9-deg resolution).
    if(auto* FrostMat=Cast<UMaterialInterface>(Assets[0]))
    {
        FrostSurface=FrostSurfaceMesh::BuildConformingDisc(this,RootComponent,Caster.Get(),Center,FVector::ForwardVector,
            CastSnapshot.Radius,CastSnapshot.Radius,FrostMat,FrostMID,40,10,true,4.f);
        if(FrostMID)
        {
            FrostMID->SetScalarParameterValue(TEXT("Fade"),1.f);
            FrostMID->SetScalarParameterValue(TEXT("RevealRadius"),bLateJoin?1.08f:.06f);
            FrostMID->SetScalarParameterValue(TEXT("FrostDensity"),.90f);
            FrostMID->SetScalarParameterValue(TEXT("EmissiveBoost"),bLateJoin?.14f:1.45f);
        }
    }

    // 2) Expanding 360-deg 3D cryo shockwave ring / pressure crest racing along the blast frontier.
    if(!bLateJoin)
    {
        if(auto* ShockMat=Cast<UMaterialInterface>(Assets[15]))
        {
            ShockRing=FrostSurfaceMesh::BuildShockRing(this,RootComponent,Center+FVector(0,0,4.f),ShockMat,ShockRingMID,56);
            if(ShockRing)ShockRing->SetWorldScale3D(FVector(1.3f,1.3f,.85f));
            if(ShockRingMID)
            {
                ShockRingMID->SetScalarParameterValue(TEXT("WaveProgress"),0.f);
                ShockRingMID->SetScalarParameterValue(TEXT("Fade"),1.f);
                ShockRingMID->SetScalarParameterValue(TEXT("Intensity"),2.6f);
            }
        }
    }

    // 3) Shadow-free intense cryo detonation flash light.
    if(!bLateJoin)
    {
        FlashLight=NewObject<UPointLightComponent>(this);
        AddInstanceComponent(FlashLight);
        FlashLight->SetupAttachment(RootComponent);
        FlashLight->SetWorldLocation(Center+FVector(0,0,150));
        FlashLight->SetLightColor(FLinearColor(.36f,.84f,1.f));
        FlashLight->SetIntensity(28000.f);
        FlashLight->SetAttenuationRadius(FMath::Min(1750.f,CastSnapshot.Radius*1.25f));
        FlashLight->SetCastShadows(false);
        FlashLight->RegisterComponent();
    }

    // 4) Dual-layer IceSpike-style ISM architecture for sculpted base-pivoted (+Z 1.0 m) razor crystal spires:
    //    - SpikeISMs[0..3]: opaque dark-glacier PBR core (M_AbsoluteZeroSpire)
    //    - SpikeShellISMs[0..2]: translucent glossy outer crystal sheath (M_AbsoluteZeroSpireShell) wrapping Hero monoliths
    UMaterialInterface* HeartMat=Cast<UMaterialInterface>(Assets[2]);
    UMaterialInterface* SpireBaseMat=Cast<UMaterialInterface>(Assets[14]);
    UMaterialInterface* SpireShellBaseMat=Cast<UMaterialInterface>(Assets[17]);
    UMaterialInterface* ChosenSpireMat=SpireBaseMat?SpireBaseMat:HeartMat;
    if(ChosenSpireMat)
    {
        SpireMID=UMaterialInstanceDynamic::Create(ChosenSpireMat,this);
        if(SpireMID)
        {
            SpireMID->SetScalarParameterValue(TEXT("EruptionFlash"),bLateJoin?0.f:1.f);
            SpireMID->SetScalarParameterValue(TEXT("ShatterGlow"),0.f);
        }
    }
    if(SpireShellBaseMat)
    {
        SpireShellMID=UMaterialInstanceDynamic::Create(SpireShellBaseMat,this);
        if(SpireShellMID)
        {
            SpireShellMID->SetScalarParameterValue(TEXT("EruptionFlash"),bLateJoin?0.f:1.f);
            SpireShellMID->SetScalarParameterValue(TEXT("ShatterGlow"),0.f);
        }
    }
    UMaterialInterface* ActiveSpireMat=SpireMID?static_cast<UMaterialInterface*>(SpireMID.Get()):ChosenSpireMat;
    UMaterialInterface* ActiveShellMat=SpireShellMID?static_cast<UMaterialInterface*>(SpireShellMID.Get()):SpireShellBaseMat;
    UMaterialInterface* ShardMat=HeartMat?HeartMat:ActiveSpireMat;
    for(int32 B=0;B<4;++B)
    {
        auto* Mesh=Cast<UStaticMesh>(Assets[10+B]);
        if(!Mesh)continue;
        auto* ISM=NewObject<UInstancedStaticMeshComponent>(this);
        AddInstanceComponent(ISM);
        ISM->SetupAttachment(RootComponent);
        ISM->SetStaticMesh(Mesh);
        if(ActiveSpireMat)ISM->SetMaterial(0,ActiveSpireMat);
        ISM->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        ISM->SetCanEverAffectNavigation(false);
        ISM->SetCastShadow(false);
        ISM->bReceivesDecals=false;
        ISM->SetCullDistances(0,9500);
        ISM->RegisterComponent();
        SpikeISMs.Add(ISM);

        if(B<3&&ActiveShellMat)
        {
            auto* ShellISM=NewObject<UInstancedStaticMeshComponent>(this);
            AddInstanceComponent(ShellISM);
            ShellISM->SetupAttachment(RootComponent);
            ShellISM->SetStaticMesh(Mesh);
            ShellISM->SetMaterial(0,ActiveShellMat);
            ShellISM->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            ShellISM->SetCanEverAffectNavigation(false);
            ShellISM->SetCastShadow(false);
            ShellISM->bReceivesDecals=false;
            // Cull translucent outer crystal sheen beyond 42 m to bound translucent overdraw.
            ShellISM->SetCullDistances(0,4200);
            ShellISM->RegisterComponent();
            SpikeShellISMs.Add(ShellISM);
        }
    }

    // Populate a dramatic 3-tier clustered glacier eruption (~76 clusters -> ~210-235 sculpted ISM instances).
    // Deterministic cross-client seed from quantized Center + NetStartedAt so all peers see identical spires.
    if(!SpikeISMs.IsEmpty())
    {
        const int32 Seed=int32(FMath::RoundToInt(Center.X*13.f+Center.Y*31.f+Center.Z*7.f))^int32(FMath::RoundToInt(NetStartedAt*100.0))^0x51A77E;
        FRandomStream Rng(Seed);
        FCollisionQueryParams Query(SCENE_QUERY_STAT(AbsoluteZeroSpike),false,this);
        if(Caster.IsValid())Query.AddIgnoredActor(Caster.Get());
        const float BlastR=FMath::Max(600.f,CastSnapshot.Radius);
        const float BaseAngle=Rng.FRandRange(0.f,2.f*PI);
        const int32 NumRays=8;
        const int32 HeroBuckets=FMath::Min(3,SpikeISMs.Num());
        const int32 FangBucket=SpikeISMs.Num()>=4?3:(SpikeISMs.Num()-1);

        auto OrientSpire=[](const FVector& FloorNormal,float OutAngleRad,float TiltOutDeg,float SpinDeg)->FQuat
        {
            const FVector Up=FMath::Lerp(FVector::UpVector,FloorNormal,.35f).GetSafeNormal();
            const FVector Radial=FVector(FMath::Cos(OutAngleRad),FMath::Sin(OutAngleRad),0.f);
            const FVector Tangent=FVector::CrossProduct(Up,Radial).GetSafeNormal(SMALL_NUMBER,FVector::RightVector);
            const FQuat AlignUp=FQuat::FindBetweenNormals(FVector::UpVector,Up);
            const FQuat TiltOut=FQuat(Tangent,FMath::DegreesToRadians(TiltOutDeg));
            const FQuat Spin=FQuat(Up,FMath::DegreesToRadians(SpinDeg));
            return (TiltOut*Spin*AlignUp).GetNormalized();
        };

        auto TryGroundAndPlace=[&](const FVector2D& XY,float RadialDist,float OutAngleRad,float HeightM,float WidthM,float TiltOutDeg,float RiseSec,float HoldJitter,int32 Bucket,bool bHero,bool bSkipWallTrace,float RefZ,FVector* OutFloorPos)->bool
        {
            FVector Sample(Center.X+XY.X,Center.Y+XY.Y,RefZ);
            if(!bSkipWallTrace)
            {
                FHitResult WallHit;
                if(MagicOcclusion::TraceBlocker(GetWorld(),Center+FVector(0,0,85),Sample+FVector(0,0,85),Query,WallHit))return false;
            }
            FHitResult FloorHit;
            const float ProbeUp=bSkipWallTrace?140.f:260.f;
            const float ProbeDown=bSkipWallTrace?180.f:360.f;
            if(!GetWorld()->LineTraceSingleByChannel(FloorHit,Sample+FVector(0,0,ProbeUp),Sample-FVector(0,0,ProbeDown),ECC_Visibility,Query))return false;
            Sample=FloorHit.ImpactPoint;
            const FVector FloorNormal=FloorHit.ImpactNormal.IsNearlyZero()?FVector::UpVector:FloorHit.ImpactNormal.GetSafeNormal();
            if(OutFloorPos)*OutFloorPos=Sample;

            // Meshes have pivot cleanly at Z=0 with a -14 cm skirt: sink only 6-10 cm to lock firmly onto slopes.
            FRadialSpike S;
            S.BasePos=Sample-FloorNormal*(6.f+WidthM*3.5f);
            S.Rotation=OrientSpire(FloorNormal,OutAngleRad,TiltOutDeg,Rng.FRandRange(0.f,360.f));
            S.FullScale=FVector(WidthM,WidthM*Rng.FRandRange(.90f,1.12f),HeightM);
            S.TriggerRadius=FMath::Max(60.f,RadialDist);
            S.RiseSeconds=RiseSec;
            S.HoldSeconds=SpikeHoldBaseSeconds+HoldJitter;
            S.MeshBucket=FMath::Clamp(Bucket,0,SpikeISMs.Num()-1);
            S.bHeroSpire=bHero;

            FVector InitScale(.001f);
            if(bLateJoin)
            {
                const float TriggerAge=(S.TriggerRadius/BlastR)*ExpandSec;
                if(InitialAge>=TriggerAge)
                {
                    S.bSpawned=true;
                    S.Age=InitialAge-TriggerAge;
                    const float Rise=FMath::Max(.05f,S.RiseSeconds);
                    const float HoldEnd=Rise+S.HoldSeconds;
                    if(S.Age>=HoldEnd+SpikeShatterCollapseSeconds)
                    {
                        S.bHoldSettled=true;S.bShatterPopped=true;S.bCollapsed=true;
                        InitScale=FVector::ZeroVector;
                    }
                    else if(S.Age>=Rise&&S.Age<HoldEnd)
                    {
                        S.bHoldSettled=true;
                        InitScale=S.FullScale;
                    }
                }
            }
            S.InstanceIndex=SpikeISMs[S.MeshBucket]->AddInstance(FTransform(S.Rotation,S.BasePos,InitScale),true);
            if(bHero&&SpikeShellISMs.IsValidIndex(S.MeshBucket))
            {
                const FVector ShellInit=InitScale.IsNearlyZero()?FVector::ZeroVector:FVector(InitScale.X*1.032f,InitScale.Y*1.032f,InitScale.Z*1.012f);
                S.ShellInstanceIndex=SpikeShellISMs[S.MeshBucket]->AddInstance(FTransform(S.Rotation,S.BasePos,ShellInit),true);
            }
            RadialSpikes.Add(S);
            return true;
        };

        auto PlaceCluster=[&](float Frac,float AngleRad,int32 Tier)
        {
            const float Dist=BlastR*FMath::Clamp(Frac,.13f,.98f);
            const FVector2D HubXY(FMath::Cos(AngleRad)*Dist,FMath::Sin(AngleRad)*Dist);

            if(Tier==0)
            {
                const float H=Rng.FRandRange(.58f,1.15f);
                const float W=Rng.FRandRange(.82f,1.22f);
                const float Tilt=Rng.FRandRange(44.f,62.f);
                TryGroundAndPlace(HubXY,Dist,AngleRad,H,W,Tilt,Rng.FRandRange(.07f,.095f),Rng.FRandRange(-.10f,.08f),FangBucket,false,false,float(Center.Z),nullptr);
                return;
            }

            if(Tier==1)
            {
                const float H=FMath::Lerp(1.55f,2.65f,FMath::Clamp((Frac-.34f)/.38f,0.f,1.f))*Rng.FRandRange(.88f,1.14f);
                const float W=H*Rng.FRandRange(.62f,.78f);
                const float Tilt=Rng.FRandRange(20.f,35.f);
                const int32 HeroB=Rng.RandRange(0,HeroBuckets-1);
                FVector HeroFloor=Center;
                if(!TryGroundAndPlace(HubXY,Dist,AngleRad,H,W,Tilt,Rng.FRandRange(.085f,.115f),Rng.FRandRange(-.08f,.14f),HeroB,true,false,float(Center.Z),&HeroFloor))return;

                const int32 SatCount=Rng.RandRange(1,2);
                for(int32 K=0;K<SatCount;++K)
                {
                    const float SideSign=(K==0?-1.f:1.f)*Rng.FRandRange(.85f,1.25f);
                    const float OffAng=AngleRad+SideSign*Rng.FRandRange(.65f,1.25f);
                    const float OffDist=Rng.FRandRange(42.f,82.f)*FMath::Clamp(W*.7f,.75f,1.35f);
                    const FVector2D SatXY=HubXY+FVector2D(FMath::Cos(OffAng)*OffDist,FMath::Sin(OffAng)*OffDist);
                    const float SatH=H*Rng.FRandRange(.42f,.62f);
                    const float SatW=SatH*Rng.FRandRange(.76f,1.02f);
                    const int32 SatB=(K==0)?FangBucket:Rng.RandRange(0,HeroBuckets-1);
                    TryGroundAndPlace(SatXY,Dist+Rng.FRandRange(12.f,40.f),AngleRad+SideSign*.45f,SatH,SatW,Rng.FRandRange(34.f,52.f),Rng.FRandRange(.09f,.12f),Rng.FRandRange(-.10f,.10f),SatB,false,true,float(HeroFloor.Z),nullptr);
                }
                return;
            }

            const float OuterT=FMath::Clamp((Frac-.72f)/.26f,0.f,1.f);
            const float H=FMath::Lerp(2.95f,4.35f,OuterT)*Rng.FRandRange(.90f,1.12f);
            const float W=H*Rng.FRandRange(.52f,.68f);
            const float Tilt=Rng.FRandRange(10.f,23.f);
            const int32 HeroB=Rng.FRand()<.42f?(HeroBuckets-1):Rng.RandRange(0,HeroBuckets-1);
            FVector HeroFloor=Center;
            if(!TryGroundAndPlace(HubXY,Dist,AngleRad,H,W,Tilt,Rng.FRandRange(.10f,.135f),Rng.FRandRange(0.f,.24f),HeroB,true,false,float(Center.Z),&HeroFloor))return;

            for(int32 K=0;K<2;++K)
            {
                const float SideSign=(K==0?-1.f:1.f);
                const float OffAng=AngleRad+SideSign*Rng.FRandRange(.55f,1.30f);
                const float OffDist=Rng.FRandRange(68.f,122.f);
                const FVector2D SatXY=HubXY+FVector2D(FMath::Cos(OffAng)*OffDist,FMath::Sin(OffAng)*OffDist);
                const float SatH=H*Rng.FRandRange(.44f,.66f);
                const float SatW=SatH*Rng.FRandRange(.68f,.92f);
                const int32 SatB=(K==0)?FangBucket:Rng.RandRange(0,HeroBuckets-1);
                TryGroundAndPlace(SatXY,Dist+Rng.FRandRange(15.f,45.f),AngleRad+SideSign*.38f,SatH,SatW,Rng.FRandRange(26.f,46.f),Rng.FRandRange(.105f,.14f),Rng.FRandRange(-.04f,.20f),SatB,false,true,float(HeroFloor.Z),nullptr);
            }
        };

        // A) Inner crater ring: 18 low outward-leaning fang clusters (14%..34% R)
        for(int32 I=0;I<18;++I)
        {
            const float Ang=BaseAngle+(2.f*PI*float(I)/18.f)+Rng.FRandRange(-.16f,.16f);
            const float Frac=Rng.FRandRange(.14f,.33f);
            PlaceCluster(Frac,Ang,0);
        }

        // B) Mid glacier forest: 8 radiating fault rays (2 clusters/ray) + 10 organic filler clusters (34%..72% R)
        for(int32 Ray=0;Ray<NumRays;++Ray)
        {
            const float RayAng=BaseAngle+(2.f*PI*float(Ray)/float(NumRays))+Rng.FRandRange(-.12f,.12f);
            PlaceCluster(Rng.FRandRange(.37f,.51f),RayAng+Rng.FRandRange(-.09f,.09f),1);
            PlaceCluster(Rng.FRandRange(.55f,.70f),RayAng+Rng.FRandRange(-.12f,.12f),1);
        }
        for(int32 I=0;I<10;++I)
        {
            const float Ang=BaseAngle+(2.f*PI*(float(I)+.5f)/10.f)+Rng.FRandRange(-.18f,.18f);
            PlaceCluster(Rng.FRandRange(.40f,.69f),Ang,1);
        }

        // C) Outer monumental glacier crown: 32 towering monolith clusters ringing 72%..98% R!
        for(int32 I=0;I<32;++I)
        {
            const float Ang=BaseAngle+(2.f*PI*float(I)/32.f)+Rng.FRandRange(-.08f,.08f);
            const float Frac=(I%2==0)?Rng.FRandRange(.74f,.87f):Rng.FRandRange(.85f,.97f);
            PlaceCluster(Frac,Ang,2);
        }
    }

    // 5) Single ISM batch for ALL flying IceWall shrapnel shards + real 3D tumbling crystal eruption splinters
    if(auto* ShardMesh=Cast<UStaticMesh>(Assets[3]))
    {
        ShardISM=NewObject<UInstancedStaticMeshComponent>(this);
        AddInstanceComponent(ShardISM);
        ShardISM->SetupAttachment(RootComponent);
        ShardISM->SetStaticMesh(ShardMesh);
        if(ShardMat)ShardISM->SetMaterial(0,ShardMat);
        ShardISM->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        ShardISM->SetCanEverAffectNavigation(false);
        ShardISM->SetCastShadow(false);
        ShardISM->bReceivesDecals=false;
        ShardISM->SetCullDistances(0,7500);
        ShardISM->RegisterComponent();

        if(InitialAge<=1.35f)
        {
            BurstSplinterISM=NewObject<UInstancedStaticMeshComponent>(this);
            AddInstanceComponent(BurstSplinterISM);
            BurstSplinterISM->SetupAttachment(RootComponent);
            BurstSplinterISM->SetStaticMesh(ShardMesh);
            if(ShardMat)BurstSplinterISM->SetMaterial(0,ShardMat);
            BurstSplinterISM->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            BurstSplinterISM->SetCanEverAffectNavigation(false);
            BurstSplinterISM->SetCastShadow(false);
            BurstSplinterISM->bReceivesDecals=false;
            BurstSplinterISM->SetCullDistances(0,4500);
            BurstSplinterISM->RegisterComponent();

            const int32 SpSeed=int32(FMath::RoundToInt(Center.X*7.f+Center.Y*19.f))^int32(FMath::RoundToInt(NetStartedAt*100.0))^0x3D51A8;
            FRandomStream SpRng(SpSeed);
            constexpr int32 SplinterCount=64;
            BurstSplinters.Reserve(SplinterCount);
            for(int32 K=0;K<SplinterCount;++K)
            {
                const float Ang=SpRng.FRandRange(0.f,2.f*PI);
                const float StartR=CastSnapshot.Radius*SpRng.FRandRange(.14f,.88f);
                const float OutSpd=SpRng.FRandRange(220.f,740.f);
                FBurstSplinter B;
                B.Position=Center+FVector(FMath::Cos(Ang)*StartR,FMath::Sin(Ang)*StartR,SpRng.FRandRange(18.f,85.f));
                B.Velocity=FVector(FMath::Cos(Ang)*OutSpd,FMath::Sin(Ang)*OutSpd,SpRng.FRandRange(260.f,640.f));
                B.Rotation=FRotator(SpRng.FRandRange(-180.f,180.f),SpRng.FRandRange(-180.f,180.f),SpRng.FRandRange(-180.f,180.f));
                B.SpinRate=FRotator(SpRng.FRandRange(-520.f,520.f),SpRng.FRandRange(-520.f,520.f),SpRng.FRandRange(-520.f,520.f));
                B.Scale=SpRng.FRandRange(.55f,1.45f);
                B.Life=SpRng.FRandRange(.62f,1.18f);
                B.Delay=(StartR/FMath::Max(1.f,CastSnapshot.Radius))*FMath::Max(.12f,CastSnapshot.ExpandSeconds);
                B.InstanceIndex=BurstSplinterISM->AddInstance(FTransform(B.Rotation,B.Position,FVector::ZeroVector),true);
                BurstSplinters.Add(B);
            }
        }
        else bBurstSplintersDone=true;
    }

    // 6) Multi-layer explosive cryo VFX:
    //    - Dedicated 360-deg outward ground cryo-fog wall + feathered snow powder (NS_AbsoluteZeroBurstWave)
    //    - Ground-slam radial frost dust burst (NS_IceWallLanding)
    if(auto* BurstSys=Cast<UNiagaraSystem>(Assets[16]))
    {
        BurstWaveFX=UNiagaraFunctionLibrary::SpawnSystemAttached(BurstSys,RootComponent,NAME_None,FVector::ZeroVector,FRotator::ZeroRotator,EAttachLocation::KeepRelativeOffset,false,false);
        if(BurstWaveFX)
        {
            BurstWaveFX->SetAbsolute(false,true,true);
            BurstWaveFX->SetVariablePosition(TEXT("User.Center"),Center);
            BurstWaveFX->SetVariableFloat(TEXT("User.Radius"),CastSnapshot.Radius);
            BurstWaveFX->SetVariableFloat(TEXT("User.Strength"),InitialAge<2.20f?1.f:FMath::Clamp(1.f-(InitialAge-2.20f)/.90f,0.f,1.f));
            BurstWaveFX->SetVariableFloat(TEXT("User.BurstActive"),bLateJoin?0.f:1.f);
            const float Bnd=CastSnapshot.Radius+450.f;
            BurstWaveFX->SetSystemFixedBounds(FBox(FVector(-Bnd,-Bnd,-260.f),FVector(Bnd,Bnd,820.f)));
            BurstWaveFX->Activate(true);
        }
    }
    if(!bLateJoin)
    {
        if(auto* SlamFX=Cast<UNiagaraSystem>(Assets[4]))
        {
            if(auto* FX=UNiagaraFunctionLibrary::SpawnSystemAtLocation(this,SlamFX,Center+FVector(0,0,8),FRotator::ZeroRotator,FVector(1.8f),true,true,ENCPoolMethod::AutoRelease))
            {
                FX->SetVariableVec3(TEXT("User.WallSize"),FVector(320.f,FMath::Min(960.f,CastSnapshot.Radius*.9f),220.f));
                FX->SetVariableFloat(TEXT("User.DustCount"),48.f);
                FX->SetVariableFloat(TEXT("User.MistCount"),32.f);
                FX->SetVariableFloat(TEXT("User.DetailReduction"),0.f);
            }
        }
        if(auto* Boom=Cast<USoundBase>(Assets[7]))
            UGameplayStatics::PlaySoundAtLocation(this,Boom,Center,1.25f,.80f);
        if(auto* ShatterSfx=Cast<USoundBase>(Assets[8]))
            UGameplayStatics::PlaySoundAtLocation(this,ShatterSfx,Center,1.05f,.72f);
        ShakeNearbyPlayers(1.20f);
    }
}

void AFPSAbsoluteZeroNova::ShakeNearbyPlayers(float Multiplier) const
{
    UWorld* World=GetWorld();if(!World)return;
    for(FConstPlayerControllerIterator It=World->GetPlayerControllerIterator();It;++It)
    {
        APlayerController* PC=It->Get();
        if(!PC||!PC->IsLocalController()||!PC->PlayerCameraManager)continue;
        const APawn* ViewPawn=PC->GetPawn();
        const FVector ViewLoc=ViewPawn?ViewPawn->GetActorLocation():PC->PlayerCameraManager->GetCameraLocation();
        const float Dist=FVector::Dist(ViewLoc,Center);
        if(Dist>CastSnapshot.Radius*1.5f)continue;
        const float Scale=FMath::Lerp(1.15f,.25f,FMath::Clamp(Dist/FMath::Max(1.f,CastSnapshot.Radius*1.5f),0.f,1.f))*Multiplier;
        PC->PlayerCameraManager->StartCameraShake(UIceWallLandingCameraShake::StaticClass(),Scale);
    }
}

void AFPSAbsoluteZeroNova::StepWaveAuthority(float PrevRadius,float CurrRadius)
{
    if(!HasAuthority())return;
    APawn* Shooter=Caster.Get();
    UColdSteelStatusModel* Model=RewardModel.Get();
    UWorld* World=GetWorld();
    if(!Shooter||!Model||!World)return;

    // 1) Detonate caster's own Solid IceWalls as the shockwave ring crosses them.
    for(int32 I=0;I<QueuedWalls.Num();++I)
    {
        auto& Q=QueuedWalls[I];
        if(Q.bDetonated||CurrRadius<Q.TriggerDistance)continue;
        Q.bDetonated=true;
        if(AFPSIceWall* Wall=Q.Wall.Get();IsValid(Wall)&&Wall->IsSolid())
            Wall->Shatter();
        LaunchShardsForWall(I,Q.Snapshot);
    }

    // 2) Sweep enemies newly engulfed by the expanding frost wave.
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_Pawn);
    Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    Objects.AddObjectTypesToQuery(ECC_PhysicsBody);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(AbsoluteZeroWave),false,this);
    Query.AddIgnoredActor(Shooter);
    for(const auto& Q:QueuedWalls)if(Q.Wall.IsValid())Query.AddIgnoredActor(Q.Wall.Get());

    TArray<FOverlapResult> Overlaps;
    World->OverlapMultiByObjectType(Overlaps,Center+FVector(0,0,70),FQuat::Identity,Objects,
        FCollisionShape::MakeSphere(CurrRadius),Query);
    int32 BatchHits=0;
    for(const auto& Ov:Overlaps)
    {
        AActor* Target=Ov.GetActor();
        if(!IsValid(Target)||Target==Shooter||HitTargets.Contains(Target))continue;
        const auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
        if(!Combat||Combat->IsDead()||HolyLightTargets::IsFriendly(Target))continue;
        const float VertGap=FMath::Abs(Target->GetActorLocation().Z-Center.Z);
        if(VertGap>380.f)continue;
        float Dist=0.f;
        if(!MagicOcclusion::BlastExposure(World,Shooter,Target,Center+FVector(0,0,75),CurrRadius+35.f,Query,Dist))continue;
        HitTargets.Add(Target);
        const int32 Before=Rewards.Hits;
        if(Model->ApplyAbsoluteZeroNovaHit(Shooter,Target,CastSnapshot,Dist,Rewards))
            BatchHits+=FMath::Max(1,Rewards.Hits-Before);
    }
    if(HitTargets.Num()>=2||BatchHits>=2)Rewards.bMultiHit=true;
}

void AFPSAbsoluteZeroNova::LaunchShardsForWall(int32 WallIndex,const FAbsoluteZeroDetonatedWall& Snap)
{
    const int32 Count=FMath::Clamp(Snap.ShardCount,1,CastSnapshot.MaxShardsPerWall);
    FRandomStream Rng(Snap.Seed);
    const FVector Right=Snap.Rotation.RotateVector(FVector::RightVector);
    const FVector WallMid=Snap.Location+Right*((Snap.MinAlong+Snap.MaxAlong)*.5f);
    FVector Outward=(WallMid-Center).GetSafeNormal2D();
    if(Outward.IsNearlyZero())Outward=Snap.Rotation.RotateVector(FVector::ForwardVector).GetSafeNormal2D();

    for(int32 K=0;K<Count;++K)
    {
        const float U=(float(K)+.5f)/float(Count);
        const float Along=FMath::Lerp(Snap.MinAlong,Snap.MaxAlong,U);
        const float LocalZ=Rng.FRandRange(45.f,FMath::Max(65.f,Snap.Height*.82f));
        const FVector Origin=Snap.Location+Right*Along+FVector(0,0,LocalZ);
        FVector BaseDir=(Origin-Center).GetSafeNormal2D();
        if(BaseDir.IsNearlyZero())BaseDir=Outward;
        const float YawSpread=Rng.FRandRange(-CastSnapshot.WallShardConeDegrees,CastSnapshot.WallShardConeDegrees);
        const float PitchSpread=Rng.FRandRange(-3.f,9.f);
        const FVector Dir=FRotator(PitchSpread,YawSpread,0.f).RotateVector(BaseDir).GetSafeNormal();

        FWallShard Shard;
        Shard.Position=Origin+Dir*28.f;
        Shard.Velocity=Dir*(CastSnapshot.WallShardSpeed*Rng.FRandRange(.88f,1.12f));
        Shard.MaxRange=CastSnapshot.WallShardRange*Rng.FRandRange(.85f,1.08f);
        Shard.HealthRatio=Snap.HealthRatio;
        Shard.Scale=Rng.FRandRange(1.1f,1.65f);
        Shard.WallIndex=WallIndex;
        Shard.bActive=true;
        if(ShardISM)
            Shard.InstanceIndex=ShardISM->AddInstance(FTransform(Dir.Rotation(),Shard.Position,FVector(Shard.Scale)),true);
        Shards.Add(Shard);
    }

    if(GetNetMode()!=NM_DedicatedServer)
    {
        if(auto* ShatterSfx=Cast<USoundBase>(Assets[8]))
            UGameplayStatics::PlaySoundAtLocation(this,ShatterSfx,WallMid,1.1f,.92f);
        if(auto* BreakFX=Cast<UParticleSystem>(Assets[6]))
            UGameplayStatics::SpawnEmitterAtLocation(GetWorld(),BreakFX,WallMid+FVector(0,0,80),Outward.Rotation(),FVector(2.f));
    }
}

void AFPSAbsoluteZeroNova::StepShards(float Delta)
{
    if(Shards.IsEmpty())return;
    UWorld* World=GetWorld();if(!World)return;
    APawn* Shooter=Caster.Get();
    UColdSteelStatusModel* Model=HasAuthority()?RewardModel.Get():nullptr;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(AbsoluteZeroShard),false,this);
    Query.AddIgnoredActor(Shooter);
    for(const auto& Q:QueuedWalls)if(Q.Wall.IsValid())Query.AddIgnoredActor(Q.Wall.Get());

    FCollisionObjectQueryParams HitObjects;
    HitObjects.AddObjectTypesToQuery(ECC_WorldStatic);
    HitObjects.AddObjectTypesToQuery(ECC_WorldDynamic);
    HitObjects.AddObjectTypesToQuery(ECC_Pawn);
    HitObjects.AddObjectTypesToQuery(ECC_PhysicsBody);

    bool bDirtyISM=false;
    for(auto& S:Shards)
    {
        if(!S.bActive)continue;
        S.Velocity.Z-=260.f*Delta; // Subtle ballistic gravity
        const FVector Next=S.Position+S.Velocity*Delta;
        const float StepLen=FVector::Dist(S.Position,Next);

        FHitResult Hit;
        const bool bBlocked=World->SweepSingleByObjectType(Hit,S.Position,Next,FQuat::Identity,HitObjects,FCollisionShape::MakeSphere(18.f),Query);
        if(bBlocked)
        {
            AActor* Target=Hit.GetActor();
            bool bHandledEnemy=false;
            if(IsValid(Target)&&Target!=Shooter&&!HolyLightTargets::IsFriendly(Target))
            {
                if(const auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();Combat&&!Combat->IsDead())
                {
                    bHandledEnemy=true;
                    if(HasAuthority()&&Shooter&&Model)
                    {
                        int32& CountRef=ShardHitsPerTarget.FindOrAdd(Target);
                        Model->ApplyAbsoluteZeroWallShardHit(Shooter,Target,CastSnapshot,S.HealthRatio,CountRef,Rewards);
                        ++CountRef;
                    }
                }
            }
            if(bHandledEnemy||!Target||!Target->FindComponentByClass<UMonsterCombatComponent>())
            {
                S.bActive=false;
                if(GetNetMode()!=NM_DedicatedServer)
                    if(auto* ImpactFX=Cast<UParticleSystem>(Assets[6]))
                        UGameplayStatics::SpawnEmitterAtLocation(World,ImpactFX,Hit.ImpactPoint,Hit.ImpactNormal.Rotation(),FVector(.9f));
                if(ShardISM&&S.InstanceIndex!=INDEX_NONE)
                {
                    ShardISM->UpdateInstanceTransform(S.InstanceIndex,FTransform(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector),true,false,true);
                    bDirtyISM=true;
                }
                continue;
            }
        }

        S.Position=Next;
        S.DistanceTraveled+=StepLen;
        if(S.DistanceTraveled>=S.MaxRange)
        {
            S.bActive=false;
            if(ShardISM&&S.InstanceIndex!=INDEX_NONE)
            {
                ShardISM->UpdateInstanceTransform(S.InstanceIndex,FTransform(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector),true,false,true);
                bDirtyISM=true;
            }
            continue;
        }
        if(ShardISM&&S.InstanceIndex!=INDEX_NONE)
        {
            ShardISM->UpdateInstanceTransform(S.InstanceIndex,FTransform(S.Velocity.GetSafeNormal().Rotation(),S.Position,FVector(S.Scale)),true,false,true);
            bDirtyISM=true;
        }
    }
    if(bDirtyISM&&ShardISM)ShardISM->MarkRenderStateDirty();
}

void AFPSAbsoluteZeroNova::UpdateVisuals(float Delta,float CurrRadius)
{
    if(GetNetMode()==NM_DedicatedServer)return;

    // 1) Sweep the crystalline frost sheet & leading glowing freeze-front smoothly across all ground surfaces.
    const float ExpandAlpha=FMath::Clamp(Age/FMath::Max(.08f,CastSnapshot.ExpandSeconds),0.f,1.f);
    const float FrostFade=Age<2.25f?1.f:FMath::Clamp(1.f-(Age-2.25f)/1.25f,0.f,1.f);
    if(FrostSurface)
    {
        const float Reveal=FMath::Clamp(CurrRadius/FMath::Max(1.f,CastSnapshot.Radius),.04f,1.f)*1.08f;
        const float Emissive=FMath::Lerp(1.65f,.14f,FMath::Clamp(Age/FMath::Max(.1f,CastSnapshot.ExpandSeconds+.42f),0.f,1.f));
        if(FrostMID)
        {
            FrostMID->SetScalarParameterValue(TEXT("RevealRadius"),Reveal);
            FrostMID->SetScalarParameterValue(TEXT("Fade"),FrostFade);
            FrostMID->SetScalarParameterValue(TEXT("EmissiveBoost"),Emissive);
        }
        FrostSurface->SetVisibility(FrostFade>.01f);
    }

    // 1b) Expand the 360-deg 3D cryo shockwave ring cleanly along the blast frontier.
    if(ShockRing)
    {
        const float RingDur=FMath::Max(.24f,CastSnapshot.ExpandSeconds+.16f);
        const float RingT=FMath::Clamp(Age/RingDur,0.f,1.f);
        const float RingFade=RingT<.72f?1.f:FMath::Clamp(1.f-(RingT-.72f)/.28f,0.f,1.f);
        const float RingR=FMath::Lerp(130.f,CastSnapshot.Radius*1.08f,FMath::InterpEaseOut(0.f,1.f,RingT,1.65f));
        const float RingXY=RingR/100.f;
        const float RingZ=FMath::Lerp(.90f,2.35f,RingT);
        ShockRing->SetWorldScale3D(FVector(RingXY,RingXY,RingZ));
        ShockRing->SetVisibility(RingFade>.01f);
        if(ShockRingMID)
        {
            ShockRingMID->SetScalarParameterValue(TEXT("WaveProgress"),RingT);
            ShockRingMID->SetScalarParameterValue(TEXT("Fade"),RingFade);
        }
    }

    // 1c) Secondary ground tremor right as mid/outer glacier monoliths rip upward, plus BurstWave fadeout.
    if(!bSecondTremorDone&&Age>=.18f)
    {
        bSecondTremorDone=true;
        ShakeNearbyPlayers(.65f);
    }
    if(BurstWaveFX)
    {
        BurstWaveFX->SetVariableFloat(TEXT("User.BurstActive"),Age<.42f?1.f:0.f);
        const float MistStrength=Age<2.20f?1.f:FMath::Clamp(1.f-(Age-2.20f)/.90f,0.f,1.f);
        BurstWaveFX->SetVariableFloat(TEXT("User.Strength"),MistStrength);
    }

    // 2) Fade cryo detonation flash light & drive global spire shader flash/pre-shatter crack surge.
    if(FlashLight)
    {
        const float LightAlpha=FMath::Clamp(1.f-Age/.62f,0.f,1.f);
        FlashLight->SetIntensity(28000.f*LightAlpha*LightAlpha);
        FlashLight->SetVisibility(LightAlpha>.01f);
    }
    const float EruptFlash=FMath::Clamp(1.f-Age/.34f,0.f,1.f);
    const float ShatterStart=CastSnapshot.ExpandSeconds+SpikeHoldBaseSeconds-.30f;
    const float ShatterAlpha=FMath::Clamp((Age-ShatterStart)/.32f,0.f,1.f);
    if(SpireMID)
    {
        SpireMID->SetScalarParameterValue(TEXT("EruptionFlash"),EruptFlash*EruptFlash);
        SpireMID->SetScalarParameterValue(TEXT("ShatterGlow"),ShatterAlpha);
    }
    if(SpireShellMID)
    {
        SpireShellMID->SetScalarParameterValue(TEXT("EruptionFlash"),EruptFlash*EruptFlash);
        SpireShellMID->SetScalarParameterValue(TEXT("ShatterGlow"),ShatterAlpha);
    }

    // 2b) Step real 3D tumbling crystal eruption splinters (stops cleanly once all 64 finish).
    if(!bBurstSplintersDone&&BurstSplinterISM&&!BurstSplinters.IsEmpty())
    {
        bool bSplinterDirty=false;
        bool bAnySplinterAlive=false;
        for(auto& B:BurstSplinters)
        {
            if(!B.bActive||B.InstanceIndex==INDEX_NONE)continue;
            bAnySplinterAlive=true;
            if(Age<B.Delay)continue;
            B.Age+=Delta;
            if(B.Age>=B.Life||B.Position.Z<Center.Z-240.f)
            {
                B.bActive=false;
                BurstSplinterISM->UpdateInstanceTransform(B.InstanceIndex,FTransform(FQuat::Identity,B.Position,FVector::ZeroVector),true,false,true);
                bSplinterDirty=true;
                continue;
            }
            B.Velocity.Z-=920.f*Delta;
            B.Position+=B.Velocity*Delta;
            B.Rotation+=B.SpinRate*Delta;
            const float T=FMath::Clamp(B.Age/B.Life,0.f,1.f);
            const float FadeScale=T<.75f?1.f:FMath::Clamp(1.f-(T-.75f)/.25f,0.f,1.f);
            BurstSplinterISM->UpdateInstanceTransform(B.InstanceIndex,FTransform(B.Rotation,B.Position,FVector(B.Scale*FadeScale)),true,false,true);
            bSplinterDirty=true;
        }
        if(bSplinterDirty)BurstSplinterISM->MarkRenderStateDirty();
        if(!bAnySplinterAlive)
        {
            bBurstSplintersDone=true;
            BurstSplinterISM->SetVisibility(false);
        }
    }

    // 3) Violent snap-eruption with elastic overshoot -> ZERO-WRITE static hold -> crisp shatter collapse!
    if(!RadialSpikes.IsEmpty())
    {
        TArray<bool> Dirty;Dirty.Init(false,SpikeISMs.Num());
        TArray<bool> ShellDirty;ShellDirty.Init(false,SpikeShellISMs.Num());
        UParticleSystem* ShatterFX=Cast<UParticleSystem>(Assets[6]);
        for(auto& S:RadialSpikes)
        {
            if(S.bCollapsed)continue;
            if(!S.bSpawned&&CurrRadius>=S.TriggerRadius)S.bSpawned=true;
            if(!S.bSpawned||!SpikeISMs.IsValidIndex(S.MeshBucket)||S.InstanceIndex==INDEX_NONE)continue;
            S.Age+=Delta;
            const float Rise=FMath::Max(.05f,S.RiseSeconds);
            const float HoldEnd=Rise+S.HoldSeconds;
            float ScaleZ=0.f,ScaleXY=0.f;
            if(S.Age<Rise)
            {
                const float U=FMath::Clamp(S.Age/Rise,0.f,1.f);
                const float BaseCurve=FMath::InterpEaseOut(0.f,1.f,U,2.4f);
                const float Overshoot=FMath::Sin(U*PI)*0.16f*(1.f-U*.35f);
                ScaleZ=BaseCurve+Overshoot;
                ScaleXY=FMath::InterpEaseOut(.25f,1.f,U,2.0f)+Overshoot*.45f;
            }
            else if(S.Age<HoldEnd)
            {
                // Write exact resting 1.0 transform ONCE on entering Hold, then skip GPU uploads for ~1.42s!
                if(S.bHoldSettled)continue;
                S.bHoldSettled=true;
                ScaleZ=1.f;ScaleXY=1.f;
            }
            else
            {
                if(!S.bShatterPopped)
                {
                    S.bShatterPopped=true;
                    if(!bShatterAudioPlayed)
                    {
                        bShatterAudioPlayed=true;
                        if(auto* ShatterSfx=Cast<USoundBase>(Assets[8]))
                            UGameplayStatics::PlaySoundAtLocation(this,ShatterSfx,Center,.95f,.92f);
                    }
                    if(S.bHeroSpire&&ShatterFX&&ShatterBurstsSpawned<MaxShatterBursts)
                    {
                        ++ShatterBurstsSpawned;
                        const FVector BurstLoc=S.BasePos+FVector(0,0,S.FullScale.Z*52.f);
                        UGameplayStatics::SpawnEmitterAtLocation(GetWorld(),ShatterFX,BurstLoc,FRotator::ZeroRotator,FVector(FMath::Clamp(S.FullScale.Z*.55f,.95f,2.1f)));
                    }
                }
                const float Collapse=FMath::Clamp(1.f-(S.Age-HoldEnd)/SpikeShatterCollapseSeconds,0.f,1.f);
                ScaleZ=Collapse*Collapse;
                ScaleXY=FMath::Lerp(1.12f,0.f,1.f-Collapse);
                if(ScaleZ<=.005f||ScaleXY<=.005f)S.bCollapsed=true;
            }
            const FVector Scale=(ScaleZ>.005f&&ScaleXY>.005f)?FVector(S.FullScale.X*ScaleXY,S.FullScale.Y*ScaleXY,S.FullScale.Z*ScaleZ):FVector::ZeroVector;
            SpikeISMs[S.MeshBucket]->UpdateInstanceTransform(S.InstanceIndex,FTransform(S.Rotation,S.BasePos,Scale),true,false,true);
            Dirty[S.MeshBucket]=true;
            if(S.ShellInstanceIndex!=INDEX_NONE&&SpikeShellISMs.IsValidIndex(S.MeshBucket))
            {
                const FVector ShellScale=Scale.IsNearlyZero()?FVector::ZeroVector:FVector(Scale.X*1.032f,Scale.Y*1.032f,Scale.Z*1.012f);
                SpikeShellISMs[S.MeshBucket]->UpdateInstanceTransform(S.ShellInstanceIndex,FTransform(S.Rotation,S.BasePos,ShellScale),true,false,true);
                ShellDirty[S.MeshBucket]=true;
            }
        }
        for(int32 B=0;B<Dirty.Num();++B)if(Dirty[B])SpikeISMs[B]->MarkRenderStateDirty();
        for(int32 B=0;B<ShellDirty.Num();++B)if(ShellDirty[B])SpikeShellISMs[B]->MarkRenderStateDirty();
    }

    // 4) Non-authority clients trigger local visual shrapnel bursts deterministically at exact server TriggerDistance.
    if(!HasAuthority())
    {
        for(int32 I=0;I<NetWalls.Num();++I)
        {
            if(ClientWallDetonated.IsValidIndex(I)&&ClientWallDetonated[I])continue;
            const auto& W=NetWalls[I];
            if(CurrRadius>=FMath::Max(60.f,W.TriggerDistance))
            {
                if(ClientWallDetonated.IsValidIndex(I))ClientWallDetonated[I]=true;
                LaunchShardsForWall(I,W);
            }
        }
    }
    (void)ExpandAlpha;
}

void AFPSAbsoluteZeroNova::Tick(float Delta)
{
    Super::Tick(Delta);
    if(!HasAuthority()&&bNetActivated&&!bActivated)
    {
        Caster=NetCaster;CastSnapshot=NetCast;Center=NetCenter;
        SetActorLocation(Center);
        bActivated=true;
        const auto* GS=GetWorld()->GetGameState();
        const double Now=GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
        Age=FMath::Max(0.f,float(Now-NetStartedAt));
        BuildClientVisuals();
    }
    if(!bActivated)return;

    Age+=Delta;
    const float ExpandAlpha=FMath::Clamp(Age/FMath::Max(.08f,CastSnapshot.ExpandSeconds),0.f,1.f);
    const float CurrRadius=CastSnapshot.Radius*ExpandAlpha;
    if(HasAuthority()&&PreviousWaveRadius<CastSnapshot.Radius)
    {
        StepWaveAuthority(PreviousWaveRadius,CurrRadius);
        PreviousWaveRadius=CurrRadius;
    }
    StepShards(Delta);
    UpdateVisuals(Delta,CurrRadius);

    bool bAnyShard=false;
    for(const auto& S:Shards)if(S.bActive){bAnyShard=true;break;}
    if(Age>=TotalVisualSeconds&&!bAnyShard)
    {
        Finish();
        if(HasAuthority())Destroy();
    }
}

void AFPSAbsoluteZeroNova::Finish()
{
    if(bFinished)return;
    bFinished=true;
    if(HasAuthority())
    {
        auto Batch=MoveTemp(Rewards);Rewards={};
        auto* Model=RewardModel.Get();RewardModel.Reset();
        const auto* Health=Caster.IsValid()?Caster->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
        if(Model&&(!Health||!Health->IsDead()))Model->FinishAbsoluteZeroCast(Batch);
    }
}

void AFPSAbsoluteZeroNova::FinishForRemoval()
{
    if(HasAuthority()&&bActivated)Finish();
}

void AFPSAbsoluteZeroNova::EndPlay(EEndPlayReason::Type Reason)
{
    Finish();
    Super::EndPlay(Reason);
}
