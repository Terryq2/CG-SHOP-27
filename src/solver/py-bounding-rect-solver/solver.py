from math import ceil
from typing import NamedTuple, Self

from more_itertools import divide, flatten, unique_justseen

from cgshop2027_pyutils.schemas import (
    CGSHOP2027Instance,
    CGSHOP2027Solution,
    CutterTour,
)

class Rectangle(NamedTuple):
    left: int
    bottom: int
    right: int
    top: int

    @property
    def height(self) -> int:
        return self.top - self.bottom + 1

    @property
    def width(self) -> int:
        return self.right - self.left + 1

    @classmethod
    def enclosing(cls, xs: list[int], ys: list[int], offset=(0, 0)) -> Self:
        """This computes a rectangular shape that covers xs and ys by aligning the four sides
        of the rectangle: left side, right side, bottom side and up side to the minimum of the xs,
        the maximum of the xs, the minimum of the ys, the maximum of the ys respectively.

        Args:
            xs: the list of x coordinates
            ys: the list of y coordinates
        Returns:
            A rectangle object that covers xs and ys
        """
        offset_x, offset_y = offset
        return cls(
            min(xs) - offset_x,
            min(ys) - offset_y,
            max(xs) - 1 - offset_x,
            max(ys) - 1 - offset_y,
        )


def solve(instance: CGSHOP2027Instance) -> CGSHOP2027Solution:
    """Solves an instance of the problem by solving instead an auxillary rectangular 
    cover of the instance. Any solution to that auxillary rectangular cover 
    necessarily covers the instance itself.

    Args:
        instance: polyomino lawn with holes possibly.
    Returns:
        A solution to an rectangular cover of instance.
    """
    boundary = instance.region_to_cover.outer_boundary
    lawn = Rectangle.enclosing(boundary.x, boundary.y)
    cutter = Rectangle.enclosing(instance.cutter.x, instance.cutter.y, instance.cutter_center)

    x_start, x_end = lawn.left - cutter.right, lawn.right - cutter.left
    strip_count = max(ceil(lawn.height / cutter.height), instance.number_of_cutters)
    anchor_rows = [lawn.top - cutter.top - i * cutter.height for i in range(strip_count)]

    tours = []
    for block in divide(instance.number_of_cutters, anchor_rows):
        tours.append(tour(list(block), x_start, x_end))

    return CGSHOP2027Solution(
        instance_uid=instance.instance_uid,
        tours=tours,
        meta={"algorithm": "bounding-rect strips"},
    )


def tour(anchor_rows: list[int], x_start: int, x_end: int) -> CutterTour:
    """It computes a tour of the anchor_rows in a zig-zag manner. For example, if 
    anchor row has size 5 and the difference between x_start and x_end is 5, then our tour traverses the rows
    in the following manner
        1/12***2/11
        4***3
        5***6
        8***7
        9***10
    where the number indicates the ith check point. 
    We return to the start of the first row from 10 via 11 and 12.

    Args:
        anchor_rows: the rows we need to traverse given that they are consecutive rows
        x_start: the horizontal start point of our traversal
        x_end: the horizontal end point of our traversal
    Returns:
        A CutterTour object that specifies our tour in the required format.
    """
    check_points = []

    for i, y in enumerate(anchor_rows):
        if _is_even(i):
            check_points.extend([(x_start, y), (x_end, y)])
        else:
            check_points.extend([(x_end, y), (x_start, y)])

    first_x, first_y = check_points[0]
    last_x, last_y = check_points[-1]

    if last_x != first_x and last_y != first_y:
        check_points.append((last_x, first_y))

    return CutterTour(x=[x for x, _ in check_points], y=[y for _, y in check_points])


def _is_even(number: int):
    return (number & 1) == 0
