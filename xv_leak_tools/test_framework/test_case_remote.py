import json
import os
import ipaddress

from xv_leak_tools.log import L
from xv_leak_tools.test_framework.test_case import TestCase
from xv_leak_tools.test_device.connector_helper import ConnectorHelper
from xv_leak_tools.exception import XVEx

class TestCaseRemote(TestCase):

    def __init__(self, devices, parameters):
        super().__init__(devices, parameters)
        self.test_device = self.devices['test_device']
        self.remote_test_config = self.parameters
        self.connector_helper = ConnectorHelper(self.test_device)

    def host_ips(self):
        guest_ips = self.test_device.ips()
        guest_subnets = [ipaddress.ip_network(ip).supernet(new_prefix=24) for ip in guest_ips]

        ips = set()
        for ip in self.test_device.local_ips():
            for subnet in guest_subnets:
                if ip in subnet:
                    ips.add(ip.exploded)

        return ips

    def test(self):
        L.info("Running test {} completely on remote device".format(
            self.remote_test_config['name']))

        remote_config_path = os.path.join(self.test_device.temp_directory(), 'test_config.py')

        self.connector_helper.write_remote_file_from_contents(
            remote_config_path, json.dumps([self.remote_test_config]))

        cmd = ['./run_tests.sh', '-o', self.test_device.output_directory(),
               '-c', remote_config_path, '-x', '../contexts/internal_context.py',
               '-f', ' '.join(self.host_ips())]
        # TODO: Use .requires_root to figure out if the test needs root.
        ret, stdout, stderr = self.connector_helper.execute_command(cmd, root=True)
        test_error = False

        # TODO: Reconsider all this. Maybe we shouldn't display the output here as it screws up the
        # logs. Possibly better is to have ERROR log go to stderr then we just dump stderr here
        if stdout:
            # TODO: Make the logger send error and other to correct out file
            L.info('*' * 80)
            L.info('BEGIN stdout from remote machine:')
            L.info('*' * 80)
            for line in stdout.splitlines():
                # TODO: Logger not satisfying my needs!
                print(line)
                if "Ran 1 / 1 tests: 0 passes, 0 fails, 1 errors" in line:
                    test_error = True
            L.info('*' * 80)
            L.info('END stdout from remote machine')
            L.info('*' * 80)

        if stderr:
            L.error('*' * 80)
            L.error('BEGIN stderr from remote machine:')
            L.error('*' * 80)
            for line in stderr.splitlines():
                # TODO: Logger not satisfying my needs!
                print(line)
            L.error('*' * 80)
            L.error('END stderr from remote machine')
            L.error('*' * 80)

        if ret == 0:
            L.info('Remote test execution succeeded')
            return

        if test_error:
            L.error('Remote test execution failed with an error')
            raise XVEx("Remote test error")

        L.error('Remote test execution failed')
        self.failTest('Remote test run failed!')
