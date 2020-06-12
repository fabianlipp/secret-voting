Deploying docker containers
Run in repository root directory:
```shell script
docker build --tag vote-registration -f docker/Dockerfile.vote-registration .
docker create --name demo_vote-registration -p 127.0.0.1:8001:80 vote-registration
docker start demo_vote-registration

docker build --tag ballot-box -f docker/Dockerfile.ballot-box .
docker create --name demo_ballot-box -p 127.0.0.1:8002:80 ballot-box
docker start demo_ballot-box
```
