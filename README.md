# Replicant

[Video demo](https://youtu.be/UX5pKOA48hM)

This is a collection of Dockerfiles, a couple of python script for automation along with a couple of other goodies. There are two options for use:

* Basic Usage: The basic usage to build, tag and store docker images in a docker registry. This process requires manually running the `build.py` script.
* Advanced Usage: This automates the build, tag and storage of docker images using systemd service files and Jenkins.

The instructions are written for a Linux workstation (Ubuntu is used, for this example. If you are using something else, you may have to adjust the Ansible tasks to your needs).

## Who is this for?

This is built for someone that is familiar with docker and wants to stake Ethereum using Docker containers. The targeted user is someone who already has a way to manage their running containers and is just looking for a way to always have the latest build ready and waiting. While there is nothing complicated about what this project does, it does not dictate how you will manage running containers and leaves that up to the user.

Personally I use this project along with Ansible to manage my running containers.

## Change Log

**Oct 24th 2020**
* Changed the service file to run as a user (configured in `vars.yml`) - Issue #1
* Added curl to `Dockerfile.lighthouse` - Issue #3
* Added a pipeline script to print the app name and release at the beginning - Issue #2

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

This sets up the system for automatic building of releases anytime a new one is published. It accomplishes this by creating a Jenkins docker container in combination with a systemd timer file and systemd service file. The timer file kicks off every 15 minutes and then activates the service. The service calls the `latest_release.py` script.

### `latest_release.py`

This script checks for available docker build files and then goes to the Github repository to check for the latest release. Once it has gathered the latest releases it checks each against the images in the docker repository (set up during the basic setup). If the image is not present it triggers a Jenkins build of the image. Jenkins will build, tag, and push the release to the docker registry.

### Setup

Run ansible against the `provisioning/advanced.yml` file. This will do the following:

* Start a docker instance of Jenkins
* Copy the service files into `/etc/systemd/system/`
* Setup an SMTP relay on the localhost (to receive emails from Jenkins).

```
ansible-playbook -K /opt/replicant/provisioning/advanced.yml
```

Check that the Jenkins container is running:

```
docker container ls
```

### Configure Jenkins

Once the Jenkins container is running you can open a browser and visit [http://localhost:8080](http://localhost:8080). Here you will be asked for the Administrator password. You can find that by viewing the container logs:

```
docker logs jenkins
```

Choose to install suggested plugins and then configure your account.

** Create an API Token **

1. Click on your user name in the top right
2. Click on Configure
3. Click Add new Token button in the API Token section.
4. Give it a name and hit Generate (I suggest that you use the name replicant)
6. Set the value of `JENKINS_TOKEN_NAME` to the name you gave entered (replicant)
5. Copy the token and put it in the `config.py` as the value for `JENKINS_API_TOKEN`
7. Click Save on the Jenkins page

** Create Jenkins Job **

1. Click on Jenkins in the top left to get to the home page
2. Click on New Item
3. Give your job a name (I suggest you use the name replicant)
4. Click on Pipeline
5. Click OK
6. Give a description if you want
7. Enable the `Do not allow concurrent builds` (optional)
7. Enable the `This project is parameterized` checkbox
8. Click Add Parameter -> String. In the name field enter `REGISTRY`
8. Click Add Parameter -> String. In the name field enter `RELEASE`
8. Click Add Parameter -> String. In the name field enter `APP_NAME`
8. Click Add Parameter -> String. In the name field enter `EMAIL`
8. In the Build Triggers section check the box named `Trigger builds remotely (e.g., from scripts)`
9. Enter the name you entered when you created the API token (step 4 in previous section)
10. In the Pipeline section click the Definition drop down and select `Pipeline script from SCM`
11. Click the SCM drop down and select `Git`
12. Enter in the repository URL: `https://github.com/tjcim/replicant.git`
13. In the Branches to build -> Branch Specifier (blank for 'any') box enter `*/main`
13. Click Save at the bottom

** Add Job info to `config.py` **

1. Enter the user name used in Jenkins as the value of `JENKINS_USER`
2. Enter the Job name you entered on step 3 in the previous section as the value for `JENKINS_JOB` (suggested name of replicant)
3. Verify that all entries in the `config.py` file are filled out

### Demo Email Setup

The following setup will probably not work for you. The main reason is that your ISP is probably blocking port 25. But, I feel the demo would not be complete without showing the email notification part. So, here are the steps I took to do the email notifications in the demo video:

Start a postfix email server - I do not vouch for this image and am only using it for the demo
```
docker container run --rm --name postfix -e "ALLOWED_SENDER_DOMAINS=jenkins.blah nowhere" -p 1587:587 boky/postfix
```

Create a docker network:
```
docker network create blah
```

Connect both containers to the network
```
docker network connect blah jenkins
docker network connect blah postfix
```

** Configure Jenkins **

1. From the Jenkins homepage click `Manage Jenkins`
2. Click `Configure System`
3. In the `Jenkins Location` section enter in the System Admin e-mail address: `no-reply@jenkins.blah`
4. Scroll down to the `E-mail Notification` and set the SMTP server to `postfix`
5. Set the Default user e-mail suffix to `@jenkins.blah`
6. Click on Advanced
7. Set the SMTP Port to 587
8. Set the Reply-To Address to `no-reply@jenkins.blah`
9. Test the config by sending an email
10. If it all works click Save

### Test the Service

Ansible has copied the service file to `/etc/sytemd/system/replicant.servic`. To verify that everything is working run:
```
sudo systemctl start replicant.service
```

Use the following to check the output form the script:
```
sudo systemctl status replicant.service
```

Check Jenkins to confim the builds have been kicked off. Wait for them to complete to ensure they are building successfully.

Once you are satisfied that the service file works as expected, enable the timer file:

```
sudo systemctl enable replicant.timer
```

To check that the status of the timer:

```
sudo systemctl list-timers replicant.timer
```
