'''
QuickBonePicker - Fast Bone Selection Canvas
Created by Aman - Version 1.0
A powerful addon to create custom buttons for picking bones in Blender with drag-and-drop canvas
'''

bl_info = {
    "name": "QuickBonePicker by Aman",
    "description": "Fast & easy bone selection with custom buttons - drag, click, done!",
    "author": "Aman",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "View 3D > Sidebar > Bone Picker",
    "category": "Animation",
    "support": "COMMUNITY"
}

import bpy
import gpu
import blf
from gpu_extras.batch import batch_for_shader
from bpy.props import StringProperty, CollectionProperty, IntProperty, FloatProperty, BoolProperty
from bpy.types import Operator, Panel, PropertyGroup, SpaceView3D
import os

# Global dictionary to store loaded textures
_loaded_textures = {}

# Store button data
class BonePickerButton(PropertyGroup):
    bone_name: StringProperty(
        name="Bone Name",
        description="Name of the bone to select",
        default=""
    )
    button_label: StringProperty(
        name="Button Label",
        description="Label shown on the button",
        default=""
    )
    pos_x: FloatProperty(
        name="X Position",
        description="X position of button in canvas",
        default=0.0
    )
    pos_y: FloatProperty(
        name="Y Position",
        description="Y position of button in canvas",
        default=0.0
    )
    width: FloatProperty(
        name="Width",
        description="Button width",
        default=100.0,
        min=10.0,
        max=1000.0
    )
    height: FloatProperty(
        name="Height",
        description="Button height",
        default=50.0,
        min=10.0,
        max=1000.0
    )
    is_empty: BoolProperty(
        name="Is Empty",
        description="Empty button for decoration only",
        default=False
    )
    image_path: StringProperty(
        name="Image Path",
        description="Path to image file for empty button background",
        default="",
        subtype='FILE_PATH'
    )
    image_name: StringProperty(
        name="Image Name",
        description="Name of loaded image in Blender",
        default=""
    )
    is_circle: BoolProperty(
        name="Is Circle",
        description="Draw button as circle/dot instead of rectangle",
        default=False
    )
    color_r: FloatProperty(
        name="Red",
        description="Button color - Red channel",
        default=0.2,
        min=0.0,
        max=1.0
    )
    color_g: FloatProperty(
        name="Green",
        description="Button color - Green channel",
        default=0.3,
        min=0.0,
        max=1.0
    )
    color_b: FloatProperty(
        name="Blue",
        description="Button color - Blue channel",
        default=0.5,
        min=0.0,
        max=1.0
    )
    is_locked: BoolProperty(
        name="Is Locked",
        description="Lock button position (cannot be moved or resized)",
        default=False
    )
    is_hidden: BoolProperty(
        name="Is Hidden",
        description="Hide button from canvas",
        default=False
    )
    z_order: IntProperty(
        name="Z Order",
        description="Drawing order - higher values draw on top",
        default=0
    )
    section: StringProperty(
        name="Section",
        description="Section/group name for organizing buttons (1-9)",
        default="1"
    )
    is_pose: BoolProperty(
        name="Is Pose",
        description="This button applies a saved pose",
        default=False
    )
    pose_data: StringProperty(
        name="Pose Data",
        description="JSON data storing bone transforms",
        default=""
    )

class BONEPICKER_OT_AddButton(Operator):
    """Add a new bone picker button"""
    bl_idname = "bonepicker.add_button"
    bl_label = "Add Bone Button"
    
    def execute(self, context):
        if context.active_pose_bone:
            bone = context.active_pose_bone
            
            # Get active section
            active_section = context.scene.bone_picker_active_section if hasattr(context.scene, 'bone_picker_active_section') else "1"
            
            # Find highest z_order among bone buttons in active section
            max_z = 0
            for btn in context.scene.bone_picker_buttons:
                btn_section = btn.section if btn.section else "1"
                if not btn.is_empty and btn_section == active_section and btn.z_order > max_z:
                    max_z = btn.z_order
            
            item = context.scene.bone_picker_buttons.add()
            item.bone_name = bone.name
            item.button_label = bone.name
            item.is_empty = False
            item.section = active_section  # Assign to active section
            item.z_order = max_z + 1  # New button on top
            # Default blue color for bone buttons
            item.color_r = 0.2
            item.color_g = 0.3
            item.color_b = 0.5
            # Auto-arrange buttons in grid
            count = len(context.scene.bone_picker_buttons) - 1
            item.pos_x = (count % 4) * 120 + 50
            item.pos_y = (count // 4) * 70 + 50
            self.report({'INFO'}, f"Added button for bone: {bone.name}")
        else:
            self.report({'WARNING'}, "No active pose bone selected")
        return {'FINISHED'}

class BONEPICKER_OT_AddEmptyButton(Operator):
    """Add an empty button for decoration"""
    bl_idname = "bonepicker.add_empty_button"
    bl_label = "Add Empty Button"
    
    def execute(self, context):
        # Get active section
        active_section = context.scene.bone_picker_active_section if hasattr(context.scene, 'bone_picker_active_section') else "1"
        
        # Find highest z_order among empty buttons in active section
        max_z = 0
        for btn in context.scene.bone_picker_buttons:
            btn_section = btn.section if btn.section else "1"
            if btn.is_empty and btn_section == active_section and btn.z_order > max_z:
                max_z = btn.z_order
        
        item = context.scene.bone_picker_buttons.add()
        item.bone_name = ""
        item.button_label = ""
        item.section = active_section  # Assign to active section
        item.is_empty = True
        item.z_order = max_z + 1  # New button on top of other empty buttons
        # Default gray color for empty buttons
        item.color_r = 0.3
        item.color_g = 0.3
        item.color_b = 0.3
        # Auto-arrange buttons in grid
        count = len(context.scene.bone_picker_buttons) - 1
        item.pos_x = (count % 4) * 120 + 50
        item.pos_y = (count // 4) * 70 + 50
        self.report({'INFO'}, "Added empty button")
        return {'FINISHED'}

class BONEPICKER_OT_SavePose(Operator):
    """Save current pose of selected bones"""
    bl_idname = "bonepicker.save_pose"
    bl_label = "Save Pose"
    
    pose_name: StringProperty(name="Pose Name", default="New Pose")
    
    def execute(self, context):
        if context.mode != 'POSE':
            self.report({'WARNING'}, "Must be in Pose Mode")
            return {'CANCELLED'}
        
        if not context.selected_pose_bones:
            self.report({'WARNING'}, "No bones selected")
            return {'CANCELLED'}
        
        import json
        
        # Get active section
        active_section = context.scene.bone_picker_active_section if hasattr(context.scene, 'bone_picker_active_section') else "1"
        
        # Store pose data for selected bones
        pose_data = {}
        for bone in context.selected_pose_bones:
            pose_data[bone.name] = {
                'location': list(bone.location),
                'rotation_quaternion': list(bone.rotation_quaternion) if bone.rotation_mode == 'QUATERNION' else None,
                'rotation_euler': list(bone.rotation_euler) if bone.rotation_mode != 'QUATERNION' else None,
                'rotation_mode': bone.rotation_mode,
                'scale': list(bone.scale)
            }
        
        # Find highest z_order in active section
        max_z = 0
        for btn in context.scene.bone_picker_buttons:
            btn_section = btn.section if btn.section else "1"
            if btn_section == active_section and btn.z_order > max_z:
                max_z = btn.z_order
        
        # Create pose button
        item = context.scene.bone_picker_buttons.add()
        item.button_label = self.pose_name
        item.is_pose = True
        item.is_empty = False
        item.pose_data = json.dumps(pose_data)
        item.section = active_section
        item.z_order = max_z + 1
        # Green color for pose buttons
        item.color_r = 0.2
        item.color_g = 0.6
        item.color_b = 0.3
        # Auto-arrange
        count = len(context.scene.bone_picker_buttons) - 1
        item.pos_x = (count % 4) * 120 + 50
        item.pos_y = (count // 4) * 70 + 50
        
        self.report({'INFO'}, f"Saved pose: {self.pose_name} ({len(pose_data)} bones)")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class BONEPICKER_OT_ApplyPose(Operator):
    """Apply saved pose"""
    bl_idname = "bonepicker.apply_pose"
    bl_label = "Apply Pose"
    
    pose_data_json: StringProperty()
    
    def execute(self, context):
        if context.mode != 'POSE':
            self.report({'WARNING'}, "Must be in Pose Mode")
            return {'CANCELLED'}
        
        if not context.active_object or context.active_object.type != 'ARMATURE':
            self.report({'WARNING'}, "No armature selected")
            return {'CANCELLED'}
        
        import json
        
        try:
            pose_data = json.loads(self.pose_data_json)
            
            applied_count = 0
            for bone_name, transforms in pose_data.items():
                if bone_name in context.active_object.pose.bones:
                    bone = context.active_object.pose.bones[bone_name]
                    
                    # Apply transforms
                    bone.location = transforms['location']
                    bone.scale = transforms['scale']
                    
                    # Apply rotation based on mode
                    if transforms['rotation_mode'] == 'QUATERNION' and transforms['rotation_quaternion']:
                        bone.rotation_mode = 'QUATERNION'
                        bone.rotation_quaternion = transforms['rotation_quaternion']
                    elif transforms['rotation_euler']:
                        bone.rotation_mode = transforms['rotation_mode']
                        bone.rotation_euler = transforms['rotation_euler']
                    
                    applied_count += 1
            
            self.report({'INFO'}, f"Applied pose to {applied_count} bones")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to apply pose: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}

class BONEPICKER_OT_RemoveButton(Operator):
    """Remove a bone picker button"""
    bl_idname = "bonepicker.remove_button"
    bl_label = "Remove Button"
    
    index: IntProperty()
    
    def execute(self, context):
        context.scene.bone_picker_buttons.remove(self.index)
        return {'FINISHED'}

class BONEPICKER_OT_RenameButton(Operator):
    """Rename a bone picker button"""
    bl_idname = "bonepicker.rename_button"
    bl_label = "Rename Button"
    
    index: IntProperty()
    new_name: StringProperty(name="Button Label", default="")
    
    def execute(self, context):
        if self.new_name:
            context.scene.bone_picker_buttons[self.index].button_label = self.new_name
            self.report({'INFO'}, f"Button renamed to: {self.new_name}")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        self.new_name = context.scene.bone_picker_buttons[self.index].button_label
        return context.window_manager.invoke_props_dialog(self)

class BONEPICKER_OT_ResizeButton(Operator):
    """Resize a bone picker button"""
    bl_idname = "bonepicker.resize_button"
    bl_label = "Resize Button"
    
    index: IntProperty()
    new_width: FloatProperty(name="Width", default=100.0, min=10.0, max=1000.0)
    new_height: FloatProperty(name="Height", default=50.0, min=10.0, max=1000.0)
    
    def execute(self, context):
        button = context.scene.bone_picker_buttons[self.index]
        button.width = self.new_width
        button.height = self.new_height
        self.report({'INFO'}, f"Button resized to {self.new_width}x{self.new_height}")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        button = context.scene.bone_picker_buttons[self.index]
        self.new_width = button.width
        self.new_height = button.height
        return context.window_manager.invoke_props_dialog(self)

class BONEPICKER_OT_SetButtonImage(Operator):
    """Set image for empty button"""
    bl_idname = "bonepicker.set_button_image"
    bl_label = "Set Button Image"
    
    index: IntProperty()
    filepath: StringProperty(subtype='FILE_PATH')
    
    def execute(self, context):
        button = context.scene.bone_picker_buttons[self.index]
        if self.filepath:
            button.image_path = self.filepath
            # Load the image into Blender - Blender 5 compatible
            try:
                img_name = os.path.basename(self.filepath)
                
                # Check if image already exists
                if img_name in bpy.data.images:
                    image = bpy.data.images[img_name]
                    # Reload the image
                    try:
                        image.reload()
                    except:
                        # If reload fails, remove and reload
                        bpy.data.images.remove(image)
                        image = bpy.data.images.load(self.filepath)
                else:
                    # Load new image
                    image = bpy.data.images.load(self.filepath)
                
                button.image_name = image.name
                
                # Force GPU load - Blender 5 compatible
                try:
                    if hasattr(image, 'gl_load'):
                        image.gl_load()
                except:
                    pass
                
                # Ensure image has data
                if not image.has_data:
                    try:
                        image.reload()
                    except:
                        pass
                
                self.report({'INFO'}, f"Image '{image.name}' loaded for button")
            except Exception as e:
                self.report({'WARNING'}, f"Failed to load image: {str(e)}")
                import traceback
                traceback.print_exc()
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class BONEPICKER_OT_ToggleCircleShape(Operator):
    """Toggle button shape between rectangle and circle"""
    bl_idname = "bonepicker.toggle_circle"
    bl_label = "Toggle Circle Shape"
    
    index: IntProperty()
    
    def execute(self, context):
        button = context.scene.bone_picker_buttons[self.index]
        button.is_circle = not button.is_circle
        shape = "circle" if button.is_circle else "rectangle"
        print(f"DEBUG: Button '{button.button_label}' is_circle = {button.is_circle}")
        self.report({'INFO'}, f"Button shape changed to {shape}")
        # Force redraw
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        return {'FINISHED'}

class BONEPICKER_OT_SetButtonColor(Operator):
    """Set button color"""
    bl_idname = "bonepicker.set_color"
    bl_label = "Set Button Color"
    
    index: IntProperty()
    color_r: FloatProperty(name="Red", default=0.2, min=0.0, max=1.0)
    color_g: FloatProperty(name="Green", default=0.3, min=0.0, max=1.0)
    color_b: FloatProperty(name="Blue", default=0.5, min=0.0, max=1.0)
    
    def execute(self, context):
        button = context.scene.bone_picker_buttons[self.index]
        button.color_r = self.color_r
        button.color_g = self.color_g
        button.color_b = self.color_b
        self.report({'INFO'}, f"Button color changed")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        button = context.scene.bone_picker_buttons[self.index]
        self.color_r = button.color_r
        self.color_g = button.color_g
        self.color_b = button.color_b
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "color_r", slider=True)
        layout.prop(self, "color_g", slider=True)
        layout.prop(self, "color_b", slider=True)

class BONEPICKER_OT_ToggleLock(Operator):
    """Lock/Unlock button position"""
    bl_idname = "bonepicker.toggle_lock"
    bl_label = "Toggle Lock"
    
    index: IntProperty()
    
    def execute(self, context):
        button = context.scene.bone_picker_buttons[self.index]
        button.is_locked = not button.is_locked
        status = "locked" if button.is_locked else "unlocked"
        self.report({'INFO'}, f"Button {status}")
        return {'FINISHED'}

class BONEPICKER_OT_ToggleHide(Operator):
    """Hide/Show button on canvas"""
    bl_idname = "bonepicker.toggle_hide"
    bl_label = "Toggle Hide"
    
    index: IntProperty()
    
    def execute(self, context):
        button = context.scene.bone_picker_buttons[self.index]
        button.is_hidden = not button.is_hidden
        status = "hidden" if button.is_hidden else "visible"
        self.report({'INFO'}, f"Button {status}")
        return {'FINISHED'}

class BONEPICKER_OT_BringToFront(Operator):
    """Bring button to front (top of its layer)"""
    bl_idname = "bonepicker.bring_to_front"
    bl_label = "Bring to Front"
    
    index: IntProperty()
    
    def execute(self, context):
        button = context.scene.bone_picker_buttons[self.index]
        
        # Find max z_order in same layer
        max_z = 0
        for btn in context.scene.bone_picker_buttons:
            if btn.is_empty == button.is_empty and btn.z_order > max_z:
                max_z = btn.z_order
        
        button.z_order = max_z + 1
        self.report({'INFO'}, f"Button brought to front")
        return {'FINISHED'}

class BONEPICKER_OT_SendToBack(Operator):
    """Send button to back (bottom of its layer)"""
    bl_idname = "bonepicker.send_to_back"
    bl_label = "Send to Back"
    
    index: IntProperty()
    
    def execute(self, context):
        button = context.scene.bone_picker_buttons[self.index]
        
        # Find min z_order in same layer
        min_z = float('inf')
        for btn in context.scene.bone_picker_buttons:
            if btn.is_empty == button.is_empty and btn.z_order < min_z:
                min_z = btn.z_order
        
        if min_z == float('inf'):
            min_z = 0
        
        button.z_order = min_z - 1
        self.report({'INFO'}, f"Button sent to back")
        return {'FINISHED'}

class BONEPICKER_OT_LockAllEmpty(Operator):
    """Lock all empty buttons"""
    bl_idname = "bonepicker.lock_all_empty"
    bl_label = "Lock All Empty Buttons"
    
    def execute(self, context):
        count = 0
        for btn in context.scene.bone_picker_buttons:
            if btn.is_empty and not btn.is_locked:
                btn.is_locked = True
                count += 1
        self.report({'INFO'}, f"Locked {count} empty buttons")
        return {'FINISHED'}

class BONEPICKER_OT_UnlockAllEmpty(Operator):
    """Unlock all empty buttons"""
    bl_idname = "bonepicker.unlock_all_empty"
    bl_label = "Unlock All Empty Buttons"
    
    def execute(self, context):
        count = 0
        for btn in context.scene.bone_picker_buttons:
            if btn.is_empty and btn.is_locked:
                btn.is_locked = False
                count += 1
        self.report({'INFO'}, f"Unlocked {count} empty buttons")
        return {'FINISHED'}

class BONEPICKER_OT_LockAllBone(Operator):
    """Lock all bone buttons"""
    bl_idname = "bonepicker.lock_all_bone"
    bl_label = "Lock All Bone Buttons"
    
    def execute(self, context):
        count = 0
        for btn in context.scene.bone_picker_buttons:
            if not btn.is_empty and not btn.is_locked:
                btn.is_locked = True
                count += 1
        self.report({'INFO'}, f"Locked {count} bone buttons")
        return {'FINISHED'}

class BONEPICKER_OT_UnlockAllBone(Operator):
    """Unlock all bone buttons"""
    bl_idname = "bonepicker.unlock_all_bone"
    bl_label = "Unlock All Bone Buttons"
    
    def execute(self, context):
        count = 0
        for btn in context.scene.bone_picker_buttons:
            if not btn.is_empty and btn.is_locked:
                btn.is_locked = False
                count += 1
        self.report({'INFO'}, f"Unlocked {count} bone buttons")
        return {'FINISHED'}

class BONEPICKER_OT_HideAll(Operator):
    """Hide all buttons"""
    bl_idname = "bonepicker.hide_all"
    bl_label = "Hide All Buttons"
    
    def execute(self, context):
        count = 0
        for btn in context.scene.bone_picker_buttons:
            if not btn.is_hidden:
                btn.is_hidden = True
                count += 1
        self.report({'INFO'}, f"Hidden {count} buttons")
        return {'FINISHED'}

class BONEPICKER_OT_UnhideAll(Operator):
    """Unhide all buttons"""
    bl_idname = "bonepicker.unhide_all"
    bl_label = "Unhide All Buttons"
    
    def execute(self, context):
        count = 0
        for btn in context.scene.bone_picker_buttons:
            if btn.is_hidden:
                btn.is_hidden = False
                count += 1
        self.report({'INFO'}, f"Unhidden {count} buttons")
        return {'FINISHED'}

class BONEPICKER_OT_SetSection(Operator):
    """Set section/group for button (1-9)"""
    bl_idname = "bonepicker.set_section"
    bl_label = "Set Section"
    
    index: IntProperty()
    section_name: StringProperty(name="Section (1-9)", default="1")
    
    def execute(self, context):
        if self.section_name and self.section_name in ['1','2','3','4','5','6','7','8','9']:
            context.scene.bone_picker_buttons[self.index].section = self.section_name
            self.report({'INFO'}, f"Button moved to section: {self.section_name}")
        else:
            self.report({'WARNING'}, "Section must be 1-9")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        self.section_name = context.scene.bone_picker_buttons[self.index].section
        return context.window_manager.invoke_props_dialog(self)

class BONEPICKER_OT_HideSection(Operator):
    """Hide all buttons in a section"""
    bl_idname = "bonepicker.hide_section"
    bl_label = "Hide Section"
    
    section_name: StringProperty()
    
    def execute(self, context):
        count = 0
        for btn in context.scene.bone_picker_buttons:
            if btn.section == self.section_name and not btn.is_hidden:
                btn.is_hidden = True
                count += 1
        self.report({'INFO'}, f"Hidden {count} buttons in section '{self.section_name}'")
        return {'FINISHED'}

class BONEPICKER_OT_ShowSection(Operator):
    """Show all buttons in a section"""
    bl_idname = "bonepicker.show_section"
    bl_label = "Show Section"
    
    section_name: StringProperty()
    
    def execute(self, context):
        count = 0
        for btn in context.scene.bone_picker_buttons:
            if btn.section == self.section_name and btn.is_hidden:
                btn.is_hidden = False
                count += 1
        self.report({'INFO'}, f"Shown {count} buttons in section '{self.section_name}'")
        return {'FINISHED'}

class BONEPICKER_OT_SwitchSection(Operator):
    """Switch to a section"""
    bl_idname = "bonepicker.switch_section"
    bl_label = "Switch Section"
    
    section_number: StringProperty()
    
    def execute(self, context):
        context.scene.bone_picker_active_section = self.section_number
        self.report({'INFO'}, f"Switched to Section {self.section_number}")
        # Force redraw
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        return {'FINISHED'}

class BONEPICKER_OT_PickBone(Operator):
    """Select the bone associated with this button"""
    bl_idname = "bonepicker.pick_bone"
    bl_label = "Pick Bone"
    
    bone_name: StringProperty()
    add_to_selection: BoolProperty(default=False)
    
    def execute(self, context):
        if context.mode != 'POSE':
            self.report({'WARNING'}, "Must be in Pose Mode")
            return {'CANCELLED'}
        
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "No armature selected")
            return {'CANCELLED'}
        
        if self.bone_name not in obj.pose.bones:
            self.report({'WARNING'}, f"Bone '{self.bone_name}' not found")
            return {'CANCELLED'}
        
        pose_bone = obj.pose.bones[self.bone_name]
        
        # Deselect all bones if not adding to selection
        if not self.add_to_selection:
            bpy.ops.pose.select_all(action='DESELECT')
        
        # BLENDER 5.0 FIX: Use context.selected_pose_bones_from_active_object
        # This is the proper way to select bones in Blender 5.0
        # We need to temporarily switch to edit mode, select, then switch back
        
        # Store current mode
        current_mode = context.mode
        
        try:
            # Switch to edit mode to select bone
            bpy.ops.object.mode_set(mode='EDIT')
            
            # Select the bone in edit mode
            if self.bone_name in obj.data.edit_bones:
                if not self.add_to_selection:
                    bpy.ops.armature.select_all(action='DESELECT')
                obj.data.edit_bones[self.bone_name].select = True
                obj.data.edit_bones[self.bone_name].select_head = True
                obj.data.edit_bones[self.bone_name].select_tail = True
                obj.data.edit_bones.active = obj.data.edit_bones[self.bone_name]
            
            # Switch back to pose mode
            bpy.ops.object.mode_set(mode='POSE')
            
            # Set as active bone in pose mode
            obj.data.bones.active = pose_bone.bone
            
            self.report({'INFO'}, f"Selected bone: {self.bone_name}")
            
        except Exception as e:
            # If mode switching fails, try to restore original mode
            try:
                if context.mode != 'POSE':
                    bpy.ops.object.mode_set(mode='POSE')
            except:
                pass
            self.report({'WARNING'}, f"Could not select bone: {str(e)}")
        
        return {'FINISHED'}

# Global variables for drawing
_draw_handler = None
_picker_window_active = False

def draw_callback_px(self, context):
    """Draw the picker canvas"""
    if not _picker_window_active:
        return
    
    # Only draw in POSE mode
    if context.mode != 'POSE':
        return
    
    font_id = 0
    
    # Draw background
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    
    # Get selected bones for highlighting
    selected_bone_names = set()
    if context.active_object and context.active_object.type == 'ARMATURE':
        try:
            selected_bone_names = {bone.name for bone in context.selected_pose_bones}
        except:
            pass
    
    # Get interactive resizing button
    interactive_resize_button = None
    if hasattr(self, 'interactive_resize_button') and self.interactive_resize_button:
        interactive_resize_button = self.interactive_resize_button
    
    # Get alt+middle dragging button
    alt_middle_drag_button = None
    if hasattr(self, 'alt_middle_drag_button') and self.alt_middle_drag_button:
        alt_middle_drag_button = self.alt_middle_drag_button
    
    # Get selected buttons for multi-drag highlighting
    selected_buttons_set = set()
    if hasattr(self, 'selected_buttons'):
        selected_buttons_set = set(self.selected_buttons)
    
    # Check if showing all hidden buttons
    show_all_hidden = False
    if hasattr(self, 'show_all_hidden'):
        show_all_hidden = self.show_all_hidden
    
    # Separate buttons by type for proper layering
    # Empty buttons will ALWAYS be drawn first (bottom layer)
    # Bone buttons will ALWAYS be drawn second (top layer)
    # Within each layer, buttons are sorted by z_order (higher = on top)
    empty_buttons = []
    bone_buttons = []
    
    # Get active section
    active_section = context.scene.bone_picker_active_section if hasattr(context.scene, 'bone_picker_active_section') else "1"
    
    for item in context.scene.bone_picker_buttons:
        # Only show buttons from active section
        item_section = item.section if item.section else "1"
        if item_section != active_section:
            continue
            
        # Skip hidden buttons unless show_all_hidden is active
        if item.is_hidden and not show_all_hidden:
            continue
            
        if item.is_empty:
            empty_buttons.append(item)
        else:
            bone_buttons.append(item)
    
    # Sort by z_order (lower values draw first, higher values on top)
    empty_buttons.sort(key=lambda x: x.z_order)
    bone_buttons.sort(key=lambda x: x.z_order)
    
    # LAYER 1: Draw empty buttons first (bottom layer - always behind everything)
    for item in empty_buttons:
        
        # Check if this is a temporarily visible hidden button
        is_temp_visible = item.is_hidden and show_all_hidden
            
        x = item.pos_x
        y = item.pos_y
        w = item.width
        h = item.height
        
        # Check if image exists and draw it
        has_image = False
        if item.image_name and item.image_name in bpy.data.images:
            try:
                image = bpy.data.images[item.image_name]
                
                # Ensure image is loaded - Blender 5 compatible
                if not image.has_data:
                    try:
                        image.reload()
                    except:
                        pass
                
                # Try to load GPU texture - Blender 5 compatible
                bindcode = 0
                try:
                    if hasattr(image, 'bindcode'):
                        bindcode = image.bindcode
                    
                    if bindcode == 0 and hasattr(image, 'gl_load'):
                        try:
                            image.gl_load()
                            bindcode = image.bindcode if hasattr(image, 'bindcode') else 0
                        except:
                            pass
                except:
                    pass
                
                # Draw image using GPU module
                if bindcode != 0 or image.has_data:
                    # Calculate aspect ratio to prevent stretching
                    img_width = image.size[0] if len(image.size) > 0 else 1
                    img_height = image.size[1] if len(image.size) > 1 else 1
                    img_aspect = img_width / img_height if img_height > 0 else 1.0
                    button_aspect = w / h if h > 0 else 1.0
                    
                    # Calculate fitted dimensions
                    if img_aspect > button_aspect:
                        # Image is wider - fit to width
                        fit_w = w
                        fit_h = w / img_aspect
                        offset_x = 0
                        offset_y = (h - fit_h) / 2
                    else:
                        # Image is taller - fit to height
                        fit_h = h
                        fit_w = h * img_aspect
                        offset_x = (w - fit_w) / 2
                        offset_y = 0
                    
                    # Adjusted position
                    img_x = x + offset_x
                    img_y = y + offset_y
                    
                    try:
                        # Create shader for textured quad
                        texture_shader = gpu.shader.from_builtin('IMAGE')
                        
                        # Prepare vertices and UVs
                        vertices = (
                            (img_x, img_y), (img_x + fit_w, img_y),
                            (img_x + fit_w, img_y + fit_h), (img_x, img_y + fit_h)
                        )
                        
                        uvs = (
                            (0, 0), (1, 0),
                            (1, 1), (0, 1)
                        )
                        
                        indices = ((0, 1, 2), (2, 3, 0))
                        
                        batch = batch_for_shader(
                            texture_shader, 'TRIS',
                            {"pos": vertices, "texCoord": uvs},
                            indices=indices
                        )
                        
                        # Bind texture and draw
                        gpu.state.blend_set('ALPHA')
                        texture_shader.bind()
                        texture_shader.uniform_sampler("image", gpu.texture.from_image(image))
                        batch.draw(texture_shader)
                        gpu.state.blend_set('NONE')
                        
                        has_image = True
                    except Exception as e:
                        print(f"Error drawing image texture: {e}")
                        has_image = False
            except Exception as e:
                print(f"Error loading image: {e}")
                has_image = False
        
        if not has_image:
            # Button background (no image or failed to load)
            if item.is_circle:
                # Draw as circle
                import math
                center_x = x + w / 2
                center_y = y + h / 2
                radius = min(w, h) / 2
                segments = 32
                
                # Create circle vertices
                circle_verts = [(center_x, center_y)]  # Center point first
                for i in range(segments + 1):
                    angle = 2 * math.pi * i / segments
                    circle_verts.append((
                        center_x + radius * math.cos(angle),
                        center_y + radius * math.sin(angle)
                    ))
                
                # Create triangles from center
                circle_indices = []
                for i in range(1, segments + 1):
                    circle_indices.append((0, i, i + 1))
                
                batch = batch_for_shader(shader, 'TRIS', {"pos": circle_verts}, indices=circle_indices)
                shader.bind()
                shader.uniform_float("color", (item.color_r, item.color_g, item.color_b, 0.6))
                batch.draw(shader)
            else:
                # Draw as rectangle
                vertices = (
                    (x, y), (x + w, y),
                    (x + w, y + h), (x, y + h)
                )
                
                indices = ((0, 1, 2), (2, 3, 0))
                
                batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
                shader.bind()
                shader.uniform_float("color", (item.color_r, item.color_g, item.color_b, 0.3 if is_temp_visible else 0.6))  # Transparent if temp visible
                batch.draw(shader)
        
        # Button border - dashed for temp visible
        vertices_border = (
            (x, y), (x + w, y),
            (x + w, y + h), (x, y + h), (x, y)
        )
        batch_border = batch_for_shader(shader, 'LINE_STRIP', {"pos": vertices_border})
        if is_temp_visible:
            shader.uniform_float("color", (1.0, 0.5, 0.0, 0.8))  # Orange dashed for temp visible
        else:
            shader.uniform_float("color", (0.8, 0.8, 0.8, 1.0))
        batch_border.draw(shader)
        
        # Resize handle (bottom-right corner) - only for rectangles
        if not item.is_circle:
            handle_size = 10
            handle_x = x + w - handle_size
            handle_y = y
            handle_vertices = (
                (handle_x, handle_y), (handle_x + handle_size, handle_y),
                (handle_x + handle_size, handle_y + handle_size), (handle_x, handle_y + handle_size)
            )
            handle_indices = ((0, 1, 2), (2, 3, 0))
            handle_batch = batch_for_shader(shader, 'TRIS', {"pos": handle_vertices}, indices=handle_indices)
            shader.uniform_float("color", (0.8, 0.5, 0.2, 0.9))
            handle_batch.draw(shader)
        
        # Button text
        if not item.is_circle and item.button_label:
            blf.position(font_id, x + 10, y + h/2 - 5, 0)
            blf.size(font_id, 12)
            blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
            blf.draw(font_id, item.button_label)
    
    # LAYER 2: Draw bone buttons on top (middle layer - always above empty buttons)
    for item in bone_buttons:
        
        # Check if this bone is selected
        is_selected = item.bone_name in selected_bone_names if not item.is_pose else False
        
        # Check if this button is being interactively resized or dragged
        is_resizing = (interactive_resize_button is not None and 
                      interactive_resize_button == item)
        is_alt_dragging = (alt_middle_drag_button is not None and 
                          alt_middle_drag_button == item)
        
        # Check if this button is in multi-selection
        is_multi_selected = item in selected_buttons_set
        
        # Check if this is a temporarily visible hidden button
        is_temp_visible = item.is_hidden and show_all_hidden
            
        x = item.pos_x
        y = item.pos_y
        w = item.width
        h = item.height
        
        # Check if image exists and draw it (for pose buttons)
        has_image = False
        if item.is_pose and item.image_name and item.image_name in bpy.data.images:
            try:
                image = bpy.data.images[item.image_name]
                
                # Ensure image is loaded - Blender 5 compatible
                if not image.has_data:
                    try:
                        image.reload()
                    except:
                        pass
                
                # Try to load GPU texture - Blender 5 compatible
                bindcode = 0
                try:
                    if hasattr(image, 'bindcode'):
                        bindcode = image.bindcode
                    
                    if bindcode == 0 and hasattr(image, 'gl_load'):
                        try:
                            image.gl_load()
                            bindcode = image.bindcode if hasattr(image, 'bindcode') else 0
                        except:
                            pass
                except:
                    pass
                
                # Draw image using GPU module
                if bindcode != 0 or image.has_data:
                    # Calculate aspect ratio to prevent stretching
                    img_width = image.size[0] if len(image.size) > 0 else 1
                    img_height = image.size[1] if len(image.size) > 1 else 1
                    img_aspect = img_width / img_height if img_height > 0 else 1.0
                    button_aspect = w / h if h > 0 else 1.0
                    
                    # Calculate fitted dimensions
                    if img_aspect > button_aspect:
                        # Image is wider - fit to width
                        fit_w = w
                        fit_h = w / img_aspect
                        offset_x = 0
                        offset_y = (h - fit_h) / 2
                    else:
                        # Image is taller - fit to height
                        fit_h = h
                        fit_w = h * img_aspect
                        offset_x = (w - fit_w) / 2
                        offset_y = 0
                    
                    # Adjusted position
                    img_x = x + offset_x
                    img_y = y + offset_y
                    
                    try:
                        # Create shader for textured quad
                        texture_shader = gpu.shader.from_builtin('IMAGE')
                        
                        # Prepare vertices and UVs
                        vertices = (
                            (img_x, img_y), (img_x + fit_w, img_y),
                            (img_x + fit_w, img_y + fit_h), (img_x, img_y + fit_h)
                        )
                        
                        uvs = (
                            (0, 0), (1, 0),
                            (1, 1), (0, 1)
                        )
                        
                        indices = ((0, 1, 2), (2, 3, 0))
                        
                        batch = batch_for_shader(
                            texture_shader, 'TRIS',
                            {"pos": vertices, "texCoord": uvs},
                            indices=indices
                        )
                        
                        # Bind texture and draw
                        gpu.state.blend_set('ALPHA')
                        texture_shader.bind()
                        texture_shader.uniform_sampler("image", gpu.texture.from_image(image))
                        batch.draw(texture_shader)
                        gpu.state.blend_set('NONE')
                        
                        has_image = True
                    except Exception as e:
                        print(f"Error drawing image texture: {e}")
                        has_image = False
            except Exception as e:
                print(f"Error loading image: {e}")
                has_image = False
        
        # Button background (if no image or not a pose button)
        if not has_image:
            if item.is_circle:
                # Draw as circle
                import math
                center_x = x + w / 2
                center_y = y + h / 2
                radius = min(w, h) / 2
                segments = 32
                
                # Create circle vertices
                circle_verts = [(center_x, center_y)]  # Center point first
                for i in range(segments + 1):
                    angle = 2 * math.pi * i / segments
                    circle_verts.append((
                        center_x + radius * math.cos(angle),
                        center_y + radius * math.sin(angle)
                    ))
                
                # Create triangles from center
                circle_indices = []
                for i in range(1, segments + 1):
                    circle_indices.append((0, i, i + 1))
                
                batch = batch_for_shader(shader, 'TRIS', {"pos": circle_verts}, indices=circle_indices)
                shader.bind()
                # Highlight: resizing/dragging > multi-selected > selected > temp-visible > normal
                if is_resizing or is_alt_dragging:
                    # Bright white/yellow for resizing/dragging (like pivot point)
                    shader.uniform_float("color", (1.0, 1.0, 0.5, 1.0))
                elif is_temp_visible:
                    # Semi-transparent for temporarily visible hidden buttons
                    shader.uniform_float("color", (item.color_r, item.color_g, item.color_b, 0.4))
                elif is_multi_selected:
                    # Cyan/blue tint for multi-selected buttons
                    shader.uniform_float("color", (item.color_r * 1.3, item.color_g * 1.3, item.color_b * 1.8, 1.0))
                elif is_selected:
                    shader.uniform_float("color", (item.color_r * 1.5, item.color_g * 1.5, item.color_b * 1.5, 1.0))
                else:
                    shader.uniform_float("color", (item.color_r, item.color_g, item.color_b, 0.8))
                batch.draw(shader)
            else:
                # Draw as rectangle
                vertices = (
                    (x, y), (x + w, y),
                    (x + w, y + h), (x, y + h)
                )
                
                indices = ((0, 1, 2), (2, 3, 0))
                
                batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
                shader.bind()
                # Highlight: resizing/dragging > multi-selected > selected > temp-visible > normal
                if is_resizing or is_alt_dragging:
                    # Bright white/yellow for resizing/dragging (like pivot point)
                    shader.uniform_float("color", (1.0, 1.0, 0.5, 1.0))
                elif is_temp_visible:
                    # Semi-transparent for temporarily visible hidden buttons
                    shader.uniform_float("color", (item.color_r, item.color_g, item.color_b, 0.4))
                elif is_multi_selected:
                    # Cyan/blue tint for multi-selected buttons
                    shader.uniform_float("color", (item.color_r * 1.3, item.color_g * 1.3, item.color_b * 1.8, 1.0))
                elif is_selected:
                    shader.uniform_float("color", (item.color_r * 1.5, item.color_g * 1.5, item.color_b * 1.5, 1.0))
                else:
                    shader.uniform_float("color", (item.color_r, item.color_g, item.color_b, 0.8))
                batch.draw(shader)
        
        # Button border - thicker for selected/resizing/dragging/multi-selected bones, orange for temp visible
        border_width = 3.0 if (is_selected or is_resizing or is_alt_dragging or is_multi_selected or is_temp_visible) else 1.0
        vertices_border = (
            (x, y), (x + w, y),
            (x + w, y + h), (x, y + h), (x, y)
        )
        batch_border = batch_for_shader(shader, 'LINE_STRIP', {"pos": vertices_border})
        if is_resizing or is_alt_dragging:
            shader.uniform_float("color", (1.0, 1.0, 1.0, 1.0))  # White border for resizing/dragging
        elif is_temp_visible:
            shader.uniform_float("color", (1.0, 0.5, 0.0, 0.8))  # Orange border for temp visible
        elif is_multi_selected:
            shader.uniform_float("color", (0.3, 0.7, 1.0, 1.0))  # Cyan border for multi-selected
        elif is_selected:
            shader.uniform_float("color", (1.0, 1.0, 0.0, 1.0))  # Yellow border for selected
        else:
            shader.uniform_float("color", (0.8, 0.8, 0.8, 1.0))
        batch_border.draw(shader)
        
        # Resize handle (bottom-right corner) - only for rectangles
        if not item.is_circle:
            handle_size = 10
            handle_x = x + w - handle_size
            handle_y = y
            handle_vertices = (
                (handle_x, handle_y), (handle_x + handle_size, handle_y),
                (handle_x + handle_size, handle_y + handle_size), (handle_x, handle_y + handle_size)
            )
            handle_indices = ((0, 1, 2), (2, 3, 0))
            handle_batch = batch_for_shader(shader, 'TRIS', {"pos": handle_vertices}, indices=handle_indices)
            shader.uniform_float("color", (0.8, 0.5, 0.2, 0.9))
            handle_batch.draw(shader)
        
        # Button text
        if not item.is_circle:
            blf.position(font_id, x + 10, y + h/2 - 5, 0)
            blf.size(font_id, 12)
            blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
            blf.draw(font_id, item.button_label)
    
    # LAYER 3: Draw box selection on top of everything (top layer - always visible)
    if hasattr(self, 'box_selecting') and self.box_selecting:
        min_x = min(self.box_start_x, self.box_end_x)
        max_x = max(self.box_start_x, self.box_end_x)
        min_y = min(self.box_start_y, self.box_end_y)
        max_y = max(self.box_start_y, self.box_end_y)
        
        # Draw selection box background
        box_vertices = (
            (min_x, min_y), (max_x, min_y),
            (max_x, max_y), (min_x, max_y)
        )
        box_indices = ((0, 1, 2), (2, 3, 0))
        box_batch = batch_for_shader(shader, 'TRIS', {"pos": box_vertices}, indices=box_indices)
        shader.bind()
        shader.uniform_float("color", (0.3, 0.6, 1.0, 0.2))
        box_batch.draw(shader)
        
        # Draw selection box border
        box_border = (
            (min_x, min_y), (max_x, min_y),
            (max_x, max_y), (min_x, max_y), (min_x, min_y)
        )
        box_border_batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": box_border})
        shader.uniform_float("color", (0.3, 0.6, 1.0, 0.8))
        box_border_batch.draw(shader)

class BONEPICKER_OT_OpenPickerWindow(Operator):
    """Open Bone Picker Canvas Window"""
    bl_idname = "bonepicker.open_window"
    bl_label = "Open Picker Canvas"
    
    dragging_button = None
    resizing_button = None
    clicked_button = None
    drag_offset_x = 0
    drag_offset_y = 0
    resize_start_width = 0
    resize_start_height = 0
    resize_start_x = 0
    resize_start_y = 0
    
    # Multiple button selection and drag
    selected_buttons = []
    multi_drag_start_x = 0
    multi_drag_start_y = 0
    multi_dragging = False
    
    # Interactive resize with middle mouse
    interactive_resizing = False
    interactive_resize_button = None
    interactive_resize_start_x = 0
    interactive_resize_start_width = 0
    interactive_resize_start_height = 0
    
    # Alt+Middle mouse drag
    alt_middle_dragging = False
    alt_middle_drag_button = None
    alt_middle_drag_offset_x = 0
    alt_middle_drag_offset_y = 0
    
    # Alt+Backtick to show all hidden buttons temporarily
    show_all_hidden = False
    
    # Double click detection for middle mouse
    last_middle_click_time = 0
    last_middle_click_button = None
    double_click_threshold = 0.3  # seconds
    
    # Temporary show hidden buttons
    show_all_hidden = False
    
    # Box selection
    box_selecting = False
    box_start_x = 0
    box_start_y = 0
    box_end_x = 0
    box_end_y = 0
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'ARMATURE'
    
    def modal(self, context, event):
        context.area.tag_redraw()
        
        # Close only on ESC or Close button
        if event.type == 'ESC':
            self.cancel(context)
            return {'CANCELLED'}
        
        # Alt+1 through Alt+9 to switch sections
        if event.alt and event.value == 'PRESS':
            section_keys = {
                'ONE': '1', 'TWO': '2', 'THREE': '3', 'FOUR': '4', 'FIVE': '5',
                'SIX': '6', 'SEVEN': '7', 'EIGHT': '8', 'NINE': '9',
                'NUMPAD_1': '1', 'NUMPAD_2': '2', 'NUMPAD_3': '3', 'NUMPAD_4': '4', 'NUMPAD_5': '5',
                'NUMPAD_6': '6', 'NUMPAD_7': '7', 'NUMPAD_8': '8', 'NUMPAD_9': '9'
            }
            if event.type in section_keys:
                section_num = section_keys[event.type]
                context.scene.bone_picker_active_section = section_num
                self.report({'INFO'}, f"Switched to Section {section_num}")
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}
        
        # Alt+L to lock/unlock selected buttons
        if event.type == 'L' and event.value == 'PRESS' and event.alt:
            if len(self.selected_buttons) > 0:
                # Check if any selected button is unlocked
                has_unlocked = any(not btn.is_locked for btn in self.selected_buttons)
                
                # If any unlocked, lock all. Otherwise unlock all
                for btn in self.selected_buttons:
                    btn.is_locked = has_unlocked
                
                status = "locked" if has_unlocked else "unlocked"
                self.report({'INFO'}, f"{len(self.selected_buttons)} buttons {status}")
            return {'RUNNING_MODAL'}
        
        # Alt+Backtick (`) to show all hidden buttons temporarily
        if event.type == 'ACCENT_GRAVE' and event.alt:
            if event.value == 'PRESS':
                self.show_all_hidden = True
                self.report({'INFO'}, "Showing all hidden buttons (hold Alt+`)")
            elif event.value == 'RELEASE':
                self.show_all_hidden = False
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}
        
        # Safety: If Alt is released, turn off show_all_hidden
        if event.type in {'LEFT_ALT', 'RIGHT_ALT'}:
            if event.value == 'RELEASE' and self.show_all_hidden:
                self.show_all_hidden = False
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}
        
        # Only handle interactions in POSE mode
        if context.mode == 'POSE':
            # Middle mouse button for interactive resize and double-click for circle toggle
            if event.type == 'MIDDLEMOUSE':
                if event.value == 'PRESS':
                    import time
                    current_time = time.time()
                    
                    # Get active section
                    active_section = context.scene.bone_picker_active_section if hasattr(context.scene, 'bone_picker_active_section') else "1"
                    
                    # Check if clicking on a button (only from active section)
                    sorted_buttons = sorted(
                        [btn for btn in context.scene.bone_picker_buttons if (btn.section if btn.section else "1") == active_section],
                        key=lambda x: (not x.is_empty, x.z_order),
                        reverse=True
                    )
                    
                    clicked_button = None
                    for item in sorted_buttons:
                        if item.is_hidden:
                            # Allow interaction with hidden buttons if show_all_hidden is active
                            if not self.show_all_hidden:
                                continue
                        if self.is_point_in_button(event.mouse_region_x, event.mouse_region_y, item):
                            clicked_button = item
                            break
                    
                    if clicked_button:
                        # Alt+Middle mouse = drag button position
                        if event.alt:
                            if not clicked_button.is_locked:
                                self.alt_middle_dragging = True
                                self.alt_middle_drag_button = clicked_button
                                self.alt_middle_drag_offset_x = event.mouse_region_x - clicked_button.pos_x
                                self.alt_middle_drag_offset_y = event.mouse_region_y - clicked_button.pos_y
                            return {'RUNNING_MODAL'}
                        
                        # Check for double click
                        if (self.last_middle_click_button == clicked_button and 
                            current_time - self.last_middle_click_time < self.double_click_threshold):
                            # Double click detected - toggle circle shape
                            clicked_button.is_circle = not clicked_button.is_circle
                            self.last_middle_click_time = 0
                            self.last_middle_click_button = None
                            self.report({'INFO'}, f"Toggled to {'circle' if clicked_button.is_circle else 'rectangle'}")
                            return {'RUNNING_MODAL'}
                        else:
                            # Single click - start resize if not locked
                            if not clicked_button.is_locked:
                                self.interactive_resizing = True
                                self.interactive_resize_button = clicked_button
                                self.interactive_resize_start_x = event.mouse_region_x
                                self.interactive_resize_start_width = clicked_button.width
                                self.interactive_resize_start_height = clicked_button.height
                            
                            # Store for double click detection
                            self.last_middle_click_time = current_time
                            self.last_middle_click_button = clicked_button
                            return {'RUNNING_MODAL'}
                
                elif event.value == 'RELEASE':
                    if self.alt_middle_dragging:
                        self.alt_middle_dragging = False
                        self.alt_middle_drag_button = None
                        return {'RUNNING_MODAL'}
                    
                    if self.interactive_resizing:
                        self.interactive_resizing = False
                        self.interactive_resize_button = None
                        return {'RUNNING_MODAL'}
            
            if event.type == 'LEFTMOUSE':
                if event.value == 'PRESS':
                    # Check if Alt is held for box selection
                    if event.alt:
                        self.box_selecting = True
                        self.box_start_x = event.mouse_region_x
                        self.box_start_y = event.mouse_region_y
                        self.box_end_x = event.mouse_region_x
                        self.box_end_y = event.mouse_region_y
                        return {'RUNNING_MODAL'}
                    
                    # Check if clicking on resize handle first (skip locked buttons)
                    active_section = context.scene.bone_picker_active_section if hasattr(context.scene, 'bone_picker_active_section') else "1"
                    
                    for item in context.scene.bone_picker_buttons:
                        # Only check buttons from active section
                        item_section = item.section if item.section else "1"
                        if item_section != active_section:
                            continue
                        if item.is_locked:
                            continue
                        if item.is_hidden and not self.show_all_hidden:
                            continue
                        if self.is_point_in_resize_handle(event.mouse_region_x, event.mouse_region_y, item):
                            self.resizing_button = item
                            self.resize_start_width = item.width
                            self.resize_start_height = item.height
                            self.resize_start_x = event.mouse_region_x
                            self.resize_start_y = event.mouse_region_y
                            return {'RUNNING_MODAL'}
                    
                    # Check if clicking on a button (skip locked buttons for dragging)
                    # Sort by z_order and layer - check top buttons first
                    sorted_buttons = sorted(
                        [btn for btn in context.scene.bone_picker_buttons if (btn.section if btn.section else "1") == active_section],
                        key=lambda x: (not x.is_empty, x.z_order),
                        reverse=True
                    )
                    
                    for item in sorted_buttons:
                        if item.is_hidden and not self.show_all_hidden:
                            continue
                        if self.is_point_in_button(event.mouse_region_x, event.mouse_region_y, item):
                            if not item.is_locked:
                                # Check if Shift is held for multi-selection
                                if event.shift:
                                    # Toggle selection
                                    if item in self.selected_buttons:
                                        self.selected_buttons.remove(item)
                                    else:
                                        self.selected_buttons.append(item)
                                    return {'RUNNING_MODAL'}
                                else:
                                    # Single selection - start drag
                                    if item not in self.selected_buttons:
                                        self.selected_buttons = [item]
                                    
                                    # Start multi-drag
                                    self.multi_dragging = True
                                    self.multi_drag_start_x = event.mouse_region_x
                                    self.multi_drag_start_y = event.mouse_region_y
                                    
                                    self.dragging_button = item
                                    self.drag_offset_x = event.mouse_region_x - item.pos_x
                                    self.drag_offset_y = event.mouse_region_y - item.pos_y
                            self.click_start_x = event.mouse_region_x
                            self.click_start_y = event.mouse_region_y
                            self.clicked_button = item
                            return {'RUNNING_MODAL'}
                
                elif event.value == 'RELEASE':
                    # Handle box selection
                    if self.box_selecting:
                        self.box_selecting = False
                        # Select all buttons within box
                        min_x = min(self.box_start_x, self.box_end_x)
                        max_x = max(self.box_start_x, self.box_end_x)
                        min_y = min(self.box_start_y, self.box_end_y)
                        max_y = max(self.box_start_y, self.box_end_y)
                        
                        # If not shift, deselect all first
                        if not event.shift:
                            bpy.ops.pose.select_all(action='DESELECT')
                        
                        # Get active section
                        active_section = context.scene.bone_picker_active_section if hasattr(context.scene, 'bone_picker_active_section') else "1"
                        
                        # Select bones whose buttons are in the box (only from active section)
                        bones_to_select = []
                        for item in context.scene.bone_picker_buttons:
                            # Only check buttons from active section
                            item_section = item.section if item.section else "1"
                            if item_section != active_section:
                                continue
                            if item.is_empty:
                                continue
                            if item.is_hidden and not self.show_all_hidden:
                                continue
                            # Check if button center is in box
                            btn_center_x = item.pos_x + item.width / 2
                            btn_center_y = item.pos_y + item.height / 2
                            if (min_x <= btn_center_x <= max_x and 
                                min_y <= btn_center_y <= max_y):
                                if item.bone_name in context.active_object.pose.bones:
                                    bones_to_select.append(item.bone_name)
                        
                        # Blender 5.0 compatible: Select bones via edit mode
                        if bones_to_select:
                            try:
                                bpy.ops.object.mode_set(mode='EDIT')
                                for bone_name in bones_to_select:
                                    if bone_name in context.active_object.data.edit_bones:
                                        context.active_object.data.edit_bones[bone_name].select = True
                                        context.active_object.data.edit_bones[bone_name].select_head = True
                                        context.active_object.data.edit_bones[bone_name].select_tail = True
                                bpy.ops.object.mode_set(mode='POSE')
                            except:
                                # Fallback: try to restore pose mode
                                try:
                                    if context.mode != 'POSE':
                                        bpy.ops.object.mode_set(mode='POSE')
                                except:
                                    pass
                        
                        return {'RUNNING_MODAL'}
                    
                    if self.resizing_button:
                        self.resizing_button = None
                        return {'RUNNING_MODAL'}
                    
                    if self.dragging_button:
                        # Check if it was a click (not a drag)
                        distance = ((event.mouse_region_x - self.click_start_x)**2 + 
                                   (event.mouse_region_y - self.click_start_y)**2)**0.5
                        if distance < 5:
                            # Check if it's a pose button
                            if self.dragging_button.is_pose:
                                # Apply pose
                                bpy.ops.bonepicker.apply_pose(pose_data_json=self.dragging_button.pose_data)
                            elif not self.dragging_button.is_empty:
                                # Select the bone
                                add_to_selection = event.shift
                                bpy.ops.bonepicker.pick_bone(
                                    bone_name=self.dragging_button.bone_name,
                                    add_to_selection=add_to_selection
                                )
                        
                        # Clear drag start positions
                        for btn in self.selected_buttons:
                            if hasattr(btn, '_drag_start_x'):
                                delattr(btn, '_drag_start_x')
                            if hasattr(btn, '_drag_start_y'):
                                delattr(btn, '_drag_start_y')
                        
                        self.dragging_button = None
                        self.clicked_button = None
                        self.multi_dragging = False
                        return {'RUNNING_MODAL'}
                    
                    # Handle click on locked button
                    if hasattr(self, 'clicked_button') and self.clicked_button:
                        distance = ((event.mouse_region_x - self.click_start_x)**2 + 
                                   (event.mouse_region_y - self.click_start_y)**2)**0.5
                        if distance < 5:
                            # Check if it's a pose button
                            if self.clicked_button.is_pose:
                                # Apply pose
                                bpy.ops.bonepicker.apply_pose(pose_data_json=self.clicked_button.pose_data)
                            elif not self.clicked_button.is_empty:
                                # Select the bone
                                add_to_selection = event.shift
                                bpy.ops.bonepicker.pick_bone(
                                    bone_name=self.clicked_button.bone_name,
                                    add_to_selection=add_to_selection
                                )
                        self.clicked_button = None
                        return {'RUNNING_MODAL'}
            
            if event.type == 'MOUSEMOVE':
                # Alt+Middle mouse drag
                if self.alt_middle_dragging and self.alt_middle_drag_button:
                    self.alt_middle_drag_button.pos_x = event.mouse_region_x - self.alt_middle_drag_offset_x
                    self.alt_middle_drag_button.pos_y = event.mouse_region_y - self.alt_middle_drag_offset_y
                    return {'RUNNING_MODAL'}
                
                # Interactive resize with middle mouse
                if self.interactive_resizing and self.interactive_resize_button:
                    delta_x = event.mouse_region_x - self.interactive_resize_start_x
                    # Scale factor: 1 pixel = 1 unit change
                    scale_factor = 1.0
                    new_width = max(10, self.interactive_resize_start_width + (delta_x * scale_factor))
                    # Maintain aspect ratio
                    aspect_ratio = self.interactive_resize_start_height / self.interactive_resize_start_width if self.interactive_resize_start_width > 0 else 1.0
                    new_height = new_width * aspect_ratio
                    
                    self.interactive_resize_button.width = new_width
                    self.interactive_resize_button.height = max(10, new_height)
                    return {'RUNNING_MODAL'}
                
                # Update box selection
                if self.box_selecting:
                    self.box_end_x = event.mouse_region_x
                    self.box_end_y = event.mouse_region_y
                    return {'RUNNING_MODAL'}
                
                if self.resizing_button:
                    # Update button size
                    delta_x = event.mouse_region_x - self.resize_start_x
                    delta_y = event.mouse_region_y - self.resize_start_y
                    self.resizing_button.width = max(10, self.resize_start_width + delta_x)
                    self.resizing_button.height = max(10, self.resize_start_height + delta_y)
                    return {'RUNNING_MODAL'}
                
                if self.dragging_button:
                    # Update button position - move all selected buttons
                    if self.multi_dragging and len(self.selected_buttons) > 0:
                        delta_x = event.mouse_region_x - self.multi_drag_start_x
                        delta_y = event.mouse_region_y - self.multi_drag_start_y
                        
                        for btn in self.selected_buttons:
                            if not btn.is_locked:
                                # Store original position if not stored
                                if not hasattr(btn, '_drag_start_x'):
                                    btn._drag_start_x = btn.pos_x
                                    btn._drag_start_y = btn.pos_y
                                
                                btn.pos_x = btn._drag_start_x + delta_x
                                btn.pos_y = btn._drag_start_y + delta_y
                    else:
                        # Single button drag
                        self.dragging_button.pos_x = event.mouse_region_x - self.drag_offset_x
                        self.dragging_button.pos_y = event.mouse_region_y - self.drag_offset_y
                    return {'RUNNING_MODAL'}
        
        return {'PASS_THROUGH'}
    
    def invoke(self, context, event):
        global _draw_handler, _picker_window_active
        
        # Picker will stay active but only visible in POSE mode
        if context.mode != 'POSE':
            self.report({'INFO'}, "Picker activated - Switch to Pose Mode to see canvas")
        
        if context.area.type == 'VIEW_3D':
            # Add the draw handler
            args = (self, context)
            _draw_handler = SpaceView3D.draw_handler_add(draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
            _picker_window_active = True
            
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}
    
    def cancel(self, context):
        global _draw_handler, _picker_window_active
        
        if _draw_handler:
            SpaceView3D.draw_handler_remove(_draw_handler, 'WINDOW')
            _draw_handler = None
        _picker_window_active = False
        context.area.tag_redraw()
    
    def is_point_in_button(self, x, y, button):
        return (button.pos_x <= x <= button.pos_x + button.width and
                button.pos_y <= y <= button.pos_y + button.height)
    
    def is_point_in_resize_handle(self, x, y, button):
        handle_size = 10
        handle_x = button.pos_x + button.width - handle_size
        handle_y = button.pos_y
        return (handle_x <= x <= handle_x + handle_size and
                handle_y <= y <= handle_y + handle_size)

class BONEPICKER_AddonPreferences(bpy.types.AddonPreferences):
    """Addon preferences with keybinding information"""
    bl_idname = __name__
    
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="Keyboard Shortcuts:", icon='KEYINGSET')
        
        col = box.column(align=True)
        col.label(text="Canvas Controls:")
        col.label(text="  • ESC - Close picker canvas")
        col.label(text="  • Alt+1 to Alt+9 - Switch sections")
        col.label(text="  • Alt+L - Lock/unlock selected buttons")
        col.label(text="  • Alt+` (backtick) - Show all hidden buttons (hold)")
        
        col.separator()
        col.label(text="Button Manipulation:")
        col.label(text="  • Left Click+Drag - Move button")
        col.label(text="  • Shift+Left Click - Multi-select buttons")
        col.label(text="  • Alt+Left Drag - Box selection")
        col.label(text="  • Middle Mouse Drag - Resize button")
        col.label(text="  • Middle Mouse 2x Click - Toggle circle/rectangle")
        col.label(text="  • Alt+Middle Drag - Move button position")
        
        col.separator()
        col.label(text="Bone Selection:")
        col.label(text="  • Click Button - Select bone")
        col.label(text="  • Shift+Click Button - Add to selection")
        
        box = layout.box()
        box.label(text="Features:", icon='INFO')
        col = box.column(align=True)
        col.label(text="• 9 Sections (tabs) for organizing buttons")
        col.label(text="• Pose Library - Save and apply poses with thumbnails")
        col.label(text="• Custom colors, shapes, and images")
        col.label(text="• Lock, hide, and layer management")
        col.label(text="• Multi-selection and bulk operations")

class BONEPICKER_PT_MainPanel(Panel):
    """Main panel for bone picker buttons"""
    bl_label = "QuickBonePicker by Aman v1.0"
    bl_idname = "BONEPICKER_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Bone Picker'
    
    @classmethod
    def poll(cls, context):
        return context.mode in {'OBJECT', 'POSE'}
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Open Picker Window button
        row = layout.row()
        row.operator("bonepicker.open_window", text="Open Picker Canvas", icon='WINDOW')
        if context.mode != 'POSE':
            layout.label(text="(Pose Mode for bone selection)", icon='INFO')
        
        layout.separator()
        
        # Section Tabs (1-9)
        box = layout.box()
        box.label(text="Sections (Alt+1-9):", icon='OUTLINER_COLLECTION')
        
        active_section = scene.bone_picker_active_section if hasattr(scene, 'bone_picker_active_section') else "1"
        
        # Row 1: Sections 1-5
        row = box.row(align=True)
        for i in range(1, 6):
            section_num = str(i)
            op = row.operator("bonepicker.switch_section", text=section_num, depress=(active_section == section_num))
            op.section_number = section_num
        
        # Row 2: Sections 6-9
        row = box.row(align=True)
        for i in range(6, 10):
            section_num = str(i)
            op = row.operator("bonepicker.switch_section", text=section_num, depress=(active_section == section_num))
            op.section_number = section_num
        
        box.label(text=f"Active: Section {active_section}", icon='RADIOBUT_ON')
        
        layout.separator()
        
        # Add button section
        box = layout.box()
        box.label(text="Create Button:", icon='ADD')
        row = box.row()
        if context.active_pose_bone:
            row.label(text=f"Active: {context.active_pose_bone.name}", icon='BONE_DATA')
        else:
            row.label(text="Select a bone in Pose Mode", icon='INFO')
        
        row = box.row(align=True)
        row.operator("bonepicker.add_button", icon='BONE_DATA')
        row.operator("bonepicker.add_empty_button", text="Add Empty", icon='MESH_PLANE')
        
        # Pose Library
        row = box.row()
        row.operator("bonepicker.save_pose", text="Save Pose", icon='ARMATURE_DATA')
        
        layout.separator()
        
        # Bulk operations section
        box = layout.box()
        box.label(text="Bulk Operations:", icon='MODIFIER')
        
        row = box.row(align=True)
        row.operator("bonepicker.lock_all_empty", text="Lock All Empty", icon='LOCKED')
        row.operator("bonepicker.unlock_all_empty", text="Unlock", icon='UNLOCKED')
        
        row = box.row(align=True)
        row.operator("bonepicker.lock_all_bone", text="Lock All Bone", icon='LOCKED')
        row.operator("bonepicker.unlock_all_bone", text="Unlock", icon='UNLOCKED')
        
        row = box.row(align=True)
        row.operator("bonepicker.hide_all", text="Hide All", icon='HIDE_ON')
        row.operator("bonepicker.unhide_all", text="Unhide All", icon='HIDE_OFF')
        
        layout.separator()
        
        # Manage buttons section with expand/collapse
        box = layout.box()
        row = box.row(align=True)
        
        # Toggle button with icon
        icon = 'DOWNARROW_HLT' if scene.bone_picker_show_manage else 'RIGHTARROW'
        row.prop(scene, "bone_picker_show_manage", text="Manage Buttons", icon=icon, toggle=True, emboss=False)
        
        # Show button count
        button_count = len(scene.bone_picker_buttons)
        row.label(text=f"({button_count})", icon='PREFERENCES')
        
        # Only show content if expanded
        if scene.bone_picker_show_manage:
            if len(scene.bone_picker_buttons) == 0:
                box.label(text="No buttons created yet")
            else:
                # Group buttons by section
                sections = {}
                for i, item in enumerate(scene.bone_picker_buttons):
                    section_name = item.section if item.section else "1"
                    if section_name not in sections:
                        sections[section_name] = []
                    sections[section_name].append((i, item))
                
                # Draw each section
                for section_name in sorted(sections.keys()):
                    section_box = box.box()
                    
                    # Section header with hide/show buttons
                    header_row = section_box.row(align=True)
                    header_row.label(text=f"Section {section_name} ({len(sections[section_name])})", icon='OUTLINER_COLLECTION')
                    
                    # Hide/Show section buttons
                    op = header_row.operator("bonepicker.hide_section", text="", icon='HIDE_ON')
                    op.section_name = section_name
                    op = header_row.operator("bonepicker.show_section", text="", icon='HIDE_OFF')
                    op.section_name = section_name
                    
                    # Sort buttons within section by layer and z_order
                    sorted_buttons = sorted(
                        sections[section_name],
                        key=lambda x: (not x[1].is_empty, x[1].z_order),
                        reverse=True
                    )
                    
                    for i, item in sorted_buttons:
                        row = section_box.row(align=True)
                        
                        # Show layer number
                        layer_text = f"[L{item.z_order}] "
                        if item.is_empty:
                            row.label(text=layer_text + "[Empty]", icon='MESH_PLANE')
                        elif item.is_pose:
                            row.label(text=layer_text + "[Pose] " + item.button_label, icon='ARMATURE_DATA')
                        else:
                            # Check if bone is selected
                            is_selected = False
                            if context.active_object and context.active_object.type == 'ARMATURE':
                                try:
                                    is_selected = item.bone_name in {bone.name for bone in context.selected_pose_bones}
                                except:
                                    pass
                            
                            # Highlight selected bones in panel
                            if is_selected:
                                row.alert = True
                            row.label(text=layer_text + item.button_label, icon='BONE_DATA')
                        
                        # Section button
                        op = row.operator("bonepicker.set_section", text="", icon='OUTLINER_COLLECTION')
                        op.index = i
                        
                        # Hide/Show button
                        hide_icon = 'HIDE_ON' if item.is_hidden else 'HIDE_OFF'
                        op = row.operator("bonepicker.toggle_hide", text="", icon=hide_icon)
                        op.index = i
                        
                        # Toggle circle shape
                        circle_icon = 'MESH_CIRCLE' if item.is_circle else 'MESH_PLANE'
                        op = row.operator("bonepicker.toggle_circle", text="", icon=circle_icon)
                        op.index = i
                        
                        # Set color button
                        op = row.operator("bonepicker.set_color", text="", icon='COLOR')
                        op.index = i
                        
                        # Lock/Unlock button
                        lock_icon = 'LOCKED' if item.is_locked else 'UNLOCKED'
                        op = row.operator("bonepicker.toggle_lock", text="", icon=lock_icon)
                        op.index = i
                        
                        # Layer order controls
                        op = row.operator("bonepicker.bring_to_front", text="", icon='TRIA_UP')
                        op.index = i
                        op = row.operator("bonepicker.send_to_back", text="", icon='TRIA_DOWN')
                        op.index = i
                        
                        # Set image button (for empty buttons and pose buttons)
                        if item.is_empty or item.is_pose:
                            op = row.operator("bonepicker.set_button_image", text="", icon='IMAGE_DATA')
                            op.index = i
                        
                        # Resize button
                        op = row.operator("bonepicker.resize_button", text="", icon='FULLSCREEN_ENTER')
                        op.index = i
                        # Rename button
                        op = row.operator("bonepicker.rename_button", text="", icon='GREASEPENCIL')
                        op.index = i
                        # Remove button
                        op = row.operator("bonepicker.remove_button", text="", icon='X')
                        op.index = i

classes = (
    BonePickerButton,
    BONEPICKER_AddonPreferences,
    BONEPICKER_OT_AddButton,
    BONEPICKER_OT_AddEmptyButton,
    BONEPICKER_OT_SavePose,
    BONEPICKER_OT_ApplyPose,
    BONEPICKER_OT_RemoveButton,
    BONEPICKER_OT_RenameButton,
    BONEPICKER_OT_ResizeButton,
    BONEPICKER_OT_SetButtonImage,
    BONEPICKER_OT_ToggleCircleShape,
    BONEPICKER_OT_SetButtonColor,
    BONEPICKER_OT_ToggleLock,
    BONEPICKER_OT_ToggleHide,
    BONEPICKER_OT_BringToFront,
    BONEPICKER_OT_SendToBack,
    BONEPICKER_OT_LockAllEmpty,
    BONEPICKER_OT_UnlockAllEmpty,
    BONEPICKER_OT_LockAllBone,
    BONEPICKER_OT_UnlockAllBone,
    BONEPICKER_OT_HideAll,
    BONEPICKER_OT_UnhideAll,
    BONEPICKER_OT_SetSection,
    BONEPICKER_OT_SwitchSection,
    BONEPICKER_OT_HideSection,
    BONEPICKER_OT_ShowSection,
    BONEPICKER_OT_PickBone,
    BONEPICKER_OT_OpenPickerWindow,
    BONEPICKER_PT_MainPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.bone_picker_buttons = CollectionProperty(type=BonePickerButton)
    bpy.types.Scene.bone_picker_show_manage = BoolProperty(
        name="Show Manage Buttons",
        description="Show or hide the manage buttons section",
        default=False
    )
    bpy.types.Scene.bone_picker_active_section = StringProperty(
        name="Active Section",
        description="Currently active section (1-9)",
        default="1"
    )
    
    # Register keymaps
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        
        # Alt+1 through Alt+9 for section switching (already handled in modal)
        # These are documented but handled internally by the modal operator
        
        # Optional: Add keymap for opening picker canvas
        # kmi = km.keymap_items.new('bonepicker.open_window', 'P', 'PRESS', ctrl=True, shift=True)
        # addon_keymaps.append((km, kmi))

def unregister():
    global _draw_handler, _picker_window_active
    
    if _draw_handler:
        SpaceView3D.draw_handler_remove(_draw_handler, 'WINDOW')
        _draw_handler = None
    _picker_window_active = False
    
    # Unregister keymaps
    # for km, kmi in addon_keymaps:
    #     km.keymap_items.remove(kmi)
    # addon_keymaps.clear()
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.bone_picker_buttons
    del bpy.types.Scene.bone_picker_show_manage
    del bpy.types.Scene.bone_picker_active_section

if __name__ == "__main__":
    register()
