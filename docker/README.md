Deploying docker containers
Run in repository root directory:
```shell script
docker build --tag vote-registration bot -f docker/Dockerfile.vote-registration .
docker create --name demo_vote-registration -p 8001:80 vote-registration
docker start vote-registration
```
