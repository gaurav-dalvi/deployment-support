#!/usr/bin/python

import paramiko
import subprocess


default_username = 'root'
default_password = 'noir0123'

# for the first compute node:
# 1) edit the /etc/neutron/dhcp-agent.ini configuration file to set "force_metadata = True"
# 2) restart neutron-dhcp-agent
# 3) scp the /etc/neutron/metadata_agent.ini file to all the other computes

# for all the computes
# 1) edit the /etc/opflex-agent-ovs/conf.d/opflex-agent-ovs.conf to set "encrypted"
# 2) kill supervisord
# 3) delete all the flows in br-fabric
# 4) restart agent-ovs
# 5) clear iptables rule created by installer

CLEAR_IP_TABLES_RULE='iptables -D INPUT -j REJECT --reject-with icmp-host-prohibited'

def update_dhcp_agent_cfg(ssh_client):
    """Fix the neutron-dhcp-agent configuration..
    
       Our nauto installer has a bug where it fails to configure
       the DHCP agent to use force_metadata (needed because there is
       no reference implementation neutron router in the network).
       This sets the force_metadata option to True and restarts
       the neutron-dhcp-agent service.
    """
    SED_FIND = '#force_metadata = false'
    SED_REPLACE = 'force_metadata = true'
    FILE = '/etc/neutron/dhcp_agent.ini'
    cmd = "sed -i 's/" + SED_FIND + "/" + SED_REPLACE + "/g' " +  FILE
    print cmd
    ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)
    cmd = "service neutron-dhcp-agent restart"
    print cmd
    ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)

def restart_metadata_agent(ssh_client):
    """Restart metdata agent.
    
       Our nauto installer has a bug where it fails to configure
       the metadata agent correctly on all compute hosts except
       the first. This function kills supervisord on the host,
       deletes all the flows on br-fabric, and restarts the neutron-opflex-agent,
       which will use create new metadata agents using the updated
       configuration file.
    """
    cmd = "systemctl stop neutron-metadata-agent"
    print cmd
    ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)
    cmd = "kill `ps -ef | grep [s]upervisord | awk -F' ' '{print $2}'`"
    print cmd
    ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)
    cmd = "ovs-ofctl del-flows br-fabric"
    print cmd
    ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)
    cmd = "service neutron-opflex-agent restart"
    print cmd
    ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)

def fix_br_fabric(ssh_client):
    cmd = "ovs-vsctl del-br br-tun"
    print cmd
    ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)
    cmd1 = "ovs-vsctl --may-exist add-port br-fabric br-fab_vxlan0 -- "
    cmd2 = "set Interface br-fab_vxlan0 type=vxlan options:remote_ip=flow "
    cmd3 = "options:key=flow options:dst_port=8472"
    cmd = cmd1 + cmd2 + cmd3
    print cmd
    ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)

def restart_agent_ovs(ssh_client):
    cmd = "service agent-ovs restart"
    print cmd
    ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)

def clear_iptables_rule(ssh_client):
    cmd = CLEAR_IP_TABLES_RULE
    print cmd
    ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)

def update_agent_ovs_cfg(ssh_client):
    """Fix the agent-ovs configuration..
    
       Our nauto installer has a bug where it configures
       the SSL option as "enabled" in agent-ovs, which is
       an invalid value. This function replaces enabled
       with the correct value of "encrypted"
    """
    SED_FIND = '"mode": "enabled"'
    SED_REPLACE = '"mode": "encrypted"'
    FILE = '/etc/opflex-agent-ovs/conf.d/opflex-agent-ovs.conf'
    cmd = "sed -i 's/" + SED_FIND + "/" + SED_REPLACE + "/g' " +  FILE
    print cmd
    ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)

def update_agent_neutron_cfg(ssh_client):
    SED_FIND = '# root_helper_daemon =.*'
    SED_REPLACE = 'root_helper_daemon = '
    FILE = '/etc/neutron/neutron.conf'
    cmd = "sed -i 's/" + SED_FIND + "/" + SED_REPLACE + "/g' " +  FILE
    print cmd
    ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)

def get_dhcp_hosts():
    """Return compute hosts running DHCP agent.
    
       Return all compute hosts running the DHCP agent.
    """
    cmd = "neutron agent-list | grep dhcp | awk -F'|' '{print $4}'"
    print cmd
    hosts = subprocess.check_output(['bash','-c', cmd])
    return [host.strip() for host in hosts.split("\n") if host]

def get_compute_hosts():
    """Return all the compute hosts in the deployment. """
    #cmd = "neutron agent-list -F host -f value | sort | uniq"
    cmd = "nova service-list  | grep nova-compute | awk -F'|' '{print $4}'"
    print cmd
    hosts = subprocess.check_output(['bash','-c', cmd])
    return [host.strip() for host in hosts.split("\n") if host]

def update_metadata_agent_cfg(hosts):
    """Fix the neutron-metaata-agent configuration.
    
       Our nauto installer has a bug where it fails to configure
       the metadata agent correctly on all compute hosts except
       the first. This scp's the configuration file from the first
       compute host to all the others
    """
    # get the file from the first compute host
    PATH = '/etc/neutron/'
    FILE = 'metadata_agent.ini'
    cmd = ('scp root@%(host)s:%(path)s%(file)s .' %
           {'host': hosts[0], 'file': FILE, 'path': PATH})
    print cmd
    subprocess.check_output(['bash','-c', cmd])
    # now copy it back down to the other compute hosts
    for host in hosts[1:]:
        cmd = ("scp %(file)s root@%(host)s:%(path)s%(file)s" %
               {'host': host, 'file': FILE, 'path': PATH})
        print cmd
        subprocess.check_output(['bash','-c', cmd])

def get_metadata_config():
    """Get the metadata configuration from the. """
    cmd = "neutron agent-list -F host -f value | sort | uniq"
    print cmd
    hosts = subprocess.check_output(['bash','-c', cmd])
    return [host.strip() for host in hosts.split("\n") if host]


def cleanup_dead_agents():
    cmd = "for agent in `neutron agent-list | grep xxx | awk -F'|' '{print $2}'`; do neutron agent-delete $agent; done"
    print cmd
    subprocess.check_output(['bash','-c', cmd])

# Main code
cleanup_dead_agents()
dhcp_host = get_dhcp_hosts()[0]
print "DHCP host is " + dhcp_host
all_hosts = get_compute_hosts()
update_metadata_agent_cfg(all_hosts)
for host in all_hosts:
    print host
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.load_system_host_keys()
    print "connecting to " + host
    ssh.connect(host, username=default_username)
    if host == dhcp_host:
        update_dhcp_agent_cfg(ssh)
    #update_agent_ovs_cfg(ssh)
    #update_agent_neutron_cfg(ssh)
    if host != all_hosts[0]:
        restart_metadata_agent(ssh)
    fix_br_fabric(ssh)
    restart_agent_ovs(ssh)
    clear_iptables_rule(ssh)

cmd1 = "openstack image create --public --disk-format qcow2 "
cmd2 = "--container-format bare --file cirros-0.3.5-x86_64-disk.img cirros.new"
cmd = cmd1 + cmd2
print cmd
hosts = subprocess.check_output(['bash','-c', cmd])
cmd1 = "neutron net-create l3out-2 --router:external True --shared "
cmd2 = "--provider:network_type opflex --provider:physical_network physnet1"
cmd = cmd1 + cmd2
print cmd
hosts = subprocess.check_output(['bash','-c', cmd])
cmd1 = "neutron subnet-create l3out-2 60.60.60.0/24 --name ext_subnet "
cmd2 = "--gateway 60.60.60.1 --disable-dhcp"
cmd = cmd1 + cmd2
print cmd
hosts = subprocess.check_output(['bash','-c', cmd])
