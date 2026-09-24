namespace DungeonDressing
{
bool FPlacementScene::PropBlocked(const FPropBody& Body,FString& Reason) const
{
    const FBox Bounds=Body.Bounds().ExpandBy(.08);
    for(const auto& Other:Settled)
        if(PropsTouch(Body,Other.Body)){Reason=TEXT("another_prop");return true;}
    auto HitsBox=[&](const FBox& Box)
    {
        if(!Bounds.Intersect(Box))return false;
        const Chaos::TBox<Chaos::FReal,3> Shape(Box.Min-Body.Origin,Box.Max-Body.Origin);
        return Chaos::GJKIntersection(*Body.Hull,Shape,Chaos::FRigidTransform3(FVector::ZeroVector,FQuat::Identity),.08);
    };
    for(const FBox& Box:Accepted)if(HitsBox(Box)){Reason=TEXT("wall_decoration");return true;}
    for(const FBox& Box:FixedBoxes)if(HitsBox(Box)){Reason=TEXT("fixed_prop");return true;}
    for(const auto& G:Geometry)
    {
        if(!G.Bounds.Intersect(Bounds))continue;
        if(G.Triangles.IsEmpty()){Reason=TEXT("unresolved_geometry:")+G.Name;return true;}
        TArray<Chaos::FConvex::FVec3Type> Points;
        for(const auto& P:Body.Hull->GetVertices())
            Points.Add(Chaos::FConvex::FVec3Type(G.Transform.InverseTransformPosition(Body.Origin+FVector(P))));
        // Transform vertices explicitly: a room part can have a non-uniform scale.
        // An axis-aligned box in its local space would over-reject tilted/close props.
        const auto Shape=PropHull(Points);
        if(!Shape){Reason=TEXT("invalid_prop_envelope");return true;}
        const double Margin=.08/FMath::Max(.001,G.Transform.GetScale3D().GetAbsMin());
        for(const auto& Tri:G.Triangles)if(Tri&&
            (Tri->OverlapGeom(*Shape,Chaos::FRigidTransform3::Identity,Margin)
                ||InsideSolid(*Tri,G.Transform.InverseTransformPosition(Body.Center()))))
        {Reason=TEXT("scene_geometry:")+G.Name;return true;}
    }
    return false;
}

bool FPlacementScene::FloorContact(FPropBody& Body,int32 Module,double Expected,double& Height,FString& Reason) const
{
    const FBox Bounds=Body.Bounds();const FVector Center=Bounds.GetCenter(),Extent=Bounds.GetExtent();
    double Low=DBL_MAX,High=-DBL_MAX;
    for(int32 X=-1;X<=1;++X)for(int32 Y=-1;Y<=1;++Y)
    {
        const FVector Sample(Center.X+Extent.X*.94*X,Center.Y+Extent.Y*.94*Y,Expected);
        FVector Hit,N;
        if(!Trace(Sample+FVector(0,0,12),Sample-FVector(0,0,12),Module,false,Hit,N)||N.Z<.985)
        {Reason=TEXT("missing_or_sloping_support");return false;}
        Low=FMath::Min(Low,Hit.Z);High=FMath::Max(High,Hit.Z);
    }
    if(High-Low>1.5){Reason=TEXT("uneven_support");return false;}
    Height=High;Body.Origin.Z=High+.2-Body.RelativeBounds.Min.Z;
    return true;
}

bool FPlacementScene::StackContact(FPropBody& Body,const FSettledProp& Parent,FString& Reason) const
{
    if(Parent.Depth>=2||(Parent.Type!=EProp::Barrel&&Parent.Type!=EProp::Rope))
    {Reason=TEXT("not_a_stack_support");return false;}
    const FBox Base=Parent.Body.Bounds(),Bounds=Body.Bounds();
    const FVector Center=Bounds.GetCenter(),E=Bounds.GetExtent();
    // No balancing a larger item on a lantern/handle, nor suspending half a barrel
    // outside its support. The actual top triangles, not the hull cap, supply contacts.
    if(Bounds.Min.X<Base.Min.X+1||Bounds.Max.X>Base.Max.X-1
        ||Bounds.Min.Y<Base.Min.Y+1||Bounds.Max.Y>Base.Max.Y-1)
    {Reason=TEXT("stack_overhang");return false;}
    TArray<FVector> Hits;
    double High=-DBL_MAX;
    for(int32 I=0;I<8;++I)
    {
        const double Angle=2*PI*I/8;
        const FVector Sample(Center.X+E.X*.68*FMath::Cos(Angle),Center.Y+E.Y*.68*FMath::Sin(Angle),0);
        FVector Hit,N;
        if(PropSurface(Parent,Sample+FVector(0,0,Base.Max.Z+2),Sample+FVector(0,0,Base.Min.Z),Hit,N)&&N.Z>.94)
        {Hits.Add(Hit);High=FMath::Max(High,Hit.Z);}
    }
    TArray<FVector> Contacts;
    for(const FVector& P:Hits)if(High-P.Z<=.85)Contacts.Add(P);
    const FVector MassCenter=Body.Origin+FVector(Body.Hull->GetCenterOfMass());
    if(Hits.Num()<5||!SupportSurrounds(MassCenter,Contacts))
    {Reason=TEXT("insufficient_stack_support");return false;}
    Body.Origin.Z=High+.2-Body.RelativeBounds.Min.Z;
    if(Body.Bounds().Max.Z>Parent.FloorZ+170)
    {Reason=TEXT("stack_height_limit");return false;}
    return true;
}

bool FPlacementScene::LeanContact(FPropBody& Body,const FSettledProp& Parent,const FVector& Direction,FString& Reason) const
{
    // The convex barrel shell supplies a reliable brace. Open ladder rungs and bucket
    // handles do not qualify merely because their enclosing hull touches the candidate.
    const double Height=Body.RelativeBounds.GetSize().Z;
    if(Parent.Type!=EProp::Barrel||Parent.Depth!=0||Parent.Body.Bounds().Max.Z<Parent.FloorZ+Height*.5)
    {Reason=TEXT("missing_lean_brace");return false;}
    const FVector Center=Parent.Body.Center(),Offset=Body.RelativeBounds.GetCenter();
    const double Reach=Parent.Body.RelativeBounds.GetExtent().Size2D()+Body.RelativeBounds.GetExtent().Size2D()+45;
    auto AtDistance=[&](double Distance)
    {
        Body.Origin.X=Center.X+Direction.X*Distance-Offset.X;
        Body.Origin.Y=Center.Y+Direction.Y*Distance-Offset.Y;
        Body.Origin.Z=Parent.FloorZ+.2-Body.RelativeBounds.Min.Z;
    };
    AtDistance(0);
    if(!PropsTouch(Body,Parent.Body,0)){Reason=TEXT("missing_lean_contact");return false;}
    AtDistance(Reach);
    if(PropsTouch(Body,Parent.Body)){Reason=TEXT("no_lean_clearance");return false;}
    double Near=0,Far=Reach;
    for(int32 I=0;I<12;++I)
    {
        const double Middle=(Near+Far)*.5;AtDistance(Middle);
        if(PropsTouch(Body,Parent.Body))Near=Middle;else Far=Middle;
    }
    AtDistance(Far+.2);
    double Floor;
    if(!FloorContact(Body,Parent.Module,Parent.FloorZ,Floor,Reason))return false;
    if(!PropsTouch(Body,Parent.Body,.9)) {Reason=TEXT("unsupported_lean");return false;}
    return true;
}

bool FPlacementScene::Place(UStaticMesh* Mesh,const FObject& Part,const FObject& Module,const FTransform& Room,
    int32 ModuleIndex,FTransform& World,FString& Reason)
{
    bool Wall=false;Part->TryGetBoolField(TEXT("dressing_wall"),Wall);
    if(Wall)return Place(Mesh->GetBoundingBox(),Part,Module,Room,ModuleIndex,World,Reason);
    int32 Cluster=INDEX_NONE,Item=INDEX_NONE,ParentItem=INDEX_NONE,TypeIndex=0,Seed=0;
    Part->TryGetNumberField(TEXT("dressing_cluster"),Cluster);Part->TryGetNumberField(TEXT("dressing_item"),Item);
    Part->TryGetNumberField(TEXT("dressing_parent"),ParentItem);Part->TryGetNumberField(TEXT("dressing_type"),TypeIndex);
    Part->TryGetNumberField(TEXT("dressing_seed"),Seed);
    bool Primary=false;Part->TryGetBoolField(TEXT("dressing_primary"),Primary);
    if(!Primary&&!AcceptedClusters.Contains(FIntPoint(ModuleIndex,Cluster)))
    {Reason=TEXT("cluster_primary_rejected");return false;}
    TSharedPtr<FPropGeometry>& Cached=PropGeometry.FindOrAdd(Mesh);
    if(!Cached)
    {
        Cached=MakeShared<FPropGeometry>();
        if(auto* Body=Mesh->GetBodySetup()){Body->CreatePhysicsMeshes();Cached->Triangles=Body->TriMeshGeometries;}
        TArray<Chaos::FConvex::FVec3Type> Points;
        for(const auto& Tri:Cached->Triangles)if(Tri)
            for(int32 I=0,Count=int32(Tri->Particles().Size());I<Count;++I)Points.Add(Chaos::FConvex::FVec3Type(Tri->Particles().GetX(I)));
        Cached->Hull=PropHull(Points);
    }
    if(!Cached->Hull){Reason=TEXT("missing_prop_geometry");return false;}
    const EProp Type=EProp(TypeIndex);
    int32 MainIndex=INDEX_NONE;
    for(int32 I=0;I<Settled.Num();++I)
        if(Settled[I].Module==ModuleIndex&&Settled[I].Item==ParentItem){MainIndex=I;break;}
    FTransform Base=World;
    if(MainIndex!=INDEX_NONE)
    {
        const FVector Authored=Room.TransformPosition(Vector(Part,TEXT("dressing_parent_position")));
        const FVector Shift=Settled[MainIndex].Transform.GetTranslation()-Authored;
        Base.AddToTranslation(FVector(Shift.X,Shift.Y,0));
    }
    FVector SupportPosition=Vector(Part,TEXT("position"));
    Part->TryGetNumberField(TEXT("dressing_base_z"),SupportPosition.Z);
    const double Expected=Room.TransformPosition(SupportPosition).Z;
    FString Arrangement;Part->TryGetStringField(TEXT("dressing_arrangement"),Arrangement);
    FRandomStream Random(Seed);
    const FProfile P=Profile(Module);
    FPropBody FloorPose;
    if(!FloorPose.SetPose(*Cached,Base)){Reason=TEXT("invalid_prop_envelope");return false;}
    for(int32 Attempt=0;Attempt<12;++Attempt)
    {
        ++PlacementAttempts;
        FTransform Candidate=Base;
        FPropBody Body;
        double FloorZ=Expected;int32 Depth=0;
        const bool Stack=MainIndex!=INDEX_NONE&&Attempt<5&&Arrangement==TEXT("stack");
        const bool Lean=MainIndex!=INDEX_NONE&&Attempt<5&&Arrangement==TEXT("lean");
        if(Stack)
        {
            int32 SupportIndex=MainIndex;
            // A second rope may land on an already settled coil, up to two layers.
            for(int32 I=Settled.Num()-1;I>=0;--I)
                if(Settled[I].Module==ModuleIndex&&Settled[I].Cluster==Cluster&&Settled[I].Depth<2
                    &&Settled[I].Type==EProp::Rope&&Random.FRand()<.5f){SupportIndex=I;break;}
            const auto& Parent=Settled[SupportIndex];
            Candidate.SetRotation(Room.GetRotation()*FRotator(0,Random.FRandRange(-180,180),0).Quaternion());
            if(!Body.SetPose(*Cached,Candidate)){Reason=TEXT("invalid_prop_envelope");continue;}
            const FVector Center=Parent.Body.Center(),Offset=Body.RelativeBounds.GetCenter();
            Body.Origin.X=Center.X-Offset.X+Random.FRandRange(-8,8);
            Body.Origin.Y=Center.Y-Offset.Y+Random.FRandRange(-8,8);
            if(!StackContact(Body,Parent,Reason))continue;
            FloorZ=Parent.FloorZ;Depth=Parent.Depth+1;
        }
        else if(Lean)
        {
            const auto& Parent=Settled[MainIndex];
            FVector D=(Base.GetTranslation()-Parent.Body.Center()).GetSafeNormal2D();
            if(D.IsNearlyZero())D=Room.GetUnitAxis(EAxis::X);
            D=FRotator(0,Random.FRandRange(-65,65),0).RotateVector(D);
            const double Angle=FMath::DegreesToRadians(Random.FRandRange(12,29));
            const FVector Up=FVector::UpVector*FMath::Cos(Angle)-D*FMath::Sin(Angle);
            Candidate.SetRotation(FQuat::FindBetweenNormals(FVector::UpVector,Up)
                *FRotator(0,Random.FRandRange(-180,180),0).Quaternion());
            if(!Body.SetPose(*Cached,Candidate)){Reason=TEXT("invalid_prop_envelope");continue;}
            if(!LeanContact(Body,Parent,D,Reason))continue;
            FloorZ=Parent.FloorZ;
        }
        else
        {
            Body=FloorPose; // Translation retries reuse the same oriented hull.
            if(Attempt>0)
            {
                if(MainIndex==INDEX_NONE)
                    Body.Origin+=Room.TransformVectorNoScale(FVector(Random.FRandRange(-45,45),Random.FRandRange(-45,45),0));
                else
                {
                    int32 Anchor=MainIndex;
                    TArray<int32> Neighbours;
                    for(int32 I=0;I<Settled.Num();++I)
                        if(Settled[I].Module==ModuleIndex&&Settled[I].Cluster==Cluster&&Settled[I].Depth==0)Neighbours.Add(I);
                    if(!Neighbours.IsEmpty()&&Random.FRand()<.7f)Anchor=Neighbours[Random.RandRange(0,Neighbours.Num()-1)];
                    const FVector Root=Settled[MainIndex].Body.Center(),Center=Settled[Anchor].Body.Center();
                    const FVector Spill=(Base.GetTranslation()-Root).GetSafeNormal2D();
                    const double Angle=FMath::Atan2(Spill.Y,Spill.X)+Random.FRandRange(-1.9,1.9);
                    const double Radius=(Body.RelativeBounds.GetExtent().Size2D()+Settled[Anchor].Body.RelativeBounds.GetExtent().Size2D())
                        *Random.FRandRange(.5,1.3);
                    const FVector At=Center+FVector(FMath::Cos(Angle),FMath::Sin(Angle),0)*Radius;
                    if(FVector::DistSquared2D(At,Root)>FMath::Square(220.0))continue;
                    const FVector Offset=Body.RelativeBounds.GetCenter();
                    Body.Origin.X=At.X-Offset.X;Body.Origin.Y=At.Y-Offset.Y;
                }
            }
            if(!FloorContact(Body,ModuleIndex,Expected,FloorZ,Reason))continue;
        }
        Candidate.SetTranslation(Body.Origin);
        // Preserve authored door/route exclusions after any contact-driven movement.
        const FBox LocalBounds=Mesh->GetBoundingBox().TransformBy(Candidate.GetRelativeTransform(Room));
        if(!Fits(LocalBounds,Module,P,{},false)){Reason=TEXT("reserved_space_after_snap");continue;}
        if(PropBlocked(Body,Reason))continue;
        FSettledProp Placed;Placed.Body=MoveTemp(Body);Placed.Transform=Candidate;Placed.Geometry=Cached;
        Placed.Type=Type;Placed.Module=ModuleIndex;Placed.Cluster=Cluster;Placed.Item=Item;Placed.Depth=Depth;Placed.FloorZ=FloorZ;
        Settled.Add(MoveTemp(Placed));
        if(Primary)AcceptedClusters.Add(FIntPoint(ModuleIndex,Cluster));
        if(Stack)++StackCount;else if(Lean)++LeanCount;
        else if(FMath::Abs(Candidate.GetUnitAxis(EAxis::Z).Z)<.25)++FallenCount;
        World=Candidate;Reason.Empty();return true;
    }
    if(Reason.IsEmpty())Reason=TEXT("pile_has_no_safe_pose");
    return false;
}
}
