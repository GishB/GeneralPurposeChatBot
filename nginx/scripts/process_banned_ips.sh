#!/bin/sh
# Process banned IPs with 5-minute expiration and 1-minute cleanup

BANNED_LOG="/var/log/nginx/banned_ips.log"
BLOCK_SCRIPT="/etc/nginx/scripts/block_ip.sh"

# Always cleanup expired entries first
"$BLOCK_SCRIPT" cleanup

# Process new banned IPs
if [ -f "$BANNED_LOG" ] && [ -s "$BANNED_LOG" ]; then
    tail -n 100 "$BANNED_LOG" | awk '{print $1}' | sort -u | while read -r ip; do
        if [ -n "$ip" ] && [ "$ip" != "-" ]; then
            "$BLOCK_SCRIPT" add "$ip" 5  # 5-minute ban
        fi
    done

    > "$BANNED_LOG"  # Clear processed log

    # Reload nginx if config is valid
    if nginx -t >/dev/null 2>&1; then
        nginx -s reload
    fi
fi
