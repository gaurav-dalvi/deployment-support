#!/bin/sh
yum install aci-integration-module.noarch
aimctl -c /etc/neutron/neutron.conf db-migration upgrade
python cfg_mgmt_tool.py 
aimctl config replace
systemctl start aim-event-service-rpc
systemctl start aim-event-service-polling
systemctl start aim-aid
echo "Make sure that aim is running, then hit return"
aimctl infra create
aimctl manager load-domains

