#include "WardBedScatter.h"
#include "../UI/ColdSteelSceneContainer.h"

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

void AWardBedScatter::EndPlay(const EEndPlayReason::Type Reason)
{
    for(AColdSteelSceneContainer* Container:SpawnedBedsideContainers)if(IsValid(Container))Container->Destroy();
    SpawnedBedsideContainers.Reset();
    Super::EndPlay(Reason);
}

void AWardBedScatter::GenerateInitial()
{
    GenerateFromSeed(bRandomizeOnBeginPlay?static_cast<int32>(FGuid::NewGuid().A):Seed);
}

void AWardBedScatter::GenerateFromSeed(int32 InSeed)
{
    UWorld* World=GetWorld();
    if(!World || !World->IsGameWorld())return; // Never populate an editor preview implicitly.
    for(AColdSteelSceneContainer* Container:SpawnedBedsideContainers)if(IsValid(Container))Container->Destroy();
    SpawnedBedsideContainers.Reset();
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
    struct FBedsideAnchor {FName Room;FBox Bounds;FTransform Bed;};
    TArray<FBedsideAnchor> BedsideAnchors;
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
            if(FMath::Abs(Selected->Rotation.Pitch)<5.f && FMath::Abs(Selected->Rotation.Roll)<5.f)
                BedsideAnchors.Add({Room.RoomId,Room.Bounds,Placement});
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
    // Patient boxes share the same occupancy ledger after every bed and loose prop.
    // The reserve includes the lid's full opening sweep, not only its closed body.
    const auto& Setting=BedsideContainers;
    if(Setting.BodyMesh && Setting.LidMesh && !BedsideAnchors.IsEmpty())
    {
        FBox LocalReserve=Setting.BodyMesh->GetBoundingBox();
        const FBox LidBounds=Setting.LidMesh->GetBoundingBox();
        for(int32 Step=0;Step<=4;++Step)
            LocalReserve+=LidBounds.TransformBy(FTransform(FRotator(0,0,Setting.OpenedRoll*Step/4.f),Setting.Hinge));
        const int32 Wanted=Random.RandRange(FMath::Clamp(Setting.MinCount,0,8),
            FMath::Clamp(Setting.MaxCount,FMath::Clamp(Setting.MinCount,0,8),8));
        TArray<int32> Order;
        for(int32 I=0;I<BedsideAnchors.Num();++I)Order.Add(I);
        for(int32 I=Order.Num()-1;I>0;--I)Order.Swap(I,Random.RandRange(0,I));
        TSet<FName> UsedRooms;
        for(int32 Index:Order)
        {
            if(SpawnedBedsideContainers.Num()>=Wanted)break;
            const auto& Anchor=BedsideAnchors[Index];
            if(UsedRooms.Contains(Anchor.Room))continue;
            const int32 FirstWall=Random.RandRange(0,3);
            bool Placed=false;
            for(int32 Attempt=0;Attempt<24 && !Placed;++Attempt)
            {
                // Wall bays leave the central treatment aisle clear. Rotate the
                // box toward the room and reserve its lid sweep before placing it.
                const int32 Wall=(FirstWall+Attempt)%4;
                const FQuat Facing=FRotator(0.f,Wall==0?0.f:Wall==1?180.f:Wall==2?-90.f:90.f,0.f).Quaternion();
                const FBox Rotated=LocalReserve.TransformBy(FTransform(Facing));
                const FVector Minimum=Anchor.Bounds.Min+FVector(12,12,0)-Rotated.Min;
                const FVector Maximum=Anchor.Bounds.Max-FVector(12,12,0)-Rotated.Max;
                if(Minimum.X>Maximum.X || Minimum.Y>Maximum.Y)continue;
                FVector Position(Random.FRandRange(Minimum.X,Maximum.X),
                    Random.FRandRange(Minimum.Y,Maximum.Y),Minimum.Z+.2f);
                if(Wall==0)Position.Y=Maximum.Y;
                else if(Wall==1)Position.Y=Minimum.Y;
                else if(Wall==2)Position.X=Maximum.X;
                else Position.X=Minimum.X;
                const FTransform At(Facing,Position);
                const FBox Candidate=LocalReserve.TransformBy(At);
                if(Candidate.Min.X<Anchor.Bounds.Min.X+10 || Candidate.Max.X>Anchor.Bounds.Max.X-10
                    || Candidate.Min.Y<Anchor.Bounds.Min.Y+10 || Candidate.Max.Y>Anchor.Bounds.Max.Y-10
                    || Candidate.Max.Z>Anchor.Bounds.Max.Z || !SpaceAvailable(Candidate,FMath::Max(12.f,Setting.BedGap)))continue;
                const FTransform WorldAt=At*RoomToWorld;
                auto* Container=World->SpawnActorDeferred<AColdSteelSceneContainer>(AColdSteelSceneContainer::StaticClass(),
                    WorldAt,this,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
                if(!Container)continue;
                Container->ContainerId=Setting.IdentityPrefix+FString::Printf(TEXT(".%s.Seed%d.%s.%d"),
                    *GetName(),InSeed,*Anchor.Room.ToString(),Index);
                Container->Caption=Setting.Caption;
                Container->OpeningMotion=EColdSteelContainerMotion::Lid;
                Container->OpenedRoll=Setting.OpenedRoll;
                Container->GetRootComponent()->SetMobility(EComponentMobility::Movable);
                Container->Body->SetMobility(EComponentMobility::Movable);
                // SetStaticMesh rejects Static components after world BeginPlay.
                Container->Body->SetStaticMesh(Setting.BodyMesh);
                Container->Door->SetStaticMesh(Setting.LidMesh);
                Container->Door->SetCollisionProfileName(TEXT("NoCollision"));
                Container->DoorHinge->SetRelativeLocation(Setting.Hinge);
                Container->FinishSpawning(WorldAt);
                Container->AttachToActor(this,FAttachmentTransformRules::KeepWorldTransform);
                SpawnedBedsideContainers.Add(Container);Occupied.Add(Candidate);UsedRooms.Add(Anchor.Room);Placed=true;
            }
        }
    }
    UE_LOG(LogTemp,Log,TEXT("Ward furnishings generated: seed=%d beds=%d props=%d bedside=%d rooms=%d"),
        ActiveSeed,PlacedBeds,PlacedProps,SpawnedBedsideContainers.Num(),Rooms.Num());
}
