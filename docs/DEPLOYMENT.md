# Deployment Guide

## Prerequisites

-   Docker
-   Minikube
-   kubectl configured

## Local Kubernetes Deployment with Minikube

1. Create configmap and secret files:

    ```bash
    cp k8s/configmap.template.yaml configmap.yaml
    cp k8s/secret.template.yaml secret.yaml
    ```

    > Make sure to replace the placeholder values in the new files with your actual values. To generate base64 encode values, you can use `echo -n "<YOUR-STRING>" | base64` or `python3 encode.py "<YOUR-STRING"`.

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
