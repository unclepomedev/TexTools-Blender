# SPDX-License-Identifier: GPL-3.0-or-later

import bpy


def ensure_uv_morph_node_group() -> bpy.types.NodeTree:
    """
    Creates and returns the Geometry Nodes group for UV Morph if it doesn't exist.
    """
    group_name = "TT_UV_Morph"

    if group_name in bpy.data.node_groups:
        return bpy.data.node_groups[group_name]

    ng = bpy.data.node_groups.new(name=group_name, type="GeometryNodeTree")

    # IO =========================================================================================
    ng.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")

    input_factor = ng.interface.new_socket(
        name="Factor", in_out="INPUT", socket_type="NodeSocketFloat"
    )
    input_factor.default_value = 1.0
    input_factor.min_value = 0.0
    input_factor.max_value = 1.0

    input_uv_name = ng.interface.new_socket(
        name="UV Map", in_out="INPUT", socket_type="NodeSocketString"
    )
    input_uv_name.default_value = "UVMap"

    # Node Creation =================================================================================
    ng.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    nodes = ng.nodes
    links = ng.links

    node_in = nodes.new("NodeGroupInput")
    node_in.location = (-800, 0)
    node_out = nodes.new("NodeGroupOutput")
    node_out.location = (800, 0)

    node_split = nodes.new("GeometryNodeSplitEdges")
    node_split.location = (-600, 0)

    node_uv_attr = nodes.new("GeometryNodeInputNamedAttribute")
    node_uv_attr.data_type = "FLOAT_VECTOR"
    node_uv_attr.location = (-400, 200)

    node_pos = nodes.new("GeometryNodeInputPosition")
    node_pos.location = (-400, 0)

    node_mix = nodes.new("ShaderNodeMix")
    node_mix.data_type = "VECTOR"
    node_mix.clamp_factor = True
    node_mix.location = (-100, 100)
    node_mix.label = "Morph Mix"

    node_set_pos = nodes.new("GeometryNodeSetPosition")
    node_set_pos.location = (200, 0)

    # linking =========================================================================
    links.new(node_in.outputs["Geometry"], node_split.inputs["Mesh"])
    links.new(node_split.outputs["Mesh"], node_set_pos.inputs["Geometry"])
    links.new(node_set_pos.outputs["Geometry"], node_out.inputs["Geometry"])

    links.new(node_in.outputs["UV Map"], node_uv_attr.inputs["Name"])

    links.new(node_in.outputs["Factor"], node_mix.inputs["Factor"])
    links.new(node_pos.outputs["Position"], node_mix.inputs["A"])
    links.new(node_uv_attr.outputs["Attribute"], node_mix.inputs["B"])

    links.new(node_mix.outputs["Result"], node_set_pos.inputs["Position"])

    return ng
