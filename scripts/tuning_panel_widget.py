# noinspection PyProtectedMember
from typing import TypeVar, Annotated, _AnnotatedAlias
from maya import cmds
from enum import Enum


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
