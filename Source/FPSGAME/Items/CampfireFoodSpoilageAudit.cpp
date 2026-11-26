#include "FoodSpoilage.h"
#include "../Building/CampfireSharedTypes.h"
#include "../Building/ColdSteelCampfire.h"
#include "../Building/SmeltingSystem.h"
#include "../Building/VoxelBuildPalette.h"
#include "../Building/VoxelBuildPersistence.h"
#include "../Building/VoxelBuildWorld.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Materials/Material.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Misc/SecureHash.h"

void RunCampfireRecoveryAudit(UWorld*,UColdSteelStatusModel*,AVoxelBuildWorld*,FIntVector,
    TFunctionRef<void(bool,const FString&)>);

namespace
{
int64 CampfireAuditCount(const TArray<FColdSteelItem>& Items,const TCHAR* Definition)
{int64 Count=0;for(const auto& Item:Items)if(Item.Definition==Definition)Count+=Item.Count;return Count;}
int64 CampfireAuditOutput(const FCampfireSharedState& State,const TCHAR* Definition)
{int64 Count=0;for(const auto& Product:State.Products)if(Product.Item==Definition)Count+=Product.Count;return Count;}
bool CampfireAuditAgeEqual(const FColdSteelItem& A,const FColdSteelItem& B)
{return A.FoodVersion==B.FoodVersion&&A.FoodClockId==B.FoodClockId&&A.FoodSampleDay==B.FoodSampleDay&&A.FoodAgeDays==B.FoodAgeDays;}
FCampfireProduct CampfireAuditProduct(const FColdSteelItem& Item)
{FCampfireProduct Product;Product.Item=Item.Definition;Product.Count=Item.Count;Product.Payload=Item;return Product;}
}

// Invoke after the main audit creates its authoritative pawn. This deliberately
// replaces the isolated audit inventory; the caller can use its normal Reset().
void RunCampfireFoodSpoilageAudit(UWorld* World,UColdSteelStatusModel* Model,
    TFunctionRef<void(bool,const FString&)> Check)
{
    auto Report=[&](bool Pass,const FString& Name,const FString& Detail=FString())
    {Check(Pass,TEXT("campfire: ")+Name+(Detail.IsEmpty()?FString():TEXT(" | ")+Detail));return Pass;};
    FString Saved=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir());FPaths::NormalizeDirectoryName(Saved);
    if(!Report(World&&Model&&Model->IsAudit()&&World->GetNetMode()==NM_Standalone
        &&Saved.Contains(TEXT("/FoodSpoilage20261015/TestRuns/")),TEXT("isolated audit guard")))return;
    auto* Cooking=World->GetGameInstance()->GetSubsystem<UColdSteelSmeltingSystem>();
    const auto Clock=ColdSteelFood::Clock(World);
    if(!Report(Cooking&&Clock.Id.IsValid(),TEXT("authoritative cooking and natural clock available")))return;
    const auto* Recipe=Cooking->Find(TEXT("roast_sausage"));
    if(!Report(Recipe&&Recipe->InputCount==1&&Recipe->OutputCount==1,TEXT("sausage recipe available")))return;
    const FIntVector Cell(0,0,0);
    const FString WorldKey=TEXT("FoodSpoilageCampfireAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FTCHARToUTF8 KeyBytes(*WorldKey);FMD5 KeyHash;uint8 Digest[16];
    KeyHash.Update(reinterpret_cast<const uint8*>(KeyBytes.Get()),KeyBytes.Length());KeyHash.Final(Digest);
    const FString Slot=TEXT("Voxel20_")+BytesToHex(Digest,16);
    FVoxelDiskSnapshot Initial;Initial.WorldKey=WorldKey;
    auto& Piece=Initial.Prefabs.AddDefaulted_GetRef();Piece.Id=TEXT("campfire");Piece.Cell=Cell;
    Piece.InstanceId=FGuid::NewGuid();Piece.Footprint=FIntVector(5,5,4);
    if(!Report(VoxelPersistence::Write(Slot,Initial),TEXT("isolated current-version building fixture saved")))return;
    auto* Building=World->SpawnActor<AVoxelBuildWorld>();
    if(!Report(Building!=nullptr,TEXT("building owner spawned")))return;
    ON_SCOPE_EXIT {if(IsValid(Building)){Building->FlushCampfirePersistence();Building->Destroy();}};
    auto* Palette=NewObject<UVoxelBuildPalette>(Building);
    auto& Material=Palette->Materials.AddDefaulted_GetRef();Material.Id=TEXT("wood");Material.Surface=UMaterial::GetDefaultMaterial(MD_Surface);
    auto& Definition=Palette->Components.AddDefaulted_GetRef();Definition.Id=TEXT("campfire");
    Definition.ActorClass=AColdSteelCampfire::StaticClass();Definition.Footprint=Piece.Footprint;
    if(!Report(Building->Initialize(WorldKey,Palette)&&Building->IsCampfireAt(Cell),TEXT("real building fixture loaded"),Building->ResultMessage()))return;
    auto Near=[](double A,double B,double Epsilon=1.e-8){return FMath::Abs(A-B)<=Epsilon;};
    auto Item=[&](const TCHAR* Id,double Age=0.,int64 Count=1)
    {auto Food=Model->CreateItem(Id,Count);ColdSteelFood::Stamp(Food,ColdSteelFood::Clock(World),Age);return Food;};
    auto FreshState=[&]()
    {
        const auto Current=ColdSteelFood::Clock(World);FCampfireSharedState State;
        State.FoodEscrowVersion=1;State.FoodClockId=Current.Id;State.FoodSampleDay=Current.Day;
        State.FoodUtcTicks=FDateTime::UtcNow().GetTicks();return State;
    };
    auto EmptyInventory=[&]()
    {
        auto P=Model->Snapshot();P.Items.Reset();P.ActiveProductionTool.Reset();P.ActiveWeaponSlot=6;
        P.Hotbar.Init(TEXT(""),4);P.HotbarDefinitions.Init(TEXT(""),4);for(auto& Binding:P.QuickBindings)Binding={};
        Model->EndStorageSession();return Model->CommitState(MoveTemp(P));
    };
    FString Reason;
    {
        auto S=FreshState();S.Recipe=Recipe->Id;S.Ingredients={Item(TEXT("raw_sausage"),.5)};
        auto& Q=S.Queue.AddDefaulted_GetRef();Q.Recipe=TEXT("roast_chicken_leg");Q.Ingredients={Item(TEXT("raw_chicken_leg"),.25)};
        S.Products.Add(CampfireAuditProduct(Item(TEXT("roasted_lamb_ribs"),.5)));
        S.FoodSampleDay+=2.;Building->WriteCampfireState(Cell,S);Cooking->SettleCampfire(Building,Cell);
        const auto Restored=Cooking->CampfireState(Building,Cell);const auto Current=ColdSteelFood::Clock(World);
        Report(Restored.Ingredients.Num()==1&&Restored.Queue.Num()==1&&Restored.Queue[0].Ingredients.Num()==1&&Restored.Products.Num()==1
            &&Near(ColdSteelFood::AgeDays(Restored.Ingredients[0],Current),2.5)
            &&Near(ColdSteelFood::AgeDays(Restored.Queue[0].Ingredients[0],Current),2.25)
            &&Near(ColdSteelFood::AgeDays(Restored.Products[0].Payload,Current),2.5),TEXT("same-domain clock rollback preserves checkpoint age for active, queued and cooked food"));
        Cooking->SettleCampfire(Building,Cell);const auto Twice=Cooking->CampfireState(Building,Cell);
        Report(Twice.Products.Num()==1&&Restored.Products.Num()==1
            &&CampfireAuditAgeEqual(Twice.Products[0].Payload,Restored.Products[0].Payload),TEXT("clock rollback recovery is idempotent"));
    }
    {
        auto S=FreshState();S.Recipe=Recipe->Id;auto Raw=Item(TEXT("raw_sausage"),1.5);S.Ingredients={Raw};
        auto Queued=Item(TEXT("raw_large_lamb"),1.);auto& Q=S.Queue.AddDefaulted_GetRef();Q.Recipe=TEXT("roast_large_lamb");Q.Ingredients={Queued};
        auto Cooked=Item(TEXT("roasted_lamb_ribs"),2.5);S.Products.Add(CampfireAuditProduct(Cooked));S.FoodSampleDay+=2.;
        const int64 Expected=int64(Raw.Width)*Raw.Height+int64(Queued.Width)*Queued.Height+int64(Cooked.Width)*Cooked.Height;
        Building->WriteCampfireState(Cell,S);Cooking->SettleCampfire(Building,Cell);const auto After=Cooking->CampfireState(Building,Cell);
        Report(After.Recipe.IsNone()&&After.Ingredients.IsEmpty()&&After.Queue.IsEmpty()
            &&CampfireAuditOutput(After,TEXT("spoiled_food"))==Expected,TEXT("expired checkpoint food cannot become fresh after clock rollback"));
    }
    {
        auto S=FreshState();S.Recipe=Recipe->Id;S.Ingredients={Item(TEXT("raw_sausage"),2.8)};
        const int64 Earlier=FDateTime::UtcNow().GetTicks()-FMath::RoundToInt64((Recipe->Seconds+30.)*ETimespan::TicksPerSecond);
        S.FireTicks=S.BurnTicks=S.FoodUtcTicks=Earlier;S.Fuel=Recipe->Seconds+10.;
        Building->WriteCampfireState(Cell,S);Cooking->SettleCampfire(Building,Cell);const auto After=Cooking->CampfireState(Building,Cell);
        Report(After.Recipe.IsNone()&&After.Products.Num()==1&&After.Products[0].Item==Recipe->Output
            &&Near(ColdSteelFood::AgeDays(After.Products[0].Payload,ColdSteelFood::Clock(World)),0.),TEXT("offline cooking completion starts cooked lifetime at restored natural time"));
    }
    {
        const auto Current=ColdSteelFood::Clock(World);const double DaySpan=FMath::Min(.02,Current.Day*.5);
        auto S=FreshState();S.Recipe=Recipe->Id;
        const FFoodClockSample EarlierClock{Current.Id,Current.Day-DaySpan};auto Raw=Item(TEXT("raw_sausage"));ColdSteelFood::Stamp(Raw,EarlierClock);S.Ingredients={Raw};
        const int64 Earlier=FDateTime::UtcNow().GetTicks()-120*ETimespan::TicksPerSecond;
        S.FireTicks=S.BurnTicks=S.FoodUtcTicks=Earlier;S.FoodSampleDay=EarlierClock.Day;S.Fuel=60.;
        Building->WriteCampfireState(Cell,S);Cooking->SettleCampfire(Building,Cell);const auto After=Cooking->CampfireState(Building,Cell);
        const double Expected=DaySpan*(120.-Recipe->Seconds)/120.;
        Report(DaySpan>0.&&After.Products.Num()==1&&Near(ColdSteelFood::AgeDays(After.Products[0].Payload,Current),Expected,1.e-4),
            TEXT("cooked age starts at completion inside elapsed natural/UTC segment, not collection"));
    }
    {
        auto S=FreshState();S.Recipe=Recipe->Id;S.Ingredients={Item(TEXT("raw_sausage"),.25)};
        const auto Expired=Item(TEXT("raw_large_lamb"),3.);auto& Q=S.Queue.AddDefaulted_GetRef();Q.Recipe=TEXT("roast_large_lamb");Q.Ingredients={Expired};
        Building->WriteCampfireState(Cell,S);Cooking->SettleCampfire(Building,Cell);const auto After=Cooking->CampfireState(Building,Cell);
        Report(After.Recipe==Recipe->Id&&After.Ingredients.Num()==1&&After.Queue.IsEmpty()
            &&CampfireAuditOutput(After,TEXT("spoiled_food"))==int64(Expired.Width)*Expired.Height
            &&CampfireAuditOutput(After,TEXT("roasted_large_lamb"))==0,TEXT("waiting raw meat expires without fuel and never cooks"));
    }
    {
        auto S=FreshState();const auto RottenCooked=Item(TEXT("roasted_large_lamb"),4.,60);
        S.Products.Add(CampfireAuditProduct(RottenCooked));Building->WriteCampfireState(Cell,S);Cooking->SettleCampfire(Building,Cell);
        const auto After=Cooking->CampfireState(Building,Cell);const int64 Expected=int64(RottenCooked.Width)*RottenCooked.Height*60;
        bool Stacks=true;for(const auto& P:After.Products)Stacks&=P.Payload.Count==P.Count&&P.Count<=10&&P.Payload.StackMax==10;
        Report(Expected>UColdSteelSmeltingSystem::CastingCapacity&&CampfireAuditOutput(After,TEXT("spoiled_food"))==Expected&&Stacks,
            TEXT("output-slot spoilage preserves area-scaled quantity above 60-slot cooking limit"));
        Cooking->SettleCampfire(Building,Cell);
        Report(CampfireAuditOutput(Cooking->CampfireState(Building,Cell),TEXT("spoiled_food"))==Expected,TEXT("repeated output spoilage does not duplicate"));
    }
    {
        auto S=FreshState();const auto Cooked=Item(TEXT("roasted_lamb_ribs"),2.25);S.Products.Add(CampfireAuditProduct(Cooked));
        Building->WriteCampfireState(Cell,S);
        const bool Collected=EmptyInventory()&&Cooking->ExecuteCampfire(Building,Cell,Model,nullptr,2,NAME_None,1,Reason);
        const auto* Claimed=Model->FindItem(Cooked.InstanceId);
        Report(Collected&&Claimed&&CampfireAuditAgeEqual(*Claimed,Cooked)&&Cooking->CampfireState(Building,Cell).Products.IsEmpty(),
            TEXT("real collect transaction retains exact cooked batch lifetime"),Reason);
        Report(!Cooking->ExecuteCampfire(Building,Cell,Model,nullptr,2,NAME_None,1,Reason)
            &&CampfireAuditCount(Model->Items(),TEXT("roasted_lamb_ribs"))==1,TEXT("repeated collection cannot duplicate cooked food"),Reason);
    }
    {
        auto S=FreshState();const auto Cooked=Item(TEXT("roasted_large_lamb"),1.25),Expired=Item(TEXT("roasted_large_lamb"),4.);
        S.Products.Add(CampfireAuditProduct(Cooked));S.Products.Add(CampfireAuditProduct(Expired));
        Building->WriteCampfireState(Cell,S);Cooking->SettleCampfire(Building,Cell);
        const auto Before=Cooking->CampfireState(Building,Cell);const int64 Yield=int64(Expired.Width)*Expired.Height*Expired.Count;
        bool Seeded=EmptyInventory();auto Full=Model->Snapshot();
        for(int32 BagCell=0;BagCell<72;++BagCell)
        {auto Block=Model->CreateItem(TEXT("spoiled_food"),10);Block.Place=0;Block.Cell=BagCell;Full.Items.Add(MoveTemp(Block));}
        Seeded=Model->CommitState(MoveTemp(Full))&&Seeded;
        const auto InventoryBefore=Model->Snapshot();
        Seeded=Seeded&&InventoryBefore.Items.Num()==72&&CampfireAuditCount(InventoryBefore.Items,TEXT("spoiled_food"))==720
            &&Cooked.Width==2&&Cooked.Height==2&&Yield==4&&Before.Products.Num()==2
            &&CampfireAuditOutput(Before,TEXT("roasted_large_lamb"))==1&&CampfireAuditOutput(Before,TEXT("spoiled_food"))==Yield;
        Report(Seeded,TEXT("full-bag collect fixture has 72 full stacks and both fresh cooked and converted expired products"));
        Reason.Reset();const bool Rejected=Seeded&&!Cooking->ExecuteCampfire(Building,Cell,Model,nullptr,2,NAME_None,1,Reason);
        const auto InventoryAfter=Model->Snapshot();const auto After=Cooking->CampfireState(Building,Cell);
        bool InventoryUnchanged=InventoryAfter.CampfireInventoryRevision==InventoryBefore.CampfireInventoryRevision
            &&InventoryAfter.Items.Num()==InventoryBefore.Items.Num();
        if(InventoryUnchanged)for(int32 N=0;N<InventoryBefore.Items.Num();++N)
            InventoryUnchanged&=FColdSteelItem::StaticStruct()->CompareScriptStruct(&InventoryBefore.Items[N],&InventoryAfter.Items[N],0);
        bool ProductsUnchanged=After.Products.Num()==Before.Products.Num();
        if(ProductsUnchanged)for(int32 N=0;N<Before.Products.Num();++N)
            ProductsUnchanged&=After.Products[N].Item==Before.Products[N].Item&&After.Products[N].Count==Before.Products[N].Count
                &&FColdSteelItem::StaticStruct()->CompareScriptStruct(&Before.Products[N].Payload,&After.Products[N].Payload,0);
        Report(Rejected&&InventoryUnchanged&&ProductsUnchanged,
            TEXT("real full-bag collect failure preserves every inventory and product field including cooked batch age"),Reason);

        // Free exactly the fresh 2x2 meal footprint plus one cell for its expired peer's four-unit yield.
        auto Space=Model->Snapshot();const int32 Removed=Space.Items.RemoveAll([](const auto& I)
        {return I.Place==0&&(I.Cell==0||I.Cell==1||I.Cell==18||I.Cell==19||I.Cell==2);});
        const bool Freed=Removed==5&&Model->CommitState(MoveTemp(Space));
        const int64 SpoiledBefore=CampfireAuditCount(Model->Items(),TEXT("spoiled_food"));
        Reason.Reset();const bool Collected=Seeded&&Freed&&Cooking->ExecuteCampfire(Building,Cell,Model,nullptr,2,NAME_None,1,Reason);
        const auto* Claimed=Model->FindItem(Cooked.InstanceId);
        Report(Collected&&SpoiledBefore==670&&Claimed&&Claimed->Count==Cooked.Count&&CampfireAuditAgeEqual(*Claimed,Cooked)
            &&CampfireAuditCount(Model->Items(),TEXT("roasted_large_lamb"))==Cooked.Count
            &&CampfireAuditCount(Model->Items(),TEXT("spoiled_food"))==SpoiledBefore+Yield
            &&Cooking->CampfireState(Building,Cell).Products.IsEmpty(),
            TEXT("real collect after freeing five cells preserves cooked age and the complete expired footprint yield"),Reason);
    }
    {
        auto S=FreshState();S.Recipe=Recipe->Id;
        const auto Raw=Item(TEXT("raw_sausage"),1.5),Queued=Item(TEXT("raw_lamb_ribs"),2.25),Cooked=Item(TEXT("roasted_chicken_leg"),3.);
        S.Ingredients={Raw};S.Products.Add(CampfireAuditProduct(Cooked));auto& Q=S.Queue.AddDefaulted_GetRef();Q.Recipe=TEXT("roast_lamb_ribs");Q.Ingredients={Queued};
        Building->WriteCampfireState(Cell,S);
        bool Returned=EmptyInventory()&&Cooking->ExecuteCampfire(Building,Cell,Model,nullptr,3,NAME_None,1,Reason);
        for(const auto& Before:{Raw,Queued,Cooked})
        {const auto* Found=Model->FindItem(Before.InstanceId);Returned&=Found&&CampfireAuditAgeEqual(*Found,Before);}
        Report(Returned&&Cooking->CampfireState(Building,Cell).Products.IsEmpty()&&Cooking->CampfireState(Building,Cell).Ingredients.IsEmpty(),
            TEXT("real teardown returns active raw, queued raw and cooked batches without refreshing age"),Reason);
    }
    {
        Building->WriteCampfireState(Cell,FreshState());EmptyInventory();auto Profile=Model->Snapshot();Profile.Items.Add(Item(TEXT("raw_sausage"),3.));
        const bool Seeded=Model->CommitState(Profile);
        Report(Seeded&&!Cooking->ExecuteCampfire(Building,Cell,Model,nullptr,1,Recipe->Id,1,Reason)
            &&Cooking->CampfireState(Building,Cell).Recipe.IsNone(),TEXT("authoritative input transaction rejects expired raw meat"),Reason);
    }
    {
        auto S=FreshState();S.Recipe=Recipe->Id;S.Ingredients={Item(TEXT("raw_sausage"),1.)};
        auto& Q=S.Queue.AddDefaulted_GetRef();Q.Recipe=TEXT("roast_large_lamb");Q.Ingredients={Item(TEXT("raw_large_lamb"),2.)};
        S.Products.Add(CampfireAuditProduct(Item(TEXT("roasted_lamb_ribs"),2.5)));Building->WriteCampfireState(Cell,S);
        FVoxelDiskSnapshot Snapshot=Initial;const auto* Job=Building->FindSmelting(Cell);if(Job)Snapshot.Smelting.Add(*Job);
        if(!Report(Job&&Snapshot.Smelting.Num()==1,TEXT("codec fixture has one actual campfire job")))return;
        TArray<uint8> Bytes;
        for(const int32 Version:{13,GVoxelBuildSaveVersion})for(const bool FreeActive:{false,true})
        {
            Snapshot.Version=Version;Snapshot.Smelting[0].bMaterialsWaived=FreeActive;
            Snapshot.Smelting[0].Queue[0].bMaterialsWaived=!FreeActive;
            const bool Encoded=VoxelPersistence::Encode(Snapshot,Bytes);auto* Decoded=Encoded?VoxelPersistence::Decode(Bytes):nullptr;
            bool Preserved=Decoded&&Decoded->Version==Version&&Decoded->Smelting.Num()==1;
            if(Preserved)
            {
                const auto& Loaded=Decoded->Smelting[0];Preserved=Loaded.FoodEscrowVersion==1&&Loaded.Ingredients.Num()==1&&Loaded.Queue.Num()==1
                    &&Loaded.Queue[0].Ingredients.Num()==1&&Loaded.Products.Num()==1
                    &&Loaded.bMaterialsWaived==(Version>=14&&FreeActive)
                    &&Loaded.Queue[0].bMaterialsWaived==(Version>=14&&!FreeActive)
                    &&FColdSteelItem::StaticStruct()->CompareScriptStruct(&Loaded.Ingredients[0],&S.Ingredients[0],0)
                    &&FColdSteelItem::StaticStruct()->CompareScriptStruct(&Loaded.Queue[0].Ingredients[0],&S.Queue[0].Ingredients[0],0)
                    &&FColdSteelItem::StaticStruct()->CompareScriptStruct(&Loaded.Products[0].Payload,&S.Products[0].Payload,0);
            }
            Report(Preserved,FString::Printf(TEXT("v%d codec preserves escrow and active/queued paid provenance (active free=%d)"),Version,FreeActive));
        }
        Snapshot.Version=12;Bytes.Reset();const bool OldEncoded=VoxelPersistence::Encode(Snapshot,Bytes);auto* Old=OldEncoded?VoxelPersistence::Decode(Bytes):nullptr;
        Report(Old&&Old->Version==12&&Old->Smelting.Num()==1&&Old->Smelting[0].FoodEscrowVersion==0
            &&Old->Smelting[0].Ingredients.IsEmpty()&&Old->Smelting[0].Products.Num()==1,TEXT("v12 building byte layout remains readable without v13 escrow"));
        auto Legacy=S;Legacy.FoodEscrowVersion=0;Legacy.Ingredients.Reset();for(auto& Order:Legacy.Queue)Order.Ingredients.Reset();
        for(auto& Product:Legacy.Products)Product.Payload={};Building->WriteCampfireState(Cell,Legacy);Cooking->SettleCampfire(Building,Cell);
        const auto Migrated=Cooking->CampfireState(Building,Cell);const auto Current=ColdSteelFood::Clock(World);
        Report(Migrated.FoodEscrowVersion==1&&Migrated.Ingredients.Num()==1&&Migrated.Queue.Num()==1&&Migrated.Queue[0].Ingredients.Num()==1
            &&Migrated.Products.Num()==1&&Near(ColdSteelFood::AgeDays(Migrated.Ingredients[0],Current),0.)
            &&Near(ColdSteelFood::AgeDays(Migrated.Products[0].Payload,Current),0.),TEXT("legacy queued and cooked food begins aging on first migration"));
    }
    Report(Building->FlushCampfirePersistence(),TEXT("isolated updated building checkpoint saved"));
    RunCampfireRecoveryAudit(World,Model,Building,Cell,Check);
}
