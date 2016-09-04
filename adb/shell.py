import subprocess
import shlex
from collections import namedtuple
from adb.adb_base import shell


class Unquoted(str):
    pass


class ShellError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


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
        return shlex.quote(string)


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


def run_script(script, cwd=None):
    pass


print(do_command('echo asdf'))
