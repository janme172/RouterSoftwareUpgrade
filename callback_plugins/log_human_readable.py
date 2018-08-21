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
        self.re_switch_details = {}
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
                self._log_dir = os.path.join(self._parent_log_path, 'playbook', 'human_readable')
                self.setup_logging()
                self._display.display('Human Readable Log dir is <{0}> on log server <{1}>'.format(self._log_dir, LOG_SERVER))
            else:
                pass
        if self._do_logging:
            #elif self._playbook_filename.strip() in  RE_SWITCHOVER_PLAYBOOKS:
            #    pass
            #else:
            self.sftp = get_sftp(LOG_SERVER, LOG_USER, LOG_USER_PASS) if not self.sftp else self.sftp    
            logfile_path = os.path.join(self._log_dir, '{}.log'.format(host))
            if self._task_name.strip().lower().startswith('gather facts from junos'):
                with self.sftp.file(logfile_path, 'a') as logfile:
                    logfile.write('\n{0}\nTask Name: {1}\nTask Status: {2}\n{0}\n'.format('-'*200, self._task_name, task_status))
                    if task_status not in ('OK', 'SKIPPED'):
                        logfile.write('\n' + str(result) + '\n')
                        logfile.write('\n{0}\n'.format('-'*200))
             
                self.get_dev_info_frm_facts(host, task_status, result)
            elif self._task_name.strip().lower().startswith('show table: device info/fact'):
                    for h in self.host_facts:
                        logfile_path = os.path.join(self._log_dir, '{}.log'.format(h))
                        with self.sftp.file(logfile_path, 'a') as logfile:
                            logfile.write('\n{0}\nTask Name: {1}\nTask Status: {2}\n{0}\n'.format('-'*200, self._task_name, task_status))
                            self.log_gathered_fact_table(h, logfile)
                            logfile.write('\n{0}\n'.format('-'*200))
            elif self._task_name.strip().lower().startswith('validate -'):
                with self.sftp.file(logfile_path, 'a') as logfile:
                    logfile.write('\n{0}\nTask Name: {1}\nTask Status: {2}\n{0}\n'.format('-'*200, self._task_name, task_status))
                    try:
                        jsnapy_log_file = os.path.join(self._parent_log_path, 'jsnapy', 'validations', '{}.log'.format(host))
                        self.sftp.stat(jsnapy_log_file)
                        with self.sftp.file(jsnapy_log_file, 'r') as jf:
                            for line in jf:
                                logfile.write('\n{0}'.format(line.strip()))
                    except IOError:
                        logfile.write('\n' + str(result) + '\n')
                    logfile.write('\n{0}\n'.format('-'*200))
            elif self._task_name.strip().lower().startswith('aborting -'):
                with self.sftp.file(logfile_path, 'a') as logfile:
                    logfile.write('\n{0}\nTask Name: {1}\nTask Status: {2}\n{0}\n'.format('-'*200, self._task_name, task_status))
                    try:
                        err_msg = result.get('msg')
                    except:
                        err_msg = None
                    if err_msg:
                        logfile.write('\nMessage: {0}\n'.format(err_msg))
                    else:
                        logfile.write('\n' + str(result) + '\n')
                    logfile.write('\n{0}\n'.format('-'*200))
            elif self._task_name.strip().lower().startswith('Take PRE Snapshot -'.lower()):
                with self.sftp.file(logfile_path, 'a') as logfile:
                    logfile.write('\n{0}\nTask Name: {1}\nTask Status: {2}\n{0}\n'.format('-'*200, self._task_name, task_status))
                    try:
                        jsnapy_log_file = os.path.join(self._parent_log_path, 'jsnapy', 'checks', 'pre', '{}.log'.format(host))
                        self.sftp.stat(jsnapy_log_file)
                        with self.sftp.file(jsnapy_log_file, 'r') as jf:
                            for line in jf:
                                logfile.write('\n{0}'.format(line.strip()))
                    except IOError:
                        logfile.write('\n' + str(result) + '\n')
                    logfile.write('\n{0}\n'.format('-'*200))
            elif self._task_name.strip().lower().startswith('Take POST Snapshot -'.lower()):
                with self.sftp.file(logfile_path, 'a') as logfile:
                    logfile.write('\n{0}\nTask Name: {1}\nTask Status: {2}\n{0}\n'.format('-'*200, self._task_name, task_status))
                    try:
                        jsnapy_log_file = os.path.join(self._parent_log_path, 'jsnapy', 'checks', 'post', '{}.log'.format(host))
                        self.sftp.stat(jsnapy_log_file)
                        with self.sftp.file(jsnapy_log_file, 'r') as jf:
                            for line in jf:
                                logfile.write('\n{0}'.format(line.strip()))
                    except IOError:
                        logfile.write('\n' + str(result) + '\n')
                    logfile.write('\n{0}\n'.format('-'*200))
            elif self._task_name.strip().lower().startswith('Compare PRE and POST Snapshots -'.lower()):
                with self.sftp.file(logfile_path, 'a') as logfile:
                    logfile.write('\n{0}\nTask Name: {1}\nTask Status: {2}\n{0}\n'.format('-'*200, self._task_name, task_status))
                    try:
                        jsnapy_log_file = os.path.join(self._parent_log_path, 'jsnapy', 'checks', 'compare', '{}.log'.format(host))
                        self.sftp.stat(jsnapy_log_file)
                        with self.sftp.file(jsnapy_log_file, 'r') as jf:
                            for line in jf:
                                logfile.write('\n{0}'.format(line.strip()))
                    except IOError:
                        logfile.write('\n' + str(result) + '\n')
                    logfile.write('\n{0}\n'.format('-'*200))
            elif  self._task_name.strip().lower().startswith('get the master re before re switchover') or self._task_name.strip().lower().startswith('get the master re after re switchover'):
                with self.sftp.file(logfile_path, 'a') as logfile:
                        logfile.write('\n{0}\nTask Name: {1}\nTask Status: {2}\n{0}\n'.format('-'*200, self._task_name, task_status))
                self.update_re_switch_details(host, task_status, result)
            elif self._task_name.strip().lower().startswith('display re switchover summary'):
                for h in self.host_facts:
                    logfile_path = os.path.join(self._log_dir, '{}.log'.format(h))
                    with self.sftp.file(logfile_path, 'a') as logfile:
                        logfile.write('\n{0}\nTask Name: {1}\nTask Status: {2}\n{0}\n'.format('-'*200, self._task_name, task_status))
                        self.log_re_switchover_summary(h, logfile)
                        logfile.write('\n{0}\n'.format('-'*200))
            elif (self._task_name.strip().lower().startswith('Set ISIS Overload -'.lower()) 
                    or self._task_name.strip().lower().startswith('Waiting for connectivity to router'.lower())
                    or self._task_name.strip().lower().startswith('Attempt RE Switchover'.lower())
                    or self._task_name.strip().lower().startswith('Delete ISIS Overload -'.lower())):
                with self.sftp.file(logfile_path, 'a') as logfile:
                    logfile.write('\n{0}\nTask Name: {1}\nTask Status: {2}\n{0}\n'.format('-'*200, self._task_name, task_status))
                    if task_status not in ('OK', 'SKIPPED'):
                        logfile.write('\n' + str(result) + '\n')
                        logfile.write('\n{0}\n'.format('-'*200))
            
            else:
                with self.sftp.file(logfile_path, 'a') as logfile:
                    logfile.write('\n{0}\nTask Name: {1}\nTask Status: {2}\n{0}\n'.format('-'*200, self._task_name, task_status))
                    if task_status not in ('SKIPPED'):
                        logfile.write('\n' + str(result) + '\n')
                        logfile.write('\n{0}\n'.format('-'*200))

                

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
                self.host_facts[host]['model'] = junos_facts.get('model')
                self.host_facts[host]['switch_style'] = junos_facts.get('switch_style')
                self.host_facts[host]['master_re'] = junos_facts.get('master')
                self.host_facts[host]['passed'] = True
        elif task_status == 'FAILED':
            if host not in self.host_facts:
                self.host_facts[host] = {RE0: {} , RE1: {}}
            #self._display.display(str(task_status))logfile_path
            self.host_facts[host]['passed'] = False
            self.host_facts[host]['err_msg'] = data.get('msg')


    def log_gathered_fact_table(self, loghost, logfile):
        
        if self._playbook_filename in ('PLAY BOOK NAMES HAVING DIFFRENT FORMAT TO LOG'):
            pass # LOGIC FOR DISPLAYING FACTS IN DIFFERENT FORMAT FOR SOME PLAYBOOKS
        else:
            for host, facts in sorted(self.host_facts.items()):
              if host == loghost:
                table_rows = []
                spans = []
                table_rows.append(['Device', 'Model', 'RE', 'Mastership State', 'Software Version', 'Switch Style', 'Comments'])
                row_num = 0
                logfile.write('\n########## Table: Device Info ####################\n')
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
                logfile.write(str(data2rst(table_rows, spans=spans, use_headers=True)))

    def update_re_switch_details(self, host, task_status, data):
        if host not in self.re_switch_details:
            self.re_switch_details[host] = {}
        if task_status == 'OK':
            if 'master_re_before_switchover' in data.get('ansible_facts', {}):
                self.re_switch_details[host]['master_re_before_switchover'] = data.get('ansible_facts', {}).get('master_re_before_switchover')
            elif 'master_re_after_switchover' in data.get('ansible_facts', {}):
                self.re_switch_details[host]['master_re_after_switchover'] = data.get('ansible_facts', {}).get('master_re_after_switchover')
        else:
            self.re_switch_details[host]['comments'].append('Unable to get RE details')

    def log_re_switchover_summary(self, loghost, logfile):
        if self._playbook_filename in RE_SWITCHOVER_PLAYBOOKS:
            table_rows = []
            table_rows.append(['Device', 'Master RE-Before Switch', 'Master RE-After Switch', 'Status', 'Comments'])
            for host, details in self.re_switch_details.items():
              if host == loghost:
                logfile.write('\n########## Table: RE Switchover Summary ####################\n')
                table_rows = []
                table_rows.append(['Device', 'Master RE-Before Switch', 'Master RE-After Switch', 'Status', 'Comments'])
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
                logfile.write(str(data2rst(table_rows, use_headers=True)))


