#!/bin/bash

# Variables
RESOURCE_GROUP="cqq_lem_resource_group"
LOCATION="eastus"
WEB_APP_NAME="cqc-lem"
REDIS_NAME="cqc-lem-redis"
MYSQL_NAME="cqc-lem-mysql"
ACI_NAME="cqc-lem-aci"
APP_INSIGHTS_NAME="cqc-lem-insights"
CONTAINER_REGISTRY="cqc-lem-container-registry"
PROMETHEUS_NAME="cqc s-lem-prometheus"
LOGIC_APP_NAME="cqc-lem-logic-app"
SELENIUM_HUB_NAME="cqc-lem-selenium-hub"
SELENIUM_NODE_NAME="cqc-lem-selenium-node"
LINKEDIN_PREVIEW_NAME="cqc-lem-linkedin-preview"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Azure App Service for web_app
az appservice plan create --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP --sku B1 --is-linux
az webapp create --resource-group $RESOURCE_GROUP --plan $WEB_APP_NAME --name $WEB_APP_NAME --deployment-container-image-name $DOCKER_IMAGE_NAME:latest

# Create Azure Cache for Redis
az redis create --name $REDIS_NAME --resource-group $RESOURCE_GROUP --location $LOCATION --sku Basic --vm-size c0

# Create Azure Database for MySQL
az mysql server create --resource-group $RESOURCE_GROUP --name $MYSQL_NAME --location $LOCATION --admin-user $MYSQL_USER --admin-password $MYSQL_PASSWORD --sku-name GP_Gen5_2
az mysql server firewall-rule create --resource-group $RESOURCE_GROUP --server $MYSQL_NAME --name AllowMyIP --start-ip-address 0.0.0.0 --end-ip-address 255.255.255.255

# Create Azure Container Instances for celery_worker
az container create --resource-group $RESOURCE_GROUP --name $ACI_NAME --image $DOCKER_IMAGE_NAME --cpu 2 --memory 4 --environment-variables MYSQL_HOST=$MYSQL_HOST MYSQL_USER=$MYSQL_USER MYSQL_PASSWORD=$MYSQL_PASSWORD

# Create Azure Container Instances for selenium_hub
az container create --resource-group $RESOURCE_GROUP --name $ACI_NAME --image $DOCKER_IMAGE_NAME --cpu 2 --memory 4 --environment-variables MYSQL_HOST=$MYSQL_HOST MYSQL_USER=$MYSQL_USER MYSQL_PASSWORD=$MYSQL_PASSWORD

# Create Azure Container Instances for selenium_node
az container create --resource-group $RESOURCE_GROUP --name $ACI_NAME --image $DOCKER_IMAGE_NAME --cpu 2 --memory 4 --environment-variables MYSQL_HOST=$MYSQL_HOST MYSQL_USER=$MYSQL_USER MYSQL_PASSWORD=$MYSQL_PASSWORD



# Create Azure Application Insights
az monitor app-insights component create --app $APP_INSIGHTS_NAME --location $LOCATION --resource-group $RESOURCE_GROUP

# Create Azure Logic App for celery_beat
az logic workflow create --resource-group $RESOURCE_GROUP --name $LOGIC_APP_NAME --definition @logicapp.json

# Create Azure Monitor for prometheus
az monitor metrics alert create --name $PROMETHEUS_NAME --resource-group $RESOURCE_GROUP --scopes /subscriptions/{subscription-id}/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$WEB_APP_NAME --condition "avg Percentage CPU > 80" --description "Alert when CPU usage is over 80%"

# Create Azure App Service for linkedin-preview
az webapp create --resource-group $RESOURCE_GROUP --plan $WEB_APP_NAME --name $LINKEDIN_PREVIEW_NAME --deployment-container-image-name $DOCKER_IMAGE_NAME:linkedinpreview

echo "Azure services created successfully."