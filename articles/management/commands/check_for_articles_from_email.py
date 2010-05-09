from django.conf import settings
from django.core.management.base import BaseCommand

from optparse import make_option

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

    def handle(self, *args, **options):
        protocol = options['protocol']
        host = options['host']
        port = options['port']
        keyfile = options['keyfile']
        certfile = options['certfile']
        username = options['username']
        password = options['password']
        ssl = options['ssl']

        params = (host, port, username, password, keyfile, certfile, ssl)
        if protocol == MB_IMAP4:
            messages = self.handle_imap4(*params)
        elif protocol == MB_POP3:
            messages = self.handle_pop3(*params)

        print messages

    def handle_imap4(self, host, port, username, password, keyfile, certfile, ssl):
        import imaplib

        messages = []
        if (keyfile and certfile) or ssl:
            M = imaplib.IMAP4_SSL(host, port, keyfile, certfile)
        else:
            M = imaplib.IMAP4(host, port)

        M.login(username, password)
        M.select()

        typ, data = M.search(None, 'ALL')

        for num in data[0].split():
            typ, data = M.fetch(num, '(RFC822)')
            messages.append((num, data))

        M.close()
        M.logout()

        return messages

    def handle_pop3(self, host, port, username, password, keyfile, certfile, ssl):
        import poplib

        messages = []
        if (keyfile and certfile) or ssl:
            M = poplib.POP3_SSL(host, port, keyfile, certfile)
        else:
            M = poplib.POP3(host, port)

        M.user(username)
        M.pass_(password)
        num = len(M.list()[1])
        for i in range(num):
            for msg in M.retr(i + 1)[1]:
                messages.append(msg)

        M.quit()

        return messages

