// Azure Dragon claw V10.6: the Fab Dragon Claw as a SOLID, readable spirit claw.
// Structure: one-sided, near-opaque; key light comes from C++ (KeyDir: above-left of the viewer,
// world space) so every pose is shaded; the Fab normal atlas drives lighting, and its deviation
// from the smooth vertex normal (VNormal) darkens the grooves between scales and knuckles.
// Only the front-most claw surface survives: an unseen follower writes the claws into custom depth
// (stencil 214) and fragments behind it are dropped, while the claw still draws over the world.
// VeinTex: reference veins, triplanar on the baked rest pose (UV1 = XY, UV2 = (Z, joint), UV3 = |n.xy|).
// Vertex color: R along digit (talon: along nail), G talon, B forearm (1 at the guard end).
// V10.10: + DetailTex pebble-scale bump (triplanar on the rest pose, derivative bump on WorldPos =
// camera-relative world position), AttrA = 0 on the sculpted palm, CD1..CD4 = custom depth taps at
// sub-pixel offsets for an anti-aliased front-surface test.
// V10.14: + Disintegrate / DisintegrateCenter / DisintegrateAxis (expiry erosion, see below).
float3 N = normalize(Normal);
float3 Nv = normalize(VNormal);
float3 V = normalize(CamVec);
float3 L = normalize(KeyDir.xyz);

// ---- pebble-scale detail ------------------------------------------------------------------------
float palm = 1.0 - AttrA;
float3 P = float3(RestXY.x, RestXY.y, RestZJoint.x);
float3 RN = float3(RestN.x, RestN.y, sqrt(saturate(1.0 - dot(RestN, RestN))));
float3 w = pow(RN, 4.0);
w /= max(1e-4, w.x + w.y + w.z);
float3 Pd = P * lerp(1.0, 1.45, palm);
float hd = Texture2DSample(DetailTex, DetailTexSampler, Pd.yz).r * w.x
         + Texture2DSample(DetailTex, DetailTexSampler, Pd.xz + 0.5).r * w.y
         + Texture2DSample(DetailTex, DetailTexSampler, Pd.xy + 0.25).r * w.z;
float3 dpdx = ddx(WorldPos), dpdy = ddy(WorldPos);
float3 r1 = cross(dpdy, N), r2 = cross(N, dpdx);
float det = dot(dpdx, r1);
float3 surfGrad = (ddx(hd) * r1 + ddy(hd) * r2) * (sign(det) / max(abs(det), 1e-6));
float detailAmt = (1.0 - Attr.g) * (1.0 - 0.7 * Attr.b) * lerp(0.4, 1.0, palm);
N = normalize(N - surfGrad * DetailDepth * detailAmt);
float ndv = saturate(dot(N, V));
float key = saturate(dot(N, L) * 0.75 + 0.25);
float fill = saturate(dot(N, -L) * 0.5 + 0.5);
float cavity = pow(saturate(abs(dot(N, Nv))), 5.0); // abs: two-sided, the vertex normal is not flipped
float rim = pow(1.0 - ndv, 3.0);
float contour = pow(1.0 - ndv, 6.0);
float3 H = normalize(V + L);
float spec = pow(saturate(dot(N, H)), 36.0);

float along = Attr.r;
float talon = Attr.g;
float forearm = Attr.b;

float3 shadowCol = float3(0.004, 0.025, 0.034);
float3 midCol    = float3(0.030, 0.300, 0.360);
float3 litCol    = float3(0.300, 0.900, 0.950);
float3 cyan      = float3(0.220, 0.950, 1.000);
float3 white     = float3(0.800, 1.000, 1.000);

// ---- faint reference veins in the glass ---------------------------------------------------------
float3 vt = Texture2DSample(VeinTex, VeinTexSampler, P.yz).rgb * w.x
          + Texture2DSample(VeinTex, VeinTexSampler, P.xz + 0.37).rgb * w.y
          + Texture2DSample(VeinTex, VeinTexSampler, P.xy + 0.71).rgb * w.z;
float vein = saturate(vt.r * 1.1);
float haze = vt.g;
float pulse = pow(saturate(sin((along * 3.0 - Age * 1.6) * 6.2832) * 0.5 + 0.5), 5.0);
float joint = RestZJoint.y * (1.0 - talon);

// ---- body: three-tone form, cavities, crisp silhouette ------------------------------------------
float shade = key * cavity * lerp(1.0, lerp(0.72, 1.06, hd), detailAmt); // grooves between scales
float3 bodyCol = lerp(shadowCol, midCol, saturate(shade * 1.4)) + litCol * pow(shade, 2.2) * 0.9;
bodyCol += midCol * fill * 0.18 * cavity;
bodyCol += midCol * pow(ndv, 3.0) * 0.22;          // V10.10: inner glow where the glass faces the viewer
bodyCol += cyan * pow(1.0 - ndv, 1.6) * 0.18;      // and a broad fresnel layer under the crisp rim
bodyCol += cyan * rim * 1.5 + white * contour * 2.0;
bodyCol += white * spec * 1.6 * cavity;
bodyCol += cyan * vein * 0.25 * (0.4 + pulse);
bodyCol += white * joint * joint * (0.8 + 1.5 * spec);
float bodyA = 0.92 + rim * 0.08;

// ---- talons: dark chrome, white specular streak, cyan edge -------------------------------------
float3 R = reflect(-V, N);
float3 talonCol = lerp(float3(0.10, 0.24, 0.28), float3(0.025, 0.07, 0.09), along) * (0.35 + 0.65 * key);
talonCol += lerp(shadowCol, midCol, saturate(dot(R, L) * 0.5 + 0.5)) * 0.8;
talonCol += white * pow(saturate(dot(N, H)), 80.0) * 6.0;
talonCol += cyan * pow(1.0 - ndv, 3.0) * 2.4;
talonCol += white * smoothstep(0.16, 0.0, along) * 1.2;
float talonA = 0.97;

float3 color = lerp(bodyCol, talonCol, talon);
float alpha = lerp(bodyA, talonA, talon);

// ---- impact flash: the whole claw kicks bright for a beat as the rake lands ----------------------
color *= 1.0 + Impact * 0.8;
color += cyan * Impact * (rim * 2.0 + 0.25);

// ---- the forearm burns away toward the arm: wispy dissolve with a fire-bright front ---------------
float wisp = (haze - 0.5) * 0.35 + (vt.r - 0.5) * 0.15;
float keep = smoothstep(0.0, 0.6, (1.0 - forearm) + wisp);
float front = saturate((1.0 - keep) * keep * 4.0) * (1.0 - talon);
color += lerp(cyan, white, 0.35) * front * 2.4;
alpha = alpha * keep + front * 0.35;

// ---- V10.14 expiry: the claw erodes along a wind-biased front and blows away as motes ------------
// C++ spawns the motes on the same front. DisintegrateCenter is camera-relative like WorldPos; the
// axis is pre-divided by the claw's span. The pebble detail and vein haze (already sampled) make the
// edge grainy, so it reads as breaking up into dust. Disintegrate < -0.5 = not dissolving.
float gD = dot(WorldPos - DisintegrateCenter.xyz, DisintegrateAxis.xyz) + 0.5
         + (hd - 0.5) * 0.16 + (haze - 0.5) * 0.18;
float goneD = Disintegrate - gD;                                  // > 0: already blown away
float keepD = 1.0 - smoothstep(-0.015, 0.015, goneD);
float edgeD = exp(-goneD * goneD * 900.0) * step(-0.5, Disintegrate);
color += lerp(cyan, white, 0.6) * edgeD * 3.2;
alpha = (alpha + edgeD * 0.3) * keepD;

// ---- front-most surface only (custom depth from the two-sided follower mesh, stencil 214) --------
// V10.6: the glass is two-sided again and the follower writes both faces, so wherever the mesh is
// thin or open the nearest face fills the gap instead of leaving a hole.
// V10.10: centre + four sub-pixel taps, so overlapping digits get an anti-aliased edge instead of
// a stair-stepped cut.
float ownFront = abs(CustomStencil.r - 214.0) < 0.5 ? 1.0 : 0.0;
float bias = 2.0 + PixelDepth * 0.004;
float behind = ((PixelDepth > CustomDepth.r + bias ? 2.0 : 0.0)
              + (PixelDepth > CD1.r + bias ? 1.0 : 0.0) + (PixelDepth > CD2.r + bias ? 1.0 : 0.0)
              + (PixelDepth > CD3.r + bias ? 1.0 : 0.0) + (PixelDepth > CD4.r + bias ? 1.0 : 0.0)) / 6.0;
alpha *= 1.0 - ownFront * behind;

// ---- near occluders: the sword, the arms and anything within NearOcclusion cm stay in front -------
// The claws still ignore farther world geometry (walls 8 m out do not swallow them).
float nearHide = (SceneDepth.r < PixelDepth - 5.0 && SceneDepth.r < NearOcclusion) ? 1.0 : 0.0;
alpha *= 1.0 - nearHide;

return float4(color, saturate(alpha * Opacity * Reveal));
