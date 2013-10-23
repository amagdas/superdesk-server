
import os
import unittest

from .nitf import parse


class TestCase(unittest.TestCase):

    def setUp(self):
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.join(dirname, 'fixtures', 'aap.xml')
        with open(fixture) as f:
            self.nitf = f.read()
            self.item = parse(self.nitf)

    def test_headline(self):
        self.assertEquals(self.item.get('headline'), "The main stories on today's 1900 ABC TV news")

    def test_guid(self):
        self.assertEquals(self.item.get('guid'), 'AAP.115314987.5417374')

    def test_item_class(self):
        self.assertEquals(self.item.get('itemClass'), 'icls:text')

    def test_urgency(self):
        self.assertEquals(self.item.get('urgency'), 5)

    def test_copyright(self):
        self.assertEquals(self.item.get('copyrightHolder'), 'Australian Associated Press')

    def test_dates(self):
        self.assertEquals(self.item.get('firstCreated').isoformat(), '2013-10-20T19:27:51')
        self.assertEquals(self.item.get('versionCreated').isoformat(), '2013-10-20T19:27:51')

    def test_content(self):
        self.assertEquals(len(self.item.get('contents')), 1)
        content = self.item.get('contents')[0]
        self.assertEquals(content.get('contenttype'), 'application/xhtml+html')
        text = "<p>   1A) More extreme weather forecast over the next few days the <br />fire situation is likely"
        self.assertIn(text, content.get('content'))

if __name__ == '__main__':
    unittest.main()