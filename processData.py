import os
import struct
import json
import numpy as np


scene_min = np.array([float('inf')] * 3)
scene_max = np.array([-float('inf')] * 3)

def sort_by_scale(opacities, colors, positions, cov3ds, scales):
    """
    sort based on the splat's size
    
    params:
        opacities (np.ndarray): length of n
        colors (np.ndarray): length of 3 * n
        positions (np.ndarray): length of 3 * n
        cov3ds (list): length of 6 * n
        scales (np.ndarray): length of 3 * n (every 3 values is a splat's [x, y, z])
        
    return:
        tuple: sorted (opacities, colors, positions, cov3ds, scales)
    """
    # calculate the utility of each splat U = x * y * z
    scales_reshaped = scales.reshape(-1, 3)  # reshape the scales to [n, 3]
    utility_values = np.prod(scales_reshaped, axis=1)  # calculate the size of each splat
    
    # get the sorted index
    sorted_indices = np.argsort(utility_values)[::-1]
    
    # sort the data based on the index
    sorted_opacities = opacities[sorted_indices]
    sorted_colors = colors.reshape(-1, 3)[sorted_indices].flatten()
    sorted_positions = positions.reshape(-1, 3)[sorted_indices].flatten()
    sorted_cov3ds = np.array(cov3ds).reshape(-1, 6)[sorted_indices].flatten().tolist()
    sorted_scales = scales_reshaped[sorted_indices].flatten()
    
    return sorted_opacities, sorted_colors, sorted_positions, sorted_cov3ds, sorted_scales

def sort_by_brightness(opacities, colors, positions, cov3ds):
    """
    sort based on the splat brightness
    
    params:
        opacities (np.ndarray): length of n
        colors (np.ndarray): length of 3 * n
        positions (np.ndarray): length of 3 * n
        cov3ds (list): length of 6 * n
        
    return:
        tuple: sorted (opacities, colors, positions, cov3ds)
    """
    # get the RGB values
    colors_reshaped = colors.reshape(-1, 3)  # reshape the colors to [n, 3]
    
    # calculate the brightness
    brightness = (
        0.299 * colors_reshaped[:, 0] +  # R
        0.587 * colors_reshaped[:, 1] +  # G
        0.114 * colors_reshaped[:, 2]    # B
    )
    
    # get the sorted index
    sorted_indices = np.argsort(brightness)[::-1]
    
    # sort the data based on the index
    sorted_opacities = opacities[sorted_indices]
    sorted_colors = colors_reshaped[sorted_indices].flatten()
    sorted_positions = positions.reshape(-1, 3)[sorted_indices].flatten()
    sorted_cov3ds = np.array(cov3ds).reshape(-1, 6)[sorted_indices].flatten().tolist()
    
    return sorted_opacities, sorted_colors, sorted_positions, sorted_cov3ds

def sort_data(opacities, colors, positions, cov3ds):
    """
    sorting based on the opacities (descending)
    
    params:
        opacities (np.ndarray): length of n
        colors (np.ndarray): length of 3 * n
        positions (np.ndarray): length of 3 * n
        cov3ds (list): length of 6 * n
        
    return:
        tuple: sorted (opacities, colors, positions, cov3ds)
    """
    # the the sorting index
    sorted_indices = np.argsort(opacities)[::-1]
    
    # resort the data based on the utility function
    sorted_opacities = opacities[sorted_indices]
    sorted_colors = colors.reshape(-1, 3)[sorted_indices].flatten()
    sorted_positions = positions.reshape(-1, 3)[sorted_indices].flatten()
    sorted_cov3ds = np.array(cov3ds).reshape(-1, 6)[sorted_indices].flatten().tolist()
    return sorted_opacities, sorted_colors, sorted_positions, sorted_cov3ds

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def compute_cov3d(scale, mod, rot):
    # Compute scaling matrix
    S = np.diag([mod * scale[0], mod * scale[1], mod * scale[2]])

    # Quaternion to rotation matrix
    r, x, y, z = rot
    R = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - r * z), 2 * (x * z + r * y)],
        [2 * (x * y + r * z), 1 - 2 * (x * x + z * z), 2 * (y * z - r * x)],
        [2 * (x * z - r * y), 2 * (y * z + r * x), 1 - 2 * (x * x + y * y)]
    ])

    # Compute 3D world covariance matrix Sigma
    # M = S @ R
    M = R @ S
    # Sigma = M.T @ M
    Sigma = M @ M.T

    # Covariance is symmetric, only store upper triangular part
    cov3d = [Sigma[0, 0], Sigma[0, 1], Sigma[0, 2], Sigma[1, 1], Sigma[1, 2], Sigma[2, 2]]
    return cov3d

def process_ply_file(input_file, output_file):
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file '{input_file}' not found")

    print("Reading ply file")
    with open(input_file, 'rb') as file:
        content = file.read()

    # Parse header and Gaussian data
    header_end = content.find(b'end_header') + len(b'end_header') + 1
    header = content[:header_end].decode('utf-8')
    gaussian_count = int(next(line.split()[-1] for line in header.splitlines() if line.startswith('element vertex')))
    num_props = 62  # Total properties per Gaussian
    #gaussian_count = gaussian_count // 50  # Debugging, scale down for experiments

    opacities = np.zeros(gaussian_count)
    
    # ===== MODIFIED FOR SH DEGREE 1 =====
    # Original degree 0: pre-computed colors (3 floats per gaussian)
    # colors = np.zeros(3 * gaussian_count)
    
    # SH Degree 1: store raw SH coefficients (4 harmonics * 3 RGB = 12 floats per gaussian)
    # Format: [sh0_r, sh0_g, sh0_b, sh1_r, sh1_g, sh1_b, sh2_r, sh2_g, sh2_b, sh3_r, sh3_g, sh3_b]
    sh_coefficients = np.zeros(12 * gaussian_count)
    # ===== END MODIFIED =====
    
    cov3ds = []
    positions = np.zeros(3 * gaussian_count)
    scales = np.zeros(3 * gaussian_count)

    for i in range(gaussian_count):
        offset = header_end + i * num_props * 4
        position = struct.unpack_from('<fff', content, offset)
        
        # ===== MODIFIED FOR SH DEGREE 1 =====
        # PLY layout for SH (48 floats starting at index 6):
        # - f_dc_0, f_dc_1, f_dc_2 (indices 6,7,8) = DC term for R,G,B
        # - f_rest_0 to f_rest_44 (indices 9-53) = 45 additional SH coefficients
        # The f_rest values are stored grouped by channel: 
        #   f_rest_0..14 (15 values) = R channel higher order
        #   f_rest_15..29 (15 values) = G channel higher order  
        #   f_rest_30..44 (15 values) = B channel higher order
        # For degree 1, we need 3 coefficients per channel from f_rest
        
        # Read DC term (degree 0)
        harmonic_dc = struct.unpack_from('<fff', content, offset + 6 * 4)
        
        # Read all 45 f_rest values to extract degree 1 coefficients properly
        all_rest = struct.unpack_from('<' + 'f' * 45, content, offset + 9 * 4)
        
        # Original degree 0 only:
        # harmonic = struct.unpack_from('<fff', content, offset + 6 * 4)
        # ===== END MODIFIED =====
        
        opacity_raw = struct.unpack_from('<f', content, offset + (6 + 48) * 4)[0]
        scale = struct.unpack_from('<fff', content, offset + (6 + 49) * 4)
        rotation = struct.unpack_from('<ffff', content, offset + (6 + 52) * 4)

        rotation = np.array(rotation, dtype=np.float32)
        scale = np.array(scale, dtype=np.float32)
        length = np.sqrt(np.sum(rotation * rotation)).astype(np.float32)
        rotation /= length
        scale = np.exp(scale).astype(np.float32)
        cov3d = compute_cov3d(scale, 1, rotation)
        opacity = sigmoid(opacity_raw)

        # ===== MODIFIED FOR SH DEGREE 1 =====
        # Original degree 0 color computation:
        # sh_c0 = 0.28209479177387814
        # color = [0.5 + sh_c0 * harmonic[0], 0.5 + sh_c0 * harmonic[1], 0.5 + sh_c0 * harmonic[2]]
        # colors[3 * i: 3 * (i + 1)] = color
        
        # Store SH coefficients for degree 1 (4 harmonics per channel)
        # sh0 (DC term) - indices 0,1,2
        sh_coefficients[12 * i + 0] = harmonic_dc[0]  # sh0_r (f_dc_0)
        sh_coefficients[12 * i + 1] = harmonic_dc[1]  # sh0_g (f_dc_1)  
        sh_coefficients[12 * i + 2] = harmonic_dc[2]  # sh0_b (f_dc_2)
        
        # sh1 (first degree 1 term, l=1 m=-1) - from f_rest
        sh_coefficients[12 * i + 3] = all_rest[0]    # sh1_r (f_rest_0)
        sh_coefficients[12 * i + 4] = all_rest[15]   # sh1_g (f_rest_15)
        sh_coefficients[12 * i + 5] = all_rest[30]   # sh1_b (f_rest_30)
        
        # sh2 (second degree 1 term, l=1 m=0)
        sh_coefficients[12 * i + 6] = all_rest[1]    # sh2_r (f_rest_1)
        sh_coefficients[12 * i + 7] = all_rest[16]   # sh2_g (f_rest_16)
        sh_coefficients[12 * i + 8] = all_rest[31]   # sh2_b (f_rest_31)
        
        # sh3 (third degree 1 term, l=1 m=1)
        sh_coefficients[12 * i + 9] = all_rest[2]    # sh3_r (f_rest_2)
        sh_coefficients[12 * i + 10] = all_rest[17]  # sh3_g (f_rest_17)
        sh_coefficients[12 * i + 11] = all_rest[32]  # sh3_b (f_rest_32)
        # ===== END MODIFIED =====
        
        opacities[i] = opacity
        positions[3 * i: 3 * (i + 1)] = position
        scales[3 * i: 3 * (i + 1)] = scale
        cov3ds.extend(cov3d)

    print("Finish preprocessing")

    # opacities, colors, positions, cov3ds = sort_by_brightness(opacities, colors, positions, cov3ds) # brightness

    # opacities, colors, positions, cov3ds, scales = sort_by_scale(opacities, colors, positions, cov3ds, scales) # size
    
    # opacities, colors, positions, cov3ds = sort_data(opacities, colors, positions, cov3ds) # opacity

    # Convert all numpy arrays to native Python types for JSON serialization
    # ===== MODIFIED FOR SH DEGREE 1 =====
    data = {
        "opacities": opacities.astype(float).tolist(),
        # Original: "colors": colors.astype(float).tolist(),
        "sh_coefficients": sh_coefficients.astype(float).tolist(),  # 12 floats per gaussian
        "positions": positions.astype(float).tolist(),
        "cov3ds": [float(value) for value in cov3ds],
        "gaussian_count": int(gaussian_count)
    }
    # ===== END MODIFIED =====

    # Save data to JSON
    with open(output_file, 'w') as f:
        json.dump(data, f)
    print(f"Preprocessed data saved to {output_file}")


if __name__ == "__main__":
    # Example usage
    input_ply_file = "room.ply"  # Replace with your .ply file
    # output_json_file = "rooms.json"  
    # output_json_file = "opacity_rooms.json"  
    output_json_file = "splats_rooms.json"
    # output_json_file = "brightness_rooms.json"

    try:
        process_ply_file(input_ply_file, output_json_file)
    except FileNotFoundError as e:
        print(e)
