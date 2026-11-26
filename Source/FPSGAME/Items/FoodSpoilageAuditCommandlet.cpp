#include "FoodSpoilageAuditCommandlet.h"
#include "FPSConsumableAuditCommandlet.h"
#include "FoodSpoilage.h"
#include "FoodSpoilageClock.h"
#include "SharedFoodSpoilageAudit.h"
#include "../FPSGAMECharacter.h"
#include "../FPSWeatherManager.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Multiplayer/ColdSteelInventoryRequestTypes.h"
#include "../Multiplayer/ColdSteelProfileTransfer.h"
#include "../Survival/FPSSurvivalComponent.h"
#include "../UI/ColdSteelFoodPresentation.h"
#include "../UI/ColdSteelItemTooltipData.h"
#include "../UI/ColdSteelPickup.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/BoxComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerState.h"
#include "GameFramework/WorldSettings.h"
#include "HAL/FileManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonSerializer.h"

void RunCampfireFoodSpoilageAudit(UWorld*,UColdSteelStatusModel*,TFunctionRef<void(bool,const FString&)>);

namespace
{
bool FoodAuditSameItems(const TArray<FColdSteelItem>& A,const TArray<FColdSteelItem>& B)
{
    if(A.Num()!=B.Num())return false;
    for(int32 N=0;N<A.Num();++N)
        if(!FColdSteelItem::StaticStruct()->CompareScriptStruct(&A[N],&B[N],0))return false;
    return true;
}
bool FoodAuditSameAge(const FColdSteelItem& A,const FColdSteelItem& B)
{
    return A.FoodVersion==B.FoodVersion&&A.FoodAgeDays==B.FoodAgeDays
        &&A.FoodSampleDay==B.FoodSampleDay&&A.FoodClockId==B.FoodClockId;
}
int64 FoodAuditCount(const TArray<FColdSteelItem>& Items,const TCHAR* Definition)
{
    int64 Count=0;for(const auto& I:Items)if(I.Definition==Definition)Count+=I.Count;return Count;
}
bool FoodAuditValidProducts(const TArray<FColdSteelItem>& Items)
{
    TSet<FString> Ids;
    for(const auto& I:Items)
    {
        if(Ids.Contains(I.InstanceId)||I.InstanceId.IsEmpty())return false;Ids.Add(I.InstanceId);
        if(I.Definition==TEXT("spoiled_food")&&(I.Count<1||I.Count>10||I.StackMax!=10||I.Width!=1||I.Height!=1||I.bRotated))return false;
    }
    return true;
}
bool FoodAuditSetStackMaximum(FColdSteelItem& I,int32 Maximum)
{
    TSharedPtr<FJsonObject> Data;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),Data)||!Data)return false;
    Data->SetNumberField(TEXT("stack_max"),Maximum);Data->SetNumberField(TEXT("maxStack"),Maximum);
    I.StackMax=Maximum;I.Data.Reset();return FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));
}
}

int32 UFoodSpoilageAuditCommandlet::Main(const FString& Params)
{
    FString UserDir,ExistingProfile;
    FString Root=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("SourceAssets/FoodSpoilage20261015/TestRuns"));
    FString Saved=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir());
    FPaths::NormalizeDirectoryName(Root);FPaths::NormalizeDirectoryName(Saved);
    const bool HasUserDir=FParse::Value(FCommandLine::Get(),TEXT("UserDir="),UserDir);
    FString UserRoot=HasUserDir?FPaths::ConvertRelativePathToFull(UserDir):FString();FPaths::NormalizeDirectoryName(UserRoot);
    // Reject before initializing any profile subsystem: no caller-selected profile and no formal Saved directory.
    if(!HasUserDir||!UserRoot.StartsWith(Root+TEXT("/"))||!Saved.StartsWith(Root+TEXT("/"))
        ||FParse::Value(FCommandLine::Get(),TEXT("ColdSteelProfile="),ExistingProfile))
    {UE_LOG(LogTemp,Error,TEXT("FoodSpoilageAudit requires an isolated FoodSpoilage20261015/TestRuns UserDir and no supplied profile"));return 2;}
    const FString Original=FCommandLine::Get();
    const FString Profile=TEXT("FoodSpoilageAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(Original+TEXT(" -ColdSteelProfile=")+Profile));
    ON_SCOPE_EXIT {FCommandLine::Set(*Original);};
    TArray<TSharedPtr<FJsonValue>> Cases;int32 Failed=0;
    auto Check=[&](bool Pass,const FString& Name,const FString& Detail=FString())
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),Pass);Row->SetStringField(TEXT("detail"),Detail);
        Cases.Add(MakeShared<FJsonValueObject>(Row));if(!Pass)++Failed;
        UE_LOG(LogTemp,Display,TEXT("FOOD_SPOILAGE_AUDIT %s %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),*Name,*Detail);return Pass;
    };
    auto Near=[](double A,double B,double Tolerance=1.e-8){return FMath::Abs(A-B)<=Tolerance;};
    UGameInstance* GI=nullptr;UWorld* World=nullptr;UColdSteelStatusModel* Model=nullptr;
    auto Shutdown=[&]()
    {
        if(Model)Model->CurrentPawn.Reset();
        if(World)
        {
            World->GetWorldSettings()->SetPauserPlayerState(nullptr);
            TArray<AActor*> Begun;for(TActorIterator<AActor> It(World);It;++It)if(It->HasActorBegunPlay())Begun.Add(*It);
            for(auto* Actor:Begun)if(IsValid(Actor))
            {
                Actor->RouteEndPlay(EEndPlayReason::Quit);TInlineComponentArray<UActorComponent*> Components;Actor->GetComponents(Components);
                for(auto* Component:Components)if(Component->HasBegunPlay())Component->EndPlay(EEndPlayReason::Quit);
            }
        }
        if(GI)GI->Shutdown();
        if(World){GEngine->DestroyWorldContext(World);World->DestroyWorld(false);}
        if(GI)GI->RemoveFromRoot();GI=nullptr;World=nullptr;Model=nullptr;
    };
    ON_SCOPE_EXIT {Shutdown();};
    auto Initialize=[&]()
    {
        GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("FoodSpoilageAuditWorld"));
        World=GI->GetWorld();Model=GI->GetSubsystem<UColdSteelStatusModel>();
        if(World)World->GetWorldSettings()->MaxUndilatedFrameTime=1.f;
        return World&&Model&&Model->IsAudit()&&Model->ProfileSlot()==TEXT("ColdSteel_")+Profile;
    };
    auto WriteReport=[&]()
    {
        auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("cases"),Cases);
        Report->SetNumberField(TEXT("passed"),Cases.Num()-Failed);Report->SetNumberField(TEXT("failed"),Failed);
        Report->SetStringField(TEXT("profile"),TEXT("ColdSteel_")+Profile);Report->SetStringField(TEXT("saved_dir"),Saved);
        Report->SetStringField(TEXT("scope"),TEXT("isolated native game world; actual catalog, weather natural clock, inventory helpers, checked profile persistence and network serializer; no PIE or rendering"));
        TArray<TSharedPtr<FJsonValue>> NotRun;
        for(const TCHAR* Name:{TEXT("rendered card layout and pointer UI"),TEXT("live multiplayer RPC transport")})
            NotRun.Add(MakeShared<FJsonValueString>(Name));
        Report->SetArrayField(TEXT("not_run"),NotRun);
        FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
        IFileManager::Get().MakeDirectory(*Saved,true);
        return FFileHelper::SaveStringToFile(Json,*(Saved/TEXT("food-spoilage-runtime.json")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    };
    if(!Check(Initialize(),TEXT("isolated world and random audit profile initialized")))return WriteReport()?2:3;
    auto* Weather=World->SpawnActor<AFPSWeatherManager>();
    auto* Clock=World->GetSubsystem<UFoodSpoilageClock>();
    if(!Check(Weather&&Clock,TEXT("real weather authority and food clock subsystem available")))return WriteReport()?2:3;
    // Initialization may sample before the weather actor is present; allow the bounded resolver its normal next opportunity.
    World->Tick(LEVELTICK_TimeOnly,1.f);const auto InitialClock=Clock->Sample();
    Check(InitialClock.Id.IsValid(),TEXT("food clock has persistent profile domain"));
    auto Seed=Model->Snapshot();Seed.Items.Reset();Seed.ActiveProductionTool.Reset();Seed.ActiveWeaponSlot=6;
    Seed.Hotbar.Init(TEXT(""),4);Seed.HotbarDefinitions.Init(TEXT(""),4);for(auto& Binding:Seed.QuickBindings)Binding={};
    Seed.ForgeJob={};Seed.WoodworkingJob={};Seed.GunAssemblyJob={};Seed.Survival={};Seed.Survival.Hunger=10;
    Seed.Health=100;Seed.Mana=100;Seed.StaminaVersion=1;Seed.Stamina=37;Seed.StaminaRecoveryDelay=60;
    if(!Check(Model->CommitState(Seed)&&Model->Items().IsEmpty(),TEXT("empty isolated profile committed before automatic clock settlement"),Model->ResultMessage()))return WriteReport()?2:3;

    const TArray<TPair<FString,double>> Expected={
        {TEXT("raw_chicken_leg"),3},{TEXT("raw_lamb_ribs"),3},{TEXT("raw_sausage"),3},{TEXT("raw_large_lamb"),3},
        {TEXT("roasted_chicken_leg"),4},{TEXT("roasted_lamb_ribs"),4},{TEXT("roasted_sausage"),4},{TEXT("roasted_large_lamb"),4},
        {TEXT("bread"),8},{TEXT("baguette_bread"),8},
        {TEXT("raw_venison"),3},{TEXT("raw_boar_meat"),3},{TEXT("raw_fox_meat"),3},
        {TEXT("roasted_venison"),4},{TEXT("roasted_boar_meat"),4},{TEXT("roasted_fox_meat"),4}};
    const FFoodClockSample Start{FGuid::NewGuid(),100.};
    FString Reason;
    for(const auto& Pair:Expected)
    {
        auto Item=Model->CreateItem(Pair.Key);ColdSteelFood::Stamp(Item,Start);
        Check(!Item.Data.IsEmpty()&&Near(ColdSteelInventory::Number(Item,TEXT("spoilDays")),Pair.Value)
            &&Near(ColdSteelFood::LifetimeDays(Item),Pair.Value),TEXT("catalog lifetime ")+Pair.Key);
        auto Before=Start;Before.Day+=Pair.Value-1.e-6;auto At=Start;At.Day+=Pair.Value;auto After=At;After.Day+=1.e-6;
        Check(!ColdSteelFood::IsExpired(Item,Before)&&ColdSteelFood::IsExpired(Item,At)&&ColdSteelFood::IsExpired(Item,After),TEXT("exact expiry boundary ")+Pair.Key);
        auto Tampered=Item;TSharedPtr<FJsonObject> TamperedData;
        bool TamperedParsed=FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Tampered.Data),TamperedData)&&TamperedData.IsValid();
        if(TamperedParsed)
        {
            TamperedData->SetNumberField(TEXT("spoilDays"),9999.);Tampered.Data.Reset();
            TamperedParsed=FJsonSerializer::Serialize(TamperedData.ToSharedRef(),TJsonWriterFactory<>::Create(&Tampered.Data));
        }
        Check(TamperedParsed&&Near(ColdSteelFood::LifetimeDays(Tampered),Pair.Value)&&ColdSteelFood::IsExpired(Tampered,At),TEXT("authority catalog overrides instance lifetime edit ")+Pair.Key);
        TArray<FColdSteelItem> Items{Item};const int64 Yield=int64(Item.Width)*Item.Height*Item.Count;
        const bool Converted=ColdSteelFood::SettleGrid(Items,Model,At,Reason);
        Check(Converted&&Reason.IsEmpty()&&FoodAuditCount(Items,TEXT("spoiled_food"))==Yield
            &&FoodAuditCount(Items,*Pair.Key)==0&&FoodAuditValidProducts(Items),TEXT("actual footprint conversion ")+Pair.Key,Reason);
        const auto Once=Items;
        Check(!ColdSteelFood::SettleGrid(Items,Model,After,Reason)&&Reason.IsEmpty()&&FoodAuditSameItems(Once,Items),TEXT("repeated conversion is idempotent ")+Pair.Key);
    }
    TSharedPtr<FJsonObject> Catalog;FString CatalogText;int32 PerishableCount=0;bool ExactCatalog=true;
    if(FFileHelper::LoadFileToString(CatalogText,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/items.json"))))
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(CatalogText),Catalog);
    if(Catalog)for(const auto& Pair:Catalog->Values)
    {
        const auto Data=Pair.Value->AsObject();double Days=0.;
        if(!Data||!Data->TryGetNumberField(TEXT("spoilDays"),Days)||Days<=0.)continue;
        ++PerishableCount;ExactCatalog&=Expected.ContainsByPredicate([&](const auto& V){return V.Key==FString(*Pair.Key)&&Near(V.Value,Days);});
    }
    Check(Catalog&&ExactCatalog&&PerishableCount==Expected.Num(),TEXT("complete catalog matches all authored perishable food lifetimes"),
        FString::Printf(TEXT("expected=%d actual=%d"),Expected.Num(),PerishableCount));
    for(const TCHAR* Id:{TEXT("mineral_water"),TEXT("soda_can"),TEXT("hp_potion"),TEXT("hp_potion_medium"),TEXT("hp_potion_high"),TEXT("hp_potion_special"),TEXT("mp_potion"),TEXT("mp_potion_medium"),TEXT("mp_potion_high"),TEXT("mp_potion_special")})
    {
        const auto Item=Model->CreateItem(Id);
        Check(!Item.Data.IsEmpty()&&ColdSteelFood::LifetimeDays(Item)==0.,FString(TEXT("actual drink or potion excluded: "))+Id);
    }
    const auto Spoiled=Model->CreateItem(TEXT("spoiled_food"));
    Check(!Spoiled.Data.IsEmpty()&&Spoiled.Width==1&&Spoiled.Height==1&&Spoiled.StackMax==10
        &&ColdSteelInventory::Text(Spoiled,TEXT("name"))==TEXT("腐败食物")
        &&ColdSteelInventory::Text(Spoiled,TEXT("category"))==TEXT("material")&&ColdSteelFood::LifetimeDays(Spoiled)==0.,TEXT("spoiled food is nonperishable 1x1 material with stack maximum 10"));

    auto Expired=[&](const TCHAR* Id,int64 Count=1)
    {auto I=Model->CreateItem(Id,Count);ColdSteelFood::Stamp(I,Start,ColdSteelFood::LifetimeDays(I));return I;};
    {
        auto OriginalItem=Expired(TEXT("baguette_bread"));auto Rotated=OriginalItem;ColdSteelInventory::ApplyOrientation(Rotated,1);
        TArray<FColdSteelItem> A{OriginalItem},B{Rotated};
        const bool AOK=ColdSteelFood::SettleGrid(A,Model,Start,Reason),BOK=ColdSteelFood::SettleGrid(B,Model,Start,Reason);
        Check(Rotated.Width==3&&Rotated.Height==1&&AOK&&BOK&&FoodAuditCount(A,TEXT("spoiled_food"))==3&&FoodAuditCount(B,TEXT("spoiled_food"))==3,TEXT("rotating 1x3 bread preserves three-unit yield"));
    }
    {
        // Stress a future/migrated stack: 6 items x 4 cells = 24 units, using the real conversion helper.
        auto Meat=Expired(TEXT("raw_large_lamb"),6);TArray<FColdSteelItem> Items{Meat};
        const bool OK=ColdSteelFood::SettleGrid(Items,Model,Start,Reason);
        Check(OK&&Items.Num()==3&&FoodAuditCount(Items,TEXT("spoiled_food"))==24&&FoodAuditValidProducts(Items),TEXT("yield above ten splits into complete 10 10 4 stacks"),Reason);
        auto Oversize=Expired(TEXT("raw_lamb_ribs"),11);Oversize.Cell=10;Items={Oversize,Expired(TEXT("raw_large_lamb"))};
        Check(ColdSteelFood::SettleGrid(Items,Model,Start,Reason)&&FoodAuditCount(Items,TEXT("spoiled_food"))==15&&FoodAuditValidProducts(Items),
            TEXT("simultaneous expired stacks share released capacity without losing yield"),Reason);
        Items={Oversize};
        for(int32 Cell=0;Cell<72;++Cell)if(Cell!=10)
        {auto Block=Model->CreateItem(TEXT("spoiled_food"),10);Block.Cell=Cell;Items.Add(Block);}
        const auto Before=Items;
        Check(!ColdSteelFood::SettleGrid(Items,Model,Start,Reason)&&!Reason.IsEmpty()&&FoodAuditSameItems(Before,Items)
            &&ColdSteelFood::IsExpired(Items[0],Start),TEXT("unplaceable legacy stack is retained atomically and remains expired"),Reason);
    }
    for(const int64 ExistingCount:{9ll,10ll})
    {
        auto Meat=Expired(TEXT("raw_large_lamb"));auto Existing=Model->CreateItem(TEXT("spoiled_food"),ExistingCount);Existing.Cell=10;
        TArray<FColdSteelItem> Items{Meat,Existing};const bool OK=ColdSteelFood::SettleGrid(Items,Model,Start,Reason);
        const auto* OldStack=Items.FindByPredicate([&](const auto& I){return I.InstanceId==Existing.InstanceId;});
        Check(OK&&OldStack&&OldStack->Count==10&&FoodAuditCount(Items,TEXT("spoiled_food"))==ExistingCount+4&&FoodAuditValidProducts(Items),FString::Printf(TEXT("existing %lld of 10 stack merges without loss"),ExistingCount),Reason);
    }
    {
        auto Meat=Expired(TEXT("raw_large_lamb"));TArray<FColdSteelItem> Items{Meat};
        for(int32 Cell=0;Cell<72;++Cell)if(Cell!=0&&Cell!=1&&Cell!=18&&Cell!=19)
        {auto Block=Model->CreateItem(TEXT("spoiled_food"),10);Block.Cell=Cell;Items.Add(Block);}
        const auto Before=Items;const bool OK=ColdSteelFood::SettleGrid(Items,Model,Start,Reason);
        bool BlockersIntact=true;for(int32 N=1;N<Before.Num();++N)
        {const auto* Found=Items.FindByPredicate([&](const auto& I){return I.InstanceId==Before[N].InstanceId;});BlockersIntact&=Found&&Found->Count==10&&Found->Cell==Before[N].Cell;}
        Check(OK&&BlockersIntact&&FoodAuditCount(Items,TEXT("spoiled_food"))==684&&FoodAuditValidProducts(Items),TEXT("full 72-cell backpack reuses released 2x2 footprint without disturbing other stacks"),Reason);
    }
    {
        auto Bag=Model->CreateItem(TEXT("ue_portable_backpack"));Bag.Place=1;Bag.Cell=14;
        auto Meat=Expired(TEXT("raw_large_lamb"),6);Meat.Place=ColdSteelInventory::ColdSteelCompartment::Place;Meat.Cell=4;
        TArray<FColdSteelItem> Items{Bag,Meat};
        for(int32 Cell=0;Cell<36;++Cell)if(Cell!=4&&Cell!=5&&Cell!=10&&Cell!=11)
        {auto Block=Model->CreateItem(TEXT("spoiled_food"),10);Block.Place=Meat.Place;Block.Cell=Cell;Items.Add(Block);}
        const bool OK=ColdSteelFood::SettleGrid(Items,Model,Start,Reason);bool CellsInBounds=true;
        for(const auto& I:Items)if(I.Place==Meat.Place)CellsInBounds&=I.Cell>=0&&I.Cell<36;
        Check(OK&&CellsInBounds&&FoodAuditCount(Items,TEXT("spoiled_food"))==344&&FoodAuditValidProducts(Items)
            &&Items.ContainsByPredicate([&](const auto& I){return I.Place==Meat.Place&&I.Cell==10&&I.Count==4;}),TEXT("full six-column compartment uses its real row stride for multi-stack yield"),Reason);
    }
    {
        auto Meat=Expired(TEXT("raw_large_lamb"),6);Meat.Place=2;Meat.Map=TEXT("FoodAuditMap");Meat.Position=FVector(23,45,67);
        Meat.WorldRotation=FRotator(10,20,30);Meat.HarvestWorldId=FGuid::NewGuid();TArray<FColdSteelItem> Items{Meat};
        const bool OK=ColdSteelFood::SettleLoose(Items,Model,Start,Reason);bool Anchors=true;
        for(const auto& I:Items)Anchors&=I.Place==2&&I.Map==Meat.Map&&I.Position==Meat.Position&&I.WorldRotation==Meat.WorldRotation&&I.HarvestWorldId==Meat.HarvestWorldId;
        Check(OK&&Anchors&&FoodAuditCount(Items,TEXT("spoiled_food"))==24&&Items.Num()==3&&FoodAuditValidProducts(Items),TEXT("ground conversion keeps location and world ownership for every output stack"),Reason);
        const auto Once=Items;Check(!ColdSteelFood::SettleLoose(Items,Model,Start,Reason)&&FoodAuditSameItems(Once,Items),TEXT("loose conversion cannot duplicate on retry"));
        Meat.Place=4;Meat.Container=TEXT("FoodAuditCrate");Items={Meat};
        Check(ColdSteelFood::SettleLoose(Items,Model,Start,Reason)&&Items.Num()==3
            &&!Items.ContainsByPredicate([&](const auto& I){return I.Place!=4||I.Container!=Meat.Container;}),TEXT("loose container outputs retain container ownership"),Reason);
        auto A=Expired(TEXT("raw_large_lamb"));A.Place=4;A.Container=TEXT("BoxA");
        auto Other=Model->CreateItem(TEXT("spoiled_food"),9);Other.Place=4;Other.Container=TEXT("BoxB");Other.Cell=0;
        Items={A,Other};const bool Converted=ColdSteelFood::SettleGrid(Items,Model,Start,Reason);
        const auto* OtherAfter=Items.FindByPredicate([&](const auto& I){return I.InstanceId==Other.InstanceId;});
        Check(Converted&&OtherAfter&&OtherAfter->Count==9&&Items.ContainsByPredicate([](const auto& I){return I.Container==TEXT("BoxA")&&I.Count==4;}),TEXT("conversion never merges into a different container"),Reason);
        auto View=A;View.Container=TEXT("NetView.FoodAudit");Items={View};const auto Before=Items;
        Check(!ColdSteelFood::SettleGrid(Items,Model,Start,Reason)&&FoodAuditSameItems(Before,Items),TEXT("replicated container view is not independently converted"));
    }
    {
        auto Legacy=Model->CreateItem(TEXT("raw_sausage"));Legacy.FoodVersion=0;Legacy.FoodClockId={};Legacy.FoodAgeDays=0;Legacy.FoodSampleDay=0;
        Check(ColdSteelFood::Rebase(Legacy,Start)&&Near(ColdSteelFood::AgeDays(Legacy,Start),0.)&&Legacy.FoodVersion==1,TEXT("legacy instance begins its lifetime on first migration"));
        auto Later=Start;Later.Day+=1.;Check(!ColdSteelFood::Rebase(Legacy,Later)&&Near(ColdSteelFood::AgeDays(Legacy,Later),1.),TEXT("repeat migration cannot reset an existing lifetime"));
        auto P=Seed;auto I=Model->CreateItem(TEXT("bread"));ColdSteelFood::Stamp(I,Start,.75);P.Items={I};P.FoodVersion=1;P.FoodClockId=Start.Id;P.FoodClockDay=Start.Day+1.25;
        const FFoodClockSample NewDomain{FGuid::NewGuid(),900.};
        Check(ColdSteelFood::RebaseProfile(P,NewDomain)&&Near(ColdSteelFood::AgeDays(P.Items[0],NewDomain),2.)
            &&P.Items[0].FoodClockId==NewDomain.Id,TEXT("cross-world profile rebase preserves cumulative saved age without adding offline time"));
        const auto Once=P.Items;Check(!ColdSteelFood::RebaseProfile(P,NewDomain)&&FoodAuditSameItems(Once,P.Items),TEXT("cross-world migration is idempotent"));
    }

    {
        auto P=Seed;auto Bread=Model->CreateItem(TEXT("bread"));auto Meat=Model->CreateItem(TEXT("raw_sausage"));
        ColdSteelFood::Stamp(Bread,Start,.75);ColdSteelFood::Stamp(Meat,Start,.75);P.Items={Bread,Meat};
        P.FoodVersion=1;P.FoodClockId=Start.Id;P.FoodClockDay=Start.Day+2.5;
        const FFoodClockSample Checkpoint{P.FoodClockId,P.FoodClockDay};
        const double SavedBreadAge=ColdSteelFood::AgeDays(P.Items[0],Checkpoint),SavedMeatAge=ColdSteelFood::AgeDays(P.Items[1],Checkpoint);
        const FFoodClockSample EarlierNow{Start.Id,Start.Day+1.};
        Check(ColdSteelFood::RebaseProfile(P,EarlierNow)&&P.FoodClockId==EarlierNow.Id&&P.FoodClockDay==EarlierNow.Day
            &&Near(SavedBreadAge,3.25)&&Near(ColdSteelFood::AgeDays(P.Items[0],EarlierNow),SavedBreadAge)
            &&Near(ColdSteelFood::AgeDays(P.Items[1],EarlierNow),SavedMeatAge),TEXT("same-domain future checkpoint preserves saved age when current clock is earlier"));
        Check(ColdSteelFood::IsExpired(P.Items[1],EarlierNow)&&!ColdSteelFood::IsExpired(P.Items[0],EarlierNow),TEXT("same-domain clock rollback cannot revive already expired food"));
        const auto Once=P.Items;
        Check(!ColdSteelFood::RebaseProfile(P,EarlierNow)&&FoodAuditSameItems(Once,P.Items),TEXT("same-domain rollback rebase is idempotent"));
        auto Later=EarlierNow;Later.Day+=.5;
        Check(ColdSteelFood::RebaseProfile(P,Later)&&Near(ColdSteelFood::AgeDays(P.Items[0],Later),SavedBreadAge+.5)
            &&Near(ColdSteelFood::AgeDays(P.Items[1],Later),SavedMeatAge+.5)&&ColdSteelFood::IsExpired(P.Items[1],Later),TEXT("food continues aging from preserved age after same-domain rollback"));
    }

    {
        // Exercise the same helper used by the owner's OnRep before its first
        // upload. The old profile checkpoint must survive a new host clock.
        auto P=Seed;auto Bread=Model->CreateItem(TEXT("bread"));
        ColdSteelFood::Stamp(Bread,Start,.75);P.Items={Bread};
        P.FoodVersion=1;P.FoodClockId=Start.Id;P.FoodClockDay=Start.Day+1.25;
        auto View=Bread;View.InstanceId+=TEXT("_view");View.Container=TEXT("NetView.ClockAudit");P.Items.Add(View);
        const auto Revision=P.CampfireInventoryRevision;
        const FFoodClockSample NewHost{FGuid::NewGuid(),900.};
        ColdSteelFood::ObserveReplicatedClock(P,NewHost);
        Check(P.FoodClockId==NewHost.Id&&Near(P.FoodClockDay,NewHost.Day)
            &&Near(ColdSteelFood::AgeDays(P.Items[0],NewHost),2.)&&FoodAuditSameAge(P.Items[1],View)
            &&P.CampfireInventoryRevision==Revision,
            TEXT("owner clock before first upload preserves cross-host saved age without settling inventory or changing shared views"));
        const auto RebasedItems=P.Items;
        ColdSteelFood::ObserveReplicatedClock(P,{NewHost.Id,NewHost.Day+.5});
        ColdSteelFood::ObserveReplicatedClock(P,{NewHost.Id,NewHost.Day-.5});
        Check(Near(P.FoodClockDay,NewHost.Day+.5)&&FoodAuditSameItems(P.Items,RebasedItems)
            &&Near(ColdSteelFood::AgeDays(P.Items[0],{P.FoodClockId,P.FoodClockDay}),2.5),
            TEXT("same-domain late owner clock never rewinds time or rewrites batch timestamps"));
        auto Upload=P;ColdSteelFood::RebaseProfile(Upload,{NewHost.Id,NewHost.Day+.75});
        Check(Near(ColdSteelFood::AgeDays(Upload.Items[0],{Upload.FoodClockId,Upload.FoodClockDay}),2.75),
            TEXT("first server rebase after early owner clock retains saved age and new-domain elapsed time"));
        ColdSteelFood::ObserveReplicatedClock(P,{});
        ColdSteelFood::ObserveReplicatedClock(P,{NewHost.Id,-1.});
        Check(Near(P.FoodClockDay,NewHost.Day+.5)&&FoodAuditSameItems(P.Items,RebasedItems),
            TEXT("invalid owner clock samples leave food checkpoint and batches unchanged"));
    }

    // Only local arrays above contain food. World ticks below may run the real
    // 1 Hz settlement subsystem, so its persisted inventory must remain empty.
    if(!Check(Model->Items().IsEmpty(),TEXT("natural-clock fixtures contain no persisted food for automatic settlement")))return WriteReport()?2:3;
    for(const float DaySeconds:{2160.f,1080.f,4320.f,60.f})
    {
        Weather->RealSecondsPerGameDay=DaySeconds;Weather->WeatherClockSeconds=0;Weather->NormalizedDayTime=0;
        const auto Before=Clock->Sample();const double NaturalBefore=Weather->GetNaturalDayProgress();
        for(int32 N=0;N<240;++N)Weather->AdvanceNaturalClock(.25f);
        const auto After=Clock->Sample();
        Check(Near(After.Day-Before.Day,60./DaySeconds,1.e-6)&&Near(After.Day-Before.Day,Weather->GetNaturalDayProgress()-NaturalBefore),
            FString::Printf(TEXT("food samples actual natural clock at %.0fs per game day"),DaySeconds));
    }
    Weather->RealSecondsPerGameDay=2160.f;
    for(const float Dilation:{.5f,1.f,2.f})
    {
        UGameplayStatics::SetGlobalTimeDilation(World,Dilation);const auto Before=Clock->Sample();double Effective=0.;
        for(int32 N=0;N<8;++N){World->Tick(LEVELTICK_TimeOnly,.25f);const float Delta=World->GetDeltaSeconds();Effective+=Delta;Weather->AdvanceNaturalClock(Delta);}
        Check(Near(Clock->Sample().Day-Before.Day,Effective/2160.,1.e-6)&&Near(Effective,2.*Dilation,1.e-5),
            FString::Printf(TEXT("food clock follows actual world dilation %.1f"),Dilation));
    }
    UGameplayStatics::SetGlobalTimeDilation(World,1.f);
    {
        const auto Before=Clock->Sample();Weather->AdvanceGameTime(96.f);
        Check(Near(Clock->Sample().Day,Before.Day),TEXT("manual four-day calendar jump does not age food"));
        for(int32 N=0;N<12;++N){World->Tick(LEVELTICK_TimeOnly,.25f);Clock->Sample();}
        Check(Near(Clock->Sample().Day,Before.Day),TEXT("elapsed world time without natural calendar progress does not age food"));
        auto* Pauser=World->SpawnActor<APlayerState>();World->GetWorldSettings()->SetPauserPlayerState(Pauser);
        const bool Paused=World->IsPaused();Clock->Tick(3600.f);
        Check(Paused&&!Clock->IsTickableWhenPaused()&&Near(Clock->Sample().Day,Before.Day),TEXT("paused world ignores food-clock settlement callback and has no natural aging"));
        World->GetWorldSettings()->SetPauserPlayerState(nullptr);Pauser->Destroy();
    }

    if(!Check(!World->IsPaused(),TEXT("pause fixture released before inventory transaction and save-failure fixtures")))return WriteReport()?2:3;
    // The remaining transaction fixtures do not tick the world or advance the
    // weather: automatic settlement cannot consume AuditFailNextSave first.
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<APlayerController>();
    auto* PlayerState=World->SpawnActor<APlayerState>();PC->SetPlayerState(PlayerState);PC->SetAsLocalPlayerController();PC->Possess(Pawn);
    Pawn->DispatchBeginPlay();Model->CurrentPawn=Pawn;
    auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();if(Health)Health->Health=Health->MaxHealth;
    Check(Pawn->HasActorBegunPlay()&&Health&&!Health->IsDead(),TEXT("alive authoritative pawn initialized for actual inventory transactions"));
    auto Reset=[&]()
    {
        auto P=Model->Snapshot();P.Items.Reset();P.ActiveProductionTool.Reset();P.ActiveWeaponSlot=6;
        P.Hotbar.Init(TEXT(""),4);P.HotbarDefinitions.Init(TEXT(""),4);for(auto& B:P.QuickBindings)B={};
        P.Survival={};P.Survival.Hunger=10;if(Health){Health->Health=Health->MaxHealth;P.Health=Health->Health;}
        Model->EndStorageSession();return P;
    };
    {
        auto P=Reset();auto Meat=Model->CreateItem(TEXT("raw_sausage"),4);const bool StackFixture=FoodAuditSetStackMaximum(Meat,10);
        ColdSteelFood::Stamp(Meat,Clock->Sample(),.5);const auto OriginalAge=Meat;P.Items.Add(Meat);
        const bool Seeded=StackFixture&&Model->CommitState(P);Check(Seeded,TEXT("future stack fixture committed for real split path"),Model->ResultMessage());
        const bool Split=Seeded&&Model->Split(Meat.InstanceId,1);const auto SplitState=Model->Snapshot();bool SameAge=true;
        for(const auto& I:SplitState.Items)SameAge&=FoodAuditSameAge(I,OriginalAge);
        Check(Split&&SplitState.Items.Num()==2&&FoodAuditCount(SplitState.Items,TEXT("raw_sausage"))==4&&SameAge,TEXT("actual split retains exact age metadata on both halves"),Model->ResultMessage());
        if(SplitState.Items.Num()==2)
        {
            Check(ColdSteelFood::Compatible(SplitState.Items[0],SplitState.Items[1])&&ColdSteelInventory::Compatible(SplitState.Items[0],SplitState.Items[1]),TEXT("halves of one batch remain stack compatible"));
            auto New=SplitState.Items[0];ColdSteelFood::Stamp(New,Clock->Sample());
            Check(!ColdSteelFood::Compatible(SplitState.Items[0],New)&&!ColdSteelInventory::Compatible(SplitState.Items[0],New),TEXT("different freshness cannot merge and refresh old meat"));
        }
        Model->BeginStorageSession(TEXT("FoodAuditCrate"),1,TEXT("隔离食物容器"));
        const bool Stored=Model->TransferWarehouse(Meat.InstanceId,4,7);const auto* StoredItem=Model->FindItem(Meat.InstanceId);
        Check(Stored&&StoredItem&&StoredItem->Container==TEXT("FoodAuditCrate")&&FoodAuditSameAge(*StoredItem,OriginalAge),TEXT("actual container transfer retains lifetime"),Model->ResultMessage());
        const bool Returned=Model->TransferWarehouse(Meat.InstanceId,0,20);const auto* ReturnedItem=Model->FindItem(Meat.InstanceId);
        Check(Returned&&ReturnedItem&&ReturnedItem->Place==0&&FoodAuditSameAge(*ReturnedItem,OriginalAge),TEXT("actual transfer back to bag retains lifetime"),Model->ResultMessage());
        Model->EndStorageSession();
        auto* Floor=World->SpawnActor<AActor>();auto* Collision=NewObject<UBoxComponent>(Floor);Floor->SetRootComponent(Collision);
        Collision->SetBoxExtent(FVector(500,500,10));Collision->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Collision->SetCollisionResponseToAllChannels(ECR_Block);Collision->RegisterComponent();Floor->SetActorLocation(FVector(0,0,-100));
        const bool Dropped=Model->Drop(Meat.InstanceId);const auto* DroppedItem=Model->FindItem(Meat.InstanceId);
        Check(Dropped&&DroppedItem&&DroppedItem->Place==2&&FoodAuditSameAge(*DroppedItem,OriginalAge),TEXT("actual ground drop retains lifetime"),Model->ResultMessage());
        AColdSteelPickup* Pickup=nullptr;
        for(TActorIterator<AColdSteelPickup> It(World);It;++It)if(It->ItemId==Meat.InstanceId){Pickup=*It;break;}
        // The actual pickup path requires focused interaction. This headless world
        // does not tick a player camera, so explicitly aim and update its view.
        // SpawnActor alone has not run the controller's normal initialization
        // in this world; use the engine's normal camera factory before aiming.
        if(!PC->PlayerCameraManager)PC->SpawnPlayerCameraManager();
        PC->bShowMouseCursor=false;PC->SetViewTarget(Pawn);
        if(Pickup&&PC->PlayerCameraManager)
        {
            // There is no ULocalPlayer in this commandlet. The default
            // client-camera mode otherwise skips DoUpdateCamera entirely.
            PC->PlayerCameraManager->bUseClientSideCameraUpdates=false;
            PC->PlayerCameraManager->UpdateCamera(0.f);
            FVector Eye;FRotator View;ColdSteelWorldInteraction::GetReachViewPoint(PC,Eye,View);
            const FRotator Aim=(Pickup->GetActorLocation()-Eye).Rotation();
            PC->SetControlRotation(Aim);
            if(auto* Camera=Pawn->FindComponentByClass<UCameraComponent>())Camera->SetWorldRotation(Aim);
            PC->PlayerCameraManager->UpdateCamera(0.f);
        }
        FVector PickupEye;FRotator PickupView;ColdSteelWorldInteraction::GetReachViewPoint(PC,PickupEye,PickupView);
        const auto* FocusedPickup=ColdSteelWorldInteraction::TraceTarget(PC);
        Check(Pickup&&Pickup->CanInteract(Pawn)&&ColdSteelWorldInteraction::TraceTarget(PC)==Pickup,
            TEXT("actual ground pickup fixture aims at the spawned item within reach"),
            FString::Printf(TEXT("camera=%s cache_time=%.3f eye=%s view=%s target=%s focused=%s target_location=%s"),
                *GetNameSafe(PC->PlayerCameraManager),PC->PlayerCameraManager?PC->PlayerCameraManager->GetCameraCacheTime():-1.f,
                *PickupEye.ToString(),*PickupView.ToString(),*GetNameSafe(Pickup),*GetNameSafe(FocusedPickup),
                Pickup?*Pickup->GetActorLocation().ToString():TEXT("missing")));
        const bool Picked=Dropped&&Model->Pickup(Meat.InstanceId);bool PickedAge=true;
        for(const auto& I:Model->Items())if(I.Definition==TEXT("raw_sausage"))PickedAge&=I.Place==0&&FoodAuditSameAge(I,OriginalAge);
        Check(Picked&&PickedAge&&FoodAuditCount(Model->Items(),TEXT("raw_sausage"))==4,TEXT("actual ground pickup preserves age and quantity"),
            FString::Printf(TEXT("picked=%d age_and_place=%d count=%lld message=%s"),Picked,PickedAge,FoodAuditCount(Model->Items(),TEXT("raw_sausage")),*Model->ResultMessage()));
        Floor->Destroy();
    }
    {
        auto P=Reset();auto Meat=Model->CreateItem(TEXT("raw_large_lamb"));ColdSteelFood::Stamp(Meat,Clock->Sample(),3.);P.Items.Add(Meat);
        Check(Model->CommitState(P),TEXT("expired item fixture persisted before failure injection"),Model->ResultMessage());
        const auto Before=Model->Snapshot();Model->AuditFailNextSave=true;
        Check(!Model->SettleFoodSpoilage(true)&&FoodAuditSameItems(Before.Items,Model->Items())&&Model->FindItem(Meat.InstanceId),TEXT("failed durable conversion retains original expired item and no output"),Model->ResultMessage());
        auto* SlotA=Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromSlot(Model->ProfileSlot()+TEXT("_A"),0));
        auto* SlotB=Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromSlot(Model->ProfileSlot()+TEXT("_B"),0));
        const auto* Latest=SlotA&&(!SlotB||SlotA->Profile.Generation>=SlotB->Profile.Generation)?SlotA:SlotB;
        Check(Latest&&Latest->Profile.Generation==Before.Generation&&FoodAuditSameItems(Before.Items,Latest->Profile.Items),TEXT("failed conversion leaves latest durable slot byte-equivalent at item level"));
        Check(Model->SettleFoodSpoilage(true)&&!Model->FindItem(Meat.InstanceId)&&FoodAuditCount(Model->Items(),TEXT("spoiled_food"))==4,TEXT("retry commits exactly four spoiled portions"),Model->ResultMessage());
        const auto Once=Model->Snapshot();
        Check(Model->SettleFoodSpoilage(true)&&FoodAuditSameItems(Once.Items,Model->Items())&&Model->Snapshot().Generation==Once.Generation,TEXT("repeat runtime settlement cannot duplicate or rewrite unchanged inventory"));
        Check(Model->ReloadProfile()&&FoodAuditCount(Model->Items(),TEXT("spoiled_food"))==4,TEXT("checked profile save and reload preserve converted output"),Model->ResultMessage());
    }
    {
        auto P=Reset();auto Meal=Model->CreateItem(TEXT("roasted_chicken_leg"));ColdSteelFood::Stamp(Meal,Clock->Sample(),4.);P.Items.Add(Meal);
        Check(Model->CommitState(P),TEXT("expired cooked meal persisted for contact validation"),Model->ResultMessage());const auto Before=Model->Snapshot();
        Model->AuditFailNextSave=true;
        Check(!Model->UseConsumableAtContact(Meal.InstanceId,true)&&Model->FindItem(Meal.InstanceId)&&Near(Model->Snapshot().Survival.Hunger,Before.Survival.Hunger),TEXT("expired contact is denied even if conversion save fails; no healing and no loss"),Model->ResultMessage());
        Check(!Model->UseConsumableAtContact(Meal.InstanceId,true)&&!Model->FindItem(Meal.InstanceId)
            &&FoodAuditCount(Model->Items(),TEXT("spoiled_food"))==2&&Near(Model->Snapshot().Survival.Hunger,Before.Survival.Hunger),TEXT("expired contact converts once without applying food effects"),Model->ResultMessage());
        const auto RottenState=Model->Snapshot();const auto* Rotten=RottenState.Items.FindByPredicate([](const auto& I){return I.Definition==TEXT("spoiled_food");});
        Check(Rotten&&!Model->UseConsumableAtContact(Rotten->InstanceId,true)&&FoodAuditCount(Model->Items(),TEXT("spoiled_food"))==2,TEXT("spoiled food cannot be eaten or consumed"));
    }
    {
        auto Item=Model->CreateItem(TEXT("bread"));ColdSteelFood::Stamp(Item,Clock->Sample(),4.);
        auto Tip=BuildColdSteelItemTooltip(Item,Model,nullptr);const FColdSteelTooltipRow* Remaining=nullptr;const FColdSteelTooltipRow* Progress=nullptr;
        if(!Tip.Cards.IsEmpty())for(const auto& R:Tip.Cards.Last().Rows)
        {if(R.Label==TEXT("腐败倒计时"))Remaining=&R;if(R.Label==TEXT("腐败进度"))Progress=&R;}
        Check(Near(ColdSteelFoodUI::Progress(4.,8.),.5)&&ColdSteelFoodUI::Progress(-1.,8.)==1.f&&ColdSteelFoodUI::Progress(9.,8.)==0.f,TEXT("card progress clamps and represents consumed lifetime"));
        Check(ColdSteelFoodUI::Color(.499f)==ColdSteelUI::Success&&ColdSteelFoodUI::Color(.5f)==ColdSteelUI::Warning
            &&ColdSteelFoodUI::Color(.799f)==ColdSteelUI::Warning&&ColdSteelFoodUI::Color(.8f)==ColdSteelUI::Danger,
            TEXT("shared food bar colors switch at half and eighty percent lifetime"));
        Check(!Remaining&&!Progress&&Near(Tip.FoodProgress,.5)&&Tip.FoodLifetimeDays==8.,TEXT("food tooltip supplies bar progress without countdown or percentage rows"));
        const int32 CardCount=Tip.Cards.Num(),RowCount=Tip.Cards.IsEmpty()?0:Tip.Cards.Last().Rows.Num();ColdSteelFood::Stamp(Item,Clock->Sample(),8.);
        RefreshColdSteelFoodTooltip(Item,Model,Tip);
        Check(Near(Tip.FoodProgress,1.)&&Tip.Cards.Num()==CardCount&&!Tip.Cards.IsEmpty()&&Tip.Cards.Last().Rows.Num()==RowCount,TEXT("tooltip updates the bar value without changing structure"));
    }

    {
        const auto Sample=Clock->Sample();auto* Reply=NewObject<UColdSteelInventoryReply>();
        Reply->Sequence=17;Reply->Revision=42;Reply->bSuccess=true;Reply->FoodClockId=Sample.Id;Reply->FoodClockDay=Sample.Day;
        auto Fresh=Model->CreateItem(TEXT("bread"));auto Aged=Model->CreateItem(TEXT("roasted_large_lamb"));auto ExpiredSample=Model->CreateItem(TEXT("raw_sausage"));
        ColdSteelFood::Stamp(Fresh,Sample);ColdSteelFood::Stamp(Aged,Sample,2.125);ColdSteelFood::Stamp(ExpiredSample,Sample,3.5);
        Fresh.Cell=0;Aged.Cell=3;ExpiredSample.Cell=6;Reply->Changed={Fresh,Aged,ExpiredSample};
        TArray<uint8> ReplyBlob;auto* Received=NewObject<UColdSteelInventoryReply>();
        const bool Encoded=ColdSteelProfileTransfer::SaveToBlob(Reply,ReplyBlob);
        const bool Decoded=Encoded&&ColdSteelProfileTransfer::BlobToSaveObject(ReplyBlob,Received);
        Check(Decoded&&!ReplyBlob.IsEmpty()&&Received->Sequence==Reply->Sequence&&Received->Revision==Reply->Revision&&Received->bSuccess
            &&Received->FoodClockId==Sample.Id&&Received->FoodClockDay==Sample.Day,TEXT("actual compressed inventory reply preserves owner food-clock checkpoint"));
        Check(Decoded&&Received->Changed.Num()==3&&FoodAuditSameItems(Reply->Changed,Received->Changed)
            &&FoodAuditSameAge(Fresh,Received->Changed[0])&&FoodAuditSameAge(Aged,Received->Changed[1])&&FoodAuditSameAge(ExpiredSample,Received->Changed[2]),
            TEXT("actual compressed inventory reply Changed preserves every food version age sample and domain field"));
        Check(Decoded&&Received->Changed.Num()==3&&Near(ColdSteelFood::AgeDays(Received->Changed[0],Sample),0.)
            &&Near(ColdSteelFood::AgeDays(Received->Changed[1],Sample),2.125)&&ColdSteelFood::IsExpired(Received->Changed[2],Sample),
            TEXT("inventory reply roundtrip retains fresh aged and expired behavior"));
    }

    RunCampfireFoodSpoilageAudit(World,Model,[&](bool Pass,const FString& Name){Check(Pass,Name);});
    RunSharedFoodSpoilageAudit(World,Model,[&](bool Pass,const FString& Name,const FString& Detail){Check(Pass,Name,Detail);});
    UFPSConsumableAuditCommandlet::RunAuthorityFoodAudit(World,Model,
        [&](bool Pass,const FString& Name,const FString& Detail){Check(Pass,Name,Detail);});
    UFPSConsumableAuditCommandlet::RunGenericMeleeAudit(World,Model,
        [&](bool Pass,const FString& Name,const FString& Detail){Check(Pass,Name,Detail);});

    // Keep a perishable in the real profile, serialize the actual compressed transfer, then restart the whole isolated world.
    auto RestartProfile=Reset();auto Kept=Model->CreateItem(TEXT("roasted_large_lamb"));ColdSteelFood::Stamp(Kept,Clock->Sample(),1.25);RestartProfile.Items.Add(Kept);
    Check(Model->CommitState(RestartProfile),TEXT("restart fixture written through checked profile transaction"),Model->ResultMessage());
    const auto SavedProfile=Model->Snapshot();const auto* KeptItem=Model->FindItem(Kept.InstanceId);
    const double SavedAge=KeptItem?ColdSteelFood::AgeDays(*KeptItem,Clock->Sample()):-1.;
    auto* Packet=NewObject<UColdSteelProfileSave>();Packet->Profile=SavedProfile;TArray<uint8> Blob;
    const bool Encoded=ColdSteelProfileTransfer::SaveToBlob(Packet,Blob);auto* Decoded=Encoded?ColdSteelProfileTransfer::BlobToSave(Blob):nullptr;
    Check(Decoded&&FoodAuditSameItems(SavedProfile.Items,Decoded->Profile.Items)&&Decoded->Profile.FoodClockId==SavedProfile.FoodClockId
        &&Decoded->Profile.FoodClockDay==SavedProfile.FoodClockDay,TEXT("actual compressed multiplayer profile serializer preserves food metadata"));
    Shutdown();const bool Restarted=Initialize();Check(Restarted,TEXT("isolated game instance restarts using the same random profile"));
    if(Restarted)
    {
        auto* RestartClock=World->GetSubsystem<UFoodSpoilageClock>();const auto* Restored=Model->FindItem(Kept.InstanceId);
        const auto Sample=RestartClock?RestartClock->Sample():FFoodClockSample{};
        Check(RestartClock&&Restored&&Sample.Id.IsValid()&&Near(ColdSteelFood::AgeDays(*Restored,Sample),SavedAge)
            &&Near(Sample.Day,SavedProfile.FoodClockDay),TEXT("restart without weather progress preserves saved age and does not charge offline time"));
    }
    const bool Wrote=WriteReport();
    UE_LOG(LogTemp,Display,TEXT("FOOD_SPOILAGE_AUDIT_RESULT passed=%d failed=%d receipt=%s"),Cases.Num()-Failed,Failed,Wrote?TEXT("saved"):TEXT("failed"));
    return !Wrote?3:Failed?1:0;
}
