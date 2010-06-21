from django.conf import settings
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.management.base import NoArgsCommand
from articles.models import Article
import simplejson as json
import re
import string
import sys
import urllib
import urllib2

NONPRINTABLE_RE = re.compile('[^%s]' % string.printable)

class Command(NoArgsCommand):
    help = """Imports any comments from django.contrib.comments into Disqus."""
    _forum_api_key = {}

    def handle_noargs(self, **opts):
        if hasattr(settings, 'DISQUS_USER_API_KEY'):
            self.forum_id = self.determine_forum()
            #print self.get_value_from_api('get_thread_list', {'forum_id': self.forum_id, 'limit': 1000})
            self.import_comments(self.forum_id)
        else:
            sys.exit('Please specify your DISQUS_USER_API_KEY in settings.py')

    def get_value_from_api(self, url, args={}, method='GET'):
        params = {
            'user_api_key': settings.DISQUS_USER_API_KEY,
            'api_version': '1.1',
        }
        params.update(args)

        # clean up the values
        for key, val in params.items():
            if isinstance(val, (str, unicode)):
                params[key] = NONPRINTABLE_RE.sub('', val)

        data = urllib.urlencode(params)
        additional = ''

        if method != 'POST':
            additional = '?%s' % data
            data = None

        url = 'http://disqus.com/api/%s/%s' % (url, additional)
        try:
            handle = urllib2.urlopen(url, data)
        except urllib2.HTTPError, err:
            print 'Failed to %s %s with args %s' % (method, url, args)
            return None
        else:
            json_obj = json.loads(handle.read())['message']
            handle.close()

            return json_obj

    def determine_forum(self):
        forums = self.get_value_from_api('get_forum_list')

        if len(forums) == 0:
            sys.exit('You have no forums on Disqus!')
        elif len(forums) == 1:
            forum_id = forums[0]['id']
        else:
            possible_ids = tuple(forum['id'] for forum in forums)
            forum_id = None
            while forum_id not in possible_ids:
                if forum_id is not None:
                    print 'Invalid forum ID.  Please try again.'

                print 'You have the following forums on Disqus:\n'

                for forum in forums:
                    print '\t%s. %s' % (forum['id'], forum['name'])

                forum_id = raw_input('\nInto which forum do you want to import your existing comments? ')

        return forum_id

    @property
    def forum_api_key(self):
        if not self._forum_api_key.get(self.forum_id, None):
            self._forum_api_key[self.forum_id] = self.get_value_from_api('get_forum_api_key', {'forum_id': self.forum_id})
        return self._forum_api_key[self.forum_id]

    def import_comments(self, forum_id):
        print 'Importing into forum %s' % self.forum_id

        article_ct = ContentType.objects.get_for_model(Article)
        for comment in Comment.objects.filter(content_type=article_ct):
            article = comment.content_object
            thread_obj = self.get_value_from_api('thread_by_identifier', {'identifier': article.id, 'title': article.title, 'forum_api_key': self.forum_api_key}, method='POST')

            thread = thread_obj['thread']
            if thread_obj['created']:
                # set the URL for this thread for good measure
                self.get_value_from_api('update_thread', {
                    'forum_api_key': self.forum_api_key,
                    'thread_id': thread['id'],
                    'title': article.title,
                    'url': 'http://%s%s' % (Site.objects.get_current().domain, article.get_absolute_url()),
                }, method='POST')
                print 'Created new thread for %s' % article.title

            # create the comment on disqus
            comment_obj = self.get_value_from_api('create_post', {
                'thread_id': thread['id'],
                'message': comment.comment,
                'author_name': comment.user_name,
                'author_email': comment.user_email,
                'forum_api_key': self.forum_api_key,
                'created_at': comment.submit_date.strftime('%Y-%m-%dT%H:%M'),
                'ip_address': comment.ip_address,
                'author_url': comment.user_url,
                'state': self.get_state(comment)
            }, method='POST')

            print 'Imported comment for %s by %s on %s' % (article, comment.user_name, comment.submit_date)

    def get_state(self, comment):
        """Determines a comment's state on Disqus based on its properties in Django"""

        if comment.is_public and not comment.is_removed:
            return 'approved'
        elif comment.is_public and comment.is_removed:
            return 'killed'
        elif not comment.is_public and not comment.is_removed:
            return 'unapproved'
        else:
            return 'spam'

