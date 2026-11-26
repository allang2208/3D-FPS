#include "DevelopmentSpawnComponent.h"
#include "DevelopmentEnvironmentObject.h"
#include "../Production/ProductionOreRocks.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Components/DynamicMeshComponent.h"
#include "EngineUtils.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"

int32 UDevelopmentSpawnComponent::SpawnEnvironment(FName Id, int32 Count, float DistanceMeters, FText& Result)
{
    auto* Player = Cast<APlayerController>(GetOwner());
    APawn* Pawn = Player ? Player->GetPawn() : nullptr;
    const auto* Entry = ADevelopmentEnvironmentObject::FindEntry(Id);
    if (!Entry || !Pawn || !Player->HasAuthority())
    {
        Result = FText::FromString(TEXT("请在单机或主机控制角色后选择环境物体"));
        return 0;
    }
    UObject* Asset = Entry->Mesh.TryLoad();
    auto* Rock = Cast<UStaticMesh>(Asset);
    auto* Tree = Cast<USkeletalMesh>(Asset);
    if (Entry->IsTree() ? !Tree : !Rock)
    {
        Result = FText::FromString(FString::Printf(TEXT("无法加载%s模型"), *Entry->Name));
        return 0;
    }

    const bool bTree = Entry->IsTree();
    UStaticMesh* OreMeshes[ProductionOreRocks::ShapeCount]={};
    if(!bTree)
        for(int32 Shape=0;Shape<ProductionOreRocks::ShapeCount;++Shape)
        {
            OreMeshes[Shape]=Cast<UStaticMesh>(ProductionOreRocks::Mesh(Entry->Ore,Shape).TryLoad());
            if(!OreMeshes[Shape]){Result=FText::FromString(TEXT("矿脉变体模型尚未就绪"));return 0;}
        }
    const uint32 SpawnSeed=uint32(FMath::Rand());
    const double Spacing = bTree ? 460. : 330.;
    const FRotator Facing(0, Player->GetControlRotation().Yaw, 0);
    const FVector Forward = Facing.Vector();
    const FVector Right = FRotationMatrix(Facing).GetUnitAxis(EAxis::Y);
    const FVector Eye = Pawn->GetPawnViewLocation();
    const FVector Front = Pawn->GetActorLocation() + Forward * FMath::Clamp(DistanceMeters, 3.f, 15.f) * 100.;
    auto* World = GetWorld();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(DevelopmentEnvironmentPlacement), false, Pawn);
    const int32 Wanted = FMath::Clamp(Count, 1, 10);
    EnvironmentObjects.RemoveAll([](const auto& Object) { return !Object.IsValid(); });
    int32 Created = 0;
    ATemperateHillsWorld* Hills=nullptr;
    TArray<FBox> FoliageFootprints;
    if(!bTree)
    {
        for(TActorIterator<ATemperateHillsWorld> It(World);It;++It){Hills=*It;break;}
        if(Hills)
        {
            // This is a bounded button action, not a Tick. Read no-collision
            // foliage once for the whole attempt area, including nearby roots
            // whose leaves/fronds extend across the requested area's border.
            FBox Area(ForceInit);
            for(int32 Side:{-2,2})for(int32 Row:{0,4})Area+=Front+Right*(Side*Spacing)+Forward*(Row*Spacing);
            Area=Area.ExpandBy(FVector(1000,1000,50000));
            TMap<FSoftObjectPath,FBox> MeshBoxes;
            for(int32 Layer=2;Layer<=4;++Layer)
            {
                TArray<FTemperatePlacement> Plants;Hills->GetPlacements(Layer,Area,Plants);
                for(const auto& P:Plants)
                {
                    if(!MeshBoxes.Contains(P.Mesh))
                    {
                        const UObject* Object=P.Mesh.ResolveObject();FBox Box(ForceInit);
                        if(const auto* Static=Cast<UStaticMesh>(Object))Box=Static->GetBoundingBox();
                        else if(const auto* Skinned=Cast<USkeletalMesh>(Object))Box=Skinned->GetBounds().GetBox();
                        MeshBoxes.Add(P.Mesh,Box);
                    }
                    const FBox& Box=MeshBoxes.FindChecked(P.Mesh);
                    if(Box.IsValid)FoliageFootprints.Add(Box.TransformBy(P.Transform).ExpandBy(18.0));
                }
            }
        }
    }
    // Try the requested point first, then alternating sides and successive rows.
    constexpr int32 Columns[] = {0, -1, 1, -2, 2};
    for (int32 Attempt = 0; Attempt < 25 && Created < Wanted; ++Attempt)
    {
        const FVector At = Front + Right * (Columns[Attempt % 5] * Spacing) + Forward * ((Attempt / 5) * Spacing);
        FHitResult Floor;
        if (!World->LineTraceSingleByChannel(Floor, At + FVector(0, 0, 110), At - FVector(0, 0, 650), ECC_Visibility, Query)
            || Floor.ImpactNormal.Z < .78 || Cast<ADevelopmentEnvironmentObject>(Floor.GetActor()) || Cast<APawn>(Floor.GetActor())) continue;
        const FVector Ground = Floor.ImpactPoint;
        if (World->LineTraceTestByChannel(Eye, Ground + FVector(0, 0, 80), ECC_Visibility, Query)) continue;

        const uint32 PlacementSeed=SpawnSeed+uint32(Attempt)*747796405U;
        const int32 Shape=ProductionOreRocks::Shape(PlacementSeed);
        FTransform Placement=bTree?FTransform(Facing.Quaternion(),Ground-FVector(0,0,10),FVector(.85)):
            ProductionOreRocks::Placement(*OreMeshes[Shape],PlacementSeed,Ground,Floor.ImpactNormal);
        const FBox Bounds=bTree?Tree->GetBounds().GetBox():OreMeshes[Shape]->GetBoundingBox();
        if(!bTree)
        {
            if(Hills)
            {
                // Never use a rock top, foliage collision or another actor as
                // the hills terrain. The numerical fit is shared with PCG.
                if(Floor.GetActor()!=Hills||!Cast<UDynamicMeshComponent>(Floor.GetComponent())||
                    !Hills->FitRockPlacement(*OreMeshes[Shape],Placement,true))continue;
            }
            else
            {
                const auto Sample=[&](const FVector& Probe,double& Z)
                {
                    FHitResult Support;
                    const FVector Above(Probe.X,Probe.Y,Ground.Z+150);
                    if(!World->LineTraceSingleByChannel(Support,Above,Above-FVector(0,0,350),ECC_Visibility,Query)||
                        Support.GetComponent()!=Floor.GetComponent()||Support.ImpactNormal.Z<.86)return false;
                    Z=Support.ImpactPoint.Z;return true;
                };
                const double Height=Bounds.GetSize().Z*Placement.GetScale3D().Z;
                if(!ProductionOreRocks::FitToSurface(*OreMeshes[Shape],Placement,Sample,
                    FMath::Clamp(Height*.16,6.0,25.0),FMath::Clamp(Height*.25,12.0,35.0)))continue;
            }
            const FBox Occupied=Bounds.TransformBy(Placement).ExpandBy(18.0);
            if(FoliageFootprints.ContainsByPredicate([&](const FBox& B)
                {return Occupied.Min.X<=B.Max.X&&Occupied.Max.X>=B.Min.X&&Occupied.Min.Y<=B.Max.Y&&Occupied.Max.Y>=B.Min.Y;}))continue;
            FCollisionQueryParams RockQuery=Query;
            RockQuery.AddIgnoredComponent(Floor.GetComponent());
            if(World->OverlapBlockingTestByChannel(Occupied.GetCenter(),FQuat::Identity,ECC_Pawn,
                FCollisionShape::MakeBox(Occupied.GetExtent()),RockQuery))continue;
        }
        const FBox RelativeBounds=Bounds.TransformBy(FTransform(Placement.GetRotation(),FVector::ZeroVector,Placement.GetScale3D()));
        const FVector Extent=RelativeBounds.GetExtent();
        const double Radius=bTree?70.:FMath::Max(55.,FMath::Max(Extent.X,Extent.Y));
        const double ClearanceHeight = bTree ? FMath::Max(600., Bounds.Max.Z * .85) : FMath::Max(45., Extent.Z * 2. - 12.);
        const double FootLift = FMath::Min(ClearanceHeight * .5, FMath::Max(12., Radius * .40));
        const double HalfHeight = (ClearanceHeight - FootLift) * .5;
        const FCollisionShape Clearance = FCollisionShape::MakeBox(FVector(Radius * .85, Radius * .85, HalfHeight));
        if (bTree && World->OverlapBlockingTestByChannel(Ground + FVector(0, 0, FootLift + HalfHeight), Facing.Quaternion(),
            ECC_Pawn, Clearance, Query)) continue;

        auto* Object = World->SpawnActorDeferred<ADevelopmentEnvironmentObject>(ADevelopmentEnvironmentObject::StaticClass(),
            Placement, Player, nullptr, ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if (!Object) continue;
        if (!Object->Initialize(Id,Shape)) { Object->Destroy(); continue; }
        Object->FinishSpawning(Placement);
        EnvironmentObjects.Add(Object);
        ++Created;
    }
    Result = FText::FromString(Created ? FString::Printf(TEXT("已生成 %d / %d 个%s"), Created, Wanted, *Entry->Name)
        : TEXT("前方没有足够的落脚空间，请面向开阔地面再试"));
    return Created;
}

int32 UDevelopmentSpawnComponent::GetEnvironmentCount() const
{
    int32 Count = 0;
    for (const auto& Object : EnvironmentObjects) if (Object.IsValid()) ++Count;
    return Count;
}

int32 UDevelopmentSpawnComponent::ClearEnvironment()
{
    int32 Cleared = 0;
    for (const auto& Object : EnvironmentObjects) if (Object.IsValid() && Object->Destroy()) ++Cleared;
    EnvironmentObjects.Reset();
    return Cleared;
}
