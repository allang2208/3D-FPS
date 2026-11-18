void AHillsNightPortal::AddAssetPaths(TArray<FSoftObjectPath>& Paths)
{
    for(const auto* Path:{FramePath,CurtainPath,MaterialPath,BeamMeshPath,BeamMaterialPath})Paths.AddUnique(FSoftObjectPath(Path));
}

// BeginPlay requests this manifest; keep the existing callback and visual setup.
TArray<FSoftObjectPath> Paths;AddAssetPaths(Paths);
