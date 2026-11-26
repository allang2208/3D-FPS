// Isolated floor fixtures exercise the same advance and contact functions used by the live oil field.
namespace
{
bool CheckVillageOilSpread(UWorld& World,const FString& Dir)
{
    auto* Cube=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
    const auto Slab=[&](FVector Pos,FVector Size,FRotator Facing)
    {
        auto* A=World.SpawnActor<AStaticMeshActor>();
        A->SetMobility(EComponentMobility::Movable);A->GetStaticMeshComponent()->SetStaticMesh(Cube);
        A->SetActorScale3D(Size/100.);A->SetActorLocationAndRotation(Pos,Facing);return A;
    };
    auto* Cursor=World.SpawnActor<AStaticMeshActor>();Cursor->SetMobility(EComponentMobility::Movable);
    auto* Holder=World.SpawnActor<AActor>();auto* Surface=NewObject<UDynamicMeshComponent>(Holder);
    Holder->AddInstanceComponent(Surface);Surface->SetCollisionEnabled(ECollisionEnabled::NoCollision);Surface->RegisterComponent();
    auto Survey=[&](FVillageOilSpread& Sheet,FVector P)
    {
        Cursor->SetActorLocation(P);World.GetPhysicsScene()->EnsureCollisionTreeIsBuilt(&World);
        while(Sheet.Built<Sheet.Half)Sheet.Grow(*Cursor,P+FVector(0,-300,160),3.f,Surface);
    };
    const FVector Flat(7200,1000,0);Slab(Flat-FVector(0,0,15),FVector(1500,1500,30),FRotator::ZeroRotator);
    FVillageOilSpread Free;Survey(Free,Flat);
    FString Rows=TEXT("age,sampled_wet_square_metres\n");int Prev=-1,First=0,Last=0;bool OK=true;
    for(float Age:{.05f,.25f,.6f,1.f,1.6f,2.5f,4.f})
    {
        int N=0;
        for(int Y=-500;Y<=500;Y+=10)for(int X=-500;X<=500;X+=10)if(Free.WetAt(FVector(X,Y,0),Age))++N;
        Rows+=FString::Printf(TEXT("%.3f,%.3f\n"),Age,N*.01);
        OK&=N>=Prev;if(Prev<0)First=N;Prev=N;Last=N;
    }
    OK&=First>0 && Last>First*10 && !Free.WetAt(FVector(180,0,0),.1f) && Free.WetAt(FVector(180,0,0),3.f);
    OK&=!Free.WetAt(FVector(501,0,0),4.f) && !Free.WetAt(FVector(0,0,100),4.f);
    FFileHelper::SaveStringToFile(Rows,*(Dir/TEXT("wet-area.csv")));
    const FVector Hill(10400,1000,0);const FRotator Tilt(-12,0,0);
    Slab(Hill-Tilt.RotateVector(FVector(0,0,15)),FVector(1450,1450,30),Tilt);
    FVillageOilSpread Inclined;Survey(Inclined,Hill);
    const double Run=4*Free.Step;
    const auto Arrival=[&](const FVillageOilSpread& S,FVector At)
    {for(int I=0;I<=400;++I)if(S.WetAt(At,I*.01f))return I*.01;return 99.;};
    const double Down=Arrival(Inclined,FVector(Run,0,-Run*.21255656)),Up=Arrival(Inclined,FVector(-Run,0,Run*.21255656));
    double Litres=0.;for(const auto& C:Inclined.Cells)Litres+=C.FilmMM*.1*Inclined.Step*Inclined.Step/1000.;
    OK&=FMath::Abs(Litres-2.3)<.002;
    const bool Grade=Down<Up && Up<4.;OK&=Grade;
    auto* Barrier=Slab(Flat+FVector(100,0,95),FVector(28,1200,190),FRotator::ZeroRotator);
    FVillageOilSpread Closed;Survey(Closed,Flat);
    const bool Wall=!Closed.WetAt(FVector(200,0,0),6);
    const bool Shore=Closed.WetAt(FVector(84,0,0),6) && !Closed.WetAt(FVector(96,0,0),6);
    OK&=Wall && Shore;
    Barrier->SetActorScale3D(FVector(.28,1.60,1.90));
    FVillageOilSpread Around;Survey(Around,Flat);
    const double ClearTime=Arrival(Free,FVector(200,0,0)),AroundTime=Arrival(Around,FVector(200,0,0));
    const bool Detour=AroundTime<6 && AroundTime>ClearTime+.05;OK&=Detour;
    UE_LOG(LogTemp,Display,TEXT("OIL_FLOW success=%d flat_early_m2=%.2f mature_m2=%.2f down_s=%.2f up_s=%.2f wall=%d shore=%d clear_s=%.2f detour_s=%.2f retained_litres=%.4f"),OK,First*.01,Last*.01,Down,Up,Wall,Shore,ClearTime,AroundTime,Litres);
    return OK;
}
}