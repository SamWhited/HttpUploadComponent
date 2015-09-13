import os

from setuptools import setup
from httpupload import VERSION

def readme():
    with open(os.path.join(os.path.dirname(__file__), 'README.md')) as f:
        return f.read()

setup(
    name='httpuploadcomponent',
    version=VERSION,
    description='XMPP HTTP file upload component',
    author='Daniel Gultch',
    author_email='',
    url='https://github.com/siacs/HttpUploadComponent',
    packages=['httpupload'],
    keywords=['xmpp'],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: System Administrators",
        "Operating System :: OS Independent",
        "Topic :: Communications :: File Sharing",
        "Topic :: Communications :: Chat :: XMPP"
    ],
    long_description=readme(),
    require=[
        'sleekxmpp'
    ],
    tests_require=[
        'pytest >= 3.7.1',
        'tox >= 2.0.1',
        'mock >= 1.0.1'
    ],
)
