#include "SmeltingSystem.h"
#include "VoxelBuildWorld.h"
#include "VoxelBuildPrefabActor.h"
#include "ColdSteelCampfire.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Items/FoodSpoilage.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace
{
    void AppendCampfireFood(TArray<FVoxelCastingProduct>& Products,FColdSteelItem Item)
    {
        if(Item.Count<=0)return;
        auto& Product=Products.AddDefaulted_GetRef();
        Product.Item=Item.Definition;Product.Count=Item.Count;Product.Payload=MoveTemp(Item);
    }
    bool SettleCampfireFood(TArray<FColdSteelItem>& Items,const UColdSteelStatusModel* Model,
        const FFoodClockSample& Clock,bool& Changed,FString& Reason)
    {
        // No per-frame rebase/JSON rebuild for still-fresh food in the same clock domain.
        const bool Needed=Items.ContainsByPredicate([&](const auto& I)
        {return ColdSteelFood::LifetimeDays(I)>0&&(I.FoodVersion!=1||I.FoodClockId!=Clock.Id||ColdSteelFood::IsExpired(I,Clock));});
        if(!Needed)return true;
        const bool Updated=ColdSteelFood::SettleLoose(Items,Model,Clock,Reason);
        if(!Reason.IsEmpty())return false;
        Changed|=Updated;return true;
    }
    bool SettleCampfireProducts(FVoxelSmeltingJob& Job,const UColdSteelStatusModel* Model,
        const FFoodClockSample& Clock,bool& Changed,FString& Reason)
    {
        bool NeedsSettlement=false;
        for(const auto& Product:Job.Products)
        {
            if(Product.Count<=0||Product.Payload.Count!=Product.Count||Product.Payload.Definition!=Product.Item
                ||Product.Payload.Data.IsEmpty())return false;
            const auto& Item=Product.Payload;
            NeedsSettlement|=ColdSteelFood::LifetimeDays(Item)>0.
                &&(Item.FoodVersion!=1||Item.FoodClockId!=Clock.Id||ColdSteelFood::IsExpired(Item,Clock));
        }
        if(!NeedsSettlement)return true;
        TArray<FColdSteelItem> Items;Items.Reserve(Job.Products.Num());
        for(const auto& Product:Job.Products)Items.Add(Product.Payload);
        bool ProductChanged=false;
        if(!SettleCampfireFood(Items,Model,Clock,ProductChanged,Reason))return false;
        if(ProductChanged)
        {
            Job.Products.Reset();for(auto& Item:Items)AppendCampfireFood(Job.Products,MoveTemp(Item));
            Changed=true;
        }
        return true;
    }
    bool MigrateCampfireEscrow(FVoxelSmeltingJob& Job,const UColdSteelSmeltingSystem* System,
        const UColdSteelStatusModel* Model,const FFoodClockSample& Clock,int64 Now)
    {
        if(Job.FoodEscrowVersion==1)return true;
        if(Job.FoodEscrowVersion!=0)return false;
        auto Restore=[&](FName Recipe,int64 Batch,TArray<FColdSteelItem>& Items)
        {
            if(Batch==0)return true;
            const auto* R=System->Find(Recipe);
            if(!R||!R->bCampfire||Batch<0||Batch>5||R->InputCount<=0||R->InputCount>MAX_int64/Batch)return false;
            auto Item=Model->CreateItem(R->Input,R->InputCount*Batch);
            if(Item.Data.IsEmpty())return false;
            ColdSteelFood::Stamp(Item,Clock);Items.Add(MoveTemp(Item));return true;
        };
        Job.Ingredients.Reset();
        if(!Job.Recipe.IsNone()&&!Restore(Job.Recipe,FMath::Max<int64>(0,Job.BatchCount-Job.ProducedBatches),Job.Ingredients))return false;
        for(auto& Order:Job.Queue)
        {Order.Ingredients.Reset();if(!Restore(Order.Recipe,Order.Batch,Order.Ingredients))return false;}
        for(auto& Product:Job.Products)
        {
            if(Product.Count<=0)return false;
            Product.Payload=Model->CreateItem(Product.Item,Product.Count);
            if(Product.Payload.Data.IsEmpty())return false;
            ColdSteelFood::Stamp(Product.Payload,Clock);
        }
        // Old un-timed raw materials and cooked products begin aging at first migration.
        Job.FoodEscrowVersion=1;Job.FoodClockId=Clock.Id;Job.FoodSampleDay=Clock.Day;Job.FoodUtcTicks=Now;
        return true;
    }
    bool RefreshCampfireIngredients(TArray<FColdSteelItem>& Ingredients,const FColdSteelSmeltingRecipe& Recipe,
        const UColdSteelStatusModel* Model,const FFoodClockSample& Clock,TArray<FVoxelCastingProduct>& Products,
        int64& Pending,bool& NextExpired,bool& Changed,FString& Reason)
    {
        int64 NextNeeded=Recipe.InputCount;NextExpired=false;
        for(const auto& Item:Ingredients)if(Item.Definition==Recipe.Input&&NextNeeded>0)
        {NextExpired|=ColdSteelFood::IsExpired(Item,Clock);NextNeeded-=FMath::Min(NextNeeded,Item.Count);}
        if(!SettleCampfireFood(Ingredients,Model,Clock,Changed,Reason))return false;
        int64 RawCount=0;
        for(int32 N=Ingredients.Num()-1;N>=0;--N)
        {
            if(Ingredients[N].Definition!=Recipe.Input)
            {AppendCampfireFood(Products,MoveTemp(Ingredients[N]));Ingredients.RemoveAt(N);Changed=true;}
            else
            {
                if(Ingredients[N].Count<=0||RawCount>MAX_int64-Ingredients[N].Count)return false;
                RawCount+=Ingredients[N].Count;
            }
        }
        if(Recipe.InputCount<=0)return false;
        Pending=RawCount/Recipe.InputCount;
        // A future multi-input recipe may lose only part of a portion. Return the
        // surviving remainder through the output buffer instead of discarding it.
        int64 Remainder=RawCount%Recipe.InputCount;
        for(int32 N=Ingredients.Num()-1;N>=0&&Remainder>0;--N)
        {
            auto Part=Ingredients[N];Part.Count=FMath::Min(Remainder,Part.Count);
            if(Part.Count<Ingredients[N].Count)Part.InstanceId=FGuid::NewGuid().ToString(EGuidFormats::Digits);
            Ingredients[N].Count-=Part.Count;Remainder-=Part.Count;
            AppendCampfireFood(Products,MoveTemp(Part));Changed=true;
            if(Ingredients[N].Count==0)Ingredients.RemoveAt(N);
        }
        return true;
    }
    bool ConsumeCampfireIngredients(TArray<FColdSteelItem>& Ingredients,const FString& Definition,int64 Count)
    {
        for(int32 N=0;N<Ingredients.Num()&&Count>0;)
        {
            auto& Item=Ingredients[N];if(Item.Definition!=Definition){++N;continue;}
            const int64 Take=FMath::Min(Count,Item.Count);Item.Count-=Take;Count-=Take;
            if(Item.Count==0)Ingredients.RemoveAt(N);else ++N;
        }
        return Count==0;
    }
}

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
    if(auto* StoredJob=World->FindSmeltingMutable(Cell);StoredJob&&!StoredJob->bCasting)
    {
        const auto Clock=ColdSteelFood::Clock(World);const auto* Status=Model();
        if(!Status||!Clock.Id.IsValid())return false;
        // Work on a proposal: a failed item conversion preserves the entire station.
        auto Job=*StoredJob;FString Reason;const bool Legacy=Job.FoodEscrowVersion==0;
        if(!MigrateCampfireEscrow(Job,this,Status,Clock,Now))return false;
        bDirty|=Legacy;
        // A building checkpoint can be newer than the restored host clock even
        // within the same domain. Materialize its already-earned age before
        // rebinding; otherwise restoring the older day would make food younger.
        if(Job.FoodClockId!=Clock.Id||Clock.Day<Job.FoodSampleDay)
        {
            const FFoodClockSample Previous{Job.FoodClockId,Job.FoodSampleDay};
            auto Rebind=[&](FColdSteelItem& Item)
            {if(ColdSteelFood::LifetimeDays(Item)>0.)ColdSteelFood::Stamp(Item,Clock,ColdSteelFood::AgeDays(Item,Previous));};
            for(auto& Item:Job.Ingredients)Rebind(Item);
            for(auto& Order:Job.Queue)for(auto& Item:Order.Ingredients)Rebind(Item);
            for(auto& Product:Job.Products)Rebind(Product.Payload);
            bDirty=true;
        }
        const double DayDelta=Job.FoodClockId==Clock.Id?FMath::Max(0.,Clock.Day-Job.FoodSampleDay):0.;
        const double UtcSpan=Job.FoodUtcTicks>0&&Now>Job.FoodUtcTicks?double(Now-Job.FoodUtcTicks):0.;
        auto At=[&](int64 Utc)
        {
            auto Sample=Clock;
            // Natural days never accrue offline. An offline UTC cooking completion
            // therefore starts at the restored natural clock, not a wall-clock age.
            if(UtcSpan>0.)Sample.Day-=DayDelta*FMath::Clamp(double(Now-Utc)/UtcSpan,0.,1.);
            return Sample;
        };
        double Budget=0;
        if(Job.BurnStartTicks>0&&Job.BurnStartTicks<=Now&&Fire>0&&Fire<=Now)
            Budget=FMath::Max(0.0,Burn-FMath::Max(0.0,static_cast<double>(Job.BurnStartTicks-Fire)*ToSeconds));
        int64 Cursor=Budget>0?FMath::Max(Fire,Job.BurnStartTicks):Now;
        // At most 8 queued orders and 5 portions per order. No unbounded offline loop.
        for(int32 Step=0;Step<50;++Step)
        {
            if(Job.Recipe.IsNone())
            {
                if(Job.Queue.IsEmpty())break;
                auto Q=MoveTemp(Job.Queue[0]);Job.Queue.RemoveAt(0);
                Job.Recipe=Q.Recipe;Job.BatchCount=Q.Batch;Job.Ingredients=MoveTemp(Q.Ingredients);
                Job.bMaterialsWaived=Q.bMaterialsWaived;
                Job.ProducedBatches=0;Job.ProgressSeconds=0;bDirty=true;
            }
            const auto* R=Find(Job.Recipe);if(!R||!R->bCampfire)break;
            int64 Pending=0;bool NextExpired=false;
            if(!RefreshCampfireIngredients(Job.Ingredients,*R,Status,At(Cursor),Job.Products,Pending,NextExpired,bDirty,Reason)
                ||!SettleCampfireProducts(Job,Status,At(Cursor),bDirty,Reason))return false;
            Job.BatchCount=Job.ProducedBatches+Pending;
            if(NextExpired)Job.ProgressSeconds=0;
            if(Pending==0){Job.Recipe=NAME_None;Job.ProgressSeconds=0;bDirty=true;continue;}
            if(CastingStored(Job)+R->OutputCount>CastingCapacity)break;
            const double Advance=FMath::Min(Budget,FMath::Max(0.0,R->Seconds-Job.ProgressSeconds));
            Job.ProgressSeconds+=Advance;Budget-=Advance;Cursor+=FMath::RoundToInt64(Advance*ETimespan::TicksPerSecond);bDirty|=Advance>0;
            if(Job.ProgressSeconds+1e-6<R->Seconds)break;
            const auto CompletedAt=At(Cursor);
            // Recheck at the completion boundary: stale paid meat cannot become fresh cooked food.
            if(!RefreshCampfireIngredients(Job.Ingredients,*R,Status,CompletedAt,Job.Products,Pending,NextExpired,bDirty,Reason))return false;
            Job.BatchCount=Job.ProducedBatches+Pending;
            if(NextExpired||Pending==0)
            {Job.ProgressSeconds=0;if(Pending==0)Job.Recipe=NAME_None;bDirty=true;continue;}
            if(!ConsumeCampfireIngredients(Job.Ingredients,R->Input,R->InputCount))return false;
            auto Cooked=Status->CreateItem(R->Output,R->OutputCount);if(Cooked.Data.IsEmpty())return false;
            ColdSteelFood::Stamp(Cooked,CompletedAt);
            AppendCampfireFood(Job.Products,MoveTemp(Cooked));
            Job.ProgressSeconds=FMath::Max(0.0,Job.ProgressSeconds-R->Seconds);++Job.ProducedBatches;bDirty=true;
            if(Job.ProducedBatches>=Job.BatchCount){Job.Recipe=NAME_None;Job.ProgressSeconds=0;}
        }
        // Waiting/cold ingredients and unclaimed products age too, without fuel or panel access.
        if(const auto* R=Find(Job.Recipe);R&&R->bCampfire)
        {
            int64 Pending=0;bool NextExpired=false;
            if(!RefreshCampfireIngredients(Job.Ingredients,*R,Status,Clock,Job.Products,Pending,NextExpired,bDirty,Reason))return false;
            Job.BatchCount=Job.ProducedBatches+Pending;
            if(NextExpired)Job.ProgressSeconds=0;
            if(Pending==0){Job.Recipe=NAME_None;Job.ProgressSeconds=0;bDirty=true;}
        }
        for(auto& Order:Job.Queue)if(const auto* R=Find(Order.Recipe);R&&R->bCampfire)
        {
            int64 Pending=0;bool NextExpired=false;
            if(!RefreshCampfireIngredients(Order.Ingredients,*R,Status,Clock,Job.Products,Pending,NextExpired,bDirty,Reason))return false;
            Order.Batch=Pending;
        }
        bDirty|=Job.Queue.RemoveAll([](const auto& Order){return Order.Batch<=0&&Order.Ingredients.IsEmpty();})>0;
        if(!SettleCampfireProducts(Job,Status,Clock,bDirty,Reason))return false;
        const auto* R=Find(Job.Recipe);
        const int64 Next=Remaining>0&&R&&R->bCampfire&&CastingStored(Job)+R->OutputCount<=CastingCapacity?Now:0;
        if(Job.BurnStartTicks!=Next){Job.BurnStartTicks=Next;bDirty=true;}
        bDirty|=Job.FoodClockId!=Clock.Id;
        Job.FoodClockId=Clock.Id;Job.FoodSampleDay=Clock.Day;Job.FoodUtcTicks=Now;
        *StoredJob=MoveTemp(Job);
    }
    World->SetFuel(Cell,Remaining);
    World->SetFurnaceFireTicks(Cell,Remaining>0?Now:0);
    if(bDirty)World->MarkSmeltingDirty();
    Publish();
    return bDirty;
}
