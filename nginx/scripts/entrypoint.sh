#!/bin/sh
# Enhanced entrypoint for nginx container with 1-minute monitoring

# Create necessary directories
mkdir -p /etc/nginx/blocked_ips
mkdir -p /var/log/nginx

# Initialize blocked IPs file
touch /etc/nginx/blocked_ips/blocked_conf

# Set proper permissions
chown -R nginx:nginx /etc/nginx/blocked_ips
chown -R nginx:nginx /var/log/nginx

# Make scripts executable
chmod +x /etc/nginx/scripts/block_ip.sh
chmod +x /etc/nginx/scripts/process_banned_ips.sh

# Start background process for IP monitoring with 1-minute interval
(
while true; do
    sleep 60 # Check every minute
    /etc/nginx/scripts/process_banned_ips.sh
done
) &

# Start nginx
exec nginx -g 'daemon off;'
