#!/bin/bash

# Установка rclone плагина на все ноды
NODES=("10.19.0.2" "10.19.0.3" "10.19.0.4" "10.19.0.5")
SSH_USER="root"

for node in "${NODES[@]}"; do
    echo "=== Установка rclone плагина на $node ==="

    ssh -o StrictHostKeyChecking=no "$SSH_USER@$node" << 'REMOTE_SCRIPT'
        echo "Нода: $(hostname)"

        # Создаем директории для плагина
        echo "=== Создание директорий ==="
        mkdir -p /var/lib/docker-plugins/rclone/config
        mkdir -p /var/lib/docker-plugins/rclone/cache

        # Создаем конфигурацию rclone
        echo "=== Создание конфигурации ==="
        cat > /var/lib/docker-plugins/rclone/config/rclone.conf << 'EOF'
[beget-s3]
type = s3
provider = Other
access_key_id = 19P0KBJ1QHA26KOTJ7MF
secret_access_key = MlGBLYh27rH79I6sk3B7Dnyf49Rt8WrUqAlE4vKS
region = ru-central1
endpoint = https://s3.ru1.storage.beget.cloud
EOF

        # Устанавливаем права на конфиг
        chmod 600 /var/lib/docker-plugins/rclone/config/rclone.conf

        # Удаляем старый плагин если есть
        echo "=== Удаление старого плагина ==="
        docker plugin disable rclone/docker-volume-rclone:latest --force 2>/dev/null || true
        docker plugin rm rclone/docker-volume-rclone:latest --force 2>/dev/null || true

        # Устанавливаем плагин
        echo "=== Установка плагина ==="
        docker plugin install rclone/docker-volume-rclone:latest --grant-all-permissions

        # Проверяем установку
        echo "=== Проверка установки ==="
        docker plugin ls | grep rclone || echo "Плагин не найден!"

        echo "✅ Установка завершена на $(hostname)"
REMOTE_SCRIPT

    if [ $? -eq 0 ]; then
        echo "✅ $node - успешно"
    else
        echo "❌ $node - ошибка"
    fi
    echo
done

echo "🎉 Установка плагина завершена на всех нодах!"


for node in 84.54.29.91 193.42.124.48 193.42.124.48 45.144.176.91; do
    echo "Настраиваем SSH конфиг на $node"
    ssh root@$node "
tee ~/.ssh/config > /dev/null <<'EOF'
# Конфигурация SSH для кластера
Host 10.19.0.*
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    IdentityFile ~/.ssh/id_ed25519
    LogLevel ERROR

# Алиасы нод
Host nginx-leader
    HostName 10.19.0.1
    User root
    IdentityFile ~/.ssh/id_ed25519

Host swarm-master1
    HostName 10.19.0.2
    User root
    IdentityFile ~/.ssh/id_ed25519

Host swarm-master2
    HostName 10.19.0.3
    User root
    IdentityFile ~/.ssh/id_ed25519
EOF
chmod 600 ~/.ssh/config
echo 'SSH конфиг настроен на $node'
"
done