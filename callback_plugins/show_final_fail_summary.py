from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import datetime, os, paramiko, json

import os
import time
import json
from collections import MutableMapping
#from texttable import Texttable
from ansible.module_utils._text import to_bytes
from ansible.plugins.callback import CallbackBase
from dashtable import data2rst

# For avoiding the ascii encoding errors
import sys
reload(sys)
sys.setdefaultencoding('utf8')

sys.path.append(os.getcwd())
from python_packages.common_vars import *
from python_packages.common_functions import *




class CallbackModule(CallbackBase):
    """
    customizes the on screen output of the play.
    """
    CALLBACK_VERSION = 1.0
    CALLBACK_TYPE = 'notification'
    CALLBACK_NAME = 'customize_play_output'

    def __init__(self):
        self.fail_summary = {}
        self.playbook_filename = None
        self.task_name = None
        super(CallbackModule, self).__init__()

    def v2_playbook_on_start(self, playbook):
        self.playbook_filename = playbook._file_name
    
    def v2_playbook_on_task_start(self, task, is_conditional):
        self.task_name = task.get_name()
        self.play_start_datetime = datetime.datetime.now()

    def runner_on_failed(self, host, res, ignore_errors=False):
        self.update_fail_summary(host, 'FAILED', res)

    def v2_playbook_on_stats(self, stats):
        if self.fail_summary:
            self._display.display('########## Table: Play Failure Summary ####################')
            #table_fail_summary = Texttable()
            table_rows = []
            spans = []
            host_span = []
            row = 0
            table_rows.append(['Device', 'Failed Tasks', 'Message(If Any)'])
            for host, tasks_and_messages in self.fail_summary.items():
                host_in_table = False
                total_rows = len(tasks_and_messages)
                host_span = []
                for task, message in tasks_and_messages:
                    row += 1
                    host_span.append([row, 0])
                    if not host_in_table:
                        table_rows.append([host, task, message])
                        host_in_table = True
                    else:
                        table_rows.append(['', task, message])
            spans.extend([host_span])
            self._display.display(data2rst(table_rows, spans=spans, use_headers=True))
            #table_fail_summary.add_rows(table_rows)
            #self._display.display(str(table_fail_summary.draw()))
 
    def update_fail_summary(self, host, task_status, data):
        stripped_lwr_task_name = self.task_name.strip().strip('.').lower()
        if self.playbook_filename in (RE_SWITCHOVER_PLAYBOOK, UPGRADE_BACKUP_RE_PLAYBOOK, VALIDATIONS_SOFT_UPGRADE_PLAYBOOK):
            if host not in self.fail_summary:
                self.fail_summary[host] = []
            task_message = ''
            if 'msg' in data:
                task_message = data['msg']
            elif 'message' in data:
                task_message = data['message']

            self.fail_summary[host].append([self.task_name, task_message])
        else:
            if host not in self.fail_summary:
                self.fail_summary[host] = []
            task_message = ''
            if 'msg' in data:
                task_message = data['msg']
            elif 'message' in data:
                task_message = data['message']

            self.fail_summary[host].append([self.task_name, task_message]) 

