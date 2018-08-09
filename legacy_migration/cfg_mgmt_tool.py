# Copyright (c) 2018 Cisco Systems
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

# This module contains a bunch of helper classes
# that are used to facilitate and somewhat automate
# migration from the legacy plugins to the merged plugin
import click
import config_info

# Where things usually live
NEUTRON_CONF = '/etc/neutron/neutron.conf'
PLUGIN_CONF = '/etc/neutron/plugin.ini'
AIM_CFG_FILE_NAME = '/etc/aim/aim.conf'
AIMCTL_CFG_FILE_NAME = '/etc/aim/aimctl.conf'


# Default values for configuration. Note that
# we use this as a way to define all the possible
# keys/configuration for a given section -- if you
# want a sepcific configuration to be migrated, it
# must be represented here
AIM_DEFAULT_CFG = {'DEFAULT': 
                       {'debug': 'False',
                        'rpc_backend': 'rabbit',
                        'control_exchange': 'neutron',
                        'default_log_levels': 'neutron.context=ERROR'},
                   'oslo_messaging_rabbit':
                       {'rabbit_host': None,
                        'rabbit_hosts': None,
                        'rabbit_userid': None,
                        'rabbit_password': None,
                        'rabbit_ha_queues': 'False',
                        'rabbit_use_ssl': None},
                   'database':
                       {'connection': None},
                   'aim':
                       {'agent_down_time': '75',
                        'poll_config': 'False',
                        'aim_system_id': None},
                   'apic':
                       {'apic_hosts': None,
                        'apic_username': 'admin',
                        'apic_password': 'noir0123',
                        'apic_use_ssl': 'True',
                        'verify_ssl_certificate': 'False',
                        'scope_names': 'True'}
                  }

AIMCTL_DEFAULT_CFG = {'DEFAULT': 
                          {'apic_system_id': None},
                      'apic':
                          {'scope_infra': 'False',
                           'apic_provision_infra': 'False',
                           'apic_provision_hostlinks': 'False',
                           'apic_vmm_type': None,
                           'apic_vlan_ns_name': None,
                           'apic_node_profile': None,
                           'apic_entity_profile': None,
                           'apic_function_profile': None,
                           'apic_vpc_pairs': None}
                     }

class AimConfig(object):
    """Update aim.conf and aimctl.conf files.

    Migration from the legacy plugin to AIM requires
    extracting configuraiton paramters from the existing
    neutron configuration and generating new configuration
    files for AIM.
    """

    def __init__(self, config_file_names):
        self.aim_filename = AIM_CFG_FILE_NAME
        self.aimctl_filename = AIMCTL_CFG_FILE_NAME
        self.aim_default_cfg = AIM_DEFAULT_CFG
        self.aimctl_default_cfg = AIMCTL_DEFAULT_CFG
        self.config_file_names = config_file_names
        self.cfg_objs = {}

    def get_legacy_config(self):
        if not self.config_file_names:
            self.config_file_names = (NEUTRON_CONF, PLUGIN_CONF)
        for filename in self.config_file_names:
            self.cfg_objs[filename] = config_info.ConfigInfo(filename)

    def _update_section(self, new_section, old_section, params):
        # Some of the parameters live in a section with a
        # different name.
        for cfg_file in self.cfg_objs.keys():
            cfg_obj = self.cfg_objs[cfg_file]
            cfg = cfg_obj.get_section_config(old_section)
            if cfg:
                break
        if not cfg:
            print "No section named %(section)s" % {'section': old_section}
            return
        for k in cfg.keys():
            if k in params[new_section].keys():
                params[new_section][k] = cfg[k]

    def _update_parameters(self, parameters, configurations):
        for section in parameters.keys():
            for configuration in configurations:
                cfg = configuration.get_section_config(section)
                for k in cfg.keys():
                    if k in parameters[section]:
                        parameters[section][k] = cfg[k]

    def _get_vmm_dom_config(self):
        vmdom_config = {}
        for config in self.cfg_objs.values():
            for section in config.sections_dict.keys():
                if section.startswith('apic_vmdom'):
                    vmdom_config.setdefault(section, {})
                    cfg = config.get_section_config(section)
                    for k in cfg.keys():
                        vmdom_config[section][k] = cfg[k]
        return vmdom_config

    def _get_physical_config(self):
        phys_config = {}
        for config in self.cfg_objs.values():
            for section in config.sections_dict.keys():
                if (section.startswith('apic_switch') or
                        section.startswith('apic_physdom') or
                        section.startswith('apic_physical_network')):
                    phys_config.setdefault(section, {})
                    cfg = config.get_section_config(section)
                    for k in cfg.keys():
                        phys_config[section][k] = cfg[k]
        return phys_config

    def _find_config_item(self, config_name):
        for config in self.cfg_objs.values():
            for section in config.sections_dict.keys():
                if config.sections_dict[section].get(config_name):
                    return config.sections_dict[section][config_name]
        return None
                
    def create_aim_config(self):
        new_section = 'apic'
        old_section = 'ml2_cisco_apic'

        params = self.aim_default_cfg
        self._update_parameters(params, self.cfg_objs.values())
        self._update_section(new_section, old_section, params)

        # THe system ID needs to be migrated to AIM
        apic_system_id = self._find_config_item('apic_system_id')
        params['aim']['aim_system_id'] = apic_system_id

        # Create aim.conf
        aim_cfg = config_info.ConfigInfo(self.aim_filename,
                                         config_dict = params)
        aim_cfg.write_configuration()

        params = self.aimctl_default_cfg
        self._update_parameters(params, self.cfg_objs.values())
        self._update_section(new_section, old_section, params)
 
        # For aimctl.conf, there are some sections that have
        # unique names that need to be added from the legacy
        # configuration
        phys_config = self._get_physical_config()
        for section in phys_config.keys():
            params[section] = phys_config[section]

        # We have to migrate the VMM domains. For now, we
        # just worry about the one in apic_domain_name
        apic_domain_name = self._find_config_item('apic_domain_name')
        if apic_domain_name:
            vmm_dom_name = 'apic_vmdom:' + apic_domain_name
            vmm_dom_name = vmm_dom_name.translate(None, '\n')
            # TODO: add vlan_ranges? Are these only in APIC?
            params[vmm_dom_name] = {}

        # TODO: how to get physdoms?

        # Create aimtcl.conf
        aimctl_cfg = config_info.ConfigInfo(self.aimctl_filename,
                                            config_dict = params)
        aimctl_cfg.write_configuration()


class NeutronConfig(object):
    """Update neutron configuration files.

    The neutron configuration files need updating for several
    steps in the legacy plugin migration process:
    1) Update the configuration with the needed changes
       in order to run the validation tool. This amounts
       to updating the service_plugins, mechanism_drivers,
       core_plugin, etc.
    2) Updating configuration state from the legacy ml2_cisco_apic
       section to the new ml2_apic_aim section
    """
    def __init__(self):
        self.aim_filename = AIM_CFG_FILE_NAME
        self.aimctl_filename = AIMCTL_CFG_FILE_NAME
        self.aim_default_cfg = AIM_DEFAULT_CFG
        self.aimctl_default_cfg = AIMCTL_DEFAULT_CFG

    # TODO: create APIs for the steps listed above
    #def migrate_md_config(self):
        

@click.command()
@click.option('--config-file', multiple=True,
              help='Configuration file name')
def make_aim_cfg(config_file):
    aim_cfg = AimConfig(config_file)
    aim_cfg.get_legacy_config()
    aim_cfg.create_aim_config()
    click.echo("Generated aim.conf and aimctl.conf.")

if __name__ == '__main__':
    make_aim_cfg()
