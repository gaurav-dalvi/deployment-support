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


class ConfigInfo(object):
    """Configuration File Interface.

    Class to get the information from an OpenStack configuration file,
    parse the file for each section, and store the configuration data
    as key-value pairs (key/value are separated by first = sign). It
    stores this information as dicts of dicts, so that the configuration
    data can be looked up by section.
    """
    def __init__(self, config_file_name, config_dict=None):
        self.filename = config_file_name
        if config_dict:
            self.sections_dict = config_dict
        else:
            fd = open(config_file_name, 'r')
            self.all_lines = fd.readlines()
            self.sections_dict = {}
            self._parse_config_by_sections()

    def _get_valid_config(self, lines):
        clean_config = [cap for cap in lines
                        if not cap.startswith('#')
                        and not cap == '\n']
        cfg_dict = {}
        for cfg_item in clean_config:
            k, v = cfg_item.split('=', 1)
            cfg_dict[k] = v
        return cfg_dict

    def find_config_item(self, config_name):
        for section_name in self.sections_dict.keys():
            section_cfg = self.sections_dict[section_name]
            if config_name in section_cfg:
                return section_name, section_cfg[config_name]
        return None, {}

    def set_section_config(self, section_name, key, value):
        self.sections_dict[section_name][key] = value

    def get_section_config(self, section_name):
        return self.sections_dict.get(section_name, {})

    def _parse_config_by_sections(self):
        capture_lines = []
        section_name = None
        for index in range(len(self.all_lines)):
            a_line = self.all_lines[index]
            if a_line.startswith('['):
                new_section = a_line.translate(None, '[]\n')
                if not section_name:
                    section_name = new_section
                    self.sections_dict.setdefault(section_name, {})
                else:
                    section_dict = self._get_valid_config(capture_lines)
                    self.sections_dict[section_name] = section_dict
                    section_name = new_section
                    capture_lines = []
            elif section_name:
                capture_lines.append(a_line)
        # Capture final section
        section_dict = self._get_valid_config(capture_lines)
        self.sections_dict[section_name] = section_dict
        return capture_lines

    def write_configuration(self, filename=None):
        output_file = filename or self.filename
        if not output_file:
            print "Can't write configuration -- no valid filename configured"
            return
        fd = open(output_file, 'w+')
        for section in self.sections_dict.keys():
            fd.write('[' + section + ']\n')
            for cfg_key in self.sections_dict[section].keys():
                if not self.sections_dict[section][cfg_key]:
                    write_string = '#' + cfg_key + '=\n'
                else:
                    write_string = cfg_key + '=' + self.sections_dict[section][cfg_key]
                    if not '\n' in write_string:
                        write_string += '\n'
                fd.write(write_string)
        fd.close()
