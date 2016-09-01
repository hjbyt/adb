import subprocess
import shlex
from collections import namedtuple

ADB_EXECUTABLE = 'adb'


class AdbError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


class ShellError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


class Unquoted(str):
    pass


CommandResult = namedtuple('CommandResult', 'output status')


def _adb_command(command, args=[]):
    command_ = [ADB_EXECUTABLE, command] + args
    result = subprocess.run(command_, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise AdbError(result.returncode, result.stderr)
    return result.stdout


def wait():
    _adb_command('wait-for-device')


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


def _shell(command):
    print('commnad: ' + command)  # TODO: XXX
    output = _adb_command('shell', args=[command])
    fixed_output = output.replace(b'\r\r\n', b'\n')
    return fixed_output


def shell_command(command):
    command = _prepare_shell_command(command)
    return _shell(command)


def shell_commands(commands):
    commands = [_prepare_shell_command(c) for c in commands]
    command = ' ; '.join(commands)
    return _shell(command)


# STATUS_PREFIX_MAGIC = '__STATUS_QTMALS12K__='
# ECHO_STATUS_COMMAND = Unquoted('echo -n {magic}$?'.format(magic=STATUS_PREFIX_MAGIC))

# def do_command_base(command):
#     commands = [_prepare_shell_command(command), ECHO_STATUS_COMMAND]
#     output = shell_commands(commands)
#     magic_index = output.rfind(bytes(STATUS_PREFIX_MAGIC, encoding='ascii'))
#     status_index = magic_index + len(STATUS_PREFIX_MAGIC)
#     output, status = output[:magic_index], output[status_index:]
#     status = int(status)
#     return CommandResult(output, status)
#
#
# def do_command(command):
#     output, status = do_command_base(command)
#     if status != 0:
#         raise ShellError(status, output)
#     return output



STATUS_PREFIX_TEMPLATE = '__STATUS_QTMALS12K__{id}__='
STATUS_SUFFIX = '__'
ECHO_STATUS_COMMAND_TEMPLATE = 'echo -n {prefix}$?{suffix}'


def do_commands_base(commands):
    prefixes = []
    echo_commands = []
    for i in range(len(commands)):
        prefix = STATUS_PREFIX_TEMPLATE.format(id=i)
        echo_command = Unquoted(ECHO_STATUS_COMMAND_TEMPLATE.format(prefix=prefix, suffix=STATUS_SUFFIX))
        echo_commands.append(echo_command)
        prefixes.append(prefix)

    # zip the lists into one list
    commands = [j for i in zip(commands, echo_commands) for j in i]
    output = shell_commands(commands)

    results = []
    for prefix in prefixes:
        prefix = bytes(prefix, encoding='ascii')
        suffix = bytes(STATUS_SUFFIX, encoding='ascii')

        prefix_index = output.index(prefix)
        status_index = prefix_index + len(prefix)
        suffix_index = status_index + output[status_index:].index(suffix)
        next_part_index = suffix_index + len(suffix)

        command_output = output[:prefix_index]
        status = output[status_index:suffix_index]
        status = int(status)

        output = output[next_part_index:]
        result = CommandResult(command_output, status)
        results.append(result)

    return results


def do_commands(commands):
    prefixes = []
    echo_commands = []
    for i in range(len(commands)):
        prefix = STATUS_PREFIX_TEMPLATE.format(id=i)
        echo_command = Unquoted(ECHO_STATUS_COMMAND_TEMPLATE.format(prefix=prefix, suffix=STATUS_SUFFIX))
        echo_commands.append(echo_command)
        prefixes.append(prefix)

    # zip the lists into one list
    commands = [j for i in zip(commands, echo_commands) for j in i]
    output = shell_commands(commands)

    results = []
    for prefix in prefixes:
        prefix = bytes(prefix, encoding='ascii')
        suffix = bytes(STATUS_SUFFIX, encoding='ascii')

        prefix_index = output.index(prefix)
        status_index = prefix_index + len(prefix)
        suffix_index = status_index + output[status_index:].index(suffix)
        next_part_index = suffix_index + len(suffix)

        command_output = output[:prefix_index]
        status = output[status_index:suffix_index]
        status = int(status)

        output = output[next_part_index:]
        result = CommandResult(command_output, status)
        results.append(result)

    return results


STATUS_PREFIX_MAGIC = '__STATUS_QTMALS12K__='
TRAP_COMMAND = Unquoted('trap "echo -n {prefix}\$?" ERR'.format(prefix=STATUS_PREFIX_MAGIC))


def do_command_base(command):
    commands = [TRAP_COMMAND, _prepare_shell_command(command)]
    output = shell_commands(commands)
    magic_index = output.rfind(bytes(STATUS_PREFIX_MAGIC, encoding='ascii'))
    if magic_index == -1:
        return CommandResult(output, 0)
    status_index = magic_index + len(STATUS_PREFIX_MAGIC)
    output, status = output[:magic_index], output[status_index:]
    status = int(status)
    return CommandResult(output, status)


def do_command(command):
    output, status = do_command_base(command)
    if status != 0:
        raise ShellError(status, output)
    return output


MAGIC = '_output_Gjn1DpA_'
ECHO_OUTPUT_PREFIX_TEMPLATE = 'echo -n {magic}{id}:'
import re

REGEX = re.compile(b'_output_Gjn1DpA_(\d+):')


def do_commands_base(commands):
    n = len(commands)
    commands = [_prepare_shell_command(command) for command in commands]
    echo_commands = [ECHO_OUTPUT_PREFIX_TEMPLATE.format(magic=MAGIC, id=i) for i in range(n)]

    # zip the lists into one list
    commands = [j for i in zip(echo_commands, commands) for j in i]

    commands.insert(0, TRAP_COMMAND)

    output = shell_commands(commands)
    print('output:\n' + output.decode('utf8'))

    status_magic_index = output.rfind(bytes(STATUS_PREFIX_MAGIC, encoding='ascii'))
    if status_magic_index == -1:
        status = 0
    else:
        status_index = status_magic_index + len(STATUS_PREFIX_MAGIC)
        output, status = output[:status_magic_index], output[status_index:]
        status = int(status)

    matches = list(REGEX.finditer(output))

    # TODO: ughhhh. trap does't stop execution in "cat XXX; cat ZZZ" ...

    return matches


COMMANDS = ['cat /data/local/tmp/aaa', 'cat /data/local/tmp/xxx', 'cat /data/local/tmp/bbb']

# for result in do_commands_base(COMMANDS):
#     print(result)
print(do_commands_base(COMMANDS))

# print(do_command('cat /data/local/tmp/aaa'))
