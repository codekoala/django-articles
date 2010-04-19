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

First of all, you must add this project to your list of ``INSTALLED_APPS`` in ``settings.py``:

{{{
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
}}}

Run ``manage.py syncdb``.  This creates a few tables in your database that are necessary for operation.

Next, set a couple of settings in your ``settings.py``:

 * ``DISQUS_USER_API_KEY``: Your user API key from Disqus.  This is free, and you can learn how to get it from  `Disqus's API Page <http://2ze.us/ME>`_ or you can try http://disqus.com/api/get_my_key/ when you're logged into Disqus.  You only need this one if you're going to be converting comments from ``django.contrib.comments`` to Disqus.
 * ``DISQUS_FORUM_SHORTNAME``: set this to ``True`` if you want to see markers on the map

Tag Auto-Completion
===================

If you would like to take advantage of the auto-completion feature for tags, copy the files from the ``articles/media`` directories into your static media directory.  ``django-articles`` expects to find each of those directories/files in your ``settings.MEDIA_URL`` directory--if this does not suit your needs, you may override the ``Media`` class of ``articles.forms.ArticleAdminForm`` with the appropriate paths.

Another assumption that is made by this feature is that the prefix you assign to your ``django-articles`` installation in your ``ROOT_URLCONF`` will be ``^blog/``.  For example:

 .. code-block:: python

    url(r'^blog', include('articles.urls')),

If this does not match your installation, all you need to change is the ``js/tag_autocomplete.js`` to reflect the proper path.

When that's done, you should be able to begin using ``django-articles``!

Good luck!  Please contact me with any questions or concerns you have with the project!

