# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy
from bpy.props import *

# Precicion for display of float values.
PRECISION = 6

"""
Name: 'Measure panel'
Blender: 250
"""
__author__ = ["Buerbaum Martin (Pontiac)"]
__url__ = ["http://gitorious.org/blender-scripts/blender-measure-panel-script",
    "http://blenderartists.org/forum/showthread.php?t=177800"]
__version__ = '0.6.1'
__bpydoc__ = """
Measure panel

This script displays in OBJECT MODE:
* The distance of the 3D cursor to the origin of the
  3D space (if NOTHING is selected).
* The distance of the 3D cursor to the center of an object
  (if exactly ONE object is selected).
* The distance between 2 object centers
  (if exactly TWO objects are selected).
* The surface area of any selected mesh object.

Display in EDIT MODE (Local and Global space supported):
* The distance of the 3D cursor to the origin
  (in Local space it is the object center instead).
* The distance of the 3D cursor to a selected vertex.
* The distance between 2 selected vertices.

Usage:

This functionality can be accessed via the
"Properties" panel in 3D View ([N] key).

It's very helpful to use one or two "Empty" objects with
"Snap during transform" enabled for fast measurement.

Version history:
v0.6.1 - Updated reenter_editmode operator description.
    Fixed search for selected mesh objects.
    Added "BU^2" after values that are not yet translated via "unit".
v0.6
    *) Fix:  Removed EditMode/ObjectMode toggle stuff. This causes all the
       crashes and is generally not stable.
       Instead I've added a manual "refresh" button.
       I registered a new operator OBJECT_OT_reenter_editmode for this.
    *) Use "unit" settings (i.e. none/metric/imperial)
    *) Fix: Only display surface area (>=3 objects) if return value is >=0.
    *) Minor: Renamed objectFaceArea to objectSurfaceArea
    *) Updated Vector() and tuple() usage.
    *) Fixed some comments.
v0.5 - Global surface area (object mode) is now calculated as well.
    Support area calculation for face selection.
    Also made measurement panel closed by default. (Area calculation
    may use up a lot of CPU/RAM in extreme cases)
v0.4.1 - Various cleanups.
    Using the shorter "scene" instead of "context.scene"
    New functions measureGlobal() and measureLocal() for
    user-friendly access to the "space" setting.
v0.4 - Calculate & display the surface area of mesh
    objects (local space only right now).
    Expanded global/local switch.
    Made "local" option for 3Dcursor-only in edit mode actually work.
    Fixed local/global calculation for 3Dcursor<->vertex in edit mode.
v0.3.2 - Fixed calculation & display of local/global coordinates.
    The user can now select via dropdown which space is wanted/needed
    Basically this is a bugfix and new feature at the same time :-)
v0.3.1 - Fixed bug where "measure_panel_dist" wasn't defined
    before it was used.
    Also added the distance calculation "origin -> 3D cursor" for edit mode.
v0.3 - Support for mesh edit mode (1 or 2 selected vertices)
v0.2.1 - Small fix (selecting nothing didn't calculate the distance
    of the cursor from the origin anymore)
v0.2 - Distance value is now displayed via a FloatProperty widget (and
    therefore saved to file too right now [according to ideasman42].
    The value is save inside the scene right now.)
    Thanks goes to ideasman42 (Campbell Barton) for helping me out on this.
v0.1 - Initial revision. Seems to work fine for most purposes.

TODO:

There is a random segmentation fault when moving the 3D cursor in edit mode.
Mainly this happens when clicking inside the white circle of the translation
manipulator. There may be other cases though.

See the other "todo" comments below.
"""

# User friendly access to the "space" setting.
def measureGlobal(scene):
    return (scene.measure_panel_transform == "measure_global")


# User friendly access to the "space" setting.
def measureLocal(scene):
    return (scene.measure_panel_transform == "measure_local")


class OBJECT_OT_reenter_editmode(bpy.types.Operator):
    bl_label = "Re-enter EditMode"
    bl_idname = "reenter_editmode"
    bl_description = "Update mesh data of an active mesh object." \
        " This is done by exiting and re-entering mesh edit mode."

    def invoke(self, context, event):

        # Get the active object.
        obj = context.active_object

        if (obj and obj.type == 'MESH' and context.mode == 'EDIT_MESH'):
            # Exit and re-enter mesh EditMode.
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
            return ('FINISHED',)

        return ('CANCELLED',)


class VIEW3D_PT_measure(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Measure"
    #bl_default_closed = True
    bl_default_closed = False

    def draw(self, context):
        from Mathutils import Vector, Matrix

        layout = self.layout
        scene = context.scene
        self.scene = context.scene

        # Get the active object.
        obj = context.active_object
        
        # Define a temporary attribute for the distance value
        scene.FloatProperty(
            name="Distance",
            attr="measure_panel_dist",
            precision=PRECISION,
            unit="LENGTH")

        TRANSFORM = [
            ("measure_global", "Global",
                "Calculate values in global space."),
            ("measure_local", "Local",
                "Calculate values inside the local object space.")]

        # Define dropdown for the global/local setting
        bpy.types.Scene.EnumProperty(
            attr="measure_panel_transform",
            name="Space",
            description="Choose in which space you want to measure.",
            items=TRANSFORM,
            default='measure_global')

        if (context.mode == 'EDIT_MESH'):
            if (obj and obj.type == 'MESH' and obj.data):
                # "Note: a Mesh will return the selection state of the mesh
                # when EditMode was last exited. A Python script operating
                # in EditMode must exit EditMode before getting the current
                # selection state of the mesh."
                # http://www.blender.org/documentation/249PythonDoc/
                # /Mesh.MVert-class.html#sel
                # We can only provide this by existing & re-entering EditMode.
                # @todo: Better way to do this?

                # Get mesh data from Object.
                mesh = obj.data

                # Get transformation matrix from object.
                ob_mat = obj.matrix
                # Also make an inversed copy! of the matrix.
                ob_mat_inv = ob_mat.copy().invert()
                #Matrix.invert(ob_mat_inv)

                # Get the selected vertices.
                # @todo: Better (more efficient) way to do this?
                verts_selected = [v for v in mesh.verts if v.selected == 1]

                if len(verts_selected) == 0:
                    # Nothing selected.
                    # We measure the distance from the origin to the 3D cursor.

                    # Convert to local space, if needed.
                    if measureLocal(scene):
                        scene.measure_panel_dist = ((scene.cursor_location - obj.location) * ob_mat_inv).length 
                    else:
                        scene.measure_panel_dist = scene.cursor_location.length 

                    row = layout.row()
                    row.prop(scene, "measure_panel_dist")

                    row = layout.row()
                    row.label(text="", icon='CURSOR')
                    row.label(text="", icon='ARROW_LEFTRIGHT')
                    row.label(text="Origin [0,0,0]")

                    row = layout.row()
                    row.operator("reenter_editmode",
                        text="Update selection & distance")
#                       @todo
#                        description="The surface area value can" \
#                            " not be updated in mesh edit mode" \
#                            " automatically. Press this button" \
#                            " to do this manually, after you changed" \
#                            " the selection.")

                    row = layout.row()
                    row.prop(scene,
                        "measure_panel_transform",
                        expand=True)

                elif len(verts_selected) == 1:
                    # One vertex selected.
                    # We measure the distance from the
                    # selected vertex object to the 3D cursor.

                    # Convert to local or global space.
                    if measureLocal(scene):
                        scene.measure_panel_dist = \
                                (verts_selected[0].co - (scene.cursor_location - obj.location) * ob_mat_inv).length 
                    else:
                        scene.measure_panel_dist = \
                                (verts_selected[0].co * ob_mat + obj.location - scene.cursor_location).length 

                    row = layout.row()
                    row.prop(scene, "measure_panel_dist")

                    row = layout.row()
                    row.label(text="", icon='CURSOR')
                    row.label(text="", icon='ARROW_LEFTRIGHT')
                    row.label(text="", icon='VERTEXSEL')

                    row = layout.row()
                    row.operator("reenter_editmode",
                        text="Update selection & distance")

                    row = layout.row()
                    row.prop(scene,
                        "measure_panel_transform",
                        expand=True)

                elif len(verts_selected) == 2:
                    # Two vertices selected.
                    # We measure the distance between the
                    # two selected vertices.

                    # Convert to local or global space.
                    if measureLocal(scene):
                        scene.measure_panel_dist = \
                                (verts_selected[0].co - verts_selected[1].co).length
                    else:
                        scene.measure_panel_dist = \
                                ((verts_selected[0].co - verts_selected[1].co) * ob_mat).lentgh

                    row = layout.row()
                    row.prop(scene, "measure_panel_dist")

                    row = layout.row()
                    row.label(text="", icon='VERTEXSEL')
                    row.label(text="", icon='ARROW_LEFTRIGHT')
                    row.label(text="", icon='VERTEXSEL')

                    row = layout.row()
                    row.operator("reenter_editmode",
                        text="Update selection & distance")

                    row = layout.row()
                    row.prop(scene,
                        "measure_panel_transform",
                        expand=True)

                else:
                    # Get selected faces
                    # @todo: Better (more efficient) way to do this?
                    faces_selected = [f for f in mesh.faces if f.selected == 1]

                    if len(faces_selected) > 0:
                        area = self.objectSurfaceArea(obj, True, measureGlobal(self.scene))
                        row = self.layout.row()
                        row.label(text="Selected Face Area: "+str(round(area, PRECISION))+self.units(2), icon='FACESEL')

                        row = layout.row()
                        row.operator("reenter_editmode",
                            text="Update selection & area")

                        row = layout.row()
                        row.prop(scene,
                            "measure_panel_transform",
                            expand=True)

                    else:
                        row = layout.row()
                        row.label(text="Selection not supported.", icon='INFO')

                        row = layout.row()
                        row.operator("reenter_editmode",
                            text="Update selection")

        elif (context.mode == 'OBJECT'):
            # We are working on object mode.

            if (context.selected_objects
                and len(context.selected_objects) > 2):
                # We have more that 2 objects selected...

                mesh_objects = [o for o in context.selected_objects
                    if (o.type == 'MESH' and o.data)]

                if (len(mesh_objects) > 0):
                    # ... and at least one of them is a mesh.

                    # Calculate and display surface area of the objects.
                    # @todo: Convert to scene units! We do not have a
                    # FloatProperty field here for automatic conversion.
                    #self.addObjectAreas(mesh_objects)
                    #self.addObjectVolumes(mesh_objects)
                    self.addAreasAndVolumes(mesh_objects)

                    row = layout.row()
                    row.prop(scene,
                        "measure_panel_transform",
                        expand=True)

            elif (context.selected_objects
                  and len(context.selected_objects) == 2):
                # 2 objects selected.
                # We measure the distance between the 2 selected objects.
                obj1 = context.selected_objects[0]
                obj2 = context.selected_objects[1]
                scene.measure_panel_dist = (obj1.location - obj2.location).length

                row = layout.row()
                row.prop(scene, "measure_panel_dist")

                row = layout.row()
                row.label(text=obj1.name, icon='OBJECT_DATA')
                #row.prop(obj1, "name", text="", icon='OBJECT_DATA')
                row.label(text="", icon='ARROW_LEFTRIGHT')
                row.label(text=obj2.name, icon='OBJECT_DATA')
                #row.prop(obj2, "name", text="", icon='OBJECT_DATA')

                # Calculate and display surface area of the objects.
                #self.addObjectAreas(mesh_objects)
                #self.addObjectVolumes(mesh_objects)
                self.addAreasAndVolumes(mesh_objects)

                row = layout.row()
                row.prop(scene,
                    "measure_panel_transform",
                    expand=True)

            elif (obj and  obj.selected
                  and context.selected_objects
                  and len(context.selected_objects) == 1):
                # One object selected.
                # We measure the distance from the
                # selected & active) object to the 3D cursor.
                scene.measure_panel_dist = (obj.location - scene.cursor_location).length

                row = layout.row()
                #row.label(text=str(dist_vec.length))
                row.prop(scene, "measure_panel_dist")

                row = layout.row()
                row.label(text="", icon='CURSOR')
                row.label(text="", icon='ARROW_LEFTRIGHT')
                row.label(text=obj.name, icon='OBJECT_DATA')
                #row.prop(obj, "name", text="")

                # Calculate and display surface area of the object.
                #self.addObjectAreas(obj)
                #self.addObjectVolumes(obj)
                self.addAreasAndVolumes(obj)

                row = layout.row()
                row.prop(scene,
                    "measure_panel_transform",
                    expand=True) 

            elif (not context.selected_objects
                  or len(context.selected_objects) == 0):
                # Nothing selected.
                # We measure the distance from the origin to the 3D cursor.
                dist_vec = scene.cursor_location
                scene.measure_panel_dist = dist_vec.length

                row = layout.row()
                row.prop(scene, "measure_panel_dist")

                row = layout.row()
                row.label(text="", icon='CURSOR')
                row.label(text="", icon='ARROW_LEFTRIGHT')
                row.label(text="Origin [0,0,0]")

            else:
                row = layout.row()
                row.label(text="Selection not supported.", icon='INFO')


    def addObjectAreas(self, *objs):
        area = 0.0
        total_area = 0.0
        globalCoords = measureGlobal(self.scene)
        for o in objs:
            area = self.objectSurfaceArea(o, False, globalCoords)
            if(area >= 0):
                total_area += area
            row = self.layout.row()
            row.label(text=o.name+" S.A.: "+str(round(area, PRECISION))+self.units(2), icon='OBJECT_DATA')

        if(len(objs) > 1 and total_area >= 0):
            row = self.layout.row()
            row.label(text='Total Area: '+str(round(total_area, PRECISION))+self.units(2), icon='OBJECT_DATA')
        return total_area

    
    def addAreasAndVolumes(self, *objs):
        area = 0.0
        total_area = 0.0
        volume = 0.0
        total_volume = 0.0
        globalCoords = measureGlobal(self.scene)
        for o in objs:
            area = self.objectSurfaceArea(o, False, globalCoords)
            if(area >= 0):
                total_area += area
            row = self.layout.row()
            row.label(text=o.name+" S.A.: "+str(round(area, PRECISION))+self.units(2), icon='OBJECT_DATA')

            volume = self.objectVolume(o, globalCoords)
            if(volume >= 0):
                total_volume += volume
            row = self.layout.row()
            row.label(text=o.name+" Vol.: "+str(round(volume, PRECISION))+self.units(3), icon='OBJECT_DATA')

        if(len(objs) > 1):
            if(total_area >= 0):
                row = self.layout.row()
                row.label(text='Total Area: '+str(round(total_area, PRECISION))+self.units(2), icon='OBJECT_DATA')
            if(total_volume >= 0):
                row = self.layout.row()
                row.label(text='Total Volume: '+str(round(total_volume, PRECISION))+self.units(3), icon='OBJECT_DATA')
        return total_area


    def addObjectVolumes(self, *objs):
        volume = 0.0
        total_volume = 0.0
        globalCoords = measureGlobal(self.scene)
        for o in objs:
            volume = self.objectVolume(o, globalCoords)
            if(volume >= 0):
                total_volume += volume
            row = self.layout.row()
            row.label(text=o.name+" Vol.: "+str(round(volume, PRECISION))+self.units(3), icon='OBJECT_DATA')

        if(len(objs) > 1 and total_volume >= 0):
            row = self.layout.row()
            row.label(text='Total Volume: '+str(round(total_volume, PRECISION))+self.units(3), icon='OBJECT_DATA')
        return total_volume


    # Calculate the surface area of a mesh object.
    # *) Set selectedOnly=1 if you only want to count selected faces.
    # *) Set globalSpace=1 if you want to calculate
    #    the global surface area (object mode).
    # Note: Be sure you have updated the mesh data before
    #       running this with selectedOnly=1!
    # @todo Support other object types (surfaces, etc...)?
    # @todo Is there a better way to handle
    #       global calculation? (transformed mesh)
    def objectSurfaceArea(self, obj, selectedOnly, globalSpace):
        if (obj and obj.type == 'MESH' and obj.data):
            areaTotal = 0

            # Apply transformation if needed.
            if globalSpace:
                mesh = obj.data.copy()
                mesh.transform(obj.matrix)
            else:
                mesh = obj.data

            # Count the area of all the faces.
            for face in mesh.faces:
                if (not selectedOnly
                    or face.selected):
                    areaTotal += face.area

            return areaTotal * (self.scene.unit_settings.scale_length ** 2)

        # We can not calculate an area for this object.
        return -1


    def objectVolume(self, obj, globalSpace):
        if not (obj and obj.type == 'MESH' and obj.data): 
            return -1

        volume = 0.0
        mesh = obj.data.copy()
        if globalSpace:
            mesh.transform(obj.matrix)

        # Change to edit mode and triangulate the copied mesh
        #self.scene.objects.active = obj
        #bpy.ops.object.mode_set(mode="EDIT")
        #bpy.ops.mesh.select_all(action='DESELECT')
        #bpy.ops.mesh.select_all(action='SELECT')
        #bpy.ops.mesh.quads_convert_to_tris()

        for face in mesh.faces:
            if len(face.verts) > 3: return -1
            volume += mesh.verts[face.verts[0]].co.cross(mesh.verts[face.verts[1]].co).dot(mesh.verts[face.verts[2]].co)
        # blender's natural units are meters. 1m = 1bu. Imperial units use yards.
        return volume / 6 * (self.scene.unit_settings.scale_length ** 3)


    def units(self, degree=0):
        if self.scene.unit_settings.system == "METRIC":
            unit = "m"
        elif self.scene.unit_settings.system == "IMPERIAL":
            unit = "yd"
        else:
            unit = "BU"
        if(degree > 0 and degree < 4):
            return unit + "^" + str(degree)
        else:
            return unit


def register():
    bpy.types.register(VIEW3D_PT_measure)
    bpy.types.register(OBJECT_OT_reenter_editmode)


def unregister():
    bpy.types.unregister(VIEW3D_PT_measure)
    bpy.types.unregister(OBJECT_OT_reenter_editmode)

#bpy.types.register(VIEW3D_PT_measure)
#bpy.types.register(OBJECT_OT_reenter_editmode)
#bpy.ops.add(OBJECT_OT_reenter_editmode)

# vim: set tabstop=4 softtabstop=4 shiftwidth=4:
