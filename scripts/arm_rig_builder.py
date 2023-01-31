from maya import cmds, mel
from scripts.tuning_panel_widget import toggle, text_field, slider, dropdown


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
            "Arrow": ArrowCtrlBuilder(),
            "FourDArrow": FourDArrowCtrlBuilder(),
            "TwoDArrow": TwoDArrowCtrlBuilder(),
            "Plus": PlusCtrlBuilder(),
            "Circle": CircleCtrlBuilder(),
            "Square": SquareCtrlBuilder()
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


class ControllerBuilder:
    def __init__(self, ctrlName="Ctrl_Arm", ctrlScale=0.5):
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
                   p=[(-1, 0, -1), (-1, 0, -3), (-2, 0, -3), (0, 0, -5), (2, 0, -3), (1, 0, -3), (1, 0, -3), (1, 0, -1),
                      (3, 0, -1), (3, 0, -2), (5, 0, 0), (3, 0, 2), (3, 0, 1), (1, 0, 1), (1, 0, 3),
                      (2, 0, 3), (0, 0, 5), (-2, 0, 3), (-1, 0, 3), (-1, 0, 1), (-3, 0, 1), (-3, 0, 2), (-5, 0, 0),
                      (-3, 0, -2), (-3, 0, -1), (-1, 0, -1)])
        cmds.scale(self.ctrlScale, self.ctrlScale, self.ctrlScale)
        cmds.CenterPivot()


class TwoDArrowCtrlBuilder(ControllerBuilder):
    def __init__(self):
        super().__init__()

    def build(self):
        cmds.curve(n=self.ctrlName, d=1,
                   p=[(-3, 0, -1), (3, 0, -1), (3, 0, -2), (5, 0, 0), (3, 0, 2), (3, 0, 1), (-3, 0, 1), (-3, 0, 2),
                      (-5, 0, 0), (-3, 0, -2), (-3, 0, -1)])
        cmds.scale(self.ctrlScale, self.ctrlScale, self.ctrlScale)
        cmds.CenterPivot()


class PlusCtrlBuilder(ControllerBuilder):
    def __init__(self):
        super().__init__()

    def build(self):
        plusShapeCtrl = mel.eval("curve -d 1 -p -1 0 -1 -p -1 0 -3 -p 1 0 -3 -p 1 0 -1 -p 3 0 -1 -p 3 0 1 -p 1 0 1 -p 1 0 3 -p -1 0 3 -p -1 0 1 -p -3 0 1 -p -3 0 -1 -p -1 0 -1 -k 0 -k 1 -k 2 -k 3 -k 4 -k 5 -k 6 -k 7 -k 8 -k 9 -k 10 -k 11 -k 12 ;")
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
