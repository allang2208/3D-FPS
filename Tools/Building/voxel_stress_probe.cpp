// Offline joint-strength probe for the 20 cm voxel building system.
//
// Thin harness around Source/FPSGAME/Building/VoxelJointStrength.h - the same code the game uses
// for the building panel tooltip - so the published span/load numbers can always be re-derived.
//
// Build and run:  powershell -File Tools/Building/run_voxel_stress_probe.ps1
// Contract and numbers: Docs/Building/voxel-build-workflow.md

#include "VoxelJointStrength.h"

#include <cstdio>

namespace
{
using VoxelJointStrength::FMaterial;

const FMaterial Materials[] = {
    { 600.0,  700000.0, 260000.0, 120000.0 },  // wood  (keep in sync with UVoxelBuildPalette::Physical())
    { 2600.0, 6000000.0, 900000.0, 80000.0 },  // stone
    { 2600.0, 6000000.0, 900000.0, 80000.0 },  // marble
};
const char* Names[] = { "wood", "stone", "marble" };

void ReportSpan(const FMaterial& Material, int SpanCells, double ExtraLoadKg)
{
    const double Ratio = VoxelJointStrength::Ratio(Material, SpanCells, ExtraLoadKg);
    printf("   ceiling %5.2f m span, %-7s worst=%7.3f %s\n", SpanCells * 0.2, ExtraLoadKg > 0 ? "+100kg" : "self",
        Ratio, Ratio > 1.0 ? "BREAK" : "ok");
}
}

int main()
{
    printf("Contract: every material holds a 2.0 m clear span with a 100 kg player mid-span,\n");
    printf("and fails before roughly 3-4 m. TensionPa is the knob; re-check after any change.\n");
    for (int Index = 0; Index < 3; ++Index)
    {
        const FMaterial& Material = Materials[Index];
        printf("\n=== %s  density=%.0f kg/m3  comp=%.0f tens=%.0f shear=%.0f (%.2f kg/cell)\n",
            Names[Index], Material.DensityKgM3, Material.CompressionPa, Material.TensionPa, Material.ShearPa,
            Material.MassPerCellKg());
        printf("   load per m^2 section: %.1f t   mass per cell: %.2f kg\n",
            Material.LoadPerSquareMeterT(), Material.MassPerCellKg());
        printf("   max clear span: self=%.2f m   with 100kg mid-span=%.2f m\n",
            VoxelJointStrength::MaxSpanMeters(Material, 0.0), VoxelJointStrength::MaxSpanMeters(Material, 100.0));
        for (int Span : { 5, 10, 12, 14, 16, 20 })
        {
            ReportSpan(Material, Span, 0.0);
            ReportSpan(Material, Span, 100.0);
        }
    }
    return 0;
}
