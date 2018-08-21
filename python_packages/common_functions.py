import paramiko
import os

def delete_files(dir_path, filename=None):
    if not os.path.exist(dir_path):
        msg = "Path doesn't exist" 


def get_sftp(host, user, password):
    transport = paramiko.Transport((host, 22))
    try:
        transport.connect(username=user, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
    except:
        return
    return sftp


def remote_makedirs(sftp, remote_dir):
    if remote_dir == '/':
        # absolute path so change directory to root
        sftp.chdir('/')
        return
    if remote_dir == '':
        # top-level relative directory must exist
        return
    try:
        sftp.chdir(remote_dir)  # sub-directory exists
    except IOError:
        dirname, basename = os.path.split(remote_dir.rstrip('/'))
        remote_makedirs(sftp, dirname)  # make parent directories
        sftp.mkdir(basename)  # sub-directory missing, so created it
        sftp.chdir(basename)
        return True

