#include "DungeonBloodScatter.h"

#include "Components/DecalComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"

ADungeonBloodScatter::ADungeonBloodScatter()
{
    PrimaryActorTick.bCanEverTick=false;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("BloodScatterRoot")));
}

void ADungeonBloodScatter::BeginPlay()
{
    Super::BeginPlay();
    if(!bGenerateOnBeginPlay)return;
    const int32 ChosenSeed=bRandomizeOnBeginPlay ? static_cast<int32>(FGuid::NewGuid().A) : Seed;
    GenerateFromSeed(ChosenSeed);
}

void ADungeonBloodScatter::GenerateFromSeed(int32 InSeed)
{
    UWorld* World=GetWorld();
    if(!World || !World->IsGameWorld() || World->GetNetMode()==NM_DedicatedServer)return;
    for(UDecalComponent* Decal:GeneratedDecals)if(Decal)Decal->DestroyComponent();
    GeneratedDecals.Reset();
    if(!BloodMaterial || Surfaces.IsEmpty())return;
    ActiveSeed=InSeed;
    FRandomStream Random(InSeed);
    TArray<FVector> PlacedCenters;
    GeneratedDecals.Reserve(FMath::Clamp(FloorCount,0,128)+FMath::Clamp(WallCount,0,64));
    ScatterGroup(Random,false,FMath::Clamp(FloorCount,0,128),PlacedCenters);
    PlacedCenters.Reset();
    ScatterGroup(Random,true,FMath::Clamp(WallCount,0,64),PlacedCenters);
}

void ADungeonBloodScatter::ScatterGroup(FRandomStream& Random,bool bOnWall,int32 DesiredCount,
                                        TArray<FVector>& PlacedCenters)
{
    TArray<int32> Candidates;
    TArray<float> CumulativeArea;
    float TotalArea=0.f;
    for(int32 Index=0;Index<Surfaces.Num();++Index)
    {
        const FDungeonBloodSurface& Surface=Surfaces[Index];
        if(Surface.bWall!=bOnWall || Surface.HalfSize.X<20.f || Surface.HalfSize.Y<20.f)continue;
        TotalArea+=Surface.HalfSize.X*Surface.HalfSize.Y;
        Candidates.Add(Index);CumulativeArea.Add(TotalArea);
    }
    if(Candidates.IsEmpty())return;
    UWorld* World=GetWorld();
    const FTransform RoomTransform=GetActorTransform();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(DungeonBloodPlacement),true,this);
    int32 Made=0;
    // Bounded placement work at room initialization only, never a retrying Tick.
    for(int32 Attempt=0;Attempt<DesiredCount*20 && Made<DesiredCount;++Attempt)
    {
        const float Pick=Random.FRandRange(0.f,TotalArea);
        int32 Selected=0;
        while(Selected<Candidates.Num()-1 && Pick>CumulativeArea[Selected])++Selected;
        const FDungeonBloodSurface& Surface=Surfaces[Candidates[Selected]];
        const FVector Normal=RoomTransform.TransformVectorNoScale(Surface.Normal).GetSafeNormal();
        const FVector U=RoomTransform.TransformVectorNoScale(Surface.AxisU).GetSafeNormal();
        const FVector V=FVector::CrossProduct(Normal,U).GetSafeNormal();
        const int32 Family=Random.RandRange(0,2); // smear, scattered droplets, pooled blot
        const float Angle=Random.FRandRange(-PI,PI);
        const float Cos=FMath::Cos(Angle),Sin=FMath::Sin(Angle);
        float LongHalf,ShortHalf;
        if(Family==0){LongHalf=Random.FRandRange(75.f,155.f);ShortHalf=Random.FRandRange(18.f,40.f);}
        else if(Family==1){LongHalf=Random.FRandRange(48.f,112.f);ShortHalf=Random.FRandRange(38.f,90.f);}
        else{LongHalf=Random.FRandRange(35.f,88.f);ShortHalf=Random.FRandRange(28.f,76.f);}
        if(bOnWall){LongHalf*=.65f;ShortHalf*=.7f;}
        const bool bScanned=ScannedSizeRangeCm.X>0.f;
        if(bScanned)
        {
            // Preserve the scan's square footprint instead of stretching it into
            // a several-metre procedural smear. Placement and yaw remain seeded.
            LongHalf=.5f*Random.FRandRange(ScannedSizeRangeCm.X,
                FMath::Max(ScannedSizeRangeCm.X,ScannedSizeRangeCm.Y));
            ShortHalf=LongHalf;
        }
        if(!bOnWall){LongHalf*=FloorSizeScale;ShortHalf*=FloorSizeScale;}
        const float MarginU=FMath::Abs(Cos)*LongHalf+FMath::Abs(Sin)*ShortHalf+8.f;
        const float MarginV=FMath::Abs(Sin)*LongHalf+FMath::Abs(Cos)*ShortHalf+8.f;
        if(MarginU>=Surface.HalfSize.X || MarginV>=Surface.HalfSize.Y)continue;
        const FVector Center=RoomTransform.TransformPosition(Surface.Center)
            +U*Random.FRandRange(-Surface.HalfSize.X+MarginU,Surface.HalfSize.X-MarginU)
            +V*Random.FRandRange(-Surface.HalfSize.Y+MarginV,Surface.HalfSize.Y-MarginV);
        bool bCrowded=false;
        for(const FVector& Existing:PlacedCenters)
            if(FVector::DistSquared(Existing,Center)<FMath::Square(FMath::Max(45.f,ShortHalf*.9f)))
            {bCrowded=true;break;}
        if(bCrowded)continue;
        FHitResult Hit;
        if(!World->LineTraceSingleByChannel(Hit,Center+Normal*35.f,Center-Normal*50.f,ECC_Visibility,Query))continue;
        AActor* Receiver=Hit.GetActor();
        if(!Receiver || (!ReceiverTag.IsNone() && !Receiver->ActorHasTag(ReceiverTag))
           || FVector::DotProduct(Hit.ImpactNormal,Normal)<.9f)continue;
        UDecalComponent* Decal=NewObject<UDecalComponent>(this);
        Decal->SetupAttachment(GetRootComponent());
        Decal->SetMobility(EComponentMobility::Movable);
        Decal->SetDecalMaterial(BloodMaterial);
        Decal->DecalSize=FVector(bScanned?4.f:10.f,ShortHalf,LongHalf);
        Decal->SetFadeScreenSize(.004f);
        // R: shape seed. G: family. B: zero for floor, 1 + aspect for wall.
        // A: rotation. Aspect keeps drips vertical on stretched, rotated decals.
        Decal->SetDecalColor(FLinearColor(Random.FRand(),(Family+.5f)/3.f,
            bOnWall?1.f+LongHalf/ShortHalf:0.f,(Angle+PI)/(2.f*PI)));
        Decal->RegisterComponent();
        Decal->SetWorldLocationAndRotation(Hit.ImpactPoint+Normal*2.f,
            FRotationMatrix::MakeFromXZ(-Normal,U*Cos+V*Sin).Rotator());
        GeneratedDecals.Add(Decal);PlacedCenters.Add(Center);++Made;
    }
}
