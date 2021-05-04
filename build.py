#!/usr/bin/env python

import os
import sys
import time
import logging
import subprocess

import click
import feedparser

import config


REGISTRY = config.DOCKER_REGISTRY
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
URLS = {
    'deposit_cli': 'https://github.com/ethereum/eth2.0-deposit-cli',
    'go_ethereum': 'https://github.com/ethereum/go-ethereum',
    'lighthouse': 'https://github.com/sigp/lighthouse',
    'prysm': 'https://github.com/prysmaticlabs/prysm',
    'teku': 'https://github.com/PegaSysEng/teku',
    'utility': 'https://github.com/wealdtech/ethdo'
}
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="{asctime} [{threadName}][{levelname}][{name}] {message}",
    style="{", datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def query_yes_no(question, default="yes"):
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError(f"invalid default answer: {default}")
    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        if choice in valid:
            return valid[choice]
        print("Please respond with 'yes' or 'no' "
              "(or 'y' or 'n').\n")


def parse_feed(feed, entry=0):
    entry = feed['entries'][entry]
    release = {
        'id': entry['id'].split('/')[-1],
        'link': entry['link'],
        'title': entry['title'],
        'content': entry['content'],
        'date': time.strftime("%a, %d %b %Y %H:%M", entry['updated_parsed'])
    }
    return release


def get_latest_releases(app_name):
    releases_url = URLS[app_name] + "/releases.atom"
    feed = feedparser.parse(releases_url)
    if len(feed['entries']) > 5:
        entries = 5
    else:
        entries = len(feed['entries'])
    latest_releases = []
    for x in range(entries):
        latest_releases.append(parse_feed(feed, x))
    return latest_releases


def get_available_apps():
    available_apps = []
    for filename in os.listdir(os.path.join(BASE_DIR, "dockerfiles/")):
        if filename.startswith("Dockerfile."):
            available_apps.append(filename.split(".")[-1])
    return available_apps


def get_desired_app(available_apps):
    # Print each available app and ask user which to build
    while True:
        for app in available_apps:
            print(f"[{available_apps.index(app) + 1}] {app}")
        value = int(input("Which do you want to build? "))
        try:
            app_name = available_apps[value - 1]
            break
        except IndexError:
            log.error(
                "You provided an incorrect value."
                f" Please enter a number between 1 and {len(available_apps)}"
            )
    return app_name


def get_desired_release(app_name):
    while True:
        latest_releases = get_latest_releases(app_name)
        print("[0] No specific release, just build master.")
        for release in latest_releases:
            print(
                f"[{latest_releases.index(release) +1}]"
                f" {release['id']} {release['title']} {release['date']}"
            )
        value = input("Which do you want to build?[1] ")
        # Set the default to 1
        if value == '':
            value = 1
        value = int(value)
        if value == 0:
            # Build master if no release is specified
            return {'id': 'master'}
        else:
            try:
                release = latest_releases[value - 1]
                break
            except IndexError:
                log.error(
                    "You provided an incorrect value."
                    f" Please enter a number between 0 and {len(latest_releases)}"
                )
    return release


def check_summary(args):
    print("*"*30)
    print("Summary")
    print("-------")
    print(f"App:           {args['app_name']}")
    print(f"Release:       {args['release']['id']}")
    print(f"Tag as latest: {args['tag_latest']}")
    print("*"*30)
    if not query_yes_no("Does this look correct?"):
        sys.exit(-1)


def build_docker_image(args):
    # Build container and tag it
    if args['tag_latest']:
        command = (
            f"docker build --build-arg RELEASE={args['release']['id']}"
            f" -t {REGISTRY}/ethereum/{args['app_name']}:{args['release']['id'].replace('+', '_')}"
            f" -t {REGISTRY}/ethereum/{args['app_name']}:latest"
            f" -f dockerfiles/Dockerfile.{args['app_name']} dockerfiles"
        )
    else:
        command = (
            f"docker build --build-arg RELEASE={args['release']['id']}"
            f" -t {REGISTRY}/ethereum/{args['app_name']}:{args['release']['id'].replace('+', '_')}"
            f" -f dockerfiles/Dockerfile.{args['app_name']} dockerfiles"
        )
    log.info(f"Running command: {command}")
    subprocess.run(command.split())


def push_docker_image(args):
    # Push image to registry
    if args['tag_latest']:
        command = (
            f"docker push {REGISTRY}/ethereum/{args['app_name']}:latest"
        )
        subprocess.run(command.split())
    command = (
        f"docker push {REGISTRY}/ethereum/{args['app_name']}:{args['release']['id'].replace('+', '_')}"
    )
    subprocess.run(command.split())


def prune_images():
    command = (
        "docker image prune -f"
    )
    subprocess.run(command.split())


def parse_args(app_name, tag_latest, build_latest, no_summary,
               prune, do_not_push, no_action):
    args = {}
    available_apps = get_available_apps()
    if app_name and app_name not in available_apps:
        print("You provided an incorrect value for app name.")
        app_name = get_desired_app(available_apps)
    if not app_name:
        print("Getting available apps")
        app_name = get_desired_app(available_apps)
    args['app_name'] = app_name
    if build_latest:
        release = get_latest_releases(app_name)[0]
    else:
        print(f"Getting releases for {app_name}")
        release = get_desired_release(app_name)
    args['tag_latest'] = tag_latest
    args['release'] = release
    args['summary'] = not no_summary
    args['push'] = not do_not_push
    args['prune'] = prune
    args['no_action'] = no_action
    return args


@click.command()
@click.option('-a', '--app-name', 'app_name',
              help="The name of the app you would like to build.")
@click.option('-b', '--build-latest', 'build_latest', is_flag=True,
              help=(
                  "Adding this flag means I will build the most latest release."
                  " (Instead of showing you available releases and asking for a number)"
              ))
@click.option('-t', '--tag-latest', 'tag_latest', is_flag=True,
              help="Adding this flag means I will tag the build as the latest.")
@click.option('-n', '--no-summary-confirmation', 'no_summary', is_flag=True,
              help="Adding this flag means I will not ask you to confirm the summary is correct")
@click.option('-p', '--prune', 'prune', is_flag=True,
              help=(
                  "Adding this flag means I will prune"
                  " dangling images (possibly deleting more than expected)"
              ))
@click.option('-d', '--do-not-push', 'do_not_push', is_flag=True,
              help=(
                  'Adding this flag means that once the image is built, I will **not** push'
                  ' it to the registry defined in the config.py file.'
              ))
@click.option('-i', '--no-action', 'no_action', is_flag=True,
              help=(
                  "Do not build, tag, push or prune. "
                  "Just show me what you would have done."
              ))
def main(app_name, tag_latest, build_latest, no_summary, prune, do_not_push,
         no_action):
    args = parse_args(
        app_name, tag_latest, build_latest, no_summary, prune, do_not_push,
        no_action
    )
    if args['summary']:
        check_summary(args)
    if args['no_action']:
        print("\n")
        print("-" * 30)
        print("What I would have done:")
        print(f"* I would have built the {args['app_name']} "
              f"image using release: {args['release']['id']}")
        if args['tag_latest']:
            print(f"* I would have tagged the image as latest and {args['release']['id']}")
    else:
        build_docker_image(args)
    if args['push']:
        if args['no_action']:
            if args['tag_latest']:
                print(f"* I would have pushed both tagged images to the registry: {REGISTRY}")
            else:
                print(f"* I would have pushed the tagged image to the registry: {REGISTRY}")
        else:
            push_docker_image(args)
    if args['prune']:
        if args['no_action']:
            print("* I would have pruned all dangling images from docker")
        else:
            prune_images()
    if args['no_action']:
        print("-" * 30)


if __name__ == '__main__':
    main()
