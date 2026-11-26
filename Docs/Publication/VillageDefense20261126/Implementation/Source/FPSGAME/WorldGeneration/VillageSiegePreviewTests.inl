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
        Offset->SetPropertyValue_InContainer(Clock,106.08f);
        TestTrue(TEXT("stone half loaded after five seconds"),Engine->GetReloadProgress(Fraction) && FMath::IsNearlyEqual(Fraction,.5f,.001f));
        TestTrue(TEXT("firing gate uses the same clock"),FMath::IsNearlyEqual(Engine->ReloadRemaining(),5.,.001));
        Offset->SetPropertyValue_InContainer(Clock,111.09f);
        TestTrue(TEXT("ready and complete together"),Engine->ReloadRemaining()==0. && Engine->GetReloadProgress(Fraction) && Fraction==1.f);
        Offset->SetPropertyValue_InContainer(Clock,112.f);
        TestFalse(TEXT("complete hint clears"),Engine->GetReloadProgress(Fraction));
        Engine->bStone=false;
        Offset->SetPropertyValue_InContainer(Clock,102.215f);
        TestTrue(TEXT("ballista keeps its original reload"),Engine->GetReloadProgress(Fraction) && FMath::IsNearlyEqual(Fraction,.5f,.001f));
    }
    World->SetGameState(nullptr);
    World->DestroyWorld(false);
    return true;
}
#endif
