#!/bin/bash
PRIMARY_NIC="en0"
ALIAS_IP="192.168.31.13"
NETMASK="255.255.255.0"

echo "=== 配置 macOS IP 别名: ${ALIAS_IP} on ${PRIMARY_NIC} ==="
sudo ifconfig ${PRIMARY_NIC} alias ${ALIAS_IP} ${NETMASK}

if [ $? -eq 0 ]; then
    echo "✅ IP 别名配置成功！现在可以在局域网中直接访问: http://${ALIAS_IP}:5089"
else
    echo "❌ 配置失败，请检查网卡名称或输入管理员密码。"
fi
