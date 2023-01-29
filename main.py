import functools
from enum import Enum
# noinspection PyProtectedMember
from typing import TypeVar, Annotated, _AnnotatedAlias
from maya import cmds, mel


class Element(Enum): TOGGLE, TEXT_FIELD, SLIDER, DROPDOWN = 0, 1, 2, 3


def toggle(label, group=""): return Annotated[bool, Element.TOGGLE, label, group]


def text_field(label, group=""): return Annotated[str, Element.TEXT_FIELD, label, group]


def slider(label, group="", min=1.0, max=10.0):
    slider_type = TypeVar('slider_type')
    return Annotated[slider_type, Element.SLIDER, label, group, min, max]


def dropdown(label, group="", *choices): return Annotated[str, Element.DROPDOWN, label, group, choices]


class ArmRigBuilder:
    """ This class defines a tool that has the objective to build a rigid arm rig for maya. """

    joint_name: text_field("Joint Name", "Rig Setup Info") = "Arm_Joint"
    """ Joint Base Name """

    ik_handle_name: text_field("Ik Name", "Rig Setup Info") = "IK_Handle"
    """ Ik Handle Base Name"""

    locator_count: slider("Joint Count", "Rig Setup Info", min=1, max=15)[int] = 5
    """ How many joints will be created """

    joint_radius: slider("Joint Radius", "Rig Setup Info", min=0.5, max=10.0)[float] = 3
    """ Joints' Size """

    control_name: text_field("Name", "Control Setup Info") = "Ctrl_Arm"
    """ The control's name """

    control_scale: slider("Scale", "Control Setup Info", min=1, max=20)[float] = 5
    """ The control scale """

    locator_name: text_field("Locator Name", "Locator Handle Info") = "Arm_Locator"
    """ Locator Base Name """

    locator_scale: slider("Locator Scale", "Locator Handle Info")[float] = 3.0
    """ Locators' Size """

    ctrl_of_choice: dropdown("Shape", "Control Setup Info", "Arrow", "FourDArrow", "TwoDArrow", "Plus", "Circle", "Square") = "Circle"

    def __init__(self) -> None:
        self.locator_group: str = ""
        self.locators: list = []
        self.control_builders: dict = {}

        self.control_builders = {
            "Arrow":      ArrowCtrlBuilder(),
            "FourDArrow": FourDArrowCtrlBuilder(),
            "TwoDArrow":  TwoDArrowCtrlBuilder(),
            "Plus":       PlusCtrlBuilder(),
            "Circle":     CircleCtrlBuilder(),
            "Square":     SquareCtrlBuilder()
        }

    def create_locator(self):
        """ CreateLocator is a method of the class ArmRig which creates locators in the scene based on user input. """
        self.locators = []
        for i in range(1, self.locator_count + 1):
            locator = cmds.spaceLocator(n=self.locator_name + "{}{}".format("_", i), position=(0, 0, 5 * i))
            cmds.scale(self.locator_scale, self.locator_scale, self.locator_scale)
            cmds.CenterPivot()
            self.locators.append(locator[0])

        self.locator_group = cmds.group(self.locators, n=self.locator_name + "_Group")

        # locatorGroup is string which contains the name of the group
        # locatorList is list of all the locators and its name

    def reset_locator(self):
        """ ResetLocator is a method of the class ArmRig which deletes the created locators (locator list and group). """
        cmds.select(self.locators)
        cmds.delete()
        self.locators.clear()
        cmds.select(self.locator_group)
        cmds.delete()

    def bake_locator_position(self):
        """ SaveLocatorPosition is a method of the class ArmRig which saves the world space position of the locators after they have been placed in the correct position by the user """
        baked_locator_positions = []
        for i in self.locators:
            print(i)
            current_locator_position = cmds.getAttr(i + ".wp")
            baked_locator_positions.append(current_locator_position)

        # locatorNewPosition is a list of position values of every locator
        return baked_locator_positions

    def create_joints(self):
        """ Create the joint objects """
        cmds.select(cl=True)
        for i in range(1, self.locator_count + 1):
            joint = cmds.joint(n=self.joint_name + "{}{}".format("_", i), rad=3)
            locator_list_index = self.locators[i - 1]
            cmds.matchTransform(joint, locator_list_index, pos=True)
        self.reset_locator()

    def create_ik_controllers(self):
        """ Create an ik controllers in the 2 selected joints """
        selected_joints = cmds.ls(sl=True)
        ik_handle = cmds.ikHandle(n=self.ik_handle_name, sj=selected_joints[0], ee=selected_joints[1], s=False, snc=False)

        self.control_builders[self.ctrl_of_choice].ctrlScale = self.control_scale
        self.control_builders[self.ctrl_of_choice].ctrlName = self.control_name
        controller = self.control_builders[self.ctrl_of_choice].build()

        cmds.matchTransform(controller, ik_handle, pos=True, rot=True)

        cmds.FreezeTransformations()
        cmds.parentConstraint(controller, ik_handle[0], mo=True)


class MetadataFragment:
    """ This class is an organized metadata info blob referred to a single variable field contained in a major object,
        Many metadata fragments account for an object's full fields meta reflection """

    def __init__(self, target_ref: object, field_name: str, default_value: object, data) -> None:
        self.bind: tuple[object, str] = target_ref, field_name
        """ The bind, represents the path to reach this variable's reference in memory, its represented by the object containing the variable and the variable's name"""

        self.default: object = default_value
        """ This value refer to the variable's default value """

        self.type: type = data.__origin__
        """ This value refer to the original's variable's annotated type """

        self.ui, self.label, self.group, *self.args = data.__metadata__
        """ Metadata UI info, Metadata UI Label, Metadata UI Group and Metadata UI Args are extracted from the reflection's metadata blob"""

    def __iter__(self) -> tuple[tuple[object, str], object, any]:
        """ Iterate over this object returning [(bind), default value, extra arguments], these are used to make UI widgets """
        yield self.bind
        yield self.default
        yield self.label
        yield from self.args

    def __repr__(self): return f"This fragment relates to the field {self.bind[1]} of {self.bind[0]}"

    @staticmethod
    def extract_reflection(target: object) -> dict[str, list]:
        """ Extract the reflection from the target's instance and populate a dictionary of fragments """
        fragment_groups = {}
        ungrouped_fragments = []
        defaults_values = type(target).__dict__      # Get all the variable names and default values of the target object reference

        for field_name, field_metadata in target.__annotations__.items():                                                     # For each metadata blob acquired from the target
            if isinstance(field_metadata, _AnnotatedAlias) and isinstance(field_metadata.__metadata__[0], Element):           # Check if that blob is about this system
                fragment = MetadataFragment(target, field_name, defaults_values[field_name], field_metadata)                  # Build the reflection fragment using the metadata blob
                (fragment_groups.setdefault(fragment.group, []) if fragment.group else ungrouped_fragments).append(fragment)  # adds it to the groups or ungroup if it has a group

        if ungrouped_fragments:                          # Append the ungrouped fragments at the end of the fragment group's dictionary
            fragment_groups[""] = ungrouped_fragments
        return fragment_groups


class Window:
    """ This class builds a window that controls the arm rigger tool"""
    NAME = "Auto_Rigger_Window"
    UI_BGC = 0.2, 0.2, 0.2
    UI_LIGHT_GRAY = 0.2, 0.2, 0.2
    UI_RED = 0.5, 0.1, 0.1
    UI_GREEN = 0.1, 0.5, 0.1
    UI_BLUE = 0.1, 0.3, 0.5
    SIZE = 350

    def __init__(self, arm_rigging_tool_ref):
        # Get a reference to the arm rigging tool
        self.bucket_tool_ref = arm_rigging_tool_ref

    def open_window(self) -> None:
        """ Open the window """
        if cmds.window(Window.NAME, query=True, exists=True):
            cmds.deleteUI(Window.NAME, window=True)
        self.assemble_window()

    def assemble_window(self) -> str:
        """ Assemble the window, then show it """
        window_element = cmds.window(Window.NAME, sizeable=False)                       # Build a window element
        cmds.columnLayout(columnAttach=('both', 0), columnWidth=Window.SIZE + 20, )     # Attach a column layout to it
        tabs_element   = cmds.tabLayout(innerMarginWidth=5, innerMarginHeight=5)        # Add a tabs element to it

        bucket_tab_element = self.assemble_abstract_tab(self.bucket_tool_ref, self.arm_control_box_widget)  # Build the first Tab "Bucket tool"

        cmds.tabLayout(tabs_element, edit=True, tabLabel=(bucket_tab_element, 'Bucket'))  # Attach the bucket tool tab to the tabs element
        cmds.showWindow(window_element)                                                   # Show the window
        return window_element

    @staticmethod
    def create_tuning_panel_widget(target_ref):
        """ Use a metadata blob to populate a list of UI elements procedurally """
        for group_name, fragments in MetadataFragment.extract_reflection(target_ref).items():
            if group_name:                                                    # For each fragment group
                cmds.frameLayout(l=group_name, cll=True, fn="boldLabelFont")  # Create a frame layout for that group
                cmds.columnLayout(columnAttach=('both', 0), adjustableColumn=True)

            for data in fragments:                          # For each fragment
                print(data.ui)
                if data.ui == Element.TEXT_FIELD:               # If it's flagged as a TEXT_FIELD
                    Window.create_text_field_widget(*data)          # Build a text field widget

                elif data.ui == Element.DROPDOWN:
                    Window.create_dropdown_widget(*data)

                elif data.ui == Element.SLIDER:                 # If it's flagged as a TEXT_FIELD
                    if data.type is int:                            # If its flagged type is INT
                        Window.create_int_slider_widget(*data)          # Build a INT slider widget

                    elif data.type is float:                        # If its flagged type is FLOAT
                        Window.create_float_slider_widget(*data)        # Build a FLOAT slider widget

                elif data.ui == Element.TOGGLE:                 # If it's flagged as a TOGGLE
                    Window.create_toggle_widget(*data)              # Build a toggle widget

            cmds.separator(style="in", h=3)
            if group_name:                                  # If this was a grouped fragment list
                cmds.setParent("..")                            # Reset the parent
                cmds.setParent("..")

    @staticmethod
    def create_int_slider_widget(*args) -> str: return Window.create_abstract_slider_widget(cmds.intSlider, cmds.intField, *args)[0]

    @staticmethod
    def create_float_slider_widget(*args) -> str:
        root_element, text_field_element, slider_element = Window.create_abstract_slider_widget(cmds.floatSlider, cmds.floatField, *args)
        cmds.floatField(text_field_element, edit=True, tze=False, value=args[1])
        return root_element

    @staticmethod
    def create_abstract_slider_widget(cmds_slider_func, cmds_field_func, bind, default, label, min_range, max_range, *_):
        """ Create an abstract slider widget, this method is supposed to be used through create_float_slider and create_int_slider """
        def on_update(value, *_):
            cmds_field_func(text_field_element, edit=True, value=round(float(value), 2))  # update the text field element with the new info
            cmds_slider_func(slider_element, edit=True, value=round(float(value), 2))   # update the slider element with the new info
            setattr(*bind, value)  # overwrite the bound variable's value with the new value

        root_element = cmds.rowLayout(numberOfColumns=3, adjustableColumn3=3, columnWidth3=(75, 35, 30), columnAlign3=["right", "left", "right"], columnAttach3=["both", "both", "right"])
        cmds.text(label=f"{label}:", align="right", font="boldLabelFont")
        text_field_element = cmds_field_func(value=default, cc=on_update)
        slider_element = cmds_slider_func(value=default, min=min_range, max=max_range, cc=on_update, dc=on_update)
        cmds.setParent("..")
        return root_element, text_field_element, slider_element

    @staticmethod
    def create_dropdown_widget(bind, default, label, choices, *_):
        """ Create a dropdown selector widget """
        root_element = cmds.rowLayout(numberOfColumns=2, adjustableColumn2=2, columnWidth2=(75, 70), columnAlign2=["right", "left"], columnAttach2=["both", "right"])
        cmds.text(label=f"{label}:", align="right", font="boldLabelFont")
        menu_element = cmds.optionMenu(changeCommand=lambda item, *_: setattr(*bind, item))
        for name in choices:
            cmds.menuItem(label=name)
        cmds.optionMenu(menu_element, edit=True, value=default)
        cmds.setParent("..")
        return root_element

    @staticmethod
    def create_text_field_widget(bind, default, label, *_) -> str:
        """ Create a text field widget """
        root_element = cmds.rowLayout(numberOfColumns=2, adjustableColumn2=2, columnWidth2=(75, 70), columnAlign2=["right", "left"], columnAttach2=["both", "right"])
        cmds.text(label=f"{label}:", align="right", font="boldLabelFont")
        cmds.textField(text=default, cc=lambda value, *_: setattr(*bind, value))
        cmds.setParent("..")
        return root_element

    @staticmethod
    def create_toggle_widget(bind, default, label, *_) -> str:
        """ Create a toggle widget """
        root_element = cmds.rowLayout(numberOfColumns=3, adjustableColumn3=3, columnWidth3=(75, 66, 53), columnAlign3=["right", "left", "right"], columnAttach3=["both", "both", "right"])
        cmds.text(label=f"{label}:", align="right", font="boldLabelFont")
        cmds.iconTextRadioCollection()
        cmds.iconTextRadioButton(st='textOnly', l='TRUE', hlc=Window.UI_GREEN, bgc=Window.UI_BGC, font="smallFixedWidthFont", fla=False, select=default, cc=lambda value, *_: setattr(*bind, value))
        cmds.iconTextRadioButton(st='textOnly', l='FALSE', hlc=Window.UI_RED, bgc=Window.UI_BGC, font="smallFixedWidthFont", fla=False, select=not default)
        cmds.setParent("..")
        return root_element

    def arm_control_box_widget(self, print_message, show_icon, enable_tuning_panel):
        """ Creates a custom 'arm rigger widget' that serves as state machine and controls other widgets' features """
        def state(message="", icon=""):
            def inner(function):
                def wrapper(*args, **kwargs):
                    if message:
                        print_message(message)
                    if icon:
                        show_icon(icon)
                    cmds.setParent(root_element)
                    children = cmds.columnLayout(root_element, query=True, childArray=True)
                    if children:
                        cmds.deleteUI(children)
                    function(*args, **kwargs)
                return wrapper
            return inner

        # -------------------------------------------------------------STARTING STATE-------------------------------------------------------------------------------------
        @state(" - Welcome!\n - Press the [Start Building Rig] button to start\n   building your arm rig.", "PxrPtexture.svg")
        def starting_state():
            def on_kickstart_tool(*_):
                enable_tuning_panel(False)
                setup_loc_state()
                self.bucket_tool_ref.create_locator()

            cmds.button(label="Start Building Rig", c=on_kickstart_tool, h=127, bgc=Window.UI_GREEN)

        # ------------------------------------------------------------------SETUP LOC STATE--------------------------------------------------------------------------------
        @state(" - I have created some locators.\n - Please move them in the arm's joint positions.\n   In order from the base to the end of the arm", "breakTangent.png")
        def setup_loc_state():
            def on_reset(*_):
                self.bucket_tool_ref.reset_locator()
                self.bucket_tool_ref.create_locator()
                setup_loc_state()

            def on_apply(*_):
                self.bucket_tool_ref.bake_locator_position()
                self.bucket_tool_ref.create_joints()
                setup_ik_state()

            def on_cancel(*_):
                self.bucket_tool_ref.reset_locator()
                enable_tuning_panel(True)
                starting_state()

            cmds.rowLayout(numberOfColumns=1)
            cmds.button(label="Accept", c=on_apply, w=129, h=63, bgc=Window.UI_GREEN)
            cmds.setParent("..")
            cmds.rowLayout(numberOfColumns=2, columnAlign2=["right", "left"], co2=[-1, -1])
            cmds.button(label="Reset", c=on_reset,  w=64, h=62, bgc=Window.UI_RED)
            cmds.button(label="Cancel", c=on_cancel, w=63, h=62, bgc=Window.UI_BGC)

        # ---------------------------------------------------------SETUP IK STATE-------------------------------------------------------------------------------------------
        @state(" - Select 2 Joints from the base to the end of the\n   arm in order to build an IK Control", "breakTangent.png")
        def setup_ik_state():
            def on_build_ik(*_):
                self.bucket_tool_ref.create_ik_controllers()

            def on_finish(*_):
                enable_tuning_panel(True)
                starting_state()

            cmds.button(label="Build IK", c=on_build_ik, w=120, h=62, bgc=Window.UI_BLUE)
            cmds.separator()
            cmds.button(label="Finish", c=on_finish, w=120, h=62, bgc=Window.UI_GREEN)

        # -----------------------------------------------------------------------------------------------------------------------------------------------------------------
        root_element = cmds.columnLayout(bgc=Window.UI_LIGHT_GRAY, columnAttach=('both', 0), adjustableColumn=True, )
        starting_state()
        cmds.setParent("..")
        return root_element

    @staticmethod
    def assemble_abstract_tab(target_reference, control_box) -> tuple[str, str, str]:
        """ This method build an abstract tab, it requires a control box method in order to become concrete, so far only arm_control_box_widget can be used as a valid control_box"""
        main_element = cmds.formLayout(numberOfDivisions=8, h=Window.SIZE + 4)

        # draw tuning box
        tuning_box_element = cmds.scrollLayout(verticalScrollBarThickness=16, childResizable=True)
        cmds.columnLayout(columnAttach=('both', 1), adj=True, rs=2, adjustableColumn=True)
        Window.create_tuning_panel_widget(target_reference)
        cmds.setParent(main_element)

        # draw icon box
        image_box_element = cmds.iconTextStaticLabel(st='iconOnly', i='PxrPtexture.svg', l='spotlight', bgc=Window.UI_BGC)

        #  draw prompt box
        prompt_box_element = cmds.text(label=""" - test\n - test\n - test""", ww=True, al="left", font="fixedWidthFont", bgc=Window.UI_BGC)

        # draw button box, and pass the key methods it needs to be able to control the entire tab
        contrl_box_element = control_box(
            lambda text:  cmds.text(prompt_box_element, edit=True, label=text),             # This method controls the prompt box's texts
            lambda icon:  cmds.iconTextStaticLabel(image_box_element, edit=True, i=icon),   # This method controls the image box's images
            lambda state: cmds.scrollLayout(tuning_box_element, edit=True, enable=state))   # This method controls the tuning box's enabled status

        # attach elements to form
        cmds.formLayout(main_element, edit=True,
            attachPosition=[
                (prompt_box_element, 'top', 1, 6), (prompt_box_element, 'bottom', 2, 8), (prompt_box_element, 'left', 2, 0), (prompt_box_element, 'right', 2, 8),
                (tuning_box_element, 'top', 1, 0), (tuning_box_element, 'bottom', 1, 6), (tuning_box_element, 'left', 1, 0), (tuning_box_element, 'right', 0, 5),
                (contrl_box_element, 'top', 2, 3), (contrl_box_element, 'bottom', 2, 6), (contrl_box_element, 'left', 2, 5), (contrl_box_element, 'right', 2, 8),
                (image_box_element,  'top', 2, 0), (image_box_element,  'bottom', 1, 3), (image_box_element,  'left', 2, 5), (image_box_element,  'right', 2, 8)])

        # Bounce to parent and return root element
        cmds.setParent('..')
        return main_element


class ControllerBuilder:
    def __init__(self, ctrlName = "Ctrl_Arm", ctrlScale = 0.5):
        self.ctrlName = ctrlName  # textFieldGroup
        self.ctrlScale = ctrlScale  # floatSliderGroup


class ArrowCtrlBuilder(ControllerBuilder):
    def __init__(self):
        super().__init__()

    def build(self):
        cmds.curve(n=self.ctrlName, d=1, p=[(0, 0, -1), (2, 0, -1), (2, 0, -2), (4, 0, 0), (2, 0, 2), (2, 0, 1), (0, 0, 1), (0, 0, -1)])
        cmds.scale(self.ctrlScale, self.ctrlScale, self.ctrlScale)
        cmds.CenterPivot()


class FourDArrowCtrlBuilder(ControllerBuilder):
    def __init__(self):
        super().__init__()

    def build(self):
        cmds.curve(n=self.ctrlName, d=1,
            p=[(-1, 0, -1), (-1, 0, -3), (-2, 0, -3), (0, 0, -5), (2, 0, -3), (1, 0, -3), (1, 0, -3), (1, 0, -1), (3, 0, -1), (3, 0, -2), (5, 0, 0), (3, 0, 2), (3, 0, 1), (1, 0, 1), (1, 0, 3),
               (2, 0, 3), (0, 0, 5), (-2, 0, 3), (-1, 0, 3), (-1, 0, 1), (-3, 0, 1), (-3, 0, 2), (-5, 0, 0), (-3, 0, -2), (-3, 0, -1), (-1, 0, -1)])
        cmds.scale(self.ctrlScale, self.ctrlScale, self.ctrlScale)
        cmds.CenterPivot()


class TwoDArrowCtrlBuilder(ControllerBuilder):
    def __init__(self):
        super().__init__()

    def build(self):
        cmds.curve(n=self.ctrlName, d=1, p=[(-3, 0, -1), (3, 0, -1), (3, 0, -2), (5, 0, 0), (3, 0, 2), (3, 0, 1), (-3, 0, 1), (-3, 0, 2), (-5, 0, 0), (-3, 0, -2), (-3, 0, -1)])
        cmds.scale(self.ctrlScale, self.ctrlScale, self.ctrlScale)
        cmds.CenterPivot()


class PlusCtrlBuilder(ControllerBuilder):
    def __init__(self):
        super().__init__()

    def build(self):
        plusShapeCtrl = mel.eval(
            "curve -d 1 -p -1 0 -1 -p -1 0 -3 -p 1 0 -3 -p 1 0 -1 -p 3 0 -1 -p 3 0 1 -p 1 0 1 -p 1 0 3 -p -1 0 3 -p -1 0 1 -p -3 0 1 -p -3 0 -1 -p -1 0 -1 -k 0 -k 1 -k 2 -k 3 -k 4 -k 5 -k 6 -k 7 -k 8 -k 9 -k 10 -k 11 -k 12 ;")
        cmds.rename(plusShapeCtrl, self.ctrlName)
        cmds.scale(self.ctrlScale, self.ctrlScale, self.ctrlScale)
        cmds.CenterPivot()


class CircleCtrlBuilder(ControllerBuilder):
    def __init__(self):
        super().__init__()

    def build(self):
        circle = cmds.circle(n=self.ctrlName, r=1, nr=(0, 1, 0))
        cmds.scale(self.ctrlScale, self.ctrlScale, self.ctrlScale)
        cmds.CenterPivot()
        return circle


class SquareCtrlBuilder(ControllerBuilder):
    def __init__(self):
        super().__init__()

    def build(self):
        squareCtrl = mel.eval("curve -d 1 -p -2 0 -2 -p 2 0 -2 -p 2 0 2 -p -2 0 2 -p -2 0 -2 -k 0 -k 1 -k 2 -k 3 -k 4 ;")
        cmds.rename(squareCtrl, self.ctrlName)
        cmds.scale(self.ctrlScale, self.ctrlScale, self.ctrlScale)
        cmds.CenterPivot()


class Event:    # This class implements a simple event object
    def __init__(self): self.event = []

    def __add__(self, other):
        self.event.append(other)
        return self

    def __sub__(self, other):
        self.event.remove(other)
        return self

    def __call__(self, *args, **kwargs):
        for method in self.event:
            method(*args, **kwargs)


tool = ArmRigBuilder()

window = Window(tool)
window.open_window()
