import click
import config_info


class ConfigFileComparitor(object):

    def __init__(self, file1, file2):
        self.file1 = file1
        self.file2 = file2

    def get_config_diffs(self):
        config1 = config_info.ConfigInfo(self.file1)
        config2 = config_info.ConfigInfo(self.file2)

        f1_sections = set(config1.sections_dict.keys())
        f2_sections = set(config2.sections_dict.keys())

        f1_only_sections = f1_sections - f2_sections
        f2_only_sections = f2_sections - f1_sections
        common_sections = f1_sections & f2_sections
        f1_only_dict = {}
        f2_only_dict = {}
        common_dict = {}
        for section in list(f1_only_sections):
            f1_only_dict[section] = config1.sections_dict[section]
        for section in list(f2_only_sections):
            f2_only_dict[section] = config2.sections_dict[section]
        for section in list(common_sections):
            common_dict[section] = self.get_key_diffs(config1.sections_dict[section],
                                                      config2.sections_dict[section])
        return (f1_only_dict, f2_only_dict, common_dict)

    def print_config_diffs(self):
        f1, f2, common = self.get_config_diffs()
        for filename, cfg in ((self.file1, f1), (self.file2, f2)):
            print "Configuration in %s only:" % filename
            for skey in cfg.keys():
               print "\tsection %s:" % skey
               for key, value in cfg[skey].iteritems():
                   print "\t\t%(key)s: %(value)s" % { 'key': key, 'value': value}
        print "Configuration differences:"
        for skey in common.keys():
           print "\tsection %s:" % skey
           for key, (val1, val2) in common[skey].iteritems():
               print "\t\t%(key)s:\n\t\t\t%(file1)s: %(val1)s\n\t\t\t%(file2)s: %(val2)s" % {
                    'file1': self.file1, 'file2': self.file2, 'key': key, 'val1': val1, 'val2': val2}

    def get_key_diffs(self, config1, config2):
        diff_dict = {}
        config1_keys = set(config1.keys())
        config2_keys = set(config2.keys())
        common_keys = config1_keys & config2_keys
        config1_only_keys = config1_keys - config2_keys
        config2_only_keys = config2_keys - config1_keys
        # Add in the config1 only configuration
        for key in list(config1_only_keys):
            cfg_item = config1[key].translate(None, '[]\n')
            diff_dict[key] = (cfg_item, None)
        # Add in the config2 only configuration
        for key in list(config2_only_keys):
            cfg_item = config2[key].translate(None, '[]\n')
            diff_dict[key] = (None, cfg_item)
        # Add in common keys with dfifferent config
        for key in list(common_keys):
            cfg1_item = config1[key].translate(None, '[]\n')
            cfg2_item = config2[key].translate(None, '[]\n')
            if cfg1_item != cfg2_item:
                diff_dict[key] = (cfg1_item, cfg2_item)
        return diff_dict
    

@click.command()
@click.option('--config-file-1',
              help='First configuration file name')
@click.option('--config-file-2',
              help='Second onfiguration file name')
def compare_config_files(config_file_1, config_file_2):
    config_comparitor = ConfigFileComparitor(config_file_1, config_file_2)
    config_comparitor.print_config_diffs()

if __name__ == '__main__':
    compare_config_files()
