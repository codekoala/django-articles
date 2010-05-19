django-articles is the blog engine that I use on codekoala.com

Features
========

* Tags for articles, with a tag cloud template tag
* Auto-completion for tags in the Django admin
* Ability to post in the future
* Article expiration facilities
* Allows articles to be written in plain text/HTML or using Markdown, ReStructured Text, or Textile markup
* Related articles
* Follow-up articles
* Disqus comments
* Article archive, with pagination
* Internationalization-ready
* Detects links in articles and creates a per-article index for you
* Word count
* RSS feeds for the latest articles
* RSS feeds for the latest articles by tag

Requirements
============

``django-articles`` wants a modern version of Django--something after 1.1.  It used to rely on ``django.contrib.comments`` for commenting needs, but I recently switched to `Disqus <http://www.disqus.com/>`_.  Included herein is a management command to convert ``django.contrib.comments`` comments to Disqus.

This project also expects ``django.contrib.sites``, ``django.contrib.admin``, ``django.contrib.markup``, ``django.contrib.auth``, ``django.contrib.humanize``, and ``django.contrib.syndication`` to be properly installed.

Installation
============

Download ``django-articles`` using *one* of the following methods:

Checkout from Mercurial
-----------------------

Use one of the following commands::

    hg clone http://django-articles.googlecode.com/hg/ django-articles
    hg clone http://bitbucket.org/codekoala/django-articles/

The CheeseShop
--------------

Use one of the following commands::

    pip install django-articles
    easy_install django-articles

Configuration
=============

First of all, you must add this project to your list of ``INSTALLED_APPS`` in ``settings.py``::

    INSTALLED_APPS = (
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.humanize',
        'django.contrib.markup',
        'django.contrib.sessions',
        'django.contrib.sites',
        'django.contrib.syndication',
        ...
        'articles',
        ...
    )

Run ``manage.py syncdb``.  This creates a few tables in your database that are necessary for operation.

Next, set a couple of settings in your ``settings.py``:

 * ``DISQUS_USER_API_KEY``: Your user API key from Disqus.  This is free, and you can learn how to get it from  `Disqus's API Page <http://2ze.us/ME>`_ or you can try http://disqus.com/api/get_my_key/ when you're logged into Disqus.  You only need this one if you're going to be converting comments from ``django.contrib.comments`` to Disqus.
 * ``DISQUS_FORUM_SHORTNAME``: set this to ``True`` if you want to see markers on the map

Template Integration
====================

There are several template blocks that ``django-articles`` expects your ``base.html`` file to contain:

* ``title``
* ``meta-keywords``
* ``meta-description``
* ``extra-head``
* ``content``
* ``footer``

Tag Auto-Completion
===================

If you would like to take advantage of the auto-completion feature for tags, copy the files from the ``articles/media`` directories into your static media directory.  ``django-articles`` expects to find each of those directories/files in your ``settings.MEDIA_URL`` directory--if this does not suit your needs, you may override the ``Media`` class of ``articles.forms.ArticleAdminForm`` with the appropriate paths.

Another assumption that is made by this feature is that the prefix you assign to your ``django-articles`` installation in your ``ROOT_URLCONF`` will be ``^blog/``.  For example::

    url(r'^blog', include('articles.urls')),

If this does not match your installation, all you need to change is the ``js/tag_autocomplete.js`` to reflect the proper path.

When that's done, you should be able to begin using ``django-articles``!

Articles From Email
===================

.. versionadded:: 0.9.1
   Articles from email

I've been working on making it possible for ``django-articles`` to post articles that you email to a special mailbox.  This seems to be working on the most basic levels right now.  It's not been tested in very many scenarios, and I would appreciate it if you could post problems with it in the ticket tracker at http://bitbucket.org/codekoala/django-articles/ so we can make it work really well.

Things to keep in mind:

* Any **active** user who is a ``django.contrib.auth.models.User`` and has an email address associated with their user information is a valid sender for articles from email.  This is how the author of an article is determined.
* Only the following fields are currently populated by the articles from email feature:

    * author
    * title
    * slug (uniqueness is handled)
    * content
    * markup
    * publish_date
    * is_active

  Any and all other attributes about an article must be configured later on using the standard mechanisms (aka the Django admin).
* There is a new management command to handle all of the magic for this feature: ``check_for_articles_from_email``.  This command is intended to be called either manually or via external scheduling utilities (like ``cron``)
* Email messages **are deleted** after they are turned into articles.  This means that you should probably have a *special mailbox dedicated to django-article and articles from email*.  However, only emails whose sender matches the email address of an active user are deleted (as described above).
* Attachments are currently not bothered with.  Don't worry, they will be :D

Configuration
-------------

There are several new variables that you can configure in your ``settings.py`` to enable articles from email:

* ``ARTICLES_EMAIL_PROTOCOL`` - Either ``IMAP4`` or ``POP3``.  *Default*: ``IMAP4``
* ``ARTICLES_EMAIL_HOST`` - The mail server. *Example*: mail.yourserver.com
* ``ARTICLES_EMAIL_PORT`` - The port to use to connect to your mail server
* ``ARTICLES_EMAIL_KEYFILE`` - The keyfile used to access your mail server *untested*
* ``ARTICLES_EMAIL_CERTFILE`` - The certfile used to access your mail server *untested*
* ``ARTICLES_EMAIL_USER`` - The username used to access your mailbox
* ``ARTICLES_EMAIL_PASSWORD`` - The password associated with the user to access your mailbox
* ``ARTICLES_EMAIL_SSL`` - Whether or not to connect to the mail server using SSL.  *Default*: ``False``
* ``ARTICLES_EMAIL_AUTOPOST`` - Whether or not to automatically post articles that are created from email messages.  If this is ``False``, the articles will be marked as inactive and you must manually make them active. *Default*: ``False``
* ``ARTICLES_EMAIL_MARKUP`` - The default markup language to use for articles from email.  Options include:

    * ``h`` for HTML/plain text
    * ``m`` for Markdown
    * ``r`` for reStructuredText
    * ``t`` for Textile

  *Default*: ``h``

* ``ARTICLES_EMAIL_ACK`` - Whether or not to email out an acknowledgment message when articles are created from email.  *Default*: ``False``

Good luck!  Please contact me with any questions or concerns you have with the project!

