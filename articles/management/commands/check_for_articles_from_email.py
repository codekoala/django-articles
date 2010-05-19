from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _

from datetime import datetime
from email.parser import FeedParser
from email.utils import parseaddr, parsedate
from optparse import make_option
import socket
import sys
import time

from django.db.models import connection
from articles.models import Article, MARKUP_HTML, MARKUP_MARKDOWN, MARKUP_REST, MARKUP_TEXTILE

MB_IMAP4 = 'IMAP4'
MB_POP3 = 'POP3'

class Command(BaseCommand):
    help = "Checks special e-mail inboxes for emails that should be posted as articles"

    option_list = BaseCommand.option_list + (
        make_option('--protocol', dest='protocol', default=MB_IMAP4, help='Protocol to use to check for email'),
        make_option('--host', dest='host', default=None),
        make_option('--port', dest='port', default=None),
        make_option('--keyfile', dest='keyfile', default=None),
        make_option('--certfile', dest='certfile', default=None),
        make_option('--username', dest='username', default=None),
        make_option('--password', dest='password', default=None),
        make_option('--ssl', action='store_true', dest='ssl', default=False),
    )

    def log(self, message, level=2):
        if self.verbosity >= level:
            print message

    def handle(self, *args, **options):
        """Main entry point for the command"""

        # retrieve configuration options--give precedence to CLI parameters
        self.from_email = getattr(settings, 'ARTICLES_FROM_EMAIL', {})
        s = lambda k, d: self.from_email.get(k, d)

        protocol = options['protocol'] or s('protocol', MB_IMAP4)
        host = options['host'] or s('host', 'mail.yourhost.com')
        port = options['port'] or s('port', None)
        keyfile = options['keyfile'] or s('keyfile', None)
        certfile = options['certfile'] or s('certfile', None)
        username = options['username'] or s('user', None)
        password = options['password'] or s('password', None)
        ssl = options['ssl'] or s('ssl', False)

        self.verbosity = int(options.get('verbosity', 1))

        # try to guess if we don't have a port
        if port is None:
            if protocol == MB_IMAP4:
                port = 993 if ssl else 143
            elif protocol == MB_POP3:
                port = 995 if ssl else 110

        handle = None
        try:
            handle = self.get_mail_handle(protocol, host, port, username, password, keyfile, certfile, ssl)
            messages = self.fetch_messages(protocol, handle)
            created = self.create_articles(messages)
            self.delete_messages(protocol, handle, created)
        finally:
            if handle:
                if protocol == MB_IMAP4:
                    # close the IMAP4 handle
                    handle.close()
                    handle.logout()

                elif protocol == MB_POP3:
                    # close the POP3 handle
                    handle.quit()

    def get_mail_handle(self, protocol, *args, **kwargs):
        """
        Returns a handle to either an IMAP4 or POP3 mailbox (or None if
        something weird happens)
        """

        self.log('Creating handle to mail server')

        if protocol == MB_IMAP4:
            return self.get_imap4_handle(*args, **kwargs)
        else:
            return self.get_pop3_handle(*args, **kwargs)

        return None

    def get_imap4_handle(self, host, port, username, password, keyfile, certfile, ssl):
        """Connects to and authenticates with an IMAP4 mail server"""

        import imaplib

        try:
            if (keyfile and certfile) or ssl:
                self.log('Creating SSL IMAP4 handle')
                M = imaplib.IMAP4_SSL(host, port, keyfile, certfile)
            else:
                self.log('Creating non-SSL IMAP4 handle')
                M = imaplib.IMAP4(host, port)
        except socket.error, err:
            raise
        else:
            self.log('Authenticating with mail server')
            M.login(username, password)
            M.select()
            return M

    def get_pop3_handle(self, host, port, username, password, keyfile, certfile, ssl):
        """Connects to and authenticates with a POP3 mail server"""

        import poplib

        try:
            if (keyfile and certfile) or ssl:
                self.log('Creating SSL POP3 handle')
                M = poplib.POP3_SSL(host, port, keyfile, certfile)
            else:
                self.log('Creating non-SSL POP3 handle')
                M = poplib.POP3(host, port)
        except socket.error, err:
            raise
        else:
            self.log('Authenticating with mail server')
            M.user(username)
            M.pass_(password)
            return M

    def fetch_messages(self, protocol, handle):
        """Fetches email messages from a server pased on the protocol"""

        self.log('Fetching new messages')
        try:
            if protocol == MB_IMAP4:
                messages = self.handle_imap4_fetch(handle)
            elif protocol == MB_POP3:
                messages = self.handle_pop3_fetch(handle)
        except socket.error, err:
            sys.exit('Error retrieving mail: %s' % (err,))
        else:
            parsed = {}

            self.log('Parsing email messages')

            # parse each email message
            for num, mess in messages.iteritems():
                fp = FeedParser()
                fp.feed(mess)
                parsed[num] = fp.close()

            return parsed

    def delete_messages(self, protocol, handle, created):
        """Deletes the messages we just created articles for"""

        self.log('Deleting consumed emails: %s' % (created,))
        try:
            if protocol == MB_IMAP4:
                self.handle_imap4_delete(handle, created)
            elif protocol == MB_POP3:
                self.handle_pop3_delete(handle, created)
        except socket.error, err:
            sys.exit('Error deleting mail: %s' % (err,))

    def handle_imap4_fetch(self, handle):
        """Fetches messages from an IMAP server"""

        messages = {}

        self.log('Fetching from IMAP4')
        typ, data = handle.search(None, 'ALL')
        for num in data[0].split():
            typ, data = handle.fetch(num, '(RFC822)')
            messages[num] = data[0][1]

        return messages

    def handle_pop3_fetch(self, handle):
        """Fetches messages from a POP3 server"""

        messages = {}

        self.log('Fetching from POP3')
        num = len(handle.list()[1])
        for i in range(num):
            messages[num] = '\n'.join([msg for msg in handle.retr(i + 1)[1]])

        return messages

    def handle_imap4_delete(self, handle, created):
        """Deletes the messages we just posted as articles"""

        self.log('Deleting from IMAP4')
        for num in created:
            handle.store(num, '+FLAGS', '\\Deleted')

        handle.expunge()

    def handle_pop3_delete(self, handle, created):
        """Deletes the messages we just posted as articles"""

        self.log('Deleting from POP3')
        map(handle.dele, created)

    def get_email_content(self, email):
        """Attempts to extract an email's content"""

        if email.is_multipart():
            self.log('Extracting email contents from multipart message')
            for pl in email.get_payload():
                if pl.get_content_type() in ('text/plain', 'text/html'):
                    return pl.get_payload()
        else:
            return email.get_payload()

        return None

    def get_unique_slug(self, slug):
        """Iterates until a unique slug is found"""

        orig_slug = slug
        year = datetime.now().year
        counter = 1

        while True:
            not_unique = Article.objects.filter(publish_date__year=year, slug=slug)
            if len(not_unique) == 0:
                return slug

            self.log('Found duplicate slug for year %s: %s. Trying again.' % (year, slug))
            slug = '%s-%s' % (orig_slug, counter)
            counter += 1

    def create_articles(self, emails):
        """Attempts to post new articles based on parsed email messages"""

        self.log('Creating article objects')
        created = []
        site = Site.objects.get_current()

        # make sure we have a valid default markup
        ack = self.from_email.get('acknowledge', False)
        autopost = self.from_email.get('autopost', False)
        markup = self.from_email.get('markup', MARKUP_HTML)
        if markup not in (MARKUP_HTML, MARKUP_MARKDOWN, MARKUP_REST, MARKUP_TEXTILE):
            markup = MARKUP_HTML

        for num, email in emails.iteritems():

            name, sender = parseaddr(email['From'])

            try:
                author = User.objects.get(email=sender, is_active=True)
            except User.DoesNotExist:
                # unauthorized sender
                self.log('Not processing message from unauthorized sender.', 0)
                continue

            # get the attributes for the article
            title = email.get('Subject', '--- article from email ---')
            slug = self.get_unique_slug(slugify(title))

            content = self.get_email_content(email)
            try:
                # try to grab the timestamp from the email message
                publish_date = datetime.fromtimestamp(time.mktime(parsedate(email['Date'])))
            except StandardError, err:
                self.log("An error occured when I tried to convert the email's timestamp into a datetime object: %s" % (err,))
                publish_date = datetime.now()

            # post the article
            article = Article(
                author=author,
                title=title,
                slug=slug,
                content=content,
                markup=markup,
                publish_date=publish_date,
                is_active=autopost,
            )

            try:
                article.save()
            except StandardError, err:
                # log it and move on to the next message
                self.log('Error creating article: %s' % (err,), 0)
                continue
            else:
                created.append(num)

            if ack:
                # notify the user when the article is posted
                subject = u'%s: %s' % (_("Article Posted"), title)
                message = _("""Your email (%(title)s) has been posted as an article on %(site_name)s.

    http://%(domain)s%(article_url)s""") % {
                    'title': title,
                    'site_name': site.name,
                    'domain': site.domain,
                    'article_url': article.get_absolute_url(),
                }

                self.log('Sending acknowledgment email to %s' % (author.email,))
                author.email_user(subject, message)

        return created

