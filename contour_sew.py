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
    def align_loop(cls, context, ob, nearest_ob, radius):
        # ob - active object -> with selected loop for align
        # nearest_ob - second selected object (not active) -> align loop from "ob" by vertices of this object
        # radius - proportional deformation radius
        print(ob, nearest_ob)
        # Make slope from selected loop
        ob = ob if ob else context.active_object
        # edit/object mode
        mode = ob.mode
        if ob.mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')
        # get data loop from source mesh
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        # source vertices
        selected_vertices = [vert for vert in bm.verts if vert.select]

        # save changed data to mesh
        bm.to_mesh(ob.data)
        bm.free()
        # return mode back
        bpy.ops.object.mode_set(mode=mode)

    @staticmethod
    def ui(layout, context):
        # ui panel
        op = layout.operator(
            operator='contour_sew.align_loop',
            icon='IPO'
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

    radius = FloatProperty(
        name='Radius',
        default=1.0
    )

    def execute(self, context):
        ContourSew.align_loop(
            context=context,
            ob=context.active_object,   # active
            nearest_ob=next((obj for obj in context.selected_objects if obj != context.active_object), None),   # selected
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
        default=1.0
    )
    register_class(ContourSew_OT_align_loop)
    if ui:
        register_class(ContourSew_PT_panel)


def unregister(ui=True):
    if ui:
        unregister_class(ContourSew_PT_panel)
    unregister_class(ContourSew_OT_align_loop)
    del Scene.contour_sew_prop_radius


if __name__ == "__main__":
    register()
