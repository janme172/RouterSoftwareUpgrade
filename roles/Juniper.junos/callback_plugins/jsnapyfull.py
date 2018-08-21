from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import collections
import os
import time
import pprint
import json
from six import iteritems

from ansible.plugins.callback import CallbackBase
from ansible import constants as C

class CallbackModule(CallbackBase):
  """
  This callback add extra logging for the module junos_jsnapy .
  """
  CALLBACK_VERSION = 2.0
  CALLBACK_TYPE = 'aggregate'
  CALLBACK_NAME = 'jsnapyfull'

## useful links regarding Callback
## https://github.com/ansible/ansible/blob/devel/lib/ansible/plugins/callback/__init__.py

  def __init__(self):
    self._pp = pprint.PrettyPrinter(indent=4)
    self._results = {}

    super(CallbackModule, self).__init__()

  def v2_runner_on_ok(self, result):
    """
    Collect test results for all tests executed if module is junos_jsnapy
    """
    #self._display.display("-----------Invoked v2_runner_on_ok----------------------")
    ## Extract module name
    module_name = ''
    module_args = {}
    #self._display.display(str(result._result))
    self._display.display("2------------------------------------------------------------------------------------------------------------------------")    
    if 'invocation' in result._result:
      if 'module_name' in result._result['invocation']:
        module_name = result._result['invocation']['module_name']
      module_args = result._result['invocation']['module_args']

    ## Check if dic return has all valid information
    #if module_name == '' or module_args == {}:                  # Commented because it is not coming in Juniper_junos_jsnapy module output
    #    return None
    if 'action' not in module_args:
        return None
    # Extra check added so that it only runs for juniper_junos_jsnapy module only
    if  module_args['action'] not in ('snapcheck', 'check') or not ('test_files' in module_args or 'config_file' in module_args):
        return None
    # Added the <''> because module name not coming in results in case of juniper_junos_jsnapy module. Only module args are available.
    if module_name in ('juniper_junos_jsnapy', 'junos_jsnapy', '') and ( module_args['action'] == 'snapcheck' or module_args['action'] == 'check' ):

      ## Check if dict entry already exist for this host
      host = result._host.name
      if not host in self._results.keys():
        self._results[host] = []

      self._results[host].append(result)

  def v2_playbook_on_stats(self, stats):
    
    #self._display.display("###################### CALLBACK INVOKED ##############################")
    #self._display.display(str(self._results.items()))

    ## Go over all results for all hosts
    for host, results in iteritems(self._results):
      #self._display.display("1")
      #self._display.display("{}:\n {}\n".format(str(host), str(results)))
      has_printed_banner = False
      for result in results:
        #self._display.display("2")
        #self._pp.pprint(result.__dict__)
        res = result._result
        #if res['final_result'] == "Failed":
      
        if True:
          test_status = "Unknown"
          try:
            test_status = res['final_result']
          except:
            pass
          #self._display.display("###################### Inside Failed ##############################")
          for command_or_rpc, test_results in iteritems(res['test_results']):
            #self._display.display("3")
            #self._display.display("###################### Test Name: {} ##############################".format(test_name))
            #self._display.display(test_name)            
            has_printed_test_name = False
            node_name = ''
            for testlet in test_results:
              	#self._display.display("4")
              	#if testlet['count']['fail'] != 0:
                test_name = testlet['test_name']
                failed_test_count = testlet['count']['fail']
                passed_test_count = testlet['count']['pass']
                if not has_printed_banner:
                  #self._display.banner("JSNAPy Results for: " + str(host))
                  self._display.banner("JSNAPy Results for Device: {}".format(host))
                  has_printed_banner = True
                if not has_printed_test_name:
	            self._display.display("Test name: {}".format(test_name))
                    has_printed_test_name = True
                node_name = testlet['node_name']
                self._display.display("\tNode name: {0}".format(node_name))
                self._display.display("\tFailed: {0}".format(failed_test_count))
                self._display.display("\tPassed: {0}".format(passed_test_count))
                for test in testlet['failed']:
		  #elf._display.display("5")
                  # Check if POST exist in the response
                  data = ''
                  if 'post' in test:
                      data = test['post']
                  else:
                      data = test
                  #self._display.display("Hello\n")
                  self._display.display(
                    "\tFail: {0}".format(test['message']), color=C.COLOR_ERROR
                  )
#                  self._display.display("\t\tAnsible Output: Value of '{0}' not '{1}' at '{2}' with {3}".format(str(testlet['node_name']), str(testlet['testoperation']), str(testlet['xpath']), json.dumps(data)), color=C.COLOR_ERROR)


                for test in testlet['passed']:
                  #self._display.display("6")
                  # Check if POST exist in the response
                  data = ''
                  if 'post' in test:
                      data = test['post']
                  else:
                      data = test
                  #self._display.display("Hello\n")
                  try:
                    pass_message = test['message']
                  except:
                    pass_message = "Value of '{0}' '{1}' at '{2}'".format(str(testlet['node_name']), str(testlet['testoperation']), str(testlet['xpath'])) 
                  self._display.display(
                    "\tPass: {0}".format(pass_message), color='green'
                  )
#                  self._display.display("\t\tAnsible Output: Value of '{0}' '{1}' at '{2}' with {3}".format(str(testlet['node_name']), str(testlet['testoperation']), str(testlet['xpath']), json.dumps(data)), color='green')
