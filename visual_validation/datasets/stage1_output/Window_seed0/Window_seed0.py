import bpy
import bmesh
import math
import mathutils

def clear_scene():
    """Clear default Blender objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Create a simple diffuse material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_box(name, width, depth, height, location=(0, 0, 0), rotation=(0, 0, 0), material=None):
    """Create a box with explicit dimensions."""
    # Create mesh and object
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    
    # Scale the cube to match dimensions (cube is 1x1x1 by default)
    # We scale it relative to the origin then move it
    scale_mat = mathutils.Matrix.Scale(1.0, 4) # Identity’ish but let's use bmesh transform
    
    # Direct vertex manipulation for precision
    for v in bm.verts:
        v.co.x *= width
        v.co.y *= depth
        v.co.z *= height
    
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = location
    obj.rotation_euler = rotation
    
    if material:
        if len(obj.data.materials) == 0:
            obj.data.materials.append(material)
        else:
            obj.data.materials[0] = material
            
    return obj

def build_window():
    # Parameters for a wide rectangular window
    W = 3.5  # Total Width
    H = 2.0  # Total Height
    D = 0.12 # Depth of frame
    F_T = 0.15 # Frame thickness (border)
    NUM_PANELS = 3
    SLAT_COUNT = 30
    SLAT_THICKNESS = 0.012
    SLAT_DEPTH = 0.08  # Blinds depth should be slightly less than frame depth
    SLAT_TILT = math.radians(30) # Louver angle

    # Materials
    mat_wood = create_material("WoodTan", (0.85, 0.75, 0.55, 1.0))     # Light Tan
    mat_blinds = create_material("BlindCream", (0.98, 0.96, 0.88, 1.0)) # Pale Cream/White

    # 1. Outer Frame
    # Top and Bottom rails: Width W, Depth D, Height F_T
    create_box("FrameTop", W, D, F_T, (0, 0, H/2 - F_T/2), (0, 0, 0), mat_wood)
    create_box("FrameBottom", W, D, F_T, (0, 0, -H/2 + F_T/2), (0, 0, 0), mat_wood)
    # Left and Right rails: Width F_T, Depth D, Height H - 2*F_T
    create_box("FrameLeft", F_T, D, H - 2*F_T, (-W/2 + F_T/2, 0, 0), (0, 0, 0), mat_wood)
    create_box("FrameRight", F_T, D, H - 2*F_T, (W/2 - F_T/2, 0, 0), (0, 0, 0), mat_wood)

    # 2. Vertical Mullions
    inner_w = W - 2 * F_T
    mullion_w = F_T * 0.7 # Slightly thinner than outer frame
    for i in range(1, NUM_PANELS):
        x_pos = -W/2 + F_T + (i * (inner_w / NUM_PANELS))
        create_box(f"Mullion_{i}", mullion_w, D, H - 2*F_T, (x_pos, 0, 0), (0, 0, 0), mat_wood)

    # 3. Blinds in panels
    panel_inner_w = (inner_w - (NUM_PANELS - 1) * mullion_w) / NUM_PANELS
    for p in range(NUM_PANELS):
        # Calculate x center of the panel gap
        start_x = -W/2 + F_T + (p * (inner_w / NUM_PANELS)) + (panel_inner_w/2 if p==0 else 0)
        # A cleaner way to get center:
        gap_center_x = -W/2 + F_T + (p * inner_w / NUM_PANELS) + (inner_w / (2 * NUM_PANELS))
        # Correcting gap center logic for mullion presence
        if p == 0:
            gap_center_x = -W/2 + F_T + (panel_inner_w / 2)
        elif p == NUM_PANELS - 1:
            gap_center_x = W/2 - F_T - (panel_inner_w / 2)
        else:
            # Middle panels: center between mullions
            gap_center_x = -W/2 + F_T + (p * inner_w / NUM_PANELS) + (inner_w / (2 * NUM_PANELS)) - (mullion_w/2 if p==1 else 0) # simplify:
            # Just calculate offset from the start of the total width
            gap_center_x = -W/2 + F_T + (p * (inner_w / NUM_PANELS)) + (panel_inner_w / 2) - (mullion_w / 2 if p > 0 else 0)

        # Recalculate gap center more robustly
        # Total width = W. Left Frame at -W/2 to -W/2+F_T. Right frame at W/2-F_T to W/2.
        # Divide inner_w into NUM_PANELS spaces and NUM_PANELS-1 mullions.
        space_per_unit = (inner_w - (NUM_PANELS-1)*mullion_w) / NUM_PANELS
        current_x = -W/2 + F_T + space_per_unit/2
        for p_idx in range(NUM_PANELS):
            # center of the current panel
            panel_x = current_x
            
            # Slat generation
            z_start = -H/2 + F_T + 0.05
            z_end = H/2 - F_T - 0.05
            z_step = (z_end - z_start) / max(1, SLAT_COUNT - 1)

            for s in range(SLAT_COUNT):
                z_pos = z_start + s * z_step
                # Slat: width=panel_inner_w, depth=SLAT_DEPTH, height=SLAT_THICKNESS
                # Rotated around X axis for louver effect
                create_box(f"Slat_{p_idx}_{s}", 
                           space_per_unit, SLAT_DEPTH, SLAT_THICKNESS, 
                           (panel_x, 0, z_pos), 
                           (SLAT_TILT, 0, 0), 
                           mat_blinds)
            
            # Move current_x to the next panel center
            current_x += space_per_unit + mullion_w

if __name__ == "__main__":
    clear_scene()
    build_window()
