// Included inside FPlan. Rooms stay rigid; only a connector's final straight sleeve changes length.
int32 BossRoom=-1,BossConfluence=-1,BossApproach=-1,Elbow=-1;
bool bBossTerminal=false;

bool StraightTo(FSocket& S,FVector Destination,const FString& Route,int32 GoalOwner=-2)
{
    const FVector Delta=Destination-S.P;
    double Remaining=Delta.Size();
    if(Remaining<.1)return true;
    if(FVector::DotProduct(Delta.GetSafeNormal(),S.N)<.999)return false;
    while(Remaining>.1)
    {
        // Keep repeated 4 m modules and a single short closure, never scale a combat room.
        const double Length=FMath::Min(400.,Remaining);
        FTransform T=Fit(Transit,0,S);T.SetScale3D(FVector(1,Length/400.,1));
        if(!Place(Transit,T,Route,-2,S.Owner,{}, {},Remaining<=400.1?GoalOwner:-2))return false;
        S=Socket(Pieces.Num()-1,1);Remaining=(Destination-S.P).Size();
    }
    return true;
}

bool RouteTo(FSocket Start,const FSocket& Goal,const FString& Route)
{
    // Search in the exact room coordinate system, without snapping authored door positions.
    const FVector A=Start.P+Start.N*600.,B=Goal.P+Goal.N*600.;
    TArray<FBox> Obstacles;Obstacles.Add(Reserved);
    for(const auto& Piece:Pieces)Obstacles.Append(Piece.Cells);
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
        const FBox Sweep(FVector(FMath::Min(P.X,Q.X)-220,FMath::Min(P.Y,Q.Y)-220,0),
                         FVector(FMath::Max(P.X,Q.X)+220,FMath::Max(P.Y,Q.Y)+220,1));
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
    while(!Open.empty()&&++Expanded<160000)
    {
        const auto Current=Open.top();Open.pop();const int32 State=Current.State,Node=State/4,Heading=State%4;
        if(Node==Last){Found=State;break;}
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
            const int32 Target=Next*4+D;if(Candidate>=Cost[Target])continue;
            Cost[Target]=Candidate;Parent[Target]=State;
            Open.push({Candidate+FMath::Abs(Q.X-B.X)+FMath::Abs(Q.Y-B.Y),Target});
        }
    }
    if(Found<0)return false;
    TArray<FVector> Reverse;for(int32 State=Found;State>=0;State=Parent[State])Reverse.Add(Position(State/4));
    TArray<FVector> Points;Points.Add(Start.P);
    for(int32 I=Reverse.Num()-1;I>=0;--I)Points.Add(Reverse[I]);Points.Add(Goal.P);
    for(int32 I=Points.Num()-2;I>0;--I)
        if(FVector::DotProduct((Points[I]-Points[I-1]).GetSafeNormal(),(Points[I+1]-Points[I]).GetSafeNormal())>.999)Points.RemoveAt(I);
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
