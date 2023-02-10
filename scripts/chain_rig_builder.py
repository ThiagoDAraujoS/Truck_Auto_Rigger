from maya import cmds
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

    def __init__(self, arm_rigging_tool_ref = None, belt_rigging_tool_ref = None, chain_tool_ref = None):
        # Get a reference to the arm rigging tool
        self.bucket_tool_ref = arm_rigging_tool_ref
        self.belt_tool_ref = belt_rigging_tool_ref
        self.chain_tool_ref = chain_tool_ref

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
        # bucket_tab_element = self.assemble_abstract_tab(self.bucket_tool_ref, self.arm_control_box_widget)
        chain_tab_element = self.assemble_abstract_tab(self.chain_tool_ref, self.chain_control_box_widget)

        # Attach tabs to the tab element
        cmds.tabLayout(tabs_element, edit=True, tabLabel=(chain_tab_element, "Belt"))

        # Show the window
        cmds.showWindow(window_element)
        return window_element

    def chain_control_box_widget(self, print_message, show_icon, enable_tuning_panel):
        """ Creates a custom 'chain rigger widget' that serves as control for other widgets' features """

        def on_has_mesh(*_):
            print("has mesh")
            self.chain_tool_ref.duplicate_mesh()

        def on_has_curve(*_):
            print("has curve")
            self.chain_tool_ref.build_curve()
            self.chain_tool_ref.get_mesh_input(on_success=on_has_mesh, on_error=lambda name, *_: print_message(f" - Chain Ring '{name}' mesh not found"))

        def on_kickstart_tool(*_):
            print("tool started")
            self.chain_tool_ref.get_curve_input(on_success=on_has_curve, on_error=lambda name, *_: print_message(f" - Curve '{name}' Reference not found"))

        root_element = cmds.columnLayout(bgc=Window.UI_LIGHT_GRAY, columnAttach=('both', 0), adjustableColumn=True)
        print_message(" - Write your curve and mesh name in the UI then press Start rig button.")
        cmds.button(label="Start Building Rig", c=on_kickstart_tool, h=127, bgc=Window.UI_GREEN)

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
        def on_update(value, *_):
            setattr(*bind, value)

        root_element = cmds.rowLayout(numberOfColumns=2, adjustableColumn2=2, columnWidth2=(self.label_size, 70),
            columnAlign2=["right", "left"], columnAttach2=["both", "right"])

        cmds.text(label=f"{label}:", align="right", font="boldLabelFont")
        cmds.textField(text=default, rfc=on_update, cc=on_update)
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


class CurveRig:
    curve_name: text_field("Target Curve", "References") = ""  # textFieldButtonGrp
    """ Selected curve name """

    mesh_name: text_field("Ring Mesh", "References") = ""  # textFieldButtonGrp
    """ Selected copy mesh name """

    curve_points_count: slider("Resolution", "Curve Settings", 2, 100)[int] = 4  # intSliderGrp
    """ Curve points count"""

    keep_original_curve: toggle("Keep Curve", "Curve Settings") = True  # radioButtonGrp
    """ Keep original curve """

    locator_name: text_field("Locator", "Naming Suffix") = "Curve_Locator"  # textFieldButtonGrp
    """ Locator suffix name """

    locator_group_name: text_field("Locator Group", "Naming Suffix") = "Curve_Locator_Group"  # textFieldButtonGrp
    """ Locator group suffix name """

    mesh_group_name: text_field("Mesh Group", "Naming Suffix") = "Chain_Mesh_Group"  # textFieldButtonGrp
    """ Locator group suffix name """

    smooth_intensity: slider("Smooth", "Curve Settings", 0, 5)[int] = 1  # intSliderGrp
    """ Curve Smooth intensity """

    def __init__(self):
        self.locator_group = ""
        """ Locator group mobject name reference """

        self.locator_list = []
        """ Locator mobject names reference list"""

    def _get_abstract_input(self, type_name, default_name, on_error, on_success):
        """ Check if referred name exists and is of the chosen type, if not check for the selected mobject """
        # if the mobject name exists
        if default_name:
            shape = cmds.listRelatives(default_name, shapes=True)[0]
            if cmds.objectType(shape, isType=type_name):
                if on_success:
                    on_success()
                return default_name

        # get the selected object
        new_selected_object = cmds.ls(sl=True, o=True)
        new_selected_object_shape = []

        if new_selected_object:
            new_selected_object = new_selected_object[0]
            new_selected_object_shape = cmds.ls(sl=True, s=True, dag=True)[0]

        if not new_selected_object or not cmds.objectType(new_selected_object_shape, isType=type_name):
            if on_error:
                on_error(new_selected_object)
        else:
            if on_success:
                on_success()
            return new_selected_object

    def get_mesh_input(self, on_success = None, on_error = None):
        self.mesh_name = self._get_abstract_input("mesh", self.mesh_name, on_error=on_error, on_success=on_success)

    def get_curve_input(self, on_success = None, on_error = None):
        self.curve_name = self._get_abstract_input("nurbsCurve", self.curve_name, on_error=on_error, on_success=on_success)

    def resample_curve(self):
        """ Resample curve """
        new_curve = cmds.rebuildCurve(self.curve_name, rpo=not self.keep_original_curve, s=self.curve_points_count, kep=True, rt=0, d=3, ch=False, n=f"{self.curve_name}_Rebuilt")[0]

        if self.keep_original_curve:
            cmds.delete(self.curve_name)

        self.curve_name = new_curve

    def create_locators(self):
        """ Create locators """
        self.clear_locator_group()

        curve_point_names = cmds.ls(self.curve_name + ".ep[*]", fl=True)
        self.locator_list = []
        for point_name in curve_point_names:
            cmds.select(point_name, r=True)
            cmds.pointCurveConstraint()
            cmds.CenterPivot()
            self.locator_list.append(cmds.rename(f"{self.locator_name}#"))
        cmds.select(self.locator_list)
        self.locator_group = cmds.group(n=f"{self.locator_name}_{self.locator_group_name}")

    def clear_locator_group(self):
        """ Delete all the locators in the locator group """
        if cmds.objExists(self.locator_group):
            cmds.delete(self.locator_group)
            self.locator_group = []
            self.locator_name = ""

    def smooth_curve(self):
        """ Smooth the curve """
        cmds.smoothCurve(self.curve_name + ".cv[*]", s=self.smooth_intensity, ch=False)

    def duplicate_mesh(self):
        """ Replicate chain's mesh """
        print(self.mesh_name)
        mesh = []
        for locator_name in self.locator_list:
            cmds.select(self.mesh_name)
            mesh.append(cmds.duplicate()[0])
            cmds.select(locator_name, add=True)
            cmds.matchTransform()
            cmds.parentConstraint(w=1)
        cmds.group(mesh, name=self.mesh_group_name)

    def build_curve(self):
        self.resample_curve()
        if self.smooth_intensity > 0:
            self.smooth_curve()
        self.create_locators()


tool = CurveRig()
window = Window(chain_tool_ref=tool)
window.open_window()
