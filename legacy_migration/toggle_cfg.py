import click
import config_info

DEFAULT_NEUTRON_CONF = '/etc/neutron/neutron.conf'
DEFAULT_PLUGIN_CONF = '/etc/neutron/plugin.ini'

class ToggleConfig(object):

    def __init__(self, config_file_names):
        self.cfg_objs = {}
        self.config_file_names = config_file_names
        self.config_changes = {'core_plugin': {
                                   'old': 'ml2',
                                   'new': 'ml2plus'},
                               'service_plugins': {
                                   'old': 'cisco_apic_l3',
                                   'new': 'apic_aim_l3,group_policy,ncp'},
                               'policy_drivers': {
                                   'old': 'implicit_policy,apic',
                                   'new': 'aim_mapping'},
                               'mechanism_drivers ': {
                                   'old': 'cisco_apic_ml2',
                                   'new': 'apic_aim'},
                               'extension_drivers': {
                                   'old': None,
                                   'new': 'apic_aim,port_security'}
                              }

    def _get_legacy_config(self):
        if not self.config_file_names:
            self.config_file_names = (DEFAULT_NEUTRON_CONF, DEFAULT_PLUGIN_CONF)
        for filename in self.config_file_names:
            self.cfg_objs[filename] = config_info.ConfigInfo(filename)

    def _set_config(self, config_type):
        self._get_legacy_config()
        for cfg_item in self.config_changes.keys():
            for cfg_obj in self.cfg_objs.values():
                section, _ = cfg_obj.find_config_item(cfg_item)
                if section:
                    value = self.config_changes[cfg_item][config_type]
                    cfg_obj.set_section_config(section, cfg_item, value)
                    # Keep going, just in case it's in more than one file
                                  
    def old_config(self):
        self._set_config('old')
        for cfg_obj in self.cfg_objs.values():
            if 'neutron.conf' in cfg_obj.filename :
                cfg_obj.set_section_config('DEFAULT',
                                           'agent_down_time', '75')

    def new_config(self):
        self._set_config('new')
        for cfg_obj in self.cfg_objs.values():
            if 'neutron.conf' in cfg_obj.filename :
                cfg_obj.set_section_config('DEFAULT',
                                           'agent_down_time', '7200')

    def write_config(self, neutron_out=None, plugin_out=None):
        for cfg_obj in self.cfg_objs.values():
            cfg_obj.write_configuration()


@click.command()
@click.option('--config-file', multiple=True,
              help='Configuration file name')
@click.option('--toggle', default='new',
              help="Configuration to use. Use 'new' for merged, 'old' for legacy")
def toggle_config(config_file, toggle):
    toggle_config = ToggleConfig(config_file)
    if toggle == 'new':
        toggle_config.new_config()
    elif toggle == 'old':
        toggle_config.old_config()
    toggle_config.write_config()

if __name__ == '__main__':
    toggle_config()
