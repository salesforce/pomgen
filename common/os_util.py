"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from contextlib import contextmanager
import os
import subprocess


@contextmanager
def cd(newdir):
    """
    Easy way to cd then cd back to original path.
    Excellent for use when running command lines and not to muddy global state
    Usage:
        with fileutil.cd('some_new_exciting_path'):
            # play in the wonderful new path
            subprocess.check_output('ls')
        'some_new_exciting_path' is only valid in the "with" block
    :param newdir:
    :return:
    """
    prevdir = os.getcwd()
    os.chdir(newdir)
    try:
        yield
    finally:
        os.chdir(prevdir)


def output_args(wrapped_func):
    """
    Simple method that outputs to stdout the args of a check_output command
    Usage:
        my_check_output = output_args(subprocess.check_output)
        my_check_output(...) # use like check_output
    :param wrapped_func:
    :return:
    """

    def result(*args, **kargs):
        print(' '.join(args[0]))
        output = wrapped_func(*args, **kargs)
        # python3 returns byte objects, python2 return strings
        try:
            return output.decode()
        except AttributeError:
            return output

    return result


def run_cmd(cmd, cwd=os.getcwd()):
    """
    Run OS command return stdout (only).
    It will throw a CalledProcessError if non-zero is returned.
    This method can be ran in python 2 and 3

    :param cmd: command to run
    :param cwd: directory to run command in
    :return: stdout
    """
    process = subprocess.Popen(cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE)
    return_code = process.wait()
    output = process.stdout.read()
    # python3 returns byte objects, python2 return strings
    try:
        output = output.decode()
    except AttributeError:
        pass
    if return_code is not 0:
        raise subprocess.CalledProcessError(return_code, cmd, output)
    return output
