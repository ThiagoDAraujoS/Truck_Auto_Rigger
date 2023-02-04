from maya import cmds
from maya.api.OpenMaya import MVector
import math
import MASH.api as mapi
#from scripts.tuning_panel_widget import toggle, text_field, slider, dropdown
# noinspection PyProtectedMember
from typing import TypeVar, Annotated, _AnnotatedAlias
from enum import Enum






class Window:
    """ This class builds a window that controls the arm rigger tool"""
    NAME = "Auto_Rigger_Window"
    UI_BGC = 0.2, 0.2, 0.2
    UI_LIGHT_GRAY = 0.2, 0.2, 0.2
    UI_RED = 0.5, 0.1, 0.1
    UI_GREEN = 0.1, 0.5, 0.1
    UI_BLUE = 0.1, 0.3, 0.5
    SIZE = 350

    def __init__(self, arm_rigging_tool_ref, belt_rigging_tool_ref):
        # Get a reference to the arm rigging tool
        self.bucket_tool_ref = arm_rigging_tool_ref
        self.belt_tool_ref = belt_rigging_tool_ref

    def open_window(self) -> None:
        """ Open the window """
        if cmds.window(Window.NAME, query=True, exists=True):
            cmds.deleteUI(Window.NAME, window=True)
        self.assemble_window()

    def assemble_window(self) -> str:
        """ Assemble the window, then show it """
        # Build a window element
        window_element = cmds.window(Window.NAME, sizeable=False)
        cmds.columnLayout(columnAttach=('both', 0), columnWidth=Window.SIZE + 20, )
        tabs_element = cmds.tabLayout(innerMarginWidth=5, innerMarginHeight=5)

        # Build the first Tab "Bucket tool"
        #bucket_tab_element = self.assemble_abstract_tab(self.bucket_tool_ref, self.arm_control_box_widget)
        belt_tab_element = self.assemble_abstract_tab(self.belt_tool_ref, self.belt_control_box_widget)

        # Attach tabs to the tab element
        cmds.tabLayout(tabs_element, edit=True, tabLabel=((belt_tab_element, "Belt")))

        # Show the window
        cmds.showWindow(window_element)
        return window_element

    def belt_control_box_widget(self, print_message, show_icon, enable_tuning_panel):
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
        @state(" - Welcome!\n - Press the [Start Building Rig] button to start\n   building your belt rig.", "PxrPtexture.svg")
        def starting_state():
            def on_kickstart_tool(*_):
                enable_tuning_panel(False)
                position_frame_state()
                self.belt_tool_ref.build_core_ctrl()

            cmds.button(label="Start Building Rig", c=on_kickstart_tool, h=127, bgc=Window.UI_GREEN)

        # ------------------------------------------------------------------SETUP LOC STATE--------------------------------------------------------------------------------
        @state(" - I have created a frame.\n - Please place it on top of the model's wheels/\n   gears.\n", "breakTangent.png")
        def position_frame_state():
            def on_reset(*_):
                self.belt_tool_ref.destroy_core_ctrl()
                self.belt_tool_ref.build_core_ctrl()
                position_frame_state()

            def on_apply(*_):
                self.belt_tool_ref.lock_frame_ctrl()
                self.belt_tool_ref.build_circle_ctrls()
                position_wheels_state()

            def on_back(*_):
                self.belt_tool_ref.destroy_core_ctrl()
                enable_tuning_panel(True)
                starting_state()

            cmds.rowLayout(numberOfColumns=1)
            cmds.button(label="Accept", c=on_apply, w=129, h=63, bgc=Window.UI_GREEN)
            cmds.setParent("..")
            cmds.rowLayout(numberOfColumns=2, columnAlign2=["right", "left"], co2=[-1, -1])
            cmds.button(label="Reset", c=on_reset, w=64, h=62, bgc=Window.UI_RED)
            cmds.button(label="Back", c=on_back, w=63, h=62, bgc=Window.UI_BGC)

        # ---------------------------------------------------------SETUP IK STATE-------------------------------------------------------------------------------------------
        @state(" - Spread these circles on top of each wheel", "breakTangent.png")
        def position_wheels_state():
            def on_reset(*_):
                self.belt_tool_ref.destroy_circle_ctrls()
                self.belt_tool_ref.build_circle_ctrls()
                position_wheels_state()

            def on_apply(*_):
                self.belt_tool_ref.finish()

                enable_tuning_panel(True)
                starting_state()

            def on_back(*_):
                self.belt_tool_ref.destroy_circle_ctrls()
                self.belt_tool_ref.unlock_frame_ctrl()
                position_frame_state()

            cmds.rowLayout(numberOfColumns=1)
            cmds.button(label="Accept", c=on_apply, w=129, h=63, bgc=Window.UI_GREEN)
            cmds.setParent("..")
            cmds.rowLayout(numberOfColumns=2, columnAlign2=["right", "left"], co2=[-1, -1])
            cmds.button(label="Reset", c=on_reset, w=64, h=62, bgc=Window.UI_RED)
            cmds.button(label="Back", c=on_back, w=63, h=62, bgc=Window.UI_BGC)

        # -----------------------------------------------------------------------------------------------------------------------------------------------------------------
        root_element = cmds.columnLayout(bgc=Window.UI_LIGHT_GRAY, columnAttach=('both', 0), adjustableColumn=True, )
        starting_state()
        cmds.setParent("..")
        return root_element

    @staticmethod
    def assemble_abstract_tab(target_reference, control_box) -> tuple[str, str, str]:
        """ This method build an abstract tab, it requires a control box method in order to become concrete, so far only arm_control_box_widget can be used as a valid control_box """
        main_element = cmds.formLayout(numberOfDivisions=8, h=Window.SIZE + 4)

        # draw tuning box
        tuning_box_element = cmds.scrollLayout(verticalScrollBarThickness=16, childResizable=True)
        create_tuning_panel_widget(ref=target_reference, label_size=75, columnAttach=('both', 1), adj=True, rs=2, adjustableColumn=True)
        cmds.setParent("..")

        # draw icon box
        image_box_element = cmds.iconTextStaticLabel(st='iconOnly', i='PxrPtexture.svg', l='spotlight', bgc=Window.UI_BGC)

        #  draw prompt box
        prompt_box_element = cmds.text(label=""" - test\n - test\n - test""", ww=True, al="left", font="fixedWidthFont", bgc=Window.UI_BGC)

        # draw button box, and pass the key methods it needs to be able to control the entire tab
        contrl_box_element = control_box(
            lambda text: cmds.text(prompt_box_element, edit=True, label=text),  # This method controls the prompt box's texts
            lambda icon: cmds.iconTextStaticLabel(image_box_element, edit=True, i=icon),  # This method controls the image box's images
            lambda state: cmds.scrollLayout(tuning_box_element, edit=True, enable=state))  # This method controls the tuning box's enabled status

        # attach elements to form
        cmds.formLayout(main_element, edit=True, attachPosition=[
            (prompt_box_element, 'top', 1, 6), (prompt_box_element, 'bottom', 2, 8), (prompt_box_element, 'left', 2, 0), (prompt_box_element, 'right', 2, 8),
            (tuning_box_element, 'top', 1, 0), (tuning_box_element, 'bottom', 1, 6), (tuning_box_element, 'left', 1, 0), (tuning_box_element, 'right', 0, 5),
            (contrl_box_element, 'top', 2, 3), (contrl_box_element, 'bottom', 2, 6), (contrl_box_element, 'left', 2, 5), (contrl_box_element, 'right', 2, 8),
            (image_box_element, 'top', 2, 0), (image_box_element, 'bottom', 1, 3), (image_box_element, 'left', 2, 5), (image_box_element, 'right', 2, 8)])

        # Bounce to parent and return root element
        cmds.setParent('..')
        return main_element



class Element(Enum):
    """ This Enum describe the type of widgets this module implements """
    TOGGLE, TEXT_FIELD, SLIDER, DROPDOWN = 0, 1, 2, 3


def toggle(label, group = ""):
    """ Metadata stub that declares variable should be bound to a toggle widget """
    return Annotated[bool, Element.TOGGLE, label, group]


def text_field(label, group = ""):
    """ Metadata stub that declares variable should be bound to a text field widget """
    return Annotated[str, Element.TEXT_FIELD, label, group]


def slider(label, group = "", min = 1.0, max = 10.0):
    """ Metadata stub that declares variable should be bound to a slider[int] or slider[float] widget """
    slider_type = TypeVar('slider_type')
    return Annotated[slider_type, Element.SLIDER, label, group, min, max]


def dropdown(label, group = "", *choices):
    """ Metadata stub that declares variable should be bound to a dropdown widget """
    return Annotated[str, Element.DROPDOWN, label, group, choices]


def create_tuning_panel_widget(ref, label_size, *args, **kwargs) -> str:
    """ Command that creates a tuning panel widget """
    root_element = cmds.columnLayout(*args, **kwargs)
    builder = _TuningPanelBuilder(ref, label_size)
    builder.create()
    cmds.setParent("..")
    return root_element


class _MetadataFragment:
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

    @staticmethod
    def extract_reflection(target: object) -> dict[str, list]:
        """ Extract the reflection from the target's instance and populate a dictionary of fragments """
        fragment_groups = {}
        ungrouped_fragments = []
        defaults_values = type(target).__dict__  # Get all the variable names and default values of the target object reference

        for field_name, field_metadata in target.__annotations__.items():  # For each metadata blob acquired from the target
            if isinstance(field_metadata, _AnnotatedAlias) and isinstance(field_metadata.__metadata__[0], Element):  # Check if that blob is about this system
                fragment = _MetadataFragment(target, field_name, defaults_values[field_name], field_metadata)  # Build the reflection fragment using the metadata blob
                (fragment_groups.setdefault(fragment.group, []) if fragment.group else ungrouped_fragments).append(fragment)  # adds it to the groups or ungroup if it has a group

        if ungrouped_fragments:  # Append the ungrouped fragments at the end of the fragment group's dictionary
            fragment_groups[""] = ungrouped_fragments
        return fragment_groups


class _TuningPanelBuilder:
    """ This tool builds a tuning panel widget by reading a target object reference, and binding to its variables """
    UI_BGC = 0.2, 0.2, 0.2
    UI_RED = 0.5, 0.1, 0.1
    UI_GREEN = 0.1, 0.5, 0.1

    def __init__(self, target_ref, label_size: 75):
        self.target_ref = target_ref
        self.label_size = label_size

    def create(self) -> None:
        """ Use a metadata blob to populate a list of UI elements procedurally """

        # Extract the target_ref's reflection and build frame layouts for each category
        for group_name, fragments in _MetadataFragment.extract_reflection(self.target_ref).items():
            if group_name:
                cmds.frameLayout(l=group_name, cll=True, fn="boldLabelFont")
                cmds.columnLayout(columnAttach=('both', 0), adjustableColumn=True)

            # For each metadata fragment, build a widget for it
            for data in fragments:
                if data.ui == Element.TEXT_FIELD:
                    self._create_text_field_widget(*data)

                elif data.ui == Element.DROPDOWN:
                    self._create_dropdown_widget(*data)

                elif data.ui == Element.SLIDER:
                    if data.type is int:
                        self._create_int_slider_widget(*data)

                    elif data.type is float:
                        self._create_float_slider_widget(*data)

                elif data.ui == Element.TOGGLE:
                    self._create_toggle_widget(*data)

            cmds.separator(style="in", h=3)

            # If a frame layout iteration return to parent before creating the next iteration
            if group_name:
                cmds.setParent("..")
                cmds.setParent("..")

    def _create_int_slider_widget(self, *args) -> str:
        return self._create_abstract_slider_widget(cmds.intSlider, cmds.intField, *args)[0]

    def _create_float_slider_widget(self, *args) -> str:
        root_element, text_field_element, slider_element = self._create_abstract_slider_widget(cmds.floatSlider, cmds.floatField, *args)
        cmds.floatField(text_field_element, edit=True, tze=False, value=args[1])
        return root_element

    def _create_abstract_slider_widget(self, cmds_slider_func, cmds_field_func, bind, default, label, min_range, max_range, *_) -> tuple[str, str, str]:
        """ Create an abstract slider widget, this method is supposed to be used through create_float_slider and create_int_slider """

        def on_update(value, *_):
            cmds_field_func(text_field_element, edit=True, value=round(float(value), 2))
            cmds_slider_func(slider_element, edit=True, value=round(float(value), 2))
            setattr(*bind, value)

        root_element = cmds.rowLayout(
            numberOfColumns=3, adjustableColumn3=3, columnWidth3=(self.label_size, 35, 30),
            columnAlign3=["right", "left", "right"], columnAttach3=["both", "both", "right"])

        cmds.text(label=f"{label}:", align="right", font="boldLabelFont")
        text_field_element = cmds_field_func(value=default, cc=on_update)
        slider_element = cmds_slider_func(value=default, min=min_range, max=max_range, cc=on_update, dc=on_update)
        cmds.setParent("..")
        return root_element, text_field_element, slider_element

    def _create_dropdown_widget(self, bind, default, label, choices, *_) -> str:
        """ Create a dropdown selector widget """
        root_element = cmds.rowLayout(
            numberOfColumns=2, adjustableColumn2=2, columnWidth2=(self.label_size, 70),
            columnAlign2=["right", "left"], columnAttach2=["both", "right"])

        cmds.text(label=f"{label}:", align="right", font="boldLabelFont")
        menu_element = cmds.optionMenu(changeCommand=lambda item, *_: setattr(*bind, item))
        for name in choices:
            cmds.menuItem(label=name)
        cmds.optionMenu(menu_element, edit=True, value=default)
        cmds.setParent("..")
        return root_element

    def _create_text_field_widget(self, bind, default, label, *_) -> str:
        """ Create a text field widget """
        root_element = cmds.rowLayout(
            numberOfColumns=2, adjustableColumn2=2, columnWidth2=(self.label_size, 70),
            columnAlign2=["right", "left"], columnAttach2=["both", "right"])

        cmds.text(label=f"{label}:", align="right", font="boldLabelFont")
        cmds.textField(text=default, cc=lambda value, *_: setattr(*bind, value))
        cmds.setParent("..")
        return root_element

    def _create_toggle_widget(self, bind, default, label, *_) -> str:
        """ Create a toggle widget """
        root_element = cmds.rowLayout(
            numberOfColumns=3, adjustableColumn3=3, columnWidth3=(self.label_size, 66, 53),
            columnAlign3=["right", "left", "right"], columnAttach3=["both", "both", "right"])

        cmds.text(label=f"{label}:", align="right", font="boldLabelFont")
        cmds.iconTextRadioCollection()
        cmds.iconTextRadioButton(
            st='textOnly', l='TRUE', hlc=_TuningPanelBuilder.UI_GREEN, bgc=_TuningPanelBuilder.UI_BGC, font="smallFixedWidthFont",
            fla=False, select=default, cc=lambda value, *_: setattr(*bind, value))

        cmds.iconTextRadioButton(
            st='textOnly', l='FALSE', hlc=_TuningPanelBuilder.UI_RED, bgc=_TuningPanelBuilder.UI_BGC, font="smallFixedWidthFont",
            fla=False, select=not default)

        cmds.setParent("..")
        return root_element























class AbstractShape:
    MINIMAL_SIZE = 0.001

    def __init__(self):
        super(AbstractShape, self).__init__()
        self.start: MVector = MVector.kZeroVector
        self.end: MVector = MVector.kZeroVector

    def is_legal(self): return (self.start - self.end).length() >= AbstractShape.MINIMAL_SIZE

    def _trace_logic(self, name) -> str: raise Exception("Abstract Method 'trace_logic' from class 'Shape' was invoked directly")

    def trace_path(self, name) -> str:
        if not self.is_legal():
            return ""
        return self._trace_logic(name)


class Arc(AbstractShape):
    def __init__(self, circle_ref):
        super(Arc, self).__init__()
        self.circle = circle_ref

    def _extrapolate_direction(self, direction) -> MVector: return (direction * self.circle.radius) + self.circle.center

    def extrapolate_start_point(self, direction) -> None: self.start = self._extrapolate_direction(direction)

    def extrapolate_end_point(self, direction) -> None: self.end = self._extrapolate_direction(direction)

    def _trace_logic(self, name: str):
        curve = cmds.createNode("nurbsCurve", name=f"{name}Shape")
        curve_transform = cmds.listRelatives(curve, parent=True)[0]
        cmds.rename(curve_transform, name)
        builder = cmds.createNode("makeTwoPointCircularArc", name="Arc_Builder")
        cmds.connectAttr(f"{builder}.outputCurve", f"{curve}.create")
        cmds.setAttr(f"{builder}.point1", *self.start)
        cmds.setAttr(f"{builder}.point2", *self.end)
        cmds.setAttr(f"{builder}.radius", self.circle.radius)
        cmds.setAttr(f"{builder}.directionVector", 0, 0, -1)
        cmds.delete(curve, constructionHistory=True)
        return curve_transform


class TangentLine(AbstractShape):
    def __init__(self, circle_a, circle_b):
        super(TangentLine, self).__init__()

        self.normal = circle_a.find_positive_external_tangent_normal(circle_b)

        self.start = self.normal * circle_a.radius + circle_a.center
        self.end = self.normal * circle_b.radius + circle_b.center

        base = self.end - self.start

        self.direction = base.normal()
        self.length = base.length()

    def __iter__(self):
        """ Iterate over the points in the tangent line """
        yield from [(self.direction * (self.length * 0.25 * i)) + self.start for i in range(5)]

    def _trace_logic(self, name: str): return cmds.curve(name=name, p=[*self])


class Circle:
    def __init__(self, center: MVector = MVector.kZeroVector, radius: float = 1.0, name=""):
        if name:
            self.build_circle_from_mobject(name)
        else:
            self.center: MVector = center
            self.radius: float = radius
            self.name = ""

    def build_circle_from_mobject(self, name):
        self.name = name
        self.center = MVector(cmds.getAttr(f"{self.name}.translate")[0])
        self.radius = abs(cmds.getAttr(f"{self.name}.scaleX"))

    def __iter__(self):
        yield from self.center
        yield self.radius

    def find_intersection(self, other):
        x0, y0, _, r0 = self
        x1, y1, _, r1 = other

        d = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)

        a = (r0 ** 2 - r1 ** 2 + d ** 2) / (2 * d)
        h = math.sqrt(r0 ** 2 - a ** 2)
        x2 = x0 + a * (x1 - x0) / d
        y2 = y0 + a * (y1 - y0) / d
        x3 = x2 + h * (y1 - y0) / d
        y3 = y2 - h * (x1 - x0) / d

        x4 = x2 - h * (y1 - y0) / d
        y4 = y2 + h * (x1 - x0) / d

        return MVector(x3, y3, 0.0), MVector(x4, y4, 0.0)

    def create_bisector_circle(self, other):
        center: MVector = (other.center - self.center) * 0.5
        return Circle(center + self.center,  center.length())

    def create_difference_circle(self, other):
        MIN_DIFF_VALUE = 0.0001
        return Circle(self.center, max(abs(self.radius - other.radius), MIN_DIFF_VALUE))

    def find_external_tangent_in_system(self, start_direction: MVector, unvisited_nodes):
        """ This sub method build tangents across all the circles and returns the one with closer angle continuation from the start direction """
        smaller_angle = math.inf
        closest_tangent = None
        closest_tangent_segway = None

        for node in unvisited_nodes:
            # If {node} is caller circle skip
            if self == node:
                continue

            # Build tangent
            new_tangent = TangentLine(self, node)
            new_angle = start_direction.angle(new_tangent.direction)

            # If new angle is larger than previous angle, skip
            if new_angle >= smaller_angle:
                continue

            smaller_angle = new_angle
            closest_tangent = new_tangent
            closest_tangent_segway = node

        return closest_tangent, closest_tangent_segway

    def find_positive_external_tangent_normal(self, other) -> MVector:
        is_forward = self.radius > other.radius
        main_circle, target_circle = (self, other) if is_forward else (other, self)

        bisector   = main_circle.create_bisector_circle(target_circle)
        difference = main_circle.create_difference_circle(target_circle)
        pos, neg   = bisector.find_intersection(difference)

        return ((pos if is_forward else neg) - main_circle.center).normal()

    def build_widget(self, name="") -> str:
        if name:
            self.name = cmds.circle(c=self.center, r=self.radius, nr=(0, 0, 1), name=name)
        else:
            self.name = cmds.circle(c=self.center, r=self.radius, nr=(0, 0, 1))
        return self.name


class BeltCurve:

    class _Part:
        """ Simple struct containing an arch curve and a tangent curve """
        def __init__(self, circle):
            self.circle = circle
            self.arc: Arc = Arc(circle)
            # noinspection PyTypeChecker
            self.tangent: TangentLine = None

        def __iter__(self):
            yield self.arc
            yield self.tangent

    def __init__(self, locator_group, name: str):
        # Copy the locator group used to build this object
        locator_group = cmds.duplicate(locator_group, rc=True)[0]

        # Get its children
        locators = cmds.listRelatives(locator_group, c=True, type="transform")

        # Un-parent them
        cmds.parent(locators, w=True, r=True)

        # Build a list of virtual circles based on the locators
        circles = [Circle(name=shape_name) for shape_name in locators]

        # Process the circle list into a list of path parts
        path_parts = self._build_belt_path(circles)

        # Process the path_parts into a curve object and save its name
        self.name = self._trace_curve(path_parts, name)

        # delete the locators and group
        cmds.delete(*locators)
        cmds.delete(locator_group)

    def _build_belt_path(self, circles) -> list[_Part]:
        """This function aims to build a list of curve parts, containing the pieces required to build the belt curve"""
        path: list[BeltCurve._Part] = []

        starting_node = None
        current_node = min(circles, key=lambda o: o.center.x)
        guide_direction = MVector(0, 1, 0)

        path.append(BeltCurve._Part(current_node))

        # While we're not back at the starting node
        while starting_node != current_node:

            # If this is the first iteration, set starting node as the next node
            if not starting_node:
                starting_node = current_node

            # Find the external tangent from current_node to the next_node
            tangent, next_node = current_node.find_external_tangent_in_system(guide_direction, circles)

            # Setup guide direction from tangent
            guide_direction = tangent.direction

            path[-1].arc.extrapolate_end_point(tangent.normal)
            path[-1].tangent = tangent

            path.append(BeltCurve._Part(next_node))
            path[-1].arc.extrapolate_start_point(tangent.normal)

            # set up current node to be this iteration next_node
            current_node = next_node

        # Wrap the belt's last node back to the first one
        path[0].arc.start = path.pop().arc.start

        return path

    def _trace_curve(self, full_path: list[_Part], name: str) -> str:
        shapes = []
        for i, path in enumerate(full_path):
            for j, sub_path in enumerate(path):
                new_curve = sub_path.trace_path(f"part_{i * 2 + j}")
                if new_curve:
                    shapes.append(new_curve)
        cmds.attachCurve(*shapes)
        result = shapes.pop(0)
        cmds.delete(result, constructionHistory=True)
        cmds.delete(*shapes)
        name = cmds.rename(result, f"{name}#")
        return name


class BeltRigBuilder:
    BELT_CTRL_NAME: str = "Belt_Ctrl"

    CORE_CTRL_SIZE: float = 20
    CORE_CTRL_NAME: str = "Belt_Core_Ctrl#"

    CIRCLE_CTRL_SPACING: float = 50
    CIRCLE_CTRL_SIZE: float = 15
    CIRCLE_CTRL_LOCK_BLUEPRINT: list[str] = "rotate", "translateZ"
    CIRCLE_CTRL_NAME: str = "Belt_Circle_Ctrl"

    FRAME_CTRL_NAME: str = "Belt_Frame_Ctrl"
    FRAME_CTRL_WIDTH: float = 160.0
    FRAME_CTRL_HEIGHT: float = 80.0
    FRAME_CTRL_LOCK_BLUEPRINT: list[str] = "scale", "rotate", "translate"

    THREAD_MESH_GROUP_NAME = "Thread_Mesh_#"
    THREAD_JOINT_NAME_PREFIX: str = "Belt_Thread"
    MASTER_JOINT_NAME_PREFIX: str = "Belt_Master"
    JOINT_NAME_SUFFIX: str = "Joint"

    MASH_NETWORK_NAME: str = "MASH_Belt_Thread_Driver"
    MASH_BREAKOUT_CONNECTION_BLUEPRINT: list[tuple[str, str]] = [(".outputs[{i}].translate", ".translate"), (".outputs[{i}].rotate", ".rotate")]

    tread_count: slider("Thread Count", "Setup", 10, 100)[int] = 30
    circle_ctrl_count: slider("Wheel Count", "Setup", 2, 12)[int] = 5

    core_ctrl: text_field("Core", "Optional") = ""
    tread_mesh: text_field("Mesh", "Optional") = ""

    torque: slider("Thread Speed", "Animation", 0.01)[float] = 3.0
    acceleration: slider("Thread Speed", "Animation", 0.01)[float] = 3.0
    is_left: toggle("Is Left", "Animation") = True

    def __init__(self):
        # noinspection PyTypeChecker
        self.belt_ctrl: BeltCurve = None
        self.frame_ctrl: str = ""
        self.master_joint: str = ""

        self.circle_ctrls: list[str] = []
        self.tread_joints: list[str] = []

    def build_core_ctrl(self):
        """ Builds a square frame used as base screen for drawing the belt's controls """
        self.frame_ctrl = cmds.polyPlane(name=f"{BeltRigBuilder.FRAME_CTRL_NAME}#", h=BeltRigBuilder.FRAME_CTRL_HEIGHT,
            w=BeltRigBuilder.FRAME_CTRL_WIDTH, sh=1, sw=1, sx=1, sy=1, ax=MVector.kZaxisVector)[0]
        cmds.move(0, BeltRigBuilder.FRAME_CTRL_HEIGHT * 0.5, BeltRigBuilder.CIRCLE_CTRL_SPACING)
        cmds.setAttr(f"{self.frame_ctrl}.overrideEnabled", 1)
        cmds.setAttr(f"{self.frame_ctrl}.overrideShading", 0)

        if self.core_ctrl and cmds.objExists(self.core_ctrl):
            return

        # build a core control box
        self.core_ctrl = cmds.polyCube(name=BeltRigBuilder.CORE_CTRL_NAME, h=BeltRigBuilder.CORE_CTRL_SIZE, w=BeltRigBuilder.CORE_CTRL_SIZE, d=BeltRigBuilder.CORE_CTRL_SIZE)[0]
        cmds.move(0, BeltRigBuilder.CORE_CTRL_SIZE * 0.5, 0)
        cmds.setAttr(f"{self.core_ctrl}.overrideEnabled", 1)
        cmds.setAttr(f"{self.core_ctrl}.overrideShading", 0)

    def destroy_core_ctrl(self):
        """ delete both the frame control and the core control widgets """
        cmds.delete(self.frame_ctrl, self.core_ctrl)

    def lock_frame_ctrl(self):
        """ Lock some of the frame ctrl's channels"""
        cmds.makeIdentity(self.frame_ctrl, apply=True, s=1, n=0)
        for attribute in BeltRigBuilder.FRAME_CTRL_LOCK_BLUEPRINT:
            cmds.setAttr(f"{self.frame_ctrl}.{attribute}", lock=True)

    def unlock_frame_ctrl(self):
        """ Unlock some of the frame ctrl's channels"""
        for attribute in BeltRigBuilder.FRAME_CTRL_LOCK_BLUEPRINT:
            cmds.setAttr(f"{self.frame_ctrl}.{attribute}", lock=False)

    def _build_circle_ctrl(self):
        """ Build a circle control """
        ctrl = cmds.circle(name=BeltRigBuilder.CIRCLE_CTRL_NAME)[0]
        cmds.scale(BeltRigBuilder.CIRCLE_CTRL_SIZE, BeltRigBuilder.CIRCLE_CTRL_SIZE, 0.0)
        for attribute in BeltRigBuilder.CIRCLE_CTRL_LOCK_BLUEPRINT:
            cmds.setAttr(f"{ctrl}.{attribute}", lock=True)
        return ctrl

    def build_circle_ctrls(self):
        """ Build a collection of circle controls """
        self.circle_ctrls = []
        for i in range(self.circle_ctrl_count):
            ctrl = self._build_circle_ctrl()
            cmds.move(*(MVector.kXaxisVector * (i * BeltRigBuilder.CIRCLE_CTRL_SPACING - BeltRigBuilder.FRAME_CTRL_WIDTH * 0.5)))
            self.circle_ctrls.append(ctrl)
        cmds.parent(*self.circle_ctrls, self.frame_ctrl, r=True)

    def destroy_circle_ctrls(self):
        """ Destroy all circle controls """
        cmds.delete(*self.circle_ctrls)

    def build_belt_ctrl(self):
        """ Build a belt control from the circle controls """
        name = f"{BeltRigBuilder.BELT_CTRL_NAME}#"
        self.belt_ctrl = BeltCurve(self.frame_ctrl, name)
        cmds.parent(self.belt_ctrl.name, self.frame_ctrl, r=True)

    def _create_tread_joints(self):
        """ Create a collection of tread joints and parent them to the master joint """
        position = cmds.getAttr(f"{self.core_ctrl}.translate")[0]
        self.master_joint = cmds.joint(name=f"{BeltRigBuilder.MASTER_JOINT_NAME_PREFIX}_{BeltRigBuilder.JOINT_NAME_SUFFIX}#", p=position)

        self.tread_joints = []
        for i in range(self.tread_count):
            cmds.select(clear=True)
            joint_name = f"{BeltRigBuilder.THREAD_JOINT_NAME_PREFIX}_{BeltRigBuilder.JOINT_NAME_SUFFIX}_{i}_Cluster_#"
            joint_name = cmds.joint(name=joint_name)
            self.tread_joints.append(joint_name)
            cmds.parent(self.tread_joints[i], self.master_joint)
            cmds.setAttr(f"{joint_name}.inheritsTransform", 0)

    # noinspection PyRedundantParentheses
    def build_mash_driver(self):
        """ Build a mash system that make joints run around the belt curve """
        cmds.select(clear=True)
        mash_network = mapi.Network()
        mash_network.createNetwork(name=f"{BeltRigBuilder.MASH_NETWORK_NAME}#")
        mash_network.setPointCount(self.tread_count)

        distribute_node_name = ""
        for node_name in mash_network.getAllNodesInNetwork():
            if "Distribute" in node_name:
                distribute_node_name = node_name
                break

        cmds.setAttr(f"{distribute_node_name}.amplitudeX", 0)

        curve_node = mash_network.addNode("MASH_Curve")
        cmds.connectAttr(f"{self.belt_ctrl.name}.worldSpace[0]", f"{curve_node.name}.inCurves[0]", force=1)
        cmds.setAttr(f"{curve_node.name}.timeStep", 1)
        cmds.setAttr(f"{curve_node.name}.timeSlide", -self.acceleration)

        breakout_node = mash_network.addNode("MASH_Breakout")
        self._create_tread_joints()
        for i, joint in enumerate(self.tread_joints):
            for connection_a, connection_b in BeltRigBuilder.MASH_BREAKOUT_CONNECTION_BLUEPRINT:
                cmds.connectAttr((f"{breakout_node.name}{connection_a}").format(i=i), f"{joint}{connection_b}")

    def copy_thread_mesh(self):
        threads = []
        if self.tread_mesh:
            for joint in self.tread_joints:
                new_thread = cmds.duplicate(self.tread_mesh, renameChildren=True)[0]
                threads.append(new_thread)
                cmds.matchTransform(new_thread, joint, scale=False)
                cmds.select(new_thread, joint)
                cmds.skinCluster(new_thread, joint, tsb=True)
        cmds.group(*threads, name=BeltRigBuilder.THREAD_MESH_GROUP_NAME)

    def clean_controls(self):
        cmds.parent(*self.circle_ctrls, self.belt_ctrl.name, w=True)
        cmds.delete(self.frame_ctrl)
        cmds.parent(*self.circle_ctrls, self.belt_ctrl.name)
        cmds.parent(self.belt_ctrl.name, self.core_ctrl)
        cmds.parentConstraint(self.core_ctrl, self.master_joint)

    def upgrade_controls(self):
        cmds.select(self.core_ctrl)
        cmds.addAttr(shortName='ac', longName='acceleration', defaultValue=self.acceleration, minValue=0.001, maxValue=10000)
        cmds.addAttr(shortName='to', longName='torque', defaultValue=self.torque, minValue=0.001, maxValue=10000)

        cmds.select(self.belt_ctrl.name)
        cmds.addAttr(shortName='dir', longName='direction', defaultValue=int(self.is_left), minValue=0, maxValue=1)

    def finish(self):
        self.build_belt_ctrl()
        self.build_mash_driver()
        self.copy_thread_mesh()
        self.clean_controls()
        self.upgrade_controls()


belt_rig_tool = BeltRigBuilder()
window = Window(None, belt_rig_tool)
window.open_window()

