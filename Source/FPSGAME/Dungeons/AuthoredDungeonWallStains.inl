// Cosmetic wall seepage uses existing authored anchors and an independent seed.
// Preparation is resumable and finishes before player release.
namespace DungeonWallStains
{
static TAutoConsoleVariable<float> KeepFraction(
    TEXT("fps.Dungeon.WallStainKeepFraction"),.32f,
    TEXT("Chance to retain an eligible authored wall seepage anchor on the next dungeon generation."));

struct FPreparation
{
    struct FCandidate
    {
        TWeakObjectPtr<UDecalComponent> Component;
        uint32 Key,Rank;
        int32 Order;
    };
    struct FRankAfter
    {
        bool operator()(const FCandidate& A,const FCandidate& B) const
        {return A.Rank==B.Rank?A.Order>B.Order:A.Rank>B.Rank;}
    };
    TUniquePtr<TActorIterator<ADecalActor>> Iterator;
    std::priority_queue<FCandidate,std::vector<FCandidate>,FRankAfter> Candidates;
    TMap<FIntPoint,TArray<FVector>> RetainedCells;
    int32 CandidateCount=0,RetainedCount=0,Limit=0;
    float Chance=0;
    bool bStarted=false,bCollected=false,bDone=false;

    bool Pump(UWorld* World,int32 Seed,double Deadline)
    {
        if(bDone||!World||!World->IsGameWorld())return true;
        if(FPlatformTime::Seconds()>=Deadline)return false;
        if(!bStarted)
        {
            Iterator=MakeUnique<TActorIterator<ADecalActor>>(World);
            Chance=FMath::Clamp(KeepFraction.GetValueOnGameThread(),0.f,1.f);
            bStarted=true;
        }
        const FName CandidateTag(TEXT("DungeonWallStain.Candidate"));
        while(!bCollected&&FPlatformTime::Seconds()<Deadline)
        {
            if(!*Iterator)
            {Iterator.Reset();Limit=FMath::CeilToInt(CandidateCount*Chance);bCollected=true;break;}
            ADecalActor* Actor=**Iterator;++(*Iterator);
            if(!IsValid(Actor))continue;
            UDecalComponent* C=Actor->GetDecal();
            UMaterialInterface* Material=C?C->GetDecalMaterial():nullptr;
            if(!Material||FMath::Abs(C->GetForwardVector().Z)>.3)continue;
            const FString Path=Material->GetBaseMaterial()->GetPathName();
            if(Path!=TEXT("/Game/Dungeons/AtmosphereV2/Materials/M_LocalDampStreak.M_LocalDampStreak")&&
               Path!=TEXT("/Game/Dungeons/AtmosphereV2/TilePolish/Materials/M_TileLeak.M_TileLeak")&&
               Path!=TEXT("/Game/Dungeons/AtmosphereV2/NaturalPass/Materials/M_NaturalLeakVertical.M_NaturalLeakVertical"))continue;
            if(!C->ComponentHasTag(CandidateTag))
            {
                if(!C->IsVisible()||C->bHiddenInGame||Actor->IsHidden())continue;
                C->ComponentTags.Add(CandidateTag);
            }
            const FVector P=C->GetComponentLocation();
            const uint32 Key=HashCombineFast(GetTypeHash(Path),HashCombineFast(
                GetTypeHash(FMath::RoundToInt(P.X)),HashCombineFast(
                    GetTypeHash(FMath::RoundToInt(P.Y)),GetTypeHash(FMath::RoundToInt(P.Z)))));
            // Incremental rank ordering avoids a whole-array finishing sort.
            Candidates.push({C,Key,HashCombineFast(uint32(Seed)^0x17A923C5u,Key),CandidateCount++});
        }
        while(bCollected&&!Candidates.empty()&&FPlatformTime::Seconds()<Deadline)
        {
            const FCandidate Candidate=Candidates.top();Candidates.pop();
            UDecalComponent* C=Candidate.Component.Get();
            if(!C)continue;
            FRandomStream Random(int32(HashCombineFast(uint32(Seed)^0x78AD459Bu,Candidate.Key)));
            bool Keep=Random.FRand()<Chance&&RetainedCount<Limit;
            const FVector P=C->GetComponentLocation();
            const FIntPoint Cell(FMath::FloorToInt(P.X/180.),FMath::FloorToInt(P.Y/180.));
            // Only these cells can intersect the original 180cm exclusion radius.
            for(int32 X=-1;Keep&&X<=1;++X)for(int32 Y=-1;Keep&&Y<=1;++Y)
                if(const auto* Nearby=RetainedCells.Find(Cell+FIntPoint(X,Y)))
                    for(const FVector& Other:*Nearby)
                        if(FMath::Abs(P.Z-Other.Z)<240&&FVector::DistSquared2D(P,Other)<FMath::Square(180.))
                        {Keep=false;break;}
            C->SetVisibility(Keep);
            if(!Keep)continue;
            RetainedCells.FindOrAdd(Cell).Add(P);++RetainedCount;
            C->DecalSize.X=FMath::Min(C->DecalSize.X,8.);
            UMaterialInstanceDynamic* MID=Cast<UMaterialInstanceDynamic>(C->GetDecalMaterial());
            if(!MID)MID=C->CreateDynamicMaterialInstance();
            if(MID)
            {
                MID->SetScalarParameterValue(TEXT("StainOpacity"),Random.FRandRange(.22f,.34f));
                MID->SetScalarParameterValue(TEXT("StainVariant"),float(Random.RandRange(0,3)));
                MID->SetScalarParameterValue(TEXT("StainWidth"),Random.FRandRange(.66f,.94f));
                MID->SetScalarParameterValue(TEXT("StainLength"),Random.FRandRange(.55f,.95f));
                MID->SetScalarParameterValue(TEXT("StainOffset"),Random.FRandRange(-.07f,.07f));
                MID->SetScalarParameterValue(TEXT("StainMirror"),float(Random.RandRange(0,1)));
                MID->SetScalarParameterValue(TEXT("StainRoughness"),Random.FRandRange(.65f,.8f));
            }
            C->MarkRenderStateDirty();
        }
        bDone=bCollected&&Candidates.empty();
        return bDone;
    }
};
}
