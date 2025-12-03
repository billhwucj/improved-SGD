# Harmonics Degree Configuration Guide

## Overview
This guide details the exact changes required to switch between different spherical harmonics degrees (0, 1, 2, 3) in the SGD implementation.

**Current Implementation:** Degree 0 (pre-computed colors, no view-dependent lighting)

---

## Degree Overview

| Degree | Harmonics Count | Floats per Gaussian | View-Dependent | GPU Computation | Performance |
|--------|-----------------|---------------------|-----------------|-----------------|-------------|
| **0** | 1 | 3 | ❌ No | ❌ None | ⭐⭐⭐⭐⭐ Best |
| **1** | 4 | 12 | ✅ Yes | ✅ Per frame | ⭐⭐⭐⭐ |
| **2** | 9 | 27 | ✅ Yes | ✅ Per frame | ⭐⭐⭐ |
| **3** | 16 | 48 | ✅ Yes | ✅ Per frame | ⭐⭐ |

---

## File Format & Data Layout

### Current .ply File Structure (62 floats per gaussian):
```
[0-2]:     position (3)
[3-5]:     normal/unused (3)
[6-53]:    spherical harmonics (48) - Degree 3 capacity
[54]:      opacity (1)
[55-57]:   scale (3)
[58-61]:   rotation/quaternion (4)
           Total: 62 floats
```

### Harmonic Coefficient Storage:
- **Degree 0:** 1 harmonic × 3 components = 3 floats → indices [6-8]
- **Degree 1:** 4 harmonics × 3 components = 12 floats → indices [6-17]
- **Degree 2:** 9 harmonics × 3 components = 27 floats → indices [6-32]
- **Degree 3:** 16 harmonics × 3 components = 48 floats → indices [6-53]

---

## Changes Required by Degree

### DEGREE 0 (Current Implementation) ✅

**Approach:** Pre-compute colors on CPU during load, no GPU updates

#### 1. `src/loader.js` - Data Extraction
```javascript
// Line 52
const harmonic = fromDataView(splatID, 6, 9)  // Extract harmonics [6-8]
const H_END = 6 + 48                          // Offset to opacity
```

#### 2. `src/loader.js` - Color Computation
```javascript
// Lines 89-102
const SH_C0 = 0.28209479177387814
const color = [
    0.5 + SH_C0 * harmonic[0],
    0.5 + SH_C0 * harmonic[1],
    0.5 + SH_C0 * harmonic[2]
]
colors.push(...color)
// harmonics.push(...harmonic)  // NOT sent to GPU
```

#### 3. `src/main.js` - GPU Buffer Setup
```javascript
// Only position, color, cov3D, opacity buffers needed
allGaussians = {
    gaussians: {
        colors: [],      // Pre-computed RGB
        cov3Ds: [],      // Pre-computed covariance
        opacities: [],
        positions: [],
        count: 0,
    }
};
```

#### 4. `shaders/splat_vertex.glsl` - Vertex Attributes
```glsl
in vec3 a_center;
in vec3 a_col;          // Pre-computed RGB color
in float a_opacity;
in vec3 a_covA;
in vec3 a_covB;
```

#### 5. `shaders/splat_fragment.glsl` - Fragment Output
```glsl
in vec3 col;            // Direct use of pre-computed color
// Output: fragColor = vec4(color * alpha, alpha);
```

---

### DEGREE 1 → Changes Needed

**Approach:** Store 4 harmonics, compute color per-frame based on view direction

#### 1. `src/loader.js` - Data Extraction
```javascript
// Change from:
const harmonic = fromDataView(splatID, 6, 9)   // 3 values
// Change to:
const harmonics = fromDataView(splatID, 6, 10) // 12 values (4 harmonics × 3)
```

#### 2. `src/loader.js` - Data Structure
```javascript
// Add harmonics array instead of colors
const harmonics = []  // NEW
const colors = []     // Remove or keep empty

// In extraction loop:
harmonics.push(...harmonics)  // Send harmonics to GPU instead of pre-computed colors
// colors.push(...color)      // REMOVE
```

#### 3. `src/main.js` - GPU Buffer Structure
```javascript
allGaussians = {
    gaussians: {
        harmonics: [],   // NEW: 12 floats per gaussian (4 × 3)
        // colors: [],   // REMOVE
        cov3Ds: [],
        opacities: [],
        positions: [],
        count: 0,
    }
};
```

#### 4. `src/utils.js` - WebGL Buffer Attributes
```javascript
// Add new attribute for harmonics
const harmonicsBuffer = gl.createBuffer()
gl.bindBuffer(gl.ARRAY_BUFFER, harmonicsBuffer)
gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(harmonicsData), gl.STATIC_DRAW)

const harmonicsLoc = gl.getAttribLocation(program, 'a_harmonics')
gl.enableVertexAttribArray(harmonicsLoc)
gl.vertexAttribPointer(harmonicsLoc, 3, gl.FLOAT, false, 12, 0)  // 4 vec3 harmonics
```

#### 5. `shaders/splat_vertex.glsl` - Add Attributes & Compute
```glsl
in vec3 a_center;
in float a_opacity;
in vec3 a_covA;
in vec3 a_covB;
in vec3 a_harmonic[4];  // NEW: 4 spherical harmonics

uniform mat4 viewmatrix;

out vec3 col;
out float depth;
out float scale_modif;
out vec4 con_o;
out vec2 xy;
out vec2 pixf;

// NEW: Helper function for SH evaluation
vec3 computeColorFromSH(vec3 dir, vec3[4] sh) {
    // SH basis functions for degree 1
    // l=0: Y_0_0 = 0.28209479
    // l=1: Y_1_-1, Y_1_0, Y_1_1
    const float SH_C0 = 0.28209479177387814;
    const float SH_C1 = 0.4886025119029200;
    
    vec3 color = vec3(0.5) + SH_C0 * sh[0];
    color += SH_C1 * dir.y * sh[1];
    color += SH_C1 * dir.z * sh[2];
    color += SH_C1 * dir.x * sh[3];
    
    return color;
}

void main() {
    // ... existing code ...
    
    // NEW: Compute camera direction in world space
    vec3 dir = normalize(p_orig - (inverse(viewmatrix) * vec4(0, 0, 0, 1)).xyz);
    
    // NEW: Compute color from harmonics based on view
    col = computeColorFromSH(dir, a_harmonic);
}
```

#### 6. `shaders/splat_fragment.glsl` - No Changes
```glsl
// Fragment shader stays mostly the same
// Uses the per-vertex computed col from vertex shader
```

---

### DEGREE 2 → Changes Needed

**Approach:** Store 9 harmonics, more accurate view-dependent lighting

#### 1. `src/loader.js` - Data Extraction
```javascript
// Change to:
const harmonics = fromDataView(splatID, 6, 15) // 27 values (9 harmonics × 3)
```

#### 2. `shaders/splat_vertex.glsl` - Add Attributes & Compute
```glsl
in vec3 a_harmonic[9];  // NEW: 9 spherical harmonics

// NEW: Helper function for SH evaluation (Degree 2)
vec3 computeColorFromSH(vec3 dir, vec3[9] sh) {
    const float SH_C0 = 0.28209479177387814;
    const float SH_C1 = 0.4886025119029200;
    const float SH_C2_0 = 1.0925484305920792;
    const float SH_C2_1 = -1.0925484305920792;
    const float SH_C2_2 = 0.3153915652525200;
    const float SH_C2_3 = -1.0925484305920792;
    const float SH_C2_4 = 0.5462742152960396;
    
    vec3 color = vec3(0.5) + SH_C0 * sh[0];
    
    // Degree 1
    color += SH_C1 * dir.y * sh[1];
    color += SH_C1 * dir.z * sh[2];
    color += SH_C1 * dir.x * sh[3];
    
    // Degree 2
    color += SH_C2_0 * dir.x * dir.y * sh[4];
    color += SH_C2_1 * dir.y * dir.z * sh[5];
    color += SH_C2_2 * (3.0 * dir.z * dir.z - 1.0) * sh[6];
    color += SH_C2_3 * dir.x * dir.z * sh[7];
    color += SH_C2_4 * (dir.x * dir.x - dir.y * dir.y) * sh[8];
    
    return color;
}
```

#### 3. All other changes similar to Degree 1

---

### DEGREE 3 → Changes Needed

**Approach:** Store all 16 harmonics, maximum visual quality with highest GPU cost

#### 1. `src/loader.js` - Data Extraction
```javascript
// Change to:
const harmonics = fromDataView(splatID, 6, 22) // 48 values (16 harmonics × 3)
```

#### 2. `shaders/splat_vertex.glsl` - Add Attributes & Compute
```glsl
in vec3 a_harmonic[16];  // NEW: 16 spherical harmonics (full degree 3)

// NEW: Full degree 3 SH computation
vec3 computeColorFromSH(vec3 dir, vec3[16] sh) {
    const float SH_C0 = 0.28209479177387814;
    const float SH_C1 = 0.4886025119029200;
    
    const float SH_C2_0 = 1.0925484305920792;
    const float SH_C2_1 = -1.0925484305920792;
    const float SH_C2_2 = 0.3153915652525200;
    const float SH_C2_3 = -1.0925484305920792;
    const float SH_C2_4 = 0.5462742152960396;
    
    const float SH_C3_0 = -0.5900435899266435;
    const float SH_C3_1 = 2.8906114426405538;
    const float SH_C3_2 = -0.4570457994644668;
    const float SH_C3_3 = 0.3731763325901154;
    const float SH_C3_4 = -0.4570457994644668;
    const float SH_C3_5 = 1.4453057213202769;
    const float SH_C3_6 = -0.5900435899266435;
    
    vec3 color = vec3(0.5) + SH_C0 * sh[0];
    
    // Degree 1
    color += SH_C1 * dir.y * sh[1];
    color += SH_C1 * dir.z * sh[2];
    color += SH_C1 * dir.x * sh[3];
    
    // Degree 2
    color += SH_C2_0 * dir.x * dir.y * sh[4];
    color += SH_C2_1 * dir.y * dir.z * sh[5];
    color += SH_C2_2 * (3.0 * dir.z * dir.z - 1.0) * sh[6];
    color += SH_C2_3 * dir.x * dir.z * sh[7];
    color += SH_C2_4 * (dir.x * dir.x - dir.y * dir.y) * sh[8];
    
    // Degree 3
    color += SH_C3_0 * dir.y * (5.0 * dir.z * dir.z - 1.0) * sh[9];
    color += SH_C3_1 * dir.x * dir.y * dir.z * sh[10];
    color += SH_C3_2 * dir.y * (5.0 * dir.z * dir.z - 3.0) * sh[11];
    color += SH_C3_3 * (5.0 * dir.z * dir.z * dir.z - 3.0 * dir.z) * sh[12];
    color += SH_C3_4 * dir.x * (5.0 * dir.z * dir.z - 3.0) * sh[13];
    color += SH_C3_5 * dir.x * dir.x * dir.z - dir.y * dir.y * dir.z * sh[14];
    color += SH_C3_6 * (dir.x * dir.x * dir.x - 3.0 * dir.x * dir.y * dir.y) * sh[15];
    
    return color;
}
```

#### 3. All other changes similar to Degree 1

---

## Performance Impact Summary

### Memory per Gaussian
- **Degree 0:** 3 floats (color pre-computed)
- **Degree 1:** 12 floats (harmonics)
- **Degree 2:** 27 floats (harmonics)
- **Degree 3:** 48 floats (harmonics)

### GPU Computation (per frame)
- **Degree 0:** ❌ None - just use pre-computed color
- **Degree 1:** ✅ Minor - 4 harmonics × 3 basis functions
- **Degree 2:** ✅ Moderate - 9 harmonics with quadratic terms
- **Degree 3:** ✅ High - 16 harmonics with cubic terms

### Bandwidth Cost
- **Degree 0:** Minimal (colors only)
- **Degree 1:** 4× memory increase
- **Degree 2:** 9× memory increase
- **Degree 3:** 16× memory increase

---

## Implementation Checklist for Switching Degrees

### To change from Degree 0 → Degree X:

- [ ] Update `src/loader.js`:
  - [ ] Modify `fromDataView()` harmonics extraction range
  - [ ] Update color computation logic or harmonics storage
  - [ ] Comment/uncomment `colors` vs `harmonics` arrays

- [ ] Update `src/main.js`:
  - [ ] Modify `allGaussians` data structure
  - [ ] Update GPU buffer initialization

- [ ] Update `src/utils.js`:
  - [ ] Add/modify attribute buffer setup for harmonics
  - [ ] Update vertex attribute pointer calls

- [ ] Update `shaders/splat_vertex.glsl`:
  - [ ] Add harmonic attribute inputs
  - [ ] Add `computeColorFromSH()` function
  - [ ] Call color computation in main()
  - [ ] Pass computed color to fragment shader

- [ ] Update `shaders/splat_fragment.glsl`:
  - [ ] No major changes (uses vertex shader output)

- [ ] Update `processData.py`:
  - [ ] Modify harmonic extraction (if processing offline data)
  - [ ] Update color computation logic

- [ ] Update `app.py`:
  - [ ] Modify harmonic extraction (if serving data)
  - [ ] Update color computation logic

---

## Constants Reference

### Spherical Harmonic Basis Coefficients

**Degree 0:**
```
SH_C0 = 0.28209479177387814
```

**Degree 1 (additional):**
```
SH_C1 = 0.4886025119029200
```

**Degree 2 (additional):**
```
SH_C2_0 = 1.0925484305920792
SH_C2_1 = -1.0925484305920792
SH_C2_2 = 0.3153915652525200
SH_C2_3 = -1.0925484305920792
SH_C2_4 = 0.5462742152960396
```

**Degree 3 (additional):**
```
SH_C3_0 = -0.5900435899266435
SH_C3_1 = 2.8906114426405538
SH_C3_2 = -0.4570457994644668
SH_C3_3 = 0.3731763325901154
SH_C3_4 = -0.4570457994644668
SH_C3_5 = 1.4453057213202769
SH_C3_6 = -0.5900435899266435
```

---

## Key Differences Summary

| Aspect | Degree 0 | Degree 1+ |
|--------|----------|-----------|
| Color Computation | CPU (pre-load) | GPU (per-frame) |
| View-Dependence | ❌ None | ✅ Dynamic |
| Harmonics Storage | 3 floats | 12/27/48 floats |
| GPU Buffer Update | ❌ Static | ✅ Stream/update |
| Basis Functions | 1 (Y_0_0) | 4/9/16 |
| Reflection Quality | ⭐ Low | ⭐⭐⭐ High |
| Performance Impact | ⭐⭐⭐⭐⭐ | ⭐/⭐⭐ |

---

## Recommended Starting Point

**For experimentation, start with Degree 1** because:
1. Minimal code changes from current Degree 0
2. Significant quality improvement (4× more harmonics)
3. Still maintains reasonable GPU performance
4. Good balance between quality and speed
