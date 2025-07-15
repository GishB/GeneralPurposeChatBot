#!/bin/sh
# Enhanced IP blocking script with 5-minute expiration

BLOCKED_CONF="/etc/nginx/blocked_ips/blocked_conf"
BANNED_LOG="/var/log/nginx/banned_ips.log"
TEMP_FILE="/tmp/blocked_ips_temp"

# Default ban duration: 5 minutes
DEFAULT_BAN_MINUTES=5

# Ensure blocked_conf exists
touch "$BLOCKED_CONF"

# Function to add IP with 5-minute expiration
add_blocked_ip() {
    local ip="$1"
    local ban_minutes="${2:-$DEFAULT_BAN_MINUTES}"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local expire_time=$(date -d "+$ban_minutes minutes" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -v+${ban_minutes}M '+%Y-%m-%d %H:%M:%S')

    if ! grep -q "deny $ip;" "$BLOCKED_CONF" 2>/dev/null; then
        echo "deny $ip; # Auto-banned on $timestamp, expires: $expire_time" >> "$BLOCKED_CONF"
        echo "[$timestamp] Blocked IP: $ip for $ban_minutes minutes" >> "$BANNED_LOG"
        return 0
    fi
    return 1
}

# Function to remove expired entries
remove_expired_entries() {
    local current_time=$(date '+%Y-%m-%d %H:%M:%S')
    > "$TEMP_FILE"

    while IFS= read -r line; do
        if [ -z "$line" ] || { echo "$line" | grep -q "^#" && ! echo "$line" | grep -q "expires:"; }; then
            echo "$line" >> "$TEMP_FILE"
            continue
        fi

        if echo "$line" | grep -q "expires:"; then
            expire_time=$(echo "$line" | sed -n 's/.*expires: \([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]\).*/\1/p')

            if [ "$expire_time" \> "$current_time" ]; then
                echo "$line" >> "$TEMP_FILE"
            else
                ip=$(echo "$line" | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+\.[0-9]\+')
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] Expired: $ip" >> "$BANNED_LOG"
            fi
        else
            echo "$line" >> "$TEMP_FILE"
        fi
    done < "$BLOCKED_CONF"

    mv "$TEMP_FILE" "$BLOCKED_CONF"
}

# Command processing
case "$1" in
    "add")
        [ -n "$2" ] && add_blocked_ip "$2" "$3"
        ;;
    "cleanup")
        remove_expired_entries
        ;;
    "clear")
        echo "# Cleared all entries on $(date)" > "$BLOCKED_CONF"
        ;;
    "list")
        echo "Currently blocked IPs:"
        grep "deny" "$BLOCKED_CONF" 2>/dev/null || echo "No blocked IPs"
        ;;
    *)
        echo "Usage: $0 {add|cleanup|clear|list} [ip] [minutes]"
        exit 1
        ;;
esac
