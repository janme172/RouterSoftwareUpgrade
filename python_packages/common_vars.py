PROJECT_NAME = 'RouterSoftwareUpgrade'

# RE STRINGS
RE0 = 'RE0'
RE1 = 'RE1'

# PLAYBOOKS
RE_SWITCHOVER_PLAYBOOK = 'RE_switchover_juniper.yml'
UPGRADE_BACKUP_RE_PLAYBOOK = 'upgrade_bkp_RE_juniper.yml'
VALIDATIONS_SOFT_UPGRADE_PLAYBOOK = 'validations_soft_upgrade_juniper.yml'
SHOW_DEVICE_INFO_PLAYBOOK = 'show_devices_info.yml'

RE_SWITCHOVER_PLAYBOOKS = ['cli_re_switchover_juniper.yml', 'tower_re_switchover_juniper.yml']

# ANSIBLE PLAYBOOK FACTS NAMES
KEY_PLAY_LOG_DIR = 'play_log_dir'
KEY_PLAY_LOG_HOST = 'play_log_host'

JSNAPY_LOG_DIRS = ['jsnapy/checks/compare', 'jsnapy/checks/pre', 'jsnapy/checks/post', 'jsnapy/validations/',]

# TASK NAMES
TASK_PLAYBOOK_LOGGING_DETAILS = 'Set Playbook Logging Details'

# LOG SERVER Details
LOG_SERVER = '62.243.147.45'
LOG_USER = 'ansible'
LOG_USER_PASS = 'ansible'
