pipeline {
  agent any
  parameters {
    string(name: 'REGISTRY', defaultValue: '', description: 'Docker registry to push docker images')
    string(name: 'RELEASE', defaultValue: '', description: 'Release that this build will be tagged as')
    string(name: 'APP_NAME', defaultValue: '', description: 'Name of the app to build')
    string(name: 'EMAIL', defaultValue: '', description: 'Email recipient')
  }
  stages {
    stage('Checkout project') {
      steps {
        git(
          url: 'https://github.com/tjcim/replicant.git',
          branch: "master"
        )
      }
    }
    stage('Building Docker Image') {
      steps {
        script {
          sh """#!/bin/bash
                docker build --build-arg "RELEASE=${params.RELEASE}" \
                -t "${params.REGISTRY}/ethereum/${params.APP_NAME}:${params.RELEASE}" \
                -t "${params.REGISTRY}/ethereum/${params.APP_NAME}:latest" \
                -f "dockerfiles/Dockerfile.${params.APP_NAME}" .
          """
        }
      }
    }
    stage('Push Docker Image to Registry') {
      steps {
        script {
          sh """#!/bin/bash
                docker push "${params.REGISTRY}/ethereum/${params.APP_NAME}:latest"
                docker push "${params.REGISTRY}/ethereum/${params.APP_NAME}:${params.RELEASE}"
          """
        }
      }
    }
  }
  post {
    always {
      emailext body: "${params.APP_NAME} release ${params.RELEASE} was built and pushed to the registry.", to: "${params.EMAIL}", subject: "JENKINS: New release of ${params.APP_NAME} - ${currentBuild.currentResult}"
    }
  }
}
