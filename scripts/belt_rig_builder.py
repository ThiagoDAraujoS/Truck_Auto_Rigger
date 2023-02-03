from maya import cmds, mel
from maya.api.OpenMaya import MVector
import math


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


class BeltPathPart:
    """ Simple struct containing necessary curve path elements to build a curve piece """
    def __init__(self, circle):
        self.circle = circle
        self.arc: Arc = Arc(circle)
        # noinspection PyTypeChecker
        self.tangent: TangentLine = None

    def __iter__(self):
        yield self.arc
        yield self.tangent


class BeltRigBuilder:
    LOCATOR_GROUP_NAME: str = "belt_handles_group"
    LOCATOR_SPACING: float = 50
    LOCATOR_SIZE: float = 15

    def __init__(self):
        self.circle_count: int = 0
        self.circles: list[Circle] = []
        self.locators: list[str] = []
        self.locator_group: str = ""
        self.curve_centroid: MVector = MVector.kZeroVector

    def generate_shapes(self):
        self.locators = []
        for i in range(self.circle_count):
            self.locators.append(cmds.circle()[0])
            cmds.move(*(MVector.kXaxisVector * i * BeltRigBuilder.LOCATOR_SPACING))
            cmds.scale(BeltRigBuilder.LOCATOR_SIZE, BeltRigBuilder.LOCATOR_SIZE, 0.0)
        self.locator_group = cmds.group(self.locators, name=BeltRigBuilder.LOCATOR_GROUP_NAME)

    def build_belt_path(self) -> list[BeltPathPart]:
        # This function aims to return a data structure containing the information required to build the belt curve
        path: list[BeltPathPart] = []

        # Remove controls from the parent object
        cmds.parent(self.locators, w=True, r=True)

        # List containing all locators as circle objects
        self.circles = [Circle(name=shape_name) for shape_name in self.locators]

        starting_node = None
        current_node = min(self.circles, key=lambda o: o.center.x)
        guide_direction = MVector(0, 1, 0)

        path.append(BeltPathPart(current_node))

        # While we're not back at the starting node
        while starting_node != current_node:

            # If this is the first iteration, set starting node as the next node
            if not starting_node:
                starting_node = current_node

            # Find the external tangent from next_node to the segway_node
            tangent, next_node = current_node.find_external_tangent_in_system(guide_direction, self.circles)

            # Setup guide direction from tangent
            guide_direction = tangent.direction

            path[-1].arc.extrapolate_end_point(tangent.normal)
            path[-1].tangent = tangent

            path.append(BeltPathPart(next_node))
            path[-1].arc.extrapolate_start_point(tangent.normal)

            # set up current node to be this iteration next_node
            current_node = next_node

        # Wrap the belt's last node back to the first one
        path[0].arc.start = path.pop().arc.start

        # return the controls back to the parent
        cmds.parent(self.locators, self.locator_group, r=True)

        return path

    def trace_curve(self, full_path: list[BeltPathPart]):
        shapes = []
        for i, path in enumerate(full_path):
            for j, sub_path in enumerate(path):
                new_curve = sub_path.trace_path(f"part_{i * 2 + j}")
                if new_curve:
                    shapes.append(new_curve)
        cmds.attachCurve(*shapes)
        print(shapes)

    def build_curve(self):
        path = self.build_belt_path()
        self.trace_curve(path)


tool = BeltRigBuilder()
tool.circle_count = 5
tool.generate_shapes()
