# Deployment Guide

## Prerequisites

-   Docker
-   Minikube
-   kubectl configured

## Local Deployment with Docker Compose

1. Start all services:

    ```bash
    docker compose up -d
    ```

2. Run migrations:

    ```bash
    python3 manage.py makemigrations
    python3 manage.py migrate
    ```

3. Create super user:

    ```bash
    python3 manage.py createsuperuser
    ```

4. Run server:

    ```bash
    python3 manage.py runserver
    ```

## Local Kubernetes Deployment with Minikube

1. Create configmap and secret files:

    ```bash
    cp k8s/configmap.template.yaml configmap.yaml
    cp k8s/secret.template.yaml secret.yaml
    ```

    > Make sure to replace the placeholder values in the new files with your actual values. To generate base64 encode values, you can use `echo -n "<YOUR-STRING>" | base64`.

2. Start minikube and enable ingress addon:

    ```bash
    minikube start

    minikube addons enable ingress
    ```

3. Build app image in minikube's Docker env:

    ```bash
    eval $(minikube docker-env)
    docker build -t ecommerce-api:local .
    ```

4. Deploy:

    ```bash
    chmod +x deploy.sh
    ./deploy.sh
    ```

5. Verify deployment:

    ```bash
    kubectl get pods
    kubectl get services
    ```

6. Obtain the Django service url:

    ```bash
    minikube service django-service --url
    ```
