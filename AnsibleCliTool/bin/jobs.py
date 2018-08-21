from __future__ import print_function
import os
import sys

import pyodbc
import MySQLdb
import pandas as pd

from collections import OrderedDict
import datetime

class Jobs(object):
    """
    This Class is used for handling different database operations.
    """
    def __init__(self, task_name, playbook_name, by_user, created_at):
        self.job_id = None
        self.task_name = task_name
        self.playbook_name = playbook_name
        self.by_user = by_user
        self.created_at = created_at
        self.create_in_db()

    def create(self):
        pas
        

    def __str__(self):
        return "Job Details :\n\tJob ID : {0.job_id}.\n\tTask Name : {0.task_name}.\n\tPlaybook : {0.playbook_name}.\n\tBy User : {0.by_user}\n\tCreated At: {0.created_at}.".format(self)

    def __repr__(self):
        return "Job('{0.job_id}', '{0.task_name}', '{0.playbook_name}', '{0.by_user}', '{0.created_at}')".format(self)
