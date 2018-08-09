#!/usr/bin/python

import paramiko
import subprocess

default_username = 'root'
default_password = 'noir0123'

# steps to convert an AIM-based setup from VXLAN to VLAN:
# 1) delete VMM domain (delete manually for now)
# 2) delete AEP (delete manually for now)
# 3) Edit /etc/neutron/plugins/ml2/ml2_conf.ini to comment out the VXLAN range
#    and add the VLAN range
# 5) edit /etc/neutron/neutron.conf to change the encap and set the VLAN range
# 4) restart neutron
# 7) Edit /etc/opflex-agent-ovs/conf.d/opflex-agent-ovs.conf on each opflex host
#    to use VLAN encap.
# 8) Add bond0 to br-fabric for each opflex host
# 9) Restart agent-ovs on each opflex host
# 10) create the AEP (manually for now)
# 11) attach the VMM domain to the AEP (manually for now)

def get_opflex_hosts():
    """Return all the hosts in the deployment running OpFlex. """
    cmd = "neutron agent-list | grep neutron-opflex-agent | awk -F'|' '{print $4}'"
    print cmd
    hosts = subprocess.check_output(['bash','-c', cmd])
    return [host.strip() for host in hosts.split("\n") if host]

def sed_generator(sed_file, sed_list):
    for sed_find, sed_replace in sed_list:
        cmd = "sed -i 's/" + sed_find + "/" + sed_replace + "/g' " +  sed_file
        print cmd
        yield cmd

def edit_local_conf(sed_file, sed_list):
    for sed_cmd in  sed_generator(sed_file, sed_list):
        subprocess.check_output(['bash','-c', sed_cmd])

def reconfigure_neutron():
    FILE = '/etc/neutron/plugins/ml2/ml2_conf.ini'
    SED_LIST = [('vni_ranges =10:100', '#vni_ranges =10:100'),
                ('#network_vlan_ranges =','network_vlan_ranges =physnet1:1000:1500')]
    edit_local_conf(FILE, SED_LIST)

    FILE = '/etc/neutron/neutron.conf'
    SED_LIST= [('\[ml2_cisco_apic\]', '\[ml2_cisco_apic\]\\nencap_mode=vlan'),
                ('\[ml2_cisco_apic\]', '\[ml2_cisco_apic\]\\nvlan_ranges=1000:1500')]
    edit_local_conf(FILE, SED_LIST)

def restart_neutron():
    cmd = 'service neutron-server restart'
    subprocess.check_output(['bash','-c', cmd])


def run_aimctl_infra_create():
    cmd = 'aimctl infra create'
    try:
        subprocess.check_output(['bash','-c', cmd])
    except:
        pass

def update_agent_ovs_cfg(ssh_client):
    """Fix the agent-ovs configuration.
    
       Change the agent-vs configuration from VXLAN to
       VLAN encapsulation. This method presumes a specific
       bridge and interface configuration of the host:
          o  currently using VXLAN encap
          o  br-fab_vxlan0 is the encap interface
          o  bond0 is a bonded interface, that uses a VPC
             connection to the leaf.
    """
    SED_LIST = [ ('"vxlan"', '"vlan"'),
        ('"encap-iface": "br-fab_vxlan0",', '"encap-iface": "bond0"'),
        ('"uplink-iface": "bond0.4093",', ' \/\/"uplink-iface": "bond0.4093",'),
        ('"uplink-vlan": 4093,', ' \/\/"uplink-vlan": 4093,'),
        ('"remote-ip": "10.0.0.32",', ' \/\/"remote-ip": "10.0.0.32",'),
        ('"remote-port": 8472', ' \/\/"remote-port": 8472')]
    FILE = '/etc/opflex-agent-ovs/conf.d/opflex-agent-ovs.conf'
    for sed_cmd in  sed_generator(FILE, SED_LIST):
        ssh_client.exec_command(sed_cmd)

def add_bridge_port(ssh_client):
    cmd = "ovs-vsctl add-port br-fabric bond0"
    print cmd
    ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)

def restart_agent_ovs(ssh_client):
    cmd = "service agent-ovs restart"
    print cmd
    ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)

def fix_opflex_agents(hosts):
    for host in hosts:
        print host
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.load_system_host_keys()
        print "connecting to " + host
        ssh.connect(host, username=default_username)
        update_agent_ovs_cfg(ssh)
        add_bridge_port(ssh)
        restart_agent_ovs(ssh)

reconfigure_neutron()
restart_neutron()
fix_opflex_agents(get_opflex_hosts())
