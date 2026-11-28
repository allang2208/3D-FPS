#if WITH_DEV_AUTOMATION_TESTS
#include "Components/BoxComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Misc/AutomationTest.h"
#include "UObject/UnrealType.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FVillageSiegePreviewTest,"FPSGAME.Village.Siege.PreviewAndReload",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)

bool FVillageSiegePreviewTest::RunTest(const FString&)
{
    UWorld::InitializationValues Settings;
    Settings.AllowAudioPlayback(false).RequiresHitProxies(false).CreatePhysicsScene(true)
        .CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if(!TestNotNull(TEXT("isolated query world"),World))return false;
    auto* Engine=World->SpawnActor<AVillageSiegeEngine>();
    Engine->bStone=true;
    const auto Box=[World](FVector Center,FVector Extent)
    {
        auto* Owner=World->SpawnActor<AActor>();
        auto* Shape=NewObject<UBoxComponent>(Owner);
        Owner->SetRootComponent(Shape);
        Shape->InitBoxExtent(Extent);
        Shape->SetCollisionProfileName(TEXT("BlockAll"));
        Shape->SetWorldLocation(Center);
        Shape->RegisterComponent();
        return Shape;
    };
    auto* Floor=Box(FVector(0,0,-50),FVector(11000,10000,50));
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SiegeGroundContactTest),false,Engine);
    TObjectPtr<ULineBatchComponent> Preview;
    TArray<FBatchedLine> Ring;
    auto CheckArc=[&](const TCHAR* Case,const FVillageSiegeSight& S)
    {
        if(!TestTrue(FString(Case)+TEXT(" predicts a first contact"),S.HasImpact && S.Arc.Num()>=2))return;
        FPSMagicPreview::BeginRefresh(Preview,Engine);
        FPSMagicPreview::DrawPath(Preview,S.Arc,FPSMagicPreview::LineThickness,0.f,true);
        if(!TestTrue(FString(Case)+TEXT(" submits dashes"),!Preview->BatchedLines.IsEmpty()))return;
        const double Error=FVector::Dist(Preview->BatchedLines.Last().End,S.Impact);
        TestTrue(FString(Case)+TEXT(" last visible dash reaches the contact point"),Error<.02);
        int32 Penetrations=0;
        for(const auto& Line:Preview->BatchedLines)
        {
            // Allow the actual contact at the last endpoint, but no solid before it.
            const FVector D=Line.End-Line.Start;
            if(D.Size()>.05 && World->LineTraceTestByChannel(Line.Start,Line.End-D.GetSafeNormal()*.05,ECC_WorldDynamic,Query))++Penetrations;
        }
        TestEqual(FString(Case)+TEXT(" solid crossings before the endpoint"),Penetrations,0);
        AddInfo(FString::Printf(TEXT("%s: end_error_cm=%.5f solid_crossings=%d"),Case,Error,Penetrations));
    };
    auto CheckRing=[&](const TCHAR* Case,const FVillageSiegeSight& S,double Radius,UPrimitiveComponent* Support,bool Complete,
        UPrimitiveComponent* LowerSupport=nullptr)
    {
        BuildImpactOutline(*World,S.Impact,S.ImpactNormal,S.bHitUnit,Query,Ring,Radius);
        TestTrue(FString(Case)+TEXT(" has supported outline"),!Ring.IsEmpty());
        if(Complete)TestEqual(FString(Case)+TEXT(" has a full circumference"),Ring.Num(),ImpactOutlineSides*2);
        int32 Detached=0;
        double Worst=0.;
        for(const FBatchedLine& L:Ring)
            for(int32 K=0;K<=4;++K)
            {
                const FVector P=FMath::Lerp(L.Start,L.End,K/4.);
                FHitResult H;
                // Probe the expected surface directly, independently of the ring builder.
                const FVector From=P+FVector(0,0,2.),To=P-FVector(0,0,4.);
                if(!Support->LineTraceComponent(H,From,To,Query) &&
                   !(LowerSupport && LowerSupport->LineTraceComponent(H,From,To,Query))) {++Detached;continue;}
                const double Clearance=P.Z-H.ImpactPoint.Z;
                Worst=FMath::Max(Worst,FMath::Abs(Clearance-GroundLift));
                if(Clearance<-.01 || Clearance>GroundLift+.1)++Detached;
            }
        TestEqual(FString(Case)+TEXT(" floating or buried ring samples"),Detached,0);
        AddInfo(FString::Printf(TEXT("%s: edge_segments=%d detached_samples=%d offset_error_cm=%.5f"),Case,Ring.Num(),Detached,Worst));
    };
    FVillageSiegeSight Sight;
    for(const float Elevation:{-28.f,-4.f,24.f})
    {
        Engine->ManualSight(nullptr,0.,Elevation,Sight,true);
        const FString Label=FString::Printf(TEXT("flat %.0f"),Elevation);
        CheckArc(*Label,Sight);
        CheckRing(*Label,Sight,500.,Floor,true);
        TestTrue(TEXT("floor contact has ground elevation"),FMath::Abs(Sight.Impact.Z)<.02);
    }
    for(int32 Rank=1;Rank<=3;++Rank)
    {
        const double Radius=500.+75.*Rank;
        CheckRing(*FString::Printf(TEXT("radius rank %d"),Rank),Sight,Radius,Floor,true);
        if(!Ring.IsEmpty())TestTrue(TEXT("upgraded radius preserved"),FMath::IsNearlyEqual(FVector::Dist2D(Ring[0].Start,Sight.Impact),Radius,.05));
    }
    Engine->SetActorLocation(FVector(0,0,1820));
    Engine->ManualSight(nullptr,35.,-4.,Sight,true);
    CheckArc(TEXT("tower"),Sight);CheckRing(TEXT("tower"),Sight,650.,Floor,true);
    Engine->SetActorLocation(FVector::ZeroVector);

    Floor->SetWorldRotation(FRotator(7.,0.,0.));
    Engine->ManualSight(nullptr,0.,-4.,Sight,true);
    TestTrue(TEXT("sloped terrain first contact"),Sight.HasImpact && Sight.ImpactNormal.Z<.999);
    CheckArc(TEXT("slope"),Sight);CheckRing(TEXT("slope"),Sight,575.,Floor,true);
    Floor->SetWorldRotation(FRotator::ZeroRotator);
    auto* Roof=Box(FVector(4700,0,550),FVector(300,850,25));
    Engine->ManualSight(nullptr,0.,-4.,Sight,true);
    TestTrue(TEXT("roof is first contact"),Sight.HasImpact && FMath::Abs(Sight.Impact.Z-575.)<.05);
    CheckArc(TEXT("roof"),Sight);CheckRing(TEXT("roof edge"),Sight,500.,Roof,false,Floor);
    TestTrue(TEXT("upper edges rest on the roof"),Ring.ContainsByPredicate([](const FBatchedLine& L){return L.Start.Z>575. && L.End.Z>575.;}));
    TestTrue(TEXT("edges beyond the roof rest on the floor"),Ring.ContainsByPredicate([](const FBatchedLine& L){return L.Start.Z<2. && L.End.Z<2.;}));
    Roof->SetCollisionEnabled(ECollisionEnabled::NoCollision);

    Engine->ManualSight(nullptr,0.,-4.,Sight,true);
    if(Sight.Arc.Num()>5)
    {
        auto* Unit=World->SpawnActor<APawn>();
        auto* Body=NewObject<UBoxComponent>(Unit);Unit->SetRootComponent(Body);
        Body->InitBoxExtent(FVector(55));Body->SetCollisionProfileName(TEXT("BlockAll"));
        Body->SetWorldLocation(Sight.Arc[Sight.Arc.Num()/2]);Body->RegisterComponent();
        Engine->ManualSight(nullptr,0.,-4.,Sight,true);
        TestTrue(TEXT("lofted unit intercepts before floor"),Sight.bHitUnit && Sight.Impact.Z>140.);
        CheckArc(TEXT("unit"),Sight);CheckRing(TEXT("floor below unit"),Sight,500.,Floor,true);
        Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    }
    Box(FVector(2300,0,1000),FVector(30,600,1800));
    Engine->ManualSight(nullptr,0.,-4.,Sight,true);
    TestTrue(TEXT("wall intercepts above floor"),Sight.HasImpact && Sight.Impact.X<2400. && Sight.Impact.Z>140.);
    CheckArc(TEXT("wall"),Sight);CheckRing(TEXT("floor below wall"),Sight,500.,Floor,false);
    Floor->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    BuildImpactOutline(*World,Sight.Impact,Sight.ImpactNormal,false,Query,Ring,500.);
    TestTrue(TEXT("unsupported ring clears"),Ring.IsEmpty());
    Engine->ManualSight(nullptr,130.,-4.,Sight,true);
    TestTrue(TEXT("no hit clears old path"),!Sight.HasImpact && Sight.Arc.IsEmpty() && !Sight.CanFire);

    auto* Clock=World->SpawnActor<AGameStateBase>();
    World->SetGameState(Clock);
    auto* Offset=FindFProperty<FFloatProperty>(AGameStateBase::StaticClass(),TEXT("ServerWorldTimeSecondsDelta"));
    if(TestNotNull(TEXT("server clock offset"),Offset))
    {
        Engine->Shot.Started=100.;
        float Fraction=0.f;
        Offset->SetPropertyValue_InContainer(Clock,101.08f);
        TestFalse(TEXT("windup alone does not start a reload hint"),Engine->GetReloadProgress(Fraction));
        Engine->Shot.bReleased=true;
        Offset->SetPropertyValue_InContainer(Clock,107.08f);
        TestTrue(TEXT("stone half loaded after six seconds"),Engine->GetReloadProgress(Fraction) && FMath::IsNearlyEqual(Fraction,.5f,.001f));
        TestTrue(TEXT("firing gate uses the same clock"),FMath::IsNearlyEqual(Engine->ReloadRemaining(),6.,.001));
        Offset->SetPropertyValue_InContainer(Clock,113.09f);
        TestTrue(TEXT("ready and complete together"),Engine->ReloadRemaining()==0. && Engine->GetReloadProgress(Fraction) && Fraction==1.f);
        Offset->SetPropertyValue_InContainer(Clock,114.f);
        TestFalse(TEXT("complete hint clears"),Engine->GetReloadProgress(Fraction));
        Engine->bStone=false;
        Offset->SetPropertyValue_InContainer(Clock,101.88f);
        TestTrue(TEXT("ballista uses updated reload"),Engine->GetReloadProgress(Fraction) && FMath::IsNearlyEqual(Fraction,.5f,.001f));
    }
    World->SetGameState(nullptr);
    World->DestroyWorld(false);
    return true;
}

#include "VillageLightningSpire.h"
#include "VillageSiegeUpgrades.h"
#include "TemperateHillsWorld.h"
#include "EngineUtils.h"
#include "Materials/MaterialInterface.h"
#include "../Building/VillageBuildDefense.h"
#include "../Skills/FPSLightningArc.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Monsters/InfectedDogMonster.h"
#include "../Monsters/MonsterCombatComponent.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FVillageLightningSpireTest,"FPSGAME.Village.Siege.LightningSpire",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FVillageLightningSpireTest::RunTest(const FString&)
{
    using namespace VillageSiegeUpgrades;
    uint64 Ranks=0;
    Ranks=SetRank(Ranks,Index(Trebuchet,Damage),15);
    Ranks=SetRank(Ranks,Index(Ballista,Reload),12);
    Ranks=SetRank(Ranks,Index(HotOil,OilBurnStacks),3);
    Ranks=SetRank(Ranks,Index(LightningSpire,SpireDamage),15);
    Ranks=SetRank(Ranks,Index(LightningSpire,SpireCooldown),15);
    Ranks=SetRank(Ranks,Index(LightningSpire,SpireElectrify),3);
    Ranks=SetRank(Ranks,Index(LightningSpire,SpireReach),15);
    TestEqual(TEXT("trebuchet damage rank preserved"),Rank(Ranks,Index(Trebuchet,Damage)),15);
    TestEqual(TEXT("ballista reload rank preserved"),Rank(Ranks,Index(Ballista,Reload)),12);
    TestEqual(TEXT("hot oil burn rank preserved"),Rank(Ranks,Index(HotOil,OilBurnStacks)),3);
    TestTrue(TEXT("spire lv0 damage is 90"),FMath::IsNearlyEqual(Value(LightningSpire,SpireDamage,0),90.,0.01));
    TestTrue(TEXT("spire max damage is 225"),FMath::IsNearlyEqual(Value(LightningSpire,SpireDamage,15),225.,0.01));
    TestTrue(TEXT("spire max reach is 7540 cm"),FMath::IsNearlyEqual(Value(LightningSpire,SpireReach,15),7540.,0.01));
    TestTrue(TEXT("spire lv0 cooldown is 5.20 s"),FMath::IsNearlyEqual(Value(LightningSpire,SpireCooldown,0),5.20,0.005));
    TestTrue(TEXT("spire max cooldown is 2.86 s"),FMath::IsNearlyEqual(Value(LightningSpire,SpireCooldown,15),2.86,0.005));
    TestTrue(TEXT("spire max electrify stacks is 4"),FMath::IsNearlyEqual(Value(LightningSpire,SpireElectrify,3),4.,0.01));
    TestTrue(TEXT("ballista lv0/lv15 damage 320/800"),FMath::IsNearlyEqual(Value(Ballista,Damage,0),320.,0.01) && FMath::IsNearlyEqual(Value(Ballista,Damage,15),800.,0.01));
    TestTrue(TEXT("ballista lv0/lv15 reload 2.60/1.43"),FMath::IsNearlyEqual(Value(Ballista,Reload,0),2.60,0.005) && FMath::IsNearlyEqual(Value(Ballista,Reload,15),1.43,0.005));
    TestTrue(TEXT("ballista lv3 armor pen 45%"),FMath::IsNearlyEqual(Value(Ballista,Special,3),0.45,0.001));
    TestTrue(TEXT("trebuchet lv0/lv15 damage 220/550"),FMath::IsNearlyEqual(Value(Trebuchet,Damage,0),220.,0.01) && FMath::IsNearlyEqual(Value(Trebuchet,Damage,15),550.,0.01));
    TestTrue(TEXT("trebuchet lv0/lv15 reload 12.0/6.6"),FMath::IsNearlyEqual(Value(Trebuchet,Reload,0),12.00,0.005) && FMath::IsNearlyEqual(Value(Trebuchet,Reload,15),6.60,0.005));
    const FRanks UniqueRanks=SetRank(FRanks{Ranks,0},TrebuchetHotOilIdx,1);
    TestTrue(TEXT("trebuchet hot oil stored in High ranks cleanly"),
        Rank(UniqueRanks,TrebuchetHotOilIdx)==1 && HasTrebuchetHotOil(UniqueRanks) && Rank(UniqueRanks,Index(Trebuchet,Damage))==15 &&
        MaxRank(TrebuchetHotOilIdx)==1 && Price(TrebuchetHotOilIdx,0)==1200 &&
        FCString::Strcmp(RequiredBlueprint(TrebuchetHotOilIdx),TEXT("siege_blueprint_insulated_oil_pack"))==0);

    // Placement range indicator calculation sync across all 4 facilities & upgrade tiers.
    VillageBuildDefense::FVillageSiegeRangeSpec Spec;
    TestTrue(TEXT("spire lv0 placement radius is 5200 cm"),VillageBuildDefense::ComputeSiegeRange(VillageBuildDefense::LightningSpire,0,1820.,Spec) && FMath::IsNearlyEqual(Spec.OuterRadiusCm,5200.,0.1) && Spec.InnerRadiusCm==0.);
    TestTrue(TEXT("spire lv15 placement radius is 7540 cm"),VillageBuildDefense::ComputeSiegeRange(VillageBuildDefense::LightningSpire,Ranks,1820.,Spec) && FMath::IsNearlyEqual(Spec.OuterRadiusCm,7540.,0.1));
    TestTrue(TEXT("trebuchet lv15 placement radius includes 1650 cm blind zone"),VillageBuildDefense::ComputeSiegeRange(VillageBuildDefense::Trebuchet,SetRank(0,Index(Trebuchet,Reach),15),0.,Spec) && FMath::IsNearlyEqual(Spec.OuterRadiusCm,11745.,0.5) && FMath::IsNearlyEqual(Spec.InnerRadiusCm,1650.,0.1));
    TestTrue(TEXT("ballista projects onto ground from 18.2m tower"),VillageBuildDefense::ComputeSiegeRange(VillageBuildDefense::Ballista,0,1820.,Spec) && FMath::IsNearlyEqual(Spec.OuterRadiusCm,FMath::Sqrt(5600.*5600.-1820.*1820.),0.5) && FMath::IsNearlyEqual(Spec.InnerRadiusCm,340.,0.1));
    TestTrue(TEXT("oil pot placement indicator fills inner pour circle + spread"),VillageBuildDefense::ComputeSiegeRange(VillageBuildDefense::OilPot,SetRank(0,Index(HotOil,OilRadius),15),0.,Spec) && FMath::IsNearlyEqual(Spec.OuterRadiusCm,800.,0.1) && Spec.bFillInner);
    TestNotNull(TEXT("M_SiegeRangeIndicator material asset loads"),LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/PlacementPreview/M_SiegeRangeIndicator.M_SiegeRangeIndicator")));

    UWorld::InitializationValues Settings;
    Settings.AllowAudioPlayback(false).RequiresHitProxies(false).CreatePhysicsScene(true)
        .CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if(!TestNotNull(TEXT("isolated spire test world"),World))return false;

    auto* Clock=World->SpawnActor<AGameStateBase>();
    World->SetGameState(Clock);
    auto* Offset=FindFProperty<FFloatProperty>(AGameStateBase::StaticClass(),TEXT("ServerWorldTimeSecondsDelta"));
    TestNotNull(TEXT("server clock offset property"),Offset);
    if(Offset)Offset->SetPropertyValue_InContainer(Clock,10.f);

    auto* Hills=World->SpawnActor<ATemperateHillsWorld>();
    uint64 ActiveRanks=0;
    ActiveRanks=SetRank(ActiveRanks,Index(LightningSpire,SpireDamage),5);
    ActiveRanks=SetRank(ActiveRanks,Index(LightningSpire,SpireReach),10);
    ActiveRanks=SetRank(ActiveRanks,Index(LightningSpire,SpireCooldown),5);
    ActiveRanks=SetRank(ActiveRanks,Index(LightningSpire,SpireElectrify),2);
    if(auto* RanksProp=FindFProperty<FUInt64Property>(ATemperateHillsWorld::StaticClass(),TEXT("SiegeRanks")))
        RanksProp->SetPropertyValue_InContainer(Hills,ActiveRanks);

    auto* Carrier=World->SpawnActor<AVoxelBuildPrefabActor>(FVector::ZeroVector,FRotator::ZeroRotator);
    auto* Spire=World->SpawnActor<AVillageLightningSpire>(FVector(0.,0.,600.),FRotator::ZeroRotator);
    TestNotNull(TEXT("carrier spawned"),Carrier);
    TestNotNull(TEXT("spire spawned"),Spire);
    Spire->AttachToActor(Carrier,FAttachmentTransformRules::KeepWorldTransform);
    Spire->Initialize(Hills,77,AVillageLightningSpire::MeshAsset(TEXT("Base")),850.f);
    TestTrue(TEXT("identifies as lightning spire"),Spire->IsLightningSpire());
    TestTrue(TEXT("uses crosshair HUD"),Spire->UsesCrosshair());
    TestTrue(TEXT("spire range reads rank 10"),FMath::IsNearlyEqual(Spire->Range(),6760.,1.));

    auto SpawnTarget=[&](const FVector& Pos)
    {
        auto* Dog=World->SpawnActor<AInfectedDogMonster>(Pos,FRotator::ZeroRotator);
        if(Dog){Dog->MaxHealth=2400.f;Dog->Health=2400.f;}
        return Dog;
    };
    auto* Dog1=SpawnTarget(FVector(1200.,0.,50.));
    auto* Dog2=SpawnTarget(FVector(1350.,120.,50.));
    TestNotNull(TEXT("primary target spawned"),Dog1);
    TestNotNull(TEXT("chain/overload neighbor spawned"),Dog2);

    auto* Op=World->SpawnActor<APawn>(FVector(-120.,0.,620.),FRotator::ZeroRotator);
    TestTrue(TEXT("operator claims spire"),Spire->Claim(Op));
    FVillageSiegeSight Sight;
    Spire->ManualSight(Op,0.f,-36.f,Sight,true);
    TestTrue(TEXT("manual sight magnetic-locks nearby target"),Sight.CanFire && Sight.bHitUnit);

    auto* Cam=World->SpawnActor<ACameraActor>();
    auto* Control=NewObject<UVillageSiegeControl>(Op);
    if(auto* StationProp=FindFProperty<FObjectProperty>(UVillageSiegeControl::StaticClass(),TEXT("Station")))
        StationProp->SetObjectPropertyValue_InContainer(Control,Spire);
    if(auto* CameraProp=FindFProperty<FObjectProperty>(UVillageSiegeControl::StaticClass(),TEXT("Camera")))
        CameraProp->SetObjectPropertyValue_InContainer(Control,Cam);
    TSet<FPrimitiveComponentId> Hidden;
    Control->AddHiddenOperatorComponents(Cam,Hidden);
    int32 RegisteredParts=0;
    Spire->ForEachComponent<UPrimitiveComponent>(false,[&](UPrimitiveComponent* Prim)
    {
        if(Prim && Prim->IsRegistered())
        {
            ++RegisteredParts;
            TestTrue(TEXT("operated lightning spire primitive hidden from aim camera"),Hidden.Contains(Prim->GetPrimitiveSceneId()));
        }
    });
    TestTrue(TEXT("all four spire mesh components hidden when aiming"),RegisteredParts>=4);
    TSet<FPrimitiveComponentId> OtherHidden;
    Control->AddHiddenOperatorComponents(Op,OtherHidden);
    TestTrue(TEXT("spire stays visible when not viewing from siege camera"),OtherHidden.IsEmpty());

    Spire->FireManual(Op,0.f,-36.f);
    for(int32 Step=0;Step<3;++Step){++GFrameCounter;World->GetTimerManager().Tick(0.04f);}

    float MaxWidth=0.f;
    int32 ArcCount=0;
    auto* WidthProp=FindFProperty<FFloatProperty>(AFPSLightningArc::StaticClass(),TEXT("NetWidth"));
    for(TActorIterator<AFPSLightningArc> It(World);It;++It)
    {
        ++ArcCount;
        if(WidthProp)MaxWidth=FMath::Max(MaxWidth,WidthProp->GetPropertyValue_InContainer(*It));
    }
    TestTrue(TEXT("boosted thickened lightning arcs spawned"),ArcCount>=3 && MaxWidth>=2.4f);

    auto* Status1=UCombatStatusFormula::GetOrAdd(Dog1);
    auto* Status2=UCombatStatusFormula::GetOrAdd(Dog2);
    TestTrue(TEXT("hit applies stun interrupt"),Status1 && Status1->IsStunned());
    TestEqual(TEXT("hit applies rank-2 electrify (3 stacks)"),Status1?Status1->ElectrifiedCount():-1,3);
    TestTrue(TEXT("chain bolt jumps to second target"),Status2 && Status2->ElectrifiedCount()==3);

    // Advance clock past manual cooldown (3.44s at rank 5) without ticking status expiry, then strike again to trigger 5-stack Overload.
    if(Offset)Offset->SetPropertyValue_InContainer(Clock,20.f);
    Spire->FireManual(Op,0.f,-36.f);
    for(int32 Step=0;Step<3;++Step){++GFrameCounter;World->GetTimerManager().Tick(0.04f);}
    int32 TotalArcCount=0;
    for(TActorIterator<AFPSLightningArc> It(World);It;++It)++TotalArcCount;
    TestEqual(TEXT("overload consumes stacks on chain target"),Status2?Status2->ElectrifiedCount():-1,0);
    TestEqual(TEXT("secondary overload splashes back 1 stack onto primary target"),Status1?Status1->ElectrifiedCount():-1,1);
    TestTrue(TEXT("overload applies stun on both targets"),Status1 && Status1->IsStunned() && Status2 && Status2->IsStunned());
    TestTrue(TEXT("overload spawns extra splash arcs"),TotalArcCount>=ArcCount+5);

    // Parapet sky-arc test: supporting tower roof directly beneath spire blocks straight ray to a base-hugger 18m down,
    // while separate closed house roof blocks indoor enemies.
    auto SpawnBox=[&](const FVector& Pos,const FVector& Extent)
    {
        auto* Owner=World->SpawnActor<AActor>();
        auto* Shape=NewObject<UBoxComponent>(Owner);
        Owner->SetRootComponent(Shape);
        Shape->InitBoxExtent(Extent);
        Shape->SetCollisionProfileName(TEXT("BlockAll"));
        Shape->SetWorldLocation(Pos);
        Shape->RegisterComponent();
        return Owner;
    };
    SpawnBox(FVector(0.,0.,580.),FVector(460.,460.,20.));
    Dog1->MaxHealth=1.f;Dog1->Health=0.f; // exclude Dog1/Dog2 so FindTarget tests new targets cleanly
    Dog2->MaxHealth=1.f;Dog2->Health=0.f;
    auto* DogBase=SpawnTarget(FVector(700.,0.,-1200.));
    auto* DogIndoors=SpawnTarget(FVector(2000.,0.,50.));
    SpawnBox(FVector(2000.,0.,400.),FVector(320.,320.,20.));
    Spire->Vacate(Op);
    if(Offset)Offset->SetPropertyValue_InContainer(Clock,30.f);
    World->TimeSeconds=1.;
    Spire->FindTarget();
    for(int32 Step=0;Step<10;++Step){++GFrameCounter;World->GetTimerManager().Tick(0.03f);}
    auto* BaseStatus=UCombatStatusFormula::GetOrAdd(DogBase);
    auto* IndoorStatus=UCombatStatusFormula::GetOrAdd(DogIndoors);
    TestTrue(TEXT("spire arcs over own parapet roof to strike tower-base enemy"),DogBase->Health<2400.f && BaseStatus && BaseStatus->ElectrifiedCount()==3);
    TestEqual(TEXT("separate closed roof still shields indoor enemy"),IndoorStatus?IndoorStatus->ElectrifiedCount():-1,0);

    // Manual ground-surge test: striking floor ~250 cm beside an agile enemy (outside 180 cm direct snap, inside 320 cm surge) deals AOE surge + electrify.
    SpawnBox(FVector(2400.,400.,0.),FVector(400.,400.,10.));
    auto* DogSurge=SpawnTarget(FVector(2400.,640.,50.));
    TestTrue(TEXT("re-claim spire for manual surge test"),Spire->Claim(Op));
    if(Offset)Offset->SetPropertyValue_InContainer(Clock,40.f);
    World->TimeSeconds=2.;
    const FVector GroundAim(2400.,400.,10.);
    const FRotator AimRot=(GroundAim-(Spire->CrownWorldOrigin()+FVector(0.,0.,24.))).Rotation();
    Spire->FireManual(Op,AimRot.Yaw,AimRot.Pitch);
    for(int32 Step=0;Step<3;++Step){++GFrameCounter;World->GetTimerManager().Tick(0.04f);}
    auto* SurgeStatus=UCombatStatusFormula::GetOrAdd(DogSurge);
    TestTrue(TEXT("manual ground strike deals surge AOE + stun + electrify"),DogSurge->Health<2400.f && SurgeStatus && SurgeStatus->IsStunned() && SurgeStatus->ElectrifiedCount()==3);

    // Pure-math manual camera poses + motion-blur suppression verification across all siege types.
    FVector CamLoc;
    FRotator CamRot,Facing;
    Spire->ComputeManualCamera(18.f,-22.f,0.,CamLoc,CamRot,Facing);
    TestTrue(TEXT("spire pure-math camera matches ManualSight pose"),CamLoc.Equals(Sight.Camera,.1));
    Control->ConfigureCameraPostProcess();
    if(auto* CamComp=Cam->GetCameraComponent())
    {
        TestTrue(TEXT("siege camera explicitly overrides and disables motion blur"),
            CamComp->PostProcessSettings.bOverride_MotionBlurAmount && CamComp->PostProcessSettings.MotionBlurAmount==0.f &&
            CamComp->PostProcessSettings.bOverride_MotionBlurMax && CamComp->PostProcessSettings.MotionBlurMax==0.f);
    }

    World->SetGameState(nullptr);
    World->DestroyWorld(false);
    return true;
}

#include "VillageHotOil.h"
#include "VillageDefenseState.h"
#include "../FPSGAMECharacter.h"
#include "../Movement/StableRidingHorse.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelPickup.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FVillageTrebuchetHotOilTest,"FPSGAME.Village.Siege.TrebuchetHotOil",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FVillageTrebuchetHotOilTest::RunTest(const FString&)
{
    using namespace VillageSiegeUpgrades;

    // 1 & 2. Validate Legendary blueprint item definition, pickup mesh/glow, and purchase gate.
    {
        const FString AuditProfile=TEXT("TrebHotOilAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
        const FString OriginalCmd=FCommandLine::Get();
        FCommandLine::Set(*(OriginalCmd+TEXT(" -ColdSteelProfile=")+AuditProfile));
        TStrongObjectPtr<UGameInstance> GI(NewObject<UGameInstance>(GEngine));
        GI->InitializeStandalone(TEXT("TrebHotOilAudit"));
        FCommandLine::Set(*OriginalCmd);
        UWorld* AuditWorld=GI->GetWorld();
        if(!TestNotNull(TEXT("isolated trebuchet hot oil audit world"),AuditWorld))return false;
        const FGuid TestWorldId=FGuid::NewGuid();
        const FString SaveSlot=TEXT("VillageDefenses_")+TestWorldId.ToString(EGuidFormats::Digits);
        auto* Wallet=GI->GetSubsystem<UColdSteelStatusModel>();
        if(!TestNotNull(TEXT("status model created"),Wallet))
        {
            GI->Shutdown();GEngine->DestroyWorldContext(AuditWorld);AuditWorld->DestroyWorld(false);
            return false;
        }
        const FString ProfileSlot=Wallet->ProfileSlot();
        ON_SCOPE_EXIT
        {
            UGameplayStatics::DeleteGameInSlot(SaveSlot,0);
            UGameplayStatics::DeleteGameInSlot(ProfileSlot+TEXT("_A"),0);
            UGameplayStatics::DeleteGameInSlot(ProfileSlot+TEXT("_B"),0);
            GI->Shutdown();
            GEngine->DestroyWorldContext(AuditWorld);
            AuditWorld->DestroyWorld(false);
        };

        const FColdSteelItem BpItem=Wallet->CreateItem(TrebuchetHotOilBlueprintId,1);
        TestFalse(TEXT("blueprint item exists in catalog"),BpItem.Data.IsEmpty());
        TestEqual(TEXT("blueprint rarity is legendary"),ColdSteelInventory::Text(BpItem,TEXT("rarity")),FString(TEXT("legendary")));
        TestEqual(TEXT("blueprint footprint is 1x2"),BpItem.Width*10+BpItem.Height,12);

        auto* Pickup=AuditWorld->SpawnActor<AColdSteelPickup>(FVector(0.,0.,100.),FRotator::ZeroRotator);
        if(TestNotNull(TEXT("blueprint pickup spawned"),Pickup))
        {
            Pickup->InitializeItem(BpItem);
            const UStaticMesh* LoadedMesh=Pickup->Mesh?Pickup->Mesh->GetStaticMesh():nullptr;
            TestTrue(TEXT("blueprint pickup reuses magic scroll mesh"),
                LoadedMesh && LoadedMesh->GetPathName().Contains(TEXT("SM_magic_scroll")));
        }

        auto* PC=AuditWorld->SpawnActor<APlayerController>();
        auto* Payer=AuditWorld->SpawnActor<AFPSGAMECharacter>(FVector::ZeroVector,FRotator::ZeroRotator);
        if(TestNotNull(TEXT("payer controller & pawn"),PC) && TestNotNull(TEXT("payer pawn"),Payer))
        {
            PC->SetAsLocalPlayerController();
            PC->Possess(Payer);
            auto* DefenseState=AuditWorld->GetSubsystem<UVillageDefenseState>();
            FText Failure;
            TestFalse(TEXT("purchase fails without blueprint"),DefenseState->PurchaseUpgrade(TestWorldId,TrebuchetHotOilIdx,0,Payer,Failure));
            Wallet->SyncRuntime();
            auto Profile=Wallet->Snapshot();
            Profile.Souls=2000;
            const bool bInserted=ColdSteelInventory::Insert(Profile.Items,Wallet->CreateItem(TrebuchetHotOilBlueprintId,1));
            TestTrue(TEXT("insert blueprint into free bag slot"),bInserted);
            const bool bSeeded=Wallet->CommitState(MoveTemp(Profile));
            TestTrue(FString::Printf(TEXT("seed payer profile (%s)"),*Wallet->ResultMessage()),bSeeded);
            const bool bPurchased=DefenseState->PurchaseUpgrade(TestWorldId,TrebuchetHotOilIdx,0,Payer,Failure);
            TestTrue(FString::Printf(TEXT("purchase succeeds with blueprint & souls (%s)"),*Failure.ToString()),bPurchased);
            const FRanks Loaded=DefenseState->SelectGeneration(TestWorldId,FGuid());
            TestEqual(TEXT("purchased unique hot oil persisted in SiegeRanksExtra"),Rank(Loaded,TrebuchetHotOilIdx),1);
            int64 RemainingBp=0;
            for(const FColdSteelItem& It:Wallet->ProfileView().Items)
                if(It.Definition==TrebuchetHotOilBlueprintId)RemainingBp+=It.Count;
            TestEqual(TEXT("unlocking hot oil consumes 1 blueprint"),RemainingBp,int64(0));
        }
    }

    // 3. Validate 4th-shot cadence, HotOil upgrade stat sync, and strict friendly-fire immunity in EditorPreview world.
    UWorld::InitializationValues Settings;
    Settings.AllowAudioPlayback(false).RequiresHitProxies(false).CreatePhysicsScene(true)
        .CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if(!TestNotNull(TEXT("isolated trebuchet hot oil test world"),World))return false;

    auto* Clock=World->SpawnActor<AGameStateBase>();
    World->SetGameState(Clock);
    auto* Offset=FindFProperty<FFloatProperty>(AGameStateBase::StaticClass(),TEXT("ServerWorldTimeSecondsDelta"));
    if(Offset)Offset->SetPropertyValue_InContainer(Clock,10.f);

    auto* FloorActor=World->SpawnActor<AActor>();
    auto* FloorBox=NewObject<UBoxComponent>(FloorActor);
    FloorActor->SetRootComponent(FloorBox);
    FloorBox->InitBoxExtent(FVector(12000.,12000.,50.));
    FloorBox->SetCollisionProfileName(TEXT("BlockAll"));
    FloorBox->SetWorldLocation(FVector(0.,0.,-50.));
    FloorBox->RegisterComponent();

    auto* Hills=World->SpawnActor<ATemperateHillsWorld>();
    uint64 CoreRanks=0;
    CoreRanks=SetRank(CoreRanks,Index(HotOil,OilDamage),10);     // 10 * 2.0 = 20 dmg
    CoreRanks=SetRank(CoreRanks,Index(HotOil,OilRadius),10);     // 275 + 150 = 425 cm
    CoreRanks=SetRank(CoreRanks,Index(HotOil,OilDuration),2);    // 10 + 4 = 14 s
    CoreRanks=SetRank(CoreRanks,Index(HotOil,OilBurnStacks),2);  // 1 + 2 = 3 stacks
    const uint64 ExtraRanks=SetRank(FRanks{},TrebuchetHotOilIdx,1).High;
    if(auto* P=FindFProperty<FUInt64Property>(ATemperateHillsWorld::StaticClass(),TEXT("SiegeRanks")))
        P->SetPropertyValue_InContainer(Hills,CoreRanks);
    if(auto* P=FindFProperty<FUInt64Property>(ATemperateHillsWorld::StaticClass(),TEXT("SiegeExtraRanks")))
        P->SetPropertyValue_InContainer(Hills,ExtraRanks);

    auto* Carrier=World->SpawnActor<AVoxelBuildPrefabActor>(FVector::ZeroVector,FRotator::ZeroRotator);
    auto* Treb=World->SpawnActor<AVillageSiegeEngine>(FVector::ZeroVector,FRotator::ZeroRotator);
    Treb->AttachToActor(Carrier,FAttachmentTransformRules::KeepWorldTransform);
    Treb->Initialize(Hills,88,AVillageSiegeEngine::MeshAsset(TEXT("TrebuchetBase")),1000.f);
    TestTrue(TEXT("trebuchet recognizes unlocked unique hot oil"),Treb->HasTrebuchetHotOil());

    auto* Op=World->SpawnActor<APawn>(FVector(-120.,0.,50.),FRotator::ZeroRotator);
    TestTrue(TEXT("operator claims trebuchet"),Treb->Claim(Op));

    int32 HotOilPayloadsSeen=0;
    TSet<AVillageSiegeMissile*> ProcessedMissiles;
    for(int32 ShotIdx=1; ShotIdx<=4; ++ShotIdx)
    {
        if(Offset)Offset->SetPropertyValue_InContainer(Clock,10.f + ShotIdx*20.f);
        Treb->FireManual(Op,0.f,0.f);
        for(int32 Step=0; Step<40; ++Step){++GFrameCounter;World->GetTimerManager().Tick(0.03f);}
        TestEqual(FString::Printf(TEXT("shot %d charge counter"),ShotIdx),Treb->HotOilChargeCount(),ShotIdx<4?ShotIdx:0);

        AVillageSiegeMissile* ShotMissile=nullptr;
        for(TActorIterator<AVillageSiegeMissile> It(World); It; ++It)
            if(!ProcessedMissiles.Contains(*It)){ShotMissile=*It;break;}
        TestNotNull(FString::Printf(TEXT("shot %d spawned missile"),ShotIdx),ShotMissile);
        if(ShotMissile)
        {
            ProcessedMissiles.Add(ShotMissile);
            if(ShotMissile->bHotOilPayload)++HotOilPayloadsSeen;
            TestEqual(FString::Printf(TEXT("shot %d hot oil payload flag"),ShotIdx),ShotMissile->bHotOilPayload,ShotIdx==4);
            FHitResult ImpactHit(FloorActor,FloorBox,FVector(2500.,0.,0.),FVector::UpVector);
            ImpactHit.bBlockingHit=true;
            ShotMissile->Impact(ImpactHit);
        }
        int32 OilCountNow=0;
        for(TActorIterator<AVillageOilField> It(World); It; ++It)++OilCountNow;
        TestEqual(FString::Printf(TEXT("shot %d cumulative oil fields"),ShotIdx),OilCountNow,ShotIdx<4?0:1);
    }
    TestEqual(TEXT("only 4th shot carries hot oil payload"),HotOilPayloadsSeen,1);

    AVillageOilField* OilField=nullptr;
    int32 OilCount=0;
    for(TActorIterator<AVillageOilField> It(World); It; ++It){++OilCount;OilField=*It;}
    TestEqual(TEXT("exactly one oil field spawned on 4th impact"),OilCount,1);

    if(TestNotNull(TEXT("trebuchet oil field spawned"),OilField))
    {
        if(!OilField->HasActorBegunPlay())OilField->DispatchBeginPlay();
        TestTrue(TEXT("oil field configured for trebuchet splash & friendly safety"),OilField->bDirectSplash && OilField->bIgnoreFriendlies);
        TestTrue(TEXT("oil damage synced to HotOil rank 10 (20)"),FMath::IsNearlyEqual(OilField->FieldDamage(),20.f,0.01f));
        TestTrue(TEXT("oil radius synced to HotOil rank 10 (425)"),FMath::IsNearlyEqual(OilField->FieldRadius(),425.f,0.01f));
        TestTrue(TEXT("oil duration synced to HotOil rank 2 (14)"),FMath::IsNearlyEqual(OilField->FieldLife(),14.f,0.01f));
        TestEqual(TEXT("oil burn stacks synced to HotOil rank 2 (3)"),OilField->FieldBurnStacks(),3);

        FActorSpawnParameters UnitSpawn;
        UnitSpawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Enemy=World->SpawnActor<AInfectedDogMonster>(FVector(2500.,0.,90.),FRotator::ZeroRotator,UnitSpawn);
        if(Enemy){Enemy->MaxHealth=500.f;Enemy->Health=500.f;Enemy->SetActorLocation(FVector(2500.,0.,Enemy->GetSimpleCollisionHalfHeight()+2.));}
        auto* AllyPlayer=World->SpawnActor<AFPSGAMECharacter>(FVector(2590.,0.,96.),FRotator::ZeroRotator,UnitSpawn);
        if(AllyPlayer)AllyPlayer->SetActorLocation(FVector(2590.,0.,AllyPlayer->GetSimpleCollisionHalfHeight()+2.));
        auto* AllyHorse=World->SpawnActor<AStableRidingHorse>(FVector(2410.,0.,96.),FRotator::ZeroRotator,UnitSpawn);
        if(AllyHorse)AllyHorse->SetActorLocation(FVector(2410.,0.,AllyHorse->GetSimpleCollisionHalfHeight()+2.));

        const float EnemyStartHp=Enemy?Enemy->Health:0.f;
        auto* AllyHealth=AllyPlayer?AllyPlayer->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
        const float AllyStartHp=AllyHealth?AllyHealth->Health:0.f;
        const float HorseStartHp=AllyHorse?AllyHorse->GetHealth():0.f;

        if(Offset)Offset->SetPropertyValue_InContainer(Clock,92.f);
        for(int32 S=0;S<8;++S)OilField->SurveyStep(10000);
        OilField->Pulse(92.0);
        if(Offset)Offset->SetPropertyValue_InContainer(Clock,92.35f);
        OilField->Pulse(92.35);
        auto* EnemyStatus=Enemy?UCombatStatusFormula::GetOrAdd(Enemy):nullptr;
        auto* AllyStatus=AllyPlayer?AllyPlayer->FindComponentByClass<UCombatStatusFormula>():nullptr;
        auto* HorseStatus=AllyHorse?AllyHorse->FindComponentByClass<UCombatStatusFormula>():nullptr;
        TestTrue(TEXT("oil spread built valid wet bounds"),OilField->Spread.WetBounds.IsValid!=0);
        TestTrue(TEXT("enemy receives trebuchet hot oil damage"),Enemy && Enemy->Health<EnemyStartHp);
        TestTrue(TEXT("enemy receives trebuchet hot oil burn stacks"),EnemyStatus && EnemyStatus->BurnCount()>=3);
        TestTrue(TEXT("friendly player takes zero damage and zero burn from trebuchet oil"),
            AllyPlayer && AllyHealth && FMath::IsNearlyEqual(AllyHealth->Health,AllyStartHp,0.01f) && (!AllyStatus || AllyStatus->BurnCount()==0));
        TestTrue(TEXT("friendly horse takes zero damage and zero burn from trebuchet oil"),
            AllyHorse && FMath::IsNearlyEqual(AllyHorse->GetHealth(),HorseStartHp,0.01f) && (!HorseStatus || HorseStatus->BurnCount()==0));
    }

    World->SetGameState(nullptr);
    World->DestroyWorld(false);
    return true;
}

#include "VillageSmartTurret.h"
#include "VillageDefenseState.h"
#include "VillageDefenseCombat.h"
#include "../Building/VillageBuildDefense.h"
#include "../Combat/RangedAttackQuery.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/NurseZombie.h"
#include "../UI/ColdSteelDamageNumberSubsystem.h"
#include "../UI/ColdSteelPickup.h"
#include "../Weapons/FPSBallisticsComponent.h"
#include "../Weapons/FPSWeaponFXComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/LocalPlayer.h"
#include "Misc/CommandLine.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FVillageSmartTurretTest,"FPSGAME.Village.Siege.SmartTurret",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)

bool FVillageSmartTurretTest::RunTest(const FString&)
{
    using namespace VillageSiegeUpgrades;

    // 1. Verify 5th facility bitpacking in FRanks.High (indices 17..22) and scaling math.
    TestEqual(TEXT("SmartTurret facility stat count"),FacilityStatCount(SmartTurret),6);
    TestEqual(TEXT("SmartTurret base index"),Index(SmartTurret,TurretDamage),17);
    TestEqual(TEXT("SmartTurret pierce max index"),Index(SmartTurret,TurretPierce),22);
    TestEqual(TEXT("SmartTurret rank limits: 15,15,15,3,3,3"),
        MaxRank(Index(SmartTurret,TurretDamage))+MaxRank(Index(SmartTurret,TurretFeed))
        +MaxRank(Index(SmartTurret,TurretOptics))+MaxRank(Index(SmartTurret,TurretWeakpoint))
        +MaxRank(Index(SmartTurret,TurretMagExpand))+MaxRank(Index(SmartTurret,TurretPierce)),54);

    FRanks Ranks{};
    TestTrue(TEXT("Rank 0 TurretDamage multiplier is 0.85"),FMath::IsNearlyEqual(Installed(Ranks,SmartTurret,TurretDamage),0.85,0.001));
    TestTrue(TEXT("Rank 0 TurretOptics reach is 4200 cm"),FMath::IsNearlyEqual(Installed(Ranks,SmartTurret,TurretOptics),4200.,0.01));
    TestTrue(TEXT("Rank 0 TurretWeakpoint is 0"),FMath::IsNearlyEqual(Installed(Ranks,SmartTurret,TurretWeakpoint),0.,0.0001));
    TestEqual(TEXT("Rank 0 TurretMagExpand keeps base capacity"),TurretExpandedCapacity(30,Rank(Ranks,Index(SmartTurret,TurretMagExpand))),30);
    TestEqual(TEXT("Rank 0 TurretPierce is 0"),TurretBonusPierce(Rank(Ranks,Index(SmartTurret,TurretPierce))),0);

    FRanks MaxRanks{};
    MaxRanks=SetRank(MaxRanks,Index(SmartTurret,TurretDamage),15);
    MaxRanks=SetRank(MaxRanks,Index(SmartTurret,TurretFeed),15);
    MaxRanks=SetRank(MaxRanks,Index(SmartTurret,TurretOptics),15);
    MaxRanks=SetRank(MaxRanks,Index(SmartTurret,TurretWeakpoint),3);
    MaxRanks=SetRank(MaxRanks,Index(SmartTurret,TurretMagExpand),3);
    MaxRanks=SetRank(MaxRanks,Index(SmartTurret,TurretPierce),3);
    TestTrue(TEXT("Max Rank TurretDamage multiplier is 1.60"),FMath::IsNearlyEqual(Installed(MaxRanks,SmartTurret,TurretDamage),1.60,0.001));
    TestTrue(TEXT("Max Rank TurretOptics reach is 6450 cm"),FMath::IsNearlyEqual(Installed(MaxRanks,SmartTurret,TurretOptics),6450.,0.01));
    TestTrue(TEXT("Max Rank TurretWeakpoint is 0.30"),FMath::IsNearlyEqual(TurretWeakpointChance(Rank(MaxRanks,Index(SmartTurret,TurretWeakpoint))),0.30,0.0001));
    TestEqual(TEXT("Max Rank TurretMagExpand expands 30->53 (+75%)"),TurretExpandedCapacity(30,Rank(MaxRanks,Index(SmartTurret,TurretMagExpand))),53);
    TestEqual(TEXT("Max Rank TurretPierce is 3"),TurretBonusPierce(Rank(MaxRanks,Index(SmartTurret,TurretPierce))),3);
    TestTrue(TEXT("Max Rank TurretFeed fire rate boost"),TurretFireRateScale(Rank(MaxRanks,Index(SmartTurret,TurretFeed)))>1.29);
    TestTrue(TEXT("Max Rank TurretFeed reload speed reduction"),TurretReloadScale(Rank(MaxRanks,Index(SmartTurret,TurretFeed)))<0.56);

    // 2. Verify build placement ComputeSiegeRange matches TurretOptics and scales down on towers.
    VillageBuildDefense::FVillageSiegeRangeSpec Flat0,FlatMax,TowerMax;
    TestTrue(TEXT("ComputeSiegeRange supports SmartTurret"),VillageBuildDefense::ComputeSiegeRange(VillageBuildDefense::SmartTurret,Ranks,0.,Flat0));
    TestTrue(TEXT("SmartTurret flat range starts at 4200 cm"),FMath::IsNearlyEqual(Flat0.OuterRadiusCm,4200.,0.5));
    TestTrue(TEXT("ComputeSiegeRange reads FRanks.High"),VillageBuildDefense::ComputeSiegeRange(VillageBuildDefense::SmartTurret,MaxRanks,0.,FlatMax));
    TestTrue(TEXT("SmartTurret flat max range reaches 6450 cm"),FMath::IsNearlyEqual(FlatMax.OuterRadiusCm,6450.,0.5));
    TestTrue(TEXT("ComputeSiegeRange computes tower height projection"),VillageBuildDefense::ComputeSiegeRange(VillageBuildDefense::SmartTurret,MaxRanks,1800.,TowerMax));
    TestTrue(TEXT("Elevated placement reduces ground projection"),TowerMax.OuterRadiusCm<FlatMax.OuterRadiusCm && TowerMax.OuterRadiusCm>6100.);

    // 3. Verify 16 primary long guns allowed and all 5 pistols excluded.
    static const TCHAR* Allowed16[]={
        TEXT("ue_m4a1"),TEXT("ue_akm"),TEXT("ue_qbz191"),TEXT("ue_ash12"),TEXT("ue_m16a2"),TEXT("ue_a762"),TEXT("ue_hk416"),
        TEXT("ue_m249"),TEXT("ue_pkm_lowpoly"),TEXT("ue_lmg201"),
        TEXT("ue_super90"),TEXT("ue_m870"),TEXT("ue_saiga12k"),
        TEXT("ue_svd"),TEXT("ue_svch"),TEXT("ue_m24")
    };
    static const TCHAR* Excluded5Pistols[]={
        TEXT("ue_m1911"),TEXT("ue_g18"),TEXT("ue_pit_viper2011"),TEXT("ue_dan_wesson715"),TEXT("ue_rsh12")
    };
    for(const TCHAR* Id : Allowed16)
        TestTrue(FString::Printf(TEXT("Allowed long gun: %s"),Id),AVillageSmartTurret::IsMountableFirearm(Id));
    for(const TCHAR* Id : Excluded5Pistols)
        TestFalse(FString::Printf(TEXT("Excluded pistol: %s"),Id),AVillageSmartTurret::IsMountableFirearm(Id));
    TestFalse(TEXT("Empty definition rejected"),AVillageSmartTurret::IsMountableFirearm(TEXT("")));

    // 4. Verify isolated world weapon stat scaling, persistence round-trip & EjectWeaponSafely drop fallback.
    UWorld::InitializationValues Settings;
    Settings.AllowAudioPlayback(false).RequiresHitProxies(false).CreatePhysicsScene(true)
        .CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if(!TestNotNull(TEXT("isolated smart turret test world"),World))return false;

    FColdSteelItem SampleM4;
    SampleM4.InstanceId=TEXT("TestTurretM4_01");
    SampleM4.Definition=TEXT("ue_m4a1");
    SampleM4.Magazine=30;
    const FSmartTurretWeaponStats Stats0=AVillageSmartTurret::ComputeWeaponStats(SampleM4,nullptr,Ranks);
    const FSmartTurretWeaponStats StatsMax=AVillageSmartTurret::ComputeWeaponStats(SampleM4,nullptr,MaxRanks);
    TestTrue(TEXT("M4 stats valid"),Stats0.bValid && StatsMax.bValid);
    TestTrue(TEXT("Workshop upgrades amplify turret damage"),StatsMax.PerShotDamage>Stats0.PerShotDamage*1.8f);
    TestTrue(TEXT("Workshop upgrades expand turret mag capacity"),StatsMax.ExpandedCapacity>Stats0.ExpandedCapacity);
    TestTrue(TEXT("Workshop upgrades speed up turret reload"),StatsMax.ReloadTime<Stats0.ReloadTime);
    TestTrue(TEXT("Workshop upgrades boost weakpoint and pierce"),StatsMax.WeakpointChance>0.29f && StatsMax.BonusPierce==3);

    const FGuid TestWorldId=FGuid::NewGuid(),TestPlacedId=FGuid::NewGuid();
    if(auto* DefState=World->GetSubsystem<UVillageDefenseState>())
    {
        DefState->SaveTurretWeapon(TestWorldId,TestPlacedId,SampleM4);
        FColdSteelItem Loaded;
        TestTrue(TEXT("UVillageDefenseState loads saved turret weapon"),DefState->LoadTurretWeapon(TestWorldId,TestPlacedId,Loaded));
        TestEqual(TEXT("Loaded weapon definition matches"),Loaded.Definition,SampleM4.Definition);
        DefState->ClearTurretWeapon(TestWorldId,TestPlacedId);
        TestFalse(TEXT("Cleared weapon no longer loads"),DefState->LoadTurretWeapon(TestWorldId,TestPlacedId,Loaded));
    }

    auto* Turret=World->SpawnActor<AVillageSmartTurret>(FVector::ZeroVector,FRotator::ZeroRotator);
    if(TestNotNull(TEXT("Spawned AVillageSmartTurret"),Turret))
    {
        Turret->MountedWeapon=SampleM4;
        Turret->MaxAmmo=Stats0.ExpandedCapacity;
        Turret->CurrentAmmo=21;
        TestTrue(TEXT("Turret reports mounted weapon"),Turret->HasMountedWeapon());
        // Crash regression: turret world-tracer FX firing without a skeletal WeaponMesh must not dereference null.
        Turret->DispatchBeginPlay();
        Turret->MulticastShotFX_Implementation(FVector(100.,0.,150.),FVector::ForwardVector,false,1);
        Turret->MulticastShotFX_Implementation(FVector(100.,0.,150.),FVector::ForwardVector,true,8);
        if(auto* FX=Turret->WeaponFX.Get())
        {
            FX->OnShotAtMuzzle(false,FTransform(FVector(100.,0.,150.)),1.f,0.f);
            FX->EjectPumpCasing();
        }
        Turret->EjectWeaponSafely(nullptr);
        TestFalse(TEXT("EjectWeaponSafely clears mounted slot"),Turret->HasMountedWeapon());
        int32 PickupsFound=0;
        for(TActorIterator<AColdSteelPickup> It(World); It; ++It)
        {
            if(It->GetSharedItem().Definition==TEXT("ue_m4a1") && It->GetSharedItem().Magazine==21)++PickupsFound;
        }
        TestEqual(TEXT("EjectWeaponSafely spawns world pickup fallback with preserved ammo"),PickupsFound,1);
    }

    World->DestroyWorld(false);

    // 5. Real aiming, rotated turret alignment, friendly pass-through, bullet impact & distance-culled damage numbers
    // in a standalone game world (so real Client RPCs and Blueprint monster meshes/PhysicsAssets run cleanly).
    const FString AuditProfile=TEXT("SmartTurretAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    const FString OriginalCmdLine=FCommandLine::Get();
    FCommandLine::Set(*(OriginalCmdLine+TEXT(" -ColdSteelProfile=")+AuditProfile));
    TStrongObjectPtr<UGameInstance> CombatGI(NewObject<UGameInstance>(GEngine));
    CombatGI->InitializeStandalone(TEXT("SmartTurretCombatWorld"));
    FCommandLine::Set(*OriginalCmdLine);

    if(UWorld* CombatWorld=CombatGI->GetWorld(); TestNotNull(TEXT("Standalone combat world created"),CombatWorld))
    {
        ON_SCOPE_EXIT
        {
            CombatGI->Shutdown();
            GEngine->DestroyWorldContext(CombatWorld);
            CombatWorld->DestroyWorld(false);
        };

        CombatWorld->InitializeActorsForPlay(FURL());

        auto* CombatTurret=CombatWorld->SpawnActor<AVillageSmartTurret>(FVector::ZeroVector,FRotator(0.f,35.f,0.f));
        FActorSpawnParameters UnitParams;
        UnitParams.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

        UClass* DogClass=LoadClass<AInfectedDogMonster>(nullptr,TEXT("/Game/Monsters/InfectedDog/BP_InfectedDog.BP_InfectedDog_C"));
        UClass* NurseClass=LoadClass<ANurseZombie>(nullptr,TEXT("/Game/Monsters/NurseZombie/BP_NurseZombie.BP_NurseZombie_C"));
        TestNotNull(TEXT("BP_InfectedDog loaded"),DogClass);
        TestNotNull(TEXT("BP_NurseZombie loaded"),NurseClass);

        auto* Dog=DogClass?CombatWorld->SpawnActor<AInfectedDogMonster>(DogClass,FVector(0.,1550.,62.),FRotator(0.f,-90.f,0.f),UnitParams):nullptr;
        auto* Nurse=NurseClass?CombatWorld->SpawnActor<ANurseZombie>(NurseClass,FVector(1400.,1800.,94.),FRotator(0.f,180.f,0.f),UnitParams):nullptr;
        auto* Friendly=CombatWorld->SpawnActor<AFPSGAMECharacter>(FVector(0.,800.,96.),FRotator(0.f,90.f,0.f),UnitParams);

        if(TestNotNull(TEXT("Combat rotated turret spawned"),CombatTurret)
            && TestNotNull(TEXT("Combat target dog spawned"),Dog)
            && TestNotNull(TEXT("Combat target nurse spawned"),Nurse)
            && TestNotNull(TEXT("Friendly blocker character spawned"),Friendly))
        {
            Dog->MaxHealth=600.f;
            Dog->Health=600.f;
            if(auto* DogMesh=Dog->GetMesh())
            {
                DogMesh->RefreshBoneTransforms();
                DogMesh->UpdateComponentToWorld();
                DogMesh->RecreatePhysicsState();
            }

            Nurse->MaxHealth=600.f;
            Nurse->Health=600.f;
            if(auto* NurseMesh=Nurse->GetMesh())
            {
                NurseMesh->RefreshBoneTransforms();
                NurseMesh->UpdateComponentToWorld();
                NurseMesh->RecreatePhysicsState();
            }

            auto* FriendlyHealth=Friendly->FindComponentByClass<UFPSCombatHealthComponent>();
            const float FriendlyStartHp=FriendlyHealth?FriendlyHealth->Health:100.f;

            FColdSteelItem CombatM4=SampleM4;
            CombatM4.InstanceId=TEXT("TestTurretM4_Combat");
            CombatTurret->MountedWeapon=CombatM4;
            CombatTurret->MaxAmmo=Stats0.ExpandedCapacity;
            CombatTurret->CurrentAmmo=Stats0.ExpandedCapacity;
            CombatTurret->DispatchBeginPlay();
            CombatTurret->OnRep_MountedWeapon();

            TestTrue(TEXT("Friendly pass-through treats player as friendly to turret"),
                RangedAttackQuery::IsFriendlyUnit(CombatTurret,Friendly));
            const FVector DogAim=CombatTurret->SelectTargetAimPoint(Dog,false);
            TestTrue(TEXT("SelectTargetAimPoint aims at real dog body instead of empty air (+78 cm)"),
                DogAim.Z<Dog->GetActorLocation().Z+40.f && DogAim.Z>Dog->GetActorLocation().Z-65.f);
            const FVector NurseTorso=CombatTurret->SelectTargetAimPoint(Nurse,false);
            const FVector NurseHead=CombatTurret->SelectTargetAimPoint(Nurse,true);
            TestTrue(TEXT("SelectTargetAimPoint aims Nurse head above Nurse torso for weakpoint"),
                NurseHead.Z>NurseTorso.Z);

            const FVector TurretPivot=CombatTurret->GetActorTransform().TransformPosition(FVector(0.,0.,145.));
            TestTrue(TEXT("Turret keeps LOS to enemy behind friendly character"),
                CombatTurret->HasLineOfSightToTarget(TurretPivot,DogAim,Dog));

            auto* ViewerPC=CombatWorld->SpawnActor<AFPSGAMEPlayerController>(FVector(0.,4550.,90.),FRotator::ZeroRotator,UnitParams);
            auto* ViewerPawn=CombatWorld->SpawnActor<APawn>(FVector(0.,4550.,90.),FRotator::ZeroRotator,UnitParams);
            if(ViewerPawn && !ViewerPawn->GetRootComponent())
            {
                auto* ViewerRoot=NewObject<USceneComponent>(ViewerPawn);
                ViewerPawn->SetRootComponent(ViewerRoot);
                ViewerRoot->RegisterComponent();
                ViewerPawn->SetActorLocation(FVector(0.,4550.,90.));
            }
            if(ViewerPC && ViewerPawn)
            {
                if(CombatWorld->GetNumPlayerControllers()==0)CombatWorld->AddController(ViewerPC);
                auto* Local=NewObject<ULocalPlayer>(GEngine);
                CombatGI->AddLocalPlayer(Local,FPlatformUserId::CreateFromInternalId(0));
                ViewerPC->SetPlayer(Local);
                ViewerPC->SetPawn(ViewerPawn);
                ViewerPC->SetViewTarget(ViewerPawn);
            }

            // Simulate 1.5s of tracking and automatic bursts (turret slews from 35 deg to 90 deg and fires swept rounds).
            for(int32 Step=0; Step<50; ++Step)
            {
                ++GFrameCounter;
                CombatWorld->TimeSeconds+=0.03;
                CombatTurret->Tick(0.03f);
                if(CombatTurret->Ballistics)
                    CombatTurret->Ballistics->TickComponent(0.03f,LEVELTICK_All,nullptr);
            }

            TestTrue(TEXT("Rotated turret fired and landed swept ballistics hits"),
                CombatTurret->Ballistics && CombatTurret->Ballistics->ImpactCount>0);
            TestTrue(TEXT("Turret rounds damaged target monster HP"),Dog->Health<600.f);
            if(Dog->Combat)
            {
                TestEqual(TEXT("Turret hits cause zero hit reactions/stagger"),Dog->Combat->HitReactions,0);
                TestFalse(TEXT("Turret hits do not stagger or control target"),Dog->Combat->IsControlled());
                TestFalse(TEXT("Turret hits do not stun target"),Dog->Combat->bStunned);
                TestEqual(TEXT("Turret hits cause zero toughness breaks"),Dog->Combat->Breaks,0);
                TestTrue(TEXT("Turret hits accumulate zero toughness damage"),FMath::IsNearlyZero(Dog->Combat->Toughness));
            }
            if(FriendlyHealth)
            {
                TestTrue(TEXT("Friendly player standing in line of fire took zero damage"),
                    FMath::IsNearlyEqual(FriendlyHealth->Health,FriendlyStartHp,0.01f));
            }

            if(auto* Numbers=CombatGI->GetSubsystem<UColdSteelDamageNumberSubsystem>(); Numbers && ViewerPC && ViewerPawn)
            {
                TArray<FColdSteelDamageNumberEvent> Events;
                const bool bLiveEventsDelivered=Numbers->ConsumeDamageNumbers(Events);
                TestTrue(TEXT("Live turret hits delivered damage numbers to local viewer within 65 m"),
                    bLiveEventsDelivered && !Events.IsEmpty());

                Events.Reset();
                ViewerPawn->SetActorLocation(FVector(0.,4550.,90.)); // 30 m <= 65 m limit
                VillageDefenseCombat::BroadcastDamageNumber(CombatWorld,Dog,Dog->GetActorLocation(),120.f,40.f,true,false);
                TestTrue(TEXT("Defense damage number delivered within 65 m visibility range"),
                    Numbers->ConsumeDamageNumbers(Events) && Events.Num()==1
                    && FMath::IsNearlyEqual(Events[0].Physical,80.f,0.1f)
                    && FMath::IsNearlyEqual(Events[0].Magic,40.f,0.1f)
                    && Events[0].bCritical);

                Events.Reset();
                ViewerPawn->SetActorLocation(FVector(0.,10550.,90.)); // 90 m > 65 m limit
                VillageDefenseCombat::BroadcastDamageNumber(CombatWorld,Dog,Dog->GetActorLocation(),120.f,40.f,true,false);
                TestFalse(TEXT("Defense damage number suppressed beyond 65 m visibility range"),
                    Numbers->ConsumeDamageNumbers(Events) && !Events.IsEmpty());
            }
            if(ViewerPC)CombatWorld->RemoveController(ViewerPC);
            for(AActor* ActorToEnd : {static_cast<AActor*>(ViewerPC),static_cast<AActor*>(ViewerPawn),static_cast<AActor*>(Friendly),static_cast<AActor*>(Dog),static_cast<AActor*>(Nurse),static_cast<AActor*>(CombatTurret)})
            {
                if(IsValid(ActorToEnd))
                {
                    if(ActorToEnd->HasActorBegunPlay())ActorToEnd->RouteEndPlay(EEndPlayReason::Destroyed);
                    ActorToEnd->Destroy();
                }
            }
        }
    }

    return true;
}
#endif
