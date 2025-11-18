pipeline {
  agent any
  stages {
    stage('Checkout') {
      steps { checkout scm }
    }
    stage('Unit tests') {
      steps {
        dir('app') {
          sh 'python3 -m pip install --user -r requirements.txt || true'
          sh 'pytest -q || true'
        }
      }
    }
    stage('Build & Deploy') {
      steps {
        sh 'docker compose -f docker-compose.yml build --no-cache'
        sh 'docker compose -f docker-compose.yml up -d --remove-orphans --build'
      }
    }
  }
}
