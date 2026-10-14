#include "SmeltingSystem.h"
#include "VoxelBuildWorld.h"
#include "VoxelBuildPrefabActor.h"
#include "ColdSteelCampfire.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

void UColdSteelSmeltingSystem::LoadCampfireRecipes()
{
    FString Text;
    TSharedPtr<FJsonObject> Root;
    const FString Path=FPaths::ProjectContentDir()/TEXT("ColdSteelData/campfire-recipes.json");
    if(!FFileHelper::LoadFileToString(Text,*Path)
        ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)||!Root)return;
    const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;
    if(!Root->TryGetArrayField(TEXT("recipes"),Rows)||!Rows)return;
    for(const auto& Row:*Rows)
    {
        const auto Obj=Row->AsObject();if(!Obj)continue;
        bool Enabled=true;Obj->TryGetBoolField(TEXT("enabled"),Enabled);if(!Enabled)continue;
        FColdSteelSmeltingRecipe R;R.bCampfire=true;
        FString Id;Obj->TryGetStringField(TEXT("id"),Id);R.Id=FName(*Id);
        const TSharedPtr<FJsonObject>* Input=nullptr,*Output=nullptr;
        if(!Obj->TryGetObjectField(TEXT("input"),Input)||!Obj->TryGetObjectField(TEXT("output"),Output))continue;
        (*Input)->TryGetStringField(TEXT("item"),R.Input);(*Output)->TryGetStringField(TEXT("item"),R.Output);
        double N=1;(*Input)->TryGetNumberField(TEXT("count"),N);R.InputCount=FMath::Clamp<int64>(FMath::RoundToInt64(N),1,999);
        N=1;(*Output)->TryGetNumberField(TEXT("count"),N);R.OutputCount=FMath::Clamp<int64>(FMath::RoundToInt64(N),1,999);
        Obj->TryGetNumberField(TEXT("seconds"),R.Seconds);
        if(R.Id.IsNone()||R.Input.IsEmpty()||R.Output.IsEmpty()||!FMath::IsFinite(R.Seconds)||R.Seconds<=0||Find(R.Id))
        {UE_LOG(LogTemp,Warning,TEXT("Campfire: skipped invalid recipe %s"),*Id);continue;}
        Recipes.Add(MoveTemp(R));
    }
}

bool UColdSteelSmeltingSystem::CanUseCampfireTransaction(const AVoxelBuildWorld* World,FIntVector Cell,FString& Reason) const
{
    if(!World||!World->IsCampfireAt(Cell))return true;
    // Legacy workbench entry points address the local profile. Multiplayer callers must
    // use the owned PlayerState request and its per-operator server inventory instead.
    if(!World->HasAuthority()||World->GetNetMode()!=NM_Standalone)
    {Reason=TEXT("联机篝火请通过共享面板提交操作者请求");return false;}
    if(const auto* Status=Model())
        for(const auto& Intent:Status->Snapshot().SmeltIntents)
            if(Intent.WorldKey==World->BuildingWorldKey()&&Intent.X==Cell.X&&Intent.Y==Cell.Y&&Intent.Z==Cell.Z)
            {Reason=TEXT("该篝火尚有待恢复的保存操作，请重新进入存档后再试");return false;}
    return true;
}

bool UColdSteelSmeltingSystem::SettleCampfire(AVoxelBuildWorld* World,FIntVector Cell)
{
    if(!World||!World->HasAuthority())return false;
    auto Publish=[&]()
    {if(const auto* Piece=World->PrefabActorAt(Cell))if(auto* Fire=Cast<AColdSteelCampfire>(Piece->Logic()))Fire->PublishSharedState();};
    if(IsCampfireSaveBlocked(World))
    {
        if(const auto* Piece=World->PrefabActorAt(Cell))if(auto* Fire=Cast<AColdSteelCampfire>(Piece->Logic()))Fire->SetFuelSeconds(0);
        Publish();return false;
    }
    constexpr double ToSeconds=1.0/ETimespan::TicksPerSecond;
    const int64 Now=FDateTime::UtcNow().GetTicks();
    const int64 Fire=World->FurnaceFireTicks(Cell);
    const double Stored=FMath::Max(0.0,World->FuelAt(Cell));
    const double Elapsed=Fire>0&&Now>Fire?static_cast<double>(Now-Fire)*ToSeconds:0.0;
    const double Burn=FMath::Min(Stored,Elapsed);
    const double Remaining=FMath::Max(0.0,Stored-Burn);
    bool bDirty=Burn>0;
    if(auto* Job=World->FindSmeltingMutable(Cell);Job&&!Job->bCasting)
    {
        double Budget=0;
        if(Job->BurnStartTicks>0&&Job->BurnStartTicks<=Now&&Fire>0&&Fire<=Now)
            Budget=FMath::Max(0.0,Burn-FMath::Max(0.0,static_cast<double>(Job->BurnStartTicks-Fire)*ToSeconds));
        // At most 8 queued orders and 5 portions per order. No unbounded offline loop.
        for(int32 Step=0;Step<50;++Step)
        {
            if(Job->Recipe.IsNone())
            {
                if(Job->Queue.IsEmpty())break;
                const auto Q=Job->Queue[0];Job->Queue.RemoveAt(0);
                Job->Recipe=Q.Recipe;Job->BatchCount=Q.Batch;Job->ProducedBatches=0;Job->ProgressSeconds=0;bDirty=true;
            }
            const auto* R=Find(Job->Recipe);
            if(!R||!R->bCampfire||CastingStored(*Job)+R->OutputCount>CastingCapacity)break;
            const double Advance=FMath::Min(Budget,FMath::Max(0.0,R->Seconds-Job->ProgressSeconds));
            Job->ProgressSeconds+=Advance;Budget-=Advance;bDirty|=Advance>0;
            if(Job->ProgressSeconds+1e-6<R->Seconds)break;
            auto* Product=Job->Products.FindByPredicate([&](const auto& P){return P.Item==R->Output;});
            if(Product)Product->Count+=R->OutputCount;else Job->Products.Add({R->Output,R->OutputCount});
            Job->ProgressSeconds=FMath::Max(0.0,Job->ProgressSeconds-R->Seconds);++Job->ProducedBatches;bDirty=true;
            if(Job->ProducedBatches>=Job->BatchCount){Job->Recipe=NAME_None;Job->ProgressSeconds=0;}
        }
        const auto* R=Find(Job->Recipe);
        const int64 Next=Remaining>0&&R&&R->bCampfire&&CastingStored(*Job)+R->OutputCount<=CastingCapacity?Now:0;
        if(Job->BurnStartTicks!=Next){Job->BurnStartTicks=Next;bDirty=true;}
    }
    World->SetFuel(Cell,Remaining);
    World->SetFurnaceFireTicks(Cell,Remaining>0?Now:0);
    if(bDirty)World->MarkSmeltingDirty();
    Publish();
    return bDirty;
}
