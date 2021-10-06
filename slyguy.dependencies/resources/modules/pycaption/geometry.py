"""
This module implements the classes used to represent positioning information.

CONVENTIONS:
* None of the methods should modify the state of the objects on which they're
  called. If the values of an object need to be recalculated, the method
  responsible for the recalculation should return a new object with the
  necessary modifications.
"""
import six

from .exceptions import RelativizationError

class Enum(object):
    """Generic class that's not easily instantiable, serving as a base for
    the enumeration classes
    """
    def __new__(cls, *args, **kwargs):
        raise Exception(u"Don't instantiate. Use like an enum")

    __init__ = __new__

class UnitEnum(Enum):
    """Enumeration-like object, specifying the units of measure for length

    Usage:
        unit = UnitEnum.PIXEL
        unit = UnitEnum.EM
        if unit == UnitEnum.CELL :
            ...
    """
    PIXEL = 'px'
    EM = 'em'
    PERCENT = '%'
    CELL = 'c'
    PT = 'pt'

class VerticalAlignmentEnum(Enum):
    """Enumeration object, specifying the allowed vertical alignment options

    Usage:
        alignment = VerticalAlignmentEnum.TOP
        if alignment == VerticalAlignmentEnum.BOTTOM:
            ...
    """
    TOP = 'top'
    CENTER = 'center'
    BOTTOM = 'bottom'


class HorizontalAlignmentEnum(Enum):
    """Enumeration object specifying the horizontal alignment preferences
    """
    LEFT = 'left'
    CENTER = 'center'
    RIGHT = 'right'
    START = 'start'
    END = 'end'


class Alignment(object):
    def __init__(self, horizontal, vertical):
        """
        :type horizontal: HorizontalAlignmentEnum
        :param horizontal: HorizontalAlignmentEnum member
        :type vertical: VerticalAlignmentEnum
        :param vertical: VerticalAlignmentEnum member
        """
        self.horizontal = horizontal
        self.vertical = vertical

    def __hash__(self):
        return hash(
            hash(self.horizontal) * 83 +
            hash(self.vertical) * 89 +
            97
        )

    def __eq__(self, other):
        return (
            other and
            type(self) == type(other) and
            self.horizontal == other.horizontal and
            self.vertical == other.vertical
        )

    def __repr__(self):
        return "<Alignment ({horizontal} {vertical})>".format(
            horizontal=self.horizontal, vertical=self.vertical
        )

    def serialized(self):
        """Returns a tuple of the useful information regarding this object
        """
        return self.horizontal, self.vertical

    @classmethod
    def from_horizontal_and_vertical_align(cls, text_align=None,
                                           display_align=None):
        horizontal_obj = None
        vertical_obj = None

        if text_align == 'left':
            horizontal_obj = HorizontalAlignmentEnum.LEFT
        if text_align == 'start':
            horizontal_obj = HorizontalAlignmentEnum.START
        if text_align == 'center':
            horizontal_obj = HorizontalAlignmentEnum.CENTER
        if text_align == 'right':
            horizontal_obj = HorizontalAlignmentEnum.RIGHT
        if text_align == 'end':
            horizontal_obj = HorizontalAlignmentEnum.END

        if display_align == 'before':
            vertical_obj = VerticalAlignmentEnum.TOP
        if display_align == 'center':
            vertical_obj = VerticalAlignmentEnum.CENTER
        if display_align == 'after':
            vertical_obj = VerticalAlignmentEnum.BOTTOM

        if not any([horizontal_obj, vertical_obj]):
            return None
        return cls(horizontal_obj, vertical_obj)


class TwoDimensionalObject(object):
    """Adds a couple useful methods to its subclasses, nothing fancy.
    """
    @classmethod
    # TODO - highly cachable. Should use WeakValueDictionary here to return
    # flyweights, not new objects.
    def from_xml_attribute(cls, attribute):
        """Instantiate the class from a value of the type "4px" or "5%"
        or any number concatenated with a measuring unit (member of UnitEnum)

        :type attribute: unicode
        """
        horizontal, vertical = six.text_type(attribute).split(' ')
        horizontal = Size.from_string(horizontal)
        vertical = Size.from_string(vertical)

        return cls(horizontal, vertical)


class Stretch(TwoDimensionalObject):
    """Used for specifying the extent of a rectangle (how much it stretches),
    or the padding in a rectangle (how much space should be left empty until
    text can be displayed)
    """
    def __init__(self, horizontal, vertical):
        """Use the .from_xxx methods. They know what's best for you.

        :type horizontal: Size
        :type vertical: Size
        """
        for parameter in [horizontal, vertical]:
            if not isinstance(parameter, Size):
                raise ValueError("Stretch must be initialized with two valid "
                                 "Size objects.")
        self.horizontal = horizontal
        self.vertical = vertical

    def is_measured_in(self, measure_unit):
        """Whether the stretch is only measured in the provided units

        :param measure_unit: a UnitEnum member
        :return: True/False
        """
        return (
            self.horizontal.unit == measure_unit and
            self.vertical.unit == measure_unit
        )

    def __repr__(self):
        return '<Stretch ({horizontal}, {vertical})>'.format(
            horizontal=self.horizontal, vertical=self.vertical
        )

    def serialized(self):
        """Returns a tuple of the useful attributes of this object"""
        return (
            None if not self.horizontal else self.horizontal.serialized(),
            None if not self.vertical else self.vertical.serialized()
        )

    def __eq__(self, other):
        return (
            other and
            type(self) == type(other) and
            self.horizontal == other.horizontal and
            self.vertical == other.vertical
        )

    def __hash__(self):
        return hash(
            hash(self.horizontal) * 59 +
            hash(self.vertical) * 61 +
            67
        )

    def __bool__(self):
        return True if self.horizontal or self.vertical else False

    def to_xml_attribute(self, **kwargs):
        """Returns a unicode representation of this object as an xml attribute
        """
        return '{horizontal} {vertical}'.format(
            horizontal=self.horizontal.to_xml_attribute(),
            vertical=self.vertical.to_xml_attribute()
        )

    def is_relative(self):
        """
        Returns True if all dimensions are expressed as percentages,
        False otherwise.
        """
        is_relative = True
        if self.horizontal:
            is_relative &= self.horizontal.is_relative()
        if self.vertical:
            is_relative &= self.vertical.is_relative()
        return is_relative

    def as_percentage_of(self, video_width, video_height):
        """
        Converts absolute units (e.g. px, pt etc) to percentage
        """
        return Stretch(
            self.horizontal.as_percentage_of(video_width=video_width),
            self.vertical.as_percentage_of(video_height=video_height)
        )


class Region(object):
    """Represents the spatial coordinates of a rectangle

    Don't instantiate by hand. use Region.from_points or Region.from_extent
    """
    @classmethod
    def from_points(cls, p1, p2):
        """Create a rectangle, knowing 2 points on the plane.
        We assume that p1 is in the upper left (closer to the origin)

        :param p1: Point instance
        :param p2: Point instance
        :return: a Point instance
        """
        inst = cls()
        inst._p1 = p1
        inst._p2 = p2
        return inst

    @classmethod
    def from_extent(cls, extent, origin):
        """Create a rectangle, knowing its upper left origin, and
        spatial extension

        :type extent: Stretch
        :type origin: Point
        :return: a Point instance
        """
        inst = cls()
        inst._extent = extent
        inst._origin = origin
        return inst

    @property
    def extent(self):
        """How wide this rectangle stretches (horizontally and vertically)
        """
        if hasattr(self, '_extent'):
            return self._extent
        else:
            return self._p1 - self._p2

    @property
    def origin(self):
        """Out of its 4 points, returns the one closest to the origin
        """
        if hasattr(self, '_origin'):
            return self._origin
        else:
            return Point.align_from_origin(self._p1, self._p2)[0]

    upper_left_point = origin

    @property
    def lower_right_point(self):
        """The point furthest from the origin from the rectangle's 4 points
        """
        if hasattr(self, '_p2'):
            return Point.align_from_origin(self._p1, self._p2)[1]
        else:
            return self.origin.add_extent(self.extent)

    def __eq__(self, other):
        return (
            other and
            type(self) == type(other) and
            self.extent == other.extent and
            self.origin == other.origin
        )

    def __hash__(self):
        return hash(
            hash(self.origin) * 71 +
            hash(self.extent) * 73 +
            79
        )


class Point(TwoDimensionalObject):
    """Represent a point in 2d space.
    """
    def __init__(self, x, y):
        """
        :type x: Size
        :type y: Size
        """
        for parameter in [x, y]:
            if not isinstance(parameter, Size):
                raise ValueError("Point must be initialized with two valid "
                                 "Size objects.")
        self.x = x
        self.y = y

    def __sub__(self, other):
        """Returns an Stretch object, if the other point's units are compatible
        """
        return Stretch(abs(self.x - other.x), abs(self.y - other.y))

    def add_stretch(self, stretch):
        """Returns another Point instance, whose coordinates are the sum of the
         current Point's, and the Stretch instance's.
        """
        return Point(self.x + stretch.horizontal, self.y + stretch.vertical)

    def is_relative(self):
        """
        Returns True if all dimensions are expressed as percentages,
        False otherwise.
        """
        is_relative = True
        if self.x:
            is_relative &= self.x.is_relative()
        if self.y:
            is_relative &= self.y.is_relative()
        return is_relative

    def as_percentage_of(self, video_width, video_height):
        """
        Converts absolute units (e.g. px, pt etc) to percentage
        """
        return Point(
            self.x.as_percentage_of(video_width=video_width),
            self.y.as_percentage_of(video_height=video_height)
        )

    @classmethod
    def align_from_origin(cls, p1, p2):
        """Returns a tuple of 2 points. The first is closest to the origin
        on both axes than the second.

        If the 2 points fulfill this condition, returns them (ordered), if not,
        creates 2 new points.
        """
        if p1.x <= p2.x and p1.y <= p2.y:
            return p1
        if p1.x >= p2.x and p1.y >= p2.y:
            return p2
        else:
            return (Point(min(p1.x, p2.x), min(p1.y, p2.y)),
                    Point(max(p1.x, p2.x), max(p1.y, p2.y)))

    def __repr__(self):
        return '<Point ({x}, {y})>'.format(
            x=self.x, y=self.y
        )

    def serialized(self):
        """Returns the "useful" values of this object.
        """
        return (
            None if not self.x else self.x.serialized(),
            None if not self.y else self.y.serialized()
        )

    def __eq__(self, other):
        return (
            other and
            type(self) == type(other) and
            self.x == other.x and
            self.y == other.y
        )

    def __hash__(self):
        return hash(
            hash(self.x) * 51 +
            hash(self.y) * 53 +
            57
        )

    def __bool__(self):
        return True if self.x or self.y else False

    def to_xml_attribute(self, **kwargs):
        """Returns a unicode representation of this object as an xml attribute
        """
        return '{x} {y}'.format(
            x=self.x.to_xml_attribute(), y=self.y.to_xml_attribute())


@six.python_2_unicode_compatible
class Size(object):
    """Ties together a number with a unit, to represent a size.

    Use as value objects! (don't change after creation)
    """
    def __init__(self, value, unit):
        """
        :param value: A number (float or int will do)
        :param unit: A UnitEnum member
        """
        if value is None:
            raise ValueError("Size must be initialized with a value.")

        self.value = float(value)
        self.unit = unit

    def __sub__(self, other):
        if self.unit == other.unit:
            return Size(self.value - other.value, self.unit)
        else:
            raise ValueError("The sizes should have the same measure units.")

    def __abs__(self):
        return Size(abs(self.value), self.unit)

    def __cmp__(self, other):
        if self.unit == other.unit:
            # python3 does not have cmp
            return (self.value > other.value) - (self.value < other.value)
        else:
            raise ValueError("The sizes should have the same measure units.")

    def __lt__(self, other):
        return self.value < other.value


    def __add__(self, other):
        if self.unit == other.unit:
            return Size(self.value + other.value, self.unit)
        else:
            raise ValueError("The sizes should have the same measure units.")

    def is_relative(self):
        """
        Returns True if value is expressed as percentage, False otherwise.
        """
        return self.unit == UnitEnum.PERCENT

    def as_percentage_of(self, video_width=None, video_height=None):
        """
        :param video_width: An integer representing a width in pixels
        :param video_height: An integer representing a height in pixels
        """
        value = self.value
        unit = self.unit

        if unit == UnitEnum.PERCENT:
            return self  # Nothing to do here

        # The input must be valid so that any conversion can be done
        if not (video_width or video_height):
            raise RelativizationError(
                "Either video width or height must be given as a reference")
        elif video_width and video_height:
            raise RelativizationError(
                "Only video width or height can be given as reference")

        if unit == UnitEnum.EM:
            # TODO: Implement proper conversion of em in function of font-size
            # The em unit is relative to the font-size, to which we currently
            # have no access. As a workaround, we presume the font-size is 16px,
            # which is a common default value but not guaranteed.
            value *= 16
            unit = UnitEnum.PIXEL

        if unit == UnitEnum.PT:
            # XXX: we will convert first to "px" and from "px" this will be
            # converted to percent. we don't take into consideration the
            # font-size
            value = value / 72.0 * 96.0
            unit = UnitEnum.PIXEL

        if unit == UnitEnum.PIXEL:
            value = value * 100.0 / (video_width or video_height)
            unit = UnitEnum.PERCENT

        if unit == UnitEnum.CELL:
            # TODO: Implement proper cell resolution
            # (w3.org/TR/ttaf1-dfxp/#parameter-attribute-cellResolution)
            # For now we will use the default values (32 columns and 15 rows)
            cell_reference = 32 if video_width else 15
            value = value * 100.0 / cell_reference
            unit = UnitEnum.PERCENT

        return Size(value, unit)

    @classmethod
    # TODO - this also looks highly cachable. Should use a WeakValueDict here
    # to return flyweights
    def from_string(cls, string):
        """Given a string of the form "46px" or "5%" etc., returns the proper
        size object

        :param string: a number concatenated to any of the UnitEnum members.
        :type string: unicode
        :rtype: Size
        """

        units = [UnitEnum.CELL, UnitEnum.PERCENT, UnitEnum.PIXEL,
                 UnitEnum.EM, UnitEnum.PT]

        raw_number = string
        for unit in units:
            if raw_number.endswith(unit):
                raw_number = raw_number.rstrip(unit)
                break
        else:
            unit = None

        if unit is not None:
            value = None
            try:
                value = float(raw_number)
                value = int(raw_number)
            except ValueError:
                pass

            if value is None:
                raise ValueError(
                    """Couldn't recognize the value "{value}" as a number"""
                    .format(value=raw_number)
                )
            instance = cls(value, unit)
            return instance
        else:
            raise ValueError(
                "The specified value is not valid because its unit "
                "is not recognized: {value}. "
                "The only supported units are: {supported}"
                .format(value=raw_number, supported=', '.join(UnitEnum._member_map_))
            )

    def __repr__(self):
        return '<Size ({value} {unit})>'.format(
            value=self.value, unit=self.unit
        )

    def __str__(self):
        value = round(self.value, 2)
        if value.is_integer():
            s = "{}".format(int(value))
        else:
            s = "{:.2f}".format(value).rstrip('0').rstrip('.')
        return "{}{}".format(s, self.unit)

    def to_xml_attribute(self, **kwargs):
        """Returns a unicode representation of this object, as an xml attribute
        """
        return six.text_type(self)

    def serialized(self):
        """Returns the "useful" values of this object"""
        return self.value, self.unit

    def __eq__(self, other):
        return (
            other and
            type(self) == type(other) and
            self.value == other.value and
            self.unit == other.unit
        )

    def __hash__(self):
        return hash(
            hash(self.value) * 41 +
            hash(self.unit) * 43 +
            47
        )

    def __bool__(self):
        return self.value is not None


class Padding(object):
    """Represents padding information. Consists of 4 Size objects, representing
    padding from (in this order): before (up), after (down), start (left) and
    end (right).

    A valid Padding object must always have all paddings set and different from
    None. If this is not true Writers may fail for they rely on this assumption.
    """
    def __init__(self, before=None, after=None, start=None, end=None):
        """
        :type before: Size
        :type after: Size
        :type start: Size
        :type end: Size
        """
        self.before = before  # top
        self.after = after  # bottom
        self.start = start  # left
        self.end = end  # right

        for attr in ['before', 'after', 'start', 'end']:
            # Ensure that a Padding object always explicitly defines all
            # four possible paddings
            if not isinstance(getattr(self, attr), Size):
                # Sets default padding (0%)
                setattr(self, attr, Size(0, UnitEnum.PERCENT))

    @classmethod
    def from_xml_attribute(cls, attribute):
        """As per the docs, the style attribute can contain 1,2,3 or 4 values.

        If 1 value: apply to all edges
        If 2: first applies to before and after, second to start and end
        If 3: first applies to before, second to start and end, third to after
        If 4: before, end, after, start;

        http://www.w3.org/TR/ttaf1-dfxp/#style-attribute-padding

        :param attribute: a string like object, representing a dfxp attr. value
        :return: a Padding object
        """
        values_list = six.text_type(attribute).split(' ')
        sizes = []

        for value in values_list:
            sizes.append(Size.from_string(value))

        if len(sizes) == 1:
            return cls(sizes[0], sizes[0], sizes[0], sizes[0])
        elif len(sizes) == 2:
            return cls(sizes[0], sizes[0], sizes[1], sizes[1])
        elif len(sizes) == 3:
            return cls(sizes[0], sizes[2], sizes[1], sizes[1])
        elif len(sizes) == 4:
            return cls(sizes[0], sizes[2], sizes[3], sizes[1])
        else:
            raise ValueError('The provided value "{value}" could not be '
                             "parsed into the a padding. Check out "
                             "http://www.w3.org/TR/ttaf1-dfxp/"
                             "#style-attribute-padding for the definition "
                             "and examples".format(value=attribute))

    def __repr__(self):
        return (
            "<Padding (before: {before}, after: {after}, start: {start}, "
            "end: {end})>".format(
                before=self.before, after=self.after, start=self.start,
                end=self.end
            )
        )

    def serialized(self):
        """Returns a tuple containing the useful values of this object
        """
        return (
            None if not self.before else self.before.serialized(),
            None if not self.after else self.after.serialized(),
            None if not self.start else self.start.serialized(),
            None if not self.end else self.end.serialized()
        )

    def __eq__(self, other):
        return (
            other and
            type(self) == type(other) and
            self.before == other.before and
            self.after == other.after and
            self.start == other.start and
            self.end == other.end
        )

    def __hash__(self):
        return hash(
            hash(self.before) * 19 +
            hash(self.after) * 23 +
            hash(self.start) * 29 +
            hash(self.end) * 31 +
            37
        )

    def to_xml_attribute(
            self, attribute_order=('before', 'end', 'after', 'start'),
            **kwargs):
        """Returns a unicode representation of this object as an xml attribute

        TODO - should extend the attribute_order tuple to contain 4 tuples,
        so we can reduce the output length to 3, 2 or 1 element.

        :type attribute_order: tuple
        :param attribute_order: the order that the attributes should be
            serialized
        """
        try:
            string_list = []
            for attrib in attribute_order:
                if hasattr(self, attrib):
                    string_list.append(
                        getattr(self, attrib).to_xml_attribute())
        except AttributeError:
            # A Padding object with attributes set to None is considered
            # invalid. All four possible paddings must be set. If one of them
            # is not, this error is raised.
            raise ValueError("The attribute order specified is invalid.")

        return ' '.join(string_list)

    def as_percentage_of(self, video_width, video_height):
        return Padding(
            self.before.as_percentage_of(video_height=video_height),
            self.after.as_percentage_of(video_height=video_height),
            self.start.as_percentage_of(video_width=video_width),
            self.end.as_percentage_of(video_width=video_width)
        )

    def is_relative(self):
        is_relative = True
        if self.before:
            is_relative &= self.before.is_relative()
        if self.after:
            is_relative &= self.after.is_relative()
        if self.start:
            is_relative &= self.start.is_relative()
        if self.end:
            is_relative &= self.end.is_relative()
        return is_relative


class Layout(object):
    """Should encapsulate all the information needed to determine (as correctly
    as possible) the layout (positioning) of elements on the screen.

     Inheritance of this property, from the CaptionSet to its children is
     specific for each caption type.
    """
    def __init__(self, origin=None, extent=None, padding=None, alignment=None,
                 webvtt_positioning=None, inherit_from=None):
        """
        :type origin: Point
        :param origin: The point on the screen which is the top left vertex
            of a rectangular region where the captions should be placed

        :type extent: Stretch
        :param extent: The width and height of the rectangle where the caption
            should be placed on the screen.

        :type padding: Padding
        :param padding: The padding of the text inside the region described
            by the origin and the extent

        :type alignment: Alignment

        :type webvtt_positioning: unicode
        :param webvtt_positioning: A string with the raw WebVTT cue settings.
            This is used so that WebVTT positioning isn't lost on conversion
            from WebVTT to WebVTT. It is needed only because pycaption
            currently doesn't support reading positioning from WebVTT.

        :type inherit_from: Layout
        :param inherit_from: A Layout with the positioning parameters to be
            used if not specified by the positioning arguments,
        """

        self.origin = origin
        self.extent = extent
        self.padding = padding
        self.alignment = alignment
        self.webvtt_positioning = webvtt_positioning

        if inherit_from:
            for attr_name in ['origin', 'extent', 'padding', 'alignment']:
                attr = getattr(self, attr_name)
                if not attr:
                    setattr(self, attr_name, getattr(inherit_from, attr_name))

    def __bool__(self):
        return any([
            self.origin, self.extent, self.padding, self.alignment,
            self.webvtt_positioning
        ])

    def __repr__(self):
        return (
            "<Layout (origin: {origin}, extent: {extent}, "
            "padding: {padding}, alignment: {alignment})>".format(
                origin=self.origin, extent=self.extent, padding=self.padding,
                alignment=self.alignment
            )
        )

    def serialized(self):
        """Returns nested tuple containing the "useful" values of this object
        """
        return (
            None if not self.origin else self.origin.serialized(),
            None if not self.extent else self.extent.serialized(),
            None if not self.padding else self.padding.serialized(),
            None if not self.alignment else self.alignment.serialized()
        )

    def __eq__(self, other):
        return (
            type(self) == type(other) and
            self.origin == other.origin and
            self.extent == other.extent and
            self.padding == other.padding and
            self.alignment == other.alignment
        )

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(
            hash(self.origin) * 7
            + hash(self.extent) * 11
            + hash(self.padding) * 13
            + hash(self.alignment) * 5
            + 17
        )

    def is_relative(self):
        """
        Returns True if all positioning values are expressed as percentages,
        False otherwise.
        """
        is_relative = True
        if self.origin:
            is_relative &= self.origin.is_relative()
        if self.extent:
            is_relative &= self.extent.is_relative()
        if self.padding:
            is_relative &= self.padding.is_relative()
        return is_relative

    def as_percentage_of(self, video_width, video_height):
        params = {'alignment': self.alignment}
        # We don't need to preserve webvtt_positioning on Layout
        # transformations because, if it is set, the WebVTT writer
        # returns as soon as it's found and the transformations are
        # never triggered.
        for attr_name in ['origin', 'extent', 'padding']:
            attr = getattr(self, attr_name)
            if attr:
                params[attr_name] = attr.as_percentage_of(video_width,
                                                          video_height)
        return Layout(**params)

    def fit_to_screen(self):
        """
        If extent is not set or if origin + extent > 100%, (re)calculate it
        based on origin. It is a pycaption fix for caption files that are
        technically valid but contain inconsistent settings that may cause
        long captions to be cut out of the screen.

        ATTENTION: This must be called on relativized objects (such as the one
        returned by as_percentage_of). All units are presumed to be percentages.
        """

        if self.origin:
            # Calculated values to be used if replacement is needed
            diff_horizontal = Size(100 - self.origin.x.value, UnitEnum.PERCENT)
            diff_vertical = Size(100 - self.origin.y.value, UnitEnum.PERCENT)
            if not self.extent:
                # Extent is not set, use the calculated values
                new_extent = Stretch(diff_horizontal, diff_vertical)
            else:
                # Extent is set but may have inconsistent values,
                # e.g. origin="35% 25%" extent="80% 80%", which would cause
                # captions to end horizontally at 115% and vertically at 105%,
                # which would result in them being cut out of the screen.
                # In this case, the horizontal and vertical values are
                # corrected so that origin + extent = 100%.
                bottom_right = self.origin.add_stretch(self.extent)

                found_absolute_unit = False
                if bottom_right.x.unit != UnitEnum.PERCENT:
                    found_absolute_unit = True
                elif bottom_right.x.unit != UnitEnum.PERCENT:
                    found_absolute_unit = True

                if found_absolute_unit:
                    raise ValueError("Units must be relativized before extent "
                                     "can be calculated based on origin.")

                new_horizontal = self.extent.horizontal
                new_vertical = self.extent.vertical
                # If extent is set but it's inconsistent, replace with
                # calculated values
                if bottom_right.x.value > 100:
                    new_horizontal = diff_horizontal
                if bottom_right.y.value > 100:
                    new_vertical = diff_vertical

                new_extent = Stretch(new_horizontal, new_vertical)

            return Layout(
                origin=self.origin,
                extent=new_extent,
                padding=self.padding,
                alignment=self.alignment
                # We don't need to preserve webvtt_positioning on Layout
                # transformations because, if it is set, the WebVTT writer
                # returns as soon as it's found and the transformations are
                # never triggered.
            )

        return self
