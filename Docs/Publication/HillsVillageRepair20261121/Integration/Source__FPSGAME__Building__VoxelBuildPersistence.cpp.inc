// Source/FPSGAME/Building/VoxelBuildPersistence.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 128-173 | file scope
        if(S.Version>=15)
        {
            for(auto& Prefab:S.Prefabs)
            {
                // V15 serialized only stairs; v16 also records exact wall and portal sockets.
                if(Prefab.Id!=VillageWallStairs::Id&&
                    !(S.Version>=16&&(Prefab.Id==VillageBuildDefense::HighWall||Prefab.Id==VillageBuildDefense::StoneGate)))continue;
                bool bDocked=Prefab.WallDockPose.IsSet();
                Ar<<bDocked;
                if(!bDocked)continue;
                FVector Origin=FVector::ZeroVector;
                double YawDegrees=0.;
                if(Ar.IsSaving())
                {
                    Origin=Prefab.WallDockPose->GetLocation();
                    YawDegrees=Prefab.WallDockPose->Rotator().Yaw;
                }
                Ar<<Origin<<YawDegrees;
                if(Ar.IsLoading())
                {
                    if(Origin.ContainsNaN()||!FMath::IsFinite(YawDegrees)){Ar.SetError();return;}
                    Prefab.WallDockPose=FTransform(FRotator(0.,YawDegrees,0.),Origin);
                }
            }
        }
        // Basic walls and timber gates turn about their existing grid centre. Only the angle
        // needs a new field; the placement rule also restores the repaired wall's 1.25 Z scale.
        // Keep this after the entire v15/v16 pose stream, including when the recipes are mixed.
        if(S.Version>=17)
        {
            for(auto& Prefab:S.Prefabs)
            {
                if(!VillageBuildDefense::IsBasicWallOrGate(Prefab.Id))continue;
                int16 Degrees=INDEX_NONE;
                if(Ar.IsSaving()&&Prefab.WallDockPose.IsSet())
                    Degrees=FMath::RoundToInt(FRotator::ClampAxis(Prefab.WallDockPose->Rotator().Yaw))%360;
                Ar<<Degrees;
                if(Ar.IsLoading()&&Degrees!=INDEX_NONE)
                {
                    if(Degrees<0||Degrees>=360){Ar.SetError();return;}
                    Prefab.WallDockPose=VillageBuildDefense::Placement(Prefab.Id,Prefab.Cell,Prefab.Footprint,Prefab.Yaw,Degrees);
                }
            }
        }
    }
    FString Path(const FString& Slot){return FPaths::ProjectSavedDir()/TEXT("SaveGames")/(Slot+TEXT(".sav"));}
