"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import os
import inspect
#needed to find test PDF file
my_path = os.path.dirname(inspect.getabsfile( inspect.currentframe() ) )



from django.test import TestCase
from magellan.extractor import BaseExtractor, PdfFileReader




class TestBaseExtractor(TestCase):
    
    def setUp(self):
        self.html = """
        <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
        <html>
            <head>
                <meta http-equiv="Content-Type" content="text/html;charset=utf-8">
                <meta name="edit_on_doubleclick" content="/productwiki">
                <meta name="robots" content="index,nofollow">
                
            <title>MY TITLE</title>
            <script type="text/javascript" src="external.js"></script>
            <script type="text/javascript">
            <!--
                var test = "THIS IS A SCRIPT TAG";
            //-->
            </script>
        
            <link rel="stylesheet" type="text/css" charset="utf-8" media="all" href="external_stylesheet.css">
            <style>
                body {
                    background-image: "THIS_IS_A_STYLE_TAG.jpg";
                }
            </stile>
            </head>
        
            <body>
        
            <div id="header">
            <form id="searchform" method="get" action="searchform">
            <div>
                <input id="titlesearch" name="titlesearch" type="submit" value="Titles" alt="Search Titles">
            </div>
            </form>
        
            <ul id="pagelocation">
            <li><a class="relative_link" href="/link" title="Link Title">Relative Link</a></li>
            <li><a class="absolute_link" href="http://myserver.com/link" title="Absolute Link Title">Absolute Link</a></li>
            <li><a class="offsite_link" href="http://notmyserver.com/link" title="Offsite Link Title">Offsite Link</a></li>
            </ul>
        
            </div>
            <h1 id="H1Content">THIS IS A H1 HEADER</h1>
            <p>Content in a paragraph</p>
            <h2 id="H2Content">THIS IS A H2 HEADER</h2>
            <span>Content In A Span</span>
        
        
            </body>
        </html>
        """
        
        
        
    def test_extractor(self):
        extractor = BaseExtractor(self.html)
        self.assertEqual(extractor.get_title(), u'MY TITLE')
        
        expected_content = [
                            u'MY TITLE',
                            u'Relative Link',
                            u'Absolute Link',
                            u'Offsite Link',
                            u'THIS IS A H1 HEADER',
                            u'Content in a paragraph',
                            u'THIS IS A H2 HEADER',
                            u'Content In A Span',
                            ]
        content = extractor.get_content()
        for c in expected_content:
            self.assertTrue(c.lower() in content.lower())
        
        expected_headings = [
                            u'THIS IS A H1 HEADER',
                            u'THIS IS A H2 HEADER',
                             ]
        
        headings = extractor.get_headings()
        for h in expected_headings:
            self.assertTrue(h.lower() in headings.lower())
            
        unexpected_content = [  
                              'meta',
                              'Content-Type',
                              'stylesheet',
                              'script',
                              'style',
                              'relative_link',
                              'absolute_link',
                              'offsite_link',
                              'pagelocation',
                              'THIS IS A SCRIPT TAG',
                              'THIS_IS_A_STYLE_TAG'
                              
                              ]

        for u in unexpected_content:
            self.assertFalse(u in content)
            self.assertFalse(u in headings)
            
            
    def test_pdf_extraction(self):
        if not PdfFileReader:
            self.skipTest("pyPdf is not installed")
        
        pdf = open(os.path.join(my_path, 'testpdf.pdf'))
        extractor = BaseExtractor(pdf.read())
        self.assertEqual(extractor.get_title(), u'This is a test PDF file')

        expected_content = [
                            'universal file format',
                            'fonts, formatting, colours and graphics',
                            'regardless of the application and platform'
                            ]
        
        content = extractor.get_content()
        for c in expected_content:
            self.assertTrue(c in content)
        


