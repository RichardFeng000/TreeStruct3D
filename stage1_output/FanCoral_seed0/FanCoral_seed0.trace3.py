import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

def clear_scene():
    """Clears all objects from the default scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(to='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def generate_coral_skeleton():
    """Generates the branching structure of a sea fan."""
    # Constants for growth
    ROOT_HEIGHT = 1.2
    ITERATIONS = 6
    INITIAL_LENGTH = 0.7
    BIFURCATION_ANGLE = math.radians(35)
    LENGTH_DECAY = 0.8
    RADIUS_DECAY = 0.75
    PLANAR_STRICTNESS = 0.1  # Variance in Y axis

    segments = [] # List of (start, end, start_rad, end_rad)
    
    # Root segment: straight up from origin
    root_start = Vector((0, 0, 0))
    root_end = Vector((0, 0, ROOT_HEIGHT))
    segments.append((root_start, root_end, 1.5, 1.0)) # Radii as multipliers

    def grow(start, direction, length, radius, depth):
        if depth <= 0:
            return [start]
        
        # Calculate end point of this branch
        end = start + direction * length
        new_radius = radius * RADIUS_DECAY
        segments.append((start, end, radius, new_radius))
        
        # Fan-like growth: primarily rotate around Y axis to stay in XZ plane
        y_axis = Vector((0, 1, 0))
        
        # Random variations for organic look
        angle1 = BIFURCATION_ANGLE + random.uniform(-0.15, 0.15)
        angle2 = -BIFURCATION_ANGLE + random.uniform(-0.15, 0.15)
        
        # Rotate directions around Y axis
        rot1 = Matrix.Rotation(angle1, 4, y_axis)
        dir1 = (rot1 @ direction).normalized()
        # Add small organic jitter in all axes
        jitter1 = Vector((random.uniform(-0.08, 0.08), 
                         random.uniform(-PLANAR_STRICTNESS, PLANAR_STRICTNESS), 
                         random.uniform(-0.08, 0.08)))
        dir1 = (dir1 + jitter1).normalized()

        rot2 = Matrix.Rotation(angle2, 4, y_axis)
        dir2 = (rot2 @ direction).normalized()
        jitter2 = Vector((random.uniform(-0.08, 0.08), 
                         random.uniform(-PLANAR_STRICTNESS, PLANAR_STRICTNESS), 
                         random.uniform(-0.08, 0.08)))
        dir2 = (dir2 + jitter2).normalized()

        points = []
        points.extend(grow(end, dir1, length * LENGTH_DECAY, new_radius, depth - 1))
        points.extend(grow(end, dir2, length * LENGTH_DECAY, new_radius, depth - 1))
        return points

    # Start growing from the root top (pointing up Z)
    grow(root_end, Vector((0, 0, 1)), INITIAL_LENGTH, 1.0, ITERATIONS)
    
    # Create cross-links for the "net" structure
    endpoints = []
    for s in segments:
        endpoints.append(s[1])
    
    unique_points = []
    for p in endpoints:
        is_new = True
        for up in unique_points:
            if (p - up).length < 0.2:
                is_new = False
                break
        if is_new:
            unique_points.append(p)

    link_dist = INITIAL_LENGTH * 1.1
    for i in range(len(unique_points)):
        for j in range(i + 1, len(unique_points)):
            p1 = unique_points[i]
            p2 = unique_points[j]
            dist = (p1 - p2).length
            if 0.2 < dist < link_dist:
                # Only link if height is similar and not too close to root base
                if abs(p1.z - p2.z) < 0.5 and p1.z > ROOT_HEIGHT * 0.5:
                    avg_rad = 0.4 # thinner links
                    segments.append((p1, p2, avg_rad, avg_rad))

    return segments

def build_coral_geometry(segments):
    """Constructs the coral using Curves converted to Mesh."""
    curve_data = bpy.data.curves.new('SeaFanCurve', type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.fill_mode = 'FULL'
    curve_data.bevel_resolution = 4
    # Global base thickness; radius of points will multiply this
    curve_data.bevel_depth = 0.025 

    for start, end, r1, r2 in segments:
        spline = curve_data.splines.new('POLY')
        spline.points.add(1) # Add second point (initial point is already there)
        
        # IMPORTANT: In Blender 3D curves, .co requires a 4-element vector (x, y, z, w)
        spline.points[0].co = (start.x, start.y, start.z, 1.0)
        spline.points[1].co = (end.x, end.y, end.z, 1.0)
        
        # The radius property of the point scales the bevel_depth
        spline.points[0].radius = r1
        spline.points[1].radius = r2

    obj = bpy.data.objects.new('SeaFanCoral', curve_data)
    bpy.context.collection.objects.link(obj)
    
    # Convert to mesh for modifiers and final geometry
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target='MESH')
    
    return bpy.context.active_object

def main():
    clear_scene()
    
    # 1. Generate skeleton data
    segments = generate_coral_skeleton()
    
    # 2. Build geometry from curves to mesh
    coral_obj = build_coral_geometry(segments)
    
    # 3. Add smooth modifier for organic feel
    mod_smooth = coral_obj.modifiers.new(name="Smooth", type='SMOOTH')
    mod_smooth.factor = 0.5
    mod_smooth.iterations = 4

    # 4. Material - Warm sandy beige / tan
    mat_beige = create_material("CoralBeige", (0.82, 0.73, 0.52, 1.0))
    coral_obj.data.materials.append(mat_beige)

if __name__ == "__main__":
    main()
