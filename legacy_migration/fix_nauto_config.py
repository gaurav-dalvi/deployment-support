import click
import config_info

DEFAULT_NEUTRON_CONF = '/etc/neutron/neutron.conf'
DEFAULT_PLUGIN_CONF = '/etc/neutron/plugin.ini'

class FixNautoConfig(object):

    def __init__(self, neutron_file=DEFAULT_NEUTRON_CONF,
                 plugin_file=DEFAULT_PLUGIN_CONF):
        self.plugin_file = plugin_file
        self.neutron_file = neutron_file
        self.plugin_config = config_info.ConfigInfo(plugin_file)
        self.neutron_config = config_info.ConfigInfo(neutron_file)

    def fix_nauto_config(self):
        # Configure L3 plugin for neutron/ML2 workflow
        self.neutron_config.sections_dict['DEFAULT'][
            'service_plugins'] = 'cisco_apic_l3'

        # Configure MD for neutron/ML2 workflow
        self.plugin_config.sections_dict['ml2'][
            'mechanism_drivers '] = 'cisco_apic_ml2'

        ext_prefix = 'apic_external_network:'
        # Change the external networks to pre-existing, with correct policy
        for ext_net, pol in [('l3out-1', 'l3out_1_net'),
                             ('l3out-2', 'l3out_2_net')]:
            ext_name = ext_prefix+ ext_net
            self.neutron_config.sections_dict[ext_name] = {}
            self.neutron_config.sections_dict[ext_name]['preexisting'] = 'True'
            self.neutron_config.sections_dict[ext_name]['external_epg'] = pol
        # Remove unused net
        for ext_net in ['Datacenter-Out', 'Management-Out', 'NoNatL3Out']:
            ext_name = ext_prefix + ext_net
        del(self.neutron_config.sections_dict[ext_name])

        # Add the missing apic_aim_auth section
        ip = self.neutron_config.sections_dict[
                'oslo_messaging_rabbit']['rabbit_host']
        ip = ip.translate(None, '\n')
        auth_url = 'http://%s:35357/v3' % ip
        self.neutron_config.sections_dict['apic_aim_auth'] = {
            'auth_plugin':         'v3password',
            'auth_url':            auth_url,
            'username':            'admin',
            'password':            'noir0123',
            'project_name':        'admin',
            'user_domain_name':    'default',
            'project_domain_name': 'default',
        }

    def write_config(self, neutron_out=None, plugin_out=None):
        plugin_file = plugin_out or self.plugin_file
        neutron_file = neutron_out or self.neutron_file

        self.plugin_config.write_configuration(plugin_file)
        self.neutron_config.write_configuration(neutron_file)

@click.command()
def fix_config():
    fixer = FixNautoConfig()
    fixer.fix_nauto_config()
    fixer.write_config()

if __name__ == '__main__':
    fix_config()
