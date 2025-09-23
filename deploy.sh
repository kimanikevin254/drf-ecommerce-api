#!/bin/bash
# A script to deploy the application
# echo "Building and pushing Docker image..."
# docker build -t kimanikevin254/ecommerce-app:latest .
# docker push kimanikevin254/ecommerce-app:latest

echo "Applying Kubernetes manifests..."
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml

echo "Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/postgres

echo "Waiting for Redis to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/redis

echo "Deploying the application..."
kubectl apply -f k8s/django.yaml
kubectl apply -f k8s/celery.yaml

echo "Waiting for the application to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/django-app

echo "Deployment completed successfully."
echo "Getting service url..."
kubectl get services django-service