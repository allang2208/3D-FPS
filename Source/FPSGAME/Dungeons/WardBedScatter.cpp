#include "WardBedScatter.h"

#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "TimerManager.h"

AWardBedScatter::AWardBedScatter()
{
    PrimaryActorTick.bCanEverTick=false;
    Beds=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Beds"));
    SetRootComponent(Beds);
    Beds->SetMobility(EComponentMobility::Movable);
    Beds->SetCollisionProfileName(TEXT("BlockAll"));
    Beds->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Beds->CanCharacterStepUpOn=ECB_Yes;
    Beds->SetGenerateOverlapEvents(false);
    Beds->SetCanEverAffectNavigation(true);
}

void AWardBedScatter::BeginPlay()
{
    Super::BeginPlay();
    // Wait for authored architecture and individual door leaves to register.
    if(bGenerateOnBeginPlay)GetWorldTimerManager().SetTimerForNextTick(this,&AWardBedScatter::GenerateInitial);
}

void AWardBedScatter::GenerateInitial()
{
    GenerateFromSeed(bRandomizeOnBeginPlay?static_cast<int32>(FGuid::NewGuid().A):Seed);
}

void AWardBedScatter::GenerateFromSeed(int32 InSeed)
{
    UWorld* World=GetWorld();
    if(!World || !World->IsGameWorld())return; // Never populate an editor preview implicitly.
    for(UInstancedStaticMeshComponent* Component:PropInstances)
        if(Component)Component->DestroyComponent();
    PropInstances.Reset();
    Beds->ClearInstances();
    PlacedBeds=0;
    if(!BedMesh || Rooms.IsEmpty() || Poses.IsEmpty())return;
    Beds->SetStaticMesh(BedMesh);
    ActiveSeed=InSeed;
    FRandomStream Random(InSeed);
    float TotalWeight=0.f;
    for(const FWardBedPose& Pose:Poses)if(Pose.Bounds.IsValid)TotalWeight+=FMath::Max(0.f,Pose.Weight);
    if(TotalWeight<=0.f)return;
    const int32 MinCount=FMath::Clamp(MinBedsPerRoom,0,8);
    const int32 MaxCount=FMath::Clamp(MaxBedsPerRoom,MinCount,8);
    const float WallMargin=FMath::Max(0.f,WallClearance);
    const float Separation=FMath::Max(0.f,BedClearance);
    const FTransform RoomToWorld=GetActorTransform();
    TArray<FBox> Occupied;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(WardBedPlacement),true,this);
    const auto SpaceAvailable=[&](const FBox& Candidate,float Clearance)
    {
        for(const FBox& Reserved:KeepClear)
            if(Reserved.IsValid && Candidate.Intersect(Reserved))return false;
        for(const FBox& Existing:Occupied)
            if(Candidate.ExpandBy(FVector(Clearance,Clearance,0.f)).Intersect(Existing))return false;
        const FBox WorldBounds=Candidate.TransformBy(RoomToWorld);
        return !World->OverlapBlockingTestByChannel(WorldBounds.GetCenter(),FQuat::Identity,ECC_Pawn,
            FCollisionShape::MakeBox(WorldBounds.GetExtent()),Query);
    };

    for(const FWardBedRoom& Room:Rooms)
    {
        if(!Room.Bounds.IsValid)continue;
        const int32 Wanted=Random.RandRange(MinCount,MaxCount);
        int32 Made=0;
        // Finite rejection sampling: crowded rooms receive fewer beds, never a forced overlap.
        for(int32 Attempt=0;Attempt<Wanted*48 && Made<Wanted;++Attempt)
        {
            float Pick=Random.FRandRange(0.f,TotalWeight);
            const FWardBedPose* Selected=nullptr;
            for(const FWardBedPose& Pose:Poses)
            {
                if(!Pose.Bounds.IsValid || Pose.Weight<=0.f)continue;
                Selected=&Pose;
                Pick-=Pose.Weight;
                if(Pick<=0.f)break;
            }
            if(!Selected)continue;
            const FQuat Yaw=FRotator(0.f,Random.FRandRange(-180.f,180.f),0.f).Quaternion();
            const FBox RotatedBounds=Selected->Bounds.TransformBy(FTransform(Yaw));
            const FVector Minimum=Room.Bounds.Min+FVector(WallMargin,WallMargin,0.f)-RotatedBounds.Min;
            const FVector Maximum=Room.Bounds.Max-FVector(WallMargin,WallMargin,0.f)-RotatedBounds.Max;
            if(Minimum.X>Maximum.X || Minimum.Y>Maximum.Y)continue;
            const FVector Position(Random.FRandRange(Minimum.X,Maximum.X),
                                   Random.FRandRange(Minimum.Y,Maximum.Y),Minimum.Z+.2f);
            const FBox Candidate(RotatedBounds.Min+Position,RotatedBounds.Max+Position);
            if(Candidate.Max.Z>Room.Bounds.Max.Z)continue;
            if(!SpaceAvailable(Candidate,Separation))continue;

            const FTransform Placement(Yaw*Selected->Rotation.Quaternion(),Position);
            if(Beds->AddInstance(Placement)==INDEX_NONE)continue;
            Occupied.Add(Candidate);
            ++Made;
            ++PlacedBeds;
        }
    }
    // These execute after every bed, sharing occupancy regardless of collision.
    // Upright props receive random yaw only; thin IV stands never block the player.
    int32 PlacedProps=0;
    for(const FWardRoomProp& Prop:RoomProps)
    {
        if(!Prop.Mesh)continue;
        const FBox MeshBounds=Prop.Mesh->GetBoundingBox();
        if(!MeshBounds.IsValid)continue;
        auto* Instances=NewObject<UInstancedStaticMeshComponent>(this);
        Instances->SetupAttachment(GetRootComponent());
        Instances->SetMobility(EComponentMobility::Movable);
        Instances->SetStaticMesh(Prop.Mesh);
        Instances->SetCollisionProfileName(Prop.bBlocking?TEXT("BlockAll"):TEXT("NoCollision"));
        Instances->SetCollisionEnabled(Prop.bBlocking?ECollisionEnabled::QueryAndPhysics:ECollisionEnabled::NoCollision);
        Instances->CanCharacterStepUpOn=Prop.bBlocking?ECB_Yes:ECB_No;
        Instances->SetGenerateOverlapEvents(false);
        Instances->SetCanEverAffectNavigation(Prop.bBlocking);
        Instances->ComponentTags.Add(Prop.TypeId);
        Instances->RegisterComponent();
        PropInstances.Add(Instances);
        const int32 MinimumCount=FMath::Clamp(Prop.MinPerRoom,0,2);
        const int32 MaximumCount=FMath::Clamp(Prop.MaxPerRoom,MinimumCount,2);
        const float Clearance=FMath::Max(0.f,Prop.Clearance);
        for(const FWardBedRoom& Room:Rooms)
        {
            if(!Room.Bounds.IsValid)continue;
            const int32 Wanted=Random.RandRange(MinimumCount,MaximumCount);
            int32 Made=0;
            for(int32 Attempt=0;Attempt<Wanted*48 && Made<Wanted;++Attempt)
            {
                const FQuat Yaw=FRotator(0.f,Random.FRandRange(-180.f,180.f),0.f).Quaternion();
                const FBox Rotated=MeshBounds.TransformBy(FTransform(Yaw));
                const FVector Minimum=Room.Bounds.Min+FVector(WallMargin,WallMargin,0.f)-Rotated.Min;
                const FVector Maximum=Room.Bounds.Max-FVector(WallMargin,WallMargin,0.f)-Rotated.Max;
                if(Minimum.X>Maximum.X || Minimum.Y>Maximum.Y)continue;
                const FVector Position(Random.FRandRange(Minimum.X,Maximum.X),
                    Random.FRandRange(Minimum.Y,Maximum.Y),Minimum.Z+.2f);
                const FBox Candidate(Rotated.Min+Position,Rotated.Max+Position);
                if(Candidate.Max.Z>Room.Bounds.Max.Z || !SpaceAvailable(Candidate,Clearance))continue;
                if(Instances->AddInstance(FTransform(Yaw,Position))==INDEX_NONE)continue;
                Occupied.Add(Candidate);++Made;++PlacedProps;
            }
        }
    }
    UE_LOG(LogTemp,Log,TEXT("Ward furnishings generated: seed=%d beds=%d props=%d rooms=%d"),ActiveSeed,PlacedBeds,PlacedProps,Rooms.Num());
}
