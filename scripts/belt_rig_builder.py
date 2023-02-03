from maya import cmds
from maya.api.OpenMaya import MVector
import math
import MASH.api as mapi


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

    _BELT_CURVE_NAME: str = "Belt_Curve"

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

    def __init__(self, locator_group, name: str = ""):
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
        name = name if name else BeltCurve._BELT_CURVE_NAME
        cmds.rename(result, name)
        return name


class BeltRigBuilder:
    CORE_CTRL_SIZE: float = 20
    CORE_CTRL_NAME: str = "Belt_Core_Ctrl"

    CIRCLE_CTRL_SPACING: float = 50
    CIRCLE_CTRL_SIZE: float = 15
    CIRCLE_CTRL_LOCK_BLUEPRINT: list[str] = "rotate", "translateZ", "scaleZ", "visibility",
    CIRCLE_CTRL_NAME: str = "Belt_Circle_Ctrl"

    FRAME_CTRL_NAME: str = "Belt_Frame_Ctrl"
    FRAME_CTRL_SIZE: float = 80.0
    FRAME_CTRL_LOCK_BLUEPRINT: list[str] = "scale", "rotate", "translate"

    THREAD_JOINT_NAME_PREFIX: str = "Belt_Thread"
    MASTER_JOINT_NAME_PREFIX: str = "Belt_Master"
    JOINT_NAME_SUFFIX: str = "Joint"

    MASH_NETWORK_NAME: str = "MASH_Belt_Thread_Driver"
    MASH_BREAKOUT_CONNECTION_BLUEPRINT: list[tuple[str, str]] = [(".outputs[{i}].translate", ".translate")]#, "outputs[{i}].rotate"

    def __init__(self):
        self.core_ctrl: str = ""
        self.tread_count: int = 30
        self.circle_ctrl_count: int = 0
        self.circle_controls: list[str] = []
        self.frame_ctrl: str = ""
        # noinspection PyTypeChecker
        self.belt_curve: BeltCurve = None
        self.master_joint: str = ""
        self.tread_joints: list[str] = []
        self.animation_speed = 3.0

    def start_building_frame_ctrl(self):
        """ Builds a square frame used as base screen for drawing the belt's controls """
        self.frame_ctrl = cmds.polyPlane(name=BeltRigBuilder.FRAME_CTRL_NAME, h=BeltRigBuilder.FRAME_CTRL_SIZE,
            w=BeltRigBuilder.FRAME_CTRL_SIZE, sh=1, sw=1, sx=1, sy=1, ax=MVector.kZaxisVector)[0]
        cmds.setAttr(f"{self.frame_ctrl}.overrideEnabled", 1)
        cmds.setAttr(f"{self.frame_ctrl}.overrideShading", 0)

        self.core_ctrl = cmds.polyCube(name=BeltRigBuilder.CORE_CTRL_NAME, h=BeltRigBuilder.CORE_CTRL_SIZE, w=BeltRigBuilder.CORE_CTRL_SIZE, d=BeltRigBuilder.CORE_CTRL_SIZE)[0]
        cmds.setAttr(f"{self.core_ctrl}.overrideEnabled", 1)
        cmds.setAttr(f"{self.core_ctrl}.overrideShading", 0)

    def finish_building_frame(self):
        cmds.makeIdentity(self.frame_ctrl, apply=True, s=1, n=0)
        for attribute in BeltRigBuilder.FRAME_CTRL_LOCK_BLUEPRINT:
            cmds.setAttr(f"{self.frame_ctrl}.{attribute}", lock=True)
        #cmds.setAttr(f"{self.frame_ctrl}.template", 1)

    def build_circle_ctrl(self):
        ctrl = cmds.circle(name=BeltRigBuilder.CIRCLE_CTRL_NAME)[0]
        cmds.scale(BeltRigBuilder.CIRCLE_CTRL_SIZE, BeltRigBuilder.CIRCLE_CTRL_SIZE, 0.0)
        for attribute in BeltRigBuilder.CIRCLE_CTRL_LOCK_BLUEPRINT:
            cmds.setAttr(f"{ctrl}.{attribute}", lock=True)
        return ctrl

    def generate_circle_ctrl_list(self):
        self.circle_controls = []
        for i in range(self.circle_ctrl_count):
            ctrl = self.build_circle_ctrl()
            cmds.move(*(MVector.kXaxisVector * i * BeltRigBuilder.CIRCLE_CTRL_SPACING))
            self.circle_controls.append(ctrl)
        cmds.parent(*self.circle_controls, self.frame_ctrl, r=True)

    def build_belt_curve(self): self.belt_curve = BeltCurve(self.frame_ctrl)

    def clear_circle_ctrls(self):
        cmds.parent(self.belt_curve.name, self.frame_ctrl, r=True)
        #cmds.parent(self.belt_curve.name, w=True)
        #cmds.delete(self.frame_ctrl)

    def create_tread_joints(self):
        position = cmds.getAttr(f"{self.core_ctrl}.translate")[0]
        self.master_joint = cmds.joint(name=f"{BeltRigBuilder.MASTER_JOINT_NAME_PREFIX}_{BeltRigBuilder.JOINT_NAME_SUFFIX}", p=position)

        self.tread_joints = []
        for i in range(self.tread_count):
            cmds.select(clear=True)
            joint_name = f"{BeltRigBuilder.THREAD_JOINT_NAME_PREFIX}_{i}_{BeltRigBuilder.JOINT_NAME_SUFFIX}"
            self.tread_joints.append(cmds.joint(name=joint_name))
            cmds.parent(self.tread_joints[i], self.master_joint)
            cmds.setAttr(f"{joint_name}.inheritsTransform", 0)

    # noinspection PyRedundantParentheses
    def build_mash_driver(self):
        cmds.select(clear=True)
        mash_network = mapi.Network()
        mash_network.createNetwork(name=BeltRigBuilder.MASH_NETWORK_NAME)
        mash_network.setPointCount(self.tread_count)

        distribute_node_name = ""
        for node_name in mash_network.getAllNodesInNetwork():
            if "Distribute" in node_name:
                distribute_node_name = node_name
                break

        cmds.setAttr(f"{distribute_node_name}.amplitudeX", 0)

        curve_node = mash_network.addNode("MASH_Curve")
        cmds.connectAttr(f"{self.belt_curve.name}.worldSpace[0]", f"{curve_node.name}.inCurves[0]", force=1)
        cmds.setAttr(f"{curve_node.name}.timeStep", 1)
        cmds.setAttr(f"{curve_node.name}.timeSlide", -self.animation_speed)

        breakout_node = mash_network.addNode("MASH_Breakout")
        self.create_tread_joints()
        for i, joint in enumerate(self.tread_joints):
            for connection_a, connection_b in BeltRigBuilder.MASH_BREAKOUT_CONNECTION_BLUEPRINT:
                cmds.connectAttr((f"{breakout_node.name}{connection_a}").format(i=i), f"{joint}{connection_b}")

    def finish(self):
        cmds.parent(self.master_joint, self.belt_curve.name, self.frame_ctrl, r=True)


tool = BeltRigBuilder()

tool.start_building_frame_ctrl()
tool.finish_building_frame()

tool.circle_ctrl_count = 5

tool.generate_circle_ctrl_list()
tool.build_belt_curve()
tool.clear_circle_ctrls()

tool.build_mash_driver()
