================================
BloxOne DDI DNS Context Switcher
================================

| Version: 0.2.0
| Author: Chris Marrison
| Email: chris@infoblox.com

Description
-----------

This script is designed to provide a simple way to manage the context of DNS 
records and changes for DR (or other) purposes. This is based on automating
the identification of applications using Tags and the value of canonical names
used by the CNAME records used for the applications.

The only state maintained in the configuration is the list of services
to enable you to query or change the state of *all* services. Otherwise the
script is essentially stateless, with all data maintained within BloxOne 
itself using Tag data.


Prerequisites
-------------

Python 3.7 or above
bloxone python module


Installing Python
~~~~~~~~~~~~~~~~~

You can install the latest version of Python 3.x by downloading the appropriate
installer for your system from `python.org <https://python.org>`_.

.. note::

  If you are running MacOS Catalina (or later) Python 3 comes pre-installed.
  Previous versions only come with Python 2.x by default and you will therefore
  need to install Python 3 as above or via Homebrew, Ports, etc.

  By default the python command points to Python 2.x, you can check this using 
  the command::

    $ python -V

  To specifically run Python 3, use the command::

    $ python3


.. important::

  Mac users will need the xcode command line utilities installed to use pip3,
  etc. If you need to install these use the command::

    $ xcode-select --install

.. note::

  If you are installing Python on Windows, be sure to check the box to have 
  Python added to your PATH if the installer offers such an option 
  (it's normally off by default).


Modules
~~~~~~~

Non-standard modules:

    - bloxone 0.8.5+
    - PyYAML

These are specified in the *requirements.txt* file.

The latest version of the bloxone module is available on PyPI and can simply be
installed using::

    pip3 install bloxone --user

To upgrade to the latest version::

    pip3 install bloxone --user --upgrade

Complete list of modules::

    import bloxone
    import os
    import logging
    import json
    import yaml
    import argparse


Installation
------------

The simplest way to install and maintain the tools is to clone this 
repository::

    % git clone https://github.com/Infoblox_WWFO/b1ddi_dns_context_switcher


Alternative you can download as a Zip file.


Basic Configuration
-------------------

There are two simple configuration files the *bloxone.ini* file and the 
*services.yml* file. Samples of which are provided.


bloxone.ini
~~~~~~~~~~~

The *bloxone.ini* file is used by the bloxone module to access the bloxone
API. A sample inifile for the bloxone module is shared as *bloxone.ini* and 
follows the following format provided below::

    [BloxOne]
    url = 'https://csp.infoblox.com'
    api_version = 'v1'
    api_key = '<you API Key here>'

Simply create and add your API Key, and this is ready for the bloxone
module used by the automation demo script. This inifile should be kept 
in a safe area of your filesystem and can be referenced with full path
in the demo.ini file.


services.yml YAML file
~~~~~~~~~~~~~~~~~~~~~~

The *services.yml* file allows you to configure the list of services that you
wish to manage with the script.

The format of the *services.yml* file is shown in the sample below::

    ---
    applications:
        - intranet
        - mail
        - www

    states:
        normal: 'Running in normal context'
        backup: 'Running in BACKUP mode'
        manual: 'Manual context detected'
        Not_configured: 'Missing Tags'


The applications listed must match the names used in the *Services* tag 
associated with the CNAME records.


Usage
-----

Bloxone Tags
~~~~~~~~~~~~

The script uses the following BloxOne Tags associated with the CNAME records:

    Service
        service name, e.g. (mail, intranet, www)

    Context_state
        The current context state: normal, backup, manual

    Primary_server
        Canonical name associated with normal state

    Backup_server
        Canonical name of associated with backup state


.. note::

    The Primary_server and Backup_server tags must include the trailing '.'
    i.e. the name should be fully qualified.


Set Up
~~~~~~

The script assumes that the best practise of using CNAME records for the 
application hostname is used. To set up a record create or use an existing
CNAME record and add the tags described above. 

The same service name can be applied to multiple CNAME records if appropriate.

Ensure that the 'service' name is added to the *applications* list in the 
*service.yml* file and matches the name used in the *Service* tag.

For the script to function all four tags are required. It is advised that the
record is setup in the 'normal' context state with the CNAME pointing to the
canonical name listed in the *Primary_server* tag. The script can be used
to check the state of the configuration once the tags have been applied.

The script should not affect any other tags applied to the records.


Examples
~~~~~~~~

The script supports -h or --help on the command line to access the options 
available::

% ./context_switch.py --help
usage: context_switch.py [-h] [-s SERVICE] [-S {get,normal,backup}] [-c CONFIG]

DNS Context Switcher

optional arguments:
  -h, --help            show this help message and exit
  -s SERVICE, --service SERVICE
                        Service Type
  -S {get,normal,backup}, --state {get,normal,backup}
                        Change or get service context
  -c CONFIG, --config CONFIG
                        Config file for bloxone


You can retrieve the state of any individual service or all services::

    % context_switch.py --service intranet --config ~/configs/bloxone.ini
    % context_switch.py --service all --config ~/configs/bloxone.ini


To change the state add the --state option::

    % context_switch.py --service intranet --state backup --config ~/configs/bloxone.ini
    

Again this can be done for all services listed in the applications section
of the *services.yml* file::

    % context_switch.py --service all --state backup --config ~/configs/bloxone.ini


If you wish to set the value of a record manually to an alternate value that
is not defined as either the primary or backup server then you can change the
mode to *manual*::

    % context_switch.py --service intranet --state manual --config ~/configs/bloxone.ini


.. note::

    Manual mode is just a marker, so that you know that the CNAME has been set
    to an alternate value. The script, however, can still be used to switch
    the state back to 'normal' or 'backup' setting the canonical name
    appropriately.


License
-------

This project, and the bloxone module are licensed under the 2-Clause BSD License
- please see LICENSE file for details.


Aknowledgements
---------------

