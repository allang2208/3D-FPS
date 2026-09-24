// Cosmetic wall seepage uses existing authored anchors and an independent seed.
// Applied only after successful runtime assembly; never changes layout/collision.
namespace DungeonWallStains
{
static TAutoConsoleVariable<float> KeepFraction(
    TEXT("fps.Dungeon.WallStainKeepFraction"),.32f,
    TEXT("Chance to retain an eligible authored wall seepage anchor on the next dungeon generation."));

static void Apply(UWorld* World,int32 Seed)
{
    if(!World||!World->IsGameWorld())return;
    struct FCandidate { UDecalComponent* Component; uint32 Key; uint32 Rank; };
    TArray<FCandidate> Candidates;
    const FName CandidateTag(TEXT("DungeonWallStain.Candidate"));
    for(TActorIterator<ADecalActor> It(World);It;++It)
    {
        UDecalComponent* C=It->GetDecal();
        UMaterialInterface* Material=C?C->GetDecalMaterial():nullptr;
        if(!Material||FMath::Abs(C->GetForwardVector().Z)>.3)continue;
        const FString Path=Material->GetBaseMaterial()->GetPathName();
        if(Path!=TEXT("/Game/Dungeons/AtmosphereV2/Materials/M_LocalDampStreak.M_LocalDampStreak")&&
           Path!=TEXT("/Game/Dungeons/AtmosphereV2/TilePolish/Materials/M_TileLeak.M_TileLeak")&&
           Path!=TEXT("/Game/Dungeons/AtmosphereV2/NaturalPass/Materials/M_NaturalLeakVertical.M_NaturalLeakVertical"))continue;
        // Do not resurrect decals explicitly disabled by the room author. Our own
        // thinning is reversible on a later seed in the same world.
        if(!C->ComponentHasTag(CandidateTag))
        {
            if(!C->IsVisible()||C->bHiddenInGame||It->IsHidden())continue;
            C->ComponentTags.Add(CandidateTag);
        }
        const FVector P=C->GetComponentLocation();
        const uint32 Key=HashCombineFast(GetTypeHash(Path),HashCombineFast(
            GetTypeHash(FMath::RoundToInt(P.X)),HashCombineFast(
                GetTypeHash(FMath::RoundToInt(P.Y)),GetTypeHash(FMath::RoundToInt(P.Z)))));
        Candidates.Add({C,Key,HashCombineFast(uint32(Seed)^0x17A923C5u,Key)});
    }
    Candidates.Sort([](const FCandidate& A,const FCandidate& B){return A.Rank<B.Rank;});
    const float Chance=FMath::Clamp(KeepFraction.GetValueOnGameThread(),0.f,1.f);
    const int32 Limit=FMath::CeilToInt(Candidates.Num()*Chance);
    TArray<FVector> Retained;
    for(const FCandidate& Candidate:Candidates)
    {
        UDecalComponent* C=Candidate.Component;
        FRandomStream Random(int32(HashCombineFast(uint32(Seed)^0x78AD459Bu,Candidate.Key)));
        bool Keep=Random.FRand()<Chance&&Retained.Num()<Limit;
        const FVector P=C->GetComponentLocation();
        if(Keep)for(const FVector& Other:Retained)
        {
            // Reject overlapping neighbouring anchors, including old layers that
            // described the same leak more than once.
            if(FMath::Abs(P.Z-Other.Z)<240&&FVector::DistSquared2D(P,Other)<FMath::Square(180.))
            {Keep=false;break;}
        }
        C->SetVisibility(Keep);
        if(!Keep)continue;
        Retained.Add(P);
        // Shallow projection reduces staining of adjacent rails and hardware.
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
}
}
