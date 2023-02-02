from maya import cmds
from maya.api.OpenMaya import MVector
import math


class BeltRigBuilder:
    LOCATOR_GROUP_NAME: str = "belt_handles_group"
    LOCATOR_SPACING: float = 50
    LOCATOR_SIZE: float = 15

    def __init__(self):
        self.circle_count: int = 0
        self.circles: list[Circle] = []
        self.locators: list[str] = []
        self.locator_group: str = ""

    def generate_shapes(self):
        self.locators = []
        for i in range(self.circle_count):
            self.locators.append(cmds.circle()[0])
            cmds.move(*(MVector.kXaxisVector * i * BeltRigBuilder.LOCATOR_SPACING))
            cmds.scale(BeltRigBuilder.LOCATOR_SIZE, BeltRigBuilder.LOCATOR_SIZE, 0.0)
        self.locator_group = cmds.group(self.locators, name=BeltRigBuilder.LOCATOR_GROUP_NAME)

    def build_curve(self):
        # Remove controls from the parent object
        cmds.parent(self.locators, w=True, r=True)

        # List containing all locators as circle objects
        self.circles = [Circle(name=shape_name) for shape_name in self.locators]

        # Initialize algorithm variables
        # List containing all tangents
        tangential_path = []

        # Slice_curves, these curves are going to be used to slice the circles in order to build the arcs that connect the tangents
        slice_curves:dict[Circle, SliceCurve] = {circle: SliceCurve(circle) for circle in self.circles}

        # List containing all the unvisited nodes
        unvisited_nodes = self.circles.copy()

        starting_node = None
        next_node = min(unvisited_nodes, key=lambda o: o.center.x)
        guide_direction = MVector(0, 1, 0)

        # While we're not back at the starting node
        while starting_node != next_node:

            # If this is the first iteration, set starting node as the next node
            if not starting_node:
                starting_node = next_node

            # Find the external tangent from next_node to the segway_node
            tangent, segway_node = next_node.find_external_tangent_in_system(guide_direction, unvisited_nodes)

            # Setup guide direction from tangent
            guide_direction = tangent.direction

            # remove the next node from the unvisited nodes list
            unvisited_nodes.remove(segway_node)

            slice_curves[next_node].extrapolate_end_point(tangent.direction)
            slice_curves[segway_node].extrapolate_start_point(tangent.direction)

            # set up next node to be this iteration segway_node
            next_node = segway_node

            # Append the tangent to the tangential path list
            tangential_path.append(tangent)

        for c, s in slice_curves.items():
            s.build_slicer_curve()

        for t in tangential_path:
            t.build_tangent_line()



class SliceCurve:
    EXTRAPOLATION_FACTOR: float = 1.001

    def __init__(self, circle_ref):
        self.circle = circle_ref
        self.start:  MVector = MVector.kZeroVector
        self.end:    MVector = MVector.kZeroVector

    def _extrapolate_direction(self, direction) -> MVector:
        return (direction * (self.circle.radius * SliceCurve.EXTRAPOLATION_FACTOR)) + self.circle.center

    def extrapolate_start_point(self, direction) -> None: self.start = self._extrapolate_direction(direction)
    def extrapolate_end_point(self, direction)   -> None: self.end = self._extrapolate_direction(direction)

    def build_slicer_curve(self):
        return cmds.curve(p=[
            self.start,
            (self.circle.center + self.start) * 0.5,
            self.circle.center,
            (self.circle.center + self.end) * 0.5,
            self.end])


class TangentLine:
    def __init__(self, circle_a, circle_b):
        direction = circle_a.find_positive_external_tangent_direction(circle_b)

        self.a = direction * circle_a.radius + circle_a.center
        self.b = direction * circle_b.radius + circle_b.center

        base = self.b - self.a

        self.direction = base.normal()
        self.length = base.length()

    def build_tangent_line(self):
        return cmds.curve(p=[(self.direction * (self.length * 0.25 * i)) + self.a for i in range(5)])


class Circle:
    def __init__(self, center: MVector = MVector.kZeroVector, radius: float = 1.0, name=""):
        if name:
            self.load_transform_data(name)
        else:
            self.center: MVector = center
            self.radius: float = radius
            self.name = ""

    def load_transform_data(self, name):
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
        return Circle(self.center, abs(self.radius - other.radius + 0.0001))

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

    def find_positive_external_tangent_direction(self, other) -> MVector:
        is_forward = self.radius > other.radius
        main_circle, target_circle = (self, other) if is_forward else (other, self)

        bisector   = main_circle.create_bisector_circle(target_circle)
        difference = main_circle.create_difference_circle(target_circle)
        pos, neg   = bisector.find_intersection(difference)

        return ((pos if is_forward else neg) - main_circle.center).normal()

        #main_tangent_intersection   = CircleIntersection(main_circle,   intersection_direction)
        #target_tangent_intersection = CircleIntersection(target_circle, intersection_direction)

        ## debug notes
        #cmds.spaceLocator()
        #cmds.move(*main_tangent_intersection.extrapolation)
        #cmds.spaceLocator()
        #cmds.move(*target_tangent_intersection.extrapolation)
        #bisector.build_widget()
        #difference.build_widget()
        #return pos, neg

    def build_widget(self, name=""):
        if name:
            self.name = cmds.circle(c=self.center, r=self.radius, nr=(0, 0, 1), name=name)
        else:
            self.name = cmds.circle(c=self.center, r=self.radius, nr=(0, 0, 1))


tool = BeltRigBuilder()
tool.circle_count = 5
tool.generate_shapes()
