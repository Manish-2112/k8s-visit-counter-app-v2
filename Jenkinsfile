pipeline {
    agent any

    parameters {
        choice(
            name: 'DEPLOY_TARGET',
            choices: ['aws-eks', 'local-k3s'],
            description: 'Target Kubernetes cluster overlay'
        )
        choice(
            name: 'ACTION',
            choices: ['deploy', 'rollback'],
            description: 'Deploy new build or trigger live rollback test'
        )
        string(
            name: 'ROLLBACK_REVISION',
            defaultValue: '0',
            description: 'Revision number to roll back to (0 = previous revision)'
        )
    }

    environment {
        AWS_REGION       = 'ap-south-1'
        AWS_ACCOUNT_ID   = 'YOUR_AWS_ACCOUNT_ID'
        EKS_CLUSTER_NAME = 'visit-counter-eks'
        K8S_NAMESPACE    = 'visit-counter'
        LOCAL_REGISTRY   = 'localhost:5000'
    }

    stages {
        stage('1. Checkout & Build Metadata') {
            steps {
                checkout scm
                script {
                    env.GIT_SHORT = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
                    env.IMAGE_TAG = "v${env.BUILD_NUMBER}-${env.GIT_SHORT}"
                    if (params.DEPLOY_TARGET == 'aws-eks') {
                        env.REGISTRY = "${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_REGION}.amazonaws.com"
                    } else {
                        env.REGISTRY = "${env.LOCAL_REGISTRY}"
                    }
                    env.BACKEND_IMAGE  = "${env.REGISTRY}/visit-counter-backend"
                    env.FRONTEND_IMAGE = "${env.REGISTRY}/visit-counter-frontend"
                    echo "Target: ${params.DEPLOY_TARGET} | Action: ${params.ACTION} | Tag: ${env.IMAGE_TAG}"
                }
            }
        }

        stage('2. Manual Rollback Mode') {
            when { expression { params.ACTION == 'rollback' } }
            steps {
                script {
                    if (params.DEPLOY_TARGET == 'aws-eks') {
                        sh "aws eks update-kubeconfig --region ${env.AWS_REGION} --name ${env.EKS_CLUSTER_NAME}"
                    }
                    def revFlag = params.ROLLBACK_REVISION != '0' ? "--to-revision=${params.ROLLBACK_REVISION}" : ""
                    sh """
                        kubectl -n ${env.K8S_NAMESPACE} rollout undo deployment/backend ${revFlag}
                        kubectl -n ${env.K8S_NAMESPACE} rollout undo deployment/frontend ${revFlag}
                        kubectl -n ${env.K8S_NAMESPACE} rollout status deployment/backend --timeout=180s
                        kubectl -n ${env.K8S_NAMESPACE} rollout status deployment/frontend --timeout=180s
                    """
                }
            }
        }

        stage('3. Static Analysis & Unit Tests') {
            when { expression { params.ACTION == 'deploy' } }
            steps {
                dir('backend') {
                    sh '''
                        python3 -m venv .venv
                        . .venv/bin/activate
                        pip install --upgrade pip
                        pip install -r requirements.txt ruff
                        ruff check app/ tests/
                        mkdir -p reports
                        python -m pytest --junitxml=reports/junit.xml
                    '''
                }
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'backend/reports/junit.xml'
                }
            }
        }

        stage('4. Build Immutable Docker Images') {
            when { expression { params.ACTION == 'deploy' } }
            steps {
                sh """
                    docker build -t ${env.BACKEND_IMAGE}:${env.IMAGE_TAG} -t ${env.BACKEND_IMAGE}:latest ./backend
                    docker build -t ${env.FRONTEND_IMAGE}:${env.IMAGE_TAG} -t ${env.FRONTEND_IMAGE}:latest ./frontend
                """
            }
        }

        stage('5. Container Security Scan (Trivy)') {
            when { expression { params.ACTION == 'deploy' } }
            steps {
                sh """
                    if command -v trivy >/dev/null 2>&1; then
                        trivy image --severity HIGH,CRITICAL --exit-code 0 ${env.BACKEND_IMAGE}:${env.IMAGE_TAG}
                        trivy image --severity HIGH,CRITICAL --exit-code 0 ${env.FRONTEND_IMAGE}:${env.IMAGE_TAG}
                    else
                        echo "Trivy not installed on agent; skipping vulnerability scan."
                    fi
                """
            }
        }

        stage('6. Push Images to Registry (ECR / Local)') {
            when { expression { params.ACTION == 'deploy' } }
            steps {
                script {
                    if (params.DEPLOY_TARGET == 'aws-eks') {
                        sh """
                            aws ecr get-login-password --region ${env.AWS_REGION} | \
                              docker login --username AWS --password-stdin ${env.REGISTRY}
                        """
                    }
                    sh """
                        docker push ${env.BACKEND_IMAGE}:${env.IMAGE_TAG}
                        docker push ${env.BACKEND_IMAGE}:latest
                        docker push ${env.FRONTEND_IMAGE}:${env.IMAGE_TAG}
                        docker push ${env.FRONTEND_IMAGE}:latest
                    """
                }
            }
        }

        stage('7. Sync Secrets from AWS SSM & Deploy to Kubernetes') {
            when { expression { params.ACTION == 'deploy' } }
            steps {
                script {
                    if (params.DEPLOY_TARGET == 'aws-eks') {
                        sh """
                            aws eks update-kubeconfig --region ${env.AWS_REGION} --name ${env.EKS_CLUSTER_NAME}
                            kubectl apply -k k8s/overlays/aws-eks/

                            # Fetch production DB credentials from AWS Systems Manager Parameter Store
                            DB_USER=\$(aws ssm get-parameter --name "/visit-counter/prod/POSTGRES_USER" --region ${env.AWS_REGION} --query "Parameter.Value" --output text)
                            DB_PASS=\$(aws ssm get-parameter --name "/visit-counter/prod/POSTGRES_PASSWORD" --with-decryption --region ${env.AWS_REGION} --query "Parameter.Value" --output text)

                            kubectl -n ${env.K8S_NAMESPACE} create secret generic db-secret \
                              --from-literal=POSTGRES_USER="\${DB_USER}" \
                              --from-literal=POSTGRES_PASSWORD="\${DB_PASS}" \
                              --dry-run=client -o yaml | kubectl apply -f -
                        """
                    } else {
                        sh "kubectl apply -k k8s/overlays/local-k3s/"
                    }

                    sh """
                        kubectl -n ${env.K8S_NAMESPACE} set env deployment/backend APP_VERSION=${env.IMAGE_TAG}
                        kubectl -n ${env.K8S_NAMESPACE} set image deployment/backend backend=${env.BACKEND_IMAGE}:${env.IMAGE_TAG}
                        kubectl -n ${env.K8S_NAMESPACE} set image deployment/frontend frontend=${env.FRONTEND_IMAGE}:${env.IMAGE_TAG}
                        kubectl -n ${env.K8S_NAMESPACE} annotate deployment/backend kubernetes.io/change-cause="Jenkins build ${env.IMAGE_TAG}" --overwrite
                        kubectl -n ${env.K8S_NAMESPACE} annotate deployment/frontend kubernetes.io/change-cause="Jenkins build ${env.IMAGE_TAG}" --overwrite

                        kubectl -n ${env.K8S_NAMESPACE} rollout status deployment/backend --timeout=180s
                        kubectl -n ${env.K8S_NAMESPACE} rollout status deployment/frontend --timeout=180s
                    """
                }
            }
        }

        stage('8. Post-Deploy Validation (Smoke Test)') {
            when { expression { params.ACTION == 'deploy' } }
            steps {
                sh """
                    kubectl -n ${env.K8S_NAMESPACE} run smoke-test --rm -i --restart=Never --image=curlimages/curl:8.10.1 -- \
                      sh -c "curl -sf http://backend-service:8000/healthz && curl -sf http://backend-service:8000/readyz && curl -sf http://backend-service:8000/api/visits"
                """
            }
        }
    }

    post {
        failure {
            script {
                if (params.ACTION == 'deploy') {
                    echo "Deployment or smoke test failed! Triggering automatic Kubernetes rollback..."
                    sh """
                        kubectl -n ${env.K8S_NAMESPACE} rollout undo deployment/backend || true
                        kubectl -n ${env.K8S_NAMESPACE} rollout undo deployment/frontend || true
                    """
                }
            }
        }
        always {
            sh 'docker image prune -f || true'
        }
    }
}
