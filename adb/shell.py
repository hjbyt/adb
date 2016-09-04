import subprocess
import shlex
from collections import namedtuple
import tempfile
from pathlib import Path, PurePosixPath
import random
from contextlib import contextmanager
import io
import tarfile
from adb.adb_base import shell, push


class Unquoted(str):
    pass


class ShellError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


BUSYBOX = '/data/local/tmp/busybox'

STATUS_PREFIX_MAGIC = '__STATUS_QTMALS12K__='
ECHO_STATUS_COMMAND = Unquoted('echo -n {magic}$?'.format(magic=STATUS_PREFIX_MAGIC))

CommandResult = namedtuple('CommandResult', 'output status')


#
#
#

def _quote_if_needed(string):
    if isinstance(string, Unquoted):
        return string
    else:
        return shlex.quote(str(string))


def _prepare_shell_command(command):
    """command should be either a (possibly Unqoated) string or a list of (possibly Unqoated) strings."""
    if isinstance(command, str):
        parts = shlex.split(command)
        if isinstance(command, Unquoted):
            command = [Unquoted(p) for p in parts]
        else:
            command = parts

    parts = [_quote_if_needed(part) for part in command]

    # Note: parts have to be merged, otherwise commands like ['echo', 'a   b'] are handled like 'echo a   b'
    command = subprocess.list2cmdline(parts)
    return command


def _shell_command(command):
    command = _prepare_shell_command(command)
    return shell(command)


def _shell_commands(commands):
    commands = [_prepare_shell_command(c) for c in commands]
    command = ' ; '.join(commands)
    return shell(command)


def do_command_base(command):
    commands = [_prepare_shell_command(command), ECHO_STATUS_COMMAND]
    output = _shell_commands(commands)
    magic_index = output.rfind(bytes(STATUS_PREFIX_MAGIC, encoding='ascii'))
    status_index = magic_index + len(STATUS_PREFIX_MAGIC)
    output, status = output[:magic_index], output[status_index:]
    status = int(status)
    return CommandResult(output, status)


def do_command(command):
    output, status = do_command_base(command)
    if status != 0:
        raise ShellError(status, output)
    return output


def run_script(script, args=[], remote_dest_dir=None):
    temp_script_name = 'temp_script_%d' % random.randrange(10000)
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        temp_script_path = temp_dir / temp_script_name
        with io.open(str(temp_script_path), mode='w', newline='') as temp_script_file:
            temp_script_file.write(script)
        return execute_file(temp_script_path, args=args, remote_dest_dir=remote_dest_dir)


@contextmanager
def temp_remote_file(local_file_path, remote_dest_dir=None):
    if remote_dest_dir is None:
        remote_dest_dir = '/data/local/tmp'
    local_file_path = Path(local_file_path)
    remote_dest_dir = PurePosixPath(remote_dest_dir)
    remote_dest = remote_dest_dir / local_file_path.name
    push(local_file_path, remote_dest)
    try:
        yield remote_dest
    finally:
        do_command(['rm', remote_dest])


def execute_file(local_file_path, args=[], remote_dest_dir=None):
    with temp_remote_file(local_file_path, remote_dest_dir) as remote_file:
        do_command(['chmod', '700', remote_file])
        return do_command([remote_file] + args)


def do_commands(commands, trap=True, cd=None):
    commands_ = commands[:]
    if cd is not None:
        commands_.insert(0, 'cd %s' % str(cd))
    if trap:
        commands_.insert(0, 'trap exit ERR')
    script = '\n'.join(commands_)
    return run_script(script)


def push_extract_tar(local_tar):
    with temp_remote_file(local_tar) as temp_tar:
        do_command([BUSYBOX, 'tar', 'xfz', temp_tar])


def push_files(files):
    if isinstance(files, dict):
        files = files.items()
    temp_tar_name = 'temp_%d.tar.gz' % random.randrange(10000)
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        temp_tar_path = str(temp_dir / temp_tar_name)
        with tarfile.open(temp_tar_path, mode='w:gz') as temp_tar:
            for local_source, remote_dest in files:
                temp_tar.add(local_source, arcname=remote_dest)
        push_extract_tar(temp_tar_path)
