import subprocess

ADB_EXECUTABLE = 'adb'


class AdbError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


#
#
#

def _adb_command(command, args=[]):
    command_ = [ADB_EXECUTABLE, command] + args
    command_ = [str(x) for x in command_]
    result = subprocess.run(command_, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise AdbError(result.returncode, result.stderr)
    return result.stdout


def wait():
    _adb_command('wait-for-device')


def shell(command):
    output = _adb_command('shell', args=[command])
    fixed_output = output.replace(b'\r\r\n', b'\n')
    return fixed_output


def reboot(option=None):
    if option is None:
        args = []
    else:
        args = [option]
    _adb_command('reboot', args)


def push(local_source, remote_dest):
    _adb_command('push', [local_source, remote_dest])


def pull(remote_source, local_dest=None):
    args = [remote_source]
    if local_dest is not None:
        args.append(local_dest)
    _adb_command('pull', args)
