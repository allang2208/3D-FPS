#include "VillageDefenseSection.h"
#include "VillageMasonry.h"
#include "VillageDefenseDebris.h"
#include "VillageGateMotionAudio.h"
#include "Sound/SoundWave.h"
#include "UObject/ConstructorHelpers.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "Net/UnrealNetwork.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

AVillageDefenseGate::AVillageDefenseGate()
{
    MotionAudio=CreateDefaultSubobject<UVillageGateMotionAudio>(TEXT("GateMotionAudio"));
    MotionAudio->SetupAttachment(RootComponent);
    static ConstructorHelpers::FObjectFinder<USoundWave> Cue(TEXT("/Game/WorldGeneration/TemperateHills/VillageDefenses/GateAudio/S_VillageTimberGate"));
    MotionAudio->SetSound(Cue.Object);
    RepairSoulCost=150;
    // Inherited masonry is a moving leaf here, not a fixed wall support.
    Masonry->ComponentTags.Remove(TEXT("Traversal.FixedStructure"));
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.bStartWithTickEnabled=false;
    RightLeaf=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("RightLeaf"));RightLeaf->SetupAttachment(RootComponent);
    RightLeaf->SetMobility(EComponentMobility::Movable);RightLeaf->SetCollisionProfileName(TEXT("BlockAll"));
    RightLeaf->SetGenerateOverlapEvents(false);Tags.Add(TEXT("VillageGate"));
    LeftMount=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("LeftHingeMount"));LeftMount->SetupAttachment(RootComponent);
    RightMount=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("RightHingeMount"));RightMount->SetupAttachment(RootComponent);
    for(auto* Mount:{LeftMount.Get(),RightMount.Get()}){Mount->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mount->SetCanEverAffectNavigation(false);}
    SetNetUpdateFrequency(15.f);
}
void AVillageDefenseGate::InitializeGate(ATemperateHillsWorld* Hills,int32 Id,bool Wide,const FGuid& BuiltId)
{
    const TCHAR* MeshRole=Wide?TEXT("GateWide"):TEXT("GateNarrow");
    Initialize(Hills,Id,FSoftObjectPath(FString::Printf(TEXT("/Game/WorldGeneration/TemperateHills/VillageDefenses/SM_%s.SM_%s"),MeshRole,MeshRole)),900.f,BuiltId);
}
FSoftObjectPath AVillageDefenseGate::PlacedPostMeshPath()
{
    return VillageMasonry::Mesh(TEXT("SM_VillageWallPierRepaired"));
}
FTransform AVillageDefenseGate::PlacedPostTransform(bool Right)
{
    // Bracket bolts are 43 cm beyond each hinge. Sink their mounting plates
    // into the front face of the pier, clear of the moving timber leaves.
    return FTransform(FQuat::Identity,FVector(Right?362.:-362.,0.,0.),FVector(.45,.34,1.10));
}
void AVillageDefenseGate::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AVillageDefenseGate,GateAngle);}
void AVillageDefenseGate::PostNetInit()
{
    Super::PostNetInit();
    // Initial replicated state is a snapshot, not an opening animation. Apply
    // it to both visual and collision transforms before the first client tick.
    DisplayAngle=GateAngle;Pose(DisplayAngle);SetActorTickEnabled(false);
#if !UE_BUILD_SHIPPING
    if(FParse::Param(FCommandLine::Get(),TEXT("VillageNetworkAudit")))
        UE_LOG(LogTemp,Display,TEXT("VILLAGE_NET_GATE_INITIAL id=%d angle=%.2f left=%.2f right=%.2f"),
            SectionId,GateAngle,Masonry->GetRelativeRotation().Yaw,RightLeaf->GetRelativeRotation().Yaw);
#endif
}
void AVillageDefenseGate::OnRep_Setup()
{
    Pose(DisplayAngle);
    Super::OnRep_Setup();if(!Masonry->GetStaticMesh())return;
    const FString Name=MeshPath.ToString().Contains(TEXT("Wide"))?TEXT("GateWideRight"):TEXT("GateNarrowRight");
    const FSoftObjectPath RightPath(FString::Printf(TEXT("/Game/WorldGeneration/TemperateHills/VillageDefenses/SM_%s.SM_%s"),*Name,*Name));
    if(auto* Mesh=Cast<UStaticMesh>(RightPath.ResolveObject()))
    {
        if(RightLeaf->GetStaticMesh()!=Mesh)
        {
            RightLeaf->SetStaticMesh(Mesh);
            // Publish this half of a streamed breach even if its mounts are still loading.
            ApplyHealth();
        }
    }
    else{MeshLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(RightPath,FStreamableDelegate::CreateUObject(this,&AVillageDefenseGate::OnRep_Setup));return;}
    const float HingeOffset=MeshPath.ToString().Contains(TEXT("Wide"))?431.f:NarrowHingeOffset;
    for(int32 Side=0;Side<2;++Side)
    {
        const TCHAR* MeshName=Side?TEXT("GateHingeMountRight"):TEXT("GateHingeMount");
        const FSoftObjectPath MountPath(FString::Printf(TEXT("/Game/WorldGeneration/TemperateHills/VillageDefenses/SM_%s.SM_%s"),MeshName,MeshName));
        auto* Mount=Side?RightMount.Get():LeftMount.Get();
        if(auto* Mesh=Cast<UStaticMesh>(MountPath.ResolveObject()))Mount->SetStaticMesh(Mesh);
        else {MeshLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(MountPath,FStreamableDelegate::CreateUObject(this,&AVillageDefenseGate::OnRep_Setup));return;}
        Mount->SetRelativeLocation(FVector(Side?HingeOffset:-HingeOffset,0,0));
    }
    if(PlacedId.IsValid()&&PlacedGatePosts.IsEmpty())
    {
        const auto Path=PlacedPostMeshPath();
        auto* Mesh=Cast<UStaticMesh>(Path.ResolveObject());
        if(!Mesh)
        {
            MeshLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Path,FStreamableDelegate::CreateUObject(this,&AVillageDefenseGate::OnRep_Setup));
            return;
        }
        for(int32 Side=0;Side<2;++Side)
        {
            auto* Post=NewObject<UStaticMeshComponent>(this,Side?TEXT("PlacedRightPier"):TEXT("PlacedLeftPier"));
            AddInstanceComponent(Post);Post->SetupAttachment(RootComponent);
            Post->SetMobility(EComponentMobility::Movable);Post->SetStaticMesh(Mesh);
            Post->SetRelativeTransform(PlacedPostTransform(Side!=0));
            Post->SetCollisionProfileName(TEXT("BlockAll"));Post->SetGenerateOverlapEvents(false);
            Post->ComponentTags.Add(TEXT("Traversal.FixedStructure"));
            Post->RegisterComponent();PlacedGatePosts.Add(Post);
        }
    }
    Pose(DisplayAngle);ApplyHealth();
}
void AVillageDefenseGate::ApplyHealth()
{
    Super::ApplyHealth();
    RightLeaf->SetVisibility(Health>0);
    RightLeaf->SetCollisionEnabled(Health>0?ECollisionEnabled::QueryAndPhysics:ECollisionEnabled::NoCollision);
    RightLeaf->SetCanEverAffectNavigation(Health>0);
    if(Health<=0)
    {
        MotionAudio->ResetForBreach();
        if(HasAuthority())GateAngle=0.f;
        DisplayAngle=GoalAngle=0.f;
        Pose(0.f);
        SetActorTickEnabled(false);
    }
}
bool AVillageDefenseGate::IsRepairSiteClear() const
{
    return Super::IsRepairSiteClear()&&IsRepairMeshClear(RightLeaf,RightLeaf->GetComponentTransform());
}
void AVillageDefenseGate::Pose(float Angle)
{
    const float HingeOffset=MeshPath.ToString().Contains(TEXT("Wide"))?431.f:NarrowHingeOffset;
    Masonry->SetRelativeLocationAndRotation(FVector(-HingeOffset,0,0),FRotator(0,Angle,0));
    RightLeaf->SetRelativeLocationAndRotation(FVector(HingeOffset,0,0),FRotator(0,-Angle,0));
}
bool AVillageDefenseGate::CanSwingTo(float Angle) const
{
    if(!Masonry->GetStaticMesh())return false;
    const float Width=MeshPath.ToString().Contains(TEXT("Wide"))?428.f:328.f;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(VillageGateSwing),false,this);
    for(int32 Side=0;Side<2;++Side)
    {
        const FTransform Local(FRotator(0,Side?-Angle:Angle,0),FVector(Side?Width+3.f:-Width-3.f,0,0));
        const FTransform T=Local*GetActorTransform();
        const FVector Center=T.TransformPosition(FVector((Side?-1.f:1.f)*Width*.5f,5.5f,115));
        // Test the real thickness including iron straps, with a small tolerance at the ground.
        if(GetWorld()->OverlapBlockingTestByChannel(Center,T.GetRotation(),ECC_WorldDynamic,
            FCollisionShape::MakeBox(FVector(Width*.5f-2,15.5f,98)),Query))return false;
    }
    return true;
}
void AVillageDefenseGate::ToggleDoor()
{
    if(!HasAuthority()||Health<=0.f)return;
    MotionAudio->Arm();
    GoalAngle=GoalAngle>0.f?0.f:88.f;SetNetDormancy(DORM_Awake);SetActorTickEnabled(true);
}
void AVillageDefenseGate::OnRep_Angle()
{if(Health>0.f)SetActorTickEnabled(true);}
void AVillageDefenseGate::Tick(float Delta)
{
    Super::Tick(Delta);
    if(HasAuthority())
    {
        const float Next=FMath::FInterpConstantTo(GateAngle,GoalAngle,Delta,42.f);
        const bool bBlocked=!CanSwingTo(Next);
        if(bBlocked)MotionAudio->Interrupted();
        else if(Next!=GateAngle)MotionAudio->Moved();
        if(!bBlocked)GateAngle=Next;
        DisplayAngle=GateAngle;Pose(DisplayAngle);
        // Keep the last requested direction so a second interaction backs out of an obstruction.
        if(bBlocked||FMath::IsNearlyEqual(GateAngle,GoalAngle,.01f))
        {ForceNetUpdate();SetActorTickEnabled(false);SetNetDormancy(DORM_DormantAll);}
    }
    else
    {
        DisplayAngle=FMath::FInterpConstantTo(DisplayAngle,GateAngle,Delta,65.f);Pose(DisplayAngle);
        if(FMath::IsNearlyEqual(DisplayAngle,GateAngle,.01f))SetActorTickEnabled(false);
    }
}
FVector AVillageDefenseGate::TargetPoint(const FVector& From) const
{
    FVector A=Super::TargetPoint(From),B=A;
    RightLeaf->GetClosestPointOnCollision(From,B);B.Z=A.Z;
    return FVector::DistSquared(From,A)<FVector::DistSquared(From,B)?A:B;
}
void AVillageDefenseGate::PresentCollapse(const FVector& Direction,int32 Seed,float AngleAtImpact)
{
    MotionAudio->ResetForBreach();
    if (GetNetMode() == NM_Client)
    {
        // A repair in the same replication update can skip the zero-health notification.
        // Drop the old swing locally. Fragments below still use the authoritative impact angle.
        DisplayAngle = 0.f;
        Pose(DisplayAngle);
        SetActorTickEnabled(false);
    }
    for(auto* Leaf:{Masonry.Get(),RightLeaf.Get()})
    {
        // A destruction RPC can arrive between the two asynchronous mesh loads.
        // Missing cosmetic geometry must never prevent authoritative destruction.
        const UStaticMesh* Mesh=Leaf->GetStaticMesh();
        if(!Mesh)continue;
        const FVector Size=Mesh->GetBoundingBox().GetSize();
        // Health and opening-angle replication can arrive before the collapse event.
        // Build both fragment origins from the angle of the authoritative hit.
        FTransform Relative=Leaf->GetRelativeTransform();
        Relative.SetRotation(FRotator(0,Leaf==Masonry.Get()?AngleAtImpact:-AngleAtImpact,0).Quaternion());
        FTransform T=Relative*GetActorTransform();
        FVector Center=Mesh->GetBoundingBox().GetCenter();Center.Z=0.;
        T.SetLocation(T.TransformPosition(Center));
        AVillageDefenseDebris::Spawn(*this,T,Size,Direction,Seed++,true);
    }
}
