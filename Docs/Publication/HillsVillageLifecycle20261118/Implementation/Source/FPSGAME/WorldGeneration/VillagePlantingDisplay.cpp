#include "VillagePlantingDisplay.h"
#include "TemperateHillsWorld.h"
#include "Components/InstancedSkinnedMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"

AVillagePlantingDisplay::AVillagePlantingDisplay()
{PrimaryActorTick.bCanEverTick=true;RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));SetReplicates(false);}
void AVillagePlantingDisplay::Initialize(ATemperateHillsWorld* Source)
{
    Hills=Source;SetOwner(Source);
    Source->OnDestroyed.AddDynamic(this,&AVillagePlantingDisplay::SourceDestroyed);
    if(GetNetMode()==NM_DedicatedServer)SetActorTickEnabled(false);
}
void AVillagePlantingDisplay::SourceDestroyed(AActor*){Destroy();}
void AVillagePlantingDisplay::Tick(float Delta)
{
    Super::Tick(Delta);if(!Hills.IsValid()){Destroy();return;}
    if(!Hills->bReady)return;
    auto* Assets=Hills->Assets.Get();if(!Assets)return;
    for(const auto& Ref:Assets->ForestSaplings)if(!Ref.Get())return;
    for(const auto& Ref:Assets->ForestShrubs)if(!Ref.Get())return;
    for(const auto& Ref:Assets->Shrubs)if(!Ref.Get())return;
    for(const auto& Ref:Assets->Grass)if(!Ref.Get())return;
    for(const auto& Ref:Assets->GrassAccents)if(!Ref.Get())return;
    for(const auto& Ref:Assets->Rocks)if(!Ref.IsNull()&&!Ref.Get())return;
    for(const auto& Ref:Assets->MeadowFlowers)if(!Ref.IsNull()&&!Ref.Get())return;
    if(!Area.IsValid)
    {
        const auto& V=Hills->GetVillageSite();const auto E=V.Extent();
        Area=FBox(V.Ground-FVector(E,5000),V.Ground+FVector(E,5000));
        Cell=Area;Cell.Max.X=FMath::Min(Cell.Min.X+2000.,Area.Max.X);
        Cell.Max.Y=FMath::Min(Cell.Min.Y+2000.,Area.Max.Y);NextY=Cell.Min.Y;
    }
    if(!Neighborhood)
    {
        // Retain the same finite competition halo and world-space candidate IDs.
        // Preparing the whole village at once was an unbudgeted 55 ms work unit.
        Neighborhood=Hills->BeginVegetationCell(Cell);return;
    }
    if(!RelationshipsReady)
    {
        Hills->CompleteVegetationCell(Neighborhood,true);RelationshipsReady=true;return;
    }
    const double Until=FPlatformTime::Seconds()+.0007;
    do
    {
        if(PendingIndex>=Pending.Num())
        {
            Pending.Reset();PendingIndex=0;
            FBox Strip=Cell;Strip.Min.Y=NextY;Strip.Max.Y=FMath::Min(NextY+200.,Cell.Max.Y);
            Hills->GetVegetationStrip(2,Strip,*Neighborhood,Pending);Hills->GetVegetationStrip(4,Strip,*Neighborhood,Pending);Hills->GetVegetationStrip(3,Strip,*Neighborhood,Pending);
            NextY=Strip.Max.Y;
        }
        for(;PendingIndex<Pending.Num();)
        {
            const auto& P=Pending[PendingIndex++];
            if(!P.bVillagePlanting)continue;
            auto& Entry=Groups.FindOrAdd(P.Mesh);
            if(!Entry)
            {
                const int32 Pass=int32((P.CandidateId>>16)&255);
                if(auto* Skin=Cast<USkeletalMesh>(P.Mesh.ResolveObject()))
                {
                    auto* C=NewObject<UInstancedSkinnedMeshComponent>(this);C->SetSkinnedAsset(Skin);
                    if(Assets->ForestWindProvider)C->SetTransformProvider(Assets->ForestWindProvider);
                    C->SetCullDistances(Pass==0?18000:12500,Pass==0?21000:15000);Entry=C;
                }
                else if(auto* Mesh=Cast<UStaticMesh>(P.Mesh.ResolveObject()))
                {
                    auto* C=NewObject<UInstancedStaticMeshComponent>(this);C->SetStaticMesh(Mesh);
                    C->SetCullDistances(Pass<2?15000:9500,Pass<2?18000:13000);Entry=C;
                }
                if(!Entry)continue;
                AddInstanceComponent(Entry);Entry->SetupAttachment(RootComponent);Entry->SetMobility(EComponentMobility::Movable);
                Entry->SetCollisionEnabled(ECollisionEnabled::NoCollision);Entry->SetCanEverAffectNavigation(false);
                Entry->SetGenerateOverlapEvents(false);Entry->SetReceivesDecals(false);Entry->ComponentTags.Add(TEXT("VillagePlanting"));Entry->RegisterComponent();
            }
            if(auto* SkinGroup=Cast<UInstancedSkinnedMeshComponent>(Entry))SkinGroup->AddInstance(P.Transform,0,true);
            else if(auto* StaticGroup=Cast<UInstancedStaticMeshComponent>(Entry))StaticGroup->AddInstance(P.Transform,true);
            ++PlantCount;
            if(FPlatformTime::Seconds()>=Until)return;
        }
    }while(NextY<Cell.Max.Y&&FPlatformTime::Seconds()<Until);
    if(NextY>=Cell.Max.Y&&PendingIndex>=Pending.Num())
    {
        Pending.Reset();PendingIndex=0;Neighborhood.Reset();RelationshipsReady=false;
        Cell.Min.X=Cell.Max.X;
        if(Cell.Min.X>=Area.Max.X){Cell.Min.X=Area.Min.X;Cell.Min.Y=Cell.Max.Y;}
        if(Cell.Min.Y>=Area.Max.Y)
        {SetActorTickEnabled(false);UE_LOG(LogTemp,Display,TEXT("VILLAGE_PLANTING_DISPLAY count=%d groups=%d"),PlantCount,Groups.Num());return;}
        Cell.Max.X=FMath::Min(Cell.Min.X+2000.,Area.Max.X);Cell.Max.Y=FMath::Min(Cell.Min.Y+2000.,Area.Max.Y);NextY=Cell.Min.Y;
    }
}
