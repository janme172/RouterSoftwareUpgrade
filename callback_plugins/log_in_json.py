# (C) 2012, Michael DeHaan, <michael.dehaan@gmail.com>
# (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type
import datetime, os, paramiko, json

DOCUMENTATION = '''
    callback: log_plays
    type: notification
    short_description: write playbook output to log file
    version_added: historical
    description:
      - This callback writes playbook output to a file per host in the `/var/log/ansible/hosts` directory
      - "TODO: make this configurable"
    requirements:
     - Whitelist in configuration
     - A writeable /var/log/ansible/hosts directory by the user executing Ansible on the controller
'''

import os
import time
import json
from collections import MutableMapping

from ansible.module_utils._text import to_bytes
from ansible.plugins.callback import CallbackBase
from dashtable import data2rst

# For avaoiding the ascii encoding errors.
import sys
reload(sys)
sys.setdefaultencoding('utf8')

sys.path.append(os.getcwd())
from python_packages.common_vars import *
from python_packages.common_functions import *

RE0 = 'RE0'
RE1 = 'RE1'
ERROR_UNABLE_2_GET = 'Error: Unable to get'


# NOTE: in Ansible 1.2 or later general logging is available without
# this plugin, just set ANSIBLE_LOG_PATH as an environment variable
# or log_path in the DEFAULTS section of your ansible configuration
# file.  This callback is an example of per hosts logging for those
# that want it.


class CallbackModule(CallbackBase):
    """
    logs playbook results, per host, in /var/log/ansible/hosts
    """
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'notification'
    CALLBACK_NAME = 'log_plays'
    #    CALLBACK_NEEDS_WHITELIST = True

    TIME_FORMAT = "%b %d %Y %H:%M:%S"
    MSG_FORMAT = "Task Name: %(task_name)s\nTimestamp: %(now)s\nTask Status:%(category)s\n%(data)s\n"

    def __init__(self):
        # self.play_start_datetime = datetime.datetime.now()
        self._start_date = datetime.datetime.now().strftime('%Y-%m-%d')
        self._start_time = datetime.datetime.now().strftime('%H%M%S_%f')
        self.sftp = None
        self._playbook_filename = None
        self._task_name = None
        self._parent_log_path = "/var/log/ansible/{0}/{1}".format(self._start_date, self._start_time)
        self._log_dir = os.path.join(self._parent_log_path, 'playbook')
        self._do_logging = False
        self.host_facts = {}
        super(CallbackModule, self).__init__()

    def v2_playbook_on_start(self, playbook):
        self._playbook_filename = playbook._file_name
        #self.create_sftp_to_log_server()
        # self.create_log_dir()

    def v2_playbook_on_task_start(self, task, is_conditional):
        self._task_name = task.get_name()
        # self.play_start_datetime = datetime.datetime.now()

    def runner_on_failed(self, host, res, ignore_errors=False):
        self.logger_main(host, 'FAILED', res)

    def runner_on_ok(self, host, res):
        self.logger_main(host, 'OK', res)

    def runner_on_skipped(self, host, item=None):
        self.logger_main(host, 'SKIPPED', '...')

    def runner_on_unreachable(self, host, res):
        self.logger_main(host, 'UNREACHABLE', res)

    def runner_on_async_failed(self, host, res, jid):
        self.logger_main(host, 'ASYNC_FAILED', res)

    def playbook_on_import_for_host(self, host, imported_file):
        self.logger_main(host, 'IMPORTED', imported_file)

    def playbook_on_not_import_for_host(self, host, missing_file):
        self.logger_main(host, 'NOTIMPORTED', missing_file)

    def setup_logging(self):
        # if self._use_logserver:
        if LOG_SERVER:
            if not self.sftp:
                self.sftp = get_sftp(LOG_SERVER, LOG_USER, LOG_USER_PASS)
            if self.sftp:
                try:
                    remote_makedirs(self.sftp, self._log_dir)
                except Exception as err:
                    self._display.display(
                        "Unable to create the Playbook log directory on log server {0}. {1}".format(LOG_SERVER, err))
                self._do_logging = True
            else:
                self._display.display("Unable to connect to log server {0}.".format(LOG_SERVER))

        # try:
        #     for jsanpy_dir in JSNAPY_LOG_DIRS:
        #         jsanpy_dir = os.path.join(self._parent_log_path, jsanpy_dir)
        #         if not os.path.exists(jsanpy_dir):
        #             os.makedirs(jsanpy_dir)
        # except Exception as err:
        #     self._display.display("Unable to create the local Jsanpy log directories. {0}".format(err))

    def logger_main(self, host, task_status, result):
        if self._task_name.strip().startswith(TASK_PLAYBOOK_LOGGING_DETAILS):
            if task_status == 'OK':
                self._parent_log_path = result.get('ansible_facts', {}).get(KEY_PLAY_LOG_DIR)
                self._log_dir = os.path.join(self._parent_log_path, 'playbook', 'json')
                self.setup_logging()
                self._display.display('JSON Log dir is <{0}> on log server <{1}>'.format(self._log_dir, LOG_SERVER))
            else:
                pass
        if self._do_logging:
            #elif self._playbook_filename.strip() in  RE_SWITCHOVER_PLAYBOOKS:
            #    pass
            #else:
            self.sftp = get_sftp(LOG_SERVER, LOG_USER, LOG_USER_PASS) if not self.sftp else self.sftp    
            logfile_path = os.path.join(self._log_dir, '{}.log'.format(host))
            with self.sftp.file(logfile_path, 'a') as logfile:
                logfile.write('\n{0}\nTask Name: {1}\nTask Status: {2}\n{0}\n'.format('-'*200, self._task_name, task_status))
                logfile.write('\n' + str(result) + '\n')
                logfile.write('\n{0}\n'.format('-'*200))
