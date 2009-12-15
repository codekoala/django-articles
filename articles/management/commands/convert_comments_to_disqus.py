from django.conf import settings
from django.contrib.comments.models import Comment
from django.core.management.base import NoArgsCommand
from articles.models import Article
import simplejson as json
import sys
import urllib
import urllib2

class Command(NoArgsCommand):
    help = """Imports any comments from django.contrib.comments into Disqus."""

    def handle_noargs(self, **opts):
        if hasattr(settings, 'DISQUS_USER_API_KEY'):
            self.forum_id = self.determine_forum()
            print 'Importing into forum %s' % self.forum_id
            print self.get_value_from_api('get_thread_list', {'forum_id': self.forum_id, 'limit': 1000})

            for comment in Comment.objects.all():
                print comment.get_absolute_url()
        else:
            sys.exit('Please specify your DISQUS_USER_API_KEY in settings.py')

    def get_value_from_api(self, url, args={}, method='GET'):
        params = {
            'user_api_key': settings.DISQUS_USER_API_KEY,
            'api_version': '1.1',
        }
        params.update(args)

        data = urllib.urlencode(params)
        additional = ''

        if method != 'POST':
            additional = '?%s' % data
            data = None

        handle = urllib2.urlopen('http://disqus.com/api/%s%s' % (url, additional), data)
        json_obj = json.loads(handle.read())['message']
        handle.close()

        return json_obj

    def determine_forum(self):
        forums = self.get_value_from_api('get_forum_list')

        if len(forums) == 0:
            sys.exit('You have no forums on Disqus!')
        elif len(forums) == 11:
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
        if not hasattr(self, '_forum_api_key'):
            self._forum_api_key = self.get_value_from_api('get_forum_api_key', {'forum_id': self.forum_id})
        return self._forum_api_key

