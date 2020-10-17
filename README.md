# Replicant

This is a collection of Dockerfiles, a couple of python script for automation along with a couple of other goodies. There are two options for use:

* Basic Usage: The basic usage to build, tag and store docker images in a docker registry. This process requires manually running the `build.py` script.
* Advanced Usage: This automates the build, tag and storage of docker images using systemd service files and Jenkins.

The instructions are written for a Linux workstation (Ubuntu is used, for this example. If you are using something else, you may have to adjust the Ansible tasks to your needs).

## Prerequisites

* `docker`
* `docker registry container`
* `python3-venv`

### Install Prereqs using Ansible

All of the prereqs can be done manually using the file `provisioning/setup.yml` as a guide. But, it is much easier to let Ansible configure everything for you.

**A note about Ansible:**

If you are unfamiliar with Ansible it is a program that is used to configure systems and applications. It is designed to be idempotent - meaning that once run it will not make changes if run again (unless the system is changed). To give an example in the Ansible file we direct Ansible to create a self-signed certificate. If the certificate does not exist it will create it, but if run again, it will recognize that the certificate is present and will not create a new one. The same idempotent properties apply to docker containers. If the container is already present, Ansible will not try to create a new one. After the first run, the only time you will see Ansible change anything is when the current instance is different than what is specified.

#### Setting up Ansible

Install Ansible:

```
sudo apt install -y ansible git
```

Install Ansible modules:

```
ansible-galaxy collection install community.crypto
ansible-galaxy collection install community.general
```

#### Running Ansible

I have chosen to clone the repository to the `/opt` directory. If you would prefer to clone it to a different location make sure to change the `clone_directory` variable in the `provisioning/vars.yml` file.

The `/opt` directory is usually owned by root. In order to clone the repository we will create a folder and then change permissions:

```
cd /opt
sudo mkdir replicant
sudo chown $USER:$USER replicant
```

Clone the repo as normal and change to the provisioning directory.

```
cd /opt
git clone https://github.com/tjcim/replicant
cd replicant/provisioning
```

Copy the `vars.yml.sample` file to `vars.yml` and modify the contents as needed.

```
cp vars.yml.sample vars.yml
```

Ansible will add an entry to the `/etc/hosts` file using the IP `127.0.0.1` and the value of `docker_registry_host` you can comment that portion out of the `setup.yml` if you have a desired host for the docker registry other than the localhost.

Run `ansible-playbook` to configure the local machine. You will be asked for the `BECOME password` - which is the password used when running `sudo`.

```
ansible-playbook -K setup.yml
```

#### After Ansible is finished

The Ansible script will add the user to the docker group. Restart the machine or run `newgrp docker` to refresh group membership.

Check that the docker registry container is running (if you get permission denied, restart the machine):
```
docker container ls
```

Check that you can list the available images (no images exist yet, so it should be empty):

```
curl https://registry.local:8443/v2/_catalog
```

## Basic Usage

Activate the virtualenv created by the Ansible script - see notes below on how to deactivate once complete

```
cd /opt/replicant
source .env/bin/activate
```

Verify that everything is working by running help:

```
./build.py --help
```

Here you will see the available options. None of the options are required, but are useful if you want to run the script without user input.

Lets run the script but add the `-i` flag so that it does not take action
```
./build.py -i
```

1. It will ask you what you want to build from the available Dockerfiles.
2. It will then reach out the github to get the latest releases from the chosen application.
3. You will enter the number that corresponds to the release you want to build (0 - will build the master branch).
4. It will show you a confirmation and ask to confirm
5. It will then show a summary of the actions it would have taken

Run the script again, this time we will build something and push it to our registry. Choose any app and a release:
```
./build.py
```

Once complete you can check that the docker image is now available by running the following (to format the json I am using `jq`):
```
curl -s https://registry.local:8443/v2/_catalog | jq
```

To see what releases are available in the registry for a specific build (example is for lighthouse):

```
curl -s https://registry.local:8443/v2/ethereum/lighthouse/tags/list
```

To deactivate the python environment when finished running the script:

```
deactivate
```

## Build Script Help

```
./build.py --help
Usage: build.py [OPTIONS]

Options:
  -a, --app-name TEXT            The name of the app you would like to build.
  -b, --build-latest             Adding this flag means I will build the most
                                 latest release. (Instead of showing you
                                 available releases and asking for a number)

  -t, --tag-latest               Adding this flag means I will tag the build
                                 as the latest.

  -n, --no-summary-confirmation  Adding this flag means I will not ask you to
                                 confirm the summary is correct

  -p, --prune                    Adding this flag means I will prune dangling
                                 images (possibly deleting more than expected)

  -d, --do-not-push              Adding this flag means that once the image is
                                 built, I will **not** push it to the registry
                                 defined in the config.py file.

  -i, --no-action                Do not build, tag, push or prune. Just show
                                 me what you would have done.

  --help                         Show this message and exit.
```

A couple of notes:

* Pruning - be careful with this as it deletes all dangling docker images.
* Build latest - This will not ask for a release number and will just build the most recent release available.

## Advanced

Documentation is coming!

### Jenkins Integration


### Systemd Service and Timer

To use the service files copy both the `replicant.service` and `replicant.timer` to `/etc/systemd/system/`. Once done you can manually trigger a check by starting the service:

```
sudo systemctl start replicant.service
```

Once you are satisfied that the service file works as expected, enable the timer file:

```
sudo systemctl enable replicant.timer
```

To check that the status of the timer:

```
sudo systemctl list-timers replicant.timer
```
