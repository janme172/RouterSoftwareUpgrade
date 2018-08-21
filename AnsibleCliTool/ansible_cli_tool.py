#!/usr/bin/python

from __future__ import print_function
import os
import ConfigParser as configparser
import collections
import subprocess
import datetime
from bin.database import Database
import tabulate

TOOL_PLAYBOOKS_PATH = '../'
PLAYBOOKS_CONFIG_FILE = 'settings/ansible_cli_tool_input.ini'
TOOL_LOG_PATH = 'logs/ansible_cli_tool/'
if not os.path.exists(TOOL_LOG_PATH):
    os.makedirs(os.path.dirname(TOOL_LOG_PATH))


def create_new_job(task_name, playbook_name, by_user, start_date):
    db = Database(server='localhost', db_type='mysql', database='AnsibleCliTool', user='root', password='root')
    db.connect()
    cur = db.connection.cursor()
    create_job_cmd = "insert into job_details (task_name, playbook_name, by_user, start_date) values ('{task_name}', '{playbook_name}', '{by_user}', '{start_date}')".format(task_name=task_name, playbook_name=playbook_name, by_user=by_user, start_date=start_date)
    cur.execute(create_job_cmd)
    job_id = cur.lastrowid   
    db.connection.commit()
    db.disconnect()     
    last_job_id = max([int(jobfolder.split('_')[1].strip()) for jobfolder in os.listdir(TOOL_LOG_PATH) if jobfolder.startswith('job_')] + [0])
    return job_id 

def run_playbook(playbook, task_name):
    start_time = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S_%f')
    created_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    playbook_name = os.path.basename(playbook)
    job_id = create_new_job(task_name, playbook_name, 'tool', created_at)
    logfile = os.path.join(TOOL_LOG_PATH, 'job_{job_id}/{playbook}_{start_time}.log'.format(playbook=playbook_name, start_time=start_time, job_id=job_id))
    if not os.path.exists(os.path.dirname(logfile)): 
        os.makedirs(os.path.dirname(logfile))
    print('Note: Playbook output will be saved to', logfile)
    #cmd = 'stdbuf -oL ansible-playbook {playbook} 2>&1 | tee -a {logfile}'.format(playbook=playbook, logfile=logfile)
    cmd = 'stdbuf -oL ansible-playbook {playbook} 3>&1 2>&1 | tee -a {logfile}'.format(playbook=playbook, logfile=logfile)
    cmd = 'script -c "cd {playbooks_path}; stdbuf -oL  ansible-playbook {playbook}" {logfile}'.format(playbook=playbook_name, logfile=logfile, playbooks_path=TOOL_PLAYBOOKS_PATH)
    process = subprocess.Popen(cmd, shell=True)
    process.wait()
    print('\nPlabook Completed.')


def read_playbook_config():
    config = configparser.ConfigParser()
    config.read(PLAYBOOKS_CONFIG_FILE)
    config_dict = collections.OrderedDict()
    for section in config.sections():
        config_dict.update({section: {}})
        for (key, val) in config.items(section):
            config_dict[section][key] = val
    return config_dict


def display_banner():
    os.system('clear')
    banner_text = '#'*100 + '\n' + '\t\t Welcome to Ansible CLI Tool' + '\n' + '#'*100 + '\n'
    print(banner_text)

def display_errors(error_messages):
    print('-'*100, 'Errors:', sep='\n')
    for msg in error_messages:
        print('\t-', msg)
        print('-'*100)

def display_home():
    print('\n\t', 'What you wish to do today:')
    print('\t\t', 1, ': ', 'Run Playbooks')
    print('\t\t', 2, ': ', 'View Jobs')
    print('\t\t', 3, ': ', 'View Logs')
    print('\t\t', 4, ': ', 'Exit')
    
def display_playbooks(playbooks_config):
    choice_details = {}
    choice = 0
    print('\n\t', 'Which task you want to perform:')
    for key, val in playbooks_config.items():
        choice += 1
        choice_details[choice] = [key, val]
        print('\t\t' ,choice, ': ', key)
    choice += 1
    choice_details[choice] = ['BACK', 'BACK']
    print('\t\t' ,choice, ': ', 'Back')
    choice += 1
    choice_details[choice] = ['EXIT', 'EXIT']
    print('\t\t' ,choice, ': ', 'Exit')
    return choice_details

def display_jobs_home():
    print('\n\t', 'Select what you want to do:')
    print('\t\t', 1, ': ', 'View all jobs')
    print('\t\t', 2, ': ', 'View last 10 jobs')
    print('\t\t', 3, ': ', 'View Jobs')
    print('\t\t', 4, ': ', 'Exit')
   

def display_jobs(limit=None, offset=None):
    db = Database(server='localhost', db_type='mysql', database='AnsibleCliTool', user='root', password='root')
    db.connect()
    jobs = db.pd_select('job_details', cols=['*'], limit=limit, offset=offset)
    db.disconnect()
    if not jobs.empty:
            print(tabulate.tabulate(jobs, tablefmt='grid', showindex=False, headers=['Job Id', 'Task Name', 'Playbook', 'By User', 'Created At']))
    return jobs

def display_paginated_jobs(results_per_page=None):
    if not results_per_page:
        results_per_page = 10
    offset = 0
    jobs = display_jobs(limit=results_per_page, offset=offset)
    if jobs.empty:
        print('No Jobs to display')
    go_back = False
    while not go_back:
        
        print('-'*50, '\n', '1: Previous\t2: Next\t3: Back')
        user_choice = take_user_choice(3)
        while user_choice is None:
            print('Invalid Input!!!')
            user_choice = user_choice = take_user_choice(3)
        if user_choice == 3:
            go_back = True
            break
        if user_choice == 1:
            offset -= results_per_page
        if user_choice == 2:
            offset += results_per_page
        if offset < 0:
            print("Can't Go back further")
            offset = 0
            continue
        jobs = display_jobs(limit=results_per_page, offset=offset)
        if jobs.empty:
            print("Can't Go Forward further")
            offset -= results_per_page
        
            
            
    
    


def take_user_choice(choice_range):
    user_choice = raw_input('\n\tYour Choice[{0}-{1}]: '.format(1, choice_range))
    try:
        user_choice = int(user_choice)
    except:
        pass
    if not isinstance(user_choice, int):
        return
    return user_choice

def set_display(available_displays, display_name):
    is_display_set = False
    for key, val in available_displays.items():
        if key == display_name:
             available_displays[key] = True
             is_display_set = True
        else:
             available_displays[key] = False
    if not is_display_set:
        available_displays['Home'] = True
    
def display_logs_home():
    selected_job_id = raw_input('\n\tPlease enter the Job Id: ')
    try:
        selected_job_id = int(selected_job_id)
    except:
        pass
    if not isinstance(selected_job_id, int):
        return
    return selected_job_id

def display_playbook_log_file(job_id):
    db = Database(server='localhost', db_type='mysql', database='AnsibleCliTool', user='root', password='root')
    db.connect()
    jobs = db.pd_select('job_details', cols=['id'])
    db.disconnect()
    if job_id not in jobs['id'].tolist(): 
        print('Job not found!!!')
        return
  
    logfile = os.path.join(TOOL_LOG_PATH, 'job_{}'.format(job_id), [logfile for logfile in os.listdir(os.path.join(TOOL_LOG_PATH, 'job_{}'.format(job_id)))][0])
    cmd = 'script -c "stdbuf -oL cat {logfile}"'.format(logfile=logfile)
    process = subprocess.Popen(cmd, shell=True)
    process.wait()
    print('\nLog Display Done.')


def main():
    exit = False
    error_messages = []
    available_displays = {'Home': True, 'PlaybookTasks': False, 'JobsHome': False, 'Logs': False}
    try:
        playbooks_config = read_playbook_config()
    except:
        print('Error in getting the playbooks configuration')
        exit()
    while not exit:
      display_banner()
      if error_messages:
          display_errors(error_messages)
          error_messages = []
      if available_displays.get('Home'):
          display_home()
          user_choice = take_user_choice(4)
          if user_choice is None:
              error_messages.append('Invalid Input Provided')
              continue
          if user_choice == 4:
              exit = True
              continue
          if user_choice == 1:
              set_display(available_displays, 'PlaybookTasks')
              continue
          if user_choice == 2:
              set_display(available_displays, 'JobsHome')
              continue
          if user_choice == 3:
              set_display(available_displays, 'Logs')
              continue


      elif available_displays.get('PlaybookTasks'):
          available_choices = display_playbooks(playbooks_config)
          user_choice = take_user_choice(len(playbooks_config) + 1)
          if user_choice is None:
              error_messages.append('Invalid Input Provided')
              continue
          if available_choices[user_choice][0] == 'EXIT':
              exit = True
              continue
          if available_choices[user_choice][0] == 'BACK':
              set_display(available_displays, 'Home')
              continue
          playbook = os.path.join(TOOL_PLAYBOOKS_PATH, available_choices[user_choice][1].get('playbook'))
          run_playbook(playbook, available_choices[user_choice][0])
      elif available_displays.get('JobsHome'):
          display_jobs_home()
          user_choice = take_user_choice(5)
          if user_choice is None:
              error_messages.append('Invalid Input Provided')
              continue
          if user_choice == 5:
              exit = True
              continue
          if user_choice == 1:
              display_jobs()
          elif user_choice == 2:
              display_jobs(limit=10, offset=0)
          elif user_choice == 3:
              results_per_page = 10
              valid_input = False
              while not valid_input:
                  results_per_page = raw_input('\t\tResults per page: ')
                  try:
                      results_per_page = int(results_per_page)
                      valid_input = True
                  except:
                      valid_input = False
              display_paginated_jobs(results_per_page)
              set_display(available_displays, 'JobsHome')
              continue
      elif available_displays.get('Logs'):
          selected_job_id = display_logs_home()
          if selected_job_id is None:
              error_messages.append('Invalid Input Provided')
              continue
          display_playbook_log_file(selected_job_id)
          
     
      print('\n1: HOME\t\t2: EXIT')
      user_choice = raw_input('Your Choice: ')
      if user_choice == '2':
          exit = True 
      elif user_choice == '1':
          exit = False
          set_display(available_displays, 'Home')
      else:
          exit = False

    print('-'*50,'\n','Thanks for using the Tool.','\n'+'-'*50)  




if __name__ == '__main__':
    main()
