#include "HighVillageDefense.h"
#include "VillageMasonry.h"
#include "HighVillageCollapse.h"
#include "VillageGateMotionAudio.h"
#include "VillagePortcullisHoist.h"
#include "VillageShopTorches.h"
#include "../Building/BronzeTorch.h"
#include "Components/ChildActorComponent.h"
#include "Sound/SoundWave.h"
#include "UObject/ConstructorHelpers.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "Net/UnrealNetwork.h"

namespace
{
    const FSoftObjectPath HighWall = VillageMasonry::CastleMesh(TEXT("SM_HighWall"));
    FSoftObjectPath SquareKeepMesh(const FString& Name)
    {
        return FSoftObjectPath(FString(VillageMasonry::CastleFolder) + TEXT("SquareKeep/") + Name + TEXT(".") + Name);
    }
    const FSoftObjectPath WestPortal = SquareKeepMesh(TEXT("SM_HighPortalGalleryWest"));
    const FSoftObjectPath EastPortal = SquareKeepMesh(TEXT("SM_HighPortalGalleryEast"));
    const FSoftObjectPath WestGrille=SquareKeepMesh(TEXT("SM_GateWroughtGrilleWest"));
    const FSoftObjectPath EastGrille=SquareKeepMesh(TEXT("SM_GateWroughtGrilleEast"));
    const FSoftObjectPath ReleaseMesh=SquareKeepMesh(TEXT("SM_GateReleaseHandle"));
    constexpr float HoistSpeed=145.f;
}

void AHighVillageWall::AddHighAssetPaths(TArray<FSoftObjectPath>& Paths)
{
    for(const auto* Mesh : {&HighWall,&WestPortal,&EastPortal,&WestGrille,&EastGrille,&ReleaseMesh}) Paths.AddUnique(*Mesh);
    AHighVillageCollapse::AddAssetPaths(Paths);
    if (!IsRunningDedicatedServer()) UVillagePortcullisHoist::AddAssetPaths(Paths);
}

const FSoftObjectPath& AHighVillageWall::WallMeshPath() { return HighWall; }
const FSoftObjectPath& AHighVillageGate::PlacedPortalMeshPath() { return PlacedPortalMeshPath(false); }
const FSoftObjectPath& AHighVillageGate::PlacedPortalMeshPath(bool bWest) { return bWest ? WestPortal : EastPortal; }
const FSoftObjectPath& AHighVillageGate::PlacedGrilleMeshPath() { return PlacedGrilleMeshPath(false); }
const FSoftObjectPath& AHighVillageGate::PlacedGrilleMeshPath(bool bWest) { return bWest ? WestGrille : EastGrille; }

void AHighVillageWall::InitializeHighWall(ATemperateHillsWorld* Hills,int32 Id,const FGuid& BuiltId)
{
    Initialize(Hills,Id,HighWall,2600.f,BuiltId);
}

void AHighVillageWall::PresentCollapse(const FVector& Direction,int32 Seed,float)
{
    AHighVillageCollapse::Wall(*this,Direction,Seed);
}

AHighVillageGate::AHighVillageGate()
{
    MotionAudio=CreateDefaultSubobject<UVillageGateMotionAudio>(TEXT("GateMotionAudio"));
    MotionAudio->SetupAttachment(RootComponent);
    static ConstructorHelpers::FObjectFinder<USoundWave> Cue(TEXT("/Game/WorldGeneration/TemperateHills/VillageDefenses/GateAudio/S_VillageIronGate"));
    MotionAudio->SetSound(Cue.Object);
    Tags.Add(TEXT("VillageGate"));
    RepairSoulCost=150;
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.bStartWithTickEnabled=false;
    SetNetUpdateFrequency(15.f);
    Masonry->ComponentTags.Remove(TEXT("Traversal.FixedStructure"));
    Portal=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("StonePortal"));
    Portal->SetupAttachment(RootComponent);
    Portal->SetMobility(EComponentMobility::Movable);
    Portal->SetCollisionProfileName(TEXT("BlockAll"));
    Portal->SetGenerateOverlapEvents(false);
    Portal->ComponentTags.Add(TEXT("Traversal.FixedStructure"));
    ReleaseHandle=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("GateRelease"));
    ReleaseHandle->SetupAttachment(RootComponent);
    ReleaseHandle->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    ReleaseHandle->SetCollisionResponseToAllChannels(ECR_Ignore);
    ReleaseHandle->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    ReleaseHandle->SetGenerateOverlapEvents(false);
    ReleaseHandle->SetCanEverAffectNavigation(false);

}

void AHighVillageGate::InitializeHighGate(ATemperateHillsWorld* Hills,int32 Id,bool bWest,const FGuid& BuiltId)
{
    Initialize(Hills,Id,PlacedGrilleMeshPath(bWest),2000.f,BuiltId);
}

void AHighVillageGate::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AHighVillageGate,LiftCm);
    DOREPLIFETIME(AHighVillageGate,bWantsOpen);
}

float AHighVillageGate::TravelCm() const { return MeshPath==WestGrille ? 500.f : 480.f; }

void AHighVillageGate::Pose(float Height)
{
    DisplayLift=Height;
    ReleaseHandle->SetRelativeTransform(ReleasePose(MeshPath==WestGrille,Height/TravelCm()));
    Masonry->SetRelativeLocation(FVector(0,0,Height));
    if (Hoist) Hoist->FollowGate(Height, Health > 0.f);
}

void AHighVillageGate::OnRep_Setup()
{
    Super::OnRep_Setup();
    if(MeshPath.IsNull())return;
    SetupHoist();
    const bool bWest=MeshPath==WestGrille;
    const FSoftObjectPath& Frame=PlacedPortalMeshPath(bWest);
    UStaticMesh* PortalMesh=Cast<UStaticMesh>(Frame.ResolveObject());
    UStaticMesh* Handle=Cast<UStaticMesh>(ReleaseMesh.ResolveObject());
    if(PortalMesh && Handle)
    {
        Portal->SetStaticMesh(PortalMesh);
        ReleaseHandle->SetStaticMesh(Handle);
        ReleaseHandle->SetRelativeTransform(ReleasePose(bWest,DisplayLift/TravelCm()));
        if(!ControlTorch && GetNetMode()!=NM_DedicatedServer)
        {
            ControlTorch=NewObject<UChildActorComponent>(this,NAME_None,RF_Transient);
            ControlTorch->SetupAttachment(RootComponent);
            ControlTorch->SetRelativeTransform(FTransform(FRotator(0,180,0),FVector(bWest?367.:267.,89.,133.)));
            ControlTorch->SetChildActorClass(ABronzeTorch::StaticClass());
            AddInstanceComponent(ControlTorch);
            ControlTorch->RegisterComponent();
            if(auto* Torch=Cast<ABronzeTorch>(ControlTorch->GetChildActor()))
            {
                VillageShopTorches::ConfigureWallTorch(*Torch,96.f,400.f);
                Torch->SetLit(true);
            }
        }
        VillageMasonry::ApplyWallPhase(*Portal,SectionId);
        PortalLoad.Reset();
    }
    else if(!PortalLoad.IsValid())
        PortalLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(TArray<FSoftObjectPath>{Frame,ReleaseMesh},
            FStreamableDelegate::CreateUObject(this,&AHighVillageGate::OnRep_Setup));
}

void AHighVillageGate::SetupHoist()
{
    if (Hoist || GetNetMode() == NM_DedicatedServer) return;
    if (UVillagePortcullisHoist::AssetsReady())
    {
        Hoist = NewObject<UVillagePortcullisHoist>(this, NAME_None, RF_Transient);
        Hoist->RegisterComponent();
        Hoist->Initialize(MeshPath == WestGrille);
        Hoist->FollowGate(DisplayLift, Health > 0.f);
        HoistLoad.Reset();
    }
    else if (!HoistLoad.IsValid())
    {
        TArray<FSoftObjectPath> Parts;
        UVillagePortcullisHoist::AddAssetPaths(Parts);
        HoistLoad = UAssetManager::GetStreamableManager().RequestAsyncLoad(Parts,
            FStreamableDelegate::CreateUObject(this, &AHighVillageGate::SetupHoist));
    }
}

void AHighVillageGate::ApplyHealth()
{
    if(Health<=0.f)
    {
        MotionAudio->ResetForBreach();
        if(HasAuthority())LiftCm=0.f;
        bWantsOpen=false;
        Pose(0.f);
        SetActorTickEnabled(false);
    }
    Super::ApplyHealth();
    if (Health > 0.f && Hoist) Hoist->FollowGate(DisplayLift, true);
}

void AHighVillageGate::PostNetInit()
{
    Super::PostNetInit();
    Pose(Health>0.f?LiftCm:0.f);
    SetActorTickEnabled(false);
}

void AHighVillageGate::OnRep_Lift()
{
    if(Health>0.f)SetActorTickEnabled(true);
}

const FSoftObjectPath& AHighVillageGate::ReleaseMeshPath() { return ReleaseMesh; }

FTransform AHighVillageGate::ReleasePose(bool bWest,float Fraction)
{
    return FTransform(FRotator(0.,0.,FMath::Lerp(-34.f,34.f,FMath::Clamp(Fraction,0.f,1.f))),
                      FVector(bWest?326.:226.,156.,113.));
}

EHighGateUse AHighVillageGate::ResolveUse(const FHitResult& Hit) const
{
    if(Hit.GetComponent()==ReleaseHandle)return EHighGateUse::Release;
    if(Hit.GetComponent()==Masonry)return EHighGateUse::Repair;
    if(Hit.GetComponent()!=Portal)return EHighGateUse::None;
    const FVector P=GetActorTransform().InverseTransformPosition(Hit.ImpactPoint);
    const bool bWest=MeshPath==WestGrille;
    const double Throat=bWest?346.:246.;
    if(P.X>=Throat-17. && P.X<=Throat+1. && FMath::Abs(P.Y-156.)<=25. && P.Z>=84. && P.Z<=149.)
        return EHighGateUse::Release;
    const double Front=bWest?-804.:-604.;
    if(P.Z<345. && FMath::Abs(P.X)<=Throat+95. &&
        (FMath::Abs(P.Y-Front)<88. || FMath::Abs(P.Y-264.)<88. || FMath::Abs(P.Y)<46.))
        return EHighGateUse::Repair;
    return EHighGateUse::None;
}

void AHighVillageGate::ToggleDoor()
{
    if(!HasAuthority()||Health<=0.f||!Masonry->GetStaticMesh())return;
    MotionAudio->Arm();
    FlushNetDormancy();
    bWantsOpen=!bWantsOpen;
    ForceNetUpdate();
    SetNetDormancy(DORM_Awake);
    SetActorTickEnabled(true);
}

bool AHighVillageGate::CanLower(float NewHeight) const
{
    const UStaticMesh* Mesh=Masonry->GetStaticMesh();
    if(!Mesh)return false;
    // The grille extends into both guide slots, beyond the clear arch opening.
    // Its authored blocking box fills these mesh bounds on both gate variants.
    const FBox Bounds=Mesh->GetBoundingBox();
    FVector Center=Bounds.GetCenter();
    FVector Extent=Bounds.GetExtent();
    Extent.Z=(LiftCm-NewHeight)*.5f;
    Center.Z=Bounds.Min.Z+NewHeight+Extent.Z+1.f; // allow the grille to settle against the road
    const FTransform& Gate=GetActorTransform();
    return !GetWorld()->OverlapBlockingTestByChannel(Gate.TransformPosition(Center),Gate.GetRotation(),
        Masonry->GetCollisionObjectType(),FCollisionShape::MakeBox(Extent*Gate.GetScale3D().GetAbs()),
        FCollisionQueryParams(SCENE_QUERY_STAT(HighGateLower),false,this));
}

void AHighVillageGate::Tick(float Delta)
{
    Super::Tick(Delta);
    if(!HasAuthority())
    {
        Pose(FMath::FInterpConstantTo(DisplayLift,LiftCm,Delta,HoistSpeed*1.3f));
        if(FMath::IsNearlyEqual(DisplayLift,LiftCm,.05f))SetActorTickEnabled(false);
        return;
    }
    const float Goal=bWantsOpen?TravelCm():0.f;
    const float Next=FMath::FInterpConstantTo(LiftCm,Goal,Delta,HoistSpeed);
    if(Next<LiftCm && !CanLower(Next))
    {
        MotionAudio->Interrupted();
        MotionAudio->Arm();
        bWantsOpen=true;
        return;
    }
    if(Next!=LiftCm)MotionAudio->Moved();
    LiftCm=Next;
    Pose(Next);
    if(FMath::IsNearlyEqual(LiftCm,Goal,.05f))
    {
        ForceNetUpdate();
        SetActorTickEnabled(false);
        SetNetDormancy(DORM_DormantAll);
    }
}

void AHighVillageGate::PresentCollapse(const FVector& Direction,int32,float StartHeight)
{
    // Health can go from full to full between updates when a breach is immediately repaired.
    MotionAudio->ResetForBreach();
    if (Hoist) Hoist->Release(StartHeight);
    AHighVillageCollapse::Gate(*this,Direction,StartHeight);
}

void AHighVillageGate::MulticastClearRepairedDebris_Implementation()
{
    Super::MulticastClearRepairedDebris_Implementation();
    // The authority rebuilds a closed leaf. A remote client can still be displaying
    // the previous half-open leaf if the intermediate zero-health update was coalesced.
    Pose(0.f);
    if (Hoist) Hoist->Reattach(0.f);
}
