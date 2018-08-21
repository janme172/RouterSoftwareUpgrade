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
        self.play_start_datetime = datetime.datetime.now()
        self.playbook_filename = None
        self.task_name = None
        self.re_switch_details = {}
        super(CallbackModule, self).__init__()

    def v2_playbook_on_start(self, playbook):
        self.playbook_filename = playbook._file_name
    
    def v2_playbook_on_task_start(self, task, is_conditional):
        self.task_name = task.get_name()
        self.play_start_datetime = datetime.datetime.now()

    def runner_on_failed(self, host, res, ignore_errors=False):
        self.display_customized_output(host, 'FAILED', res)

    def runner_on_ok(self, host, res):
        self.display_customized_output(host, 'OK', res)

    def runner_on_skipped(self, host, item=None):
        self.display_customized_output(host, 'SKIPPED', '...')

    def runner_on_unreachable(self, host, res):
        self.display_customized_output(host, 'UNREACHABLE', res)

    def runner_on_async_failed(self, host, res, jid):
        self.display_customized_output(host, 'ASYNC_FAILED', res)

    def playbook_on_import_for_host(self, host, imported_file):
        self.display_customized_output(host, 'IMPORTED', imported_file)

    def playbook_on_not_import_for_host(self, host, missing_file):
        self.display_customized_output(host, 'NOTIMPORTED', missing_file)

    ########################################
    # CUSTOM FUNCTIONS                    
    ########################################
    def display_customized_output(self, host, task_status, data):
        if host == 'localhost':
            return
        if host not in self.re_switch_details:
            self.re_switch_details[host] = {'master_re_before_switchover': None, 'master_re_after_switchover': None, 'comments': []}

        stripped_lwr_task_name = self.task_name.strip().strip('.').lower()
        if self.playbook_filename in RE_SWITCHOVER_PLAYBOOKS:
            if  stripped_lwr_task_name.startswith('get the master re before re switchover') or stripped_lwr_task_name.startswith('get the master re after re switchover'):
                self.update_re_switch_details(host, task_status, data)
            elif stripped_lwr_task_name.startswith('display re switchover summary'):
                self.display_re_switchover_summary(host, task_status, data)
                self.re_switch_details = {}

    def update_re_switch_details(self, host, task_status, data):
        if task_status == 'OK':
            if 'master_re_before_switchover' in data.get('ansible_facts', {}):
                self.re_switch_details[host]['master_re_before_switchover'] = data.get('ansible_facts', {}).get('master_re_before_switchover')
            elif 'master_re_after_switchover' in data.get('ansible_facts', {}):
                self.re_switch_details[host]['master_re_after_switchover'] = data.get('ansible_facts', {}).get('master_re_after_switchover')
            
        else:
            self.re_switch_details[host]['comments'].append('Unable to get RE details')

    def display_re_switchover_summary(self, host, task_status, data):
        if self.re_switch_details:
            self._display.display('########## Table: RE Switchover Summary ####################')
        if self.playbook_filename in RE_SWITCHOVER_PLAYBOOKS:
            table_rows = []
            table_rows.append(['Device', 'Master RE-Before Switch', 'Master RE-After Switch', 'Switchover Status', 'Comments'])
            for host, details in self.re_switch_details.items():
                table_row = [host, '', '', '', '']
                for key, val in self.re_switch_details[host].items():
                    if key == 'master_re_before_switchover':
                        table_row[1] = val if val else ''
                    elif key == 'master_re_after_switchover':
                        table_row[2] = val if val else ''
                    elif key == 'comments':
                        for comment in val:
                            table_row[4] = '{0}\n- {1}'.format(table_row[4] + '- ' + comment)

                if table_row[1].strip().lower() == table_row[2].strip().lower() and table_row[1] != '' and table_row[2] != '':
                    table_row[3] = 'Fail'
                elif table_row[1].strip().lower() != table_row[2].strip().lower() and table_row[1] != '' and table_row[2] != '':
                    table_row[3] = 'Success'
                else:
                    table_row[3] = 'Fail'
                
                table_rows.append(table_row)
            self._display.display(data2rst(table_rows, use_headers=True))
        

