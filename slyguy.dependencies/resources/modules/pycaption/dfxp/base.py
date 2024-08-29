import re
import six
from copy import deepcopy
from xml.sax.saxutils import escape
from bs4 import BeautifulSoup, NavigableString

from ..base import (
    BaseReader, BaseWriter, CaptionSet, CaptionList, Caption, CaptionNode,
    DEFAULT_LANGUAGE_CODE)
from ..exceptions import (
    CaptionReadNoCaptions, CaptionReadSyntaxError, InvalidInputError)
from ..geometry import (
    Point, Stretch, UnitEnum, Padding, VerticalAlignmentEnum,
    HorizontalAlignmentEnum, Alignment, Layout)
from ..utils import is_leaf

__all__ = [
    'DFXP_BASE_MARKUP', 'DFXP_DEFAULT_STYLE', 'DFXP_DEFAULT_STYLE_ID',
    'DFXP_DEFAULT_REGION_ID', 'DFXPReader', 'DFXPWriter', 'DFXP_DEFAULT_REGION'
]

DFXP_BASE_MARKUP = '''
<tt xmlns="http://www.w3.org/ns/ttml"
    xmlns:tts="http://www.w3.org/ns/ttml#styling">
    <head>
        <styling/>
        <layout/>
    </head>
    <body/>
</tt>
'''

DFXP_DEFAULT_STYLE = {
    'color': 'white',
    'font-family': 'monospace',
    'font-size': '1c',
}

DFXP_DEFAULT_REGION = Layout(
    alignment=Alignment(
        HorizontalAlignmentEnum.CENTER, VerticalAlignmentEnum.BOTTOM)
)

DFXP_DEFAULT_STYLE_ID = 'default'
DFXP_DEFAULT_REGION_ID = 'bottom'


class DFXPReader(BaseReader):

    def __init__(self, *args, **kw):
        super(DFXPReader, self).__init__(*args, **kw)
        self.read_invalid_positioning = (
            kw.get('read_invalid_positioning', False))
        self.nodes = []

    def detect(self, content):
        if '</tt>' in content.lower():
            return True
        else:
            return False

    def read(self, content):
        if type(content) != six.text_type:
            raise InvalidInputError('The content is not a unicode string.')

        dfxp_document = self._get_dfxp_parser_class()(
            content, read_invalid_positioning=self.read_invalid_positioning)

        caption_dict = {}
        style_dict = {}

        # Each div represents all the captions for a single language.
        for div in dfxp_document.find_all('div'):
            lang = div.attrs.get('xml:lang', DEFAULT_LANGUAGE_CODE)

            caption_dict[lang] = self._translate_div(div)

        for style in dfxp_document.find_all('style'):
            id_ = style.attrs.get('xml:id') or style.attrs.get('id')
            if id_:
                # Don't create document styles for those styles that are
                # descendants of <region> tags. See link:
                # http://www.w3.org/TR/ttaf1-dfxp/#styling-vocabulary-style
                if 'region' not in [
                        parent_.name for parent_ in style.parents]:
                    style_dict[id_] = self._translate_style(style)

        caption_set = CaptionSet(caption_dict, styles=style_dict)

        if caption_set.is_empty():
            raise CaptionReadNoCaptions("empty caption file")

        return caption_set

    @staticmethod
    def _get_dfxp_parser_class():
        """Hook method for providing a custom DFXP parser
        """
        return LayoutAwareDFXPParser

    def _translate_div(self, div):
        return CaptionList(
            [self._translate_p_tag(p_tag) for p_tag in div.find_all('p')],
            div.layout_info
        )

    def _translate_p_tag(self, p_tag):
        start, end = self._find_times(p_tag)
        self.nodes = []
        self._translate_tag(p_tag)
        styles = self._translate_style(p_tag)

        if len(self.nodes) > 0:
            return Caption(
                start, end, self.nodes, style=styles,
                layout_info=p_tag.layout_info)
        return None

    def _find_times(self, p_tag):
        start = self._translate_time(p_tag['begin'])

        try:
            end = self._translate_time(p_tag['end'])
        except KeyError:
            dur = self._translate_time(p_tag['dur'])
            end = start + dur

        return start, end

    def _translate_time(self, stamp):
        coefs = [3600000000, 60000000, 1000000]
        framerate = 24.0
        frameRateMultiplier = 1.0
        subFrameRate = 1.0

        if stamp[-1].isdigit():
            microseconds = 0

            params = stamp.split(':')
            if len(params) in (3, 4):
                if len(params) == 4:
                    frames = params[3].split('.', 2)
                    if len(frames) == 1:
                        params[2] = float(params[2]) + float(params[3]) / (framerate * frameRateMultiplier)
                    else:
                        params[2] = float(params[2]) + (
                            float(frames[0]) / frameRate +
                            float(frames[1]) / (frameRate * subFrameRate)
                        ) * frameRateMultiplier
                    del params[3]

                for c, v in zip(coefs, params):
                    microseconds += int(c*float(v))

            return microseconds
        else:
            # Must be offset-time
            m = re.search('^([0-9.]+)([a-z]+)$', stamp)
            value = float(m.group(1))
            metric = m.group(2)
            if metric == "h":
                microseconds = value * 60 * 60 * 1000000
            elif metric == "m":
                microseconds = value * 60 * 1000000
            elif metric == "s":
                microseconds = value * 1000000
            elif metric == "ms":
                microseconds = value * 1000
            else:
                raise InvalidInputError("Unsupported offset-time metric " + metric)

            return int(microseconds)

    def _translate_tag(self, tag):
        # convert text
        if isinstance(tag, NavigableString):
            # strips indentation whitespace only
            pattern = re.compile(r"^(?:[\n\r]+\s*)?(.+)")
            result = pattern.search(tag)
            if result:
                # Escaping/unescaping xml entities is the responsibility of the
                # xml parser used by BeautifulSoup in its initialization. The
                # content of the tag variable at this point should be a plain
                # unicode string with xml entities already converted to unicode
                # characters.
                tag_text = result.groups()[0]
                node = CaptionNode.create_text(
                    tag_text, layout_info=tag.layout_info)
                self.nodes.append(node)
        # convert line breaks
        elif tag.name == 'br':
            self.nodes.append(
                CaptionNode.create_break(layout_info=tag.layout_info))
        # convert italics
        elif tag.name == 'span':
            # convert span
            self._translate_span(tag)
        else:
            # recursively call function for any children elements
            for a in tag.contents:
                self._translate_tag(a)

    def _translate_span(self, tag):
        # convert tag attributes
        args = self._translate_style(tag)
        # only include span tag if attributes returned
        # TODO - this is an obvious very old bug. args will be a dictionary.
        # but since nobody complained, I'll leave it like that.
        # Happy investigating!
        if args != '':
            node = CaptionNode.create_style(
                True, args, layout_info=tag.layout_info)
            node.start = True
            node.content = args
            self.nodes.append(node)

            # recursively call function for any children elements
            for a in tag.contents:
                self._translate_tag(a)
            node = CaptionNode.create_style(
                False, args, layout_info=tag.layout_info)
            node.start = False
            node.content = args
            self.nodes.append(node)
        else:
            for a in tag.contents:
                self._translate_tag(a)

    # convert style from DFXP
    def _translate_style(self, tag):
        """Converts the attributes of an XML node to a dictionary. This is a
         deprecated method of handling styling/ layout information, and
         overlaps (in partially known ways)with the newer way of doing stuff.

         For examples of how to refactor this, see the .layout_info attribute,
         and the geometry.Layout class.


        :param tag: BeautifulSoup Tag
        :rtype: dict
        """
        attrs = {}
        dfxp_attrs = tag.attrs
        for arg in dfxp_attrs:
            if arg.lower() == "style":
                # Support multiple classes per tag
                attrs['classes'] = dfxp_attrs[arg].strip().split(' ')
                # Save old class attribute for compatibility
                attrs['class'] = dfxp_attrs[arg]
            elif arg.lower() == "tts:fontstyle" and dfxp_attrs[arg] == "italic":
                attrs['italics'] = True
            elif arg.lower() == "tts:fontweight" and dfxp_attrs[arg] == "bold":
                attrs['bold'] = True
            elif arg.lower() == "tts:textdecoration" and "underline" in dfxp_attrs[arg].strip().split(" "):
                attrs['underline'] = True
            elif arg.lower() == "tts:textalign":
                attrs['text-align'] = dfxp_attrs[arg]
            elif arg.lower() == "tts:fontfamily":
                attrs['font-family'] = dfxp_attrs[arg]
            elif arg.lower() == "tts:fontsize":
                attrs['font-size'] = dfxp_attrs[arg]
            elif arg.lower() == "tts:color":
                attrs['color'] = dfxp_attrs[arg]
        return attrs


class DFXPWriter(BaseWriter):
    def __init__(self, *args, **kwargs):
        self.write_inline_positioning = kwargs.pop(
            'write_inline_positioning', False)
        self.p_style = False
        self.open_span = False
        self.region_creator = None
        super(DFXPWriter, self).__init__(*args, **kwargs)

    def write(self, caption_set, force=''):
        """Converts a CaptionSet into an equivalent corresponding DFXP file

        :type caption_set: pycaption.base.CaptionSet
        :param force: only use this language, if available in the caption_set

        :rtype: unicode
        """
        dfxp = BeautifulSoup(DFXP_BASE_MARKUP, 'lxml-xml')
        dfxp.find('tt')['xml:lang'] = "en"

        langs = caption_set.get_languages()
        if force in langs:
            langs = [force]

        caption_set = deepcopy(caption_set)

        # Loop through all captions/nodes and apply transformations to layout
        # in function of the provided or default settings
        for lang in langs:
            for caption in caption_set.get_captions(lang):
                caption.layout_info = self._relativize_and_fit_to_screen(
                    caption.layout_info)
                for node in caption.nodes:
                    node.layout_info = self._relativize_and_fit_to_screen(
                        node.layout_info)

        # Create the styles in the <styling> section, or a default style.
        for style_id, style in caption_set.get_styles():
            if style != {}:
                dfxp = self._recreate_styling_tag(style_id, style, dfxp)
        if not caption_set.get_styles():
            dfxp = self._recreate_styling_tag(
                DFXP_DEFAULT_STYLE_ID, DFXP_DEFAULT_STYLE, dfxp)

        self.region_creator = self._get_region_creator_class()(dfxp, caption_set)
        self.region_creator.create_document_regions()

        body = dfxp.find('body')

        for lang in langs:
            div = dfxp.new_tag('div')
            div['xml:lang'] = str(lang)
            self._assign_positioning_data(div, lang, caption_set)

            for caption in caption_set.get_captions(lang):
                if caption.style:
                    caption_style = caption.style
                else:
                    caption_style = {'class': DFXP_DEFAULT_STYLE_ID}

                p = self._recreate_p_tag(
                    caption, caption_style, dfxp, caption_set, lang)
                self._assign_positioning_data(p, lang, caption_set, caption)
                div.append(p)

            body.append(div)
        self.region_creator.cleanup_regions()
        caption_content = dfxp.prettify(formatter=None)
        return caption_content

    @staticmethod
    def _get_region_creator_class():
        """Hook method for providing a custom RegionCreator
        """
        return RegionCreator

    def _assign_positioning_data(self, tag, lang, caption_set=None,
                                 caption=None, caption_node=None):
        """Modifies the current tag, assigning it the 'region' attribute.

        :param tag: the BeautifulSoup tag to be modified
        :type lang: unicode
        :param lang: the caption language
        :type caption_set: CaptionSet
        :param caption_set: The CaptionSet parent
        :type caption: Caption
        :type caption_node: CaptionNode
        """
        assigned_id, attribs = self.region_creator.get_positioning_info(
            lang, caption_set, caption, caption_node)

        if assigned_id:
            tag['region'] = assigned_id

            # Write non-standard positioning information
            if self.write_inline_positioning:
                tag.attrs.update(attribs)

    def _recreate_styling_tag(self, style, content, dfxp):
        # TODO - should be drastically simplified: if attributes : append
        dfxp_style = dfxp.new_tag('style')
        dfxp_style.attrs.update({'xml:id': style})

        attributes = _recreate_style(content, dfxp)
        dfxp_style.attrs.update(attributes)

        new_tag = dfxp.new_tag('style')
        new_tag.attrs.update({'xml:id': style})
        if dfxp_style != new_tag:
            dfxp.find('styling').append(dfxp_style)

        return dfxp

    def _recreate_p_tag(self, caption, caption_style, dfxp, caption_set=None,
                        lang=None):
        start = caption.format_start()
        end = caption.format_end()
        p = dfxp.new_tag("p", begin=start, end=end)
        p.string = self._recreate_text(caption, dfxp, caption_set, lang)

        if dfxp.find("style", {"xml:id": "p"}):
            p['style'] = 'p'

        p.attrs.update(_recreate_style(caption_style, dfxp))

        return p

    def _recreate_text(self, caption, dfxp, caption_set=None, lang=None):
        line = ''

        for node in caption.nodes:
            if node.type_ == CaptionNode.TEXT:
                line += self._encode(node.content)

            elif node.type_ == CaptionNode.BREAK:
                line = line.rstrip() + '<br/>\n    '

            elif node.type_ == CaptionNode.STYLE:
                line = self._recreate_span(
                    line, node, dfxp, caption_set, caption, lang)

        return line.rstrip()

    def _recreate_span(self, line, node, dfxp, caption_set=None, caption=None,
                       lang=None):
        # TODO - This method seriously has to go away!
        # Because of the CaptionNode.STYLE nodes, tree-like structures are
        # are really hard to build, and proper xml elements can't be added.
        # We are left with creating tags manually, which is hard to understand
        # and harder to maintain
        if node.start:
            styles = ''

            content_with_style = _recreate_style(node.content, dfxp)
            for style, value in list(content_with_style.items()):
                styles += ' %s="%s"' % (style, value)
            if node.layout_info:
                region_id, region_attribs = (
                    self.region_creator.get_positioning_info(
                        lang, caption_set, caption, node
                    ))
                styles += ' region="{region_id}"'.format(
                    region_id=region_id)
                if self.write_inline_positioning:
                    styles += ' ' + ' '.join(
                        [
                            '{key}="{val}"'.format(key=k_, val=v_)
                            for k_, v_ in list(region_attribs.items())
                        ]
                    )

            if styles:
                if self.open_span:
                    line = line.rstrip() + '</span> '
                line += '<span%s>' % styles
                self.open_span = True

        elif self.open_span:
            line = line.rstrip() + '</span> '
            self.open_span = False

        return line

    def _encode(self, s):
        """
        Escapes XML 1.0 illegal or discouraged characters
        For details see:
            - http://www.w3.org/TR/2008/REC-xml-20081126/#dt-chardata
        :type s: unicode
        :param s: The content of a text node
        """
        return escape(s)


class LayoutAwareDFXPParser(BeautifulSoup):
    """This makes the xml instance capable of providing layout information
    for every one of its nodes (it adds a 'layout_info' attribute on each node)

    It parses the element tree in pre-order-like fashion as dictated by the
    dfxp specs here:
    http://www.w3.org/TR/ttaf1-dfxp/#semantics-style-resolution-process-overall

    TODO: Some sections require pre-order traversal, others post-order (e.g.
    http://www.w3.org/TR/ttaf1-dfxp/#semantics-region-layout-step-1). For the
    features we support, it was easier to use pre-order and it seems to have
    been enough. It should be clarified whether this is ok or not.
    """
    # A lot of elements will have no positioning info. Use this flyweight
    # to save memory
    NO_POSITIONING_INFO = None

    def __init__(self, markup="", features="html.parser", builder=None,
                 parse_only=None, from_encoding=None,
                 read_invalid_positioning=False, **kwargs):
        """The `features` param determines the parser to be used. The parsers
        are usually html parsers, some more forgiving than others, and as such
        they do stuff very differently especially for xml files. We chose this
        one because even though the docs say it's slower, it's very forgiving
        (it allows unescaped `<` characters, for example). It doesn't support
        the `&apos;` entity, however, since it respects the HTML4 and not HTML5
        syntax. Since this is valid XML 1.0, as a workaround we have to
        manually replace the every occurrence of this entity in the string
        before using the parser.

        The reason why we haven't used the 'xml' parser is that it destroys
        characters such as < or & (even the escaped ones).

        The 'lxml' parser seems to respect the html specification the best, but
        it's not as forgiving as 'html.parser' and fails when there are
        unescaped `<` characters in the input, for example.

        An alternative would be using html5lib, but that (1) is an external
        dependency and (2) BeautifulSoup says it's the slowest option.

        :type read_invalid_positioning: bool
        :param read_invalid_positioning: if True, will try to also look for
            layout info on every element itself (even if the docs explicitly
            call for ignoring attributes, when incorrectly placed)


        Check out the docs below for explanation.
        http://www.crummy.com/software/BeautifulSoup/bs4/doc/#installing-a-parser
        """

        # Work around for lack of '&apos;' support in html.parser
        markup = markup.replace("&apos;", "'")

        super(LayoutAwareDFXPParser, self).__init__(
            markup, features, builder, parse_only, from_encoding, **kwargs)

        self.read_invalid_positioning = read_invalid_positioning

        for div in self.find_all('div'):
            self._pre_order_visit(div)

    def _pre_order_visit(self, element, inherit_from=None):
        """Process the xml tree elements in pre order by adding a .layout_info
        attribute to each of them.

        The specs say this is how the attributes should be determined, but
        for the region attribute this might be irrelevant and any type of tree
        walk might do.
        :param element: a BeautifulSoup Tag or NavigableString.
        :param inherit_from: a Layout object with all the layout info
                inherited from the ancestors of the present node
        """
        if is_leaf(element):
            # The element is a leaf (e.g. NavigableString or <br>)
            element.layout_info = inherit_from
        else:
            region_id = self._determine_region_id(element)
            # TODO - this looks highly cachable. If it turns out too much
            # memory is being taken up by the caption set, cache this with a
            # WeakValueDict
            layout_info = (
                self._extract_positioning_information(region_id, element))
            element.layout_info = layout_info
            for child in element.contents:
                self._pre_order_visit(child, inherit_from=layout_info)

    @staticmethod
    def _get_region_from_ancestors(element):
        """Try to get the region ID from the nearest ancestor that has it
        """
        region_id = None
        parent = element.parent
        while parent:
            region_id = parent.get('region')
            if region_id:
                break
            parent = parent.parent

        return region_id

    @staticmethod
    def _get_region_from_descendants(element):
        """Try to get the region_id from the closest descendant (that has it)
        This is trickier, because at different times, the determined region
        could be different. If this happens, discard region data
        """
        # element might be a NavigableString, not a Tag.
        # if is_leaf(element):
        if isinstance(element, NavigableString):
            return None

        region_id = None
        child_region_ids = {
            child.get('region') for child in element.findChildren()
        }
        if len(child_region_ids) > 1:
            raise LookupError
        if len(child_region_ids) == 1:
            region_id = child_region_ids.pop()

        return region_id

    @classmethod
    def _determine_region_id(cls, element):
        """Determines the TT region of an element.

        For determining the region of an element, check out the url, look for
        section "[associate region]". One difference, is that we leave the
        default region id empty. The writer will know what to do:
        http://www.w3.org/TR/ttaf1-dfxp/#semantics-region-layout-step-1

        :param element: the xml element for which we're trying to get region
            info
        """
        # element could be a NavigableString. Those are dumb.
        region_id = None

        if hasattr(element, 'get'):
            region_id = element.get('region')

        if not region_id:
            region_id = cls._get_region_from_ancestors(element)

        if not region_id:
            try:
                region_id = cls._get_region_from_descendants(element)
            except LookupError:
                return

        return region_id

    def _extract_positioning_information(self, region_id, element):
        """Returns a Layout object that describes the element's positioning
        information

        :param region_id: the id of the region to which the element is
            associated
        :type region_id: unicode
        :param element: BeautifulSoup Tag or NavigableString; this only comes
            into action (at the moment) if the
        :rtype: Layout
        """
        region_tag = None

        if region_id is not None:
            region_tag = self.find('region', {'xml:id': region_id})

        region_scraper = (
            self._get_layout_info_scraper_class()(self, region_tag))

        layout_info = region_scraper.scrape_positioning_info(
            element, self.read_invalid_positioning
        )

        if layout_info and any(layout_info):
            # layout_info contains information?
            return self._get_layout_class()(*layout_info)
        else:
            # layout_info doesn't contain any information
            return self.NO_POSITIONING_INFO

    @staticmethod
    def _get_layout_info_scraper_class():
        """Hook method for getting an implementation of a LayoutInfoScraper.
        """
        return LayoutInfoScraper

    @staticmethod
    def _get_layout_class():
        """Hook method for providing the Layout class to use
        """
        return Layout


class LayoutInfoScraper(object):
    """Encapsulates the methods for determining the layout information about
    an element (with the element's region playing an important role).
    """
    def __init__(self, document, region=None):
        """
        :param document: the BeautifulSoup document instance, of which `region`
            is a descendant
        :param region: the region tag
        """
        self.region = region
        self._styling_section = document.findChild('styling')
        if region:
            self.region_styles = self._get_style_sources(
                self._styling_section, region)
        else:
            self.region_styles = []
        self.root_element = document.find('tt')

    @classmethod
    def _get_style_sources(cls, styling_section, element):
        """Returns a list, containing  tags, in the order they should be
        evaluated, for determining layout information.

        This method should be extended if the styles provided by it are not
        enough (like for the captions created with CaptionMaker 6, which are
        not compatible with the specs)

        Check the URL for detailed description of how styles should be resolved
        http://www.w3.org/TR/ttaf1-dfxp/#semantics-style-association

        Returns:
          1. All child styles of the element, each with its reference chain
          2. The style referenced by the element, via the attrib. style="asdf"
            together with its reference chain
        Note: the specs are unclear about the priority of styles that are
        referenced by nested styles. I've assumed it's higher than referential
        styling
        """
        # If we're analyzing a NavigableString, just quit
        if not hasattr(element, 'findAll'):
            return ()

        nested_styles = []

        # <div> tags have a huge number of children, with highly unlikely
        # <style> tags among them. Looping through all of them as is, would
        # make the DFXP parser freeze for a long time, so we skip this step
        # if the parent is a <div> tag. Technically, this step shouldn't be
        # skipped, but it would make the reader read in O(n^2) (half an hour
        # for 1500 timed captions)
        if element.name not in ('div', 'body', 'tt'):
            for style in element.contents:
                if getattr(style, 'name', None) == 'style':
                    nested_styles.extend(
                        cls._get_style_reference_chain(style, styling_section)
                    )

        referenced_style_id = element.get('style')

        referenced_styles = []
        if referenced_style_id and styling_section:
            referenced_style = styling_section.findChild(
                'style', {'xml:id': referenced_style_id}
            )

            referenced_styles = (
                cls._get_style_reference_chain(
                    referenced_style, styling_section)
            )
        return nested_styles + referenced_styles

    @classmethod
    def _get_style_reference_chain(cls, style, styling_tag):
        """If style s1 references s2, and s3 -> s4 -> s5 -> ... -> sn,
        if called with s1, this returns [s1, s2, ... sn] (supposing all the
        styles are defined in the styling section, or stops at the last found
        style)

        :param style: a style tag, that might refer another style
        :param styling_tag: The tag representing the '<styling>' section of the
            dfxp document
        """
        if not style:
            return []

        result = [style]

        if not styling_tag:
            return result

        reference = style.get('style')

        if reference:
            referenced_styles = styling_tag.findChildren(
                'style', {'xml:id': reference}
            )

            if len(referenced_styles) == 1:
                return result + cls._get_style_reference_chain(
                    referenced_styles[0], styling_tag
                )
            elif len(referenced_styles) > 1:
                raise CaptionReadSyntaxError(
                    "Invalid caption file. "
                    "More than 1 style with 'xml:id': {id}"
                    .format(id=reference)
                )

        return result

    def scrape_positioning_info(self, element=None, even_invalid=False):
        """Determines the positioning information tuple
        (origin, extent, padding, alignment) from the region element.

        The first 3 attributes can be specified inline, on the region node,
        on child tags of type <style> or on referenced <style> tags.

        The fourth attribute can be specified like the first 3, or on the xml
        element itself.

        If the attributes can't be determined, default values are returned
        (where such values exist) - XXX this is incorrect. No default values
        should be provided.

        :param element: BeautifulSoup Tag or NavigableString
        :type even_invalid: bool
        :param even_invalid: if True, will search attributes on the element
            (when they really should be checked only on the region)
        :rtype: tuple
        """
        usable_elem = element if even_invalid else None

        origin = self._find_attribute(
            usable_elem, 'tts:origin', Point.from_xml_attribute, ['auto']
        ) or DFXP_DEFAULT_REGION.origin

        extent = self._find_attribute(
            usable_elem, 'tts:extent', Stretch.from_xml_attribute, ['auto'])

        if not extent:
            extent = self._find_root_extent() or DFXP_DEFAULT_REGION.extent

        padding = self._find_attribute(
            usable_elem, 'tts:padding', Padding.from_xml_attribute
        ) or DFXP_DEFAULT_REGION.padding

        # tts:textAlign is a special attribute, which can not be ignored when
        # specified on the element itself (only <p> nodes matter)
        # On elements like <span> it is also read, because this was legacy
        # behavior.
        if getattr(element, 'name', None) in ('span', 'p'):
            text_align_source = element
        else:
            text_align_source = None

        text_align = (
            self._find_attribute(text_align_source, 'tts:textAlign')
            or _create_external_horizontal_alignment(
                DFXP_DEFAULT_REGION.alignment.horizontal
            )
        )
        display_align = (
            self._find_attribute(usable_elem, 'tts:displayAlign')
            or _create_external_vertical_alignment(
                DFXP_DEFAULT_REGION.alignment.vertical
            )
        )
        alignment = _create_internal_alignment(text_align, display_align)

        return origin, extent, padding, alignment

    def _find_attribute_on_element_or_styles(self, attribute_name, element,
                                             factory, ignore, ignorecase):
        """Look up the given attribute on the element, and all the styles
        referenced by it.

        :type attribute_name: unicode
        :param element: BeautifulSoup Tag or NavigableString
        :param factory: a function, to apply to the xml attribute
        :param ignore: a list of values to ignore
        :type ignore: list
        :param ignorecase: Whether to ignore the casing
        :type ignorecase: bool
        :return: The result of applying the `factory` to the found attribute
            value, or None
        """
        value = _get_object_from_attribute(
            element, attribute_name, factory, ignore, ignorecase
        )
        if value is None:
            # Does a referenced style of the element have it?
            for style in self._get_style_sources(
                    self._styling_section, element):
                value = _get_object_from_attribute(
                    style, attribute_name, factory, ignore, ignorecase
                )
                if value:
                    break
        return value

    def _find_attribute(self, element, attribute_name, factory=lambda x: x,
                        ignore=(), ignorecase=True):
        """Try to find the `attribute_name` specified on the element, all its
        parents and all their styles (and referenced styles).

        :param element: BeautifulSoup Tag or NavigableString
        :type attribute_name: unicode
        :param attribute_name: the name of the attribute to resolve
        :type attribute_name: unicode
        :param factory: callable to transform the xml attribute into something
        :param ignore: iterable of values to ignore (will return None if the
            xml attribute is in that list)
        :param ignorecase: if True, the attribute will be searched in lowercase
            too
        :type ignorecase: bool
        :rtype: unicode
        :raises CaptionSyntaxError:
        """
        value = None

        # Does the element itself have it inline, or any of its styles?
        if element:
            value = self._find_attribute_on_element_or_styles(
                attribute_name, element, factory, ignore, ignorecase)

            if value is None:
                # Do any of the element's parents have the attribute?
                for parent in element.parents:
                    value = self._find_attribute_on_element_or_styles(
                        attribute_name, parent, factory, ignore, ignorecase
                    )
                    if value:
                        break

        # Does self.region or any of its styles have it?
        if value is None:
            value = self._find_attribute_on_element_or_styles(
                attribute_name, self.region, factory, ignore, ignorecase
            )

        return value

    def _find_root_extent(self):
        """Finds the "tts:extent" for the root <tt> element

        The tts:extent attribute, like the "tts:origin", can be specified on
        the region, its styles, or can be inherited from the root <tt> element.
        For the latter case, it must be specified in the unit 'pixel'.

        :rtype: Stretch
        """
        extent = None

        # Does the root 'tt' element have it?
        if extent is None:
            root = self.root_element
            extent = _get_object_from_attribute(
                root, 'tts:extent', Stretch.from_xml_attribute
            )

            if extent is not None:
                if not extent.is_measured_in(UnitEnum.PIXEL):
                    raise CaptionReadSyntaxError(
                        "The base <tt> element attribute 'tts:extent' should "
                        "only be specified in pixels. Check the docs: "
                        "http://www.w3.org/TR/ttaf1-dfxp/"
                        "#style-attribute-extent"
                    )
        return extent


class RegionCreator(object):
    """Creates the DFXP regions, and knows how retrieve them, for assigning
    region IDs to every element

    # todo - needs to remember the IDs created, and later, when assigning a
    region to every dfxp element, needs to know what region to assign to that
    element, based on the CaptionNode, its Caption and its CaptionSet.

    The layout information for a node is determined like this:
        - If a node has a (NON-NULL*).layout_info attribute, return the region
            created for that exact specification
        - If a node has .layout_info = NULL*, retrieve the .layout_info from
            its Caption parent... if still NULL*, retrieve it from its
            CaptionSet
        - If the retrieval still resulted in None, assign to it the Default
            region

        *: NULL means LayoutAwareBeautifulParser.NO_POSITIONING_INFO
    """
    def __init__(self, dfxp, caption_set):
        """
        :type dfxp: BeautifulSoup
        :type caption_set: CaptionSet
        """
        self._dfxp = dfxp
        self._caption_set = caption_set
        self._region_map = {}
        self._id_seed = 0
        self._assigned_region_ids = set()

    @staticmethod
    def _collect_unique_regions(caption_set, ignore_region):
        """Iterate through all the nodes in the caption set, and return a list
        of all unique region specs (Layout objects)

        If a default region was created, and any scraped region matches its
        attributes, don't duplicate the region (eliminate that region from the
        result set)

        :type caption_set: CaptionSet
        :return: iterable containing the unique regions that will have to
            appear in the document
        """
        # This used to be a set, however since set order depends on the hash,
        # this messed up the tests every time some little detail was added to
        # the Layout class, or its references (which is highly fragile)
        unique_regions = _OrderedSet()
        # Get all the regions for all the <div>'s..corresponding to all the
        # languages
        languages = caption_set.get_languages()
        for lang in languages:
            layout_info = caption_set.get_layout_info(lang)
            unique_regions.add(layout_info)

            # Get the regions of all the captions.. (the <p> tags)
            for caption in caption_set.get_captions(lang):
                unique_regions.add(caption.layout_info)

                # The regions of all the text/br/style nodes
                for node in caption.nodes:
                    unique_regions.add(node.layout_info)

        unique_regions.discard(None)
        unique_regions.discard(ignore_region)
        return unique_regions

    @staticmethod
    def _create_unique_regions(unique_layouts, dfxp, id_factory):
        """Create each one of the regions in the list, inside the dfxp
        document, under the 'layout' section.

        :param unique_layouts: an iterable (unique!) geometry.Layout instances,
            describing the properties to be added to the dfxp regions
        :type dfxp: BeautifulSoup
        :param id_factory: A callable which generates unique IDs
        :return: a dict, mapping each unique layout to the ID of the region
            created for it
        :rtype: dict
        """
        region_map = {}
        layout_section = dfxp.find('layout')

        for region_spec in unique_layouts:
            if (
                    region_spec.origin or region_spec.extent or
                    region_spec.padding or region_spec.alignment):

                new_region = dfxp.new_tag('region')
                new_id = id_factory()
                new_region['xml:id'] = new_id

                region_map[region_spec] = new_id
                region_attribs = _convert_layout_to_attributes(region_spec)
                new_region.attrs.update(region_attribs)

                layout_section.append(new_region)
        return region_map

    def create_document_regions(self):
        """Create the <region> tags required to position all the captions.

        Makes sure we have a default region
        """
        # Creates the default region
        default_region_map = self._create_unique_regions(
            [DFXP_DEFAULT_REGION],
            self._dfxp, lambda: DFXP_DEFAULT_REGION_ID
        )
        unique_regions = self._collect_unique_regions(
            self._caption_set, DFXP_DEFAULT_REGION)

        # Create the document specified regions
        self._region_map = self._create_unique_regions(
            unique_regions, self._dfxp, self._get_new_id)

        self._region_map.update(default_region_map)

    def _get_new_id(self, prefix='r'):
        """Return new, unique ids (use an internal counter).

        :type prefix: unicode
        """
        new_id = str((prefix or '') + str(self._id_seed))
        self._id_seed += 1
        return new_id

    def get_positioning_info(
            self, lang, caption_set=None, caption=None, caption_node=None):
        """For the given element will return a valid region ID, used for
        assigning to the element, and a dict containing the positioning
        attributes of that region (useful for inline non-standard positioning)

        For the region_id to be returned for the entire CaptionSet, don't
        supply the `caption` or `caption_node` params.

        For the region_id to be returned for the Caption, don't supply the
        `caption_node` param

        <div> tags mean the caption is None and caption_node is None.
        <p> tags mean the caption_node is None

        :type lang: unicode
        :param lang: the language of the current caption element
        :type caption_set: CaptionSet
        :type caption: Caption
        :type caption_node: CaptionNode
        :rtype: tuple
        :return: (unicode, dict)
        """
        # More intelligent people would have used an elem.parent.parent..parent
        # pattern, but pycaption is not yet structured for this. 3 params
        # is not too much of a bother. If someone wants to make the structure
        # tree-like, they can easily change this.
        layout_info = None
        if caption_node:
            layout_info = caption_node.layout_info

        if not layout_info and caption:
            layout_info = caption.layout_info

        if not layout_info and caption_set:
            layout_info = caption_set.get_layout_info(lang)
            if not layout_info:
                layout_info = caption_set.layout_info

        region_id = self._region_map.get(layout_info)

        # Make sure the default region ID/ attributes are always returned
        # as fallback
        if not region_id:
            region_id = DFXP_DEFAULT_REGION_ID

        positioning_attributes = _convert_layout_to_attributes(layout_info)

        # Mark the region as having been assigned, so we can perform cleanup
        self._assigned_region_ids.add(region_id)

        return region_id, positioning_attributes

    def cleanup_regions(self):
        """Remove the unused regions from the output file
        """
        layout_tag = self._dfxp.find('layout')
        if not layout_tag:
            return

        regions = layout_tag.findChildren('region')
        if not regions:
            return

        for region in regions:
            if region.attrs.get('xml:id') not in self._assigned_region_ids:
                region.extract()


def _recreate_style(content, dfxp):
    dfxp_style = {}

    if 'class' in content:
        if dfxp.find("style", {"xml:id": content['class']}):
            dfxp_style['style'] = content['class']
    if 'text-align' in content:
        dfxp_style['tts:textAlign'] = content['text-align']
    if 'italics' in content:
        dfxp_style['tts:fontStyle'] = 'italic'
    if 'font-family' in content:
        dfxp_style['tts:fontFamily'] = content['font-family']
    if 'font-size' in content:
        dfxp_style['tts:fontSize'] = content['font-size']
    if 'color' in content:
        dfxp_style['tts:color'] = content['color']
    if 'display-align' in content:
        dfxp_style['tts:displayAlign'] = content['display-align']

    return dfxp_style


# TODO - highly cacheable. use WeakValueDict to improve performance
def _create_internal_alignment(text_align, display_align):
    """Given the 2 DFXP specific attributes, return the internal representation
    of an alignment

    In DFXP, the tts:textAlign can have the values
        "left", "center", "right", "start" and "end"
        with the default being "start".
    We interpret "start" as "left"... we don't yet support languages
    with right-to-left writing

    The "tts:displayAlign" can have the values
        "before", "center" and "after",
    with the default of "before". These refer to top/bottom positioning.

    :type text_align: unicode
    :type display_align: unicode
    :rtype: Alignment
    """
    if not (text_align or display_align):
        return None

    return Alignment.from_horizontal_and_vertical_align(
        text_align, display_align)


def _create_external_horizontal_alignment(horizontal_component):
    """From an internal horizontal alignment value, create a value to be used
    in the dfxp output file.

    :type horizontal_component: unicode
    :rtype: unicode
    """
    result = None

    if horizontal_component == HorizontalAlignmentEnum.LEFT:
        result = 'left'
    if horizontal_component == HorizontalAlignmentEnum.CENTER:
        result = 'center'
    if horizontal_component == HorizontalAlignmentEnum.RIGHT:
        result = 'right'
    if horizontal_component == HorizontalAlignmentEnum.START:
        result = 'start'
    if horizontal_component == HorizontalAlignmentEnum.END:
        result = 'end'

    return result


def _create_external_vertical_alignment(vertical_component):
    """Given an alignment value used in the internal representation of the
    caption, return a value usable in the actual dfxp output file.

    :type vertical_component: unicode
    :rtype: unicode
    """
    result = None

    if vertical_component == VerticalAlignmentEnum.TOP:
        result = 'before'
    if vertical_component == VerticalAlignmentEnum.CENTER:
        result = 'center'
    if vertical_component == VerticalAlignmentEnum.BOTTOM:
        result = 'after'

    return result


def _create_external_alignment(alignment):
    """Given an alignment object, return a dictionary. The keys are the dfxp
    attributes, and the value the dfxp values for the 'tts:textAlign' and
    'tts:displayAlign' attributes

    :type alignment: Alignment
    :rtype: dict
    """
    result = {}
    if not alignment:
        return result

    if not (alignment.horizontal or alignment.vertical):
        return result

    horizontal_alignment = _create_external_horizontal_alignment(
        alignment.horizontal)
    if horizontal_alignment:
        result['tts:textAlign'] = horizontal_alignment

    vertical_alignment = _create_external_vertical_alignment(
        alignment.vertical)
    if vertical_alignment:
        result['tts:displayAlign'] = vertical_alignment

    return result


def _get_object_from_attribute(tag, attr_name, factory,
                               ignore_vals=(), ignorecase=True):
    """For the xml `tag`, tries to retrieve the attribute `attr_name` and
    pass that to the factory in order to get a result. If the value of the
    attribute is in the `ignore_vals` iterable, returns None.

    :param tag: a BeautifulSoup tag
    :param attr_name: a string; represents an xml attribute name
    :param factory: a callable to transform the attribute into something
        usable (such as the classes from .geometry)
    :param ignore_vals: iterable of attribute values to ignore
    :raise CaptionReadSyntaxError: if the attribute has some crazy value
    """
    if not hasattr(tag, 'has_attr'):
        return

    attr_value = None
    if tag.has_attr(attr_name):
        attr_value = tag.get(attr_name)

    if ignorecase and attr_name is not None:
        attr_value = tag.get(attr_name.lower())

    if attr_value is None:
        return

    usable_value = None

    if attr_value not in ignore_vals:
        try:
            usable_value = factory(attr_value)
        except ValueError as err:
            raise CaptionReadSyntaxError(err)

    return usable_value


def _convert_layout_to_attributes(layout):
    """Takes a layout object, and returns a dict whose keys are the dfxp
    attribute names, and the values are the dfxp attr. values.

    If the layout is None, return region default attributes

    :type layout: Layout
    :rtype: dict
    """
    result = {}
    if not layout:
        # TODO - change this to actually use the DFXP_DEFAULT_REGION
        result['tts:textAlign'] = HorizontalAlignmentEnum.CENTER
        result['tts:displayAlign'] = VerticalAlignmentEnum.BOTTOM
        return result

    if layout.origin:
        result['tts:origin'] = layout.origin.to_xml_attribute()

    if layout.extent:
        result['tts:extent'] = layout.extent.to_xml_attribute()

    if layout.padding:
        result['tts:padding'] = layout.padding.to_xml_attribute()

    if layout.alignment:
        result.update(_create_external_alignment(layout.alignment))

    return result


class _OrderedSet(list):
    """Quick implementation of a set that tracks the order. If this is a
    performance bottleneck, replace it with some other implementation.
    """
    def add(self, p_object):
        if p_object not in self:
            super(_OrderedSet, self).append(p_object)

    def discard(self, value):
        if value in self:
            super(_OrderedSet, self).remove(value)
