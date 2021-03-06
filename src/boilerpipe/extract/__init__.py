import jpype
import urllib2
import socket
import charade
# import requests
# import requests.packages
# from requests.packages.urllib3.exceptions import InsecureRequestWarning
import threading

socket.setdefaulttimeout(15)
lock = threading.Lock()

InputSource        = jpype.JClass('org.xml.sax.InputSource')
StringReader       = jpype.JClass('java.io.StringReader')
HTMLHighlighter    = jpype.JClass('de.l3s.boilerpipe.sax.HTMLHighlighter')
BoilerpipeSAXInput = jpype.JClass('de.l3s.boilerpipe.sax.BoilerpipeSAXInput')


class Extractor(object):
    """
    Extract text. Constructor takes 'extractor' as a keyword argument,
    being one of the boilerpipe extractors:
    - DefaultExtractor
    - ArticleExtractor
    - ArticleSentencesExtractor
    - KeepEverythingExtractor
    - KeepEverythingWithMinKWordsExtractor
    - LargestContentExtractor
    - NumWordsRulesExtractor
    - CanolaExtractor
    """
    extractor = None
    source    = None
    data      = None
    headers   = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'}
    # headers   = {'User-Agent': 'Mozilla/5.0'}

    def __init__(self, extractor='DefaultExtractor', **kwargs):
        if kwargs.get('url'):

            request     = urllib2.Request(kwargs['url'], headers=self.headers)

            # Version without headers
            # request     = urllib2.Request(kwargs['url'])

            connection  = urllib2.urlopen(request)

            self.data   = connection.read()

            encoding    = connection.headers['content-type'].lower().split('charset=')[-1]

            # Try requests
            # request     = requests.get(kwargs['url'], headers=self.headers, verify=False)

            # self.data   = request.text
            # encoding    = request.headers['content-type'].lower().split('charset=')[-1]

            if encoding.lower() == 'text/html':
                encoding = charade.detect(self.data)['encoding']

                try:

                    self.data = unicode(self.data, encoding, errors='replace')

                except LookupError as e:

                    print e
                    import ipdb; ipdb.set_trace()  # XXX BREAKPOINT

        elif kwargs.get('html'):
            self.data = kwargs['html']

            if not isinstance(self.data, unicode):
                self.data = unicode(self.data, charade.detect(self.data)['encoding'], errors='replace')
                import ipdb; ipdb.set_trace()  # XXX BREAKPOINT

        else:
            raise Exception('No text or url provided')

        try:
            # make it thread-safe
            if threading.activeCount() > 1:
                if jpype.isThreadAttachedToJVM() == False:
                    jpype.attachThreadToJVM()
            lock.acquire()

            self.extractor = jpype.JClass(
                "de.l3s.boilerpipe.extractors."+extractor).INSTANCE
        finally:
            lock.release()

        reader = StringReader(self.data)
        self.source = BoilerpipeSAXInput(InputSource(reader)).getTextDocument()
        self.extractor.process(self.source)

    def getText(self):
        return self.source.getContent()

    def getHTML(self):
        highlighter = HTMLHighlighter.newExtractingInstance()
        return highlighter.process(self.source, self.data)

    def getImages(self):
        extractor = jpype.JClass(
            "de.l3s.boilerpipe.sax.ImageExtractor").INSTANCE
        images = extractor.process(self.source, self.data)
        jpype.java.util.Collections.sort(images)
        images = [
            {
                'src': image.getSrc(),
                'width': image.getWidth(),
                'height': image.getHeight(),
                'alt': image.getAlt(),
                'area': image.getArea()
            } for image in images
        ]
        return images
