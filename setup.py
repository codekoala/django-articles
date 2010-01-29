from distutils.core import setup
from articles import __version__

setup(
    name='django-articles',
    version=__version__,
    description='Sophisticated blogging engine for Django-powered sites',
    long_description=open('README', 'r').read(),
    keywords='django, blog, blogging, engine',
    author='Josh VanderLinden',
    author_email='codekoala at gmail com',
    url='http://bitbucket.org/codekoala/django-articles/',
    license='BSD',
    package_dir={'articles': 'articles'},
    packages=['articles'],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Communications",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: News/Diary",
    ],
)
