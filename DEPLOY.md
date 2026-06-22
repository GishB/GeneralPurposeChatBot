# Деплой GeneralPurposeChatBot в Kubernetes

## Требования

- Доступ к кластеру Yandex Cloud Kubernetes (`kubectl` настроен).
- Docker с поддержкой `--platform linux/amd64`.
- Аутентификация в Yandex Container Registry (`yc cr login` или `docker login`).
- Установленные инструменты: `kubectl`, `base64`.

## 1. Сборка и публикация образа

```bash
cd GeneralPurposeChatBot

# Укажите актуальную версию
export IMAGE_TAG="v0.3.0-k8s"

# Сборка
docker build \
  --platform linux/amd64 \
  -t cr.yandex/crpinqlic51h4qsoph6e/general-purpose-chatbot:${IMAGE_TAG} \
  -f mlops/docker/Dockerfile .

# Пуш в YCR
docker push cr.yandex/crpinqlic51h4qsoph6e/general-purpose-chatbot:${IMAGE_TAG}
```

Обновите тег образа в файле `k8s/unionchatbot/03-deployment.yaml`:

```yaml
image: cr.yandex/crpinqlic51h4qsoph6e/general-purpose-chatbot:v0.3.0-k8s
```

## 2. Подготовка секретов

Запустите helper и вставьте закодированные значения в `k8s/unionchatbot/02-secret.yaml`:

```bash
bash scripts/prepare-secrets.sh
```

Или вручную:

```bash
echo -n 'your-value' | base64
```

## 3. Применение манифестов

Выполняйте строго в указанном порядке:

```bash
# 3.1. Создание namespace
kubectl apply -f k8s/unionchatbot/00-namespace.yaml

# 3.2. ConfigMap и Secret
kubectl apply -f k8s/unionchatbot/01-configmap.yaml
kubectl apply -f k8s/unionchatbot/02-secret.yaml

# 3.3. Создание базы данных (Job в sevenelement-db namespace)
# Убедитесь, что CNPG кластер запущен:
kubectl wait --for=condition=ready pod -l app=sevenelement-db -n sevenelement-db --timeout=120s
kubectl apply -f k8s/unionchatbot/09-job-create-db.yaml

# Дождитесь завершения Job:
kubectl wait --for=condition=complete job/create-unionchatbot-db -n sevenelement-db --timeout=120s

# 3.4. Основные рабочие нагрузки
kubectl apply -f k8s/unionchatbot/03-deployment.yaml
kubectl apply -f k8s/unionchatbot/04-service.yaml
kubectl apply -f k8s/unionchatbot/05-hpa.yaml
kubectl apply -f k8s/unionchatbot/06-pdb.yaml

# 3.5. Сетевые политики
kubectl apply -f k8s/unionchatbot/07-network-policy.yaml

# 3.6. Мониторинг
kubectl apply -f k8s/unionchatbot/08-service-monitor.yaml

# 3.7. Обновление политик существующей инфраструктуры
kubectl apply -f k8s/sevenelement/manifests/08-network-policy.yaml
```

## 4. Проверка деплоя

```bash
# Статус подов
kubectl get pods -n unionchatbot

# Логи
kubectl logs -n unionchatbot -l app=general-purpose-chatbot --tail=100 -f

# Проверка проб через port-forward
kubectl port-forward -n unionchatbot svc/general-purpose-chatbot 8080:80

# В другом терминале:
curl http://localhost:8080/health
curl http://localhost:8080/ready
curl http://localhost:8080/metrics
```

## 5. Проверка доступности из sevenelement-backend

Выполните внутри пода `sevenelement-backend`:

```bash
kubectl exec -n sevenelement-backend deploy/sevenelement-backend -- \
  curl -s http://general-purpose-chatbot.unionchatbot.svc.cluster.local/health
```

Ожидаемый ответ:

```json
{"status":"running"}
```

## 6. Интеграционные тесты через port-forward

После деплоя можно запустить интеграционные тесты прямо против кластера:

```bash
bash scripts/run-integration-tests.sh
```

Скрипт автоматически настроит `kubectl port-forward` для всех зависимостей
(Redis, Postgres, Langfuse, Chroma, самого чатбота), получит секреты из k8s и
запустит `pytest` в режиме `UNION_TEST_MODE=cluster`.

Для запуска отдельного теста передайте аргументы pytest:

```bash
bash scripts/run-integration-tests.sh -k test_postgres
```

## 7. Откат / масштабирование

```bash
# Масштабирование вручную
kubectl scale deployment general-purpose-chatbot -n unionchatbot --replicas=3

# Перезапуск (rolling update)
kubectl rollout restart deployment general-purpose-chatbot -n unionchatbot

# Откат на предыдущую ревизию
kubectl rollout undo deployment general-purpose-chatbot -n unionchatbot
```

## 8. Удаление ресурсов (полный снос)

```bash
kubectl delete namespace unionchatbot
kubectl delete job create-unionchatbot-db -n sevenelement-db
```

## Важные замечания

- **Логи:** приложение продолжает писать текстовые логи внутри контейнера (`/opt/app-root`). Для долгосрочного хранения используйте `kubectl logs` или настройте сбор через Fluentd/Fluent Bit.
- **База данных:** Job `09-job-create-db.yaml` создаёт только БД `unionchatbot_db`. Таблицы для LangGraph checkpoint'ов создаются автоматически при первом запуске `AsyncPostgresSaver`.
- **Redis:** используется существующий Redis Sentinel из `sevenelement-backend`. Убедитесь, что `REDIS_PASSWORD` в `02-secret.yaml` совпадает с `redis-credentials` в `sevenelement-backend`.
