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


RE0 = 'RE0'
RE1 = 'RE1'
ERROR_UNABLE_2_GET = 'Error: Unable to get'

class CallbackModule(CallbackBase):
    """
    customizes the on screen output of the play.
    """
    CALLBACK_VERSION = 1.0
    CALLBACK_TYPE = 'notification'
    CALLBACK_NAME = 'show_device_facts'

    def __init__(self):
        self.playbook_filename = None
        self.task_name = None
        self.host_facts = {}
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

#    def runner_on_skipped(self, host, item=None):
#        self.display_customized_output(host, 'SKIPPED', '...')

    def display_customized_output(self, host, task_status, data):
        # Craete an entry for host in the data 
        if host == 'localhost':
            return
             
        stripped_lwr_task_name = self.task_name.strip().strip('.').lower()
        if self.playbook_filename == 'PLAYBOOK NAME VARIABLE':
            pass # Flexibility to add if conditioons based on play book names.... DIfferent logic for different playbooks.
        else:
            if stripped_lwr_task_name.startswith('gather facts from junos'):
                self.get_dev_info_frm_facts(host, task_status, data)
            elif stripped_lwr_task_name.startswith('show table: device info/fact'):
                self.display_gathered_fact_table()
                self.host_facts = {}

    def get_dev_info_frm_facts(self, host, task_status, data):
        if task_status == 'OK':
            if host not in self.host_facts:
                self.host_facts[host] = {RE0: {} , RE1: {}}
            #self._display.display(str(task_status)+ '=<' + str(host))
            junos_facts = data.get('ansible_facts', {}).get('junos')
            if junos_facts:
                self.host_facts[host]['has_2re'] = junos_facts.get('has_2RE')
                re0_info = junos_facts.get(RE0)
                re1_info = junos_facts.get(RE1)
                if re0_info is not None:
                    self.host_facts[host][RE0].update({'mastership_state': junos_facts.get(RE0, {}).get('mastership_state')})
                if re1_info is not None:
                    self.host_facts[host][RE1].update({'mastership_state': junos_facts.get(RE1, {}).get('mastership_state')})
                self.host_facts[host][RE0].update({'soft_ver': junos_facts.get('version_RE0')})
                self.host_facts[host][RE1].update({'soft_ver': junos_facts.get('version_RE1')})
                self.host_facts[host]['model'] = junos_facts.get('model') if not junos_facts.get('model') is None else junos_facts.get('model_info', {}).get(junos_facts.get('master', '').lower(), 'Error: Unable to determine')
                self.host_facts[host]['switch_style'] = junos_facts.get('switch_style')
                self.host_facts[host]['master_re'] = junos_facts.get('master')
                self.host_facts[host]['passed'] = True
        elif task_status == 'FAILED':
            if host not in self.host_facts:
                self.host_facts[host] = {RE0: {} , RE1: {}}
            #self._display.display(str(task_status))
            self.host_facts[host]['passed'] = False
            self.host_facts[host]['err_msg'] = data.get('msg')

    def display_gathered_fact_table(self):
        if self.host_facts:
            self._display.display('\n########## Table: Device Info ####################')
        if self.playbook_filename in ('PLAY BOOK NAMES HAVING DIFFRENT FORMAT TO DISPLAY'):
            pass # LOGIC FOR DISPLAYING FACTS IN DIFFERENT FORMAT FOR SOME PLAYBOOKS
        else:
            table_rows = []
            spans = []
            table_rows.append(['Device', 'Model', 'RE', 'Mastership State', 'Software Version', 'Switch Style', 'Comments'])
            row_num = 0
            for host, facts in sorted(self.host_facts.items()):
                if  self.host_facts.get(host, {}).get('passed'):
                    device_model = facts.get('model', ERROR_UNABLE_2_GET)
                    switch_style = facts.get('switch_style', ERROR_UNABLE_2_GET)
                    #try:
                    #self._display.display(str(self.host_facts.get(host, {}.get('master_re'))))
                    #self._display.display(str(host))
                    master_re = self.host_facts.get(host, {}).get('master_re').upper()
                    #except:
                    #    master_re = None
                    #self._display.display(str(self.host_facts))
                    if not self.host_facts.get(host, {}).get('has_2re'):
                        row_num += 1
                        mastership_state = self.host_facts.get(host, {}).get(master_re, {}).get('mastership_state', ERROR_UNABLE_2_GET)
                        soft_ver = self.host_facts.get(host, {}).get(master_re, {}).get('soft_ver', ERROR_UNABLE_2_GET)
                        table_rows.append([host, device_model, master_re, mastership_state, soft_ver, switch_style, 'Single RE device'])
                    else:
                        host_span = []
                        model_span = []
                        switch_style_span = []
                        comments_span = []
                        for re in (RE0, RE1):
                            row_num += 1
                            host_span.append([row_num, 0])
                            model_span.append([row_num, 1])
                            switch_style_span.append([row_num, 5])
                            comments_span.append([row_num, 6])
                            mastership_state = self.host_facts.get(host, {}).get(re, {}).get('mastership_state', ERROR_UNABLE_2_GET)
                            soft_ver = self.host_facts.get(host, {}).get(re, {}).get('soft_ver', ERROR_UNABLE_2_GET)
                            if re == RE0:
                                table_rows.append([host ,device_model, re, mastership_state, soft_ver, switch_style, ''])
                            else:
                                table_rows.append(['', '', re, mastership_state, soft_ver, '', ''])
                        spans.extend([host_span, model_span, switch_style_span, comments_span]) 
                else:
                    #self._display.display(str(self.host_facts))
                    row_num += 1
                    err_msg = self.host_facts.get(host, {}).get('err_msg')
                    if not err_msg:
                        err_msg = 'Unable to get the details'
                    table_rows.append([host, '', '', '', '', '', err_msg])
            self._display.display('\n'+data2rst(table_rows, spans=spans, use_headers=True))
