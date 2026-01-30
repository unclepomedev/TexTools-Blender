# SPDX-License-Identifier: GPL-3.0-or-later

import bmesh
import bpy
from bmesh.types import BMesh
from bpy.types import Object


def align_uv_rectify(obj: Object, bm: BMesh, uv_layer_name: str):
    """
    Rectify logic as a wrapper for Blender's native 'follow_active_quads'.

    NOTE: Only processes Quads. Triangles and N-gons are explicitly excluded
    to prevent UV layout distortion during normalization.
    """
    mesh_data = obj.data
    uv_layer = bm.loops.layers.uv.get(uv_layer_name)
    if uv_layer is None:
        print(f"Error: UV layer '{uv_layer_name}' not found.")
        return False

    all_selected = [f for f in bm.faces if f.select]
    target_faces = [f for f in all_selected if len(f.verts) == 4]

    if not target_faces:
        return False

    active_face = bm.faces.active

    if not active_face or active_face not in target_faces:
        active_face = target_faces[0]
        bm.faces.active = active_face

    loops = active_face.loops
    loops[0][uv_layer].uv = (0, 0)
    loops[1][uv_layer].uv = (1, 0)
    loops[2][uv_layer].uv = (1, 1)
    loops[3][uv_layer].uv = (0, 1)

    bmesh.update_edit_mesh(mesh_data)

    try:
        bpy.ops.uv.follow_active_quads(mode="EVEN")
    except RuntimeError:
        return False

    returned_bmesh: BMesh = bmesh.from_edit_mesh(mesh_data)
    uv_layer = returned_bmesh.loops.layers.uv.get(uv_layer_name)

    selected_faces = [f for f in returned_bmesh.faces if f.select and len(f.verts) == 4]

    if not selected_faces:
        return True

    min_x, max_x = float("inf"), float("-inf")
    min_y, max_y = float("inf"), float("-inf")

    has_verts = False
    for face in selected_faces:
        for loop in face.loops:
            u, v = loop[uv_layer].uv
            if u < min_x:
                min_x = u
            if u > max_x:
                max_x = u
            if v < min_y:
                min_y = v
            if v > max_y:
                max_y = v
            has_verts = True

    if not has_verts:
        return True

    width = max_x - min_x
    height = max_y - min_y
    if width == 0:
        width = 1
    if height == 0:
        height = 1

    for face in selected_faces:
        for loop in face.loops:
            u, v = loop[uv_layer].uv
            loop[uv_layer].uv = ((u - min_x) / width, (v - min_y) / height)

    bmesh.update_edit_mesh(mesh_data)
    return True
