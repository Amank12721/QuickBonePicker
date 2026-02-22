# QuickBonePicker v1.0

A Blender addon that lets you create custom buttons for selecting bones in your armature. Instead of clicking around the viewport to find bones, you can build a visual picker interface with buttons that select bones instantly.

## Why Use This?

When animating characters with complex rigs, finding and selecting the right bone can slow you down. QuickBonePicker solves this by letting you create a custom button layout that matches your character. Click a button, select a bone. Simple as that.

## Features

### Button Creation
- Create buttons linked to specific bones in your armature
- Add empty buttons for backgrounds and reference images
- Customize button colors with RGB picker
- Choose between circle or rectangle shapes
- Add images to empty buttons with automatic aspect ratio preservation

### Interactive Controls
- Drag buttons to reposition them in the viewport
- Resize buttons by dragging with middle mouse
- Multi-select buttons with Shift+Click
- Box selection for selecting multiple bones at once (Alt+Drag)
- Double-click middle mouse to toggle between circle and rectangle shapes

### Organization
- Layer system with z-order control (bring to front/send to back)
- Lock buttons to prevent accidental movement
- Hide buttons temporarily or permanently
- Bulk operations for locking, unlocking, hiding, and showing buttons

### Keyboard Shortcuts
- Alt+L: Lock or unlock selected buttons
- Alt+` (backtick): Hold to temporarily show all hidden buttons
- Alt+Drag: Box selection for bones
- Alt+Middle Mouse Drag: Move button position
- Middle Mouse Drag: Resize button
- Middle Mouse Double-Click: Toggle shape
- ESC: Close picker window

## Installation

1. Download the `QuickBonePicker_v1.py` file
2. Open Blender and go to Edit > Preferences > Add-ons
3. Click Install and select the downloaded file
4. Enable the addon by checking the box next to "QuickBonePicker by Aman"
5. The panel will appear in the 3D View sidebar under the Bone Picker tab

## Getting Started

1. Select your armature and switch to Pose Mode
2. Select a bone you want to create a button for
3. Open the Bone Picker panel in the sidebar (press N if hidden)
4. Click "Add Bone Button"
5. Click "Open Picker Canvas" to see your button in the viewport
6. Click the button to select that bone

You can create as many buttons as you need and arrange them however you like. The picker window stays open while you work, so you can quickly switch between bones as you animate.

## Usage Tips

**Background Images**: Use empty buttons to add character reference images behind your bone buttons. This makes it easier to remember which button controls which part of the character.

**Lock Your Layout**: Once you've arranged your buttons, lock the background elements so you don't accidentally move them while working.

**Layer Organization**: Empty buttons always draw behind bone buttons, so you can layer your interface without buttons overlapping incorrectly.

**Multi-Selection**: Select multiple buttons with Shift+Click, then drag any selected button to move them all together. Useful for repositioning groups of buttons.

**Hidden Buttons**: If you have buttons you only need occasionally, hide them to reduce clutter. Press Alt+` to temporarily reveal all hidden buttons when needed.

**Box Selection**: Hold Alt and drag to create a selection box. Any bone whose button center falls within the box will be selected. Hold Shift+Alt to add to your current selection.

## Button Properties

Each button in the panel shows its layer number and provides quick access to:

- Eye icon: Hide or show the button
- Shape icon: Toggle between circle and rectangle
- Color icon: Open color picker
- Lock icon: Lock or unlock position
- Up/Down arrows: Change layer order
- Image icon (empty buttons): Add background image
- Resize icon: Set exact dimensions
- Pencil icon: Rename button
- X icon: Delete button

## Bulk Operations

The panel includes bulk operation buttons for managing multiple buttons at once:

- Lock/Unlock All Empty: Manage all background buttons
- Lock/Unlock All Bone: Manage all bone selection buttons
- Hide/Unhide All: Toggle visibility for all buttons

## Compatibility

This addon works with Blender 2.80 and later, including Blender 4.x and 5.0. It has been tested on Windows, macOS, and Linux.

## Technical Notes

The picker window uses GPU drawing to render buttons directly in the viewport. This approach keeps the interface responsive even with many buttons. The addon automatically handles mode switching and will only show the picker interface when you're in Pose Mode.

For Blender 5.0 users: The addon includes compatibility fixes for bone selection API changes in Blender 5.0, so it works seamlessly across versions.

## Changelog

### Version 1.0
- Initial release
- Custom bone picker buttons with drag and drop
- Multi-selection and box selection support
- Interactive resize with middle mouse
- Circle and rectangle shape options
- Custom colors per button
- Image support for empty buttons with aspect ratio preservation
- Layer system with z-order control
- Lock and hide functionality
- Bulk operations for managing multiple buttons
- Keyboard shortcuts for common actions
- Full compatibility with Blender 2.80 through 5.0

## Author

Created by Aman

## License

Free to use for personal and commercial projects.

## Support

If you encounter issues or have suggestions for improvements, please report them through the appropriate channels. Feedback helps make the addon better for everyone.
