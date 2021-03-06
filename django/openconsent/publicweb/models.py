#pylint: disable-msg=E1102

from django.db import models
from django.utils.html import strip_tags
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from tagging.fields import TagField

from emails import OpenConsentEmailMessage
import re

# Ideally django-tinymce should be patched
# http://south.aeracode.org/wiki/MyFieldsDontWork
# http://code.google.com/p/django-tinymce/issues/detail?id=80
# TODO: Status codes could possibly be harvested off into its
# own class with accessor methods to return values.

from south.modelsinspector import add_introspection_rules
import datetime

add_introspection_rules([], ["^tagging\.fields\.TagField"])

class Decision(models.Model):

    TAGS_HELP_FIELD_TEXT = "Enter a list of tags separated by spaces."
    PROPOSAL_STATUS = 0
    DECISION_STATUS = 1
    ARCHIVED_STATUS = 2

    STATUS_CHOICES = (
                  (PROPOSAL_STATUS, _('proposal')),
                  (DECISION_STATUS, _('decision')),
                  (ARCHIVED_STATUS, _('archived')),
                  )

    DEFAULT_SIZE = 140

    #User entered fields
    description = models.TextField(verbose_name=_('Description'))
    decided_date = models.DateField(null=True, blank=True,
        verbose_name=_('Decided Date'))
    effective_date = models.DateField(null=True, blank=True,
        verbose_name=_('Effective Date'))
    review_date = models.DateField(null=True, blank=True,
        verbose_name=_('Review Date'))
    expiry_date = models.DateField(null=True, blank=True,
        verbose_name=_('Expiry Date'))
    deadline = models.DateField(null=True, blank=True,
        verbose_name=_('Deadline'))
    archived_date = models.DateField(null=True, blank=True,
        verbose_name=_('Archived Date'))
    budget = models.CharField(blank=True, max_length=255,
        verbose_name=_('Budget/Resources'))
    people = models.CharField(blank=True, max_length=255,
        verbose_name=_('People'))
    author = models.ForeignKey(User, blank=True, null=True, editable=False, related_name='open_consent_author')
    watchers = models.ManyToManyField(User, blank=True, editable=False)
    status = models.IntegerField(choices=STATUS_CHOICES,
                                 default=PROPOSAL_STATUS,
                                 verbose_name=_('Status'))
    tags = TagField(null=True, blank=True, editable=True, 
                    help_text=TAGS_HELP_FIELD_TEXT)

    #Autocompleted fields
    #should use editable=False?
    excerpt = models.CharField(verbose_name=_('Excerpt'), max_length=255, blank=True)
    created_date = models.DateField(null=True, blank=True, editable=False,
        verbose_name=_('Created Date'))

    #methods
    def is_watched(self, user):
        return user in self.watchers.all()
                        
    def add_watcher(self, user):
        if user not in self.watchers.all():
            self.watchers.add(user)
    
    def remove_watcher(self, user):
        if user in self.watchers.all():
            self.watchers.remove(user)
    
    def status_text(self):
        return self.STATUS_CHOICES[self.status][1]
    
    def unresolvedfeedback(self):
        answer = _("No")
        linked_feedback = self.feedback_set.all()
        for thisfeedback in linked_feedback:
            if (not thisfeedback.resolved):
                answer = _("Yes")
                break
            
        return answer

    unresolvedfeedback.short_description = _("Unresolved Feedback")

    def feedbackcount(self):
        return self.feedback_set.all().count()    

    feedbackcount.short_description = _("Feedback")

    def _get_excerpt(self):
        description = strip_tags(self.description)
        match = re.search("\.|\\r|\\n", description)
        position = self.DEFAULT_SIZE
        if match:
            start = match.start()
            if start < position:
                position = start
        return description[:position]
    
    def __unicode__(self):
        return self.excerpt

    @classmethod
    def get_fields(cls):
        return cls._meta.fields
    
    @models.permalink
    def get_absolute_url(self):
        return ('publicweb_decision_edit', (), {'decision_id':self.id})

    def save(self, author, *args, **kwargs):
        self.excerpt = self._get_excerpt()        
        self.author = author

        if not self.id:
            self.created_date = datetime.date.today()        

        #-----------------------------------#
        # This is email stuff. Would be good
        # if it could be hived off to a signal
        #-  --------------------------------#
        # ||
        # \/
        #record newness before saving
        if self.id:
            typ = 'status_change'
            old = Decision.objects.get(id=self.id)
            if old.status != self.status:
                typ = 'status_change'
            else:
                typ = 'content_change'
        else:
            old = None
            typ = 'new'
                    
        super(Decision, self).save(*args, **kwargs)

        email = OpenConsentEmailMessage(typ = typ,
                                        obj = self,
                                        old_obj = old)  

        email.send()
        
class Feedback(models.Model):

    QUESTION_STATUS = 0
    DANGER_STATUS = 1
    SIGNIFICANT_CONCERNS_STATUS = 2
    CONSENT_STATUS = 3
    HAPPY_STATUS = 4
    DELIGHTED_STATUS = 5

    RATING_CHOICES = ( 
                  (QUESTION_STATUS, _('Question')),
                  (DANGER_STATUS, _('Danger')),
                  (SIGNIFICANT_CONCERNS_STATUS, _('Concerns')),
                  (CONSENT_STATUS, _('Consent')),
                  )
    
    description = models.TextField(verbose_name=_('Description'), null=True, blank=True)    
    decision = models.ForeignKey('Decision', verbose_name=_('Decision'))
    resolved = models.BooleanField(verbose_name=_('Resolved'))
    rating = models.IntegerField(choices=RATING_CHOICES,
                                 verbose_name=_('Rating'),
                                 null=True, 
                                 blank=True )
