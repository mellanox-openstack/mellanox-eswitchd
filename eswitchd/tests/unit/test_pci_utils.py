import contextlib
import mock
import sys
sys.modules['ethtool'] = mock.Mock()

from eswitchd.tests import base
from eswitchd.utils import pci_utils

class TestPciUtils(base.TestCase):

    def setUp(self):
        super(TestPciUtils, self).setUp()
        self.pci_utils = pci_utils.pciUtils()

    def _assert_get_auto_pf_error(self, log_msg):
        with mock.patch.object(pci_utils, 'LOG') as LOG:
            self.assertRaises(SystemExit,
                              self.pci_utils.get_auto_pf, 'fabtype')
            LOG.error.assert_called_with(log_msg)

    def _test_get_auto_pf(self, devices=[], is_vendor_pf=True,
                          is_sriov=True, valid_fabric_type=True):
        ifcs = devices if valid_fabric_type else []
        return contextlib.nested(
            mock.patch('ethtool.get_devices', return_value=devices),
            mock.patch.object(self.pci_utils, 'verify_vendor_pf',
                              return_value=is_vendor_pf),
            mock.patch.object(self.pci_utils, 'is_sriov_pf',
                              return_value=is_sriov),
            mock.patch.object(self.pci_utils, 'filter_ifcs_module',
                              return_value=ifcs),
        )

    def test_get_auto_pf_no_mlnx_devices(self):
        log_msg = "Didn't find any Mellanox devices."
        with self._test_get_auto_pf():
            self._assert_get_auto_pf_error(log_msg)

        log_msg = "Didn't find any Mellanox devices."
        with self._test_get_auto_pf(devices=['device-1'], is_vendor_pf=False):
            self._assert_get_auto_pf_error(log_msg)

    def test_get_auto_pf_no_mlnx_sriov_devices(self):
        log_msg = "Didn't find Mellanox NIC with SR-IOV capabilities."
        with self._test_get_auto_pf(devices=['device-1'], is_sriov=False):
            self._assert_get_auto_pf_error(log_msg)

    def test_get_auto_pf_wrong_fabric_type(self):
        log_msg = ("Didn't find Mellanox NIC of type fabtype with "
                   "SR-IOV capabilites.")
        with self._test_get_auto_pf(devices=['device-1'],
                                    valid_fabric_type=False):
            self._assert_get_auto_pf_error(log_msg)

    def test_get_auto_pf_multiple_pfs(self):
        devices = ['device-1', 'device-2']
        log_msg = "Found multiple PFs %s. Configure Manually." % devices
        with self._test_get_auto_pf(devices=devices):
            self._assert_get_auto_pf_error(log_msg)
