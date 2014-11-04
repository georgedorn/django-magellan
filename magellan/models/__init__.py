#import all models from plugins here so django can find them.
#@todo: do this dynamically, using settings file and validating against
#installed plugins.
#In theory, user should be able to write their own, put it anywhere on the
#pythonpath, and tell magellan about it.

from django.conf import settings
from django.db import models
#helpful functions and generic models also go here.

MULTIUSER = getattr(settings, 'MAGELLAN_MULTI_USER_MODE', True)
if MULTIUSER:
    from django.contrib.auth import get_user_model
    User = get_user_model()


class BaseContentSubscription(models.Model):
    """
    Common attributes all content subscriptions are expected to have.
    """
    active = models.BooleanField(default=True)
    name = models.CharField(max_length=255,
        help_text="Content's source, e.g. a tumblr user or website name.")

    created_at = models.DateTimeField(auto_add_now=True)
    last_run = models.DateTimeField(null=True)

    if MULTIUSER:
        user = models.ForeignKey(User)
    else:
        user = None  # so we can test self.user

    class Meta:
        abstract = True

    def get_content(self):
        """
        Every content subscription model must implement this method.
        """
        raise NotImplementedError


#import models here
from .generic import GenericWebsiteSubscription
