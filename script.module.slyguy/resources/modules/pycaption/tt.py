import re
import six
import sys
from xml.etree import ElementTree

from .base import (
    BaseReader, BaseWriter, CaptionSet, CaptionList, Caption, CaptionNode
)

from .geometry import Layout

from .exceptions import (
    CaptionReadError, CaptionReadSyntaxError, CaptionReadNoCaptions,
    InvalidInputError
)

class TTReader(BaseReader):
    def __init__(self, rich_formatting=True, *args, **kwargs):
        """
        :param ignore_timing_errors: Whether to ignore timing checks
        """
        self.rich_formatting = rich_formatting

    def detect(self, content):
        return 'WEBVTT' in content

    def read(self, content, lang='en-US'):
        if type(content) != six.text_type:
            raise InvalidInputError('The content is not a unicode string.')

        caption_set = CaptionSet({lang: self._parse(content)})

        if caption_set.is_empty():
            raise CaptionReadNoCaptions("empty caption file")

        return caption_set

    def __parse_style(self, element):
        style = {}
        for k, v in list(element.items()):
            if k == '{tts}color':
                if re.match(r'#\d{6}\d{2}?', v):
                    style['color'] = v[0:7]
                else:
                    rgb_color = re.match(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', v.strip())
                    if rgb_color:
                        style['color'] = '#%02x%02x%02x' % (int(rgb_color.group(1)), int(rgb_color.group(2)), int(rgb_color.group(3)))
                    else:
                        c = self.__named_colors.get(v)
                        if c:
                            style['color'] = c
            elif k == '{tts}fontStyle':
                style['italic'] = v == 'italic'
            elif k == '{tts}fontWeight':
                style['bold'] = v == 'bold'
            elif k == '{tts}textDecoration':
                style['underline'] = v == 'underline'
        return style

    def __process_time(self, text):
        coefs = [3600, 60, 1]
        time = 0.0

        offset_match = re.match(r'(\d+)(:?\.\d+)?(h|m|s|ms|f|t)', text)
        if offset_match:
            return float(offset_match.group(1)) * {
                'h': 3600.0,
                'm': 60.0,
                's': 1.0,
                'ms': 0.001,
                'f': 1.0/(self.frameRate * self.frameRateMultiplier),
                't': 1.0/self.tickRate
            }.get(offset_match.group(2), 1.0)
        params = text.split(':')
        if len(params) == 1:
            return float(text)
        elif len(params) in (3, 4):
            if len(params) == 4:
                frames = params[3].split('.', 2)
                if len(frames) == 1:
                    params[2] = float(params[2]) + float(params[3]) / (self.frameRate * self.frameRateMultiplier)
                else:
                    params[2] = float(params[2]) + (
                        float(frames[0]) / self.frameRate +
                        float(frames[1]) / (self.frameRate * self.subFrameRate)
                    ) * self.frameRateMultiplier
                del params[3]
            for c, v in zip(coefs, params):
                time += c*float(v)
            return time
        return 0.0

    def _parse(self, content):
        # Normalize namespaces to a single alias. The draft namespace are still used in some file which makes searching for tags cumbersome
        namespace_clean = {
            'http://www.w3.org/2006/10/ttaf1': 'tt',
            'http://www.w3.org/2006/04/ttaf1': 'tt',
            'http://www.w3.org/ns/ttml': 'tt',
            'http://www.w3.org/2006/10/ttaf1#styling': 'tts',
            'http://www.w3.org/2006/04/ttaf1#styling': 'tts',
            'http://www.w3.org/ns/ttml#styling': 'tts',
            'http://www.w3.org/2006/10/ttaf1#parameter': 'ttp',
            'http://www.w3.org/2006/04/ttaf1#parameter': 'ttp',
            'http://www.w3.org/ns/ttml#parameter': 'ttp',
        }
        def normalize_qname(name):
            if name[0] == '{':
                (ns, name) = name[1:].split('}', 1)
                ns = namespace_clean.get(ns, ns)
                return '{%s}%s' % (ns, name)
            return name

        xml = ElementTree.fromstring(content)
        for element in xml.getiterator():
            element.tag = normalize_qname(element.tag)
            for k, v in list(element.items()):
                new_k = normalize_qname(k)
                if k != new_k:
                    del element.attrib[k]
                    element.attrib[new_k] = v

        # Define style aliases
        styles = {}
        regions = {}

        root = list(xml.getiterator())[0]
        if int(root.get('{ttp}tickRate', 0)) > 0:
            self.tickRate = int(root.get('{ttp}tickRate'))
        if int(root.get('{ttp}frameRate', 0)) > 0:
            self.frameRate = int(root.get('{ttp}frameRate'))
        if int(root.get('{ttp}subFrameRate', 0)) > 0:
            self.subFrameRate = int(root.get('{ttp}subFrameRate'))
        if root.get('{ttp}frameRateMultiplier'):
            num, denom = root.get('{ttp}frameRateMultiplier').split(' ')
            self.frameRateMultiplier = float(num) / float(denom)
        if not self.tickRate:
            self.tickRate = self.frameRate * self.subFrameRate * self.frameRateMultiplier

        # Build a cache for the default styles
        for style_tag in xml.findall('{tt}head/{tt}styling/{tt}style'):
            style = self.__parse_style(style_tag)
            styles[style_tag.get('{http://www.w3.org/XML/1998/namespace}id')] = style

        # Build a cache for the default style of the regions
        for region_tag in xml.findall('{tt}head/{tt}layout/{tt}region'):
            region = self.__parse_style(region_tag)
            regions[region_tag.get('{http://www.w3.org/XML/1998/namespace}id')] = region

        def compute_style_tree(element):
            style_ref = element.get('style')
            region_ref = element.get('region')

            style = {}
            if region_ref:
                style.update(regions[region_ref])
            if style_ref:
                style.update(styles[style_ref])
            style.update(self.__parse_style(element))

            return style

        def styleToHtml(tag, value):
            return {
                'bold': ('b', '<b>'),
                'italic': ('i', '<i>'),
                'underline': ('u', '<u>'),
                'color': ('font', '<font color="%s">' % value),
            }[tag]

        def openTags(output, style_pairs):
            (before, after) = style_pairs
            for tag in sorted(after.keys()):
                new_value = after[tag]
                old_value = before.get(tag, None)
                if old_value == None and new_value:
                    html = styleToHtml(tag, new_value)
                    output.openTag(html[0], html[1])
                elif old_value != new_value:
                    if new_value:
                        html = styleToHtml(tag, new_value)
                        output.openTag(html[0], html[1])
                    else:
                        output.closeTag(styleToHtml(tag, new_value)[0])

        def closeTags(output, style_pairs):
            (before, after) = style_pairs
            for tag in sorted(list(after.keys()), reverse=True):
                new_value = after[tag]
                old_value = before.get(tag, None)
                if old_value == None and new_value:
                    output.closeTag(styleToHtml(tag, new_value)[0])
                elif old_value != new_value:
                    if new_value:
                        output.closeTag(styleToHtml(tag, new_value)[0])
                    else:
                        html = styleToHtml(tag, before[tag])
                        output.openTag(html[0], html[1])

        # Store the subs in a list
        self.subs = []
        prev_sub = None
        content = None
        sub_grouping = False
        for sub in xml.findall('{tt}body/{tt}div/{tt}p'):
            begin = self.__process_time(sub.get('begin'))
            if not sub.get('end'):
                end = begin + self.__process_time(sub.get('dur'))
            else:
                end = self.__process_time(sub.get('end'))

            style_stack = [{'color': '#ffffff'}] # default color

            if not prev_sub or begin != prev_sub[0] or end != prev_sub[1]:
                content = RichText(self.rich_formatting)
                sub_grouping = False
            else:
                content.write("\n")
                sub_grouping = True

            def parseChildTree(element_list):
                for child in element_list:
                    style_stack.append(compute_style_tree(child))
                    openTags(content, style_stack[-2:])
                    if child.text and child.text.strip():
                        content.write(child.text.strip())
                    if child.tag == '{tt}br':
                        content.write("\n")
                    parseChildTree(list(child))
                    if child.tail and child.tail.strip():
                        content.write(child.tail.strip())
                    closeTags(content, style_stack[-2:])
                    style_stack.pop()

            parseChildTree([sub])

            # try to regroup subtitles if possible
            if sub_grouping:
                self.subs[-1][2] = six.text_type(content)
            else:
                prev_sub = [begin, end, six.text_type(content)]
                self.subs.append(prev_sub)

    # def _parse(self, lines):
    #     captions = CaptionList()
    #     start = None
    #     end = None
    #     nodes = []
    #     layout_info = None
    #     found_timing = False

    #     for i, line in enumerate(lines):

    #         if '-->' in line:
    #             found_timing = True
    #             timing_line = i
    #             last_start_time = captions[-1].start if captions else 0
    #             try:
    #                 start, end, layout_info = self._parse_timing_line(
    #                     line, last_start_time)
    #             except CaptionReadError as e:
    #                 new_message = '%s (line %d)' % (e.args[0], timing_line)
    #                 six.reraise(type(e), type(e)(new_message), sys.exc_info()[2])

    #         elif '' == line:
    #             if found_timing:
    #                 if not nodes:
    #                     raise CaptionReadSyntaxError(
    #                         'Cue without content. (line %d)' % timing_line)
    #                 else:
    #                     found_timing = False
    #                     caption = Caption(
    #                         start, end, nodes, layout_info=layout_info)
    #                     captions.append(caption)
    #                     nodes = []
    #         else:
    #             if found_timing:
    #                 if nodes:
    #                     nodes.append(CaptionNode.create_break())
    #                 nodes.append(CaptionNode.create_text(
    #                     self._decode(line)))
    #             else:
    #                 # it's a comment or some metadata; ignore it
    #                 pass

    #     # Add a last caption if there are remaining nodes
    #     if nodes:
    #         caption = Caption(start, end, nodes, layout_info=layout_info)
    #         captions.append(caption)

    #     return captions

class RichText:
    def __init__(self, use_html_tags):
        self.tag_stack = []
        self.opened_tags = set()
        self.output = []
        self.add_html_tags = use_html_tags

    def write(self, string):
        self.output.append(string)

    def openTag(self, tag_name, tag_html=None):
        if not tag_html:
            tag_html = '<%s>' % tag_name
        if tag_name not in self.opened_tags:
            self.tag_stack.append((tag_name, tag_html))
            self.opened_tags.add(tag_name)
            if not self.add_html_tags:
                self.output.append(' ')
            else:
                self.output.append(tag_html)

    def closeTag(self, tag):
        if not self.add_html_tags:
            return
        tag_html = '</%s>' % tag
        if tag in self.opened_tags:
            reopen_stack = []
            while self.tag_stack:
                tag_to_close = self.tag_stack.pop()
                if tag_to_close[0] == tag:
                    self.output.append(tag_html)
                    self.opened_tags.remove(tag)
                    break
                else:
                    reopen_stack += tag_to_close
            for tag_to_reopen in reopen_stack:
                self.output.append(tag_to_reopen[1])
                self.tag_stack.append(tag_to_reopen)

    def __str__(self):
        if not self.add_html_tags:
            return ''.join(self.output)

        closing_tags = []
        # Close all the tags still open
        for tag in self.tag_stack[::-1]:
            closing_tags.append('</%s>' % tag[0])
        return ''.join(self.output + closing_tags)