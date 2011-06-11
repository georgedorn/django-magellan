from magellan.models import BaseExtractor
from django.utils.html import strip_tags
from django.utils.encoding import force_unicode

class productwiki(BaseExtractor):
    
    def get_content(self):
        content = force_unicode(self.content)
        return strip_tags(content)

