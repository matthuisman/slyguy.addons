from copy import deepcopy
import six

from .base import (
    BaseReader, BaseWriter, CaptionSet, CaptionList, Caption, CaptionNode)
from .exceptions import CaptionReadNoCaptions, InvalidInputError


class SRTReader(BaseReader):
    def detect(self, content):
        lines = content.splitlines()
        if lines[0].isdigit() and '-->' in lines[1]:
            return True
        else:
            return False

    def read(self, content, lang='en-US'):
        if type(content) != six.text_type:
            raise InvalidInputError('The content is not a unicode string.')

        lines = content.splitlines()
        start_line = 0
        captions = CaptionList()

        while start_line < len(lines):
            if not lines[start_line].isdigit():
                break

            end_line = self._find_text_line(start_line, lines)

            timing = lines[start_line + 1].split('-->')
            start = self._srttomicro(timing[0].strip(' \r\n'))
            end = self._srttomicro(timing[1].strip(' \r\n'))

            nodes = []

            for line in lines[start_line + 2:end_line - 1]:
                # skip extra blank lines
                if not nodes or line != '':
                    nodes.append(CaptionNode.create_text(line))
                    nodes.append(CaptionNode.create_break())

            if len(nodes):
                # remove last line break from end of caption list
                nodes.pop()
                caption = Caption(start, end, nodes)
                captions.append(caption)

            start_line = end_line

        caption_set = CaptionSet({lang: captions})

        if caption_set.is_empty():
            raise CaptionReadNoCaptions("empty caption file")

        return caption_set

    def _srttomicro(self, stamp):
        timesplit = stamp.split(':')
        if ',' not in timesplit[2]:
            timesplit[2] += ',000'
        secsplit = timesplit[2].split(',')
        microseconds = (int(timesplit[0]) * 3600000000 +
                        int(timesplit[1]) * 60000000 +
                        int(secsplit[0]) * 1000000 +
                        int(secsplit[1]) * 1000)

        return microseconds

    def _find_text_line(self, start_line, lines):
        end_line = start_line

        found = False
        while end_line < len(lines):
            if lines[end_line].strip() == "":
                found = True
            elif found is True:
                end_line -= 1
                break
            end_line += 1

        return end_line + 1


class SRTWriter(BaseWriter):
    def write(self, caption_set):
        caption_set = deepcopy(caption_set)

        srt_captions = []

        for lang in caption_set.get_languages():
            srt_captions.append(
                self._recreate_lang(caption_set.get_captions(lang))
            )

        caption_content = 'MULTI-LANGUAGE SRT\n'.join(srt_captions)
        return caption_content

    def _recreate_lang(self, captions):
        srt = ''
        count = 1

        for caption in captions:
            srt += '%s\n' % count

            start = caption.format_start(msec_separator=',')
            end = caption.format_end(msec_separator=',')
            timestamp = '%s --> %s\n' % (start[:12], end[:12])

            srt += timestamp.replace('.', ',')

            new_content = ''
            for node in caption.nodes:
                new_content = self._recreate_line(new_content, node)

            # Eliminate excessive line breaks
            new_content = new_content.strip()
            while '\n\n' in new_content:
                new_content = new_content.replace('\n\n', '\n')

            srt += "%s%s" % (new_content, '\n\n')
            count += 1

        return srt[:-1]  # remove unwanted newline at end of file

    def _recreate_line(self, srt, line):
        if line.type_ == CaptionNode.TEXT:
            return srt + '%s ' % line.content
        elif line.type_ == CaptionNode.BREAK:
            return srt + '\n'
        else:
            return srt
