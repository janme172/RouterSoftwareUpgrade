########################################################################
# Callback Plugin for showing the Jsanpy logs to user.
# 
########################################################################

# Imports

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import collections
import os
import re
import time
import pprint
import json
from six import iteritems
import datetime

# For avaoiding the ascii encoding errors.
import sys
reload(sys)
sys.setdefaultencoding('utf8')

from ansible.plugins.callback import CallbackBase
from ansible import constants as C
from ansible.template import Templar
from ansible.plugins.strategy import SharedPluginLoaderObj

sys.path.append(os.getcwd())
from python_packages.common_vars import *
from python_packages.common_functions import *

ANSIBLE_PLAYBOOKS = [RE_SWITCHOVER_PLAYBOOK, VALIDATIONS_SOFT_UPGRADE_PLAYBOOK, 'test.yml']
CHECK = 'check'
SNAPCHECK = 'snapcheck'
SNAP_PRE = 'snap_pre'
SNAP_POST = 'snap_post'
KEY_ACTION = 'action'

class CallbackModule(CallbackBase):
    """
    This callback add extra logging for the module junos_jsnapy .
    """
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'aggregate'
    CALLBACK_NAME = 'jsnapyfull'

    def __init__(self):
        self._start_date = datetime.datetime.now().strftime('%Y-%m-%d')
        self._start_time = datetime.datetime.now().strftime('%H%M%S_%f')
        self._pp = pprint.PrettyPrinter(indent=4)
        self._playbook_filename = None
        self._task_name = None
        self._results = {}
        self._parent_log_path = "/var/log/ansible/{0}/{1}".format(self._start_date, self._start_time)
        self._jsnapy_log_dir = None
        self._log_server = None
        self.sftp = None

        #self._use_logserver = None
        super(CallbackModule, self).__init__()

    def runner_on_ok(self, host, result):
        if self._task_name.strip().startswith(TASK_PLAYBOOK_LOGGING_DETAILS):
            self._parent_log_path = result.get('ansible_facts', {}).get(KEY_PLAY_LOG_DIR)
            #self._use_logserver = result.get('ansible_facts', {}).get(KEY_PLAY_LOG_HOST)
            self.setup_logging()  
        module_name = result.get('invocation', {}).get('module_name')
        module_args = result.get('invocation', {}).get('module_args', {})
        #self._display.display(str(result))
        self._jsnapy_log_dir = os.path.join(self._parent_log_path, 'jsnapy')
        if KEY_ACTION not in module_args:
            return
#        if self._playbook_filename in ANSIBLE_PLAYBOOKS:
        log_file = None
        if module_args[KEY_ACTION] == SNAP_PRE:
            log_file = os.path.join(self._jsnapy_log_dir, 'checks/pre/', host+'.log')
        if module_args[KEY_ACTION] == SNAP_POST:
            log_file = os.path.join(self._jsnapy_log_dir, 'checks/post/', host+'.log')
        if module_args[KEY_ACTION] == CHECK:
            log_file = os.path.join(self._jsnapy_log_dir, 'checks/compare/', host+'.log')            
        if module_args[KEY_ACTION] == SNAPCHECK:
            log_file = os.path.join(self._jsnapy_log_dir, 'validations', host+'.log')

        if module_args[KEY_ACTION] in (SNAP_PRE, SNAP_POST, CHECK, SNAPCHECK) and log_file is not None:
            self.copy_file_to(log_file, LOG_SERVER, log_file)
            self.display_jsnapy_log_info(log_file, host)

    def v2_playbook_on_task_start(self, task, is_conditional):
        self._task_name = task.get_name()

    def v2_playbook_on_start(self, playbook):
        self.playbook = playbook
        self._playbook_filename = playbook._file_name


    ####################
    # Custom Functions
    ####################
    def setup_logging(self):
        #if self._use_logserver:
        if LOG_SERVER:
            if not self.sftp:
                self.sftp = get_sftp(LOG_SERVER, LOG_USER, LOG_USER_PASS)
            if self.sftp:
                try:
                    for jsanpy_dir in JSNAPY_LOG_DIRS:
                        jsanpy_dir = os.path.join(self._parent_log_path, jsanpy_dir)
                        remote_makedirs(self.sftp, jsanpy_dir)                
                except Exception as err:
                    self._display.display("Unable to create the Jsanpy log directories on log server {0}. {1}".format(LOG_SERVER, err))
            else:
                self._display.display("Unable to connect to log server {0}.".format(LOG_SERVER))
        
        try:
            for jsanpy_dir in JSNAPY_LOG_DIRS:
                jsanpy_dir = os.path.join(self._parent_log_path, jsanpy_dir)
                if not os.path.exists(jsanpy_dir):
                    os.makedirs(jsanpy_dir)
        except Exception as err:
            self._display.display("Unable to create the local Jsanpy log directories. {0}".format(err))

    def copy_file_to(self, filepath, to_server, to_file_path):
        if not self.sftp:
            self.sftp = get_sftp(LOG_SERVER, LOG_USER, LOG_USER_PASS)
#        if self.sftp:
#            with open(filepath, 'r') as lf:
#                with self.sftp.file(to_path, 'a') as rf:
#                    for line in lf:
#                        rf.write(line)
        try:
            self.sftp.stat(to_file_path)
        except IOError:
            self.sftp.put(filepath, to_file_path)

    def display_jsnapy_log_info(self, jsnapy_log_file, host):
        display_color = 'green'
        try:
            with open(jsnapy_log_file, 'r') as jf:
                for line in jf:
                    if 'FAIL' in line:
                        display_color = 'red'
        except:
            display_color = 'red'
        self._display.display("Jsnapy log file is <{jsnapy_log_file}> for host <{host}> on log server <{log_server}>".format(jsnapy_log_file=jsnapy_log_file, host=host, log_server=LOG_SERVER), color=display_color) 
#        with open(os.path.join(log_dir, jsnapy_log_file), 'r') as logfile:
#            for line in logfile:
#                log_line_match = re.match(r'^(\d{4}-\d{2}-\d{2}.*jnpr\.jsnapy)', line)
#                if log_line_match:
#                    self._display.display(line.encode('utf-8'))
