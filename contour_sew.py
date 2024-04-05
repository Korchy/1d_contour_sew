# Nikita Akimov
# interplanety@interplanety.org
#
# GitHub
#    https://github.com/Korchy/1d_contour_sew

import bmesh
import bpy
from bpy.props import FloatProperty
from bpy.types import Operator, Panel, Scene
from bpy.utils import register_class, unregister_class
from mathutils import kdtree, Vector
from mathutils.geometry import intersect_point_line

bl_info = {
    "name": "Contour Sew",
    "description": "Aligns selected loop by nearest surface",
    "author": "Nikita Akimov, Paul Kotelevets",
    "version": (1, 0, 0),
    "blender": (2, 79, 0),
    "location": "View3D > Tool panel > 1D > Slope Loop",
    "doc_url": "https://github.com/Korchy/1d_contour_sew",
    "tracker_url": "https://github.com/Korchy/1d_contour_sew",
    "category": "All"
}


# MAIN CLASS

class ContourSew:

    @classmethod
    def align_loop(cls, context, ob, nearest_ob):
        # ob - active object -> with selected loop for align
        # nearest_ob - second selected object (not active) -> align loop from "ob" by contour edges of this object
        # radius - proportional deformation radius
        # Make slope from selected loop
        ob = ob if ob else context.active_object
        # edit/object mode
        mode = ob.mode
        if ob.mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')
        # get contour edges from nearest_ob
        nearest_bm = bmesh.new()
        nearest_bm.from_mesh(nearest_ob.data)
        nearest_bm.edges.ensure_lookup_table()
        contour_edges = [
            (edge, nearest_ob.matrix_world * edge.verts[0].co, nearest_ob.matrix_world * edge.verts[1].co)
            for edge in nearest_bm.edges if len(edge.link_faces) <= 1
        ]
        # work with selected vertices from ob
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.verts.ensure_lookup_table()
        # source vertices
        selected_vertices = [vert for vert in bm.verts if vert.select]
        for vertex in selected_vertices:
            # find nearest edge from nearest_ob
            vertex_co_global = ob.matrix_world * vertex.co
            nearest_edge, min_distance, ratio = cls._nearest_edge(
                vert_data=(vertex, vertex_co_global),
                edges_data_list=contour_edges
            )
            # find point on edge
            point_on_edge = nearest_edge[1] + (nearest_edge[2] - nearest_edge[1]) * ratio
            translation = point_on_edge - vertex_co_global
            vertex.co.z += translation.z
        # save changed data to mesh
        bm.to_mesh(ob.data)
        bm.free()
        nearest_bm.free()
        # return mode back
        bpy.ops.object.mode_set(mode=mode)

    @classmethod
    def align_neighbour(cls, context, ob, radius):
        # align neighbour to selected loop vertices proportionally by radius
        ob = ob if ob else context.active_object
        # edit/object mode
        mode = ob.mode
        if ob.mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')
        # get bmesh from active mesh
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.verts.ensure_lookup_table()
        # source loop - selected vertices
        selected_vertices = [vert for vert in bm.verts if vert.select]
        # create kdtree from vertices
        size = len(selected_vertices)
        kd = kdtree.KDTree(size)
        for vertex in selected_vertices:
            kd.insert(Vector((vertex.co.x, vertex.co.y, 0.0)), vertex.index)    # in xy projection
        kd.balance()
        # get vertices neighbour to selected loop by radius
        neighbour_vertices = (
            vertex for vertex in bm.verts if
            (not vertex.select)
            and (not vertex.hide)
            and cls._is_neighbour(vertex, selected_vertices, radius)
        )
        for vertex in neighbour_vertices:
            # get the closest vertex from selected
            nearest_vertex = kd.find(
                co=Vector((vertex.co.x, vertex.co.y, 0.0))  # in xy projection
            )   # (Vector, index, distance)
            if nearest_vertex:
                nearest_vertex_z = cls._vertex_by_index(ob=ob, index=nearest_vertex[1]).co.z
                vertex.co.z = nearest_vertex_z - (nearest_vertex_z - vertex.co.z) * abs(nearest_vertex[2] / radius)
        # save changed data to mesh
        bm.to_mesh(ob.data)
        bm.free()
        # return mode back
        bpy.ops.object.mode_set(mode=mode)

    @staticmethod
    def _nearest_edge(vert_data, edges_data_list):
        # find nearest edge for vert
        #   vert_data = vertex (BMVert, global vert co)
        #   edges_data_list = list of edges [(BMEdge, edge vert1 global co, edge vert2 global co), ...]
        min_distance = None
        closest_edge = None
        ratio = None    # 0...1 ratio of point projection on edge
        vertex_xy_projection_co = Vector((vert_data[1].x, vert_data[1].y))
        for edge in edges_data_list:

            # in 3d
            # intersect = intersect_point_line(vert_data[1], edge[1], edge[2])
            # distance = (intersect[0] - vert_data[1]).length

            # in 2d (xy projection)
            edge_vertex1_xy_projection_co = Vector((edge[1].x, edge[1].y))
            edge_vertex2_xy_projection_co = Vector((edge[2].x, edge[2].y))
            intersect = intersect_point_line(
                vertex_xy_projection_co,
                edge_vertex1_xy_projection_co,
                edge_vertex2_xy_projection_co
            )
            distance = (intersect[0] - vertex_xy_projection_co).length
            # get point with min distance and projection on edge (not on in's continuation in any direction)
            if (
                    (closest_edge is None)  # first edge (any case)
                    or ((0.0 <= intersect[1] <= 1.0) and (ratio < 0.0 or ratio > 1.0))  # vert projects on edge (not on its continuation in any direction)
                    or ((0.0 <= intersect[1] <= 1.0) and (distance < min_distance))     # distance to this edge is less
            ):
                min_distance = distance
                closest_edge = edge
                ratio = intersect[1]
        return closest_edge, min_distance, ratio

    @staticmethod
    def _vertex_by_index(ob, index):
        # get vertex by index
        return next((v for v in ob.data.vertices if v.index == index), None)

    @staticmethod
    def _is_neighbour(vertex, vertices_list, radius):
        # check if vertex is neighbour to at least one vertex from vertices_list by radius
        for vert in vertices_list:
            if (vertex.co - vert.co).length <= radius:
                return True
        return False

    @staticmethod
    def ui(layout, context):
        # ui panel
        layout.operator(
            operator='contour_sew.align_loop',
            icon='IPO'
        )
        op = layout.operator(
            operator='contour_sew.align_neighbour',
            icon='IPO_BOUNCE'
        )
        op.radius = context.scene.contour_sew_prop_radius
        # props
        layout.prop(
            data=context.scene,
            property='contour_sew_prop_radius'
        )


# OPERATORS

class ContourSew_OT_align_loop(Operator):
    bl_idname = 'contour_sew.align_loop'
    bl_label = 'Align Loop'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        ContourSew.align_loop(
            context=context,
            ob=context.active_object,  # active
            nearest_ob=next((obj for obj in context.selected_objects if obj != context.active_object), None)
        )
        return {'FINISHED'}


class ContourSew_OT_align_neighbour(Operator):
    bl_idname = 'contour_sew.align_neighbour'
    bl_label = 'Align Neighbour'
    bl_options = {'REGISTER', 'UNDO'}

    radius = FloatProperty(
        name='Radius',
        default=1.0,
        min=0.0
    )

    def execute(self, context):
        ContourSew.align_neighbour(
            context=context,
            ob=context.active_object,
            radius=self.radius
        )
        return {'FINISHED'}


# PANELS

class ContourSew_PT_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_label = "Contour Sew"
    bl_category = '1D'

    def draw(self, context):
        ContourSew.ui(
            layout=self.layout,
            context=context
        )


# REGISTER

def register(ui=True):
    Scene.contour_sew_prop_radius = FloatProperty(
        name='Radius',
        default=1.0,
        min=0.0
    )
    register_class(ContourSew_OT_align_loop)
    register_class(ContourSew_OT_align_neighbour)
    if ui:
        register_class(ContourSew_PT_panel)


def unregister(ui=True):
    if ui:
        unregister_class(ContourSew_PT_panel)
    unregister_class(ContourSew_OT_align_neighbour)
    unregister_class(ContourSew_OT_align_loop)
    del Scene.contour_sew_prop_radius


if __name__ == "__main__":
    register()
