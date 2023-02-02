from maya import cmds
from maya.api.OpenMaya import MVector, MEulerRotation, MQuaternion, MAngle
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
        tangential_path = []

        cmds.parent(self.locators, w=True, r=True)
        self.circles = [Circle(name=shape_name) for shape_name in self.locators]
        unvisited_nodes = self.circles.copy()

        slice_curves = {circle: SliceCurve(circle) for circle in self.circles}

        def find_tangent(circle, start_direction: MVector):
            angle = math.inf
            closest_tangent = None
            segway = None
            print(unvisited_nodes)
            for node in unvisited_nodes:
                if circle != node:
                    tangent = TangentLine(circle, node)
                    new_angle = start_direction.angle(tangent.direction)
                    if new_angle < angle:
                        angle = new_angle
                        closest_tangent = tangent
                        segway = node

            return closest_tangent, segway

        starting_node = None
        next_node = unvisited_nodes[0]
        guide_direction = MVector(0, 1, 0)

        while starting_node != next_node:
            if not starting_node:
                starting_node = next_node

            tangent, segway_node = find_tangent(next_node, guide_direction)
            guide_direction = tangent.direction
            unvisited_nodes.remove(segway_node)
            next_node = segway_node
            tangential_path.append(tangent)


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

    def extrapolate_start_point(self, direction) -> None: self.start = MVector.kZeroVector = self._extrapolate_direction(direction)
    def extrapolate_end_point(self, direction)   -> None: self.end = MVector.kZeroVector   = self._extrapolate_direction(direction)

    def build_slicer_curve(self):
        pass


class TangentLine:
    def __init__(self, circle_a, circle_b):
        direction = circle_a.find_positive_external_tangent_direction(circle_b)

        self.a = direction * circle_a.radius + circle_a.center
        self.b = direction * circle_b.radius + circle_b.center

        base = self.b - self.a

        self.direction = base.normal()
        self.length = base.length()

    def build_tangent_line(self):
        cmds.curve(p=[(self.direction * (self.length * 0.25 * i)) + self.a for i in range(5)])


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



#c_1 = Circle(center=MVector(0, 0, 0), radius=10)
#c_1.build_widget("Circle_A")
#c_2 = Circle(center=MVector(0, 80, 40), radius=30)
#c_2.build_widget("Circle_B")
#
## for p in c_2.intersection(c_1):
##    cmds.spaceLocator(p=p)
#
## Build bisector circle
#bisector = c_1.create_bisector_circle(c_2)
#bisector.build_widget("Bisector")
#
## Build difference circle
#difference = c_1.create_difference_circle(c_2)
#difference.build_widget("Difference")
#
## Find intersection between circle1 and bisector circle
#p1, p2 = difference.find_intersection(bisector)
#cmds.spaceLocator(p=p1)
#cmds.spaceLocator(p=p2)
#
## Project the c_1 difference intersections
#d1, d2 = c_1.project_to_perimeter(position=p1), c_1.project_to_perimeter(position=p2)
#
#j1_1, j2_1 = d1 + c_1.center,  d2 + c_1.center
#cmds.spaceLocator(p=j1_1)
#cmds.spaceLocator(p=j2_1)

## Project the c_1 difference intersections
#d3, d4 = c_2.project_to_perimeter(direction=d1), c_2.project_to_perimeter(direction=d2)
#j1_2, j2_2 = d3 + c_2.center,  d4 + c_2.center
#cmds.spaceLocator(p=j1_2)
#cmds.spaceLocator(p=j2_2)


#j1_2, j2_2 = c_2.project_to_perimeter(direction=j1_1) + c_2.center, c_2.project_to_perimeter(direction=j2_1) + c_2.center


# cmds.spaceLocator(p=j1_2)
# cmds.spaceLocator(p=j2_2)
