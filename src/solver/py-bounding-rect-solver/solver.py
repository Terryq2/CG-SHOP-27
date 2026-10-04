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
    cutter = Rectangle.enclosing(
        instance.cutter.x, instance.cutter.y, instance.cutter_center
    )

    x_start, x_end = lawn.left - cutter.right, lawn.right - cutter.left

    y_start, y_end = lawn.top - cutter.bottom, lawn.bottom - cutter.top

    rows_strip_count = max(
        ceil(lawn.height / cutter.height), instance.number_of_cutters
    )
    columns_strip_count = max(
        ceil(lawn.width / cutter.width), instance.number_of_cutters
    )

    anchor_rows = [
        lawn.top - cutter.top - i * cutter.height for i in range(rows_strip_count)
    ]
    anchor_columns = [
        lawn.left - cutter.left + i * cutter.width for i in range(columns_strip_count)
    ]

    tours = _tour(anchor_rows, x_start, x_end, anchor_columns, y_start, y_end, instance.number_of_cutters, cutter.height, cutter.width)

    return CGSHOP2027Solution(
        instance_uid=instance.instance_uid,
        tours=tours,
        meta={"algorithm": "bounding-rect strips"},
    )
    # This the largest number of rows and columns that any cutter will be assigned to.


def _tour_horizontal(anchor_rows: list[int], x_start: int, x_end: int) -> CutterTour:
    """It computes a tour of the anchor_rows in a zig-zag manner. For example, if
    anchor row has size 5 and the difference between x_start and x_end is 5, then our tour traverses the rows
    in the following manner
        1/12***2/11
        4***3
        5***6
        8***7
        9***10
    where the number indicates the ith check point. We assume for simplicity, 1 * 1 mower.
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
        check_points.extend(
            [(x_start, y), (x_end, y)] if _is_even(i) else [(x_end, y), (x_start, y)]
        )

    first_x, first_y = check_points[0]
    last_x, last_y = check_points[-1]

    if last_x != first_x and last_y != first_y:
        check_points.append((last_x, first_y))

    return CutterTour(x=[x for x, _ in check_points], y=[y for _, y in check_points])


def _tour_vertical(anchor_cols: list[int], y_start: int, y_end: int) -> CutterTour:
    """The same as tour_horizontal except that we sweep columns"""
    check_points = []

    for i, x in enumerate(anchor_cols):
        check_points.extend(
            [(x, y_start), (x, y_end)] if _is_even(i) else [(x, y_end), (x, y_start)]
        )

    first_x, first_y = check_points[0]
    last_x, last_y = check_points[-1]

    if last_x != first_x and last_y != first_y:
        check_points.append((first_x, last_y))

    return CutterTour(x=[x for x, _ in check_points], y=[y for _, y in check_points])


def _horizontal_more_optimal_than_vertical(
    max_cutter_rows: int,
    max_cutter_columns: int,
    x_bounds: tuple[int, int],
    y_bounds: tuple[int, int],
    cutter_height,
    cutter_width,
):
    """This function computes whether sweeping horizontally takes less move than sweeping vertically

    Args:
        max_cutter_rows: the maximum number of rows that a cutter can be assigned to,
        max_cutter_columns: the maximum number of columns that a cutter can be assigned to,,
        x_bounds: tuple of (x_start, x_end)
        y_bounds: tuple of (y_start, y_end)
        cutter_height: height of the cutter
        cutter_width: width of the cutter
    Returns:
        true if horizontal sweeps takes less moves than vertical sweeps.
    """
    x_start, x_end = x_bounds
    y_start, y_end = y_bounds

    horizontal_sweep_distance = abs(x_end - x_start)
    vertical_sweep_distance = abs(y_end - y_start)

    # First half of the sum:
    # Need to sweep over a total of max_cutter_rows, then if max_cutter_rows is odd
    # we will arrive, owing to our zigzag pattern, at a different column as our starting column.
    # To get back to our original column we would need to travese an additional horizontal_sweep_distance.

    # Second half of the sum
    # Moreover, to arrive at the next row we need to move downwards by cutter_height. We need to do this 2 times, since we
    # also need to get back from the last row.
    length_of_tour_horizontal = (
        horizontal_sweep_distance * (max_cutter_rows + max_cutter_rows % 2)
    ) + (2 * (max_cutter_rows - 1) * cutter_height)

    length_of_tour_vertical = (
        vertical_sweep_distance * (max_cutter_columns + max_cutter_columns % 2)
        + 2 * (max_cutter_columns - 1) * cutter_width
    )

    print(length_of_tour_horizontal, length_of_tour_vertical)

    return length_of_tour_horizontal > length_of_tour_vertical


def _tour(
    anchor_rows: list[int],
    x_start: int,
    x_end: int,
    anchor_columns: list[int],
    y_start: int,
    y_end: int,
    number_of_cutters: int,
    cutter_height: int,
    cutter_width: int,
):
    max_cutter_rows = ceil(len(anchor_rows) / number_of_cutters)
    max_cutter_columns = ceil(len(anchor_columns) / number_of_cutters)

    match _horizontal_more_optimal_than_vertical(
        max_cutter_rows,
        max_cutter_columns,
        (x_start, x_end),
        (y_start, y_end),
        cutter_height,
        cutter_width,
    ):
        case True:
            tours_horizontal = []
            for block in divide(number_of_cutters, anchor_rows):
                tours_horizontal.append(_tour_horizontal(list(block), x_start, x_end))
            return tours_horizontal
        case False:
            tours_vertical = []
            for block in divide(number_of_cutters, anchor_columns):
                tours_vertical.append(_tour_vertical(list(block), y_start, y_end))
            return tours_vertical


def _is_even(number: int):
    return (number & 1) == 0
