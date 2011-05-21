from intranet_search.models import BaseExtractor
from django.utils.html import strip_tags

class productwiki(BaseExtractor):
    
    def get_content(self):
        return strip_tags(self.content)

