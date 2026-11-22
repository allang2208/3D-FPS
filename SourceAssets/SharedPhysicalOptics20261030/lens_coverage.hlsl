// Peakwatch has one closed glass disk. Its rasterized geometry is the complete
// aperture, including during draw/release and first-person FOV correction.
// Comparing its corrected pixel world position to an uncorrected world plane
// slices that disk, exposing the unzoomed scene and moving the seam with pose.
if (abs(ReticleStyle - 7.0) < 0.25)
    return saturate(Blend);

// The position input excludes the first-person vertex transform. Both camera
// poses and scaled fitted meshes therefore classify a complete rear surface.
return saturate(Blend) * step(dot(Position - Center, Forward), Depth);
