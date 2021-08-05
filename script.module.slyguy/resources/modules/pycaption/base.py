from datetime import timedelta
from numbers import Number
from six import text_type

from .exceptions import CaptionReadError, CaptionReadTimingError

DEFAULT_LANGUAGE_CODE = 'en-US'


def force_byte_string(content):
    try:
        return content.encode('UTF-8')
    except UnicodeEncodeError:
        raise RuntimeError('Invalid content encoding')
    except UnicodeDecodeError:
        return content


class CaptionConverter(object):
    def __init__(self, captions=None):
        self.captions = captions if captions else []

    def read(self, content, caption_reader):
        try:
            self.captions = caption_reader.read(content)
        except AttributeError as e:
            raise Exception(e)
        return self

    def write(self, caption_writer):
        try:
            return caption_writer.write(self.captions)
        except AttributeError as e:
            raise Exception(e)


class BaseReader(object):
    def __init__(self, *args, **kwargs):
        pass

    def detect(self, content):
        if content:
            return True
        else:
            return False

    def read(self, content):
        return CaptionSet()


class BaseWriter(object):
    def __init__(self, relativize=True, video_width=None, video_height=None,
                 fit_to_screen=True):
        """
        Initialize writer with the given parameters.

        :param relativize: If True (default), converts absolute positioning
            values (e.g. px) to percentage. ATTENTION: WebVTT does not support
            absolute positioning. If relativize is set to False and it finds
            an absolute positioning parameter for a given caption, it will
            ignore all positioning for that cue and show it in the default
            position.
        :param video_width: The width of the video for which the captions being
            converted were made. This is necessary for relativization.
        :param video_height: The height of the video for which the captions
            being converted were made. This is necessary for relativization.
        :param fit_to_screen: If extent is not set or
            if origin + extent > 100%, (re)calculate it based on origin.
            It is a pycaption fix for caption files that are technically valid
            but contains inconsistent settings that may cause long captions to
            be cut out of the screen.
        """
        self.relativize = relativize
        self.video_width = video_width
        self.video_height = video_height
        self.fit_to_screen = fit_to_screen

    def _relativize_and_fit_to_screen(self, layout_info):
        if layout_info:
            if self.relativize:
                # Transform absolute values (e.g. px) into percentages
                layout_info = layout_info.as_percentage_of(
                    self.video_width, self.video_height)
            if self.fit_to_screen:
                # Make sure origin + extent <= 100%
                layout_info = layout_info.fit_to_screen()
        return layout_info

    def write(self, content):
        return content


class Style(object):
    def __init__(self):
        pass


class CaptionNode(object):
    """
    A single node within a caption, representing either
    text, a style, or a linebreak.

    Rules:
        1. All nodes should have the property layout_info set.
        The value None means specifically that no positioning information
        should be specified. Each reader is to supply its own default
        values (if necessary) when reading their respective formats.
    """

    TEXT = 1
    # When and if this is extended, it might be better to turn it into a
    # property of the node, not a type of node itself.
    STYLE = 2
    BREAK = 3

    def __init__(self, type_, layout_info=None):
        """
        :type type_: int
        :type layout_info: Layout
        """
        self.type_ = type_
        self.content = None

        # Boolean. Marks the beginning/ end of a Style node.
        self.start = None
        self.layout_info = layout_info

    def __repr__(self):
        t = self.type_

        if t == CaptionNode.TEXT:
            return repr(self.content)
        elif t == CaptionNode.BREAK:
            return repr('BREAK')
        elif t == CaptionNode.STYLE:
            return repr('STYLE: %s %s' % (self.start, self.content))
        else:
            raise RuntimeError('Unknown node type: ' + str(t))

    @staticmethod
    def create_text(text, layout_info=None):
        data = CaptionNode(CaptionNode.TEXT, layout_info=layout_info)
        data.content = text
        return data

    @staticmethod
    def create_style(start, content, layout_info=None):
        data = CaptionNode(CaptionNode.STYLE, layout_info=layout_info)
        data.content = content
        data.start = start
        return data

    @staticmethod
    def create_break(layout_info=None):
        return CaptionNode(CaptionNode.BREAK, layout_info=layout_info)


class Caption(object):
    """
    A single caption, including the time and styling information
    for its display.
    """
    def __init__(self, start, end, nodes, style={}, layout_info=None):
        """
        Initialize the Caption object
        :param start: The start time in microseconds
        :type start: Number
        :param end: The end time in microseconds
        :type end: Number
        :param nodes: A list of CaptionNodes
        :type nodes: list
        :param style: A dictionary with CSS-like styling rules
        :type style: dict
        :param layout_info: A Layout object with the necessary positioning
            information
        :type layout_info: Layout
        """
        if not isinstance(start, Number):
            raise CaptionReadTimingError("Captions must be initialized with a"
                                         " valid start time")
        if not isinstance(end, Number):
            raise CaptionReadTimingError("Captions must be initialized with a"
                                         " valid end time")
        if not nodes:
            raise CaptionReadError("Node list cannot be empty")
        self.start = start
        self.end = end
        self.nodes = nodes
        self.style = style
        self.layout_info = layout_info

    def is_empty(self):
        return len(self.nodes) == 0

    def format_start(self, msec_separator=None):
        """
        Format the start time value in milliseconds into a string
        value suitable for some of the supported output formats (ex.
        SRT, DFXP).
        """
        return self._format_timestamp(self.start, msec_separator)

    def format_end(self, msec_separator=None):
        """
        Format the end time value in milliseconds into a string value suitable
        for some of the supported output formats (ex. SRT, DFXP).
        """
        return self._format_timestamp(self.end, msec_separator)

    def __repr__(self):
        return repr(
            '{start} --> {end}\n{text}'.format(
                start=self.format_start(),
                end=self.format_end(),
                text=self.get_text()
            )
        )

    def get_text(self):
        """
        Get the text of the caption.
        """
        def get_text_for_node(node):
            if node.type_ == CaptionNode.TEXT:
                return node.content
            if node.type_ == CaptionNode.BREAK:
                return '\n'
            return ''
        text_nodes = [get_text_for_node(node) for node in self.nodes]
        return ''.join(text_nodes).strip()

    def _format_timestamp(self, value, msec_separator=None):
        datetime_value = timedelta(milliseconds=(int(value / 1000)))

        str_value = text_type(datetime_value)[:11]
        if not datetime_value.microseconds:
            str_value += '.000'

        if msec_separator is not None:
            str_value = str_value.replace(".", msec_separator)

        return '0' + str_value


class CaptionList(list):
    """ A list of captions with a layout object attached to it """
    def __init__(self, iterable=None, layout_info=None):
        """
        :param iterable: An iterator used to populate the caption list
        :param Layout layout_info: A Layout object with the positioning info
        """
        self.layout_info = layout_info
        args = [iterable] if iterable else []
        super(CaptionList, self).__init__(*args)

    def __getslice__(self, i, j):
        return CaptionList(
            list.__getslice__(self, i, j), layout_info=self.layout_info)

    def __getitem__(self, y):
        item = list.__getitem__(self, y)
        if isinstance(item, Caption):
            return item
        return CaptionList(item, layout_info=self.layout_info)

    def __add__(self, other):
        add_is_safe = (
            not hasattr(other, 'layout_info') or
            not other.layout_info or
            self.layout_info == other.layout_info
        )
        if add_is_safe:
            return CaptionList(
                list.__add__(self, other), layout_info=self.layout_info)
        else:
            raise ValueError(
                "Cannot add CaptionList objects with different layout_info")

    def __mul__(self, other):
        return CaptionList(
            list.__mul__(self, other), layout_info=self.layout_info)

    __rmul__ = __mul__


class CaptionSet(object):
    """
    A set of captions in potentially multiple languages,
    all representing the same underlying content.

    The .layout_info attribute, keeps information that should be inherited
    by all the children.
    """
    def __init__(self, captions, styles={}, layout_info=None):
        """
        :param captions: A dictionary of the format {'language': CaptionList}
        :param styles: A dictionary with CSS-like styling rules
        :param Layout layout_info: A Layout object with the positioning info
        """
        self._captions = captions
        self._styles = styles
        self.layout_info = layout_info

    def set_captions(self, lang, captions):
        self._captions[lang] = captions

    def get_languages(self):
        return list(self._captions.keys())

    def get_captions(self, lang):
        return [x for x in self._captions.get(lang, []) if x]

    def add_style(self, selector, rules):
        """
        :param selector: The selector indicating the elements to which the
            rules should be applied.
        :param rules: A dictionary with CSS-like styling rules.
        """
        self._styles[selector] = rules

    def get_style(self, selector):
        """
        Returns a dictionary with CSS-like styling rules for a given selector.
        :param selector: The selector whose rules should be returned (e.g. an
            element or class name).
        """
        return self._styles.get(selector, {})

    def get_styles(self):
        return sorted(self._styles.items())

    def set_styles(self, styles):
        self._styles = styles

    def is_empty(self):
        return all(
            [len(captions) == 0 for captions in list(self._captions.values())]
        )

    def set_layout_info(self, lang, layout_info):
        self._captions[lang].layout_info = layout_info

    def get_layout_info(self, lang):
        caption_list = self._captions.get(lang)
        if caption_list:
            return caption_list.layout_info
        return None

    def adjust_caption_timing(self, offset=0, rate_skew=1.0):
        """
        Adjust the timing according to offset and rate_skew.
        Skew is applied first, then offset.

        e.g. if skew == 1.1, and offset is 5, a caption originally
        displayed from 10-11 seconds would instead be at 16-17.1
        """
        for lang in self.get_languages():
            captions = self.get_captions(lang)
            out_captions = CaptionList()
            for caption in captions:
                caption.start = caption.start * rate_skew + offset
                caption.end = caption.end * rate_skew + offset
                if caption.start >= 0:
                    out_captions.append(caption)
            self.set_captions(lang, out_captions)


# Functions
def merge_concurrent_captions(caption_set):
    """Merge captions that have the same start and end times"""
    for lang in caption_set.get_languages():
        captions = caption_set.get_captions(lang)
        last_caption = None
        concurrent_captions = CaptionList()
        merged_captions = CaptionList()
        for caption in captions:
            if last_caption:
                last_timespan = last_caption.start, last_caption.end
                current_timespan = caption.start, caption.end
                if current_timespan == last_timespan:
                    concurrent_captions.append(caption)
                    last_caption = caption
                    continue
                else:
                    merged_captions.append(merge(concurrent_captions))
            concurrent_captions = [caption]
            last_caption = caption

        if concurrent_captions:
            merged_captions.append(merge(concurrent_captions))
        if merged_captions:
            caption_set.set_captions(lang, merged_captions)
    return caption_set


def merge(captions):
    """
    Merge list of captions into one caption. The start/end times from the first
    caption are kept.
    """
    new_nodes = []
    for caption in captions:
        if new_nodes:
            new_nodes.append(CaptionNode.create_break())
        for node in caption.nodes:
            new_nodes.append(node)
    caption = Caption(
        captions[0].start, captions[0].end, new_nodes, captions[0].style)
    return caption
