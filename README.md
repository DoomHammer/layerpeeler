# Layerpeeler

This is a simple console tool visualizing your Docker images.

## Running from Docker
Run the "latest" forward compatible Docker client version (works with host Docker 1.4.x up to 1.8.x)
```
$ docker run -v /var/run/docker.sock:/var/run/docker.sock -v /var/lib/docker:/var/lib/docker --rm -ti doomhammer/layerpeeler
```

If you symlinked /var/lib/docker to somewhere else make sure you tell the Docker container where it is by providing the real path or by using readlink in volume parameter.
```
$ docker run -v /var/run/docker.sock:/var/run/docker.sock -v $(readlink -f /var/lib/docker):/var/lib/docker --rm -ti doomhammer/layerpeeler
```

## Running from docker using the host docker binary
It is also possible to use the host docker binary by mounting the host docker bin directory. This way you make sure the Docker versions are the same between host and container. For example:
```
$ docker run -v $(which docker):/bin/docker -v /var/run/docker.sock:/var/run/docker.sock -v $(readlink -f /var/lib/docker):/var/lib/docker --rm -ti doomhammer/layerpeeler
```
