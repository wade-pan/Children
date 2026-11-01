#!/bin/bash
# 为当前网络接口配置 192.168.31.88 IP 别名

TARGET_IP="192.168.31.88"
NETMASK="255.255.255.0"

echo "=================================================="
echo "🌐 正在检查并配置网络接口 IP 别名: $TARGET_IP"
echo "=================================================="

# 自动获取默认活动网卡 (如 en0, en1)
IFACE=$(route get default 2>/dev/null | awk '/interface:/ {print $2}')
if [ -z "$IFACE" ]; then
    IFACE="en0"
fi

echo "📍 检测到活动网络接口: $IFACE"

# 检查是否已经存在该 IP
if ifconfig "$IFACE" | grep -q "$TARGET_IP"; then
    echo "✅ 接口 $IFACE 已经绑定了 $TARGET_IP 别名！"
else
    echo "⚙️ 正在添加 $TARGET_IP 到接口 $IFACE..."
    sudo ifconfig "$IFACE" alias "$TARGET_IP" netmask "$NETMASK"
    if [ $? -eq 0 ]; then
        echo "✅ 成功绑定 IP: $TARGET_IP 到 $IFACE"
    else
        echo "❌ 绑定失败，请确认是否具备 sudo 权限"
    fi
fi

echo ""
echo "📊 当前 $IFACE 接口 IP 配置:"
ifconfig "$IFACE" | grep "inet "

echo ""
echo "🚀 访问地址: http://$TARGET_IP:5088"
echo "=================================================="
