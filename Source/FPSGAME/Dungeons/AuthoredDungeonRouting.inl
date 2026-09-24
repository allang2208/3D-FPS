// Included inside FPlan. Rooms stay rigid; only a connector's final straight sleeve changes length.
int32 BossRoom=-1,BossConfluence=-1,BossApproach=-1,Elbow=-1;
bool bBossTerminal=false;

bool StraightTo(FSocket& S,FVector Destination,const FString& Route,int32 GoalOwner=-2)
{
    const FVector Delta=Destination-S.P;
    double Remaining=Delta.Size();
    if(Remaining<.1)return true;
    const double Forward=FVector::DotProduct(Delta,S.N);
    if(Forward<=0||(Delta-S.N*Forward).Size()>.1)return false;
    Remaining=Forward;
    while(Remaining>.1)
    {
        // Keep repeated 4 m modules and a single short closure, never scale a combat room.
        double Length=FMath::Min(400.,Remaining);
        if(Remaining>400.1&&Remaining-Length<80.)Length=Remaining-80.;
        const int32 Connector=FMath::IsNearlyEqual(Length,80.,.01)?Threshold:Transit;
        if(!Compatible(S,Connector,0))return false;
        FTransform T=Fit(Connector,0,S);
        if(Connector==Transit)T.SetScale3D(FVector(1,Length/400.,1));
        if(!Place(Connector,T,Route,-2,S.Owner,{}, {},Remaining<=400.1?GoalOwner:-2))return false;
        S=Socket(Pieces.Num()-1,1);
        const FVector Left=Destination-S.P;
        Remaining=FVector::DotProduct(Left,S.N);
        if(Remaining<-.1||(Left-S.N*Remaining).Size()>.1)return false;
    }
    return S.P.Equals(Destination,.1);
}

bool PlaceRoutePolyline(FSocket Start,const FSocket& Goal,const FString& Route,TArray<FVector> Points,double MaxLength,double MaxStraight)
{
    for(int32 I=Points.Num()-1;I>0;--I)if(Points[I].Equals(Points[I-1],.1))Points.RemoveAt(I);
    for(int32 I=Points.Num()-2;I>0;--I)
        if(FVector::DotProduct((Points[I]-Points[I-1]).GetSafeNormal(),(Points[I+1]-Points[I]).GetSafeNormal())>.999)Points.RemoveAt(I);
    double Walk=0;
    for(int32 I=1;I<Points.Num();++I){const double L=(Points[I]-Points[I-1]).Size();if(L>MaxStraight)return false;Walk+=L;}
    if(Walk>MaxLength)return false;
    const int32 Before=Pieces.Num();FSocket S=Start;
    for(int32 I=1;I<Points.Num();++I)
    {
        const FVector Incoming=(Points[I]-Points[I-1]).GetSafeNormal();const bool Bend=I+1<Points.Num();
        if(FVector::DotProduct(S.N,Incoming)<.999){Pieces.SetNum(Before);return false;}
        const FVector EndPoint=Points[I]-(Bend?Incoming*200.:FVector::ZeroVector);
        if(!StraightTo(S,EndPoint,Route,Bend?-2:Goal.Owner)){Pieces.SetNum(Before);return false;}
        if(Bend)
        {
            const FVector Outgoing=(Points[I+1]-Points[I]).GetSafeNormal();bool Placed=false;
            for(int32 Entry=0;Entry<2;++Entry)
            {
                FTransform T=Fit(Elbow,Entry,S);
                if(FVector::DotProduct(T.TransformVectorNoScale(Modules[Elbow].Ports[1-Entry].N),Outgoing)<.999)continue;
                if(Place(Elbow,T,Route,-2,S.Owner)){S=Socket(Pieces.Num()-1,1-Entry);Placed=true;break;}
            }
            if(!Placed){Pieces.SetNum(Before);return false;}
        }
    }
    if(!S.P.Equals(Goal.P,1)||FVector::DotProduct(S.N,Goal.N)>-.999){Pieces.SetNum(Before);return false;}
    return true;
}

bool RouteTo(FSocket Start,const FSocket& Goal,const FString& Route,double MaxLength=DBL_MAX,double MaxStraight=DBL_MAX)
{
    if(FMath::Abs(Start.P.Z-Goal.P.Z)>1)return false; // Floors connect only through authored stair ports.
    if(Start.P.Equals(Goal.P,1))return FVector::DotProduct(Start.N,Goal.N)<-.999;
    if((Start.P-Goal.P).Size()>MaxLength)return false;
    const int32 DirectBefore=Pieces.Num();FSocket Direct=Start;
    if(FVector::DotProduct(Start.N,Goal.N)<-.999&&(Start.P-Goal.P).Size()<=MaxStraight&&StraightTo(Direct,Goal.P,Route,Goal.Owner))return true;
    Pieces.SetNum(DirectBefore);
    if(bCompactBoss)
    {
        // A short offset join needs its bend halfway between the two doors. Fixed
        // 4 m leads overshoot each other when the remaining gap is only 4-8 m.
        for(const FVector& Corner:{FVector(Start.P.X,Goal.P.Y,Start.P.Z),FVector(Goal.P.X,Start.P.Y,Start.P.Z)})
            if(PlaceRoutePolyline(Start,Goal,Route,{Start.P,Corner,Goal.P},MaxLength,MaxStraight))return true;
        if(FVector::DotProduct(Start.N,Goal.N)<-.999)
        {
            const double ForwardGap=FVector::DotProduct(Goal.P-Start.P,Start.N);
            if(ForwardGap>=400&&PlaceRoutePolyline(Start,Goal,Route,
                {Start.P,Start.P+Start.N*(ForwardGap*.5),Goal.P+Goal.N*(ForwardGap*.5),Goal.P},MaxLength,MaxStraight))return true;
        }
        // Most short joins need only one dogleg; do not spend a grid search on those.
        for(double LA:{200.,400.,800.,1200.})for(double LB:{200.,400.,800.,1200.})
        {
            const FVector A=Start.P+Start.N*LA,B=Goal.P+Goal.N*LB;
            for(const FVector& Corner:{FVector(A.X,B.Y,A.Z),FVector(B.X,A.Y,A.Z)})
            {
                if(--CompactBudget<0)return false;
                if(PlaceRoutePolyline(Start,Goal,Route,{Start.P,A,Corner,B,Goal.P},MaxLength,MaxStraight))return true;
            }
        }
    }
    // Search in the exact room coordinate system, without snapping authored door positions.
    const double Lead=bCompactBoss?400.:600.;
    const FVector A=Start.P+Start.N*Lead,B=Goal.P+Goal.N*Lead;
    TArray<FBox> Obstacles;Obstacles.Add(Reserved);
    for(const auto& Piece:Pieces)Obstacles.Append(Piece.Cells);
    Obstacles.RemoveAll([&](const FBox& Box){return Box.Max.Z<Start.P.Z-80||Box.Min.Z>Start.P.Z+320;});
    TArray<double> X{A.X,B.X},Y{A.Y,B.Y};
    for(const FBox& Box:Obstacles)
    {
        X.Add(Box.Min.X-260);X.Add(Box.Max.X+260);
        Y.Add(Box.Min.Y-260);Y.Add(Box.Max.Y+260);
    }
    auto Normalize=[](TArray<double>& Values)
    {
        Values.Sort();for(int32 I=Values.Num()-1;I>0;--I)if(FMath::Abs(Values[I]-Values[I-1])<.01)Values.RemoveAt(I);
        Values.Insert(Values[0]-800,0);Values.Add(Values.Last()+800);
    };
    Normalize(X);Normalize(Y);
    const int32 NX=X.Num(),NY=Y.Num(),Count=NX*NY;
    auto Nearest=[](const TArray<double>& V,double Q){return V.IndexOfByPredicate([Q](double P){return FMath::Abs(P-Q)<.01;});};
    const int32 First=Nearest(Y,A.Y)*NX+Nearest(X,A.X),Last=Nearest(Y,B.Y)*NX+Nearest(X,B.X);
    auto Position=[&](int32 Node){return FVector(X[Node%NX],Y[Node/NX],Start.P.Z);};
    auto Clear=[&](FVector P,FVector Q)
    {
        const FBox Sweep(FVector(FMath::Min(P.X,Q.X)-220,FMath::Min(P.Y,Q.Y)-220,Start.P.Z-22),
                         FVector(FMath::Max(P.X,Q.X)+220,FMath::Max(P.Y,Q.Y)+220,Start.P.Z+298));
        for(const FBox& Box:Obstacles)if(Overlap(Sweep,Box))return false;
        return true;
    };
    // Heading is part of the search state, avoiding an unnecessary turn in a narrow lane.
    struct FOpen {double F;int32 State;bool operator<(const FOpen& Other)const{return F>Other.F;}};
    std::priority_queue<FOpen> Open;
    TArray<double> Cost;Cost.Init(TNumericLimits<double>::Max(),Count*4);
    TArray<int32> Parent;Parent.Init(-1,Count*4);
    auto Direction=[](FVector V){return FMath::Abs(V.X)>.5?(V.X>0?0:1):(V.Y>0?2:3);};
    const int32 Initial=First*4+Direction(Start.N);Cost[Initial]=0;Open.push({0,Initial});
    int32 Found=-1,Expanded=0;
    while(!Open.empty()&&++Expanded<(bCompactBoss?600:160000))
    {
        if(bCompactBoss&&--CompactBudget<0)return false;
        const auto Current=Open.top();Open.pop();const int32 State=Current.State,Node=State/4,Heading=State%4;
        if(Node==Last&&Heading==Direction(-Goal.N)){Found=State;break;}
        const int32 IX=Node%NX,IY=Node/NX;
        const int32 Nexts[4]={IX+1<NX?Node+1:-1,IX>0?Node-1:-1,IY+1<NY?Node+NX:-1,IY>0?Node-NX:-1};
        for(int32 D=0;D<4;++D)
        {
            const int32 Next=Nexts[D];if(Next<0||(D^1)==Heading)continue;
            const FVector P=Position(Node),Q=Position(Next);
            if(!Clear(P,Q))continue;
            if(D!=Heading)
            {
                int32 Previous=State;while(Parent[Previous]>=0&&Parent[Previous]%4==Heading)Previous=Parent[Previous];
                if((P-Position(Previous/4)).Size()<500&&Node!=First)continue;
            }
            const double Candidate=Cost[State]+(P-Q).Size()+(D==Heading?0:120);
            if(Candidate+FMath::Abs(Q.X-B.X)+FMath::Abs(Q.Y-B.Y)+2*Lead>MaxLength)continue;
            const int32 Target=Next*4+D;if(Candidate>=Cost[Target])continue;
            Cost[Target]=Candidate;Parent[Target]=State;
            Open.push({Candidate+FMath::Abs(Q.X-B.X)+FMath::Abs(Q.Y-B.Y),Target});
        }
    }
    if(Found<0)return false;
    TArray<FVector> Reverse;for(int32 State=Found;State>=0;State=Parent[State])Reverse.Add(Position(State/4));
    TArray<FVector> Points;Points.Add(Start.P);
    for(int32 I=Reverse.Num()-1;I>=0;--I)Points.Add(Reverse[I]);Points.Add(Goal.P);
    return PlaceRoutePolyline(Start,Goal,Route,MoveTemp(Points),MaxLength,MaxStraight);
}

bool ReserveBoss(const FVector& Center,const FVector& Forward,TArray<FSocket>& Targets)
{
    // Reserve the complete unique terminal before any branch grows into its space.
    FSocket Entry{Center+Forward*22000,Forward,-2};Entry.P.Z=Pieces[0].Transform.GetLocation().Z;
    if(!Place(BossConfluence,Fit(BossConfluence,0,Entry),TEXT("BossConfluence")))return false;
    const int32 Hub=Pieces.Num()-1;
    Targets={Socket(Hub,0),Socket(Hub,2),Socket(Hub,3)};
    FSocket Door=Socket(Hub,1);
    if(!Place(BossApproach,Fit(BossApproach,0,Door),TEXT("BossApproach"),-2,Hub))return false;
    Door=Socket(Pieces.Num()-1,1);
    return Place(BossRoom,Fit(BossRoom,0,Door),TEXT("BossTerminal"),-2,Door.Owner);
}
