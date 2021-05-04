#!/usr/bin/env python

import os
import sys
import logging
import urllib.parse
from urllib3.exceptions import InsecureRequestWarning

import click
import requests
from requests.auth import HTTPBasicAuth

import build
import config


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="{asctime} [{threadName}][{levelname}][{name}] {message}",
    style="{", datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


def trigger_build(build_dict):
    auth = HTTPBasicAuth(config.JENKINS_USER, config.JENKINS_API_TOKEN)
    url = (
        f"{config.JENKINS_URL}/job/{config.JENKINS_JOB}"
        f"/buildWithParameters?token={config.JENKINS_TOKEN_NAME}"
        f"&REGISTRY={config.DOCKER_REGISTRY}"
        f"&RELEASE={build_dict['release_id'].replace('+', '_')}"
        f"&APP_NAME={build_dict['app_name']}"
        f"&EMAIL={config.JENKINS_EMAIL}"
    )
    resp = requests.get(url, auth=auth, verify=False)
    if resp.status_code == 201:
        return True
    log.error(f"Received {resp.status_code} while trying to submit build")
    return False


def registry_image_exists(app_name, release):
    url = f"https://{config.DOCKER_REGISTRY}/v2/_catalog"
    resp = requests.get(url, verify=False)
    repositories = resp.json()['repositories']
    registry_app_name = f"ethereum/{app_name}"
    if registry_app_name in repositories:
        url = f"https://{config.DOCKER_REGISTRY}/v2/ethereum/{app_name}/tags/list"
        resp = requests.get(url, verify=False)
        if release['id'].replace("+", "_") in resp.json()['tags']:
            return True
    return False


def create_build_list(available_apps):
    build_list = []
    for app_name in available_apps:
        log.info(f"Checking latest release for {app_name}")
        release = build.get_latest_releases(app_name)[0]
        log.info(f"Checking docker registry for {app_name} and release {release['id']}")
        if not registry_image_exists(app_name, release):
            log.info(f"Need to build {app_name}:{release['id']}")
            build_list.append({'app_name': app_name, 'release_id': release['id']})
    return build_list


@click.command()
def main():
    available_apps = build.get_available_apps()
    build_list = create_build_list(available_apps)
    if len(build_list) == 0:
        log.info("No need to build any apps. We are all up to date.")
    for build_dict in build_list:
        log.info(f"Triggering a build of {build_dict['app_name']}:{build_dict['release_id']}")
        trigger_build(build_dict)


if __name__ == '__main__':
    main()
