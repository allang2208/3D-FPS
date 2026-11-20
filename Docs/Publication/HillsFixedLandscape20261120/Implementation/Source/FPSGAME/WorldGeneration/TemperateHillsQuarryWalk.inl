// Opt-in Development walk. Only the space between stations enters frames.csv.
struct FQuarryWalk : FWalk
{
    struct FStation { FVector2D At,Look; const TCHAR* LegName; const TCHAR* Photo; double LookHeight; };
    TArray<FStation> RoutePoints;
    TArray<FVector> DryEye;
    TArray<FRotator> DryAim;
    TemperateRiver::FPlan::FWhiteCliffs Quarry;
    bool VisitIssued=false,Registered=false,bReferenceCamera=false;
    int32 StableFrames=0;
    double ReadyAt=0.;
    FVector2D LastXY;
    FString Poses=TEXT("lap,site,eye_x,eye_y,eye_z,pitch,yaw,roll,fov,wetness,rain,hour\n");
    FString ContactRows=TEXT("station,mesh,instance,world_x,world_y,world_z,min_sample_gap_cm,valid_samples\n");
    TMap<UStaticMesh*,TArray<FVector>> Supports;
    TSet<FString> ContactsSeen;
    bool Compose()
    {
        auto Add=[&](double X,double Y,const TCHAR* Segment,const TCHAR* Photo=nullptr,double LX=0.,double LY=0.,double Up=0.)
        {RoutePoints.Add({Quarry.World(X,Y),Quarry.World(LX,LY),Segment,Photo,Up});};
        using namespace TemperateQuarry;
        Add(RoadX(EntryY),EntryY,TEXT("entry"),TEXT("01_entry"),EntryLook.X,EntryLook.Y);
        Add(RoadX(ShedJunction),ShedJunction,TEXT("shed"));
        Add(ShedElbow.X,ShedElbow.Y,TEXT("shed"));
        Add(-685,-1915,TEXT("shed"),TEXT("02_shed"),Shed.X,Shed.Y,100);
        Add(ShedElbow.X,ShedElbow.Y,TEXT("hoist"));
        Add(RoadX(HoistJunction),HoistJunction,TEXT("hoist"));
        Add(HoistElbow.X,HoistElbow.Y,TEXT("hoist"));
        Add(635,-1660,TEXT("hoist"),TEXT("03_hoist"),Hoist.X,Hoist.Y,200);
        Add(HoistElbow.X,HoistElbow.Y,TEXT("face"));
        Add(RoadX(-1720.),-1720,TEXT("face"));
        Add(RoadX(-580.),-580,TEXT("face"));
        Add(RoadX(100.),100,TEXT("face"));
        Add(-835,150,TEXT("face"),TEXT("04_face"),-1850,465,580);
        Add(-945,20,TEXT("toe"),TEXT("05_toe"),-1530,200,30);
        if(FParse::Param(FCommandLine::Get(),TEXT("QuarryUpperRoad")))
        {
            Add(RoadX(210.),210,TEXT("upper"));
            Add(RoadX(910.),910,TEXT("upper"));
            Add(RoadX(1520.),1520,TEXT("upper"),TEXT("06_bend"),610,2080,25);
            Add(RoadX(2330.),2330,TEXT("upper"));
            Add(RoadX(2930.),2930,TEXT("upper"));
            Add(RoadX(3530.),3530,TEXT("upper"),TEXT("07_upper"),510,2840,40);
        }
        DryEye.SetNum(RoutePoints.Num());DryAim.SetNum(RoutePoints.Num());
        const FString Meta=FString::Printf(TEXT("seed=%d\nworld=%s\ncenter=%s\naxis=%s\n"),
            Hills->Seed,*Hills->WorldId.ToString(),*Quarry.Center.ToString(),*Quarry.Axis.ToString());
        FFileHelper::SaveStringToFile(Meta,*(Out/TEXT("world.txt")));
        FString Directory;
        if(!FParse::Value(FCommandLine::Get(),TEXT("HillsLandscapeInput="),Directory))return true;
        FString ReferenceWorld;
        TArray<FString> Rows;
        if(!FFileHelper::LoadFileToString(ReferenceWorld,*(Directory/TEXT("world.txt"))) ||
           ReferenceWorld.TrimStartAndEnd()!=Meta.TrimStartAndEnd() ||
           !FFileHelper::LoadFileToStringArray(Rows,*(Directory/TEXT("poses.csv"))))return false;
        for(int32 I=0;I<RoutePoints.Num();++I)
        {
            if(!RoutePoints[I].Photo)continue;
            const FString Prefix=FString::Printf(TEXT("0,%s,"),RoutePoints[I].Photo);
            const FString* Row=Rows.FindByPredicate([&](const FString& R){return R.StartsWith(Prefix);});
            TArray<FString> Fields;
            if(!Row || Row->ParseIntoArray(Fields,TEXT(","),false)!=12)return false;
            DryEye[I]=FVector(FCString::Atod(*Fields[2]),FCString::Atod(*Fields[3]),FCString::Atod(*Fields[4]));
            DryAim[I]=FRotator(FCString::Atod(*Fields[5]),FCString::Atod(*Fields[6]),FCString::Atod(*Fields[7]));
        }
        bReferenceCamera=true;return true;
    }
    void ContactSurvey(const FStation& S)
    {
#if WITH_EDITOR
        TInlineComponentArray<UInstancedStaticMeshComponent*> Parts(Hills.Get());
        TArray<UInstancedStaticMeshComponent*,TInlineAllocator<2>> Caps;
        for(auto* Part:Parts)
            if(Part->ComponentHasTag(TEXT("HillsQuarryRimSupport")))Caps.Add(Part);
        FCollisionQueryParams SupportQuery(SCENE_QUERY_STAT(QuarryRimContact),true);
        for(auto* Part:Parts)
        {
            if(!Part->ComponentHasTag(TEXT("HillsWhiteCliffs"))&&!Part->ComponentHasTag(TEXT("HillsQuarryChips"))&&
               !Part->ComponentHasTag(TEXT("HillsQuarryVerge")))continue;
            UStaticMesh* Mesh=Part->GetStaticMesh();if(!Mesh)continue;
            for(int32 I=0;I<Part->GetInstanceCount();++I)
            {
                FTransform T;Part->GetInstanceTransform(I,T,true);
                const FVector P=T.GetLocation();
                if(FVector2D::Distance(FVector2D(P),S.Look)>2250.)continue;
                const FString ID=Mesh->GetName()+FString::FromInt(I);if(ContactsSeen.Contains(ID))continue;
                auto& Points=Supports.FindOrAdd(Mesh);
                if(Points.IsEmpty())
                {
                    const FMeshDescription* Desc=Mesh->GetMeshDescription(0);if(!Desc)continue;
                    const auto Position=FStaticMeshConstAttributes(*Desc).GetVertexPositions();
                    const FBox B=HillsVegetation::BoundsOf(Mesh);
                    FVector Low[36];for(auto& V:Low)V=FVector(0,0,DBL_MAX);
                    for(const FVertexID V:Desc->Vertices().GetElementIDs())
                    {
                        const FVector At(Position[V]);
                        const FVector U=(At-B.Min)/B.GetSize().ComponentMax(FVector(1));
                        const int32 Bin=FMath::Clamp(int(U.X*6),0,5)+6*FMath::Clamp(int(U.Y*6),0,5);
                        if(At.Z<Low[Bin].Z)Low[Bin]=At;
                    }
                    for(auto& V:Low)if(V.Z<DBL_MAX)Points.Add(V);
                }
                double Gap=DBL_MAX;int32 N=0;
                for(const auto& V:Points)
                {
                    const FVector At=T.TransformPosition(V);FHitResult Hit;
                    bool bHit=HillsLandscapeCapture::GroundHit(Hills.Get(),FVector2D(At),Hit);
                    double SupportZ=bHit?Hit.ImpactPoint.Z:-DBL_MAX;
                    if(Part->ComponentHasTag(TEXT("HillsQuarryVerge")) && At.Z-SupportZ>2.)
                    {
                        for(auto* Cap:Caps)
                        {
                            if(!Cap->Bounds.GetBox().IsInsideOrOnXY(At))continue;
                            if(Cap->LineTraceComponent(Hit,At+FVector(0,0,45.),At-FVector(0,0,1800.),SupportQuery))
                            {SupportZ=FMath::Max(SupportZ,Hit.ImpactPoint.Z);bHit=true;}
                        }
                    }
                    if(bHit){Gap=FMath::Min(Gap,At.Z-SupportZ);++N;}
                }
                if(N)
                {
                    ContactsSeen.Add(ID);
                    ContactRows+=FString::Printf(TEXT("%s,%s,%d,%.2f,%.2f,%.2f,%.3f,%d\n"),S.Photo,*Mesh->GetName(),I,P.X,P.Y,P.Z,Gap,N);
                }
            }
        }
        FFileHelper::SaveStringToFile(ContactRows,*(Out/TEXT("contacts.csv")));
#endif
    }
    void PhotoStop(APlayerController* PC,ACharacter* C,double Now)
    {
        Forward(PC,false);
        auto* Move=C->GetCharacterMovement();
        Move->StopMovementImmediately();Move->DisableMovement();
        FHitResult Hit;
        if(HillsLandscapeCapture::GroundHit(Hills.Get(),RoutePoints[Leg].At,Hit))
            C->SetActorLocation(Hit.ImpactPoint+FVector(0,0,C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.));
        PC->SetViewTarget(C);
        Requested=Registered=false;ReadyAt=0;StableFrames=0;Enter(EStage::Photograph,Now);
    }
    void StartLeg(ACharacter* C,double Now)
    {
        ++Leg;Best=DBL_MAX;LastProgress=Now;LastXY=FVector2D(C->GetActorLocation());
        C->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
        Enter(EStage::Walk,Now);
    }
    bool TickQuarry(float)
    {
        const double Now=FPlatformTime::Seconds();
        if(!World.IsValid()||Now-Began>2800.)return Finish(TEXT("quarry walk timeout"),false);
        auto* PC=World->GetFirstPlayerController();auto* C=PC?Cast<ACharacter>(PC->GetPawn()):nullptr;
        if(!C)return true;
        if(Stage==EStage::Boot)
        {
            if(Now<NextPoll)return true;NextPoll=Now+1;
            for(TActorIterator<ATemperateHillsWorld> It(World.Get());It;++It)Hills=*It;
            for(TActorIterator<AFPSWeatherManager> It(World.Get());It;++It)Weather=*It;
            if(!Hills.IsValid()||!Hills->bReady||!Weather.IsValid()||PC->IsMoveInputIgnored())return true;
            TemperateHillsGround::FMapSource Map;Hills->CopyMapGround(Map);
            if(!Map.River||!Map.River->WhiteCliffs.Valid)return Finish(TEXT("saved world has no quarry"),false);
            Quarry=Map.River->WhiteCliffs;
            if(!Compose())return Finish(TEXT("quarry reference world or photo stations do not match"),false);
            C->SetCanBeDamaged(false);
            Weather->RealSecondsPerGameDay=864000.f;
            Weather->AdvanceGameTime(FMath::Fmod(10.5f-24.f*Weather->NormalizedDayTime+24.f,24.f)+.0001f);
            Weather->SetWeatherState(EFPSWeatherState::Clear);
            Enter(EStage::Settle,Now);return true;
        }
        const double Wet=Weather->GetSurfaceWetness(),Rain=Weather->GetEffectiveRainIntensity();
        if(Now>NextStatus)
        {
            NextStatus=Now+15.;
            UE_LOG(LogTemp,Display,TEXT("QUARRY_WALK stage=%d lap=%d leg=%d wet=%.3f rain=%.3f pos=%s"),
                int32(Stage),Lap,Leg,Wet,Rain,*C->GetActorLocation().ToCompactString());
        }
        if(Stage==EStage::Settle||Stage==EStage::Soak)
        {
            if(Now<NextPoll)return true;NextPoll=Now+.65;
            if(!VisitIssued)
            {
                FString Reason;VisitIssued=Hills->RequestQuarryVisit(C,Reason);
                if(VisitIssued)UE_LOG(LogTemp,Display,TEXT("QUARRY_WALK requested normal entrance lap=%d"),Lap);
                return true;
            }
            if(FVector2D::Distance(FVector2D(C->GetActorLocation()),RoutePoints[0].At)>750.)return true;
            if(Stage==EStage::Soak)
            {
                if(Wet<.98)return true;
                Weather->SetWeatherState(EFPSWeatherState::Cloudy);Enter(EStage::Settle,Now);return true;
            }
            if(Now-Since<3. || Rain>.015 || (!Lap&&Wet>.035))return true;
            if(!HillsLandscapeCapture::Readiness(Hills.Get(),C->GetActorLocation(),C->GetActorLocation(),3800.).Complete())return true;
            PhotoStop(PC,C,Now);return true;
        }
        const auto& S=RoutePoints[Leg];
        if(Stage==EStage::Photograph)
        {
            if(Lap||bReferenceCamera)PC->SetControlRotation(DryAim[Leg]);
            else if(!Leg)PC->SetControlRotation(FRotator(TemperateQuarry::EntryPitch,FVector(S.Look-S.At,0.).Rotation().Yaw,0));
            else Aim(PC,Ground(S.Look,S.LookHeight));
            if(!ReadyAt)
            {
                if(Now<NextPoll)return true;NextPoll=Now+.7;
                const auto Ready=HillsLandscapeCapture::Readiness(Hills.Get(),C->GetActorLocation(),C->GetActorLocation(),3200.);
                if(!Ready.Complete())return true;
                if(Lap&&Wet<.55&&!Registered){Weather->SetWeatherState(EFPSWeatherState::Rain);Registered=true;}
                if(Registered){if(Wet<.98)return true;Weather->SetWeatherState(EFPSWeatherState::Cloudy);Registered=false;}
                if(Rain>.015)return true;
                ReadyAt=Now;
            }
            FVector Eye;FRotator R;PC->GetPlayerViewPoint(Eye,R);
            if((Lap||bReferenceCamera)&&!Requested&&(DryEye[Leg]-Eye).Size()>.15)
            {
                C->SetActorLocation(C->GetActorLocation()+DryEye[Leg]-Eye,false,nullptr,ETeleportType::TeleportPhysics);
                StableFrames=0;return true;
            }
            if(++StableFrames<8||Now-ReadyAt<2.)return true;
            if(!Requested)
            {
                if(!Lap&&!bReferenceCamera){DryEye[Leg]=Eye;DryAim[Leg]=R;}
                Poses+=FString::Printf(TEXT("%d,%s,%.4f,%.4f,%.4f,%.5f,%.5f,%.5f,%.3f,%.4f,%.4f,%.4f\n"),
                    Lap,S.Photo,Eye.X,Eye.Y,Eye.Z,R.Pitch,R.Yaw,R.Roll,PC->PlayerCameraManager->GetFOVAngle(),Wet,Rain,Weather->NormalizedDayTime*24);
                Shot=Out/FString::Printf(TEXT("%s_%s.png"),Lap?TEXT("wet"):TEXT("dry"),S.Photo);
                FScreenshotRequest::RequestScreenshot(Shot,false,false);Requested=true;return true;
            }
            if(IFileManager::Get().FileSize(*Shot)<=0)return true;
            if(!Lap)ContactSurvey(S);
            FFileHelper::SaveStringToFile(Poses,*(Out/TEXT("poses.csv")));Save();
            if(Leg+1<RoutePoints.Num()){StartLeg(C,Now);return true;}
            if(Lap)return Finish(TEXT("quarry clear and post-rain walks complete"),true);
            Lap=1;Leg=0;VisitIssued=false;
            Weather->SetWeatherState(EFPSWeatherState::Rain);Enter(EStage::Soak,Now);return true;
        }
        const FVector P=C->GetActorLocation();const FVector2D XY(P),Delta=S.At-XY;
        if(Previous>0.)Frames+=FString::Printf(TEXT("%d,%s,%.4f,%.3f,%.3f,%.3f,%.2f,%.2f,%.2f,%.4f,%.4f\n"),
            Lap,S.LegName,1000.*(Now-Previous),FPlatformTime::ToMilliseconds(GGameThreadTime),
            FPlatformTime::ToMilliseconds(GRenderThreadTime),FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles(0)),
            P.X,P.Y,P.Z,Wet,Rain);
        Previous=Now;
        const FVector2D Step=XY-LastXY;
        const double T=FMath::Clamp(FVector2D::DotProduct(S.At-LastXY,Step)/FMath::Max(1.,Step.SizeSquared()),0.,1.);
        const bool AtStation=FVector2D::DistSquared(LastXY+T*Step,S.At)<65.*65.;
        LastXY=XY;
        if(AtStation)
        {
            if(S.Photo)PhotoStop(PC,C,Now);
            else {++Leg;Best=DBL_MAX;LastProgress=Now;}
            return true;
        }
        if(Delta.Size()<Best-10.){Best=Delta.Size();LastProgress=Now;}
        if(Now-LastProgress>24.){Forward(PC,false);return Finish(TEXT("quarry route blocked"),false);}
        PC->SetControlRotation(FVector(Delta,0.).Rotation());Forward(PC,true);return true;
    }
};
FAutoConsoleCommandWithWorld QuarryWalkCommand(TEXT("fps.Test.HillsQuarryWalk"),TEXT("Walk and photograph the four quarry stations."),
    FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* W)
    {
        if(!W||!W->IsGameWorld()||!FParse::Param(FCommandLine::Get(),TEXT("HillsQuarryWalk")))return;
        auto Walk=MakeShared<FQuarryWalk>();Walk->World=W;
        if(!FParse::Value(FCommandLine::Get(),TEXT("HillsLandscapeOutput="),Walk->Out))return;
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Walk](float Dt){return Walk->TickQuarry(Dt);}));
    }));
