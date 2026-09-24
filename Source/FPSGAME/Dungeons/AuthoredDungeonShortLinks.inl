// Included in FPlan. Pure-data room placement and short corridor transactions.
static constexpr double ShortLinkLimit=1200.,PreferredLinkLength=600.,ExitLeadLength=80.;
struct FShortLink
{
    TArray<FVector> Points;
    FSocket End;
    double Length=0;
    int32 Turns=0;
};

double LinkCost(const FShortLink& Link,double ReservedLead=0)const
{
    const double Length=Link.Length+ReservedLead;
    return Length*.35+FMath::Max(0.,200.-Length)*1.5+FMath::Max(0.,Length-PreferredLinkLength)*.75+Link.Turns*160.;
}

void AddShortLink(TArray<FShortLink>& Links,const FSocket& Start,TArray<FVector> Points,double OtherLead=0)const
{
    for(int32 I=Points.Num()-1;I>0;--I)if(Points[I].Equals(Points[I-1],.1))Points.RemoveAt(I);
    for(int32 I=Points.Num()-2;I>0;--I)
        if(FVector::DotProduct((Points[I]-Points[I-1]).GetSafeNormal(),(Points[I+1]-Points[I]).GetSafeNormal())>.999)Points.RemoveAt(I);
    if(Points.Num()<2||Points.Num()>4||!Points[0].Equals(Start.P,.1))return;
    FShortLink Link;Link.Points=MoveTemp(Points);Link.Turns=Link.Points.Num()-2;
    FVector Previous=Start.N;
    for(int32 I=1;I<Link.Points.Num();++I)
    {
        const FVector Delta=Link.Points[I]-Link.Points[I-1],Direction=Delta.GetSafeNormal();
        if(Delta.ContainsNaN()||FMath::Abs(Delta.Z)>.1||FMath::Max(FMath::Abs(Direction.X),FMath::Abs(Direction.Y))<.999)return;
        if(I==1?FVector::DotProduct(Direction,Previous)<.999:FMath::Abs(FVector::DotProduct(Direction,Previous))>.001)return;
        // Each authored elbow consumes 2 m on each incident centreline. Leave
        // an actual 80 cm sleeve between bends and at both room door collars.
        const double Sleeve=Delta.Size()-(I>1?200.:0.)-(I+1<Link.Points.Num()?200.:0.);
        if(Sleeve<ExitLeadLength-.1)return;
        Link.Length+=Delta.Size();Previous=Direction;
    }
    if(Link.Length+Start.ReservedLead+OtherLead>ShortLinkLimit+.1)return;
    Link.End={Link.Points.Last(),Previous,-2,Start.Width,Start.Height};
    for(const auto& Existing:Links)
    {
        if(Existing.Points.Num()!=Link.Points.Num())continue;
        bool Same=true;for(int32 I=0;I<Link.Points.Num();++I)Same&=Existing.Points[I].Equals(Link.Points[I],.1);
        if(Same)return;
    }
    Links.Add(MoveTemp(Link));
}

TArray<FShortLink> RoomLinks(const FSocket& Start)const
{
    TArray<FShortLink> Links;
    const FVector F=Start.N,R(-F.Y,F.X,0),P=Start.P;
    for(double Length:{80.,240.,400.,560.})AddShortLink(Links,Start,{P,P+F*Length});
    if(Modules.IsValidIndex(Elbow))for(double Sign:{-1.,1.})
    {
        const FVector Side=R*Sign;
        for(double Lead:{80.,240.})
        {
            const FVector Corner=P+F*(Lead+200.);
            AddShortLink(Links,Start,{P,Corner,Corner+Side*280.});
        }
        const FVector A=P+F*280.,B=A+Side*480.;
        AddShortLink(Links,Start,{P,A,B,B+F*280.});
    }
    Links.StableSort([&](const FShortLink& A,const FShortLink& B){return LinkCost(A,Start.ReservedLead)<LinkCost(B,Start.ReservedLead);});
    return Links;
}

double LinkGoalCost(const FShortLink& Link,int32 Module,int32 Entry,const FSocket& Goal,int32 Remaining)const
{
    const FTransform T=Fit(Module,Entry,Link.End);
    const auto& Exit=Modules[Module].Ports[1-Entry];
    const FVector N=T.TransformVectorNoScale(Exit.N),P=T.TransformPosition(Exit.P)+N*ExitLeadLength;
    return (P-Goal.P).Size()/(1.+Remaining*.6)+(Remaining==0?300.*(1.+FVector::DotProduct(N,Goal.N)):0.)+LinkCost(Link);
}

bool AttachRoom(int32 Module,int32 Entry,const FSocket& Start,const FShortLink& Link,const FString& Route,
                FSocket& Exit,FVector SectorOrigin={},FVector SectorDir={})
{
    if(!Compatible(Link.End,Module,Entry)||Link.Length+Start.ReservedLead>ShortLinkLimit+.1)return false;
    const int32 Before=Pieces.Num();
    // Reserve the whole room first. Corridors must avoid its other walls too;
    // only the exact matching doorway permits an architectural seam overlap.
    if(!Place(Module,Fit(Module,Entry,Link.End),Route,-2,-2,SectorOrigin,SectorDir))return false;
    const FSocket Goal=Socket(Before,Entry);
    if(!PlaceRoutePolyline(Start,Goal,Route,Link.Points,ShortLinkLimit-Start.ReservedLead,ShortLinkLimit))
    {Pieces.SetNum(Before);return false;}
    // Preserve connector-before-room ordering used by staged assembly. FPlaced
    // stores no owner indices; only the two local socket indices need refreshing.
    FPlaced Room=MoveTemp(Pieces[Before]);Pieces.RemoveAt(Before);
    const int32 RoomIndex=Pieces.Add(MoveTemp(Room));
    FSocket Out=Socket(RoomIndex,1-Entry);
    if(!Corridor(1,Out,Route,Threshold)){Pieces.SetNum(Before);return false;}
    Out.ReservedLead=ExitLeadLength;Exit=Out;return true;
}

TArray<FShortLink> LinksBetween(const FSocket& Start,const FSocket& Goal)const
{
    TArray<FShortLink> Links;
    if(FMath::Abs(Start.P.Z-Goal.P.Z)>.1||FMath::Abs(Start.Width-Goal.Width)>=1.||FMath::Abs(Start.Height-Goal.Height)>=1.)return Links;
    const FVector P=Start.P,Q=Goal.P;
    auto Add=[&](TArray<FVector> Points){AddShortLink(Links,Start,MoveTemp(Points),Goal.ReservedLead);};
    Add({P,Q});
    if(Modules.IsValidIndex(Elbow))
    {
        Add({P,FVector(P.X,Q.Y,P.Z),Q});Add({P,FVector(Q.X,P.Y,P.Z),Q});
        const double Facing=FVector::DotProduct(Start.N,Goal.N),Gap=FVector::DotProduct(Q-P,Start.N);
        if(Facing<-.999)for(double Lead:{280.,400.,Gap*.5,Gap-280.,Gap-400.})
            Add({P,P+Start.N*Lead,Q+Goal.N*(Gap-Lead),Q});
        else if(Facing>.999)for(double Extra:{280.,400.,560.})
        {
            const double Lead=FMath::Max(0.,Gap)+Extra;
            Add({P,P+Start.N*Lead,Q+Goal.N*(Lead-Gap),Q});
        }
    }
    Links.RemoveAll([&](const FShortLink& Link){return FVector::DotProduct(Link.End.N,Goal.N)>-.999;});
    Links.StableSort([&](const FShortLink& A,const FShortLink& B){return LinkCost(A)<LinkCost(B);});
    return Links;
}

void AddTargetRoomLinks(TArray<FShortLink>& Links,int32 Module,int32 Entry,const FSocket& Start,const FSocket& Goal)const
{
    if(!Compatible(Goal,Module,1-Entry))return;
    auto AddExit=[&](FSocket ExitTarget)
    {
        // The backwards link ends at the outer end of the room's exit sleeve.
        ExitTarget.P+=ExitTarget.N*ExitLeadLength;
        const FTransform T=Fit(Module,1-Entry,ExitTarget);
        const FPort& Port=Modules[Module].Ports[Entry];
        const FSocket Door{T.TransformPosition(Port.P),T.TransformVectorNoScale(Port.N),-2,Port.Width,Port.Height};
        for(const auto& Link:LinksBetween(Start,Door))AddShortLink(Links,Start,Link.Points);
    };
    AddExit(Goal);
    // Solve both sides of the last room. Restricting its exit to a straight
    // sleeve discarded rooms that need an L/Z link on the target side instead.
    for(const auto& Back:RoomLinks(Goal))
        if(Back.Length+Goal.ReservedLead+ExitLeadLength<=ShortLinkLimit+.1)AddExit(Back.End);
}

bool ShortRouteTo(const FSocket& Start,const FSocket& Goal,const FString& Route)
{
    if(FMath::Abs(Start.P.Z-Goal.P.Z)>.1||FMath::Abs(Start.Width-Goal.Width)>=1.||FMath::Abs(Start.Height-Goal.Height)>=1.)return false;
    if(Start.P.Equals(Goal.P,.1))return FVector::DotProduct(Start.N,Goal.N)<-.999;
    const auto Links=LinksBetween(Start,Goal);
    const int32 Before=Pieces.Num();
    for(const auto& Link:Links)
    {
        if(--CompactBudget<0)break;
        Pieces.SetNum(Before);
        if(PlaceRoutePolyline(Start,Goal,Route,Link.Points,ShortLinkLimit-Start.ReservedLead-Goal.ReservedLead,ShortLinkLimit))return true;
    }
    Pieces.SetNum(Before);return false;
}
