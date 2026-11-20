// Included inside HillsRouteWalk, using the village walk's real pawn input,
// GPU frame clock and offscreen-process cleanup.
struct FShoreSite
{
    FString Name;
    TArray<FVector2D> Path;
    FVector Detail, Vista;
    FVector ReferenceEye[2];
    FRotator ReferenceRotation[2];
    double Form = 0.;
};

struct FShoreWalk : FWalk
{
    TArray<FShoreSite> Sites;
    int32 SiteIndex=0, Photo=0;
    int32 InnerPasses=0,InnerPass=0;
    double ReadyAt=0., DetourUntil=0.;
    int32 Detours=0;
    FVector2D Dodge;
    FVector2D LastFoot;
    int32 FramesWithoutApproach=0;
    bool RefreshRain=false;
    bool bReference=false,bEyeAligned=false;
    double NextReadinessLog=0.;
    FString Poses=TEXT("lap,site,view,x,y,z,pitch,yaw,roll,fov,wetness,rain\n");
    FString Survey=TEXT("site,node,x,y,ground,edge,form\n");
    FString Contacts=TEXT("site,mesh,x,y,min_bound_z,highest_probe_z,gap_cm\n");
    FString DesignedContacts=TEXT("site,layer,mesh,candidate,x,y,width_cm,edge_cm,above_water_cm\n");

    // A conservative screen for completely suspended rocks. Sample the actual
    // terrain collision around each rendered instance, after movement and photos.
    void RecordContacts(const FShoreSite& Site)
    {
        const bool bOutlet=Site.Name==TEXT("lake_cove") && Hills->Seed==TemperateRiver::LakeShoreDetail::SurveySeed;
        const auto OutletXY=TemperateRiver::LakeShoreDetail::Cove.Point(1250.,370.);
        const FVector OutletCenter=bOutlet?Ground(OutletXY,20.):FVector::ZeroVector;
        FString OutletContacts=TEXT("mesh,x,y,edge_cm,silt,gravel,stone,grass,gap_cm\n");
        const FBox Window(Site.Detail-FVector(550.,550.,10000.),Site.Detail+FVector(550.,550.,10000.));
        for(int32 Layer:{1,3})
        {
            TArray<FTemperatePlacement> Items;
            Hills->GetPlacements(Layer,Window,Items);
            for(const auto& P:Items)
            {
                if(Layer==3 && (P.CandidateId>>56)!=0x74)continue;
                const FBox Local=HillsVegetation::BoundsOf(P.Mesh.ResolveObject());
                if(!Local.IsValid)continue;
                const FBox Box=Local.TransformBy(P.Transform);
                const FVector At=Box.GetCenter();
                const auto Water=Hills->SampleRiver(At.X,At.Y);
                DesignedContacts+=FString::Printf(TEXT("%s,%d,%s,%016llx,%.1f,%.1f,%.1f,%.1f,%.1f\n"),
                    *Site.Name,Layer,*P.Mesh.GetAssetName(),P.CandidateId,At.X,At.Y,
                    FMath::Max(Box.GetSize().X,Box.GetSize().Y),Water.Distance-Water.HalfWidth,Hills->Height(At.X,At.Y)-Water.WaterZ);
            }
        }
        FFileHelper::SaveStringToFile(DesignedContacts,*(Out/TEXT("designed-contacts.csv")));
        for(TObjectIterator<UInstancedStaticMeshComponent> It;It;++It)
        {
            if(It->GetWorld()!=World.Get()||!It->IsRegistered()||!It->IsVisible())continue;
            const UStaticMesh* Mesh=It->GetStaticMesh();if(!Mesh)continue;
            const auto Has=[Mesh](const auto& Family)
            {return Family.ContainsByPredicate([Mesh](const auto& Ref){return Ref.Get()==Mesh;});};
            const bool bStone=Has(Hills->Assets->RiverRocks)||Has(Hills->Assets->RiverPebbles)||Has(Hills->Assets->Rocks);
            if(!bStone&&(!bOutlet||(!Has(Hills->Assets->Grass)&&!Has(Hills->Assets->RainforestCarpetGrass)&&!Has(Hills->Assets->RiverGroundCover))))continue;
            const FBox Local=HillsVegetation::BoundsOf(Mesh);
            for(int32 Instance:It->GetInstancesOverlappingSphere(bOutlet?OutletCenter:Site.Detail,bOutlet?2280.f:550.f,true))
            {
                FTransform T;if(!It->GetInstanceTransform(Instance,T,true))continue;
                const FBox Box=Local.TransformBy(T);
                const FVector Mid=Box.GetCenter(),Half=Box.GetExtent();
                const bool bNearDetail=bStone&&Box.ComputeSquaredDistanceToPoint(Site.Detail)<=550.*550.;
                const double SignedEdge=bOutlet?Edge(FVector2D(Mid)):0.;
                const auto Deposit=TemperateRiver::LakeShoreDetail::CoveOutlet::Sample(Mid.X,Mid.Y,Hills->Seed,SignedEdge);
                const bool bInOutlet=bOutlet&&FMath::Max(FMath::Max3(Deposit.Silt,Deposit.Gravel,Deposit.Stones),Deposit.Grass)>.12;
                if(!bNearDetail&&!bInOutlet)continue;
                double Surface=-DBL_MAX;
                for(int32 J=-1;J<=1;++J)for(int32 I=-1;I<=1;++I)
                {
                    FHitResult Hit;
                    if(HillsLandscapeCapture::GroundHit(Hills.Get(),{Mid.X+.9*I*Half.X,Mid.Y+.9*J*Half.Y},Hit))
                        Surface=FMath::Max(Surface,Hit.ImpactPoint.Z);
                }
                if(bNearDetail&&Surface>-DBL_MAX)Contacts+=FString::Printf(TEXT("%s,%s,%.1f,%.1f,%.2f,%.2f,%.2f\n"),
                    *Site.Name,*Mesh->GetName(),Mid.X,Mid.Y,Box.Min.Z,Surface,Box.Min.Z-Surface);
                if(bInOutlet&&Surface>-DBL_MAX)OutletContacts+=FString::Printf(TEXT("%s,%.1f,%.1f,%.1f,%.2f,%.2f,%.2f,%.2f,%.2f\n"),
                    *Mesh->GetName(),Mid.X,Mid.Y,SignedEdge,Deposit.Silt,Deposit.Gravel,Deposit.Stones,Deposit.Grass,Box.Min.Z-Surface);
            }
        }
        FFileHelper::SaveStringToFile(Contacts,*(Out/TEXT("contacts.csv")));
        if(bOutlet)FFileHelper::SaveStringToFile(OutletContacts,*(Out/TEXT("outlet-contacts.csv")));
    }

    double Edge(FVector2D P) const
    {
        const auto S=Hills->SampleRiver(P.X,P.Y);
        return S.Distance-S.HalfWidth;
    }
    FVector2D Normal(FVector2D P) const
    {
        return FVector2D(Edge(P+FVector2D(45.,0.))-Edge(P-FVector2D(45.,0.)),
            Edge(P+FVector2D(0.,45.))-Edge(P-FVector2D(0.,45.))).GetSafeNormal();
    }
    FVector2D Offset(FVector2D P,double Distance) const
    {
        for(int32 I=0;I<4;++I)
        {
            const double Error=Distance-Edge(P);
            if(FMath::Abs(Error)<4.)break;
            P+=Normal(P)*FMath::Clamp(Error,-600.,600.);
        }
        return P;
    }
    bool Compose()
    {
        TemperateHillsGround::FMapSource Map;
        Hills->CopyMapGround(Map);
        if(!Map.River||!Map.River->Lake.Valid)return false;
        const auto& Plan=*Map.River;
        const auto& Lake=Plan.Lake;
        FVector2D Landmarks[4];
        double Form[4]={-1.,-1.,-1.,-1.};
        double BestBend=-1.,BestLake[2]={-1.,-1.};
        for(const auto& P:Plan.Points)
        {
            if(P.Distance<5500.||P.Distance>Plan.Points.Last().Distance-4000.||
                Lake.Edge(P.XY.X,P.XY.Y)<5000.||Plan.Protection(P.XY.X,P.XY.Y)>.1)continue;
            const double Sign=P.Bend>=0.?1.:-1.;
            const auto Left=P.XY+P.Side*P.LeftWidth,Right=P.XY-P.Side*P.RightWidth;
            const double Half=Hills->SizeMeters*50.-5000.;
            if(FMath::Max(FMath::Abs(P.XY.X),FMath::Abs(P.XY.Y))>Half)continue;
            const double Score=FMath::Abs(P.Bend)+.07*FMath::Min(P.LeftWidth,P.RightWidth)/800.;
            if(Score<=BestBend)continue;
            BestBend=Score;Landmarks[0]=Sign>0?Left:Right;Landmarks[1]=Sign>0?Right:Left;
            Form[0]=FMath::Abs(P.Bend);Form[1]=-Form[0];
        }
        const FVector2D Side(-Lake.Axis.Y,Lake.Axis.X);
        for(int32 I=0;I<160;++I)
        {
            const double A=2.*PI*I/160.;
            const FVector2D D=Lake.Axis*(FMath::Cos(A)*Lake.RadiusX)+Side*(FMath::Sin(A)*Lake.RadiusY);
            double Lo=.35,Hi=1.65;
            for(int32 J=0;J<17;++J)
            {
                const double R=(Lo+Hi)*.5;const auto P=Lake.Center+D*R;
                if(Lake.Edge(P.X,P.Y)<0.)Lo=R;else Hi=R;
            }
            const auto P=Lake.Center+D*((Lo+Hi)*.5);
            if(!Hills->SampleRiver(P.X,P.Y).bLake)continue;
            bool Mouth=false;
            for(const auto& M:Lake.RiverMouths)Mouth|=(M-P).Size()<3600.;
            if(Mouth)continue;
            const auto S=Lake.Shore(P.X,P.Y);
            for(int32 J=0;J<2;++J)
            {
                const double Weight=J?S.Rock:S.Beach;
                const double Score=Weight-.15*(J?S.Beach:S.Rock);
                if(Score>BestLake[J]){BestLake[J]=Score;Form[2+J]=Weight;Landmarks[2+J]=P;}
            }
        }
        if(BestBend<0.||BestLake[0]<=0.||BestLake[1]<=0.)return false;
        const TCHAR* Names[]={TEXT("river_inner"),TEXT("river_outer"),TEXT("lake_cove"),TEXT("lake_headland")};
        for(int32 I=0;I<4;++I)
        {
            auto& Site=Sites.AddDefaulted_GetRef();Site.Name=Names[I];Site.Form=Form[I];
            FVector2D Mark=Landmarks[I];
            TArray<FTemperatePlacement> Rocks;
            const FVector M(Mark,0.);
            Hills->GetPlacements(1,FBox(M-FVector(1350.,1350.,100000.),M+FVector(1350.,1350.,100000.)),Rocks);
            double BestRock=DBL_MAX;
            for(const auto& R:Rocks)
            {
                if(!R.Mesh.GetAssetName().Contains(TEXT("NordicRiver")))continue;
                const FVector2D At(R.Transform.GetLocation());
                const auto S=Hills->SampleRiver(At.X,At.Y);
                const double E=S.Distance-S.HalfWidth;
                if(S.bLake!=(I>=2)||E< -95.||E>240.||
                    (I<2&&S.Bend*FMath::Sign(S.SignedDistance)*(I==0?1.:-1.)<.15))continue;
                const double D=(At-Landmarks[I]).Size();
                if(D<BestRock){BestRock=D;Mark=At;}
            }
            const auto N=Normal(Mark);
            if(N.IsNearlyZero())return false;
            const FVector2D T(-N.Y,N.X);
            Site.Detail=Ground(Mark,18.);
            Site.Vista=Ground(Offset(Mark+T*960.,5.),35.);
            auto P=Offset(Mark-T*320.,335.);
            Site.Path.Add(P);
            for(int32 K=0;K<6;++K)
            {
                const auto U=Normal(P);
                P=Offset(P-FVector2D(-U.Y,U.X)*470.,K<2?390.:480.);
                Site.Path.Insert(P,0);
            }
            for(int32 K=0;K<Site.Path.Num();++K)
            {
                const auto XY=Site.Path[K];
                Survey+=FString::Printf(TEXT("%s,%d,%.2f,%.2f,%.2f,%.2f,%.4f\n"),*Site.Name,K,
                    XY.X,XY.Y,Hills->Height(XY.X,XY.Y),Edge(XY),Site.Form);
            }
        }
        FString Reference;
        if(FParse::Value(FCommandLine::Get(),TEXT("HillsLandscapeInput="),Reference))
        {
            if(!LoadReference(Reference))return false;
            bReference=true;
        }
        FFileHelper::SaveStringToFile(Survey,*(Out/TEXT("routes.csv")));
        UE_LOG(LogTemp,Display,TEXT("SHORE_WALK world=%s seed=%d"),*Hills->WorldId.ToString(),Hills->Seed);
        return true;
    }
    bool LoadReference(const FString& Directory)
    {
        // A landform edit can change the shoreline normal and auto-selected
        // survey point. Replay the measured world locations and real pawn views.
        TArray<FString> Routes,Views,ContactsIn,Fields;
        if(!FFileHelper::LoadFileToStringArray(Routes,*(Directory/TEXT("routes.csv"))) ||
           !FFileHelper::LoadFileToStringArray(Views,*(Directory/TEXT("poses.csv"))))return false;
        FFileHelper::LoadFileToStringArray(ContactsIn,*(Directory/TEXT("designed-contacts.csv")));
        FString ReplaySurvey=Survey.Left(Survey.Find(TEXT("\n"))+1);
        for(auto& Site:Sites)
        {
            TArray<FVector2D> Path;
            for(const FString& Row:Routes)
            {
                Row.ParseIntoArray(Fields,TEXT(","),false);
                if(Fields.Num()!=7 || Fields[0]!=Site.Name)continue;
                if(FCString::Atoi(*Fields[1])!=Path.Num())return false;
                const FVector2D XY(FCString::Atod(*Fields[2]),FCString::Atod(*Fields[3]));
                Path.Add(XY);
                ReplaySurvey+=FString::Printf(TEXT("%s,%d,%.2f,%.2f,%.2f,%.2f,%.4f\n"),
                    *Site.Name,Path.Num()-1,XY.X,XY.Y,Hills->Height(XY.X,XY.Y),Edge(XY),Site.Form);
            }
            if(Path.Num()!=Site.Path.Num())return false;
            Site.Path=MoveTemp(Path);
            uint8 Mask=0;
            for(const FString& Row:Views)
            {
                Row.ParseIntoArray(Fields,TEXT(","),false);
                if(Fields.Num()!=12 || Fields[0]!=TEXT("0") || Fields[1]!=Site.Name)continue;
                const int32 View=Fields[2]==TEXT("bank")?0:Fields[2]==TEXT("detail")?1:INDEX_NONE;
                if(View==INDEX_NONE || (Mask&(1<<View)))return false;
                Mask|=1<<View;
                Site.ReferenceEye[View]=FVector(FCString::Atod(*Fields[3]),FCString::Atod(*Fields[4]),FCString::Atod(*Fields[5]));
                Site.ReferenceRotation[View]=FRotator(FCString::Atod(*Fields[6]),FCString::Atod(*Fields[7]),FCString::Atod(*Fields[8]));
            }
            if(Mask!=3)return false;
            for(const FString& Row:ContactsIn)
            {
                Row.ParseIntoArray(Fields,TEXT(","),false);
                if(Fields.Num()==9 && Fields[0]==Site.Name && Fields[1]==TEXT("1") && Fields[2].Contains(TEXT("NordicRiver")))
                {
                    Site.Detail=Ground({FCString::Atod(*Fields[4]),FCString::Atod(*Fields[5])},18.);
                    break;
                }
            }
        }
        Survey=MoveTemp(ReplaySurvey);
        return true;
    }
    void BeginSite(APlayerController* PC,ACharacter* C,double Now)
    {
        Forward(PC,false);
        C->GetCharacterMovement()->StopMovementImmediately();
        C->GetCharacterMovement()->DisableMovement();
        C->SetActorLocation(Ground(Sites[SiteIndex].Path[0],C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+3.),
            false,nullptr,ETeleportType::TeleportPhysics);
        PC->SetViewTarget(C);Aim(PC,Ground(Sites[SiteIndex].Path[1],85.));
        Leg=1;Photo=0;Requested=false;RefreshRain=false;ReadyAt=0.;Detours=0;DetourUntil=0.;Best=DBL_MAX;
        if(Lap)Weather->SetWeatherState(EFPSWeatherState::Rain);
        Enter(Lap?EStage::Soak:EStage::Settle,Now);
        UE_LOG(LogTemp,Display,TEXT("SHORE_WALK start lap=%d site=%s"),Lap,*Sites[SiteIndex].Name);
    }
    bool ShoreReady(FVector Anchor,FVector Target,double Now)
    {
        const auto Local=HillsLandscapeCapture::Readiness(Hills.Get(),Anchor,Target,5500.);
        if(!Local.Complete()&&Now>=NextReadinessLog)
        {
            NextReadinessLog=Now+15.;
            UE_LOG(LogTemp,Display,TEXT("SHORE_READY site=%s stage=%d ground=%d/%d pcg=%d/%d error=%.1f"),
                *Sites[SiteIndex].Name,int32(Stage),Local.TerrainReady,Local.TerrainRequired,
                Local.VegetationReady,Local.VegetationRequired,Local.MaxGroundError);
        }
        return Local.Complete();
    }
    bool TickShore(float)
    {
        const double Now=FPlatformTime::Seconds();
        if(!World.IsValid()||Now-Began>7200.)return Finish(TEXT("shore walk timed out"),false);
        auto* PC=World->GetFirstPlayerController();
        auto* C=PC?Cast<ACharacter>(PC->GetPawn()):nullptr;
        if(!C)return true;
        if(Stage==EStage::Boot)
        {
            if(Now<NextPoll)return true;
            NextPoll=Now+1.;
            for(TActorIterator<ATemperateHillsWorld> It(World.Get());It;++It)Hills=*It;
            for(TActorIterator<AFPSWeatherManager> It(World.Get());It;++It)Weather=*It;
            if(!Hills.IsValid()||!Hills->bReady||!Weather.IsValid()||PC->IsMoveInputIgnored())return true;
            if(!Compose())return Finish(TEXT("shore survey incomplete"),false);
            C->SetCanBeDamaged(false);
            Weather->RealSecondsPerGameDay=864000.f;
            Weather->AdvanceGameTime(FMath::Fmod(10.5f-24.f*Weather->NormalizedDayTime+24.f,24.f)+.0001f);
            Weather->SetWeatherState(EFPSWeatherState::Clear);
            BeginSite(PC,C,Now);return true;
        }
        const auto& Site=Sites[SiteIndex];
        const double Wet=Weather->GetSurfaceWetness(),Rain=Weather->GetEffectiveRainIntensity();
        // Initial streaming and natural wetting can progress much more slowly
        // than wall time on a busy GPU. These waits are outside the frame sample.
        if(Stage!=EStage::Walk&&Now-Since>1000.)return Finish(TEXT("shore readiness or weather timeout"),false);
        if(Now>NextStatus)
        {
            NextStatus=Now+15.;
            UE_LOG(LogTemp,Display,TEXT("SHORE_WALK lap=%d site=%s stage=%d leg=%d wet=%.3f rain=%.3f pos=%s"),
                Lap,*Site.Name,int32(Stage),Leg,Wet,Rain,*C->GetActorLocation().ToCompactString());
        }
        if(Stage==EStage::Soak)
        {
            if(Wet>.975&&Now>=NextPoll)
            {
                NextPoll=Now+.8;
                if(ShoreReady(C->GetActorLocation(),C->GetActorLocation(),Now))
                {Weather->SetWeatherState(EFPSWeatherState::Cloudy);Enter(EStage::Settle,Now);}
            }
            return true;
        }
        if(Stage==EStage::Settle)
        {
            if(Now<NextPoll)return true;
            NextPoll=Now+.8;
            FHitResult Hit;
            if(Now-Since<6.||Rain>.015||(!Lap&&Wet>.035)||
                !HillsLandscapeCapture::GroundHit(Hills.Get(),Site.Path[0],Hit))return true;
            if(!ShoreReady(C->GetActorLocation(),Hit.ImpactPoint,Now))return true;
            C->SetActorLocation(Hit.ImpactPoint+FVector::UpVector*(C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.));
            C->ClientCheatWalk();C->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
            LastFoot=FVector2D(C->GetActorLocation());FramesWithoutApproach=0;
            Enter(EStage::Walk,Now);LastProgress=Now;return true;
        }
        if(Stage==EStage::Photograph)
        {
            if(bReference)PC->SetControlRotation(Site.ReferenceRotation[Photo]);
            else Aim(PC,Photo?Site.Detail:Site.Vista);
            if(!ReadyAt)
            {
                if(Now<NextPoll)return true;
                NextPoll=Now+.8;
                if(!ShoreReady(C->GetActorLocation(),Site.Detail,Now))return true;
                if(Lap&&Wet<.65&&!RefreshRain){Weather->SetWeatherState(EFPSWeatherState::Rain);RefreshRain=true;}
                if(RefreshRain)
                {
                    if(Wet<.975)return true;
                    Weather->SetWeatherState(EFPSWeatherState::Cloudy);RefreshRain=false;
                }
                if(Lap&&Rain>.015)return true;
                ReadyAt=Now;
            }
            if(Now-ReadyAt<2.5)return true;
            if(bReference&&!bEyeAligned)
            {
                FVector Eye;FRotator R;PC->GetPlayerViewPoint(Eye,R);
                C->SetActorLocation(C->GetActorLocation()+Site.ReferenceEye[Photo]-Eye,false,nullptr,ETeleportType::TeleportPhysics);
                bEyeAligned=true;ReadyAt=Now;return true;
            }
            if(!Requested)
            {
                FVector Eye;FRotator R;PC->GetPlayerViewPoint(Eye,R);
                const TCHAR* View=Photo?TEXT("detail"):TEXT("bank");
                Poses+=FString::Printf(TEXT("%d,%s,%s,%.3f,%.3f,%.3f,%.5f,%.5f,%.5f,%.3f,%.4f,%.4f\n"),
                    Lap,*Site.Name,View,Eye.X,Eye.Y,Eye.Z,R.Pitch,R.Yaw,R.Roll,PC->PlayerCameraManager->GetFOVAngle(),Wet,Rain);
                Shot=Out/FString::Printf(TEXT("%s_%s_%s.png"),Lap?TEXT("wet"):TEXT("dry"),*Site.Name,View);
                FScreenshotRequest::RequestScreenshot(Shot,false,false);Requested=true;
                return true;
            }
            if(Now-ReadyAt<3.4||IFileManager::Get().FileSize(*Shot)<=0)return true;
            FFileHelper::SaveStringToFile(Poses,*(Out/TEXT("poses.csv")));
            bEyeAligned=false;
            if(++Photo<2){Requested=false;ReadyAt=Now;return true;}
            if(!Lap)RecordContacts(Site);
            Save();
            if(++SiteIndex==Sites.Num()){SiteIndex=0;if(++Lap==2)return Finish(TEXT("all eight shoreline walks completed"),true);}
            BeginSite(PC,C,Now);return true;
        }
        const auto P=C->GetActorLocation();
        const FVector2D XY(P);
        if(InnerPasses)
        {
            TRACE_CPUPROFILER_EVENT_SCOPE(HillsShore_InnerWalkSample);
            if(!Previous){TRACE_BOOKMARK(TEXT("HillsShore.Inner.Begin pass=%d"),InnerPass);}
            else if(Now-Previous>.050){TRACE_BOOKMARK(TEXT("HillsShore.Inner.Hitch pass=%d leg=%d ms=%.2f"),InnerPass,Leg,(Now-Previous)*1000.);}
        }
        if(Previous>0.)Frames+=FString::Printf(TEXT("%d,%s,%.3f,%.3f,%.3f,%.3f,%.2f,%.2f,%.2f,%.4f,%.4f\n"),
            InnerPasses?InnerPass:Lap,*Site.Name,1000.*(Now-Previous),FPlatformTime::ToMilliseconds(GGameThreadTime),
            FPlatformTime::ToMilliseconds(GRenderThreadTime),FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles(0)),
            P.X,P.Y,P.Z,Wet,Rain);
        Previous=Now;
        // At a long render frame the pawn can step completely across a 60 cm
        // waypoint. Measure its swept track and steer into the next segment now.
        const FVector2D Step=XY-LastFoot;
        const FVector2D Target=Site.Path[Leg];
        const double Fraction=FMath::Clamp(FVector2D::DotProduct(Target-LastFoot,Step)/FMath::Max(1.,Step.SizeSquared()),0.,1.);
        const bool Crossed=FVector2D::DistSquared(LastFoot+Step*Fraction,Target)<FMath::Square(75.);
        const FVector2D Segment=(Target-Site.Path[Leg-1]).GetSafeNormal();
        const bool Past=FVector2D::DotProduct(XY-Target,Segment)>0. &&
            FMath::Abs(FVector2D::CrossProduct(XY-Target,Segment))<135.;
        LastFoot=XY;
        if((Crossed||Past)&&Leg+1<Site.Path.Num())
        {
            ++Leg;Best=DBL_MAX;LastProgress=Now;Detours=0;DetourUntil=0.;FramesWithoutApproach=0;
        }
        else if(Crossed||Past)
        {
            ++Leg;
            Forward(PC,false);C->GetCharacterMovement()->StopMovementImmediately();C->GetCharacterMovement()->DisableMovement();
            if(InnerPasses)
            {
                if(++InnerPass>=InnerPasses)return Finish(TEXT("sunny inner bend repetitions completed"),true);
                Save();BeginSite(PC,C,Now);return true;
            }
            // Only after the last measured step, register the pawn at the same
            // contact point on each pass; aim through its ordinary first-person camera.
            FHitResult Hit;
            if(!HillsLandscapeCapture::GroundHit(Hills.Get(),Site.Path.Last(),Hit))return Finish(TEXT("no terrain at camera station"),false);
            C->SetActorLocation(Hit.ImpactPoint+FVector::UpVector*(C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.),false,nullptr,ETeleportType::TeleportPhysics);
            Enter(EStage::Photograph,Now);ReadyAt=0.;Requested=false;Save();return true;
        }
        const FVector2D Delta=Site.Path[Leg]-XY;
        const double D=Delta.Size();
        ++FramesWithoutApproach;
        if(D<Best-12.){Best=D;LastProgress=Now;FramesWithoutApproach=0;}
        if(Now>DetourUntil&&Now-LastProgress>1.8&&FramesWithoutApproach>=18)
        {
            if(++Detours>8)return Finish(TEXT("shore movement obstructed"),false);
            const auto Dir=Delta.GetSafeNormal();
            const auto Right=FVector2D(-Dir.Y,Dir.X);
            Dodge=Right*((Detours%3==0)?-1.:1.);
            DetourUntil=Now+(.6+.14*Detours);LastProgress=Now;FramesWithoutApproach=0;
        }
        const auto Dir=Now<DetourUntil?Dodge:Delta.GetSafeNormal();
        PC->SetControlRotation(FVector(Dir,0.).Rotation());Forward(PC,true);
        return true;
    }
};

FAutoConsoleCommandWithWorld ShoreCommand(TEXT("fps.Test.HillsShoreWalk"),TEXT("Walk four water margins in a copied hills world."),
    FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* W)
    {
        if(!W||!W->IsGameWorld()||!FParse::Param(FCommandLine::Get(),TEXT("HillsShoreWalk")))return;
        auto Walk=MakeShared<FShoreWalk>();Walk->World=W;
        int32 Passes=0;
        if(FParse::Value(FCommandLine::Get(),TEXT("HillsShoreInnerPasses="),Passes))
            Walk->InnerPasses=FMath::Clamp(Passes,1,12);
        if(!FParse::Value(FCommandLine::Get(),TEXT("HillsLandscapeOutput="),Walk->Out))return;
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Walk](float Dt){return Walk->TickShore(Dt);}));
    }));
