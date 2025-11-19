pipeline {
    agent any

    environment {
        SSH_CRED = 'ec2-deploy-key'
        DEPLOY_USER = 'ubuntu'
        DEPLOY_HOST = 'localhost'
        APP_DIR = '/home/ubuntu/Two-Tier-Web-App'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build on Jenkins Server') {
            steps {
                echo "Nothing to build locally (Docker build will run on deploy server)"
            }
        }

        stage('Deploy to EC2') {
            steps {
                sshagent([SSH_CRED]) {
                    sh """
                        ssh -o StrictHostKeyChecking=no ${DEPLOY_USER}@${DEPLOY_HOST} '
                            cd ${APP_DIR}
                            git pull
                            docker-compose down || true
                            docker-compose up --build -d
                        '
                    """
                }
            }
        }
    }

    post {
        success {
            echo "Deployment Successful!"
        }
        failure {
            echo "Deployment Failed."
        }
    }
}
