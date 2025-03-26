import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';
import Image from '@theme/IdealImage';

# Docker, Deployment

You can find the Dockerfile to build llm proxy [here](https://github.com/BerriAI/llm/blob/main/Dockerfile)

## Quick Start

To start using Llm, run the following commands in a shell:

```bash
# Get the code
git clone https://github.com/BerriAI/llm

# Go to folder
cd llm

# Add the master key - you can change this after setup
echo 'LLM_MASTER_KEY="sk-1234"' > .env

# Add the llm salt key - you cannot change this after adding a model
# It is used to encrypt / decrypt your LLM API Key credentials
# We recommned - https://1password.com/password-generator/ 
# password generator to get a random hash for llm salt key
echo 'LLM_SALT_KEY="sk-1234"' >> .env

source .env

# Start
docker-compose up
```


### Docker Run 

#### Step 1. CREATE config.yaml 

Example `llm_config.yaml` 

```yaml
model_list:
  - model_name: azure-gpt-3.5
    llm_params:
      model: azure/<your-azure-model-deployment>
      api_base: os.environ/AZURE_API_BASE # runs os.getenv("AZURE_API_BASE")
      api_key: os.environ/AZURE_API_KEY # runs os.getenv("AZURE_API_KEY")
      api_version: "2023-07-01-preview"
```



#### Step 2. RUN Docker Image

```shell
docker run \
    -v $(pwd)/llm_config.yaml:/app/config.yaml \
    -e AZURE_API_KEY=d6*********** \
    -e AZURE_API_BASE=https://openai-***********/ \
    -p 4000:4000 \
    ghcr.io/berriai/llm:main-latest \
    --config /app/config.yaml --detailed_debug
```

Get Latest Image 👉 [here](https://github.com/berriai/llm/pkgs/container/llm)

#### Step 3. TEST Request

  Pass `model=azure-gpt-3.5` this was set on step 1

  ```shell
  curl --location 'http://0.0.0.0:4000/chat/completions' \
      --header 'Content-Type: application/json' \
      --data '{
      "model": "azure-gpt-3.5",
      "messages": [
          {
          "role": "user",
          "content": "what llm are you"
          }
      ]
  }'
  ```

### Docker Run - CLI Args

See all supported CLI args [here](https://docs.llm.ai/docs/proxy/cli): 

Here's how you can run the docker image and pass your config to `llm`
```shell
docker run ghcr.io/berriai/llm:main-latest --config your_config.yaml
```

Here's how you can run the docker image and start llm on port 8002 with `num_workers=8`
```shell
docker run ghcr.io/berriai/llm:main-latest --port 8002 --num_workers 8
```


### Use llm as a base image

```shell
# Use the provided base image
FROM ghcr.io/berriai/llm:main-latest

# Set the working directory to /app
WORKDIR /app

# Copy the configuration file into the container at /app
COPY config.yaml .

# Make sure your docker/entrypoint.sh is executable
RUN chmod +x ./docker/entrypoint.sh

# Expose the necessary port
EXPOSE 4000/tcp

# Override the CMD instruction with your desired command and arguments
# WARNING: FOR PROD DO NOT USE `--detailed_debug` it slows down response times, instead use the following CMD
# CMD ["--port", "4000", "--config", "config.yaml"]

CMD ["--port", "4000", "--config", "config.yaml", "--detailed_debug"]
```

### Build from llm `pip` package

Follow these instructons to build a docker container from the llm pip package. If your company has a strict requirement around security / building images you can follow these steps.

Dockerfile 

```shell
FROM cgr.dev/chainguard/python:latest-dev

USER root
WORKDIR /app

ENV HOME=/home/llm
ENV PATH="${HOME}/venv/bin:$PATH"

# Install runtime dependencies
RUN apk update && \
    apk add --no-cache gcc python3-dev openssl openssl-dev

RUN python -m venv ${HOME}/venv
RUN ${HOME}/venv/bin/pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN --mount=type=cache,target=${HOME}/.cache/pip \
    ${HOME}/venv/bin/pip install -r requirements.txt

EXPOSE 4000/tcp

ENTRYPOINT ["llm"]
CMD ["--port", "4000"]
```


Example `requirements.txt`

```shell
llm[proxy]==1.57.3 # Specify the llm version you want to use
prometheus_client
langfuse
prisma
```

Build the docker image

```shell
docker build \
  -f Dockerfile.build_from_pip \
  -t llm-proxy-with-pip-5 .
```

Run the docker image

```shell
docker run \
    -v $(pwd)/llm_config.yaml:/app/config.yaml \
    -e OPENAI_API_KEY="sk-1222" \
    -e DATABASE_URL="postgresql://xxxxxxxxx \
    -p 4000:4000 \
    llm-proxy-with-pip-5 \
    --config /app/config.yaml --detailed_debug
```

### Terraform

s/o [Nicholas Cecere](https://www.linkedin.com/in/nicholas-cecere-24243549/) for his LLM User Management Terraform

👉 [Go here for Terraform](https://github.com/ncecere/terraform-llm-user-mgmt)

### Kubernetes

Deploying a config file based llm instance just requires a simple deployment that loads
the config.yaml file via a config map. Also it would be a good practice to use the env var
declaration for api keys, and attach the env vars with the api key values as an opaque secret.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: llm-config-file
data:
  config.yaml: |
      model_list: 
        - model_name: gpt-3.5-turbo
          llm_params:
            model: azure/gpt-turbo-small-ca
            api_base: https://my-endpoint-canada-berri992.openai.azure.com/
            api_key: os.environ/CA_AZURE_OPENAI_API_KEY
---
apiVersion: v1
kind: Secret
type: Opaque
metadata:
  name: llm-secrets
data:
  CA_AZURE_OPENAI_API_KEY: bWVvd19pbV9hX2NhdA== # your api key in base64
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-deployment
  labels:
    app: llm
spec:
  selector:
    matchLabels:
      app: llm
  template:
    metadata:
      labels:
        app: llm
    spec:
      containers:
      - name: llm
        image: ghcr.io/berriai/llm:main-latest # it is recommended to fix a version generally
        ports:
        - containerPort: 4000
        volumeMounts:
        - name: config-volume
          mountPath: /app/proxy_server_config.yaml
          subPath: config.yaml
        envFrom:
        - secretRef:
            name: llm-secrets
      volumes:
        - name: config-volume
          configMap:
            name: llm-config-file
```

:::info
To avoid issues with predictability, difficulties in rollback, and inconsistent environments, use versioning or SHA digests (for example, `llm:main-v1.30.3` or `llm@sha256:12345abcdef...`) instead of `llm:main-latest`.
:::


### Helm Chart

:::info

[BETA] Helm Chart is BETA. If you run into an issues/have feedback please let us know [https://github.com/BerriAI/llm/issues](https://github.com/BerriAI/llm/issues)

:::

Use this when you want to use llm helm chart as a dependency for other charts. The `llm-helm` OCI is hosted here [https://github.com/BerriAI/llm/pkgs/container/llm-helm](https://github.com/BerriAI/llm/pkgs/container/llm-helm)

#### Step 1. Pull the llm helm chart

```bash
helm pull oci://ghcr.io/berriai/llm-helm

# Pulled: ghcr.io/berriai/llm-helm:0.1.2
# Digest: sha256:7d3ded1c99c1597f9ad4dc49d84327cf1db6e0faa0eeea0c614be5526ae94e2a
```

#### Step 2. Unzip llm helm
Unzip the specific version that was pulled in Step 1

```bash
tar -zxvf llm-helm-0.1.2.tgz
```

#### Step 3. Install llm helm

```bash
helm install lite-helm ./llm-helm
```

#### Step 4. Expose the service to localhost

```bash
kubectl --namespace default port-forward $POD_NAME 8080:$CONTAINER_PORT
```

Your LLM Proxy Server is now running on `http://127.0.0.1:4000`.

**That's it ! That's the quick start to deploy llm**

#### Make LLM API Requests

:::info
💡 Go here 👉 [to make your first LLM API Request](user_keys)

LLM is compatible with several SDKs - including OpenAI SDK, Anthropic SDK, Mistral SDK, LLamaIndex, Langchain (Js, Python)

:::

## Deployment Options

| Docs                                                                                              | When to Use                                                                                                                                           |
| ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Quick Start](#quick-start)                                                                       | call 100+ LLMs + Load Balancing                                                                                                                       |
| [Deploy with Database](#deploy-with-database)                                                     | + use Virtual Keys + Track Spend (Note: When deploying with a database providing a `DATABASE_URL` and `LLM_MASTER_KEY` are required in your env ) |
| [LLM container + Redis](#llm-container--redis)                                            | + load balance across multiple llm containers                                                                                                     |
| [LLM Database container + PostgresDB + Redis](#llm-database-container--postgresdb--redis) | + use Virtual Keys + Track Spend + load balance across multiple llm containers                                                                    |

### Deploy with Database
##### Docker, Kubernetes, Helm Chart

Requirements:
- Need a postgres database (e.g. [Supabase](https://supabase.com/), [Neon](https://neon.tech/), etc) Set `DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<dbname>` in your env 
- Set a `LLM_MASTER_KEY`, this is your Proxy Admin key - you can use this to create other keys (🚨 must start with `sk-`)

<Tabs>

<TabItem value="docker-deploy" label="Dockerfile">

We maintain a [separate Dockerfile](https://github.com/BerriAI/llm/pkgs/container/llm-database) for reducing build time when running LLM proxy with a connected Postgres Database 

```shell
docker pull ghcr.io/berriai/llm-database:main-latest
```

```shell
docker run \
    -v $(pwd)/llm_config.yaml:/app/config.yaml \
    -e LLM_MASTER_KEY=sk-1234 \
    -e DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<dbname> \
    -e AZURE_API_KEY=d6*********** \
    -e AZURE_API_BASE=https://openai-***********/ \
    -p 4000:4000 \
    ghcr.io/berriai/llm-database:main-latest \
    --config /app/config.yaml --detailed_debug
```

Your LLM Proxy Server is now running on `http://0.0.0.0:4000`.

</TabItem>
<TabItem value="kubernetes-deploy" label="Kubernetes">

#### Step 1. Create deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: llm
  template:
    metadata:
      labels:
        app: llm
    spec:
      containers:
        - name: llm-container
          image: ghcr.io/berriai/llm:main-latest
          imagePullPolicy: Always
          env:
            - name: AZURE_API_KEY
              value: "d6******"
            - name: AZURE_API_BASE
              value: "https://ope******"
            - name: LLM_MASTER_KEY
              value: "sk-1234"
            - name: DATABASE_URL
              value: "po**********"
          args:
            - "--config"
            - "/app/proxy_config.yaml"  # Update the path to mount the config file
          volumeMounts:                 # Define volume mount for proxy_config.yaml
            - name: config-volume
              mountPath: /app
              readOnly: true
          livenessProbe:
            httpGet:
              path: /health/liveliness
              port: 4000
            initialDelaySeconds: 120
            periodSeconds: 15
            successThreshold: 1
            failureThreshold: 3
            timeoutSeconds: 10
          readinessProbe:
            httpGet:
              path: /health/readiness
              port: 4000
            initialDelaySeconds: 120
            periodSeconds: 15
            successThreshold: 1
            failureThreshold: 3
            timeoutSeconds: 10
      volumes:  # Define volume to mount proxy_config.yaml
        - name: config-volume
          configMap:
            name: llm-config  

```

```bash
kubectl apply -f /path/to/deployment.yaml
```

#### Step 2. Create service.yaml 

```yaml
apiVersion: v1
kind: Service
metadata:
  name: llm-service
spec:
  selector:
    app: llm
  ports:
    - protocol: TCP
      port: 4000
      targetPort: 4000
  type: NodePort
```

```bash
kubectl apply -f /path/to/service.yaml
```

#### Step 3. Start server

```
kubectl port-forward service/llm-service 4000:4000
```

Your LLM Proxy Server is now running on `http://0.0.0.0:4000`.

</TabItem>

<TabItem value="helm-deploy" label="Helm">



:::info

[BETA] Helm Chart is BETA. If you run into an issues/have feedback please let us know [https://github.com/BerriAI/llm/issues](https://github.com/BerriAI/llm/issues)

:::

Use this to deploy llm using a helm chart. Link to [the LLM Helm Chart](https://github.com/BerriAI/llm/tree/main/deploy/charts/llm-helm)

#### Step 1. Clone the repository

```bash
git clone https://github.com/BerriAI/llm.git
```

#### Step 2. Deploy with Helm

Run the following command in the root of your `llm` repo. This will set the llm proxy master key as `sk-1234`

```bash
helm install \
  --set masterkey=sk-1234 \
  mydeploy \
  deploy/charts/llm-helm
```

#### Step 3. Expose the service to localhost

```bash
kubectl \
  port-forward \
  service/mydeploy-llm-helm \
  4000:4000
```

Your LLM Proxy Server is now running on `http://127.0.0.1:4000`.


If you need to set your llm proxy config.yaml, you can find this in [values.yaml](https://github.com/BerriAI/llm/blob/main/deploy/charts/llm-helm/values.yaml)

</TabItem>

<TabItem value="helm-oci" label="Helm OCI Registry (GHCR)">

:::info

[BETA] Helm Chart is BETA. If you run into an issues/have feedback please let us know [https://github.com/BerriAI/llm/issues](https://github.com/BerriAI/llm/issues)

:::

Use this when you want to use llm helm chart as a dependency for other charts. The `llm-helm` OCI is hosted here [https://github.com/BerriAI/llm/pkgs/container/llm-helm](https://github.com/BerriAI/llm/pkgs/container/llm-helm)

#### Step 1. Pull the llm helm chart

```bash
helm pull oci://ghcr.io/berriai/llm-helm

# Pulled: ghcr.io/berriai/llm-helm:0.1.2
# Digest: sha256:7d3ded1c99c1597f9ad4dc49d84327cf1db6e0faa0eeea0c614be5526ae94e2a
```

#### Step 2. Unzip llm helm
Unzip the specific version that was pulled in Step 1

```bash
tar -zxvf llm-helm-0.1.2.tgz
```

#### Step 3. Install llm helm

```bash
helm install lite-helm ./llm-helm
```

#### Step 4. Expose the service to localhost

```bash
kubectl --namespace default port-forward $POD_NAME 8080:$CONTAINER_PORT
```

Your LLM Proxy Server is now running on `http://127.0.0.1:4000`.

</TabItem>
</Tabs>

### Deploy with Redis
Use Redis when you need llm to load balance across multiple llm containers

The only change required is setting Redis on your `config.yaml`
LLM Proxy supports sharing rpm/tpm shared across multiple llm instances, pass `redis_host`, `redis_password` and `redis_port` to enable this. (LLM will use Redis to track rpm/tpm usage )

```yaml
model_list:
  - model_name: gpt-3.5-turbo
    llm_params:
      model: azure/<your-deployment-name>
      api_base: <your-azure-endpoint>
      api_key: <your-azure-api-key>
      rpm: 6      # Rate limit for this deployment: in requests per minute (rpm)
  - model_name: gpt-3.5-turbo
    llm_params:
      model: azure/gpt-turbo-small-ca
      api_base: https://my-endpoint-canada-berri992.openai.azure.com/
      api_key: <your-azure-api-key>
      rpm: 6
router_settings:
  redis_host: <your redis host>
  redis_password: <your redis password>
  redis_port: 1992
```

Start docker container with config

```shell
docker run ghcr.io/berriai/llm:main-latest --config your_config.yaml
```

### Deploy with Database + Redis

The only change required is setting Redis on your `config.yaml`
LLM Proxy supports sharing rpm/tpm shared across multiple llm instances, pass `redis_host`, `redis_password` and `redis_port` to enable this. (LLM will use Redis to track rpm/tpm usage )


```yaml
model_list:
  - model_name: gpt-3.5-turbo
    llm_params:
      model: azure/<your-deployment-name>
      api_base: <your-azure-endpoint>
      api_key: <your-azure-api-key>
      rpm: 6      # Rate limit for this deployment: in requests per minute (rpm)
  - model_name: gpt-3.5-turbo
    llm_params:
      model: azure/gpt-turbo-small-ca
      api_base: https://my-endpoint-canada-berri992.openai.azure.com/
      api_key: <your-azure-api-key>
      rpm: 6
router_settings:
  redis_host: <your redis host>
  redis_password: <your redis password>
  redis_port: 1992
```

Start `llm-database`docker container with config

```shell
docker run --name llm-proxy \
-e DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<dbname> \
-p 4000:4000 \
ghcr.io/berriai/llm-database:main-latest --config your_config.yaml
```

###  (Non Root) - without Internet Connection

By default `prisma generate` downloads [prisma's engine binaries](https://www.prisma.io/docs/orm/reference/environment-variables-reference#custom-engine-file-locations). This might cause errors when running without internet connection. 

Use this docker image to deploy llm with pre-generated prisma binaries.

```bash
docker pull ghcr.io/berriai/llm-non_root:main-stable
```

[Published Docker Image link](https://github.com/BerriAI/llm/pkgs/container/llm-non_root)

## Advanced Deployment Settings

### 1. Custom server root path (Proxy base url)

💥 Use this when you want to serve LLM on a custom base url path like `https://localhost:4000/api/v1` 

:::info

In a Kubernetes deployment, it's possible to utilize a shared DNS to host multiple applications by modifying the virtual service

:::

Customize the root path to eliminate the need for employing multiple DNS configurations during deployment.

Step 1.
👉 Set `SERVER_ROOT_PATH` in your .env and this will be set as your server root path
```
export SERVER_ROOT_PATH="/api/v1"
```

**Step 2** (If you want the Proxy Admin UI to work with your root path you need to use this dockerfile)
- Use the dockerfile below (it uses llm as a base image)
- 👉 Set `UI_BASE_PATH=$SERVER_ROOT_PATH/ui` in the Dockerfile, example `UI_BASE_PATH=/api/v1/ui`

Dockerfile

```shell
# Use the provided base image
FROM ghcr.io/berriai/llm:main-latest

# Set the working directory to /app
WORKDIR /app

# Install Node.js and npm (adjust version as needed)
RUN apt-get update && apt-get install -y nodejs npm

# Copy the UI source into the container
COPY ./ui/llm-dashboard /app/ui/llm-dashboard

# Set an environment variable for UI_BASE_PATH
# This can be overridden at build time
# set UI_BASE_PATH to "<your server root path>/ui"
# 👇👇 Enter your UI_BASE_PATH here
ENV UI_BASE_PATH="/api/v1/ui" 

# Build the UI with the specified UI_BASE_PATH
WORKDIR /app/ui/llm-dashboard
RUN npm install
RUN UI_BASE_PATH=$UI_BASE_PATH npm run build

# Create the destination directory
RUN mkdir -p /app/llm/proxy/_experimental/out

# Move the built files to the appropriate location
# Assuming the build output is in ./out directory
RUN rm -rf /app/llm/proxy/_experimental/out/* && \
    mv ./out/* /app/llm/proxy/_experimental/out/

# Switch back to the main app directory
WORKDIR /app

# Make sure your entrypoint.sh is executable
RUN chmod +x ./docker/entrypoint.sh

# Expose the necessary port
EXPOSE 4000/tcp

# Override the CMD instruction with your desired command and arguments
# only use --detailed_debug for debugging
CMD ["--port", "4000", "--config", "config.yaml"]
```

**Step 3** build this Dockerfile

```shell
docker build -f Dockerfile -t llm-prod-build . --progress=plain
```

**Step 4. Run Proxy with `SERVER_ROOT_PATH` set in your env **

```shell
docker run \
    -v $(pwd)/proxy_config.yaml:/app/config.yaml \
    -p 4000:4000 \
    -e LLM_LOG="DEBUG"\
    -e SERVER_ROOT_PATH="/api/v1"\
    -e DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<dbname> \
    -e LLM_MASTER_KEY="sk-1234"\
    llm-prod-build \
    --config /app/config.yaml
```

After running the proxy you can access it on `http://0.0.0.0:4000/api/v1/` (since we set `SERVER_ROOT_PATH="/api/v1"`)

**Step 5. Verify Running on correct path**

<Image img={require('../../img/custom_root_path.png')} />

**That's it**, that's all you need to run the proxy on a custom root path

### 2. SSL Certification 

Use this, If you need to set ssl certificates for your on prem llm proxy

Pass `ssl_keyfile_path` (Path to the SSL keyfile) and `ssl_certfile_path` (Path to the SSL certfile) when starting llm proxy 

```shell
docker run ghcr.io/berriai/llm:main-latest \
    --ssl_keyfile_path ssl_test/keyfile.key \
    --ssl_certfile_path ssl_test/certfile.crt
```

Provide an ssl certificate when starting llm proxy server 

### 3. Http/2 with Hypercorn

Use this if you want to run the proxy with hypercorn to support http/2

Step 1. Build your custom docker image with hypercorn

```shell
# Use the provided base image
FROM ghcr.io/berriai/llm:main-latest

# Set the working directory to /app
WORKDIR /app

# Copy the configuration file into the container at /app
COPY config.yaml .

# Make sure your docker/entrypoint.sh is executable
RUN chmod +x ./docker/entrypoint.sh

# Expose the necessary port
EXPOSE 4000/tcp

# 👉 Key Change: Install hypercorn
RUN pip install hypercorn

# Override the CMD instruction with your desired command and arguments
# WARNING: FOR PROD DO NOT USE `--detailed_debug` it slows down response times, instead use the following CMD
# CMD ["--port", "4000", "--config", "config.yaml"]

CMD ["--port", "4000", "--config", "config.yaml", "--detailed_debug"]
```

Step 2. Pass the `--run_hypercorn` flag when starting the proxy

```shell
docker run \
    -v $(pwd)/proxy_config.yaml:/app/config.yaml \
    -p 4000:4000 \
    -e LLM_LOG="DEBUG"\
    -e SERVER_ROOT_PATH="/api/v1"\
    -e DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<dbname> \
    -e LLM_MASTER_KEY="sk-1234"\
    your_custom_docker_image \
    --config /app/config.yaml
    --run_hypercorn
```

### 4. config.yaml file on s3, GCS Bucket Object/url

Use this if you cannot mount a config file on your deployment service (example - AWS Fargate, Railway etc)

LLM Proxy will read your config.yaml from an s3 Bucket or GCS Bucket 

<Tabs>
<TabItem value="gcs" label="GCS Bucket">

Set the following .env vars 
```shell
LLM_CONFIG_BUCKET_TYPE = "gcs"                              # set this to "gcs"         
LLM_CONFIG_BUCKET_NAME = "llm-proxy"                    # your bucket name on GCS
LLM_CONFIG_BUCKET_OBJECT_KEY = "proxy_config.yaml"         # object key on GCS
```

Start llm proxy with these env vars - llm will read your config from GCS 

```shell
docker run --name llm-proxy \
   -e DATABASE_URL=<database_url> \
   -e LLM_CONFIG_BUCKET_NAME=<bucket_name> \
   -e LLM_CONFIG_BUCKET_OBJECT_KEY="<object_key>> \
   -e LLM_CONFIG_BUCKET_TYPE="gcs" \
   -p 4000:4000 \
   ghcr.io/berriai/llm-database:main-latest --detailed_debug
```

</TabItem>

<TabItem value="s3" label="s3">

Set the following .env vars 
```shell
LLM_CONFIG_BUCKET_NAME = "llm-proxy"                    # your bucket name on s3 
LLM_CONFIG_BUCKET_OBJECT_KEY = "llm_proxy_config.yaml"  # object key on s3
```

Start llm proxy with these env vars - llm will read your config from s3 

```shell
docker run --name llm-proxy \
   -e DATABASE_URL=<database_url> \
   -e LLM_CONFIG_BUCKET_NAME=<bucket_name> \
   -e LLM_CONFIG_BUCKET_OBJECT_KEY="<object_key>> \
   -p 4000:4000 \
   ghcr.io/berriai/llm-database:main-latest
```
</TabItem>
</Tabs>

## Platform-specific Guide

<Tabs>
<TabItem value="AWS EKS" label="AWS EKS - Kubernetes">

### Kubernetes (AWS EKS)

Step1. Create an EKS Cluster with the following spec

```shell
eksctl create cluster --name=llm-cluster --region=us-west-2 --node-type=t2.small
```

Step 2. Mount llm proxy config on kub cluster 

This will mount your local file called `proxy_config.yaml` on kubernetes cluster

```shell
kubectl create configmap llm-config --from-file=proxy_config.yaml
```

Step 3. Apply `kub.yaml` and `service.yaml`
Clone the following `kub.yaml` and `service.yaml` files and apply locally

- Use this `kub.yaml` file - [llm kub.yaml](https://github.com/BerriAI/llm/blob/main/deploy/kubernetes/kub.yaml)

- Use this `service.yaml` file - [llm service.yaml](https://github.com/BerriAI/llm/blob/main/deploy/kubernetes/service.yaml)

Apply `kub.yaml`
```
kubectl apply -f kub.yaml
```

Apply `service.yaml` - creates an AWS load balancer to expose the proxy
```
kubectl apply -f service.yaml

# service/llm-service created
```

Step 4. Get Proxy Base URL

```shell
kubectl get services

# llm-service   LoadBalancer   10.100.6.31   a472dc7c273fd47fd******.us-west-2.elb.amazonaws.com   4000:30374/TCP   63m
```

Proxy Base URL =  `a472dc7c273fd47fd******.us-west-2.elb.amazonaws.com:4000`

That's it, now you can start using LLM Proxy

</TabItem>


<TabItem value="aws-stack" label="AWS Cloud Formation Stack">

### AWS Cloud Formation Stack
LLM AWS Cloudformation Stack - **Get the best LLM AutoScaling Policy and Provision the DB for LLM Proxy**

This will provision:
- LLMServer - EC2 Instance
- LLMServerAutoScalingGroup
- LLMServerScalingPolicy (autoscaling policy)
- LLMDB - RDS::DBInstance

#### Using AWS Cloud Formation Stack
**LLM Cloudformation stack is located [here - llm.yaml](https://github.com/BerriAI/llm/blob/main/enterprise/cloudformation_stack/llm.yaml)**

#### 1. Create the CloudFormation Stack:
In the AWS Management Console, navigate to the CloudFormation service, and click on "Create Stack."

On the "Create Stack" page, select "Upload a template file" and choose the llm.yaml file 

Now monitor the stack was created successfully. 

#### 2. Get the Database URL:
Once the stack is created, get the DatabaseURL of the Database resource, copy this value 

#### 3. Connect to the EC2 Instance and deploy llm on the EC2 container
From the EC2 console, connect to the instance created by the stack (e.g., using SSH).

Run the following command, replacing `<database_url>` with the value you copied in step 2

```shell
docker run --name llm-proxy \
   -e DATABASE_URL=<database_url> \
   -p 4000:4000 \
   ghcr.io/berriai/llm-database:main-latest
```

#### 4. Access the Application:

Once the container is running, you can access the application by going to `http://<ec2-public-ip>:4000` in your browser.

</TabItem>
<TabItem value="google-cloud-run" label="Google Cloud Run">

### Google Cloud Run

1. Fork this repo - [github.com/BerriAI/example_llm_gcp_cloud_run](https://github.com/BerriAI/example_llm_gcp_cloud_run)

2. Edit the `llm_config.yaml` file in the repo to include your model settings 

3. Deploy your forked github repo on Google Cloud Run

#### Testing your deployed proxy
**Assuming the required keys are set as Environment Variables**

https://llm-7yjrj3ha2q-uc.a.run.app is our example proxy, substitute it with your deployed cloud run app

```shell
curl https://llm-7yjrj3ha2q-uc.a.run.app/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
     "model": "gpt-3.5-turbo",
     "messages": [{"role": "user", "content": "Say this is a test!"}],
     "temperature": 0.7
   }'
```


</TabItem>
<TabItem value="render" label="Render deploy">

### Render 

https://render.com/

<iframe width="840" height="500" src="https://www.loom.com/embed/805964b3c8384b41be180a61442389a3" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>



</TabItem>
<TabItem value="railway" label="Railway">

### Railway 

https://railway.app

**Step 1: Click the button** to deploy to Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/S7P9sn?referralCode=t3ukrU)

**Step 2:** Set `PORT` = 4000 on Railway Environment Variables

</TabItem>
</Tabs>


## Extras 

### Docker compose

**Step 1**

- (Recommended) Use the example file `docker-compose.yml` given in the project root. e.g. https://github.com/BerriAI/llm/blob/main/docker-compose.yml

Here's an example `docker-compose.yml` file
```yaml
version: "3.9"
services:
  llm:
    build:
      context: .
      args:
        target: runtime
    image: ghcr.io/berriai/llm:main-latest
    ports:
      - "4000:4000" # Map the container port to the host, change the host port if necessary
    volumes:
      - ./llm-config.yaml:/app/config.yaml # Mount the local configuration file
    # You can change the port or number of workers as per your requirements or pass any new supported CLI augument. Make sure the port passed here matches with the container port defined above in `ports` value
    command: [ "--config", "/app/config.yaml", "--port", "4000", "--num_workers", "8" ]

# ...rest of your docker-compose config if any
```

**Step 2**

Create a `llm-config.yaml` file with your LLM config relative to your `docker-compose.yml` file.

Check the config doc [here](https://docs.llm.ai/docs/proxy/configs)

**Step 3**

Run the command `docker-compose up` or `docker compose up` as per your docker installation.

> Use `-d` flag to run the container in detached mode (background) e.g. `docker compose up -d`


Your LLM container should be running now on the defined port e.g. `4000`.

### IAM-based Auth for RDS DB 

1. Set AWS env var 

```bash
export AWS_WEB_IDENTITY_TOKEN='/path/to/token'
export AWS_ROLE_NAME='arn:aws:iam::123456789012:role/MyRole'
export AWS_SESSION_NAME='MySession'
```

[**See all Auth options**](https://github.com/BerriAI/llm/blob/089a4f279ad61b7b3e213d8039fb9b75204a7abc/llm/proxy/auth/rds_iam_token.py#L165)

2. Add RDS credentials to env

```bash
export DATABASE_USER="db-user"
export DATABASE_PORT="5432"
export DATABASE_HOST="database-1-instance-1.cs1ksmwz2xt3.us-west-2.rds.amazonaws.com"
export DATABASE_NAME="database-1-instance-1"
export DATABASE_SCHEMA="schema-name" # skip to use the default "public" schema
```

3. Run proxy with iam+rds


```bash
llm --config /path/to/config.yaml --iam_token_db_auth
```

